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

import myutils

class AdvancedAnalytics:
    """Advanced analytics for trace data with high-level insights"""
    
    def __init__(self, config_class):
        self.config = config_class
        self.logger = self._setup_logger()
        
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
    
    def analyze_trace_data(self, events, target_pid=None):
        """
        Perform comprehensive analysis of trace data
        
        Args:
            events: List of parsed events
            target_pid: Target process ID for analysis
            
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
            charts = self._generate_charts(events, target_pid)
            
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
        """Analyze potential sensitive data access"""
        # This is a placeholder - would need actual sensitive resource mappings
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
    
    def _generate_charts(self, events, target_pid):
        """Generate base64-encoded charts similar to the notebook"""
        charts = {}
        
        try:
            # 1. High-Level Behavior Timeline (from notebook cell 11)
            charts['behavior_timeline'] = self._create_behavior_timeline_chart(events, target_pid)
            
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
    
    def _create_behavior_timeline_chart(self, events, target_pid):
        """Create high-level behavior timeline chart based on notebook cell 11"""
        try:
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
            
            # Perform windowed analysis (simplified version of notebook approach)
            window_size = 1000  # Smaller windows for web
            overlap = 200
            step = window_size - overlap
            
            if window_size > len(events):
                window_size = len(events)
                
            # Get windows and categorize devices/events in each window
            cats2windows = []
            tcp_events_windows = []
            
            i = 0
            while i < len(events):
                end = min(i + window_size, len(events))
                window = events[i:end]
                
                # Categorize events in this window
                cats_window = []
                tcp_window = []
                
                # Device categorization
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
                            tcp_info = f"{details['newstate']}: {details['daddr']}"
                            tcp_window.append(tcp_info)
                
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
            
            # Annotate TCP IPs
            for x, y, ip, marker, color in annotations:
                if ip:
                    ax.text(x, y - 0.2, ip, fontsize=6, ha="center", rotation=45, color=color)
            
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
            network_events = [e for e in events if 'inet' in e.get('event', '')]
            
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