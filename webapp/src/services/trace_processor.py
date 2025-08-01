import os
import sys
import json
import csv
import re
import logging
import tempfile
import shutil
import socket
import struct
from pathlib import Path


class TraceProcessor:
    """Process .trace files and convert them to JSON for visualization"""

    def __init__(self, config_class):
        self.config = config_class
        self.logger = self._setup_logger()

    def _setup_logger(self):
        """Setup logging for trace processing"""
        logger = logging.getLogger("TraceProcessor")
        logger.setLevel(logging.INFO)

        # Create handler if not exists
        if not logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
            handler.setFormatter(formatter)
            logger.addHandler(handler)

        return logger

    def _convert_raw_ip_to_string(self, raw_ip):
        """Convert raw 32-bit IP value to readable IP address string"""
        try:
            # Handle special cases
            if raw_ip == 0:
                return "0.0.0.0"
            
            # Convert from little-endian to IP string
            ip_bytes = struct.pack('<I', raw_ip)
            ip_string = socket.inet_ntoa(ip_bytes)
            
            # Log for debugging
            self.logger.debug(f"Converted IP: {raw_ip} -> {ip_string}")
            return ip_string
        except (struct.error, OSError) as e:
            self.logger.warning(f"Failed to convert IP {raw_ip}: {e}")
            return str(raw_ip)  # Return raw value if conversion fails

    def _format_size_to_kb(self, size_value):
        """Convert size to KB format for better readability"""
        try:
            if isinstance(size_value, str) and size_value.startswith("0x"):
                size_bytes = int(size_value, 16)
            else:
                size_bytes = int(size_value)
            
            if size_bytes >= 1024:
                return f"{size_bytes / 1024:.2f}KB"
            else:
                return f"{size_bytes}B"
        except (ValueError, TypeError):
            return str(size_value)

    def process_trace_file(self, trace_file_path, progress_callback=None, target_app=None):
        """
        Process a .trace file and generate JSON output

        Args:
            trace_file_path: Path to the .trace file
            progress_callback: Optional callback function for progress updates
            target_app: Optional target app name to avoid auto-detection from filename

        Returns:
            dict: Result containing success status, message, and file paths
        """
        try:
            if progress_callback:
                progress_callback(10, "Validating trace file...")

            # Validate input file
            if not Path(trace_file_path).exists():
                return {
                    'success': False,
                    'error': 'Trace file does not exist'
                }

            if not trace_file_path.endswith('.trace'):
                return {
                    'success': False,
                    'error': 'File must have .trace extension'
                }

            if progress_callback:
                progress_callback(20, "Parsing trace events...")

            # Parse the trace file with smart size limiting for performance
            file_size = Path(trace_file_path).stat().st_size / (1024 * 1024)  # Size in MB
            
            # Process all events without any limits
            max_events = None
            
            raw_events = self._parse_ftrace_log(trace_file_path, max_events=max_events, progress_callback=progress_callback)
            self.logger.info(f"Parsed {len(raw_events)} raw events from {file_size:.1f}MB file")
            with open('raw_events.json', 'w', encoding='utf-8') as f:
                json.dump(raw_events, f, indent=4, ensure_ascii=False)
            if not raw_events:
                return {
                    'success': False,
                    'error': 'No events found in trace file'
                }

            if progress_callback:
                progress_callback(40, "Finding target process...")

            # Find target process
            if target_app:
                # Skip process finding when target app is specified - will be handled later
                t_pid = None
                self.logger.info(f"Skipping auto process detection - target app specified: {target_app}")
            else:
                t_pid = self._find_process(raw_events, trace_file_path)
                if t_pid == 0:
                    return {
                        'success': False,
                        'error': 'Could not identify target process from trace file'
                    }

            self.logger.info(f"Target PID: {t_pid}")

            if progress_callback:
                progress_callback(60, "Processing events...")

            # Remove excess API logging
            events_pruned = self._remove_apis(raw_events)
            self.logger.info(f"After pruning: {len(events_pruned)} events")

            if progress_callback:
                progress_callback(80, "Generating output files...")

            # Process events into the format expected by the web app
            processed_events = self._process_events_for_webapp(events_pruned, t_pid)

            # Ensure output directory exists
            output_dir = Path(self.config.EXPORTS_DIR)
            output_dir.mkdir(parents=True, exist_ok=True)

            # Generate output file paths
            csv_output_path = output_dir / 'processed_events.csv'
            json_output_path = output_dir / 'processed_events.json'

            # Export the processed events
            self._export_events(processed_events, str(csv_output_path), str(json_output_path))

            if progress_callback:
                progress_callback(100, "Processing complete!")

            return {
                'success': True,
                'message': f'Successfully processed {len(processed_events)} events',
                'csv_file': str(csv_output_path),
                'json_file': str(json_output_path),
                'events_count': len(processed_events),
                'target_pid': t_pid
            }

        except Exception as e:
            self.logger.error(f"Error processing trace file: {str(e)}")
            return {
                'success': False,
                'error': f'Processing failed: {str(e)}'
            }

    def _find_process(self, events, filepath):
        """Find the target process from the trace events using shortened name matching"""
        from collections import Counter

        # Determine application name from trace filename
        basename = os.path.splitext(os.path.basename(filepath))[0]
        app_name = basename.split('.')[0]  # part before first dot
        self.logger.info(f"Looking for process matching '{app_name}'")

        # Try exact match first (case-insensitive)
        t_pid = None
        for e in events:
            if e.get('process', '').lower() == app_name.lower():
                t_pid = e['tgid']
                self.logger.info(f"Exact match: process '{e['process']}' with PID {t_pid}")
                break

        # Try shortened name matching if no exact match
        if t_pid is None:
            self.logger.info(f"No exact match found, trying shortened name matching...")
            shortened_name = self._create_shortened_name(app_name)
            self.logger.info(f"Shortened name: '{shortened_name}'")
            
            for e in events:
                event_process = e.get('process', '')
                if shortened_name in event_process:
                    t_pid = e['tgid']
                    self.logger.info(f"Shortened match: found '{shortened_name}' in process '{event_process}' with PID {t_pid}")
                    break

        # Fallback to most frequent process if still no match
        if t_pid is None:
            procs = Counter(e.get('process', '') for e in events)
            if procs:
                proc, count = procs.most_common(1)[0]
                t_pid = next((e['tgid'] for e in events if e.get('process', '') == proc), 0)
                self.logger.info(f"Fallback: selected most frequent process '{proc}' ({count} events) with PID {t_pid}")
        
        return t_pid or 0
    
    def _create_shortened_name(self, full_name):
        """Create shortened process name for matching"""
        if '.' in full_name:
            parts = full_name.split('.')
            if len(parts) >= 3:
                # For com.google.android.apps.nbu.files -> .apps.nbu.files
                if parts[0] in ['com', 'org'] and parts[1] in ['google', 'android', 'samsung', 'nothing']:
                    if len(parts) > 4:
                        return '.' + '.'.join(parts[3:])
                    else:
                        # For com.google.android.contacts -> .contacts
                        return '.' + parts[-1]
                elif parts[0] in ['com', 'org']:
                    # For com.spotify.music -> .spotify.music
                    return '.' + '.'.join(parts[1:])
        return full_name

    def _remove_apis(self, events):
        """Remove excess API logging"""
        cleaned_events = []
        for i, e in enumerate(events):
            e['raw'] = i
            # Remove API logging and monkey process operations
            try:
                if not (e['event'] == 'write_probe' and
                       e.get('details', {}).get('pathname') == 'null' and
                       e.get('details', {}).get('count', 0) > 999999) and \
                   'monkey' not in e.get('process', ''):
                    cleaned_events.append(e.copy())
            except Exception as ex:
                self.logger.warning(f"Error processing event {i}: {ex}")

        return cleaned_events

    def _process_events_for_webapp(self, events, t_pid):
        """
        Process events into the format expected by the web application
        This is a simplified version that prepares events for visualization
        """
        processed_events = []

        for event in events:
            # Only include events that are relevant for visualization
            if self._is_visualization_relevant(event):
                # Add event categorization for better visualization
                event['category'] = self._categorize_event(event)
                processed_events.append(event)

        return processed_events
    
    def _categorize_event(self, event):
        """Categorize event for visualization purposes using simplified categories"""
        event_name = event.get('event', '')
        
        # Read operations (traditional filesystem reads + hardware reads)
        if event_name in ['read_probe'] or any(keyword in event_name for keyword in ['read', 'recv']):
            return 'read'
        
        # Write operations (traditional filesystem writes + hardware writes) 
        elif (event_name in ['write_probe', 'tracing_mark_write'] or 
              any(keyword in event_name for keyword in ['write', 'send', 'enable', 'prepare', 'vote'])):
            return 'write'
        
        # IOCTL and hardware control operations
        elif (event_name in ['ioctl_probe', 'android_vh_blk_account_io_done_handler', 'ioc_timer_fn'] or
              any(keyword in event_name for keyword in ['ioctl', 'clk', 'runtime', 'suspend', 'resume', 'hw_'])):
            return 'ioctl'
        
        # Binder and IPC operations  
        elif (event_name in ['binder_transaction', 'binder_transaction_received'] or
              any(keyword in event_name for keyword in ['binder', 'interrupt'])):
            return 'binder'
        
        # Network operations (including audio/communication subsystems)
        elif (event_name in ['tcp_sendmsg', 'tcp_recvmsg', 'udp_sendmsg', 'udp_recvmsg',
                           'unix_stream_sendmsg', 'unix_stream_recvmsg', 'unix_dgram_sendmsg', 'unix_dgram_recvmsg',
                           '__sys_socket', '__sys_connect', '__sys_bind', 'sock_sendmsg', 'inet_sock_set_state'] or
              any(keyword in event_name for keyword in ['audio', 'bolero', 'swrm', 'digital_cdc', 'lpass_hw', 'sock', 'inet'])):
            return 'network'
        
        else:
            return 'other'

    def _is_visualization_relevant(self, event):
        """Check if an event is relevant for visualization"""
        event_name = event.get('event', '')
        
        # Traditional system call events
        traditional_events = [
            # File system operations
            'read_probe', 'write_probe', 'ioctl_probe',
            # IPC operations
            'inet_sock_set_state', 'binder_transaction', 'binder_transaction_received',
            'unix_stream_sendmsg', 'unix_stream_recvmsg',
            'unix_dgram_sendmsg', 'unix_dgram_recvmsg',
            # Network operations
            'tcp_sendmsg', 'tcp_recvmsg', 'udp_sendmsg', 'udp_recvmsg',
            '__sys_socket', '__sys_connect', '__sys_bind', 'sock_sendmsg',
            # Security operations
            'ptrace_attach', '__arm64_sys_setuid', '__arm64_sys_setresuid', 
            '__arm64_sys_setresgid', '__arm64_sys_capset', '__arm64_sys_mprotect',
            # Process operations
            '__arm64_sys_execve', 'load_elf_binary', 'sched_process_fork', 'sched_process_exec',
            # Memory operations
            'mmap_probe',
            # Bluetooth operations
            'hci_sock_sendmsg', 'sco_sock_sendmsg', 'l2cap_sock_sendmsg',
            # Device-specific operations
            'aoc_service_write_message'
        ]
        
        # Hardware and low-level events (new support)
        hardware_events = [
            # Block I/O
            'android_vh_blk_account_io_done_handler', 'ioc_timer_fn',
            # System tracing
            'tracing_mark_write',
            # Audio subsystem
            'audio_ext_clk_prepare', 'audio_ext_clk_unprepare',
            'bolero_runtime_resume', 'bolero_runtime_suspend', 'bolero_clk_rsc_request_clock',
            'digital_cdc_rsc_mgr_hw_vote_enable', 'digital_cdc_rsc_mgr_hw_vote_disable',
            'rx_macro_mclk_enable', 'rx_swrm_clock',
            'swrm_mstr_interrupt', 'swrm_request_hw_vote', 'swrm_runtime_resume', 'swrm_runtime_suspend', 'swrm_clk_request',
            'lpass_hw_vote_prepare', 'lpass_hw_vote_unprepare',
            # Power management
            'pm_runtime', 'lpi_pinctrl_runtime_resume', 'lpi_pinctrl_runtime_suspend',
            # Clock management
            'clk_cnt', 'hw_clk_en'
        ]
        
        # Check both traditional and hardware events
        if event_name in traditional_events or event_name in hardware_events:
            return True
            
        # Also check for generic patterns that might be relevant
        relevant_patterns = ['handle', 'enable', 'status']
        for pattern in relevant_patterns:
            if pattern in event_name and len(event_name) < 50:  # Avoid very long event names
                return True
        
        return False

    def _parse_ftrace_log(self, filepath, max_events=None, progress_callback=None):
        """
        Parse ftrace log file and extract events with optional size limiting
        Parse ftrace log and extract events with detailed parsing
        """
        # Regular expression to match Ftrace event log lines with TGID inside parentheses
        trace_pattern = re.compile(r'\s*(?P<process>((\S|\s)+|\<\.\.\.\>))-(?P<tid>\d+)\s+\(\s*(?P<tgid>(\d+|-------))\)\s+\[(?P<cpu>\d+)\]\s+(?P<flags>[\S]+)\s+(?P<timestamp>\d+\.\d+):\s+(?P<event>\S+):\s+(?P<details>.*)')

        # Regular expression to match key-value pairs inside the 'details' section
        detail_pattern = re.compile(r'(\S+)=(".*?"|\S+)')
        parsed_events = []  # List to store parsed events (sequence of events)

        with open(filepath, 'r') as f:
            line_count = 0
            for line in f:
                # Skip very long lines to avoid processing issues
                if len(line) > 1000:
                    continue
                
                # Progress reporting for large files
                line_count += 1
                if line_count % 50000 == 0:
                    self.logger.info(f"Processed {line_count} lines, parsed {len(parsed_events)} events")
                    if progress_callback:
                        progress_callback(30, f"Parsing... {len(parsed_events)} events processed")
                
                # Match the main trace line format
                match = trace_pattern.match(line)
                if match:
                    # Extract main fields from the log line
                    process = match.group('process')
                    tid = int(match.group('tid'))      # Thread ID (TID) -> PID as integer
                    try:
                        tgid = int(match.group('tgid'))    # Thread Group ID (TGID) as integer
                    except ValueError:
                        tgid = -1 # When tgid is not known by the system use -1
                    cpu = int(match.group('cpu'))      # CPU as integer
                    flags = match.group('flags')
                    timestamp = float(match.group('timestamp'))  # Timestamp as float
                    event = match.group('event')
                    details = match.group('details')

                    # Parse the details section (key-value pairs)
                    parsed_details = {}
                    for detail_match in detail_pattern.finditer(details):
                        key, value = detail_match.groups()
                        if value.startswith("0x"):  # Handle hexadecimal values
                            parsed_details[key] = int(value, 16)  # Convert to integer
                        else:
                            try:
                                parsed_details[key] = int(value)  # Convert to integer if possible
                            except ValueError:
                                parsed_details[key] = value.strip('"')  # Keep as string if not int
                    
                    # Convert IP addresses and sizes for network events
                    if event in ['tcp_sendmsg', 'tcp_recvmsg', 'tcp_connect', 'udp_sendmsg', 'udp_recvmsg']:
                        # Debug logging
                        self.logger.info(f"Processing {event} with details: {parsed_details}")
                        
                        # Convert IP addresses to readable format
                        if 'src_ip' in parsed_details and isinstance(parsed_details['src_ip'], int):
                            if parsed_details['src_ip'] != 0:  # Only convert non-zero IPs
                                parsed_details['src_ip_readable'] = self._convert_raw_ip_to_string(parsed_details['src_ip'])
                            else:
                                parsed_details['src_ip_readable'] = "0.0.0.0"
                                
                        if 'dst_ip' in parsed_details and isinstance(parsed_details['dst_ip'], int):
                            if parsed_details['dst_ip'] != 0:  # Only convert non-zero IPs
                                parsed_details['dst_ip_readable'] = self._convert_raw_ip_to_string(parsed_details['dst_ip'])
                            else:
                                parsed_details['dst_ip_readable'] = "0.0.0.0"
                        
                        # Convert sizes to KB format
                        for size_key in ['size', 'len']:
                            if size_key in parsed_details:
                                parsed_details[f'{size_key}_formatted'] = self._format_size_to_kb(parsed_details[size_key])

                    # Create a dictionary to store the parsed event
                    parsed_event = {
                        "process": process,
                        "tid": tid,         # TID (PID) as integer
                        "tgid": tgid,       # TGID as integer
                        "cpu": cpu,         # CPU as integer
                        "flags": flags,     # Flags as string
                        "timestamp": timestamp,  # Timestamp as float
                        "event": event,     # Event name
                        "details": parsed_details  # Parsed key-value pairs
                    }

                    # Append the event to the list
                    parsed_events.append(parsed_event)
                    
                    # Memory management for very large files
                    if len(parsed_events) % 10000 == 0 and len(parsed_events) > 0:
                        # Force garbage collection every 10k events to prevent memory bloat
                        import gc
                        gc.collect()
                else:
                    # Skip printing invalid lines to reduce noise
                    pass

        return parsed_events

    def _export_events(self, events, csv_path, json_path):
        """
        Export events to CSV and JSON files
        Export events to CSV format with proper formatting
        """
        # Export events to JSON
        with open(json_path, 'w', encoding='utf-8') as json_file:
            json.dump(events, json_file, indent=4, ensure_ascii=False)

        # Flatten events for CSV output
        flat_events = [self._flatten_event(event) for event in events]

        # Compute header columns as the union of all keys from all flattened events
        if flat_events:
            headers = sorted(set().union(*(event.keys() for event in flat_events)))
        else:
            headers = []

        # Export events to CSV
        with open(csv_path, 'w', newline='', encoding='utf-8') as csv_file:
            writer = csv.DictWriter(csv_file, fieldnames=headers, extrasaction='ignore')
            writer.writeheader()
            writer.writerows(flat_events)

        self.logger.info(f"Exported {len(events)} events to {json_path} and {csv_path}")

    def _flatten_event(self, event):
        """Flatten event structure for CSV export"""
        flat = {}
        for key, value in event.items():
            if key == "details" and isinstance(value, dict):
                for subkey, subvalue in value.items():
                    flat[f"detail_{subkey}"] = subvalue
            else:
                flat[key] = value
        return flat