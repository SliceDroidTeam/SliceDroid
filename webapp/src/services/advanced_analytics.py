import os
import sys
import json
import logging
import numpy as np
import matplotlib.pyplot as plt
import matplotlib
matplotlib.use('Agg')  # Use non-interactive backend for web
import base64
from io import BytesIO
from pathlib import Path
from collections import Counter, defaultdict

# Add the app directory to Python path
APP_DIR = Path(__file__).parent.parent / 'app'
sys.path.insert(0, str(APP_DIR))

try:
    import myutils
except ImportError:
    # If myutils is not available, create minimal functionality
    class MyUtils:
        @staticmethod
        def load_file(filename):
            """Load a file containing device mappings"""
            result = {}
            try:
                with open(filename, 'r') as f:
                    # Try to load as JSON first
                    try:
                        f.seek(0)
                        content = f.read()
                        result = json.loads(content)
                        return result
                    except json.JSONDecodeError:
                        # Fall back to text format parsing
                        f.seek(0)
                        lines = f.readlines()
                        current_category = None
                        for line in lines:
                            line = line.strip()
                            if line and not line.startswith('#'):
                                if ':' in line and not line.startswith('\t'):
                                    current_category = line.replace(':', '').strip()
                                    result[current_category] = []
                                elif line.startswith('\t') and current_category:
                                    device = line.strip()
                                    if device.isdigit():
                                        result[current_category].append(int(device))
            except:
                pass
            return result
    
    myutils = MyUtils()

class AdvancedAnalytics:
    """Advanced analytics for trace data with high-level insights"""
    
    def __init__(self, config_class):
        self.config = config_class
        self.logger = self._setup_logger()
        
        # Import comprehensive analyzer for behavior timeline
        try:
            from .comprehensive_analyzer import ComprehensiveAnalyzer
            self.comprehensive_analyzer = ComprehensiveAnalyzer(config_class)
        except ImportError:
            self.logger.warning("ComprehensiveAnalyzer not available")
            self.comprehensive_analyzer = None
        
    def _setup_logger(self):
        """Setup logging"""
        logger = logging.getLogger("AdvancedAnalytics")
        logger.setLevel(logging.INFO)
        
        if not logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
            handler.setFormatter(formatter)
            logger.addHandler(handler)
        
        return logger
    
    def analyze_trace_data(self, events, target_pid=None, window_size=1000, overlap=200):
        """
        Perform comprehensive analysis of trace data
        
        Args:
            events: List of parsed events
            target_pid: Target process ID for analysis
            window_size: Size of analysis windows for behavior timeline
            overlap: Overlap between analysis windows
            
        Returns:
            dict: Comprehensive analysis results
        """
        try:
            if not events:
                return {'error': 'No events to analyze'}
            
            # If no target PID provided, find it
            if target_pid is None:
                target_pid = self._find_target_pid(events)
            
            # Perform different types of analysis
            time_range = self._analyze_time_range(events)
            process_analysis = self._analyze_processes(events)
            device_analysis = self._analyze_devices(events)
            category_analysis = self._analyze_categories(events)
            network_analysis = self._analyze_network_events(events)
            sensitive_data_analysis = self._analyze_sensitive_data(events)
            temporal_patterns = self._analyze_temporal_patterns(events, target_pid)
            charts = self._generate_charts(events, target_pid, window_size, overlap)
            
            # Add comprehensive analysis for behavior timeline
            comprehensive_analytics = None
            if self.comprehensive_analyzer and target_pid:
                try:
                    comprehensive_analytics = self.comprehensive_analyzer.slice_file_analysis(
                        events, target_pid, window_size=window_size, overlap=overlap
                    )
                except Exception as e:
                    self.logger.warning(f"Comprehensive analysis failed: {str(e)}")
            
            analysis = {
                'target_pid': target_pid,
                'total_events': len(events),
                'time_range': time_range,
                'process_analysis': process_analysis,
                'device_analysis': device_analysis,
                'category_analysis': category_analysis,
                'network_analysis': network_analysis,
                'sensitive_data_analysis': sensitive_data_analysis,
                'temporal_patterns': temporal_patterns,
                'charts': charts,
                'comprehensive_analytics': comprehensive_analytics,
                'detailed_insights': self._generate_detailed_insights({
                    'device_analysis': device_analysis,
                    'category_analysis': category_analysis,
                    'network_analysis': network_analysis,
                    'sensitive_data_analysis': sensitive_data_analysis
                })
            }
            
            return analysis
            
        except Exception as e:
            self.logger.error(f"Error in advanced analysis: {str(e)}")
            return {'error': f'Analysis failed: {str(e)}'}
    
    def _find_target_pid(self, events):
        """Find the most active PID in the trace"""
        pid_counts = Counter(e.get('tgid', 0) for e in events if e.get('tgid', 0) > 0)
        if pid_counts:
            return pid_counts.most_common(1)[0][0]
        return 0
    
    def _analyze_time_range(self, events):
        """Analyze the time range of events"""
        timestamps = [e.get('timestamp', 0) for e in events if e.get('timestamp')]
        if not timestamps:
            return {'error': 'No timestamps found'}
        
        return {
            'start_time': min(timestamps),
            'end_time': max(timestamps),
            'duration': max(timestamps) - min(timestamps),
            'total_events': len(timestamps)
        }
    
    def _analyze_processes(self, events):
        """Analyze process distribution"""
        process_counts = Counter(e.get('process', 'unknown') for e in events)
        pid_counts = Counter(e.get('tgid', 0) for e in events if e.get('tgid', 0) > 0)
        
        # Map PIDs to process names
        pid_to_process = {}
        for e in events:
            if e.get('tgid') and e.get('process'):
                pid_to_process[e['tgid']] = e['process']
        
        return {
            'process_distribution': dict(process_counts.most_common(10)),
            'pid_distribution': dict(pid_counts.most_common(10)),
            'pid_to_process_map': pid_to_process,
            'unique_processes': len(process_counts),
            'unique_pids': len(pid_counts)
        }
    
    def _analyze_devices(self, events):
        """Analyze device usage patterns"""
        device_counts = defaultdict(int)
        device_paths = defaultdict(set)
        device_categories = defaultdict(int)
        
        # Load device category mappings
        try:
            cat2devs_file = self.config.MAPPINGS_DIR / 'cat2devs.txt'
            if cat2devs_file.exists():
                cat2devs = myutils.load_file(str(cat2devs_file))
                dev2cat = {}
                for cat, devs in cat2devs.items():
                    for dev in devs:
                        dev2cat[dev] = cat
            else:
                dev2cat = {}
        except:
            dev2cat = {}
        
        for event in events:
            if 'details' in event:
                # Check for both k_dev and k__dev
                device = event['details'].get('k_dev') or event['details'].get('k__dev')
                if device and device != 0:
                    device_counts[device] += 1
                    
                    # Track paths
                    if 'pathname' in event['details'] and event['details']['pathname']:
                        device_paths[device].add(event['details']['pathname'])
                    
                    # Categorize device
                    if device in dev2cat:
                        device_categories[dev2cat[device]] += 1
        
        # Convert sets to lists for JSON serialization
        device_paths_dict = {k: list(v) for k, v in device_paths.items()}
        
        return {
            'device_usage': dict(sorted(device_counts.items(), key=lambda x: x[1], reverse=True)[:20]),
            'device_paths': device_paths_dict,
            'category_usage': dict(device_categories),
            'unique_devices': len(device_counts),
            'total_device_events': sum(device_counts.values())
        }
    
    def _analyze_categories(self, events):
        """Analyze event categories"""
        category_counts = defaultdict(int)
        event_type_counts = Counter()
        
        for event in events:
            event_type = event.get('event', 'unknown')
            event_type_counts[event_type] += 1
            
            # Categorize event
            category = self._categorize_event(event_type)
            category_counts[category] += 1
        
        return {
            'category_distribution': dict(category_counts),
            'event_type_distribution': dict(event_type_counts.most_common(15)),
            'read_write_ratio': self._calculate_read_write_ratio(category_counts),
            'io_patterns': self._analyze_io_patterns(events)
        }
    
    def _categorize_event(self, event_type):
        """Categorize an event type"""
        if not event_type:
            return 'other'
        
        event_type_lower = event_type.lower()
        
        if any(keyword in event_type_lower for keyword in ['read', 'pread']):
            return 'read'
        elif any(keyword in event_type_lower for keyword in ['write', 'pwrite']):
            return 'write'
        elif 'ioctl' in event_type_lower:
            return 'ioctl'
        elif 'binder' in event_type_lower:
            return 'binder'
        elif any(keyword in event_type_lower for keyword in ['unix', 'sock', 'inet', 'tcp', 'udp']):
            return 'network'
        else:
            return 'other'
    
    def _calculate_read_write_ratio(self, category_counts):
        """Calculate read/write ratio"""
        reads = category_counts.get('read', 0)
        writes = category_counts.get('write', 0)
        
        if writes == 0:
            return float('inf') if reads > 0 else 0
        
        return reads / writes
    
    def _analyze_io_patterns(self, events):
        """Analyze I/O patterns"""
        io_events = [e for e in events if e.get('event', '').endswith('_probe')]
        
        if not io_events:
            return {'error': 'No I/O events found'}
        
        # Analyze file types accessed
        file_types = defaultdict(int)
        path_analysis = defaultdict(int)
        
        for event in io_events:
            if 'details' in event and 'pathname' in event['details']:
                pathname = event['details']['pathname']
                if pathname:
                    # File extension analysis
                    if '.' in pathname:
                        ext = pathname.split('.')[-1].lower()
                        if len(ext) <= 4:  # Reasonable extension length
                            file_types[ext] += 1
                    
                    # Path pattern analysis
                    if pathname.startswith('/'):
                        parts = pathname.split('/')
                        if len(parts) > 1:
                            path_analysis[parts[1]] += 1  # Top-level directory
        
        return {
            'file_types': dict(sorted(file_types.items(), key=lambda x: x[1], reverse=True)[:10]),
            'path_patterns': dict(sorted(path_analysis.items(), key=lambda x: x[1], reverse=True)[:10]),
            'total_io_events': len(io_events)
        }
    
    def _analyze_network_events(self, events):
        """Analyze network-related events"""
        network_events = [e for e in events if 'inet' in e.get('event', '') or 'sock' in e.get('event', '')]
        
        if not network_events:
            return {'no_network_events': True}
        
        tcp_states = defaultdict(int)
        connections = defaultdict(int)
        
        for event in network_events:
            if event.get('event') == 'inet_sock_set_state' and 'details' in event:
                details = event['details']
                if 'newstate' in details:
                    tcp_states[details['newstate']] += 1
                
                if 'daddr' in details:
                    connections[details['daddr']] += 1
        
        return {
            'network_events_count': len(network_events),
            'tcp_state_transitions': dict(tcp_states),
            'connection_destinations': dict(sorted(connections.items(), key=lambda x: x[1], reverse=True)[:10])
        }
    
    def _analyze_sensitive_data(self, events):
        """Analyze potential sensitive data access using device ID + inode matching"""
        try:
            # Load sensitive resources mappings
            sensitive_resources_file = self.config.MAPPINGS_DIR / 'cat2stdevs_oneplus.json'
            if not sensitive_resources_file.exists():
                self.logger.warning(f"Sensitive resources file not found: {sensitive_resources_file}")
                return self._fallback_sensitive_analysis(events)
            
            with open(sensitive_resources_file, 'r') as f:
                sensitive_resources = json.load(f)
            
            sensitive_access = defaultdict(int)
            
            # Accurate detection using s_dev_inode and inode matching
            for event in events:
                if 'details' in event:
                    sensitive_type = self._check_sensitive_resource(event, sensitive_resources)
                    if sensitive_type:
                        sensitive_access[sensitive_type] += 1
            
            # Fallback to pathname patterns for additional categories
            self._add_pathname_based_detection(events, sensitive_access)
            
            return {
                'sensitive_data_access': dict(sensitive_access),
                'total_sensitive_events': sum(sensitive_access.values())
            }
            
        except Exception as e:
            self.logger.error(f"Error in sensitive data analysis: {str(e)}")
            return self._fallback_sensitive_analysis(events)
    
    def _check_sensitive_resource(self, event, sensitive_resources):
        """Check if event accesses a sensitive resource using device+inode matching"""
        try:
            for data_type, resource_info in sensitive_resources.items():
                # Check if event matches device and inode
                event_details = event.get('details', {})
                
                # Check s_dev_inode (32-bit device ID) and inode
                if (event_details.get('s_dev_inode') == resource_info.get('st_dev32') and 
                    event_details.get('inode') == resource_info.get('inode')):
                    return data_type
                
                # Alternative check using k_dev if s_dev_inode not available
                if (event_details.get('k_dev') == resource_info.get('st_dev32') and 
                    event_details.get('inode') == resource_info.get('inode')):
                    return data_type
                    
            return None
            
        except Exception as e:
            self.logger.warning(f"Error checking sensitive resource: {str(e)}")
            return None
    
    def _add_pathname_based_detection(self, events, sensitive_access):
        """Add pathname-based detection for categories not covered by device+inode"""
        pathname_patterns = {
            'location': ['gps', 'location', 'gnss'],
            'camera': ['camera', 'picture', 'photo'],
            'microphone': ['audio', 'mic', 'sound'],
            'bluetooth': ['bluetooth', 'bt'],
            'nfc': ['nfc']
        }
        
        for event in events:
            if 'details' in event and 'pathname' in event['details']:
                pathname = event['details']['pathname'].lower()
                for category, patterns in pathname_patterns.items():
                    if any(pattern in pathname for pattern in patterns):
                        sensitive_access[category] += 1
    
    def _fallback_sensitive_analysis(self, events):
        """Fallback analysis using only pathname patterns"""
        sensitive_patterns = {
            'contacts': ['contacts', 'people', 'addressbook'],
            'sms': ['sms', 'messages', 'mms'],
            'calendar': ['calendar', 'events'],
            'call_logs': ['calls', 'calllog'],
            'location': ['gps', 'location', 'gnss'],
            'camera': ['camera', 'picture', 'photo'],
            'microphone': ['audio', 'mic', 'sound']
        }
        
        sensitive_access = defaultdict(int)
        
        for event in events:
            if 'details' in event and 'pathname' in event['details']:
                pathname = event['details']['pathname'].lower()
                for category, patterns in sensitive_patterns.items():
                    if any(pattern in pathname for pattern in patterns):
                        sensitive_access[category] += 1
        
        return {
            'sensitive_data_access': dict(sensitive_access),
            'total_sensitive_events': sum(sensitive_access.values())
        }
    
    def _analyze_temporal_patterns(self, events, target_pid):
        """Analyze temporal patterns in the data"""
        if not events:
            return {'error': 'No events to analyze'}
        
        # Filter events for target PID
        target_events = [e for e in events if e.get('tgid') == target_pid]
        
        if not target_events:
            return {'error': f'No events found for PID {target_pid}'}
        
        # Time-based analysis
        timestamps = [e.get('timestamp', 0) for e in target_events if e.get('timestamp')]
        if not timestamps:
            return {'error': 'No timestamps found'}
        
        timestamps.sort()
        
        # Calculate activity bursts
        time_diffs = [timestamps[i+1] - timestamps[i] for i in range(len(timestamps)-1)]
        avg_interval = np.mean(time_diffs) if time_diffs else 0
        
        # Find activity bursts (intervals much smaller than average)
        burst_threshold = avg_interval * 0.1 if avg_interval > 0 else 0.001
        bursts = sum(1 for diff in time_diffs if diff < burst_threshold)
        
        return {
            'target_pid_events': len(target_events),
            'time_span': timestamps[-1] - timestamps[0] if len(timestamps) > 1 else 0,
            'average_event_interval': avg_interval,
            'activity_bursts': bursts,
            'events_per_second': len(target_events) / (timestamps[-1] - timestamps[0]) if len(timestamps) > 1 and timestamps[-1] != timestamps[0] else 0
        }
    
    def _generate_charts(self, events, target_pid, window_size=1000, overlap=200):
        """Generate base64-encoded charts similar to the notebook"""
        charts = {}
        
        try:
            # 1. High-Level Behavior Timeline (from notebook cell 11)
            charts['behavior_timeline'] = self._create_behavior_timeline_chart(events, target_pid, window_size, overlap)
            
            # 2. Category Distribution Chart
            charts['category_distribution'] = self._create_category_chart(events)
            
            # 3. Device Usage Chart
            charts['device_usage'] = self._create_device_chart(events)
            
            # 4. Network Activity Chart
            charts['network_activity'] = self._create_network_chart(events)
            
            # 5. Process Activity Chart
            charts['process_activity'] = self._create_process_chart(events)
            
        except Exception as e:
            self.logger.error(f"Error generating charts: {str(e)}")
            charts['error'] = str(e)
        
        return charts
    
    def _create_behavior_timeline_chart(self, events, target_pid, window_size=1000, overlap=200):
        """Create high-level behavior timeline chart based on notebook cell 11"""
        try:
            # Load device category mappings (use OnePlus specific file for more accuracy)
            try:
                # Try OnePlus specific mapping first
                cat2devs_file = self.config.MAPPINGS_DIR / 'cat2devs_oneplus.txt'
                if not cat2devs_file.exists():
                    # Fallback to generic mapping
                    cat2devs_file = self.config.MAPPINGS_DIR / 'cat2devs.txt'
                
                if cat2devs_file.exists():
                    cat2devs = myutils.load_file(str(cat2devs_file))
                    dev2cat = {}
                    for cat, devs in cat2devs.items():
                        for dev in devs:
                            dev2cat[dev] = cat
                else:
                    dev2cat = {}
            except:
                dev2cat = {}
            
            # Load sensitive resources mappings
            try:
                sensitive_resources_file = self.config.MAPPINGS_DIR / 'cat2stdevs_oneplus.json'
                if sensitive_resources_file.exists():
                    with open(sensitive_resources_file, 'r') as f:
                        sensitive_resources = json.load(f)
                else:
                    sensitive_resources = {}
            except:
                sensitive_resources = {}
            
            # Use provided window parameters
            step = window_size - overlap
            
            if window_size > len(events):
                window_size = len(events)
                
            # Get windows and categorize devices/events in each window
            cats2windows = []
            tcp_events_windows = []
            sensitive_data_trace = {'contacts': [], 'sms': [], 'calendar': [], 'call_logs': []}
            
            i = 0
            while i < len(events):
                end = min(i + window_size, len(events))
                window = events[i:end]
                
                # Categorize events in this window
                cats_window = []
                tcp_window = []
                window_sensitive = {data_type: [] for data_type in sensitive_data_trace}
                
                # Device categorization and sensitive data detection
                for event in window:
                    if event.get('tgid') == target_pid and 'details' in event:
                        device = event['details'].get('k_dev') or event['details'].get('k__dev')
                        if device and device != 0 and device in dev2cat:
                            cat = dev2cat[device]
                            if cat not in cats_window:
                                cats_window.append(cat)
                    
                    # TCP events
                    if event.get('event') == 'inet_sock_set_state' and 'details' in event:
                        details = event['details']
                        if 'newstate' in details and 'daddr' in details:
                            # Include both IP and port information
                            daddr = details.get('daddr', 'unknown')
                            dport = details.get('dport', '')
                            sport = details.get('sport', '')
                            
                            # Format: STATE: IP:PORT (local_port)
                            if dport and sport:
                                tcp_info = f"{details['newstate']}: {daddr}:{dport} ({sport})"
                            else:
                                tcp_info = f"{details['newstate']}: {daddr}"
                            tcp_window.append(tcp_info)
                    
                    # Sensitive data detection (device+inode matching)
                    if sensitive_resources and 'details' in event:
                        sensitive_type = self._check_sensitive_resource(event, sensitive_resources)
                        if sensitive_type and sensitive_type in window_sensitive:
                            window_sensitive[sensitive_type].append(event)
                
                # Store sensitive data for this window
                for data_type in sensitive_data_trace:
                    sensitive_data_trace[data_type].append(window_sensitive[data_type])
                
                cats2windows.append(cats_window)
                tcp_events_windows.append(tcp_window)
                
                if end == len(events):
                    break
                i += step
            
            # Add TCP events to windows
            for i, tcp_window in enumerate(tcp_events_windows):
                if tcp_window and i < len(cats2windows):
                    # Add first TCP event of window
                    cats2windows[i].append(tcp_window[0])
            
            # Add sensitive data events to windows (matching notebook cell 11 logic)
            for i, ev_list in enumerate(cats2windows):
                # Add contacts if detected in this window
                if i < len(sensitive_data_trace['contacts']) and len(sensitive_data_trace['contacts'][i]) > 0:
                    if "contacts" not in ev_list:
                        ev_list.append("contacts")
                
                # Add SMS if detected in this window
                if i < len(sensitive_data_trace['sms']) and len(sensitive_data_trace['sms'][i]) > 0:
                    if "sms" not in ev_list:
                        ev_list.append("sms")
                
                # Add calendar if detected in this window
                if i < len(sensitive_data_trace['calendar']) and len(sensitive_data_trace['calendar'][i]) > 0:
                    if "calendar" not in ev_list:
                        ev_list.append("calendar")
                
                # Add call_logs if detected in this window
                if i < len(sensitive_data_trace['call_logs']) and len(sensitive_data_trace['call_logs'][i]) > 0:
                    if "call_logs" not in ev_list:
                        ev_list.append("call_logs")
            
            # Define event types, markers, and colors (from notebook)
            event_markers = {
                "camera": "o",          # Circle
                "TCP_SYN_SENT": "^",    # Triangle Up
                "audio_in": "x",
                "bluetooth": "1",
                "nfc": "2",
                "gnss": "3",
                "TCP_LAST_ACK": "v",     # Triangle Down
                "contacts": "*",
                "sms": "s",
                "calendar": "D",
                "call_logs": "p"
            }
            event_colors = {
                "camera": "blue",
                "audio_in": "red",
                "TCP_SYN_SENT": "green",
                "TCP_LAST_ACK": "orange",
                "bluetooth": "grey",
                "nfc": "magenta",
                "gnss": "black",
                "contacts": "purple",
                "sms": "brown",
                "calendar": "cyan",
                "call_logs": "olive"
            }
            
            # Prepare data for plotting
            x_values, y_values, markers, colors, annotations = [], [], [], [], []
            event_types = ["camera", "audio_in", "TCP", "bluetooth", "nfc", "gnss", "contacts", "sms", "calendar", "call_logs"]
            
            N = len(cats2windows)
            
            for i, ev_list in enumerate(cats2windows):
                for ev in ev_list:
                    if ev.startswith("TCP_SYN_SENT"):
                        ev_type = "TCP"
                        marker = event_markers["TCP_SYN_SENT"]
                        color = event_colors["TCP_SYN_SENT"]
                        ip = ev.split(": ")[1] if ": " in ev else ""
                        annotations.append((i, event_types.index("TCP"), ip, marker, color))
                    elif ev.startswith("TCP_LAST_ACK") or ev.startswith("TCP_CLOSE") or ev.startswith("TCP_FIN_WAIT1"):
                        ev_type = "TCP"
                        marker = event_markers["TCP_LAST_ACK"]
                        color = event_colors["TCP_LAST_ACK"]
                        ip = ev.split(": ")[1] if ": " in ev else ""
                        annotations.append((i, event_types.index("TCP"), ip, marker, color))
                    elif ev in event_types:
                        ev_type = ev
                        marker = event_markers.get(ev, "o")
                        color = event_colors.get(ev, "blue")
                    else:
                        continue  # Skip unknown events
                    
                    if "TCP" in ev:
                        y_pos = event_types.index("TCP")
                    else:
                        y_pos = event_types.index(ev_type) if ev_type in event_types else 0
                    
                    x_values.append(i)
                    y_values.append(y_pos)
                    markers.append(marker)
                    colors.append(color)
            
            if not x_values:
                return None
            
            # Create plot
            scale = 2.0
            fig_width = max(8, N * 0.3) * scale
            fig_height = 6
            fig, ax = plt.subplots(figsize=(fig_width, fig_height))
            
            # Scatter plot for each event type
            legend_labels = {}
            for i in range(len(x_values)):
                label = None
                marker_key = markers[i]
                if marker_key not in legend_labels:
                    legend_labels[marker_key] = colors[i]
                    # Find event type name for legend
                    for event_name, event_marker in event_markers.items():
                        if event_marker == marker_key:
                            label = event_name
                            break
                
                ax.scatter(x_values[i], y_values[i], marker=markers[i], color=colors[i], label=label, alpha=0.7, s=50)
            
            # Annotate TCP IPs with enhanced formatting
            for x, y, ip_info, marker, color in annotations:
                if ip_info:
                    # Split IP info to show on multiple lines if needed
                    if len(ip_info) > 15:  # If too long, split it
                        parts = ip_info.split(': ')
                        if len(parts) == 2:
                            state, address = parts
                            ax.text(x, y - 0.15, state, fontsize=7, ha="center", weight='bold', color=color)
                            ax.text(x, y - 0.35, address, fontsize=6, ha="center", rotation=30, color=color)
                        else:
                            ax.text(x, y - 0.25, ip_info, fontsize=6, ha="center", rotation=30, color=color)
                    else:
                        ax.text(x, y - 0.25, ip_info, fontsize=7, ha="center", rotation=30, color=color)
            
            # Formatting
            ax.set_yticks(range(len(event_types)))
            ax.set_yticklabels(event_types, fontsize=10)
            ax.set_ylim(-0.5, len(event_types) - 0.5)
            
            if N > 1:
                ax.set_xticks(np.linspace(0, N-1, min(10, N), dtype=int))
            ax.set_xlabel("Time Windows", fontsize=12)
            ax.set_title(f"High-Level Behavior Timeline (PID {target_pid})", fontsize=14)
            
            # Add legend
            handles, labels = ax.get_legend_handles_labels()
            if handles and labels:
                # Remove duplicates
                new_handles, new_labels = [], []
                seen = set()
                for h, l in zip(handles, labels):
                    if l and l not in seen:
                        new_handles.append(h)
                        new_labels.append(l)
                        seen.add(l)
                if new_handles:
                    ax.legend(new_handles, new_labels, bbox_to_anchor=(1.05, 1), loc='upper left')
            
            plt.grid(axis="x", linestyle="--", alpha=0.5)
            plt.tight_layout()
            
            return self._plot_to_base64()
            
        except Exception as e:
            self.logger.error(f"Error creating behavior timeline chart: {str(e)}")
            return None
    
    def _create_category_chart(self, events):
        """Create category distribution pie chart"""
        try:
            category_counts = defaultdict(int)
            for event in events:
                category = self._categorize_event(event.get('event', ''))
                category_counts[category] += 1
            
            if not category_counts:
                return None
            
            plt.figure(figsize=(8, 8))
            labels = list(category_counts.keys())
            sizes = list(category_counts.values())
            colors = ['#28a745', '#007bff', '#6f42c1', '#fd7e14', '#17a2b8', '#6c757d']
            
            plt.pie(sizes, labels=labels, colors=colors[:len(labels)], autopct='%1.1f%%', startangle=90)
            plt.title('Event Category Distribution')
            plt.axis('equal')
            
            return self._plot_to_base64()
            
        except Exception as e:
            self.logger.error(f"Error creating category chart: {str(e)}")
            return None
    
    def _create_device_chart(self, events):
        """Create device usage bar chart"""
        try:
            device_counts = defaultdict(int)
            for event in events:
                if 'details' in event:
                    device = event['details'].get('k_dev') or event['details'].get('k__dev')
                    if device and device != 0:
                        device_counts[device] += 1
            
            if not device_counts:
                return None
            
            # Top 10 devices
            top_devices = sorted(device_counts.items(), key=lambda x: x[1], reverse=True)[:10]
            
            plt.figure(figsize=(12, 6))
            devices, counts = zip(*top_devices)
            
            plt.bar(range(len(devices)), counts, color='#4682B4')
            plt.xlabel('Device ID')
            plt.ylabel('Event Count')
            plt.title('Top 10 Devices by Usage')
            plt.xticks(range(len(devices)), [str(d) for d in devices], rotation=45)
            
            # Add value labels on bars
            for i, count in enumerate(counts):
                plt.text(i, count + max(counts) * 0.01, str(count), ha='center')
            
            plt.tight_layout()
            
            return self._plot_to_base64()
            
        except Exception as e:
            self.logger.error(f"Error creating device chart: {str(e)}")
            return None
    
    def _create_network_chart(self, events):
        """Create network activity chart"""
        try:
            # Use the same criteria as _analyze_network_events to find network events
            network_events = [e for e in events if 'inet' in e.get('event', '') or 'sock' in e.get('event', '') or 'tcp' in e.get('event', '').lower() or 'udp' in e.get('event', '').lower()]
            
            if not network_events:
                return None
            
            tcp_states = defaultdict(int)
            for event in network_events:
                if event.get('event') == 'inet_sock_set_state' and 'details' in event:
                    state = event['details'].get('newstate', 'unknown')
                    tcp_states[state] += 1
            
            if not tcp_states:
                return None
            
            plt.figure(figsize=(10, 6))
            states = list(tcp_states.keys())
            counts = list(tcp_states.values())
            
            plt.bar(states, counts, color='#17a2b8')
            plt.xlabel('TCP State')
            plt.ylabel('Transition Count')
            plt.title('TCP State Transitions')
            plt.xticks(rotation=45)
            plt.tight_layout()
            
            return self._plot_to_base64()
            
        except Exception as e:
            self.logger.error(f"Error creating network chart: {str(e)}")
            return None
    
    def _create_process_chart(self, events):
        """Create process activity chart"""
        try:
            process_counts = Counter(e.get('process', 'unknown') for e in events)
            top_processes = process_counts.most_common(10)
            
            if not top_processes:
                return None
            
            plt.figure(figsize=(12, 6))
            processes, counts = zip(*top_processes)
            
            plt.barh(range(len(processes)), counts, color='#fd7e14')
            plt.xlabel('Event Count')
            plt.ylabel('Process Name')
            plt.title('Top 10 Most Active Processes')
            plt.yticks(range(len(processes)), processes)
            
            # Add value labels
            for i, count in enumerate(counts):
                plt.text(count + max(counts) * 0.01, i, str(count), va='center')
            
            plt.tight_layout()
            
            return self._plot_to_base64()
            
        except Exception as e:
            self.logger.error(f"Error creating process chart: {str(e)}")
            return None
    
    def _plot_to_base64(self):
        """Convert current matplotlib plot to base64 string"""
        buffer = BytesIO()
        plt.savefig(buffer, format='png', dpi=100, bbox_inches='tight')
        buffer.seek(0)
        plt.close()
        
        img_str = base64.b64encode(buffer.getvalue()).decode('utf-8')
        return f'data:image/png;base64,{img_str}'
    
    def _generate_detailed_insights(self, analysis_data):
        """Generate detailed insights based on analysis results"""
        insights = {}
        
        # Device Analysis Insights
        if analysis_data.get('device_analysis'):
            insights['device'] = self._generate_device_insights(analysis_data['device_analysis'])
        
        # Category Analysis Insights
        if analysis_data.get('category_analysis'):
            insights['category'] = self._generate_category_insights(analysis_data['category_analysis'])
        
        # Network Analysis Insights
        if analysis_data.get('network_analysis') and not analysis_data['network_analysis'].get('no_network_events'):
            insights['network'] = self._generate_network_insights(analysis_data['network_analysis'])
        
        # Sensitive Data Insights
        if analysis_data.get('sensitive_data_analysis') and analysis_data['sensitive_data_analysis'].get('total_sensitive_events', 0) > 0:
            insights['sensitive'] = self._generate_sensitive_data_insights(analysis_data['sensitive_data_analysis'])
        
        return insights
    
    def _generate_device_insights(self, device_analysis):
        """Generate device analysis insights"""
        insights = []
        
        if device_analysis.get('unique_devices', 0) > 0:
            insights.append({
                'icon': '📱',
                'text': f"<strong>{device_analysis['unique_devices']}</strong> unique devices accessed"
            })
            insights.append({
                'icon': '📊',
                'text': f"<strong>{device_analysis['total_device_events']}</strong> total device events"
            })
            
            if device_analysis.get('category_usage') and device_analysis['category_usage']:
                top_category = max(device_analysis['category_usage'].items(), key=lambda x: x[1])
                insights.append({
                    'icon': '🏆',
                    'text': f"Most used category: <strong>{top_category[0]}</strong> ({top_category[1]} events)"
                })
        else:
            insights.append({
                'icon': 'ℹ️',
                'text': "No device access detected"
            })
        
        return {
            'title': 'Device Analysis',
            'insights': insights
        }
    
    def _generate_category_insights(self, category_analysis):
        """Generate category analysis insights"""
        insights = []
        
        if 'read_write_ratio' in category_analysis:
            ratio = category_analysis['read_write_ratio']
            if ratio == float('inf'):
                insights.append({
                    'icon': '📖',
                    'text': "Only read operations detected (no writes)"
                })
            elif ratio == 0:
                insights.append({
                    'icon': '✏️',
                    'text': "Only write operations detected (no reads)"
                })
            else:
                insights.append({
                    'icon': '⚖️',
                    'text': f"Read/Write ratio: <strong>{ratio:.2f}</strong>"
                })
        
        if category_analysis.get('io_patterns') and category_analysis['io_patterns'].get('total_io_events'):
            io_patterns = category_analysis['io_patterns']
            insights.append({
                'icon': '💾',
                'text': f"<strong>{io_patterns['total_io_events']}</strong> I/O events detected"
            })
            
            if io_patterns.get('file_types') and io_patterns['file_types']:
                top_file_type = list(io_patterns['file_types'].items())[0]
                insights.append({
                    'icon': '📄',
                    'text': f"Most accessed file type: <strong>.{top_file_type[0]}</strong> ({top_file_type[1]} times)"
                })
        
        return {
            'title': 'Category Analysis',
            'insights': insights
        }
    
    def _generate_network_insights(self, network_analysis):
        """Generate network analysis insights"""
        insights = []
        
        insights.append({
            'icon': '🌐',
            'text': f"<strong>{network_analysis['network_events_count']}</strong> network events detected"
        })
        
        if network_analysis.get('tcp_state_transitions') and network_analysis['tcp_state_transitions']:
            states = list(network_analysis['tcp_state_transitions'].keys())
            insights.append({
                'icon': '🔄',
                'text': f"TCP states observed: <strong>{', '.join(states)}</strong>"
            })
        
        if network_analysis.get('connection_destinations') and network_analysis['connection_destinations']:
            dest_count = len(network_analysis['connection_destinations'])
            insights.append({
                'icon': '🎯',
                'text': f"<strong>{dest_count}</strong> unique connection destinations"
            })
        
        return {
            'title': 'Network Analysis',
            'insights': insights
        }
    
    def _generate_sensitive_data_insights(self, sensitive_analysis):
        """Generate sensitive data analysis insights"""
        insights = []
        
        insights.append({
            'icon': '🔒',
            'text': f"<strong>{sensitive_analysis['total_sensitive_events']}</strong> potential sensitive data accesses"
        })
        
        emoji_map = {
            'contacts': '👥',
            'sms': '💬',
            'calendar': '📅',
            'call_logs': '📞',
            'location': '📍',
            'camera': '📷',
            'microphone': '🎤'
        }
        
        for category, count in sensitive_analysis.get('sensitive_data_access', {}).items():
            if count > 0:
                emoji = emoji_map.get(category, '📁')
                insights.append({
                    'icon': emoji,
                    'text': f"{category}: <strong>{count}</strong> accesses"
                })
        
        return {
            'title': 'Sensitive Data Analysis',
            'insights': insights
        }
    
    def generate_comprehensive_report(self, events, target_pid, analysis_results=None):
        """
        Generate a comprehensive analysis report including all new capabilities
        
        Args:
            events: List of parsed events
            target_pid: Target process ID
            analysis_results: Optional pre-computed analysis results
            
        Returns:
            Dictionary with comprehensive analysis report
        """
        from .comprehensive_analyzer import ComprehensiveAnalyzer
        
        if not analysis_results:
            analyzer = ComprehensiveAnalyzer(self.config)
            
            # Run all analysis types
            security_analysis = analyzer.analyze_security_events(events, target_pid)
            network_analysis = analyzer.analyze_network_flows(events, target_pid)
            process_analysis = analyzer.analyze_process_genealogy(events, target_pid)
            file_analysis = analyzer.slice_file_analysis(events, target_pid)
        else:
            security_analysis = analysis_results.get('security_analysis', {})
            network_analysis = analysis_results.get('network_analysis', {})
            process_analysis = analysis_results.get('process_analysis', {})
            file_analysis = analysis_results.get('file_analysis', {})
        
        # Generate visualization data
        visualization_data = self._generate_enhanced_visualization_data(
            events, target_pid, security_analysis, network_analysis, process_analysis
        )
        
        # Calculate risk assessment
        risk_assessment = self._calculate_comprehensive_risk(
            security_analysis, network_analysis, process_analysis
        )
        
        # Generate timeline data
        timeline_data = self._generate_enhanced_timeline_data(events, target_pid)
        
        # Generate category statistics
        category_stats = self._generate_enhanced_category_statistics(events)
        
        report = {
            'executive_summary': self._generate_executive_summary(
                security_analysis, network_analysis, process_analysis, risk_assessment
            ),
            'security_analysis': security_analysis,
            'network_analysis': network_analysis,
            'process_analysis': process_analysis,
            'file_analysis': file_analysis,
            'risk_assessment': risk_assessment,
            'visualization_data': visualization_data,
            'timeline_data': timeline_data,
            'category_statistics': category_stats,
            'recommendations': self._generate_recommendations(risk_assessment, security_analysis)
        }
        
        self.logger.info(f"Generated comprehensive report for PID {target_pid}")
        return report
    
    def _generate_enhanced_visualization_data(self, events, target_pid, security_analysis, network_analysis, process_analysis):
        """Generate enhanced data optimized for new visualization categories"""
        
        # Event categories for enhanced pie charts
        category_counts = defaultdict(int)
        
        # Enhanced timeline data for multi-line charts
        timeline_data = {
            'timestamps': [],
            'security_events': [],
            'network_events': [],
            'process_events': [],
            'filesystem_events': [],
            'ipc_events': [],
            'memory_events': [],
            'bluetooth_events': []
        }
        
        # Security heatmap data
        security_heatmap = defaultdict(lambda: defaultdict(int))
        
        # Network flow data for enhanced network diagrams
        network_flows = {
            'tcp_flows': [],
            'udp_flows': [],
            'bluetooth_flows': [],
            'socket_operations': []
        }
        
        for event in events:
            if target_pid and event.get('tgid') != target_pid:
                continue
                
            category = event.get('category', 'other')
            category_counts[category] += 1
            
            timestamp = event.get('timestamp')
            if timestamp:
                time_bucket = int(timestamp)
                timeline_data['timestamps'].append(timestamp)
                
                # Enhanced categorization for timeline
                timeline_data['security_events'].append(1 if category == 'security' else 0)
                timeline_data['network_events'].append(1 if category == 'network' else 0)
                timeline_data['process_events'].append(1 if category == 'process' else 0)
                timeline_data['filesystem_events'].append(1 if category == 'filesystem' else 0)
                timeline_data['ipc_events'].append(1 if category == 'ipc' else 0)
                timeline_data['memory_events'].append(1 if category == 'memory' else 0)
                timeline_data['bluetooth_events'].append(1 if category == 'bluetooth' else 0)
                
                # Security heatmap
                if category == 'security':
                    event_name = event.get('event', 'unknown')
                    security_heatmap[time_bucket][event_name] += 1
        
        # Convert process tree to enhanced visualization format
        enhanced_process_tree = {}
        if 'process_tree' in process_analysis:
            enhanced_process_tree = self._convert_enhanced_process_tree_for_viz(process_analysis['process_tree'])
        
        return {
            'category_distribution': dict(category_counts),
            'timeline_data': timeline_data,
            'security_heatmap': dict(security_heatmap),
            'network_flows': network_flows,
            'process_tree': enhanced_process_tree,
            'event_distribution_by_hour': self._generate_hourly_distribution(events, target_pid),
            'risk_indicators': self._generate_risk_indicators(security_analysis, network_analysis)
        }
    
    def _convert_enhanced_process_tree_for_viz(self, process_tree):
        """Convert process tree to enhanced visualization-friendly format"""
        nodes = []
        edges = []
        levels = defaultdict(list)
        
        def traverse_tree(node, parent_id=None, level=0):
            if not node:
                return
                
            node_id = node.get('pid')
            node_info = node.get('info', {})
            
            node_data = {
                'id': node_id,
                'label': f"PID {node_id}",
                'name': node_info.get('name', 'unknown'),
                'level': level,
                'birth_time': node_info.get('birth_time'),
                'parent': node_info.get('parent'),
                'size': len(node.get('children', [])) + 1,  # Size based on children count
                'type': 'process'
            }
            
            nodes.append(node_data)
            levels[level].append(node_data)
            
            if parent_id is not None:
                edges.append({
                    'from': parent_id,
                    'to': node_id,
                    'type': 'fork',
                    'label': 'fork'
                })
            
            for child in node.get('children', []):
                traverse_tree(child, node_id, level + 1)
        
        for root_pid, root_node in process_tree.items():
            traverse_tree(root_node)
        
        return {
            'nodes': nodes, 
            'edges': edges,
            'levels': dict(levels),
            'max_depth': max(levels.keys()) if levels else 0
        }
    
    def _generate_hourly_distribution(self, events, target_pid):
        """Generate event distribution by hour of day"""
        hourly_dist = defaultdict(int)
        
        for event in events:
            if target_pid and event.get('tgid') != target_pid:
                continue
                
            timestamp = event.get('timestamp')
            if timestamp:
                import datetime
                hour = datetime.datetime.fromtimestamp(timestamp).hour
                hourly_dist[hour] += 1
        
        # Convert to list format for easier charting
        hourly_data = [hourly_dist.get(i, 0) for i in range(24)]
        
        return {
            'hourly_counts': hourly_data,
            'peak_hour': max(hourly_dist, key=hourly_dist.get) if hourly_dist else 0,
            'total_events': sum(hourly_data)
        }
    
    def _generate_risk_indicators(self, security_analysis, network_analysis):
        """Generate risk indicators for visualization"""
        indicators = []
        
        if security_analysis:
            # Security risk indicators
            if security_analysis.get('privilege_escalation'):
                indicators.append({
                    'type': 'security',
                    'level': 'high',
                    'title': 'Privilege Escalation',
                    'count': len(security_analysis['privilege_escalation']),
                    'icon': '⚠️'
                })
            
            if security_analysis.get('debugging_attempts'):
                indicators.append({
                    'type': 'security',
                    'level': 'medium',
                    'title': 'Debug Attempts',
                    'count': len(security_analysis['debugging_attempts']),
                    'icon': '🔍'
                })
            
            if security_analysis.get('memory_protection_changes'):
                rwx_changes = sum(1 for change in security_analysis['memory_protection_changes'] 
                                if change.get('suspicious', False))
                if rwx_changes > 0:
                    indicators.append({
                        'type': 'security',
                        'level': 'high',
                        'title': 'Suspicious Memory Changes',
                        'count': rwx_changes,
                        'icon': '🛡️'
                    })
        
        if network_analysis:
            # Network risk indicators
            summary = network_analysis.get('summary', {})
            if summary.get('communication_intensity') == 'HIGH':
                indicators.append({
                    'type': 'network',
                    'level': 'medium',
                    'title': 'High Network Activity',
                    'count': summary.get('total_tcp_events', 0) + summary.get('total_udp_events', 0),
                    'icon': '🌐'
                })
        
        return indicators
    
    def _calculate_comprehensive_risk(self, security_analysis, network_analysis, process_analysis):
        """Calculate comprehensive risk assessment"""
        risk_factors = {
            'security_risk': 0,
            'network_risk': 0,
            'process_risk': 0,
            'overall_risk': 0
        }
        
        # Security risk calculation
        if security_analysis and 'summary' in security_analysis:
            security_summary = security_analysis['summary']
            risk_level = security_summary.get('risk_level', 'NONE')
            
            risk_mapping = {'NONE': 0, 'LOW': 25, 'MEDIUM': 50, 'HIGH': 100}
            risk_factors['security_risk'] = risk_mapping.get(risk_level, 0)
        
        # Network risk calculation
        if network_analysis and 'summary' in network_analysis:
            network_summary = network_analysis['summary']
            intensity = network_summary.get('communication_intensity', 'LOW')
            
            intensity_mapping = {'LOW': 10, 'MEDIUM': 30, 'HIGH': 60}
            risk_factors['network_risk'] = intensity_mapping.get(intensity, 0)
        
        # Process risk calculation
        if process_analysis and 'summary' in process_analysis:
            process_summary = process_analysis['summary']
            suspicious_patterns = process_summary.get('suspicious_patterns', [])
            
            risk_factors['process_risk'] = min(len(suspicious_patterns) * 20, 80)
        
        # Calculate overall risk (weighted average)
        weights = {'security_risk': 0.5, 'network_risk': 0.2, 'process_risk': 0.3}
        
        overall_risk = sum(
            risk_factors[factor] * weight 
            for factor, weight in weights.items()
        )
        
        risk_factors['overall_risk'] = overall_risk
        
        # Categorize overall risk
        if overall_risk >= 70:
            risk_category = 'CRITICAL'
        elif overall_risk >= 50:
            risk_category = 'HIGH'
        elif overall_risk >= 30:
            risk_category = 'MEDIUM'
        elif overall_risk >= 10:
            risk_category = 'LOW'
        else:
            risk_category = 'MINIMAL'
        
        return {
            'risk_factors': risk_factors,
            'overall_risk_score': overall_risk,
            'risk_category': risk_category,
            'risk_breakdown': {
                'security': f"{risk_factors['security_risk']}%",
                'network': f"{risk_factors['network_risk']}%",
                'process': f"{risk_factors['process_risk']}%"
            }
        }
    
    def _generate_enhanced_timeline_data(self, events, target_pid):
        """Generate enhanced timeline data for visualization"""
        timeline_events = []
        
        for event in events:
            if target_pid and event.get('tgid') != target_pid:
                continue
                
            timeline_event = {
                'timestamp': event.get('timestamp'),
                'event_type': event.get('event'),
                'category': event.get('category', 'other'),
                'process': event.get('process'),
                'pid': event.get('tgid'),
                'description': self._generate_enhanced_event_description(event),
                'severity': self._calculate_event_severity(event)
            }
            timeline_events.append(timeline_event)
        
        # Sort by timestamp
        timeline_events.sort(key=lambda x: x['timestamp'] or 0)
        
        return timeline_events
    
    def _generate_enhanced_event_description(self, event):
        """Generate enhanced human-readable description for an event"""
        event_name = event.get('event', 'unknown')
        details = event.get('details', {})
        category = event.get('category', 'other')
        
        descriptions = {
            # Enhanced filesystem descriptions
            'read_probe': f"📖 Read from {details.get('pathname', 'file')} ({details.get('count', 0)} bytes)",
            'write_probe': f"✏️ Write to {details.get('pathname', 'file')} ({details.get('count', 0)} bytes)",
            'ioctl_probe': f"⚙️ IOCTL operation on {details.get('pathname', 'device')}",
            
            # Enhanced network descriptions
            'tcp_sendmsg': f"📤 TCP send ({details.get('size', 0)} bytes)",
            'tcp_recvmsg': f"📥 TCP receive ({details.get('len', 0)} bytes)",
            'udp_sendmsg': f"📤 UDP send ({details.get('len', 0)} bytes)",
            'udp_recvmsg': f"📥 UDP receive ({details.get('len', 0)} bytes)",
            '__sys_socket': f"🔌 Create socket (family: {details.get('family', 'unknown')})",
            '__sys_connect': f"🔗 Connect socket (fd: {details.get('sockfd', 'unknown')})",
            '__sys_bind': f"🔒 Bind socket (fd: {details.get('sockfd', 'unknown')})",
            
            # Enhanced security descriptions
            '__arm64_sys_setuid': f"👤 Set UID to {details.get('uid', 'unknown')}",
            '__arm64_sys_setresuid': f"👥 Set RUID/EUID/SUID ({details.get('ruid', '-')}/{details.get('euid', '-')}/{details.get('suid', '-')})",
            'ptrace_attach': f"🔍 Ptrace attach to task {details.get('task', 'unknown')}",
            '__arm64_sys_mprotect': f"🛡️ Memory protection change at {hex(details.get('start', 0))} (len: {details.get('len', 0)})",
            '__arm64_sys_capset': f"⚡ Capability change",
            
            # Enhanced process descriptions
            'sched_process_fork': f"🍴 Process fork (child: {details.get('child_pid', 'unknown')})",
            'sched_process_exec': f"🚀 Process exec",
            '__arm64_sys_execve': f"📋 Execute {details.get('filename', 'unknown')}",
            'load_elf_binary': f"📚 Load ELF binary",
            
            # Enhanced IPC descriptions
            'binder_transaction': f"📨 Binder transaction",
            'binder_transaction_received': f"📬 Binder transaction received",
            'unix_stream_sendmsg': f"💬 Unix stream send",
            'unix_stream_recvmsg': f"💬 Unix stream receive",
            
            # Memory descriptions
            'mmap_probe': f"🗺️ Memory map of {details.get('pathname', 'file')}",
            
            # Bluetooth descriptions
            'hci_sock_sendmsg': f"📶 HCI Bluetooth send",
            'sco_sock_sendmsg': f"🎧 SCO Bluetooth send",
            'l2cap_sock_sendmsg': f"🔵 L2CAP Bluetooth send"
        }
        
        return descriptions.get(event_name, f"Event: {event_name}")
    
    def _calculate_event_severity(self, event):
        """Calculate severity level for an event"""
        event_name = event.get('event', 'unknown')
        category = event.get('category', 'other')
        
        # High severity events
        high_severity_events = [
            '__arm64_sys_setuid', '__arm64_sys_setresuid', 'ptrace_attach',
            '__arm64_sys_mprotect', '__arm64_sys_capset'
        ]
        
        # Medium severity events
        medium_severity_events = [
            '__arm64_sys_execve', 'load_elf_binary', 'sched_process_fork'
        ]
        
        if event_name in high_severity_events:
            return 'high'
        elif event_name in medium_severity_events:
            return 'medium'
        elif category in ['security', 'process']:
            return 'medium'
        else:
            return 'low'
    
    def _generate_enhanced_category_statistics(self, events):
        """Generate enhanced statistics by event category"""
        category_stats = defaultdict(lambda: {
            'count': 0,
            'first_timestamp': None,
            'last_timestamp': None,
            'processes': set(),
            'event_types': set(),
            'severity_distribution': defaultdict(int),
            'hourly_distribution': defaultdict(int)
        })
        
        for event in events:
            category = event.get('category', 'other')
            timestamp = event.get('timestamp')
            process = event.get('process')
            event_type = event.get('event')
            severity = self._calculate_event_severity(event)
            
            stats = category_stats[category]
            stats['count'] += 1
            stats['processes'].add(process)
            stats['event_types'].add(event_type)
            stats['severity_distribution'][severity] += 1
            
            if timestamp:
                import datetime
                hour = datetime.datetime.fromtimestamp(timestamp).hour
                stats['hourly_distribution'][hour] += 1
                
                if stats['first_timestamp'] is None or timestamp < stats['first_timestamp']:
                    stats['first_timestamp'] = timestamp
                if stats['last_timestamp'] is None or timestamp > stats['last_timestamp']:
                    stats['last_timestamp'] = timestamp
        
        # Convert sets to lists and dicts for JSON serialization
        for category in category_stats:
            category_stats[category]['processes'] = list(category_stats[category]['processes'])
            category_stats[category]['event_types'] = list(category_stats[category]['event_types'])
            category_stats[category]['severity_distribution'] = dict(category_stats[category]['severity_distribution'])
            category_stats[category]['hourly_distribution'] = dict(category_stats[category]['hourly_distribution'])
            
            # Calculate duration
            if (category_stats[category]['first_timestamp'] and 
                category_stats[category]['last_timestamp']):
                duration = (category_stats[category]['last_timestamp'] - 
                           category_stats[category]['first_timestamp'])
                category_stats[category]['duration'] = duration
            else:
                category_stats[category]['duration'] = 0
        
        return dict(category_stats)
    
    def _generate_executive_summary(self, security_analysis, network_analysis, process_analysis, risk_assessment):
        """Generate executive summary"""
        summary = {
            'overview': '',
            'key_findings': [],
            'risk_level': risk_assessment.get('risk_category', 'UNKNOWN'),
            'recommendations_count': 0
        }
        
        # Build overview
        overview_parts = []
        
        if security_analysis and 'summary' in security_analysis:
            sec_summary = security_analysis['summary']
            if sec_summary.get('total_privilege_escalations', 0) > 0:
                overview_parts.append(f"{sec_summary['total_privilege_escalations']} privilege escalation(s) detected")
            if sec_summary.get('total_suspicious_activities', 0) > 0:
                overview_parts.append(f"{sec_summary['total_suspicious_activities']} suspicious security activity(ies)")
        
        if network_analysis and 'summary' in network_analysis:
            net_summary = network_analysis['summary']
            if net_summary.get('total_tcp_events', 0) > 0 or net_summary.get('total_udp_events', 0) > 0:
                overview_parts.append(f"Network activity detected ({net_summary.get('communication_intensity', 'LOW')} intensity)")
        
        if process_analysis and 'summary' in process_analysis:
            proc_summary = process_analysis['summary']
            if proc_summary.get('total_forks', 0) > 0:
                overview_parts.append(f"{proc_summary['total_forks']} process creation(s)")
        
        summary['overview'] = '. '.join(overview_parts) if overview_parts else 'No significant activity detected'
        
        # Key findings
        if security_analysis:
            if security_analysis.get('privilege_escalation'):
                summary['key_findings'].append('Privilege escalation attempts detected')
            if security_analysis.get('debugging_attempts'):
                summary['key_findings'].append('Process debugging attempts detected')
        
        if network_analysis and network_analysis.get('summary', {}).get('communication_intensity') == 'HIGH':
            summary['key_findings'].append('High network communication activity')
        
        if process_analysis and process_analysis.get('summary', {}).get('suspicious_patterns'):
            summary['key_findings'].append('Suspicious process behavior patterns')
        
        return summary
    
    def _generate_recommendations(self, risk_assessment, security_analysis):
        """Generate security recommendations"""
        recommendations = []
        
        risk_category = risk_assessment.get('risk_category', 'MINIMAL')
        
        if risk_category in ['CRITICAL', 'HIGH']:
            recommendations.append({
                'priority': 'HIGH',
                'category': 'immediate_action',
                'title': 'Immediate Security Review Required',
                'description': 'High risk activity detected. Conduct immediate security analysis.'
            })
        
        if security_analysis:
            if security_analysis.get('privilege_escalation'):
                recommendations.append({
                    'priority': 'HIGH',
                    'category': 'security',
                    'title': 'Review Privilege Escalation',
                    'description': 'Privilege escalation detected. Verify if this is expected behavior.'
                })
            
            if security_analysis.get('debugging_attempts'):
                recommendations.append({
                    'priority': 'MEDIUM',
                    'category': 'security',
                    'title': 'Monitor Debugging Activity',
                    'description': 'Process debugging attempts detected. Monitor for malicious activity.'
                })
            
            if security_analysis.get('memory_protection_changes'):
                rwx_changes = [
                    change for change in security_analysis['memory_protection_changes']
                    if change.get('suspicious', False)
                ]
                if rwx_changes:
                    recommendations.append({
                        'priority': 'HIGH',
                        'category': 'security',
                        'title': 'Review Memory Protection Changes',
                        'description': 'Suspicious memory protection changes (RWX) detected.'
                    })
        
        if risk_category == 'MINIMAL':
            recommendations.append({
                'priority': 'LOW',
                'category': 'monitoring',
                'title': 'Continue Monitoring',
                'description': 'No significant threats detected. Continue regular monitoring.'
            })
        
        return recommendations
