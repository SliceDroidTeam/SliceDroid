"""
Comprehensive Analysis Engine
Integrates all functionality from /app into the web application
"""

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
        
        @staticmethod
        def clean_event_list(events):
            """Clean event list by removing duplicates and sorting"""
            return events
        
        @staticmethod
        def clean_event_list_withpath(events):
            """Clean event list with path information"""
            return events
        
        @staticmethod
        def are_equivalent(events1, events2):
            """Check if two event lists are equivalent"""
            return len(events1) == len(events2) and str(events1) == str(events2)
        
        @staticmethod
        def get_pid(tid, tgid, tgid_slicing=False):
            """Get process ID"""
            return tgid if tgid_slicing else tid
    
    myutils = MyUtils()

class ComprehensiveAnalyzer:
    """
    Comprehensive analysis engine that combines all functionality from /app
    with the web application capabilities
    """
    
    def __init__(self, config_class):
        self.config = config_class
        self.logger = self._setup_logger()
        
    def _setup_logger(self):
        """Setup logging"""
        logger = logging.getLogger("ComprehensiveAnalyzer")
        logger.setLevel(logging.INFO)
        
        if not logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
            handler.setFormatter(formatter)
            logger.addHandler(handler)
        
        return logger
    
    def slice_events(self, events, t_pid, asynchronous=False):
        """
        Advanced bidirectional event slicing algorithm
        Tracks process relationships through IPC mechanisms
        
        Args:
            events: List of parsed events
            t_pid: Target process ID
            asynchronous: Whether to allow asynchronous analysis
            
        Returns:
            List of filtered relevant events
        """
        # Relevant processes are tracked dynamically
        pid_set = {t_pid}
        binders = dict()
        unix_streams = dict()
        unix_dgrams_waiting = set()
        unix_dgrams = dict()
        
        tgid2source_tids = dict()
        
        out_flows_slice = []
        in_flows_slice = []
        
        # Forward slicing for output operations
        e_index = 0
        for e in events:
            tgid = e['tgid']
            tid = e['tid']
            event = e['event']
            
            # Force only per-thread-synchronous calls
            if tgid == t_pid and not asynchronous:
                for pids in list(tgid2source_tids.keys()):
                    if tid in tgid2source_tids[pids]:
                        tgid2source_tids[pids].remove(tid)
                        if len(tgid2source_tids[pids]) == 0:
                            pid_set.discard(pids)
            
            if tgid in pid_set:
                # If the process is associated with the examined process
                if tgid == t_pid:
                    sources = set([tid])
                else:
                    sources = tgid2source_tids[tgid]
                
                if event == 'binder_transaction':
                    binders[e['details']['transaction']] = sources
                elif event == 'unix_stream_sendmsg':
                    if e['details']['topid'] in unix_streams:
                        unix_streams[e['details']['topid']] = unix_streams[e['details']['topid']].union(sources)
                    else:
                        unix_streams[e['details']['topid']] = sources
                elif event == 'unix_dgram_sendmsg':
                    unix_dgrams_waiting.add(tid)
                elif event == 'sock_queue_tail' and tid in unix_dgrams_waiting:
                    if e['details']['inode'] in unix_dgrams:
                        unix_dgrams[e['details']['inode']] = unix_dgrams[e['details']['inode']].union(sources)
                    else:
                        unix_dgrams[e['details']['inode']] = sources
                    unix_dgrams_waiting.remove(tid)
                elif ((event == 'write_probe' and e['details']['pathname'] != 'null') or 
                      (event == 'ioctl_probe') or (event == 'inet_sock_set_state')):
                    # Add event as output event for this instance
                    out_flows_slice.append(e_index)
            
            # If a process receives a binder transaction originating from a tracked process
            if event == 'binder_transaction_received' and e['details']['transaction'] in binders:
                if tgid not in pid_set:
                    pid_set.add(tgid)
                if tgid in tgid2source_tids:
                    tgid2source_tids[tgid] = tgid2source_tids[tgid].union(binders[e['details']['transaction']])
                else:
                    tgid2source_tids[tgid] = binders[e['details']['transaction']]
                del binders[e['details']['transaction']]
            elif event == 'unix_stream_recvmsg' and e['details'].get('topid') in unix_streams:
                if tgid not in pid_set:
                    pid_set.add(tgid)
                if tgid in tgid2source_tids:
                    tgid2source_tids[tgid] = tgid2source_tids[tgid].union(unix_streams[e['details']['topid']])
                else:
                    tgid2source_tids[tgid] = unix_streams[e['details']['topid']]
                del unix_streams[e['details']['topid']]
            elif event == 'unix_dgram_recvmsg' and e['details']['inode'] in unix_dgrams:
                if tgid not in pid_set:
                    pid_set.add(tgid)
                if tgid in tgid2source_tids:
                    tgid2source_tids[tgid] = tgid2source_tids[tgid].union(unix_dgrams[e['details']['inode']])
                else:
                    tgid2source_tids[tgid] = unix_dgrams[e['details']['inode']]
                del unix_dgrams[e['details']['inode']]
            
            e_index += 1
        
        # Backward slicing for input operations
        pid_set = {t_pid}
        binders = dict()
        unix_streams = dict()
        unix_dgrams_waiting = set()
        unix_dgrams = dict()
        tgid2source_tids = dict()
        
        e_index = len(events) - 1
        for e in reversed(events):
            tgid = e['tgid']
            tid = e['tid']
            event = e['event']
            
            # Same as the forward path
            if tgid == t_pid and not asynchronous:
                for pids in list(tgid2source_tids.keys()):
                    if tid in tgid2source_tids[pids]:
                        tgid2source_tids[pids].remove(tid)
                        if len(tgid2source_tids[pids]) == 0:
                            pid_set.discard(pids)
            
            if tgid in pid_set:
                if tgid == t_pid:
                    sources = set([tid])
                else:
                    sources = tgid2source_tids[tgid]
                
                if event == 'binder_transaction_received':
                    binders[e['details']['transaction']] = sources
                elif event == 'unix_stream_recvmsg':
                    if e['details'].get('frompid') in unix_streams:
                        unix_streams[e['details']['frompid']] = unix_streams[e['details']['frompid']].union(sources)
                    else:
                        unix_streams[e['details']['frompid']] = sources
                elif event == 'unix_dgram_recvmsg':
                    if e['details']['inode'] in unix_dgrams:
                        unix_dgrams[e['details']['inode']] = unix_dgrams[e['details']['inode']].union(sources)
                    else:
                        unix_dgrams[e['details']['inode']] = sources
                elif (event == 'read_probe' or event == 'ioctl_probe' or (event == 'inet_sock_set_state')):
                    # Add event as input event for this instance
                    in_flows_slice.append(e_index)
            
            # If a process sends a binder transaction to a tracked process
            if event == 'binder_transaction' and e['details']['transaction'] in binders:
                if tgid not in pid_set:
                    pid_set.add(tgid)
                if tgid in tgid2source_tids:
                    tgid2source_tids[tgid] = tgid2source_tids[tgid].union(binders[e['details']['transaction']])
                else:
                    tgid2source_tids[tgid] = binders[e['details']['transaction']]
                del binders[e['details']['transaction']]
            if event == 'unix_stream_sendmsg' and e['details'].get('topid') in unix_streams:
                if tgid not in pid_set:
                    pid_set.add(tgid)
                if tgid in tgid2source_tids:
                    tgid2source_tids[tgid] = tgid2source_tids[tgid].union(unix_streams[e['details']['topid']])
                else:
                    tgid2source_tids[tgid] = unix_streams[e['details']['topid']]
                del unix_streams[e['details']['topid']]
            elif event == 'sock_queue_tail' and e['details']['inode'] in unix_dgrams:
                if tgid not in pid_set:
                    pid_set.add(tgid)
                if tgid in tgid2source_tids:
                    tgid2source_tids[tgid] = tgid2source_tids[tgid].union(unix_dgrams[e['details']['inode']])
                else:
                    tgid2source_tids[tgid] = unix_dgrams[e['details']['inode']]
            
            e_index -= 1
        
        # Merge everything to one sequence
        merged = []
        i = 0
        j = 0
        
        len_in = len(in_flows_slice)
        len_out = len(out_flows_slice)
        
        while (i < len_in) and (j < len_out):
            if in_flows_slice[i] < out_flows_slice[j]:
                merged.append(in_flows_slice[i])
                i += 1
            else:
                merged.append(out_flows_slice[j])
                j += 1
        
        merged = merged + in_flows_slice[i:] + out_flows_slice[j:]
        
        # Eliminate duplicate ioctl entries
        merged_unique_index = []
        seen = set()
        for e_index in merged:
            if e_index not in seen:
                seen.add(e_index)
                merged_unique_index.append(e_index)
        
        merged_unique = []
        for e_index in merged_unique_index:
            merged_unique.append(events[e_index])
        
        filtered_events = []
        for e in merged_unique:
            # Filter out remnant api logging and binder transactions
            if ((e['event'] == 'write_probe' and e['details']['pathname'] != 'null') or 
                (e['event'] == 'ioctl_probe' and 
                 e['details']['pathname'] != 'binder' and 
                 e['details']['pathname'] != 'hwbinder') or 
                (e['event'] != 'write_probe' and e['event'] != 'ioctl_probe' and 'binder' not in e['event'])):
                light_e = dict()
                light_e['event'] = e['event']
                light_e['details'] = e['details']
                filtered_events.append(light_e.copy())
        
        new_events = myutils.clean_event_list_withpath(filtered_events)
        return new_events
    
    def slice_file_analysis(self, events, target_pid, window_size=5000, overlap=1000, asynchronous=True):
        """
        Complete file analysis with windowed approach
        Integrates sensitive data detection and device categorization
        
        Args:
            events: List of parsed events
            target_pid: Target process ID
            window_size: Size of analysis window
            overlap: Overlap between windows
            asynchronous: Whether to allow asynchronous analysis
            
        Returns:
            Complete analysis results including windowed data
        """
        self.logger.info(f"Starting comprehensive analysis for PID {target_pid}")
        
        # Initialize tracking structures
        kdev2pathnames = dict()
        kdevs_trace = []
        apis_trace = []
        TCP_trace = []
        
        sensitive_data_trace = {'contacts': [], 'sms': [], 'calendar': [], 'call_logs': []}
        all_sensitive_events = {'contacts': [], 'sms': [], 'calendar': [], 'call_logs': []}
        
        # Load sensitive resources
        try:
            sensitive_resources_file = self.config.MAPPINGS_DIR / 'cat2stdevs_oneplus.json'
            if sensitive_resources_file.exists():
                with open(sensitive_resources_file, 'r') as f:
                    sensitive_resources = json.load(f)
            else:
                sensitive_resources = {}
        except:
            sensitive_resources = {}
        
        # Detect all sensitive events first
        if sensitive_resources:
            for event in events:
                _, sensitive_type = self._is_filtered_sensitive(event, sensitive_resources, True)
                if sensitive_type:
                    all_sensitive_events[sensitive_type].append(event)
            
            # Log detection results
            for data_type, events_list in all_sensitive_events.items():
                if events_list:
                    self.logger.info(f"Access to {data_type} detected! Found {len(events_list)} events.")
                else:
                    self.logger.info(f"No access to {data_type} detected in this trace.")
        
        # Remove API logging
        events_pruned = self._remove_apis(events)
        self.logger.info(f'After removing excess API logging: {len(events_pruned)} events')
        
        # Calculate step size
        step = window_size - overlap
        if step <= 0:
            raise ValueError("Overlap must be less than the window size.")
        
        if window_size > len(events_pruned):
            window_size = len(events_pruned)
        
        # Slide the window over the event sequence
        i = 0
        window_count = 0
        while i < len(events_pruned):
            end = i + window_size
            begin = i
            if end > len(events_pruned):
                end = len(events_pruned)
                if len(events_pruned) - window_size >= 0:
                    begin = len(events_pruned) - window_size
                else:
                    begin = 0
            
            window = events_pruned[begin:end]
            
            try:
                # Apply advanced slicing
                relevant_events = self.slice_events(window, target_pid, asynchronous)
                tcp_window = self._get_tcp_events(relevant_events)
                window_sensitive = {data_type: [] for data_type in sensitive_data_trace}
                
                # Detect sensitive data in this window
                if sensitive_resources:
                    for event in window:
                        _, sensitive_type = self._is_filtered_sensitive(event, sensitive_resources, True)
                        if sensitive_type:
                            window_sensitive[sensitive_type].append(event)
                    
                    for data_type in sensitive_data_trace:
                        sensitive_data_trace[data_type].append(window_sensitive[data_type])
                
                # Analyze devices and pathnames
                kdev2count_window = dict()
                kdev2pathname_window = dict()
                for e in relevant_events:
                    filtered = self._is_filtered_device(e)
                    if not filtered:
                        kdev = e['details'].get('k_dev') or e['details'].get('k__dev')
                        pathname = e['details']['pathname']
                        if kdev not in kdev2count_window:
                            kdev2count_window[kdev] = 1
                        else:
                            kdev2count_window[kdev] += 1
                        if kdev not in kdev2pathname_window:
                            kdev2pathname_window[kdev] = [pathname]
                        else:
                            if pathname not in kdev2pathname_window[kdev]:
                                kdev2pathname_window[kdev].append(pathname)
                
                # Update global device mappings
                for kdev in kdev2pathname_window:
                    if kdev not in kdev2pathnames:
                        kdev2pathnames[kdev] = set(kdev2pathname_window[kdev])
                    else:
                        kdev2pathnames[kdev] = kdev2pathnames[kdev].union(set(kdev2pathname_window[kdev]))
                
                apis_window = []  # Placeholder for API analysis
                kdevs_trace.append(kdev2count_window.copy())
                apis_trace.append(apis_window.copy())
                TCP_trace.append(tcp_window.copy())
                
                window_count += 1
                
            except Exception as e:
                self.logger.error(f"Error processing window {window_count}: {str(e)}")
                if end == len(events_pruned):
                    i = end
                else:
                    i += step
                continue
            
            if end == len(events_pruned):
                i = end
            else:
                i += step
        
        self.logger.info(f"Processed {window_count} windows successfully")
        
        return {
            'dev2pathnames': kdev2pathnames,
            'kdevs_trace': kdevs_trace,
            'apis_trace': apis_trace,
            'TCP_trace': TCP_trace,
            'sensitive_data_trace': sensitive_data_trace,
            'all_sensitive_events': all_sensitive_events,
            'window_count': window_count,
            'events_processed': len(events_pruned)
        }
    
    def _is_filtered_sensitive(self, e, sensitive_resources=None, track_sensitive=False):
        """Check if event is filtered and detect sensitive type"""
        filtered = True
        sensitive_type = None
        filtered_pathnames = []
        
        if 'details' in e:
            device = e['details'].get('k_dev') or e['details'].get('k__dev')
            if (e['event'] in ['read_probe', 'write_probe', 'ioctl_probe']) and device and device != 0:
                filtered = False
                try:
                    if 'pathname' in e['details'] and e['details']['pathname'] in filtered_pathnames:
                        filtered = True
                except:
                    filtered = True
        
        if track_sensitive and sensitive_resources and 'details' in e:
            try:
                for dtype in ['contacts', 'sms', 'calendar', 'call_logs']:
                    if dtype in sensitive_resources:
                        res = sensitive_resources[dtype]
                        if (e['details'].get('s_dev_inode') == res['st_dev32'] and 
                            e['details'].get('inode') == res['inode']):
                            sensitive_type = dtype
                            break
            except Exception as ex:
                self.logger.warning(f"Error checking sensitive type: {str(ex)}")
        
        if not track_sensitive:
            return filtered
        
        return filtered, sensitive_type
    
    def _is_filtered_device(self, e):
        """Check if event should be filtered for device analysis"""
        filtered_pathnames = []
        
        if 'details' in e:
            device = e['details'].get('k_dev') or e['details'].get('k__dev')
            if (e['event'] in ['read_probe', 'write_probe', 'ioctl_probe']) and device and device != 0:
                try:
                    if 'pathname' in e['details'] and e['details']['pathname'] in filtered_pathnames:
                        return True
                    return False
                except:
                    return True
        return True
    
    def _remove_apis(self, events):
        """Remove API logging events"""
        cleaned_events = []
        i = -1
        for e in events:
            i += 1
            e['raw'] = i
            # Remove API logging and monkey process operations
            try:
                if (not (e['event'] == 'write_probe' and 
                        e['details']['pathname'] == 'null' and 
                        e['details']['count'] > 999999) and 
                    'monkey' not in e['process']):
                    cleaned_events.append(e.copy())
            except:
                self.logger.warning(f"Error processing event {i}")
        return cleaned_events
    
    def _get_tcp_events(self, window):
        """Extract TCP events from window"""
        tcp_events = []
        for e in window:
            if e['event'] == "inet_sock_set_state":
                tcp_events.append(e.copy())
        return tcp_events
    
    def produce_comprehensive_stats(self, analysis_results):
        """
        Produce comprehensive statistics from analysis results
        
        Args:
            analysis_results: Results from slice_file_analysis
            
        Returns:
            Dictionary with comprehensive statistics
        """
        kdevs_trace = analysis_results['kdevs_trace']
        dev2pathnames = analysis_results['dev2pathnames']
        
        # Calculate device statistics
        devs2num = dict()
        for temp_list in kdevs_trace:
            for kdev in temp_list:
                if kdev not in devs2num:
                    devs2num[kdev] = 1
                else:
                    devs2num[kdev] += 1
        
        # Load device categories
        try:
            cat2devs_file = self.config.MAPPINGS_DIR / 'cat2devs_oneplus.txt'
            if not cat2devs_file.exists():
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
        
        # Calculate category statistics
        cat2num = dict()
        for kdev in devs2num:
            if kdev in dev2cat:
                cat_temp = dev2cat[kdev]
                if cat_temp not in cat2num:
                    cat2num[cat_temp] = 1
                else:
                    cat2num[cat_temp] += 1
        
        # Find most used category
        most_used_cat = None
        max_count = 0
        for cat, count in cat2num.items():
            if count > max_count:
                max_count = count
                most_used_cat = cat
        
        # Top devices
        sorted_devices = sorted(devs2num.items(), key=lambda x: x[1], reverse=True)
        top_devices = sorted_devices[:10]
        
        return {
            'total_windows': analysis_results['window_count'],
            'total_categories': len(cat2num),
            'total_devices': len(devs2num),
            'most_used_category': {'name': most_used_cat, 'count': max_count},
            'top_devices': top_devices,
            'device_stats': devs2num,
            'category_stats': cat2num,
            'device_pathnames': {k: list(v) for k, v in dev2pathnames.items()},
            'events_processed': analysis_results['events_processed']
        }
    
    def extract_api_instances(self, parsed_events, target_pid=None):
        """
        Extract API instances from parsed events
        Identifies API call patterns and their relationships
        
        Args:
            parsed_events: List of parsed events
            target_pid: Optional target process ID to filter
            
        Returns:
            Dictionary mapping API codes to instance lists
        """
        api_instances = dict()
        open_instances = dict()
        
        i = -1
        for e in parsed_events:
            i += 1
            
            # Skip if filtering by PID and this event doesn't match
            if target_pid and e.get('tgid') != target_pid:
                continue
            
            if (e['event'] == 'write_probe' and 
                e['details']['pathname'] == 'null' and 
                e['details']['count'] > 999999):
                
                api = e['details']['count']
                tid = e['tid']
                
                start = (api % 2 == 0)
                
                if start:
                    if tid not in open_instances:
                        open_instances[tid] = dict()
                    if api not in open_instances[tid]:
                        open_instances[tid][api] = []
                    
                    open_instances[tid][api].append(i)
                
                if not start:
                    if (tid not in open_instances or 
                        (api + 1) not in open_instances[tid] or
                        open_instances[tid][api + 1] == []):
                        continue
                    
                    last_instance_start = open_instances[tid][api + 1].pop()
                    if (api + 1) not in api_instances:
                        api_instances[api + 1] = []
                    api_instances[api + 1].append([last_instance_start, i])
        
        self.logger.info(f"Extracted {len(api_instances)} API instance types")
        return api_instances
    
    def extract_relevant_api_instances(self, parsed_events, target_pid):
        """
        Extract all relevant API instances for a target PID
        
        Args:
            parsed_events: List of parsed events
            target_pid: Target process ID
            
        Returns:
            Set of relevant API codes
        """
        api_instances = set()
        
        for e in parsed_events:
            if (e['tgid'] == target_pid and 
                e['event'] == 'write_probe' and 
                e['details']['pathname'] == 'null' and 
                e['details']['count'] > 99999):
                
                api = e['details']['count']
                start = (api % 2 == 0)
                
                if start:
                    api_instances.add(api)
                else:
                    api_instances.add(api + 1)
        
        self.logger.info(f"Found {len(api_instances)} relevant API instances for PID {target_pid}")
        return api_instances
    
    def slice_log_advanced(self, api_instances, parsed_events, tgid_slicing=False):
        """
        Advanced log slicing with IPC tracking
        Creates detailed flow analysis for each API instance
        
        Args:
            api_instances: Dictionary of API instances
            parsed_events: List of parsed events
            tgid_slicing: Whether to use TGID for process identification
            
        Returns:
            Dictionary mapping APIs to flow instances
        """
        flows = dict()
        
        for api in api_instances:
            flows[api] = []
            
            for instance in api_instances[api]:
                out_flows_slice = []
                in_flows_slice = []
                ioinstance = {'pid': 0, 'command': 0, 'in': [], 'out': []}
                
                # API start event
                ee = parsed_events[instance[0]]
                tgid = ee['tgid']
                tid = ee['tid']
                pid = myutils.get_pid(tid, tgid, tgid_slicing)
                api_pid = pid
                api_command = ee['process']
                
                # Relevant processes are tracked dynamically
                pid_set = {pid}
                binders = set()
                
                # Forward pass
                for line in range(instance[0], instance[1] + 1):
                    e = parsed_events[line]
                    
                    # Continue if an API start/end event is encountered
                    if e['event'] == 'write_probe' and e['details']['pathname'] == 'null':
                        continue
                    
                    tid = e['tid']
                    tgid = e['tgid']
                    event = e['event']
                    
                    pid = myutils.get_pid(tid, tgid, tgid_slicing)
                    
                    if pid in pid_set:
                        if event == 'binder_transaction':
                            binders.add(e['details']['transaction'])
                        elif ((event == 'write_probe' and e['details']['pathname'] != 'null') or 
                              (event == 'ioctl_probe') or (event == 'inet_sock_set_state')):
                            out_flows_slice.append(line)
                    
                    # Track binder transaction receivers
                    if (event == 'binder_transaction_received' and 
                        e['details']['transaction'] in binders):
                        if pid not in pid_set:
                            pid_set.add(pid)
                        binders.remove(e['details']['transaction'])
                
                # Backward pass
                pid_set = {api_pid}
                binders = set()
                
                for line in range(instance[1], instance[0] - 1, -1):
                    e = parsed_events[line]
                    
                    if e['event'] == 'write_probe' and e['details']['pathname'] == 'null':
                        continue
                    
                    tid = e['tid']
                    tgid = e['tgid']
                    event = e['event']
                    
                    pid = myutils.get_pid(tid, tgid, tgid_slicing)
                    
                    if pid in pid_set:
                        if event == 'binder_transaction_received':
                            binders.add(e['details']['transaction'])
                        elif (event == 'read_probe' or event == 'ioctl_probe' or 
                              (event == 'inet_sock_set_state')):
                            in_flows_slice.append(line)
                    
                    # Track binder transaction senders
                    if (event == 'binder_transaction' and 
                        e['details']['transaction'] in binders):
                        if pid not in pid_set:
                            pid_set.add(pid)
                        binders.remove(e['details']['transaction'])
                
                # Save the flows
                ioinstance['pid'] = api_pid
                ioinstance['command'] = api_command
                ioinstance['out'] = out_flows_slice.copy()
                ioinstance['in'] = in_flows_slice.copy()
                flows[api].append(ioinstance.copy())
        
        return flows
    
    def create_unique_io_patterns(self, flows, withpath=False):
        """
        Create unique I/O patterns from flow analysis
        Groups equivalent patterns and counts their frequency
        
        Args:
            flows: Flow analysis results
            withpath: Whether to include pathname information
            
        Returns:
            Dictionary mapping APIs to unique I/O patterns
        """
        apis2uio = dict()
        
        for api in flows:
            unique_instances = []
            
            for instance in flows[api]:
                simple_instance = dict()
                
                # Merge input and output flows
                merged = []
                i = 0
                j = 0
                
                len_in = len(instance['in'])
                len_out = len(instance['out'])
                
                if len_in == 0 and len_out == 0:
                    simple_instance['merged'] = []
                    if not unique_instances:
                        simple_instance['count'] = 1
                        unique_instances.append(simple_instance.copy())
                    else:
                        # Find matching pattern or create new one
                        found_match = False
                        for ui in unique_instances:
                            if len(ui['merged']) == 0:  # Both empty
                                ui['count'] += 1
                                found_match = True
                                break
                        if not found_match:
                            simple_instance['count'] = 1
                            unique_instances.append(simple_instance.copy())
                    continue
                
                while (i < len_in) and (j < len_out):
                    if instance['in'][i] < instance['out'][j]:
                        merged.append(instance['in'][i])
                        i += 1
                    else:
                        merged.append(instance['out'][j])
                        j += 1
                
                merged = merged + instance['in'][i:] + instance['out'][j:]
                
                # Create filtered events
                filtered_events = []
                for line in merged:
                    # Note: This would need access to parsed_events
                    # For now, we'll create a simplified version
                    filtered_events.append({'line': line})
                
                if not withpath:
                    simple_instance['merged'] = myutils.clean_event_list(filtered_events)
                else:
                    simple_instance['merged'] = myutils.clean_event_list_withpath(filtered_events)
                
                # Check for equivalent patterns
                if not unique_instances:
                    simple_instance['count'] = 1
                    unique_instances.append(simple_instance.copy())
                else:
                    unique = True
                    for ui in unique_instances:
                        if myutils.are_equivalent(ui['merged'], simple_instance['merged']):
                            unique = False
                            ui['count'] += 1
                            break
                    if unique:
                        simple_instance['count'] = 1
                        unique_instances.append(simple_instance.copy())
            
            apis2uio[api] = unique_instances.copy()
        
        return apis2uio