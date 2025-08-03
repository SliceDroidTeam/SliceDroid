from collections import Counter, defaultdict
import json
import numpy as np
from ..utils import get_device_identifier
from . import get_logger
from .utils import check_sensitive_resource, categorize_event

class DescriptivesAnalyser:
    def __init__(self, config_class):
        self.logger = get_logger("DescriptivesAnalyser")
        self.config = config_class
    
    def analyze_time_range(self, events):
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
    
    def analyze_processes(self, events):
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
            'pid_distribution': {str(k): v for k, v in pid_counts.most_common(10)},
            'pid_to_process_map': {str(k): v for k, v in pid_to_process.items()},
            'unique_processes': len(process_counts),
            'unique_pids': len(pid_counts)
        }
    

    def analyze_devices(self, events):
        """Analyze device usage patterns"""
        device_counts = defaultdict(int)
        device_paths = defaultdict(set)
        device_categories = defaultdict(int)
        
        # Load device category mappings
        try:
            cat2devs_file = self.config.MAPPINGS_DIR / 'cat2devs.txt'
            if cat2devs_file.exists():
                with open(cat2devs_file, 'r') as f:
                    try:
                        cat2devs = json.load(f)
                    except json.JSONDecodeError:
                        cat2devs = {}
                dev2cat = {}
                for cat, devs in cat2devs.items():
                    for dev in devs:
                        # Store both int and str versions for flexible lookup
                        dev2cat[dev] = cat
                        dev2cat[str(dev)] = cat
            else:
                dev2cat = {}
        except:
            dev2cat = {}
        
        for event in events:
            if 'details' in event:
                # Get device identifier - use stdev+inode for regular files, kdev for device nodes
                device_id = get_device_identifier(event)
                if device_id:
                    device_counts[device_id] += 1
                    
                    # Track paths
                    if 'pathname' in event['details'] and event['details']['pathname']:
                        device_paths[device_id].add(event['details']['pathname'])
                    
                    # Categorize device
                    if device_id in dev2cat:
                        device_categories[dev2cat[device_id]] += 1
        
        # Convert sets to lists and ensure string keys for JSON serialization
        device_paths_dict = {str(k): list(v) for k, v in device_paths.items()}
        
        return {
            'device_usage': {str(k): v for k, v in sorted(device_counts.items(), key=lambda x: (x[1], str(x[0])), reverse=True)[:20]},
            'device_paths': device_paths_dict,
            'category_usage': dict(device_categories),
            'unique_devices': len(device_counts),
            'total_device_events': sum(device_counts.values())
        }
    
    def _calculate_read_write_ratio(self, category_counts):
        """Calculate read/write ratio"""
        reads = category_counts.get('read', 0)
        writes = category_counts.get('write', 0)
        
        if writes == 0:
            return float('inf') if reads > 0 else 0
        
        return reads / writes
    
    def analyze_categories(self, events):
        """Analyze event categories"""
        category_counts = defaultdict(int)
        event_type_counts = Counter()
        
        for event in events:
            event_type = event.get('event', 'unknown')
            event_type_counts[event_type] += 1
            
            # Categorize event
            category = categorize_event(event_type)
            category_counts[category] += 1
        
        return {
            'category_distribution': dict(category_counts),
            'event_type_distribution': dict(event_type_counts.most_common(15)),
            'read_write_ratio': self._calculate_read_write_ratio(category_counts),
            'io_patterns': self._analyze_io_patterns(events)
        }
    
    def _fallback_sensitive_analysis(self, events):
        """Fallback analysis using only specific pathname patterns to avoid false positives"""
        # More conservative patterns to reduce false positives
        sensitive_patterns = {
            'contacts': ['contacts2.db', 'contacts.db', 'people.db', 'com.android.contacts'],
            'sms': ['mmssms.db', 'sms.db', 'telephony.db', 'com.android.providers.telephony'],
            'calendar': ['calendar.db', 'calendarconfig.db', 'com.android.providers.calendar'],
            'call_logs': ['calllog.db', 'calls.db', 'call_log.db'],
        }
        
        sensitive_access = defaultdict(int)
        
        for event in events:
            # Only check file access events to avoid counting unrelated events
            if (event.get('event', '') in ['read_probe', 'write_probe', 'ioctl_probe'] and 
                'details' in event and 'pathname' in event['details']):
                pathname = event['details']['pathname'].lower()
                for category, patterns in sensitive_patterns.items():
                    # Use stricter matching - require exact database file names or provider URIs
                    if any(pattern in pathname for pattern in patterns):
                        self.logger.debug(f"Fallback detection: {category} access via pathname {pathname}")
                        sensitive_access[category] += 1
                        break  # Only count once per event
        
        return {
            'sensitive_data_access': dict(sensitive_access),
            'total_sensitive_events': sum(sensitive_access.values())
        }
    
        
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
    

    def analyze_sensitive_data(self, events):
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
                    sensitive_type = check_sensitive_resource(event, sensitive_resources, self.logger)
                    if sensitive_type:
                        sensitive_access[sensitive_type] += 1
            
            # Log detection results for verification
            self.logger.info(f"Sensitive data detection results:")
            for data_type, count in sensitive_access.items():
                if count > 0:
                    self.logger.info(f"  {data_type}: {count} events detected")
                else:
                    self.logger.debug(f"  {data_type}: No events detected")
            
            # Fallback to pathname patterns for additional categories
            self._add_pathname_based_detection(events, sensitive_access)
            
            return {
                'sensitive_data_access': dict(sensitive_access),
                'total_sensitive_events': sum(sensitive_access.values())
            }
            
        except Exception as e:
            self.logger.error(f"Error in sensitive data analysis: {str(e)}")
            return self._fallback_sensitive_analysis(events)
        
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


    def analyze_temporal_patterns(self, events, target_pid):
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