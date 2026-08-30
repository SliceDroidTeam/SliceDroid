"""
SliceDroid dashboard backend.

Slim Flask app exposing the final API route set (see DESIGN.md):

    GET  /                      dashboard shell (static, no template data)
    GET  /api/health            backend / trace / analysis status
    POST /api/upload            upload a trace (multipart field "file")
    GET  /api/trace-info        newest trace file metadata (or null)
    GET  /api/apps              known apps from the device mapping
    POST /api/apps/refresh      refresh mapping / running state
    POST /api/analyze           run the analysis pipeline synchronously
    GET  /api/analysis          last persisted analysis contract
    GET  /api/export/events     download sliced events (json or csv)
    GET  /api/export/analysis   download the analysis contract
"""

from __future__ import annotations

import csv
import gzip
import io
import json
import os
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from flask import Flask, Response, jsonify, render_template, request, send_file
from werkzeug.utils import secure_filename

from src.services.app_mapper_service import AppMapperService

#: Upload size cap (bytes) — the legacy app had no explicit limit.
MAX_UPLOAD_BYTES = 2 * 1024 * 1024 * 1024  # 2 GB

#: Accepted upload extensions. Gzipped uploads are decompressed on arrival;
#: everything is stored in TRACES_DIR as a plain .trace file.
ALLOWED_EXTENSIONS = {'.trace', '.gz', '.txt', '.log'}


def create_app(config_name: str = 'default') -> Flask:
    """Application factory pattern"""
    app = Flask(
        __name__,
        static_folder='src/static',
        template_folder='src/templates'
    )

    # Load configuration
    from src.config import config
    app.config.from_object(config[config_name])
    app.config_class = config[config_name]
    app.config['MAX_CONTENT_LENGTH'] = MAX_UPLOAD_BYTES

    return app


app = create_app(os.getenv('FLASK_ENV', 'default'))
Config = app.config_class

app_mapper = AppMapperService(Config.PROJECT_ROOT)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def get_trace_file() -> Optional[Path]:
    """
    Return the active trace file: the newest *.trace in TRACES_DIR.

    When both trace.trace and trace_corrected.trace exist and the corrected
    trace is at least as new, prefer the corrected one.
    """
    traces_dir = Path(Config.TRACES_DIR)
    if not traces_dir.is_dir():
        return None
    traces = sorted(traces_dir.glob('*.trace'), key=lambda p: p.stat().st_mtime)
    if not traces:
        return None
    newest = traces[-1]

    corrected = traces_dir / 'trace_corrected.trace'
    plain = traces_dir / 'trace.trace'
    if (newest == plain and corrected.exists()
            and corrected.stat().st_mtime >= plain.stat().st_mtime):
        return corrected
    return newest


def _apps_payload() -> dict[str, Any]:
    """Serialize the app mapping, running apps first, then by name."""
    apps = [
        {
            'package': info.package_name,
            'name': info.commercial_name,
            'processes': info.processes,
            'running': info.is_running,
        }
        for info in app_mapper.get_all_apps()
    ]
    apps.sort(key=lambda a: (not a['running'], (a['name'] or a['package']).lower()))
    return {'apps': apps}


def _api_error(message: str, status: int):
    return jsonify({'error': message}), status


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@app.route('/')
def index():
    return render_template('index.html')


@app.route('/api/health')
def health():
    return jsonify({
        'status': 'ok',
        'trace_loaded': get_trace_file() is not None,
        'analysis_available': Path(Config.ANALYSIS_JSON).exists(),
    })


@app.route('/api/upload', methods=['POST'])
def upload_trace():
    if 'file' not in request.files:
        return _api_error('No file provided (multipart field "file")', 400)

    file = request.files['file']
    filename = secure_filename(file.filename or '')
    if not filename:
        return _api_error('No file selected', 400)

    suffix = Path(filename).suffix.lower()
    if suffix not in ALLOWED_EXTENSIONS:
        return _api_error(
            f'Unsupported file type "{suffix}". '
            f'Allowed: {", ".join(sorted(ALLOWED_EXTENSIONS))}', 400)

    traces_dir = Path(Config.TRACES_DIR)
    traces_dir.mkdir(parents=True, exist_ok=True)

    # Store everything as a plain .trace so it becomes the active trace.
    stem = filename[:-len(suffix)]
    if suffix == '.gz' and stem.lower().endswith('.trace'):
        stem = stem[:-len('.trace')]
    destination = traces_dir / f'{stem}.trace'

    try:
        if suffix == '.gz':
            with gzip.open(file.stream, 'rb') as src, open(destination, 'wb') as dst:
                shutil.copyfileobj(src, dst)
        else:
            file.save(destination)
    except (OSError, EOFError, gzip.BadGzipFile) as exc:
        if destination.exists():
            destination.unlink()
        return _api_error(f'Failed to store trace: {exc}', 400)

    return jsonify({
        'filename': destination.name,
        'size': destination.stat().st_size,
    })


@app.route('/api/trace-info')
def trace_info():
    trace = get_trace_file()
    if trace is None:
        return jsonify(None)
    stat = trace.stat()
    return jsonify({
        'filename': trace.name,
        'size': stat.st_size,
        'mtime': datetime.fromtimestamp(stat.st_mtime, timezone.utc).isoformat(),
    })


#: Cache for scan_processes keyed by (path, mtime) so switching to PID mode
#: does not re-scan a large trace on every request.
_process_cache: dict[tuple[str, float], list] = {}


@app.route('/api/trace-processes')
def trace_processes():
    """List the processes present in the active trace, for the PID picker."""
    trace = get_trace_file()
    if trace is None:
        return jsonify({'processes': []})

    from src.analysis.parser import scan_processes
    key = (str(trace), trace.stat().st_mtime)
    processes = _process_cache.get(key)
    if processes is None:
        try:
            processes = scan_processes(trace)
        except OSError as exc:
            return _api_error(f'Could not read trace: {exc}', 500)
        _process_cache.clear()          # only the current trace matters
        _process_cache[key] = processes
    return jsonify({'processes': processes})


@app.route('/api/apps')
def list_apps():
    return jsonify(_apps_payload())


@app.route('/api/apps/refresh', methods=['POST'])
def refresh_apps():
    result = app_mapper.refresh_mapping_from_device(force=True)
    if 'error' in result:
        return _api_error(result['error'], 500)
    return jsonify(_apps_payload())


@app.route('/api/analyze', methods=['POST'])
def analyze():
    from src.analysis import run_analysis

    data = request.get_json(silent=True) or {}
    mode = data.get('mode')

    trace_file = get_trace_file()
    if trace_file is None:
        return _api_error('No trace file available. Upload a trace first.', 400)

    try:
        window_size = int(data['window_size']) if data.get('window_size') is not None else 500
        overlap = int(data['overlap']) if data.get('overlap') is not None else 100
    except (TypeError, ValueError):
        return _api_error('window_size and overlap must be integers', 400)
    if window_size <= 0 or overlap < 0 or overlap >= window_size:
        return _api_error('window_size must be > 0 and overlap must satisfy 0 <= overlap < window_size', 400)

    target_app = None
    target_pid = None

    if mode == 'pid':
        try:
            target_pid = int(data.get('pid'))
        except (TypeError, ValueError):
            return _api_error('pid mode requires an integer "pid"', 400)
    elif mode == 'app':
        package = data.get('package')
        if not package:
            return _api_error('app mode requires a "package"', 400)
        info = app_mapper.get_app_by_package(package)
        if info is None:
            return _api_error(f'Unknown app package: {package}', 404)
        target_app = {
            'package': info.package_name,
            'name': info.commercial_name,
            'process_names': app_mapper.get_processes_for_app(package),
        }
    else:
        return _api_error('mode must be "app" or "pid"', 400)

    try:
        result = run_analysis(
            trace_file,
            target_app=target_app,
            target_pid=target_pid,
            window_size=window_size,
            overlap=overlap,
        )
    except ValueError as exc:
        status = 404 if 'not found' in str(exc).lower() else 400
        return _api_error(str(exc), status)
    except Exception as exc:  # surface pipeline failures as JSON, not HTML 500s
        app.logger.exception('Analysis failed')
        return _api_error(f'Analysis failed: {exc}', 500)

    return jsonify(result)


@app.route('/api/analysis')
def get_analysis():
    analysis_path = Path(Config.ANALYSIS_JSON)
    if not analysis_path.exists():
        # No analysis yet is a normal state on first load, not an error.
        return jsonify(None)
    # The file is already the exact JSON payload — stream it without re-parsing.
    return send_file(analysis_path, mimetype='application/json')


@app.route('/api/export/events')
def export_events():
    events_path = Path(Config.SLICED_EVENTS_JSON)
    if not events_path.exists():
        return _api_error('No sliced events available. Run an analysis first.', 404)

    export_format = request.args.get('format', 'json').lower()
    if export_format == 'json':
        return send_file(events_path, as_attachment=True,
                         download_name='sliced_events.json',
                         mimetype='application/json')
    if export_format != 'csv':
        return _api_error('format must be "json" or "csv"', 400)

    with open(events_path, 'r') as f:
        events = json.load(f)

    # Flatten each event's "details" dict into details.<key> columns.
    base_fields: list = []
    detail_fields: list = []
    for event in events:
        for key in event:
            if key != 'details' and key not in base_fields:
                base_fields.append(key)
        for key in (event.get('details') or {}):
            column = f'details.{key}'
            if column not in detail_fields:
                detail_fields.append(column)

    # Stream row by row so the full CSV never has to exist in memory.
    def generate_csv():
        buffer = io.StringIO()
        writer = csv.DictWriter(buffer, fieldnames=base_fields + detail_fields,
                                extrasaction='ignore')
        writer.writeheader()
        for event in events:
            row = {k: v for k, v in event.items() if k != 'details'}
            for key, value in (event.get('details') or {}).items():
                row[f'details.{key}'] = value
            writer.writerow(row)
            yield buffer.getvalue()
            buffer.seek(0)
            buffer.truncate(0)

    return Response(
        generate_csv(),
        mimetype='text/csv',
        headers={'Content-Disposition': 'attachment; filename=sliced_events.csv'},
    )


@app.route('/api/export/analysis')
def export_analysis():
    analysis_path = Path(Config.ANALYSIS_JSON)
    if not analysis_path.exists():
        return _api_error('No analysis available. Run an analysis first.', 404)
    return send_file(analysis_path, as_attachment=True,
                     download_name='analysis.json',
                     mimetype='application/json')


# ---------------------------------------------------------------------------
# Error handlers — JSON errors for API paths
# ---------------------------------------------------------------------------

@app.errorhandler(404)
def handle_404(error):
    if request.path.startswith('/api/'):
        return _api_error('Not found', 404)
    return error


@app.errorhandler(405)
def handle_405(error):
    if request.path.startswith('/api/'):
        return _api_error('Method not allowed', 405)
    return error


@app.errorhandler(413)
def handle_413(error):
    return _api_error(f'File too large (limit {MAX_UPLOAD_BYTES} bytes)', 413)


@app.errorhandler(500)
def handle_500(error):
    if request.path.startswith('/api/'):
        return _api_error('Internal server error', 500)
    return error


if __name__ == '__main__':
    config_errors = Config.validate_paths()
    if config_errors:
        print('Configuration warnings:')
        for error in config_errors:
            print(f'  - {error}')

    app.run(host=Config.HOST, port=Config.PORT, debug=Config.DEBUG)
