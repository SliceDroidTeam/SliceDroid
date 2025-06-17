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
    
    def analyze_security_events(self, events, target_pid=None):
        """
        Analyze security-related events for threat detection based on available events
        
        Args:
            events: List of parsed events
            target_pid: Optional target process ID to filter
            
        Returns:
            Dictionary with security analysis results
        """
        security_analysis = {
            'suspicious_file_access': [],
            'sensitive_data_access': [],
            'binder_communications': [],
            'ioctl_operations': [],
            'privilege_escalation': [],
            'debugging_attempts': [],
            'memory_protection_changes': [],
            'capability_changes': [],
            'suspicious_activity': [],
            'summary': {}
        }
        
        # Track suspicious patterns based on available events
        suspicious_paths = set()
        binder_activity = []
        ioctl_activity = []
        file_access_patterns = {}
        
        for event in events:
            if target_pid and event.get('tgid') != target_pid:
                continue
                
            event_name = event.get('event', '')
            details = event.get('details', {})
            pathname = details.get('pathname', '')
            timestamp = event.get('timestamp')
            pid = event.get('tgid')
            process = event.get('process', '')
            
            # Analyze file access patterns
            if event_name in ['read_probe', 'write_probe']:
                # Check for suspicious file paths
                if pathname and any(suspicious in pathname.lower() for suspicious in [
                    'passwd', 'shadow', 'sudoers', 'keys', 'private', 'secret', 
                    'credential', 'token', 'config', 'etc', 'system'
                ]):
                    security_analysis['suspicious_file_access'].append({
                        'type': f'suspicious_{event_name}',
                        'timestamp': timestamp,
                        'pid': pid,
                        'process': process,
                        'pathname': pathname,
                        'operation': event_name.replace('_probe', ''),
                        'details': details
                    })
                    suspicious_paths.add(pathname)
                
                # Track file access frequency per process
                if pid not in file_access_patterns:
                    file_access_patterns[pid] = {'read': 0, 'write': 0, 'paths': set()}
                
                if event_name == 'read_probe':
                    file_access_patterns[pid]['read'] += 1
                else:
                    file_access_patterns[pid]['write'] += 1
                
                file_access_patterns[pid]['paths'].add(pathname)
            
            # Analyze Binder communications (Android IPC)
            elif event_name == 'binder_transaction':
                binder_activity.append({
                    'timestamp': timestamp,
                    'pid': pid,
                    'process': process,
                    'transaction': details.get('transaction'),
                    'details': details
                })
                
                # Check for excessive binder activity (potential malicious IPC)
                if len(binder_activity) > 50:  # Threshold for suspicious activity
                    security_analysis['suspicious_activity'].append({
                        'type': 'excessive_binder_activity',
                        'timestamp': timestamp,
                        'process': process,
                        'details': f'High frequency of binder transactions detected'
                    })
            
            # Analyze IOCTL operations
            elif event_name == 'ioctl_probe':
                ioctl_activity.append({
                    'timestamp': timestamp,
                    'pid': pid,
                    'process': process,
                    'pathname': pathname,
                    'details': details
                })
                
                # Check for potentially dangerous device access
                if pathname and any(device in pathname.lower() for device in [
                    'mem', 'kmem', 'port', 'random', 'urandom', 'zero', 'null'
                ]):
                    security_analysis['ioctl_operations'].append({
                        'type': 'device_access',
                        'timestamp': timestamp,
                        'pid': pid,
                        'process': process,
                        'device': pathname,
                        'details': details
                    })
        
        # Analyze file access patterns for anomalies
        for pid, patterns in file_access_patterns.items():
            # High read/write ratio might indicate data exfiltration
            total_operations = patterns['read'] + patterns['write']
            if total_operations > 100:  # High activity threshold
                read_ratio = patterns['read'] / total_operations
                if read_ratio > 0.8:  # More than 80% reads
                    security_analysis['suspicious_activity'].append({
                        'type': 'potential_data_exfiltration',
                        'timestamp': timestamp,
                        'pid': pid,
                        'details': f'High read activity: {patterns["read"]} reads, {patterns["write"]} writes'
                    })
                elif patterns['write'] > patterns['read'] * 3:  # Much more writes than reads
                    security_analysis['suspicious_activity'].append({
                        'type': 'potential_data_corruption',
                        'timestamp': timestamp,
                        'pid': pid,
                        'details': f'High write activity: {patterns["write"]} writes, {patterns["read"]} reads'
                    })
            
            # Access to many different paths might indicate reconnaissance
            if len(patterns['paths']) > 20:
                security_analysis['suspicious_activity'].append({
                    'type': 'broad_file_system_access',
                    'timestamp': timestamp,
                    'pid': pid,
                    'details': f'Access to {len(patterns["paths"])} different file paths'
                })
        
        # Store binder and ioctl data
        security_analysis['binder_communications'] = binder_activity
        security_analysis['ioctl_operations'] = ioctl_activity
        
        # Generate summary
        security_analysis['summary'] = {
            'total_suspicious_file_access': len(security_analysis['suspicious_file_access']),
            'total_binder_transactions': len(binder_activity),
            'total_ioctl_operations': len(ioctl_activity),
            'total_privilege_escalations': len(security_analysis['privilege_escalation']),
            'total_debugging_attempts': len(security_analysis['debugging_attempts']),
            'total_memory_changes': len(security_analysis['memory_protection_changes']),
            'total_capability_changes': len(security_analysis['capability_changes']),
            'total_suspicious_activities': len(security_analysis['suspicious_activity']),
            'suspicious_paths_count': len(suspicious_paths),
            'risk_level': self._calculate_risk_level_from_file_analysis(security_analysis)
        }
        
        return security_analysis
    
    def _calculate_risk_level_from_file_analysis(self, security_analysis):
        """Calculate risk level based on file access analysis"""
        score = 0
        
        # Suspicious file access is medium risk
        score += len(security_analysis['suspicious_file_access']) * 5
        
        # Excessive binder activity is high risk
        score += len(security_analysis['binder_communications']) * 3
        
        # IOCTL operations on sensitive devices is high risk
        score += len(security_analysis['ioctl_operations']) * 8
        
        # General suspicious activities
        score += len(security_analysis['suspicious_activity']) * 6
        
        if score >= 30:
            return 'HIGH'
        elif score >= 15:
            return 'MEDIUM'
        elif score > 0:
            return 'LOW'
        else:
            return 'NONE'
    
    def _calculate_risk_level(self, security_analysis):
        """Calculate overall risk level based on security events"""
        score = 0
        
        # Privilege escalation is high risk
        score += len(security_analysis['privilege_escalation']) * 10
        
        # Debugging attempts are medium risk
        score += len(security_analysis['debugging_attempts']) * 5
        
        # Suspicious memory operations are high risk
        score += len(security_analysis['suspicious_activity']) * 8
        
        # Capability changes are medium risk
        score += len(security_analysis['capability_changes']) * 3
        
        if score >= 20:
            return 'HIGH'
        elif score >= 10:
            return 'MEDIUM'
        elif score > 0:
            return 'LOW'
        else:
            return 'NONE'
    
    def analyze_network_flows(self, events, target_pid=None):
        """
        Analyze network-related events to detect communication patterns
        
        Args:
            events: List of parsed events
            target_pid: Optional target process ID to filter
            
        Returns:
            Dictionary with network flow analysis results
        """
        network_analysis = {
            'unix_stream_connections': [],
            'unix_dgram_communications': [],
            'tcp_connections': [],
            'udp_communications': [],
            'socket_operations': [],
            'bluetooth_activity': [],
            'connection_timeline': [],
            'flow_relationships': [],
            'summary': {}
        }
        
        # Track connection states and relationships
        active_sockets = {}
        process_connections = {}
        communication_flows = []
        
        for event in events:
            if target_pid and event.get('tgid') != target_pid:
                continue
                
            event_name = event.get('event', '')
            timestamp = event.get('timestamp')
            process = event.get('process')
            details = event.get('details', {})
            pid = event.get('tgid')
            tid = event.get('tid')
            
            # Unix domain socket stream communications
            if event_name == 'unix_stream_sendmsg':
                stream_send = {
                    'timestamp': timestamp,
                    'pid': pid,
                    'tid': tid,
                    'process': process,
                    'to_pid': details.get('topid'),
                    'direction': 'send',
                    'details': details
                }
                network_analysis['unix_stream_connections'].append(stream_send)
                
                # Track flow relationship
                if details.get('topid'):
                    communication_flows.append({
                        'from_pid': pid,
                        'to_pid': details.get('topid'),
                        'type': 'unix_stream',
                        'direction': 'send',
                        'timestamp': timestamp
                    })
            
            elif event_name == 'unix_stream_recvmsg':
                stream_recv = {
                    'timestamp': timestamp,
                    'pid': pid,
                    'tid': tid,
                    'process': process,
                    'from_pid': details.get('frompid'),
                    'direction': 'receive',
                    'details': details
                }
                network_analysis['unix_stream_connections'].append(stream_recv)
                
                # Track flow relationship
                if details.get('frompid'):
                    communication_flows.append({
                        'from_pid': details.get('frompid'),
                        'to_pid': pid,
                        'type': 'unix_stream',
                        'direction': 'receive',
                        'timestamp': timestamp
                    })
            
            # Unix domain socket datagram communications
            elif event_name == 'unix_dgram_sendmsg':
                dgram_send = {
                    'timestamp': timestamp,
                    'pid': pid,
                    'tid': tid,
                    'process': process,
                    'direction': 'send',
                    'details': details
                }
                network_analysis['unix_dgram_communications'].append(dgram_send)
            
            elif event_name == 'unix_dgram_recvmsg':
                dgram_recv = {
                    'timestamp': timestamp,
                    'pid': pid,
                    'tid': tid,
                    'process': process,
                    'direction': 'receive',
                    'inode': details.get('inode'),
                    'details': details
                }
                network_analysis['unix_dgram_communications'].append(dgram_recv)
            
            # TCP communications (if present)
            elif event_name == 'tcp_sendmsg':
                tcp_send = {
                    'timestamp': timestamp,
                    'pid': pid,
                    'process': process,
                    'socket': details.get('sk'),
                    'size': details.get('size'),
                    'direction': 'send',
                    'details': details
                }
                network_analysis['tcp_connections'].append(tcp_send)
            
            elif event_name == 'tcp_recvmsg':
                tcp_recv = {
                    'timestamp': timestamp,
                    'pid': pid,
                    'process': process,
                    'socket': details.get('sk'),
                    'len': details.get('len'),
                    'direction': 'receive',
                    'details': details
                }
                network_analysis['tcp_connections'].append(tcp_recv)
            
            # UDP communications (if present)
            elif event_name == 'udp_sendmsg':
                udp_send = {
                    'timestamp': timestamp,
                    'pid': pid,
                    'process': process,
                    'socket': details.get('sock'),
                    'len': details.get('len'),
                    'direction': 'send',
                    'details': details
                }
                network_analysis['udp_communications'].append(udp_send)
            
            elif event_name == 'udp_recvmsg':
                udp_recv = {
                    'timestamp': timestamp,
                    'pid': pid,
                    'process': process,
                    'socket': details.get('sk'),
                    'len': details.get('len'),
                    'direction': 'receive',
                    'details': details
                }
                network_analysis['udp_communications'].append(udp_recv)
            
            # Socket state changes
            elif event_name == 'inet_sock_set_state':
                state_change = {
                    'timestamp': timestamp,
                    'pid': pid,
                    'process': process,
                    'details': details
                }
                network_analysis['connection_timeline'].append(state_change)
            
            # General socket operations
            elif 'socket' in event_name or 'sock' in event_name:
                socket_op = {
                    'timestamp': timestamp,
                    'pid': pid,
                    'process': process,
                    'event': event_name,
                    'details': details
                }
                network_analysis['socket_operations'].append(socket_op)
        
        # Process communication flows
        network_analysis['flow_relationships'] = self._process_communication_flows(communication_flows)
        
        # Analyze patterns
        network_analysis['summary'] = self._analyze_network_patterns(network_analysis)
        
        return network_analysis
    
    def _process_communication_flows(self, communication_flows):
        """Process communication flows to identify relationships"""
        flow_summary = {}
        
        for flow in communication_flows:
            from_pid = flow['from_pid']
            to_pid = flow['to_pid']
            flow_type = flow['type']
            
            # Create unique flow identifier
            flow_id = f"{from_pid}->{to_pid}"
            
            if flow_id not in flow_summary:
                flow_summary[flow_id] = {
                    'from_pid': from_pid,
                    'to_pid': to_pid,
                    'types': set(),
                    'count': 0,
                    'first_seen': flow['timestamp'],
                    'last_seen': flow['timestamp']
                }
            
            flow_summary[flow_id]['types'].add(flow_type)
            flow_summary[flow_id]['count'] += 1
            flow_summary[flow_id]['last_seen'] = max(flow_summary[flow_id]['last_seen'], flow['timestamp'])
        
        # Convert sets to lists for JSON serialization
        for flow_id in flow_summary:
            flow_summary[flow_id]['types'] = list(flow_summary[flow_id]['types'])
        
        return flow_summary
    
    def _analyze_network_patterns(self, network_analysis):
        """Analyze network communication patterns"""
        summary = {
            'total_tcp_events': len(network_analysis['tcp_connections']),
            'total_udp_events': len(network_analysis['udp_communications']),
            'total_unix_stream_events': len(network_analysis['unix_stream_connections']),
            'total_unix_dgram_events': len(network_analysis['unix_dgram_communications']),
            'total_socket_operations': len(network_analysis['socket_operations']),
            'total_bluetooth_events': len(network_analysis['bluetooth_activity']),
            'tcp_send_count': 0,
            'tcp_recv_count': 0,
            'udp_send_count': 0,
            'udp_recv_count': 0,
            'unix_stream_send_count': 0,
            'unix_stream_recv_count': 0,
            'unix_dgram_send_count': 0,
            'unix_dgram_recv_count': 0,
            'active_protocols': set(),
            'communication_intensity': 'LOW',
            'unique_flows': len(network_analysis['flow_relationships'])
        }
        
        # Count send/receive operations for TCP
        for tcp_event in network_analysis['tcp_connections']:
            if tcp_event['direction'] == 'send':
                summary['tcp_send_count'] += 1
            else:
                summary['tcp_recv_count'] += 1
        
        # Count send/receive operations for UDP
        for udp_event in network_analysis['udp_communications']:
            if udp_event['direction'] == 'send':
                summary['udp_send_count'] += 1
            else:
                summary['udp_recv_count'] += 1
        
        # Count send/receive operations for Unix stream
        for stream_event in network_analysis['unix_stream_connections']:
            if stream_event['direction'] == 'send':
                summary['unix_stream_send_count'] += 1
            else:
                summary['unix_stream_recv_count'] += 1
        
        # Count send/receive operations for Unix datagram
        for dgram_event in network_analysis['unix_dgram_communications']:
            if dgram_event['direction'] == 'send':
                summary['unix_dgram_send_count'] += 1
            else:
                summary['unix_dgram_recv_count'] += 1
        
        # Identify active protocols
        if summary['total_tcp_events'] > 0:
            summary['active_protocols'].add('TCP')
        if summary['total_udp_events'] > 0:
            summary['active_protocols'].add('UDP')
        if summary['total_unix_stream_events'] > 0:
            summary['active_protocols'].add('Unix Domain Sockets (Stream)')
        if summary['total_unix_dgram_events'] > 0:
            summary['active_protocols'].add('Unix Domain Sockets (Datagram)')
        if summary['total_bluetooth_events'] > 0:
            summary['active_protocols'].add('Bluetooth')
        
        # Calculate communication intensity
        total_events = (summary['total_tcp_events'] + 
                       summary['total_udp_events'] + 
                       summary['total_unix_stream_events'] +
                       summary['total_unix_dgram_events'] +
                       summary['total_bluetooth_events'])
        
        if total_events > 100:
            summary['communication_intensity'] = 'HIGH'
        elif total_events > 20:
            summary['communication_intensity'] = 'MEDIUM'
        else:
            summary['communication_intensity'] = 'LOW'
        
        summary['active_protocols'] = list(summary['active_protocols'])
        
        return summary
    
    def analyze_process_genealogy(self, events, target_pid=None):
        """
        Analyze process patterns based on available events (file access and IPC)
        
        Args:
            events: List of parsed events
            target_pid: Optional target process ID to filter
            
        Returns:
            Dictionary with process analysis results
        """
        genealogy_analysis = {
            'process_creations': [],
            'process_executions': [],
            'elf_loads': [],
            'process_tree': {},
            'execution_timeline': [],
            'process_activities': [],
            'ipc_communications': [],
            'summary': {}
        }
        
        # Track process activities and patterns
        process_activities = {}
        unique_processes = set()
        ipc_events = []
        file_operations = []
        
        for event in events:
            event_name = event.get('event', '')
            timestamp = event.get('timestamp')
            pid = event.get('tgid')
            tid = event.get('tid')
            process = event.get('process', '')
            details = event.get('details', {})
            
            unique_processes.add(pid)
            
            # Track process activity patterns
            if pid not in process_activities:
                process_activities[pid] = {
                    'process_name': process,
                    'first_seen': timestamp,
                    'last_seen': timestamp,
                    'total_events': 0,
                    'read_operations': 0,
                    'write_operations': 0,
                    'ioctl_operations': 0,
                    'binder_transactions': 0,
                    'unix_communications': 0,
                    'accessed_files': set(),
                    'communication_partners': set()
                }
            
            activity = process_activities[pid]
            activity['last_seen'] = timestamp
            activity['total_events'] += 1
            
            # Analyze different event types
            if event_name == 'read_probe':
                activity['read_operations'] += 1
                if details.get('pathname'):
                    activity['accessed_files'].add(details['pathname'])
                file_operations.append({
                    'timestamp': timestamp,
                    'pid': pid,
                    'process': process,
                    'operation': 'read',
                    'pathname': details.get('pathname', ''),
                    'details': details
                })
            
            elif event_name == 'write_probe':
                activity['write_operations'] += 1
                if details.get('pathname'):
                    activity['accessed_files'].add(details['pathname'])
                file_operations.append({
                    'timestamp': timestamp,
                    'pid': pid,
                    'process': process,
                    'operation': 'write',
                    'pathname': details.get('pathname', ''),
                    'details': details
                })
            
            elif event_name == 'ioctl_probe':
                activity['ioctl_operations'] += 1
                if details.get('pathname'):
                    activity['accessed_files'].add(details['pathname'])
                file_operations.append({
                    'timestamp': timestamp,
                    'pid': pid,
                    'process': process,
                    'operation': 'ioctl',
                    'pathname': details.get('pathname', ''),
                    'details': details
                })
            
            elif event_name == 'binder_transaction':
                activity['binder_transactions'] += 1
                ipc_events.append({
                    'timestamp': timestamp,
                    'pid': pid,
                    'process': process,
                    'type': 'binder',
                    'transaction': details.get('transaction'),
                    'details': details
                })
            
            elif event_name in ['unix_stream_sendmsg', 'unix_stream_recvmsg', 'unix_dgram_sendmsg', 'unix_dgram_recvmsg']:
                activity['unix_communications'] += 1
                peer_pid = details.get('topid') or details.get('frompid')
                if peer_pid:
                    activity['communication_partners'].add(peer_pid)
                
                ipc_events.append({
                    'timestamp': timestamp,
                    'pid': pid,
                    'process': process,
                    'type': event_name,
                    'peer_pid': peer_pid,
                    'details': details
                })
        
        # Convert sets to lists and calculate durations
        for pid, activity in process_activities.items():
            activity['accessed_files'] = list(activity['accessed_files'])
            activity['communication_partners'] = list(activity['communication_partners'])
            activity['duration'] = activity['last_seen'] - activity['first_seen']
            activity['files_accessed_count'] = len(activity['accessed_files'])
            activity['partners_count'] = len(activity['communication_partners'])
        
        # Build simplified process tree based on communication patterns
        process_tree = self._build_communication_tree(process_activities, ipc_events)
        
        genealogy_analysis['process_activities'] = list(process_activities.values())
        genealogy_analysis['ipc_communications'] = ipc_events
        genealogy_analysis['process_tree'] = process_tree
        
        # Generate summary
        genealogy_analysis['summary'] = self._analyze_process_patterns_from_activities(
            process_activities, ipc_events, file_operations, target_pid
        )
        
        return genealogy_analysis
    
    def _build_communication_tree(self, process_activities, ipc_events):
        """Build a tree structure based on communication patterns"""
        tree = {}
        
        # Create nodes for each process
        for pid, activity in process_activities.items():
            tree[pid] = {
                'pid': pid,
                'process_name': activity['process_name'],
                'total_events': activity['total_events'],
                'duration': activity['duration'],
                'communication_partners': activity['communication_partners'],
                'children': []
            }
        
        # Add communication relationships as edges
        for event in ipc_events:
            if event['type'] in ['unix_stream_sendmsg', 'unix_dgram_sendmsg']:
                from_pid = event['pid']
                to_pid = event.get('peer_pid')
                if from_pid in tree and to_pid in tree:
                    # Add as child relationship (simplified)
                    if to_pid not in [child['pid'] for child in tree[from_pid]['children']]:
                        tree[from_pid]['children'].append({
                            'pid': to_pid,
                            'relationship': 'communication_target'
                        })
        
        return tree
    
    def _analyze_process_patterns_from_activities(self, process_activities, ipc_events, file_operations, target_pid):
        """Analyze process patterns from activity data"""
        total_processes = len(process_activities)
        total_file_ops = len(file_operations)
        total_ipc_events = len(ipc_events)
        
        # Find most active process
        most_active = None
        max_events = 0
        for pid, activity in process_activities.items():
            if activity['total_events'] > max_events:
                max_events = activity['total_events']
                most_active = {'pid': pid, 'events': max_events, 'name': activity['process_name']}
        
        # Detect suspicious patterns
        suspicious_patterns = []
        
        for pid, activity in process_activities.items():
            # High file access activity
            if activity['files_accessed_count'] > 50:
                suspicious_patterns.append({
                    'type': 'high_file_access',
                    'description': f'Process {pid} ({activity["process_name"]}) accessed {activity["files_accessed_count"]} different files'
                })
            
            # Imbalanced read/write ratio
            total_rw = activity['read_operations'] + activity['write_operations']
            if total_rw > 100:
                read_ratio = activity['read_operations'] / total_rw
                if read_ratio > 0.9:
                    suspicious_patterns.append({
                        'type': 'excessive_reading',
                        'description': f'Process {pid} has unusually high read activity ({activity["read_operations"]} reads vs {activity["write_operations"]} writes)'
                    })
                elif read_ratio < 0.1:
                    suspicious_patterns.append({
                        'type': 'excessive_writing',
                        'description': f'Process {pid} has unusually high write activity ({activity["write_operations"]} writes vs {activity["read_operations"]} reads)'
                    })
            
            # High communication activity
            if activity['partners_count'] > 5:
                suspicious_patterns.append({
                    'type': 'high_communication_activity',
                    'description': f'Process {pid} communicates with {activity["partners_count"]} different processes'
                })
        
        # Calculate activity frequency
        if total_file_ops > 1000:
            activity_frequency = 'HIGH'
        elif total_file_ops > 200:
            activity_frequency = 'MEDIUM'
        else:
            activity_frequency = 'LOW'
        
        return {
            'total_processes': total_processes,
            'total_file_operations': total_file_ops,
            'total_ipc_events': total_ipc_events,
            'total_forks': 0,  # Not available in current trace
            'total_execs': 0,  # Not available in current trace
            'process_tree_depth': min(3, total_processes),  # Simplified depth
            'most_active_process': most_active,
            'activity_frequency': activity_frequency,
            'suspicious_patterns': suspicious_patterns,
            'unique_processes': total_processes
        }
    
    def _build_process_tree(self, parent_child_map, process_info):
        """Build hierarchical process tree"""
        def build_subtree(pid, visited=None):
            if visited is None:
                visited = set()
            
            if pid in visited:
                return None  # Prevent infinite loops
            
            visited.add(pid)
            
            node = {
                'pid': pid,
                'info': process_info.get(pid, {}),
                'children': []
            }
            
            if pid in parent_child_map:
                for child_pid in parent_child_map[pid]:
                    child_node = build_subtree(child_pid, visited.copy())
                    if child_node:
                        node['children'].append(child_node)
            
            return node
        
        # Find root processes (those without parents in our data)
        all_children = set()
        for children in parent_child_map.values():
            all_children.update(children)
        
        root_pids = set(parent_child_map.keys()) - all_children
        
        tree = {}
        for root_pid in root_pids:
            tree[root_pid] = build_subtree(root_pid)
        
        return tree
    
    def _analyze_process_patterns(self, genealogy_analysis, target_pid):
        """Analyze process creation and execution patterns"""
        summary = {
            'total_forks': len(genealogy_analysis['process_creations']),
            'total_execs': len(genealogy_analysis['process_executions']),
            'total_elf_loads': len(genealogy_analysis['elf_loads']),
            'process_tree_depth': 0,
            'most_active_parent': None,
            'execution_frequency': 'LOW',
            'suspicious_patterns': []
        }
        
        # Calculate tree depth
        def calculate_depth(tree, current_depth=0):
            max_depth = current_depth
            for node in tree.values():
                if node and 'children' in node:
                    for child in node['children']:
                        depth = calculate_depth({child['pid']: child}, current_depth + 1)
                        max_depth = max(max_depth, depth)
            return max_depth
        
        summary['process_tree_depth'] = calculate_depth(genealogy_analysis['process_tree'])
        
        # Find most active parent (most forks)
        parent_activity = {}
        for creation in genealogy_analysis['process_creations']:
            parent_pid = creation['parent_pid']
            if parent_pid not in parent_activity:
                parent_activity[parent_pid] = 0
            parent_activity[parent_pid] += 1
        
        if parent_activity:
            most_active_pid = max(parent_activity, key=parent_activity.get)
            summary['most_active_parent'] = {
                'pid': most_active_pid,
                'fork_count': parent_activity[most_active_pid]
            }
        
        # Calculate execution frequency
        total_execution_events = (summary['total_execs'] + summary['total_elf_loads'])
        if total_execution_events > 50:
            summary['execution_frequency'] = 'HIGH'
        elif total_execution_events > 10:
            summary['execution_frequency'] = 'MEDIUM'
        else:
            summary['execution_frequency'] = 'LOW'
        
        # Detect suspicious patterns
        if summary['process_tree_depth'] > 5:
            summary['suspicious_patterns'].append({
                'type': 'deep_process_tree',
                'description': f'Unusually deep process tree (depth: {summary["process_tree_depth"]})'
            })
        
        if summary['most_active_parent'] and summary['most_active_parent']['fork_count'] > 10:
            summary['suspicious_patterns'].append({
                'type': 'excessive_forking',
                'description': f'Process {summary["most_active_parent"]["pid"]} created {summary["most_active_parent"]["fork_count"]} child processes'
            })
        
        if total_execution_events > 100:
            summary['suspicious_patterns'].append({
                'type': 'high_execution_activity',
                'description': f'High number of execution events ({total_execution_events})'
            })
        
        return summary