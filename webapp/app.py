from flask import Flask, render_template, request, jsonify, send_file, make_response
import os
import json
import pandas as pd
import csv
from io import StringIO
import matplotlib.pyplot as plt
import matplotlib
matplotlib.use('Agg')
import numpy as np
import base64
from io import BytesIO
import re
from pathlib import Path
from src.config import Config
import tempfile
import threading
import uuid
from werkzeug.utils import secure_filename
from src.services.trace_processor import TraceProcessor
from src.services.advanced_analytics import AdvancedAnalytics
from src.services.comprehensive_analyzer import ComprehensiveAnalyzer
from src.services.app_mapper_service import AppMapperService
import shutil

def create_app(config_name='default'):
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

    return app

app = create_app(os.getenv('FLASK_ENV', 'default'))

# Global variables for upload tracking
upload_progress = {}
trace_processor = TraceProcessor(app.config_class)
advanced_analytics = AdvancedAnalytics(app.config_class)
comprehensive_analyzer = ComprehensiveAnalyzer(app.config_class)
app_mapper = AppMapperService(app.config_class.PROJECT_ROOT)

# Load device name mapping from rdevs.txt
device_name_mapping = {}
try:
    rdevs_path = app.config_class.PROJECT_ROOT / 'data' / 'nodes_and_files_data' / 'rdevs.txt'
    if rdevs_path.exists():
        with open(rdevs_path, 'r') as f:
            for line in f:
                parts = line.strip().split()
                if len(parts) >= 2:
                    device_name = parts[0]
                    device_id = int(parts[1])
                    device_name_mapping[device_id] = device_name
        print(f"Loaded {len(device_name_mapping)} device name mappings from {rdevs_path}")
    else:
        print(f"Device mapping file not found: {rdevs_path}")
except Exception as e:
    print(f"Error loading device name mapping: {e}")

def load_data():
    """Load the processed events from JSON file"""
    events_file = app.config_class.PROCESSED_EVENTS_JSON
    try:
        if Path(events_file).exists():
            with open(events_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                if not isinstance(data, list):
                    return []
                return data
    except (json.JSONDecodeError, IOError) as e:
        print(f"Error loading data from {events_file}: {e}")
    return []

def get_unique_pids(events):
    """Extract unique PIDs from events"""
    pids = set()
    for event in events:
        if 'tgid' in event:
            pids.add(event['tgid'])
    return sorted(list(pids))

def get_unique_devices(events):
    """Extract unique devices from events"""
    devices = set()
    for event in events:
        if 'details' in event:
            # Check for both k_dev and k__dev (double underscore)
            device_key = None
            if 'k_dev' in event['details']:
                device_key = 'k_dev'
            elif 'k__dev' in event['details']:
                device_key = 'k__dev'

            if device_key and event['details'][device_key] != 0:
                devices.add(event['details'][device_key])
    return sorted(list(devices))

def filter_events(events, pid=None, device=None):
    """Filter events by PID and/or device"""
    if not isinstance(events, list):
        return []

    filtered = events

    if pid:
        try:
            pid_int = int(pid)
            filtered = [e for e in filtered if isinstance(e, dict) and 'tgid' in e and e['tgid'] == pid_int]
        except (ValueError, TypeError):
            return []

    if device:
        try:
            device_int = int(device)
            def has_matching_device(event):
                if not isinstance(event, dict) or 'details' not in event:
                    return False
                details = event['details']
                if not isinstance(details, dict):
                    return False
                # Check both k_dev and k__dev
                device_value = details.get('k_dev') or details.get('k__dev')
                return device_value == device_int

            filtered = [e for e in filtered if has_matching_device(e)]
        except (ValueError, TypeError):
            return []

    return filtered

def create_timeline_data(events):
    """Create timeline data for visualization"""
    timeline_data = []
    max_events = app.config_class.TIMELINE_MAX_EVENTS

    # Limit events for performance
    events_to_process = events[:max_events] if len(events) > max_events else events

    for idx, event in enumerate(events_to_process):
        if not isinstance(event, dict):
            continue

        event_type = event.get('event', 'unknown')
        category = app.config_class.get_event_category(event_type)

        # Get device info
        device = None
        pathname = None
        if 'details' in event and isinstance(event['details'], dict):
            # Check both k_dev and k__dev
            device = event['details'].get('k_dev') or event['details'].get('k__dev')
            pathname = event['details'].get('pathname', None)

        timeline_data.append({
            'id': idx,
            'time': idx,
            'event': event_type,
            'category': category,
            'device': device,
            'pathname': pathname,
            'pid': event.get('tgid', None),
            'tid': event.get('tid', None),
        })

    return timeline_data

def create_device_stats(events):
    """Create device usage statistics"""
    device_counts = {}
    device_paths = {}

    for event in events:
        if 'details' in event:
            # Check both k_dev and k__dev
            device = event['details'].get('k_dev') or event['details'].get('k__dev')
            if not device or device == 0:
                continue

            # Count device usage
            if device not in device_counts:
                device_counts[device] = 0
            device_counts[device] += 1

            # Track pathnames for each device
            if 'pathname' in event['details'] and event['details']['pathname']:
                if device not in device_paths:
                    device_paths[device] = set()
                device_paths[device].add(event['details']['pathname'])

    # Convert to list of dictionaries for easy rendering
    device_stats = []
    for device, count in sorted(device_counts.items(), key=lambda x: x[1], reverse=True):
        paths = list(device_paths.get(device, []))
        device_stats.append({
            'device': device,
            'count': count,
            'paths': paths,
            'path_count': len(paths)
        })

    return device_stats

def create_event_stats(events):
    """Create event type statistics"""
    event_counts = {}

    for event in events:
        event_type = event.get('event', 'unknown')
        if event_type not in event_counts:
            event_counts[event_type] = 0
        event_counts[event_type] += 1

    return [{'event': k, 'count': v} for k, v in
            sorted(event_counts.items(), key=lambda x: x[1], reverse=True)]

def create_pie_chart_base64(data, labels, title):
    """Create a base64 encoded pie chart"""
    if not data or not labels or len(data) != len(labels):
        return None

    try:
        plt.figure(figsize=(8, 6))
        plt.pie(data, labels=labels, autopct='%1.1f%%', startangle=90)
        plt.axis('equal')
        plt.title(title)

        buffer = BytesIO()
        plt.savefig(buffer, format='png', dpi=100, bbox_inches='tight')
        buffer.seek(0)
        plt.close()

        img_str = base64.b64encode(buffer.getvalue()).decode('utf-8')
        return img_str
    except Exception as e:
        print(f"Error creating pie chart: {e}")
        plt.close()
        return None

def process_tcp_events(events):
    """Extract and process TCP state events"""
    tcp_events = []
    for event in events:
        if event.get('event') == "inet_sock_set_state":
            tcp_events.append({
                'time': tcp_events[-1]['time'] + 1 if tcp_events else 0,
                'state': event['details'].get('newstate', 'unknown'),
                'daddr': event['details'].get('daddr', 'unknown'),
                'saddr': event['details'].get('saddr', 'unknown'),
                'sport': event['details'].get('sport', 'unknown'),
                'dport': event['details'].get('dport', 'unknown'),
                'pid': event.get('tgid', None),
                'tid': event.get('tid', None),
            })
    return tcp_events

# Routes
@app.route('/')
def index():
    """Main application page"""
    events = load_data()
    pids = get_unique_pids(events)
    devices = get_unique_devices(events)
    return render_template('index.html', pids=pids, devices=devices)

@app.route('/api/timeline')
def timeline_data():
    """API endpoint for timeline data"""
    try:
        events = load_data()
        pid = request.args.get('pid')
        device = request.args.get('device')

        # Validate input parameters
        if pid and not pid.isdigit():
            return jsonify({'error': 'Invalid PID parameter'}), 400
        if device and not device.isdigit():
            return jsonify({'error': 'Invalid device parameter'}), 400

        filtered_events = filter_events(events, pid, device)
        timeline_data = create_timeline_data(filtered_events)

        return jsonify(timeline_data)
    except Exception as e:
        print(f"Error in timeline_data: {e}")
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/api/device_stats')
def device_stats():
    """API endpoint for device statistics"""
    try:
        events = load_data()
        pid = request.args.get('pid')

        # Validate input parameters
        if pid and not pid.isdigit():
            return jsonify({'error': 'Invalid PID parameter'}), 400

        filtered_events = filter_events(events, pid)
        stats = create_device_stats(filtered_events)

        return jsonify(stats)
    except Exception as e:
        print(f"Error in device_stats: {e}")
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/api/event_stats')
def event_stats():
    """API endpoint for event type statistics"""
    try:
        events = load_data()
        pid = request.args.get('pid')
        device = request.args.get('device')

        # Validate input parameters
        if pid and not pid.isdigit():
            return jsonify({'error': 'Invalid PID parameter'}), 400
        if device and not device.isdigit():
            return jsonify({'error': 'Invalid device parameter'}), 400

        filtered_events = filter_events(events, pid, device)
        stats = create_event_stats(filtered_events)

        return jsonify(stats)
    except Exception as e:
        print(f"Error in event_stats: {e}")
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/api/device_pie_chart')
def device_pie_chart():
    """API endpoint for device usage pie chart"""
    try:
        events = load_data()
        pid = request.args.get('pid')

        # Validate input parameters
        if pid and not pid.isdigit():
            return jsonify({'error': 'Invalid PID parameter'}), 400

        filtered_events = filter_events(events, pid)
        device_stats = create_device_stats(filtered_events)

        # Use configurable number of top devices for chart
        top_n = app.config_class.CHART_TOP_N_DEVICES
        top_devices = device_stats[:top_n]
        counts = [d['count'] for d in top_devices]
        labels = [f"Device {d['device']}" for d in top_devices]

        img_str = create_pie_chart_base64(counts, labels, f'Top {top_n} Devices by Usage')

        if img_str is None:
            return jsonify({'error': 'Failed to generate chart'}), 500

        return jsonify({'image': f'data:image/png;base64,{img_str}'})
    except Exception as e:
        print(f"Error in device_pie_chart: {e}")
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/api/event_pie_chart')
def event_pie_chart():
    """API endpoint for event type pie chart"""
    try:
        events = load_data()
        pid = request.args.get('pid')
        device = request.args.get('device')

        # Validate input parameters
        if pid and not pid.isdigit():
            return jsonify({'error': 'Invalid PID parameter'}), 400
        if device and not device.isdigit():
            return jsonify({'error': 'Invalid device parameter'}), 400

        filtered_events = filter_events(events, pid, device)
        event_stats = create_event_stats(filtered_events)

        # Use configurable number of top events for chart
        top_n = app.config_class.CHART_TOP_N_EVENTS
        top_events = event_stats[:top_n]
        counts = [e['count'] for e in top_events]
        labels = [e['event'] for e in top_events]

        img_str = create_pie_chart_base64(counts, labels, f'Top {top_n} Event Types')

        if img_str is None:
            return jsonify({'error': 'Failed to generate chart'}), 500

        return jsonify({'image': f'data:image/png;base64,{img_str}'})
    except Exception as e:
        print(f"Error in event_pie_chart: {e}")
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/api/tcp_stats')
def tcp_stats():
    """API endpoint for TCP statistics"""
    try:
        events = load_data()
        pid = request.args.get('pid')

        # Validate input parameters
        if pid and not pid.isdigit():
            return jsonify({'error': 'Invalid PID parameter'}), 400

        filtered_events = filter_events(events, pid)
        tcp_events = process_tcp_events(filtered_events)

        return jsonify(tcp_events)
    except Exception as e:
        print(f"Error in tcp_stats: {e}")
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/api/config')
def get_config():
    """API endpoint for client configuration"""
    return jsonify({
        'event_categories': app.config_class.EVENT_CATEGORIES,
        'timeline_max_events': app.config_class.TIMELINE_MAX_EVENTS,
        'default_zoom': app.config_class.TIMELINE_DEFAULT_ZOOM,
        'top_devices': app.config_class.CHART_TOP_N_DEVICES,
        'top_events': app.config_class.CHART_TOP_N_EVENTS
    })

@app.route('/api/health')
def health_check():
    """Health check endpoint"""
    errors = app.config_class.validate_paths()
    status = 'healthy' if not errors else 'unhealthy'
    return jsonify({
        'status': status,
        'errors': errors,
        'data_file_exists': Path(app.config_class.PROCESSED_EVENTS_JSON).exists()
    })

@app.route('/api/preloaded-file')
def preloaded_file_info():
    """Return information about the preloaded file if one exists"""
    default_trace_path = app.config_class.PROJECT_ROOT / 'data' / 'traces' / 'trace.trace'
    processed_file_exists = Path(app.config_class.PROCESSED_EVENTS_JSON).exists()

    if default_trace_path.exists() and processed_file_exists:
        return jsonify({
            'preloaded': True,
            'filename': default_trace_path.name
        })
    else:
        return jsonify({
            'preloaded': False
        })

@app.route('/api/upload', methods=['POST'])
def upload_trace():
    """Upload and process a trace file"""
    try:
        if 'trace_file' not in request.files:
            return jsonify({'error': 'No file provided'}), 400

        file = request.files['trace_file']
        if file.filename == '':
            return jsonify({'error': 'No file selected'}), 400

        if not file.filename.endswith('.trace'):
            return jsonify({'error': 'File must have .trace extension'}), 400

        # Generate unique upload ID
        upload_id = str(uuid.uuid4())

        # Save uploaded file temporarily
        filename = secure_filename(file.filename)
        temp_dir = tempfile.mkdtemp()
        temp_file_path = os.path.join(temp_dir, filename)
        file.save(temp_file_path)

        # Initialize progress tracking
        upload_progress[upload_id] = {
            'progress': 0,
            'status': 'Starting...',
            'completed': False,
            'error': None,
            'result': None
        }

        # Start processing in background thread
        def process_file():
            def progress_callback(progress, status):
                upload_progress[upload_id]['progress'] = progress
                upload_progress[upload_id]['status'] = status

            try:
                result = trace_processor.process_trace_file(temp_file_path, progress_callback)
                upload_progress[upload_id]['result'] = result
                upload_progress[upload_id]['completed'] = True

                if not result['success']:
                    upload_progress[upload_id]['error'] = result.get('error', 'Unknown error')

            except Exception as e:
                upload_progress[upload_id]['error'] = str(e)
                upload_progress[upload_id]['completed'] = True
            finally:
                # Clean up temporary file
                try:
                    shutil.rmtree(temp_dir)
                except:
                    pass

        thread = threading.Thread(target=process_file)
        thread.daemon = True
        thread.start()

        return jsonify({
            'upload_id': upload_id,
            'message': 'Upload started, processing in background'
        })

    except Exception as e:
        return jsonify({'error': f'Upload failed: {str(e)}'}), 500

@app.route('/api/upload/progress/<upload_id>')
def upload_progress_check(upload_id):
    """Check upload progress"""
    if upload_id not in upload_progress:
        return jsonify({'error': 'Upload ID not found'}), 404

    progress_data = upload_progress[upload_id]

    # Clean up completed uploads after returning status
    if progress_data['completed']:
        # Keep for a short time then clean up
        def cleanup():
            import time
            time.sleep(60)  # Keep for 1 minute
            if upload_id in upload_progress:
                del upload_progress[upload_id]

        cleanup_thread = threading.Thread(target=cleanup)
        cleanup_thread.daemon = True
        cleanup_thread.start()

    return jsonify(progress_data)

@app.route('/api/advanced-analytics')
def get_advanced_analytics():
    """API endpoint for advanced analytics"""
    try:
        events = load_data()
        pid = request.args.get('pid')
        window_size = int(request.args.get('window_size', 1000))
        overlap = int(request.args.get('overlap', 200))

        # Validate PID parameter
        target_pid = None
        if pid:
            if not pid.isdigit():
                return jsonify({'error': 'Invalid PID parameter'}), 400
            target_pid = int(pid)

        # Validate window parameters
        if overlap >= window_size:
            return jsonify({'error': 'Overlap must be less than window size'}), 400

        # Perform advanced analysis with custom parameters
        analysis = advanced_analytics.analyze_trace_data(events, target_pid, window_size, overlap)

        return jsonify(analysis)

    except Exception as e:
        print(f"Error in advanced analytics: {e}")
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/api/export/events')
def export_events():
    """Export events data in specified format"""
    try:
        events = load_data()
        pid = request.args.get('pid')
        device = request.args.get('device')
        format_type = request.args.get('format', 'json')
        limit = request.args.get('limit')

        # Validate input parameters
        if pid and not pid.isdigit():
            return jsonify({'error': 'Invalid PID parameter'}), 400
        if device and not device.isdigit():
            return jsonify({'error': 'Invalid device parameter'}), 400

        # Filter events
        filtered_events = filter_events(events, pid, device)
        
        # Apply limit if specified
        if limit:
            try:
                limit_int = int(limit)
                filtered_events = filtered_events[:limit_int]
            except ValueError:
                return jsonify({'error': 'Invalid limit parameter'}), 400

        # Generate filename
        timestamp = pd.Timestamp.now().strftime('%Y%m%d_%H%M%S')
        filename_parts = ['events']
        if pid:
            filename_parts.append(f'pid{pid}')
        if device:
            filename_parts.append(f'dev{device}')
        filename_parts.append(timestamp)
        
        if format_type.lower() == 'csv':
            # Create CSV response
            df = pd.DataFrame(filtered_events)
            output = StringIO()
            df.to_csv(output, index=False)
            output.seek(0)
            
            filename = '_'.join(filename_parts) + '.csv'
            response = make_response(output.getvalue())
            response.headers['Content-Type'] = 'text/csv'
            response.headers['Content-Disposition'] = f'attachment; filename={filename}'
            return response
        else:
            # JSON response
            filename = '_'.join(filename_parts) + '.json'
            response = make_response(json.dumps(filtered_events, indent=2))
            response.headers['Content-Type'] = 'application/json'
            response.headers['Content-Disposition'] = f'attachment; filename={filename}'
            return response

    except Exception as e:
        print(f"Error in export events: {e}")
        return jsonify({'error': 'Internal server error'}), 500


@app.route('/api/network-analysis')
def get_network_analysis():
    """API endpoint for network analysis"""
    try:
        events = load_data()
        pid = request.args.get('pid')
        
        # Validate PID parameter
        target_pid = None
        if pid:
            if not pid.isdigit():
                return jsonify({'error': 'Invalid PID parameter'}), 400
            target_pid = int(pid)
        
        # Perform network analysis
        network_analysis = comprehensive_analyzer.analyze_network_flows(events, target_pid)
        
        return jsonify({
            'network_analysis': network_analysis
        })
        
    except Exception as e:
        print(f"Error in network analysis: {e}")
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/api/process-analysis')
def get_process_analysis():
    """API endpoint for process analysis"""
    try:
        events = load_data()
        pid = request.args.get('pid')
        
        # Validate PID parameter
        target_pid = None
        if pid:
            if not pid.isdigit():
                return jsonify({'error': 'Invalid PID parameter'}), 400
            target_pid = int(pid)
        
        # Perform process genealogy analysis
        process_analysis = comprehensive_analyzer.analyze_process_genealogy(events, target_pid)
        
        return jsonify({
            'process_analysis': process_analysis
        })
        
    except Exception as e:
        print(f"Error in process analysis: {e}")
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/api/apps')
def get_apps():
    """API endpoint for getting available apps"""
    try:
        category = request.args.get('category')
        search = request.args.get('search')
        
        if search:
            apps = app_mapper.search_apps(search)
        else:
            apps = app_mapper.get_all_apps(category)
            
        # Convert to dictionaries for JSON serialization
        apps_data = [app_mapper.to_dict(app) for app in apps]
        
        return jsonify({
            'apps': apps_data,
            'categories': app_mapper.get_categories(),
            'stats': app_mapper.get_app_stats(),
            'device_status': app_mapper.get_device_status()
        })
        
    except Exception as e:
        print(f"Error in get_apps: {e}")
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/api/apps/refresh', methods=['POST'])
def refresh_apps():
    """API endpoint for refreshing app mapping from device"""
    try:
        result = app_mapper.refresh_mapping_from_device()
        
        if 'error' in result:
            return jsonify(result), 400
        else:
            return jsonify(result)
            
    except Exception as e:
        print(f"Error in refresh_apps: {e}")
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/api/apps/generate-targets', methods=['POST'])
def generate_process_targets():
    """API endpoint for generating process targets from selected apps"""
    try:
        data = request.get_json()
        selected_apps = data.get('selected_apps', [])
        
        if not selected_apps:
            return jsonify({'error': 'No apps selected'}), 400
            
        # Export process targets
        targets_file = app_mapper.export_process_targets(selected_apps)
        
        # Get process names for confirmation
        process_names = []
        for app_id in selected_apps:
            processes = app_mapper.get_processes_for_app(app_id)
            process_names.extend(processes)
            
        unique_processes = sorted(list(set(process_names)))
        
        return jsonify({
            'success': True,
            'targets_file': targets_file,
            'processes': unique_processes,
            'message': f'Generated {len(unique_processes)} process targets'
        })
        
    except Exception as e:
        print(f"Error in generate_process_targets: {e}")
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/api/apps/analyze', methods=['POST'])
def analyze_app():
    """API endpoint for re-slicing events for a specific app"""
    try:
        data = request.get_json()
        app_id = data.get('app_id')
        
        if not app_id:
            return jsonify({'error': 'No app specified'}), 400
        
        # Load all events (original unfiltered data)
        events = load_data()
        if not events:
            return jsonify({'error': 'No trace data available'}), 400
        
        # Get PIDs for the selected app
        app_pids = app_mapper.get_pids_for_app(app_id, events)
        if not app_pids:
            return jsonify({'error': f'No PIDs found for app {app_id} in trace data'}), 400
        
        print(f"Found PIDs {app_pids} for app {app_id}")
        
        # Use the main PID (first one found) for slicing
        target_pid = app_pids[0]
        
        # Generate process targets file automatically
        app_mapper.export_process_targets([app_id])
        
        # Perform slicing analysis for this specific app
        sliced_events = comprehensive_analyzer.slice_events(events, target_pid, asynchronous=True)
        
        # Create app-specific processed events file
        app_name = app_mapper.get_app_by_package(app_id)
        app_display_name = app_name.commercial_name if app_name else app_id
        
        # Save sliced events to a new file for the dashboard to use
        app_events_file = app.config_class.EXPORTS_DIR / f'app_{app_id.replace(".", "_")}_events.json'
        app_events_file.parent.mkdir(parents=True, exist_ok=True)
        
        with open(app_events_file, 'w', encoding='utf-8') as f:
            json.dump(sliced_events, f, indent=2, ensure_ascii=False)
        
        # Update the main processed events file to show app-specific data
        main_events_file = app.config_class.PROCESSED_EVENTS_JSON
        with open(main_events_file, 'w', encoding='utf-8') as f:
            json.dump(sliced_events, f, indent=2, ensure_ascii=False)
        
        return jsonify({
            'success': True,
            'app_name': app_display_name,
            'target_pid': target_pid,
            'pids': app_pids,
            'events_count': len(sliced_events),
            'message': f'Analysis complete for {app_display_name}. Found {len(sliced_events)} relevant events.',
            'events_file': str(app_events_file)
        })
        
    except Exception as e:
        print(f"Error in analyze_app: {e}")
        return jsonify({'error': f'Analysis failed: {str(e)}'}), 500

@app.route('/api/apps/search')
def search_apps():
    """API endpoint for searching apps"""
    try:
        query = request.args.get('q', '')
        
        if not query:
            return jsonify({'apps': []})
            
        apps = app_mapper.search_apps(query)
        apps_data = [app_mapper.to_dict(app) for app in apps]
        
        return jsonify({'apps': apps_data})
        
    except Exception as e:
        print(f"Error in search_apps: {e}")
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/api/export/analysis')
def export_analysis():
    """Export analysis results in specified format"""
    try:
        events = load_data()
        pid = request.args.get('pid')
        format_type = request.args.get('format', 'json')
        window_size = int(request.args.get('window_size', 1000))
        overlap = int(request.args.get('overlap', 200))

        # Validate PID parameter
        target_pid = None
        if pid:
            if not pid.isdigit():
                return jsonify({'error': 'Invalid PID parameter'}), 400
            target_pid = int(pid)

        # Perform analysis
        analysis = advanced_analytics.analyze_trace_data(events, target_pid, window_size, overlap)
        
        # Generate filename
        timestamp = pd.Timestamp.now().strftime('%Y%m%d_%H%M%S')
        filename_parts = ['analysis']
        if pid:
            filename_parts.append(f'pid{pid}')
        filename_parts.append(timestamp)
        
        if format_type.lower() == 'csv':
            # Convert analysis to CSV format
            analysis_data = []
            for key, value in analysis.items():
                if isinstance(value, dict):
                    for subkey, subvalue in value.items():
                        analysis_data.append({
                            'category': key,
                            'metric': subkey,
                            'value': str(subvalue)
                        })
                else:
                    analysis_data.append({
                        'category': 'general',
                        'metric': key,
                        'value': str(value)
                    })
            
            df = pd.DataFrame(analysis_data)
            output = StringIO()
            df.to_csv(output, index=False)
            output.seek(0)
            
            filename = '_'.join(filename_parts) + '.csv'
            response = make_response(output.getvalue())
            response.headers['Content-Type'] = 'text/csv'
            response.headers['Content-Disposition'] = f'attachment; filename={filename}'
            return response
        else:
            # JSON response
            filename = '_'.join(filename_parts) + '.json'
            response = make_response(json.dumps(analysis, indent=2))
            response.headers['Content-Type'] = 'application/json'
            response.headers['Content-Disposition'] = f'attachment; filename={filename}'
            return response

    except Exception as e:
        print(f"Error in export analysis: {e}")
        return jsonify({'error': 'Internal server error'}), 500

def preload_trace_file():
    """Pre-load the default trace file if it exists"""
    try:
        default_trace_path = app.config_class.PROJECT_ROOT / 'data' / 'traces' / 'trace.trace'
        if default_trace_path.exists():
            print(f"Found default trace file: {default_trace_path}")
            # Check if processed file already exists to avoid reprocessing
            if not Path(app.config_class.PROCESSED_EVENTS_JSON).exists():
                print("Processing default trace file...")
                result = trace_processor.process_trace_file(str(default_trace_path))
                if result['success']:
                    print(f"Default trace processed successfully: {result['events_count']} events")
                else:
                    print(f"Failed to process default trace: {result.get('error', 'Unknown error')}")
            else:
                print("Processed events file already exists, skipping processing")
        else:
            print(f"No default trace file found at: {default_trace_path}")
    except Exception as e:
        print(f"Error preloading trace file: {e}")

if __name__ == '__main__':
    # Validate configuration on startup
    config_errors = app.config_class.validate_paths()
    if config_errors:
        print("Configuration warnings:")
        for error in config_errors:
            print(f"  - {error}")

    # Pre-load the default trace file
    preload_trace_file()

    app.run(
        host=app.config_class.HOST,
        port=app.config_class.PORT,
        debug=app.config_class.DEBUG
    )
