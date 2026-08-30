"""
Unified trace analysis package for SliceDroid.

Modules:
- parser:   ftrace log parsing (canonical, normalizes k__dev -> k_dev)
- slicer:   advanced bidirectional event slicing (IPC taint tracking)
- devices:  device identification, categorization and sensitive-data detection
- network:  IP/port helpers, private-IP filtering and network metrics
- windows:  windowed slicing driver with metric accumulation
- insights: plain-text insight generation
- pipeline: end-to-end orchestration producing the analysis JSON contract
"""

from .parser import parse_ftrace_log, calculate_major_minor
from .slicer import (
    slice_events,
    find_process,
    remove_apis,
    get_tcp_events,
    is_filtered,
    categorize_event,
)
from .network import (
    int_to_ip,
    is_private_ip,
    has_private_ip,
    filter_private_ip_events,
    convert_port_endianness,
    NetworkAccumulator,
)
from .devices import (
    get_device_identifier,
    load_category_map,
    invert_category_map,
    is_legitimate_sensitive_access,
    sensitive_category,
    detect_sensitive_events,
    build_device_summary,
)
from .windows import run_windowed_analysis
from .insights import generate_insights
from .pipeline import run_analysis

__all__ = [
    'parse_ftrace_log',
    'calculate_major_minor',
    'slice_events',
    'find_process',
    'remove_apis',
    'get_tcp_events',
    'is_filtered',
    'categorize_event',
    'int_to_ip',
    'is_private_ip',
    'has_private_ip',
    'filter_private_ip_events',
    'convert_port_endianness',
    'NetworkAccumulator',
    'get_device_identifier',
    'load_category_map',
    'invert_category_map',
    'is_legitimate_sensitive_access',
    'sensitive_category',
    'detect_sensitive_events',
    'build_device_summary',
    'run_windowed_analysis',
    'generate_insights',
    'run_analysis',
]
