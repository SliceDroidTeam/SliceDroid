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
        network_events = [e for e in events if 'inet' in e.get('event', '') or 'sock' in e.get('event', '') or 'tcp' in e.get('event', '').lower() or 'udp' in e.get('event', '').lower()]
        
        if not network_events:
            return {'no_network_events': True}
        
        tcp_states = defaultdict(int)
        connections = defaultdict(int)
        
        # Track data transfer
        data_transfer = self._analyze_data_transfer(events)
        
        # Analyze socket types
        socket_types = self._analyze_socket_types(events)
        
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
            'connection_destinations': dict(sorted(connections.items(), key=lambda x: x[1], reverse=True)[:10]),
            'data_transfer': data_transfer,
            'socket_types': socket_types,
            '_events': events  # Store events for further analysis
        }
    
    def _get_event_size(self, event):
        """Helper method to extract size information from an event"""
        if not event or 'details' not in event:
            return 0
            
        details = event.get('details', {})
        event_name = event.get('event', '').lower()
        
        # Try different field names for size
        size = details.get('size', details.get('len', 0))
        
        # Convert to integer if it's a string
        if isinstance(size, str):
            try:
                size = int(size)
            except ValueError:
                size = 0
        elif not isinstance(size, (int, float)):
            size = 0
            
        # Sanity check: reject unreasonably large values
        if size > 100 * 1024 * 1024:  # > 100MB
            return 0
            
        return size
    
    def _analyze_socket_types(self, events):
        """Analyze socket types and their data transfer amounts"""
        # Socket type definitions
        socket_type_map = {
            1: 'SOCK_STREAM',    # TCP
            2: 'SOCK_DGRAM',     # UDP
            3: 'SOCK_RAW',       # Raw IP packets
            4: 'SOCK_RDM',       # Reliable datagram
            5: 'SOCK_SEQPACKET', # Connection-oriented packets
            10: 'SOCK_PACKET'    # Device level packet
        }
        
        socket_type_descriptions = {
            'SOCK_STREAM': 'TCP',
            'SOCK_DGRAM': 'UDP',
            'SOCK_RAW': 'Raw IP',
            'SOCK_RDM': 'Reliable Datagram',
            'SOCK_SEQPACKET': 'Sequential Packet',
            'SOCK_PACKET': 'Device Level',
            'unknown': 'Unknown Type'
        }
        
        # Initialize socket type tracking
        socket_types = {
            'total_sockets': 0,
            'types': defaultdict(lambda: {
                'count': 0, 
                'data_bytes': 0, 
                'data_mb': 0,
                'description': 'Unknown Type'
            })
        }
        
        # Track socket creation events to map file descriptors to socket types
        fd_to_socket_type = {}
        
        # First pass: identify socket types from socket creation events
        for event in events:
            event_name = event.get('event', '')
            details = event.get('details', {})
            
            # Socket creation events - check multiple event names that might indicate socket creation
            if (event_name in ['__sys_socket', 'sys_socket', 'socket_create', 'socket_syscall'] and 
                'type' in details):
                socket_fd = details.get('ret', details.get('fd', -1))  # Return value is the file descriptor
                socket_type_num = details.get('type')
                
                if socket_fd > 0:  # Valid file descriptor
                    socket_type = socket_type_map.get(socket_type_num, 'unknown')
                    fd_to_socket_type[socket_fd] = socket_type
                    
                    # Increment socket type count
                    socket_types['types'][socket_type]['count'] += 1
                    socket_types['types'][socket_type]['description'] = socket_type_descriptions.get(socket_type, 'Unknown Type')
                    socket_types['total_sockets'] += 1
            
            # If we can't find socket creation events, infer from other events
            elif 'tcp' in event_name.lower():
                # For TCP events, create a SOCK_STREAM entry if we don't have one
                if 'SOCK_STREAM' not in socket_types['types']:
                    socket_types['types']['SOCK_STREAM']['count'] = 1
                    socket_types['types']['SOCK_STREAM']['description'] = 'TCP'
                    socket_types['total_sockets'] += 1
                    
            elif 'udp' in event_name.lower():
                # For UDP events, create a SOCK_DGRAM entry if we don't have one
                if 'SOCK_DGRAM' not in socket_types['types']:
                    socket_types['types']['SOCK_DGRAM']['count'] = 1
                    socket_types['types']['SOCK_DGRAM']['description'] = 'UDP'
                    socket_types['total_sockets'] += 1
        
        # Second pass: associate data transfer with socket types
        for event in events:
            event_name = event.get('event', '')
            details = event.get('details', {})
            
            # Data transfer events
            if event_name in ['tcp_sendmsg', 'tcp_recvmsg', 'udp_sendmsg', 'udp_recvmsg']:
                # Get socket file descriptor
                socket_fd = details.get('sock_fd', details.get('fd', -1))
                
                # Get data size
                size = 0
                if event_name in ['tcp_sendmsg', 'udp_sendmsg']:
                    size = details.get('size', details.get('len', 0))
                else:  # receive events
                    size = details.get('len', 0)
                
                # Convert to integer if it's a string
                if isinstance(size, str) and size.isdigit():
                    size = int(size)
                elif not isinstance(size, int):
                    size = 0
                
                # Associate with socket type
                socket_type = fd_to_socket_type.get(socket_fd, None)
                
                # If we don't have the socket type from fd, infer from event name
                if not socket_type:
                    if 'tcp' in event_name:
                        socket_type = 'SOCK_STREAM'
                    elif 'udp' in event_name:
                        socket_type = 'SOCK_DGRAM'
                    else:
                        socket_type = 'unknown'
                
                # Update data transfer for this socket type
                socket_types['types'][socket_type]['data_bytes'] += size
        
        # Convert bytes to MB for each socket type
        bytes_to_mb = lambda b: round(b / (1024 * 1024), 2)
        for socket_type in socket_types['types']:
            socket_types['types'][socket_type]['data_mb'] = bytes_to_mb(socket_types['types'][socket_type]['data_bytes'])
        
        return socket_types
    
    def _analyze_data_transfer(self, events):
        """Analyze and calculate data transfer amounts via TCP/UDP with careful metric handling"""
        data_transfer = {
            'tcp': {
                'sent_bytes': 0,
                'received_bytes': 0,
                'sent_mb': 0.0,
                'received_mb': 0.0,
                'total_mb': 0.0,
                'per_destination': defaultdict(lambda: {'sent_bytes': 0, 'received_bytes': 0}),
                'per_process': defaultdict(lambda: {'sent_bytes': 0, 'received_bytes': 0})
            },
            'udp': {
                'sent_bytes': 0,
                'received_bytes': 0,
                'sent_mb': 0.0,
                'received_mb': 0.0,
                'total_mb': 0.0,
                'per_destination': defaultdict(lambda: {'sent_bytes': 0, 'received_bytes': 0}),
                'per_process': defaultdict(lambda: {'sent_bytes': 0, 'received_bytes': 0})
            },
            'total': {
                'sent_bytes': 0,
                'received_bytes': 0,
                'sent_mb': 0.0,
                'received_mb': 0.0,
                'total_mb': 0.0
            }
        }
        
        # Track unique packet identifiers to avoid double counting
        # Use (timestamp, fd, size) as a unique identifier for packets
        processed_packets = set()
        
        # Helper function to safely parse size values
        def safe_parse_size(size_value):
            """Safely parse size values with validation"""
            if size_value is None:
                return 0
                
            # Handle string values
            if isinstance(size_value, str):
                try:
                    # Remove any non-numeric characters
                    clean_size = ''.join(c for c in size_value if c.isdigit())
                    if clean_size:
                        size = int(clean_size)
                        # Sanity check: reject unreasonably large values (>100MB per packet)
                        if size > 100 * 1024 * 1024:
                            return 0
                        return size
                except ValueError:
                    return 0
            
            # Handle numeric values
            elif isinstance(size_value, (int, float)):
                size = int(size_value)
                # Sanity check: reject unreasonably large values (>100MB per packet)
                if size > 100 * 1024 * 1024:
                    return 0
                return size
                
            return 0
        
        # Filter for TCP/UDP send/receive events
        for event in events:
            event_name = event.get('event', '')
            details = event.get('details', {})
            process = event.get('process', 'unknown')
            timestamp = event.get('timestamp', 0)
            
            # Skip events without details
            if not details:
                continue
                
            # Get socket file descriptor for deduplication
            socket_fd = details.get('sock_fd', details.get('fd', -1))
            
            # TCP send events
            if event_name == 'tcp_sendmsg':
                # Try different field names for size
                size = safe_parse_size(details.get('size', details.get('len', 0)))
                
                # Skip if size is 0 or unreasonable
                if size <= 0:
                    continue
                    
                # Create a unique identifier for this packet to avoid double counting
                packet_id = (timestamp, socket_fd, size, 'tcp_send')
                if packet_id in processed_packets:
                    continue
                    
                processed_packets.add(packet_id)
                
                data_transfer['tcp']['sent_bytes'] += size
                data_transfer['total']['sent_bytes'] += size
                
                # Track per destination
                daddr = details.get('daddr', 'unknown')
                if daddr != 'unknown':
                    data_transfer['tcp']['per_destination'][daddr]['sent_bytes'] += size
                
                # Track per process
                data_transfer['tcp']['per_process'][process]['sent_bytes'] += size
            
            # TCP receive events
            elif event_name == 'tcp_recvmsg':
                # Try different field names for size
                size = safe_parse_size(details.get('len', details.get('size', 0)))
                
                # Skip if size is 0 or unreasonable
                if size <= 0:
                    continue
                    
                # Create a unique identifier for this packet to avoid double counting
                packet_id = (timestamp, socket_fd, size, 'tcp_recv')
                if packet_id in processed_packets:
                    continue
                    
                processed_packets.add(packet_id)
                
                data_transfer['tcp']['received_bytes'] += size
                data_transfer['total']['received_bytes'] += size
                
                # Track per destination
                daddr = details.get('daddr', 'unknown')
                if daddr != 'unknown':
                    data_transfer['tcp']['per_destination'][daddr]['received_bytes'] += size
                
                # Track per process
                data_transfer['tcp']['per_process'][process]['received_bytes'] += size
            
            # UDP send events
            elif event_name == 'udp_sendmsg':
                # Try different field names for size
                size = safe_parse_size(details.get('len', details.get('size', 0)))
                
                # Skip if size is 0 or unreasonable
                if size <= 0:
                    continue
                    
                # Create a unique identifier for this packet to avoid double counting
                packet_id = (timestamp, socket_fd, size, 'udp_send')
                if packet_id in processed_packets:
                    continue
                    
                processed_packets.add(packet_id)
                
                data_transfer['udp']['sent_bytes'] += size
                data_transfer['total']['sent_bytes'] += size
                
                # Track per destination
                daddr = details.get('daddr', 'unknown')
                if daddr != 'unknown':
                    data_transfer['udp']['per_destination'][daddr]['sent_bytes'] += size
                
                # Track per process
                data_transfer['udp']['per_process'][process]['sent_bytes'] += size
            
            # UDP receive events
            elif event_name == 'udp_recvmsg':
                # Try different field names for size
                size = safe_parse_size(details.get('len', details.get('size', 0)))
                
                # Skip if size is 0 or unreasonable
                if size <= 0:
                    continue
                    
                # Create a unique identifier for this packet to avoid double counting
                packet_id = (timestamp, socket_fd, size, 'udp_recv')
                if packet_id in processed_packets:
                    continue
                    
                processed_packets.add(packet_id)
                
                data_transfer['udp']['received_bytes'] += size
                data_transfer['total']['received_bytes'] += size
                
                # Track per destination
                daddr = details.get('daddr', 'unknown')
                if daddr != 'unknown':
                    data_transfer['udp']['per_destination'][daddr]['received_bytes'] += size
                
                # Track per process
                data_transfer['udp']['per_process'][process]['received_bytes'] += size
        
        # Convert bytes to megabytes for easier reading
        bytes_to_mb = lambda b: round(b / (1024 * 1024), 2)
        
        # Calculate MB values
        data_transfer['tcp']['sent_mb'] = bytes_to_mb(data_transfer['tcp']['sent_bytes'])
        data_transfer['tcp']['received_mb'] = bytes_to_mb(data_transfer['tcp']['received_bytes'])
        data_transfer['tcp']['total_mb'] = bytes_to_mb(data_transfer['tcp']['sent_bytes'] + data_transfer['tcp']['received_bytes'])
        
        data_transfer['udp']['sent_mb'] = bytes_to_mb(data_transfer['udp']['sent_bytes'])
        data_transfer['udp']['received_mb'] = bytes_to_mb(data_transfer['udp']['received_bytes'])
        data_transfer['udp']['total_mb'] = bytes_to_mb(data_transfer['udp']['sent_bytes'] + data_transfer['udp']['received_bytes'])
        
        data_transfer['total']['sent_mb'] = bytes_to_mb(data_transfer['total']['sent_bytes'])
        data_transfer['total']['received_mb'] = bytes_to_mb(data_transfer['total']['received_bytes'])
        data_transfer['total']['total_mb'] = bytes_to_mb(data_transfer['total']['sent_bytes'] + data_transfer['total']['received_bytes'])
        
        # Convert defaultdicts to regular dicts for JSON serialization
        data_transfer['tcp']['per_destination'] = dict(data_transfer['tcp']['per_destination'])
        data_transfer['tcp']['per_process'] = dict(data_transfer['tcp']['per_process'])
        data_transfer['udp']['per_destination'] = dict(data_transfer['udp']['per_destination'])
        data_transfer['udp']['per_process'] = dict(data_transfer['udp']['per_process'])
        
        # Sort destinations by total data transferred
        tcp_destinations = data_transfer['tcp']['per_destination']
        for dest in tcp_destinations:
            tcp_destinations[dest]['total_bytes'] = tcp_destinations[dest]['sent_bytes'] + tcp_destinations[dest]['received_bytes']
            tcp_destinations[dest]['total_mb'] = bytes_to_mb(tcp_destinations[dest]['total_bytes'])
        
        udp_destinations = data_transfer['udp']['per_destination']
        for dest in udp_destinations:
            udp_destinations[dest]['total_bytes'] = udp_destinations[dest]['sent_bytes'] + udp_destinations[dest]['received_bytes']
            udp_destinations[dest]['total_mb'] = bytes_to_mb(udp_destinations[dest]['total_bytes'])
        
        # Add metadata about the analysis
        data_transfer['metadata'] = {
            'unique_packets': len(processed_packets),
            'analysis_method': 'Packet-level deduplication with size validation'
        }
        
        return data_transfer
    
    def _analyze_sensitive_data(self, events):
        """Analyze potential sensitive data access using device ID + inode matching"""
        try:
            # Load device categories from cat2devs.txt (unified mapping file)
            cat2devs_file = self.config.MAPPINGS_DIR / 'cat2devs.txt'
            if not cat2devs_file.exists():
                self.logger.debug("cat2devs.txt not found, using fallback analysis")
                return self._fallback_sensitive_analysis(events)
            
            with open(cat2devs_file, 'r') as f:
                category_mapping = json.load(f)
                
            # Extract sensitive categories for analysis
            sensitive_resources = {}
            sensitive_categories = ['contacts', 'sms', 'calendar', 'callogger']
            for category in sensitive_categories:
                if category in category_mapping:
                    sensitive_resources[category] = category_mapping[category]
            
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
            
            # 5. Data Transfer Chart (MB) - using the original key for backward compatibility
            data_transfer_chart = self._create_data_transfer_chart(events)
            charts['data_transfer'] = data_transfer_chart
            charts['data_transfer_mb'] = data_transfer_chart  # Also add with new key
            
            # 6. Protocol Socket Type Distribution Chart - using the original key for backward compatibility
            socket_chart = self._create_socket_type_chart(events)
            charts['socket_types'] = socket_chart
            charts['protocol_socket_types'] = socket_chart  # Also add with new key
            
            # 7. Process Activity Chart
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
            
            # Load device categories from cat2devs.txt (unified mapping file)
            try:
                cat2devs_file = self.config.MAPPINGS_DIR / 'cat2devs.txt'
                if cat2devs_file.exists():
                    with open(cat2devs_file, 'r') as f:
                        category_mapping = json.load(f)
                    
                    # Extract sensitive categories for analysis
                    sensitive_resources = {}
                    sensitive_categories = ['contacts', 'sms', 'calendar', 'callogger']
                    for category in sensitive_categories:
                        if category in category_mapping:
                            sensitive_resources[category] = category_mapping[category]
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
                            # Only add categories that are in our defined event types
                            if cat in event_types and cat not in cats_window:
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
            # Define event types without "other" category
            event_types = ["camera", "audio_in", "TCP", "bluetooth", "nfc", "gnss", "contacts", "sms", "calendar", "call_logs"]
            
            N = len(cats2windows)
            
            for i, ev_list in enumerate(cats2windows):
                for ev in ev_list:
                    # Skip if the event is not in our defined event types or not a TCP event
                    if not (ev in event_types or ev.startswith("TCP_")):
                        continue
                        
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
                    
                    # Determine y-position for the event
                    if "TCP" in ev:
                        y_pos = event_types.index("TCP")
                    else:
                        y_pos = event_types.index(ev_type)
                    
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
            ax.set_title(f"Key Behavior Timeline (PID {target_pid})", fontsize=14)
            
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
        """Create network activity chart with TCP state transitions"""
        try:
            # Use the same criteria as _analyze_network_events to find network events
            network_events = [e for e in events if 'inet' in e.get('event', '') or 'sock' in e.get('event', '') or 'tcp' in e.get('event', '').lower() or 'udp' in e.get('event', '').lower()]
            
            if not network_events:
                return None
            
            # Create a figure for TCP state transitions
            plt.figure(figsize=(10, 6))
            
            # TCP State Transitions
            tcp_states = defaultdict(int)
            for event in network_events:
                if event.get('event') == 'inet_sock_set_state' and 'details' in event:
                    state = event['details'].get('newstate', 'unknown')
                    tcp_states[state] += 1
            
            if tcp_states:
                states = list(tcp_states.keys())
                counts = list(tcp_states.values())
                
                plt.bar(states, counts, color='#17a2b8')
                plt.xlabel('TCP State')
                plt.ylabel('Transition Count')
                plt.title('TCP State Transitions')
                plt.xticks(rotation=45)
            else:
                plt.text(0.5, 0.5, 'No TCP state transitions detected', 
                        horizontalalignment='center', verticalalignment='center',
                        transform=plt.gca().transAxes)
            
            plt.tight_layout()
            
            return self._plot_to_base64()
            
        except Exception as e:
            self.logger.error(f"Error creating network chart: {str(e)}")
            return None
            
    def _create_data_transfer_chart(self, events):
        """Create data transfer chart showing MB transferred by protocol and process"""
        try:
            # Get data transfer information
            data_transfer = self._analyze_data_transfer(events)
            
            # Create a basic chart even if there's no data
            if not data_transfer or not isinstance(data_transfer, dict):
                data_transfer = {
                    'tcp': {'sent_mb': 0.001, 'received_mb': 0.001},
                    'udp': {'sent_mb': 0.001, 'received_mb': 0.001},
                    'total': {'sent_mb': 0.002, 'received_mb': 0.002}
                }
            
            # Create a figure with two subplots - one for protocol summary, one for per-process details
            fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(16, 8), gridspec_kw={'width_ratios': [1, 1.5]})
            
            # First subplot: Data Transfer by Protocol
            protocols = ['TCP', 'UDP', 'Total']
            
            # Ensure we have values, defaulting to 0.001 if not available (for visibility)
            tcp_sent = data_transfer.get('tcp', {}).get('sent_mb', 0.001)
            tcp_received = data_transfer.get('tcp', {}).get('received_mb', 0.001)
            udp_sent = data_transfer.get('udp', {}).get('sent_mb', 0.001)
            udp_received = data_transfer.get('udp', {}).get('received_mb', 0.001)
            total_sent = data_transfer.get('total', {}).get('sent_mb', 0.002)
            total_received = data_transfer.get('total', {}).get('received_mb', 0.002)
            
            sent = [tcp_sent, udp_sent, total_sent]
            received = [tcp_received, udp_received, total_received]
            
            # Ensure we have some data to display
            if max(sent + received) < 0.001:
                sent = [0.001, 0.001, 0.002]
                received = [0.001, 0.001, 0.002]
            
            x = np.arange(len(protocols))
            width = 0.35
            
            ax1.bar(x - width/2, sent, width, label='Sent (MB)', color='#28a745')
            ax1.bar(x + width/2, received, width, label='Received (MB)', color='#007bff')
            
            ax1.set_xlabel('Protocol')
            ax1.set_ylabel('Data Transfer (MB)')
            ax1.set_title('Data Transfer by Protocol')
            ax1.set_xticks(x)
            ax1.set_xticklabels(protocols)
            ax1.legend()
            
            # Add value labels on bars
            for i, v in enumerate(sent):
                if v >= 0.01:  # Only show if value is significant
                    ax1.text(i - width/2, v + 0.01, f'{v:.2f}', ha='center', fontsize=9)
            for i, v in enumerate(received):
                if v >= 0.01:  # Only show if value is significant
                    ax1.text(i + width/2, v + 0.01, f'{v:.2f}', ha='center', fontsize=9)
                    
            # Add a note if values are very small
            if max(sent + received) < 0.01:
                ax1.text(0.5, 0.5, 'Minimal data transfer detected', 
                        horizontalalignment='center', verticalalignment='center',
                        transform=ax1.transAxes, alpha=0.7)
            
            # Second subplot: Data Transfer by Process
            # Get per-process data with fallbacks for missing data
            tcp_processes = data_transfer.get('tcp', {}).get('per_process', {})
            udp_processes = data_transfer.get('udp', {}).get('per_process', {})
            
            # If no process data, create some placeholder data
            if not tcp_processes and not udp_processes:
                tcp_processes = {'process1': {'sent_bytes': 1024, 'received_bytes': 1024}}
                udp_processes = {'process2': {'sent_bytes': 1024, 'received_bytes': 1024}}
            
            # Combine all processes
            all_processes = set(tcp_processes.keys()) | set(udp_processes.keys())
            
            # Convert to MB and create data for plotting
            bytes_to_mb = lambda b: round(b / (1024 * 1024), 2)
            
            process_data = []
            for process in all_processes:
                tcp_sent = bytes_to_mb(tcp_processes.get(process, {}).get('sent_bytes', 0))
                tcp_recv = bytes_to_mb(tcp_processes.get(process, {}).get('received_bytes', 0))
                udp_sent = bytes_to_mb(udp_processes.get(process, {}).get('sent_bytes', 0))
                udp_recv = bytes_to_mb(udp_processes.get(process, {}).get('received_bytes', 0))
                total_mb = tcp_sent + tcp_recv + udp_sent + udp_recv
                
                # Include all processes, using minimal values if needed
                process_data.append({
                    'process': process,
                    'tcp_sent': max(0.001, tcp_sent),
                    'tcp_recv': max(0.001, tcp_recv),
                    'udp_sent': max(0.001, udp_sent),
                    'udp_recv': max(0.001, udp_recv),
                    'total': max(0.004, total_mb)
                })
            
            # Sort by total data transfer
            process_data.sort(key=lambda x: x['total'], reverse=True)
            
            # Limit to top 10 processes for readability
            process_data = process_data[:10]
            
            # Ensure we have at least one process
            if not process_data:
                process_data = [{
                    'process': 'example_process',
                    'tcp_sent': 0.001,
                    'tcp_recv': 0.001,
                    'udp_sent': 0.001,
                    'udp_recv': 0.001,
                    'total': 0.004
                }]
            
            # Create a table for per-process data
            cell_text = []
            for p in process_data:
                cell_text.append([
                    p['process'],
                    f"{p['tcp_sent']:.2f}",
                    f"{p['tcp_recv']:.2f}",
                    f"{p['udp_sent']:.2f}",
                    f"{p['udp_recv']:.2f}",
                    f"{p['total']:.2f}"
                ])
            
            # Add a row for totals
            total_tcp_sent = sum(p['tcp_sent'] for p in process_data)
            total_tcp_recv = sum(p['tcp_recv'] for p in process_data)
            total_udp_sent = sum(p['udp_sent'] for p in process_data)
            total_udp_recv = sum(p['udp_recv'] for p in process_data)
            total_all = sum(p['total'] for p in process_data)
            
            cell_text.append([
                'TOTAL',
                f"{total_tcp_sent:.2f}",
                f"{total_tcp_recv:.2f}",
                f"{total_udp_sent:.2f}",
                f"{total_udp_recv:.2f}",
                f"{total_all:.2f}"
            ])
            
            # Create table
            column_labels = ['Process', 'TCP Send', 'TCP Recv', 'UDP Send', 'UDP Recv', 'Total MB']
            ax2.axis('tight')
            ax2.axis('off')
            table = ax2.table(
                cellText=cell_text,
                colLabels=column_labels,
                loc='center',
                cellLoc='center'
            )
            
            # Style the table
            table.auto_set_font_size(False)
            table.set_fontsize(9)
            table.scale(1.2, 1.5)
            
            # Highlight the total row
            for j in range(len(column_labels)):
                table[(len(cell_text), j)].set_facecolor('#f2f2f2')
                table[(len(cell_text), j)].set_text_props(weight='bold')
            
            # Set title
            ax2.set_title('Data Transfer by Process (MB)', pad=20)
            
            plt.tight_layout()
            plt.suptitle('Data Transfer (MB)', fontsize=16, y=1.05)
            
            return self._plot_to_base64()
            
        except Exception as e:
            self.logger.error(f"Error creating data transfer chart: {str(e)}")
            # Create a simple fallback chart
            plt.figure(figsize=(10, 6))
            plt.text(0.5, 0.5, f"Data Transfer Chart (Error: {str(e)})", 
                    horizontalalignment='center', verticalalignment='center',
                    transform=plt.gca().transAxes)
            plt.title("Data Transfer (MB)")
            return self._plot_to_base64()
            
    def _create_socket_type_chart(self, events):
        """Create protocol socket type distribution chart with data transfer metrics"""
        try:
            # Use the same criteria as _analyze_network_events to find network events
            network_events = [e for e in events if 'inet' in e.get('event', '') or 'sock' in e.get('event', '') or 'tcp' in e.get('event', '').lower() or 'udp' in e.get('event', '').lower()]
            
            # If no network events, create some minimal placeholder events
            if not network_events:
                network_events = [{'event': 'tcp_sendmsg', 'details': {'size': 1024}}]
                
            # Extract socket type information directly from network events
            socket_types = self._analyze_socket_types(network_events)
            
            # Always ensure we have at least TCP and UDP entries
            if not socket_types or socket_types['total_sockets'] == 0:
                socket_types = {
                    'total_sockets': 2,
                    'types': {
                        'SOCK_STREAM': {
                            'count': 1,
                            'data_bytes': 1024,
                            'data_mb': 0.001,
                            'description': 'TCP'
                        },
                        'SOCK_DGRAM': {
                            'count': 1,
                            'data_bytes': 1024,
                            'data_mb': 0.001,
                            'description': 'UDP'
                        }
                    }
                }
            
            # Create a figure with two subplots for socket types and protocol details
            fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(16, 8), gridspec_kw={'width_ratios': [1.5, 1]})
            
            # First subplot: Socket Type Distribution with Data Transfer
            socket_labels = []
            socket_counts = []
            socket_data_mb = []
            socket_colors = []
            
            color_map = {
                'SOCK_STREAM': '#4287f5',  # TCP - blue
                'SOCK_DGRAM': '#42f5a7',   # UDP - green
                'SOCK_RAW': '#f54242',     # RAW - red
                'SOCK_SEQPACKET': '#f5a742', # SEQPACKET - orange
                'SOCK_RDM': '#a742f5',     # RDM - purple
                'SOCK_PACKET': '#f542e6',  # PACKET - pink
                'unknown': '#b0b0b0'       # Unknown - gray
            }
            
            # Sort socket types by count
            sorted_types = sorted(socket_types['types'].items(), key=lambda x: x[1]['count'], reverse=True)
            
            if not sorted_types:
                # If still no socket types, create a default entry
                socket_labels = ["SOCK_STREAM (TCP)"]
                socket_counts = [1]  # Minimal count
                socket_data_mb = [0.001]  # Minimal data
                socket_colors = [color_map['SOCK_STREAM']]
            else:
                for socket_type, data in sorted_types:
                    socket_labels.append(f"{socket_type} ({data['description']})")
                    socket_counts.append(max(1, data['count']))  # Ensure at least 1 for visibility
                    socket_data_mb.append(max(0.001, data['data_mb']))  # Ensure some minimal value for visibility
                    socket_colors.append(color_map.get(socket_type, '#b0b0b0'))
            
            # Create horizontal bars for socket counts
            y_pos = np.arange(len(socket_labels))
            ax1.barh(y_pos, socket_counts, color=socket_colors, alpha=0.7)
            
            # Add data transfer annotations
            for i, (count, data_mb) in enumerate(zip(socket_counts, socket_data_mb)):
                if data_mb >= 0.01:  # Only show if significant
                    ax1.text(count + 1, i, f"{data_mb:.2f} MB", va='center')
                else:
                    ax1.text(count + 1, i, "< 0.01 MB", va='center')
            
            ax1.set_yticks(y_pos)
            ax1.set_yticklabels(socket_labels)
            ax1.set_xlabel('Socket Count')
            ax1.set_title('Socket Type Distribution')
            
            # Second subplot: Protocol Data Transfer Details
            # Create a table with detailed protocol information
            protocol_data = []
            
            # Extract protocol information from socket types
            for socket_type, data in socket_types['types'].items():
                # Include all protocols, even with minimal data
                protocol_name = data['description']
                protocol_data.append({
                    'protocol': f"{socket_type} ({protocol_name})",
                    'count': max(1, data.get('count', 1)),
                    'data_mb': max(0.001, data.get('data_mb', 0.001))
                })
            
            # Sort by data transfer amount
            protocol_data.sort(key=lambda x: x['data_mb'], reverse=True)
            
            # Ensure we have at least one protocol
            if not protocol_data:
                protocol_data = [{
                    'protocol': 'SOCK_STREAM (TCP)',
                    'count': 1,
                    'data_mb': 0.001
                }]
            
            # Create a table for protocol data
            cell_text = []
            for p in protocol_data:
                cell_text.append([
                    p['protocol'],
                    f"{p['count']}",
                    f"{p['data_mb']:.2f} MB"
                ])
            
            # Add a row for totals
            total_count = sum(p['count'] for p in protocol_data)
            total_mb = sum(p['data_mb'] for p in protocol_data)
            
            cell_text.append([
                'TOTAL',
                f"{total_count}",
                f"{total_mb:.2f} MB"
            ])
            
            # Create table
            column_labels = ['Protocol', 'Count', 'Data Transfer']
            ax2.axis('tight')
            ax2.axis('off')
            table = ax2.table(
                cellText=cell_text,
                colLabels=column_labels,
                loc='center',
                cellLoc='center'
            )
            
            # Style the table
            table.auto_set_font_size(False)
            table.set_fontsize(9)
            table.scale(1.2, 1.5)
            
            # Highlight the total row
            for j in range(len(column_labels)):
                table[(len(cell_text), j)].set_facecolor('#f2f2f2')
                table[(len(cell_text), j)].set_text_props(weight='bold')
            
            # Set title
            ax2.set_title('Protocol Data Transfer', pad=20)
            
            plt.tight_layout()
            plt.suptitle('Protocol Socket Type Distribution', fontsize=16, y=1.05)
            
            return self._plot_to_base64()
            
        except Exception as e:
            self.logger.error(f"Error creating socket type chart: {str(e)}")
            # Create a simple fallback chart
            plt.figure(figsize=(10, 6))
            plt.text(0.5, 0.5, f"Protocol Socket Type Distribution (Error: {str(e)})", 
                    horizontalalignment='center', verticalalignment='center',
                    transform=plt.gca().transAxes)
            plt.title("Protocol Socket Type Distribution")
            return self._plot_to_base64()
    
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
        """Generate network analysis insights including socket type information"""
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
        
        # Add data transfer insights
        if network_analysis.get('data_transfer'):
            data_transfer = network_analysis['data_transfer']
            
            # Add metadata insight if available
            if data_transfer.get('metadata') and data_transfer['metadata'].get('unique_packets'):
                insights.append({
                    'icon': '📦',
                    'text': f"<strong>{data_transfer['metadata']['unique_packets']}</strong> unique network packets analyzed"
                })
            
            # Total data transfer
            total_mb = data_transfer.get('total', {}).get('total_mb', 0)
            total_sent_mb = data_transfer.get('total', {}).get('sent_mb', 0)
            total_received_mb = data_transfer.get('total', {}).get('received_mb', 0)
            
            if total_mb > 0.01:  # Only show if significant
                insights.append({
                    'icon': '📊',
                    'text': f"Total data transferred: <strong>{total_mb:.2f} MB</strong> " +
                           f"(↑ {total_sent_mb:.2f} MB, ↓ {total_received_mb:.2f} MB)"
                })
            elif total_mb > 0:
                insights.append({
                    'icon': '📊',
                    'text': "Minimal data transfer detected (< 0.01 MB)"
                })
            
            # TCP data transfer
            tcp_total_mb = data_transfer.get('tcp', {}).get('total_mb', 0)
            tcp_sent_mb = data_transfer.get('tcp', {}).get('sent_mb', 0)
            tcp_received_mb = data_transfer.get('tcp', {}).get('received_mb', 0)
            
            if tcp_total_mb > 0.01:  # Only show if significant
                insights.append({
                    'icon': '📡',
                    'text': f"TCP data: <strong>{tcp_total_mb:.2f} MB</strong> " +
                           f"(↑ {tcp_sent_mb:.2f} MB, ↓ {tcp_received_mb:.2f} MB)"
                })
            elif tcp_total_mb > 0:
                insights.append({
                    'icon': '📡',
                    'text': "TCP data: minimal transfer detected (< 0.01 MB)"
                })
            
            # UDP data transfer
            udp_total_mb = data_transfer.get('udp', {}).get('total_mb', 0)
            udp_sent_mb = data_transfer.get('udp', {}).get('sent_mb', 0)
            udp_received_mb = data_transfer.get('udp', {}).get('received_mb', 0)
            
            if udp_total_mb > 0.01:  # Only show if significant
                insights.append({
                    'icon': '📶',
                    'text': f"UDP data: <strong>{udp_total_mb:.2f} MB</strong> " +
                           f"(↑ {udp_sent_mb:.2f} MB, ↓ {udp_received_mb:.2f} MB)"
                })
            elif udp_total_mb > 0:
                insights.append({
                    'icon': '📶',
                    'text': "UDP data: minimal transfer detected (< 0.01 MB)"
                })
            
            # Top destination by data transfer
            tcp_destinations = data_transfer['tcp']['per_destination']
            if tcp_destinations:
                top_tcp_dest = max(tcp_destinations.items(), key=lambda x: x[1]['total_bytes'], default=(None, None))
                if top_tcp_dest[0] and top_tcp_dest[1]['total_mb'] > 0:
                    insights.append({
                        'icon': '🔝',
                        'text': f"Top TCP destination: <strong>{top_tcp_dest[0]}</strong> " +
                               f"({top_tcp_dest[1]['total_mb']:.2f} MB)"
                    })
        
        # Add socket type insights
        socket_types = self._analyze_socket_types(network_analysis.get('_events', []))
        
        # If no socket types detected, try to infer from network events
        if socket_types['total_sockets'] == 0 and network_analysis.get('_events'):
            events = network_analysis.get('_events', [])
            has_tcp = any('tcp' in e.get('event', '').lower() for e in events)
            has_udp = any('udp' in e.get('event', '').lower() for e in events)
            
            if has_tcp:
                socket_types['types']['SOCK_STREAM'] = {
                    'count': sum(1 for e in events if 'tcp' in e.get('event', '').lower()),
                    'data_bytes': sum(self._get_event_size(e) for e in events if 'tcp' in e.get('event', '').lower()),
                    'data_mb': 0.0,
                    'description': 'TCP'
                }
                socket_types['total_sockets'] += 1
            
            if has_udp:
                socket_types['types']['SOCK_DGRAM'] = {
                    'count': sum(1 for e in events if 'udp' in e.get('event', '').lower()),
                    'data_bytes': sum(self._get_event_size(e) for e in events if 'udp' in e.get('event', '').lower()),
                    'data_mb': 0.0,
                    'description': 'UDP'
                }
                socket_types['total_sockets'] += 1
            
            # Calculate MB values
            bytes_to_mb = lambda b: round(b / (1024 * 1024), 2)
            for socket_type in socket_types['types']:
                socket_types['types'][socket_type]['data_mb'] = bytes_to_mb(socket_types['types'][socket_type]['data_bytes'])
        
        # Add insights based on socket types
        if socket_types['types']:
            # Get the most common socket type
            most_common_type = max(socket_types['types'].items(), key=lambda x: x[1]['count'], default=(None, None))
            if most_common_type[0]:
                socket_type, data = most_common_type
                data_mb = data.get('data_mb', 0)
                
                if data_mb > 0.01:
                    insights.append({
                        'icon': '🧩',
                        'text': f"Most used socket type: <strong>{socket_type}</strong> ({data['description']}) - " +
                               f"{data['count']} sockets, {data_mb:.2f} MB transferred"
                    })
                else:
                    insights.append({
                        'icon': '🧩',
                        'text': f"Most used socket type: <strong>{socket_type}</strong> ({data['description']}) - " +
                               f"{data['count']} sockets, minimal data transfer"
                    })
            
            # Add insight about total socket count
            insights.append({
                'icon': '🔌',
                'text': f"<strong>{socket_types['total_sockets']}</strong> total sockets created"
            })
        else:
            # Fallback if no socket types detected
            insights.append({
                'icon': '🔌',
                'text': "Network activity detected but socket types could not be determined"
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
            'socket_operations': [],
            'data_transfer': {
                'tcp': {'sent_bytes': 0, 'received_bytes': 0, 'sent_mb': 0, 'received_mb': 0},
                'udp': {'sent_bytes': 0, 'received_bytes': 0, 'sent_mb': 0, 'received_mb': 0},
                'total': {'sent_bytes': 0, 'received_bytes': 0, 'sent_mb': 0, 'received_mb': 0}
            }
        }
        
        # Process data transfer information
        data_transfer = self._analyze_data_transfer(events)
        network_flows['data_transfer'] = data_transfer
        
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
                
                # Track network flows
                event_name = event.get('event', '')
                details = event.get('details', {})
                
                # Add TCP/UDP flow information
                if event_name in ['tcp_sendmsg', 'tcp_recvmsg']:
                    daddr = details.get('daddr', 'unknown')
                    dport = details.get('dport', 0)
                    size = details.get('size', details.get('len', 0))
                    
                    if daddr != 'unknown' and size:
                        flow = {
                            'timestamp': timestamp,
                            'source': event.get('process', 'unknown'),
                            'destination': daddr,
                            'port': dport,
                            'size_bytes': size,
                            'direction': 'outgoing' if event_name == 'tcp_sendmsg' else 'incoming'
                        }
                        network_flows['tcp_flows'].append(flow)
                
                elif event_name in ['udp_sendmsg', 'udp_recvmsg']:
                    daddr = details.get('daddr', 'unknown')
                    dport = details.get('dport', 0)
                    size = details.get('len', 0)
                    
                    if daddr != 'unknown' and size:
                        flow = {
                            'timestamp': timestamp,
                            'source': event.get('process', 'unknown'),
                            'destination': daddr,
                            'port': dport,
                            'size_bytes': size,
                            'direction': 'outgoing' if event_name == 'udp_sendmsg' else 'incoming'
                        }
                        network_flows['udp_flows'].append(flow)
        
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
