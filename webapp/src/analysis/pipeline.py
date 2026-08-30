"""
End-to-end analysis pipeline.

``run_analysis`` parses a trace, slices it with the advanced windowed
algorithm, and returns the FROZEN analysis result contract (see
DESIGN.md; the frontend is built against this exact shape):

{
    "meta":     {"trace_file", "target": {"mode", "package", "name", "pids"},
                 "generated_at", "window_size", "overlap", "duration_s",
                 "total_events", "sliced_events", "windows"},
    "summary":  {"event_categories", "device_categories", "top_processes"},
    "timeline": {"categories", "series", "sensitive", "network"},
    "network":  {"metrics", "peers", "connections"},
    "sensitive": [{"category", "window", "process", "tgid", "identifier",
                   "pathname", "timestamp"}],
    "insights": [{"level": "info"|"warning", "text"}]
}

The result is fully JSON-serializable (one pass through
``make_json_serializable``) and persisted atomically to
``Config.ANALYSIS_JSON`` (data/Exports/analysis.json) unless another
output path is given.  The deduplicated sliced events are additionally
persisted to ``Config.SLICED_EVENTS_JSON`` for the export endpoints.
"""

from __future__ import annotations

import json
import logging
import os
import tempfile
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional, Union

from ..config import Config
from ..services.utils import make_json_serializable
from .devices import build_device_summary, invert_category_map, load_category_map
from .insights import generate_insights
from .network import NetworkAccumulator
from .parser import parse_ftrace_log
from .slicer import categorize_event, find_process, remove_apis
from .windows import run_windowed_analysis

logger = logging.getLogger(__name__)

#: Maximum number of processes reported in summary.top_processes
TOP_PROCESSES = 8


def _dedupe_by_raw(events: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Deduplicate sliced events collected from overlapping windows."""
    seen: set = set()
    unique = []
    for event in events:
        raw = event.get('raw')
        if raw in seen:
            continue
        seen.add(raw)
        unique.append(event)
    return unique


def _load_cat2devs(cat2devs_path: Optional[Union[str, Path]]) -> dict[str, list[str]]:
    path = Path(cat2devs_path) if cat2devs_path else Path(Config.MAPPINGS_DIR) / 'cat2devs.txt'
    if not path.exists():
        logger.warning("Device category mapping not found at %s; categories disabled", path)
        return {}
    try:
        cat2devs = load_category_map(path)
        logger.info("Loaded device category mapping with %d categories from %s", len(cat2devs), path)
        return cat2devs
    except (json.JSONDecodeError, OSError):
        logger.exception("Failed to load device category mapping from %s", path)
        return {}


def _write_atomic(path: Path, payload: Any) -> None:
    """Persist the payload as JSON atomically (write to temp file + rename)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(dir=path.parent, prefix=path.name, suffix='.tmp')
    try:
        with os.fdopen(fd, 'w') as f:
            json.dump(payload, f, indent=2)
        os.replace(tmp_name, path)
    except BaseException:
        try:
            os.unlink(tmp_name)
        except OSError:
            pass
        raise


def _resolve_target(target_app: Optional[Union[str, dict]],
                    target_name: Optional[str]) -> tuple[Optional[str], Optional[str], list[str]]:
    """
    Normalize target metadata.

    ``target_app`` may be a package name string or a dict with keys
    "package", "name" and optionally "process_names".  Returns
    (package, display name, candidate process names for lookup).
    """
    if isinstance(target_app, dict):
        package = target_app.get('package')
        name = target_app.get('name') or target_name
        process_names = list(target_app.get('process_names') or [])
    else:
        package = target_app
        name = target_name
        process_names = []
    if package and package not in process_names:
        process_names.append(package)
    return package, name, process_names


def _build_summary(slice_events_list: list[dict[str, Any]],
                   device_summary: dict[str, Any]) -> dict[str, Any]:
    """Build the ``summary`` section of the contract from the sliced events."""
    event_categories = Counter(categorize_event(e) for e in slice_events_list)

    process_counts: Counter = Counter()
    for e in slice_events_list:
        process_counts[(e['process'], e['tgid'])] += 1
    top_processes = [
        {'process': process, 'tgid': tgid, 'events': count}
        for (process, tgid), count in sorted(
            process_counts.items(), key=lambda item: (-item[1], item[0][0])
        )[:TOP_PROCESSES]
    ]

    return {
        'event_categories': dict(event_categories),
        'device_categories': dict(device_summary.get('categories', {})),
        'top_processes': top_processes,
    }


def _build_timeline(windowed: dict[str, Any], cat2devs: dict[str, list[str]]) -> dict[str, Any]:
    """Build the ``timeline`` section from per-window traces."""
    dev2cat = invert_category_map(cat2devs)
    window_count = windowed['window_count']

    # Per-window counts per device category (dense series, 0-filled)
    category_counts: dict[str, list[int]] = {}
    for window_idx, kdev2count in enumerate(windowed['kdevs_trace']):
        for kdev, count in kdev2count.items():
            category = dev2cat.get(kdev)
            if not category:
                continue
            series = category_counts.setdefault(category, [0] * window_count)
            series[window_idx] += count

    categories = sorted(category_counts)
    series = [
        {
            'category': category,
            'points': [[window_idx, count]
                       for window_idx, count in enumerate(category_counts[category])],
        }
        for category in categories
    ]

    sensitive = [
        {
            'window': hit['window'],
            'category': hit['category'],
            'identifier': hit['identifier'],
            'pathname': hit['pathname'],
        }
        for hit in windowed['sensitive_hits']
    ]

    return {
        'categories': categories,
        'series': series,
        'sensitive': sensitive,
        'network': windowed['network_trace'],
    }


def run_analysis(
    trace_file: Union[str, Path],
    target_app: Optional[Union[str, dict]] = None,
    target_pid: Optional[int] = None,
    target_name: Optional[str] = None,
    window_size: int = 500,
    overlap: int = 100,
    asynchronous: bool = True,
    cat2devs_path: Optional[Union[str, Path]] = None,
    output_path: Optional[Union[str, Path]] = None,
    events_output_path: Optional[Union[str, Path]] = None,
) -> dict[str, Any]:
    """
    Run the complete analysis pipeline on an ftrace log.

    Args:
        trace_file: Path to the .trace file.
        target_app: Target application: either the package name (str) or a
            dict {"package": str, "name": str, "process_names": [str]}.
            Used to find the tgid when target_pid is not given, and to fill
            meta.target.
        target_pid: Target process tgid; when given, meta.target.mode is
            "pid" and no process-name lookup is performed.
        target_name: Optional human-readable app name (used when
            target_app is a plain string).
        window_size: Events per analysis window.
        overlap: Events shared between consecutive windows.
        asynchronous: Whether to allow asynchronous taint propagation.
        cat2devs_path: Optional override for the device category mapping
            (defaults to Config.MAPPINGS_DIR / 'cat2devs.txt').
        output_path: Optional override for the persisted contract JSON
            (defaults to Config.ANALYSIS_JSON).
        events_output_path: Optional override for the persisted sliced
            events JSON (defaults to Config.SLICED_EVENTS_JSON).

    Returns:
        The frozen analysis result contract dict (JSON-serializable).

    Raises:
        ValueError: If neither target_app nor target_pid is provided, if
            no events could be parsed from the trace file, or if the
            target process/PID cannot be found in the trace.
    """
    package, name, process_names = _resolve_target(target_app, target_name)
    if target_pid is None and not process_names:
        raise ValueError("Either target_app or target_pid must be provided.")

    raw_events = parse_ftrace_log(trace_file)
    logger.info("Parsed %d raw events", len(raw_events))
    if not raw_events:
        raise ValueError('No events could be parsed from the trace file — is it a valid ftrace log?')

    if target_pid is not None:
        mode = 'pid'
        t_pid = target_pid
        if not any(e['tgid'] == t_pid for e in raw_events):
            raise ValueError(f'PID {target_pid} not found in trace')
    else:
        mode = 'app'
        t_pid = 0
        for candidate in process_names:
            t_pid = find_process(raw_events, candidate)
            if t_pid:
                break
    if not t_pid:
        raise ValueError(f"Target process '{package or target_pid}' not found in trace {trace_file}")
    logger.info("Target PID: %d (mode=%s)", t_pid, mode)

    events_pruned = remove_apis(raw_events)
    logger.info("After removing API logging: %d events", len(events_pruned))

    cat2devs = _load_cat2devs(cat2devs_path)

    windowed = run_windowed_analysis(
        events_pruned,
        t_pid,
        window_size=window_size,
        overlap=overlap,
        asynchronous=asynchronous,
        cat2devs=cat2devs,
    )

    slice_events_list = _dedupe_by_raw(windowed['all_relevant_events'])
    device_summary = build_device_summary(slice_events_list, cat2devs)

    # Feed the network accumulator ONCE with the deduplicated slice so
    # overlapping windows cannot double-count bytes or connections.
    accumulator = NetworkAccumulator()
    accumulator.update(slice_events_list)
    network = accumulator.summary()

    meta = {
        'trace_file': str(trace_file),
        'target': {
            'mode': mode,
            'package': package,
            'name': name,
            'pids': [t_pid],
        },
        'generated_at': datetime.now(timezone.utc).isoformat(),
        'window_size': window_size,
        'overlap': overlap,
        'duration_s': float(windowed['events_duration']),
        'total_events': len(raw_events),
        'sliced_events': len(slice_events_list),
        'windows': windowed['window_count'],
    }

    result = {
        'meta': meta,
        'summary': _build_summary(slice_events_list, device_summary),
        'timeline': _build_timeline(windowed, cat2devs),
        'network': network,
        'sensitive': windowed['sensitive_hits'],
        'insights': generate_insights(meta, device_summary, network),
    }

    serializable = make_json_serializable(result)

    destination = Path(output_path) if output_path else Path(Config.ANALYSIS_JSON)
    _write_atomic(destination, serializable)
    logger.info("Analysis result written to %s", destination)

    events_destination = (Path(events_output_path) if events_output_path
                          else Path(Config.SLICED_EVENTS_JSON))
    _write_atomic(events_destination, make_json_serializable(slice_events_list))
    logger.info("Sliced events written to %s", events_destination)

    return serializable
