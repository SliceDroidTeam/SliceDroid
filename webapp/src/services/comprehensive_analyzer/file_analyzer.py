"""
File Analysis Module
Core file analysis with windowed approach and device categorization
"""

import json
import traceback
from .base_utils import BaseAnalyzer, DeviceUtils, SensitiveDataUtils, EventUtils


class FileAnalyzer(BaseAnalyzer):
    """File system analysis with device categorization and sensitive data detection"""
    
    def __init__(self, config_class):
        super().__init__(config_class, "FileAnalyzer")
    
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
        from .event_slicer import EventSlicer
        
        self.logger.info(f"Starting comprehensive analysis for PID {target_pid}")

        # Initialize tracking structures
        kdev2pathnames = dict()
        kdevs_trace = []
        apis_trace = []
        TCP_trace = []

        sensitive_data_trace = {'contacts': [], 'sms': [], 'calendar': [], 'call_logs': []}
        all_sensitive_events = {'contacts': [], 'sms': [], 'calendar': [], 'call_logs': []}

        # Load device categories from cat2devs.txt (unified mapping file)
        try:
            cat2devs_file = self.config.MAPPINGS_DIR / 'cat2devs.txt'
            if cat2devs_file.exists():
                self.logger.info(f"Loading device category mapping from: {cat2devs_file}")
                with open(cat2devs_file, 'r') as f:
                    category_mapping = json.load(f)

                self.logger.info(f"Successfully loaded device category mapping with {len(category_mapping)} categories")

                # Extract sensitive categories for analysis
                sensitive_resources = {}
                sensitive_categories = ['contacts', 'sms', 'calendar', 'call_logs']
                for category in sensitive_categories:
                    if category in category_mapping:
                        # Convert all device IDs to strings for consistent comparison
                        sensitive_resources[category] = [str(dev) for dev in category_mapping[category]]
                        self.logger.info(f"Loaded {len(sensitive_resources[category])} device IDs for {category}: {sensitive_resources[category][:3]}...")
                    else:
                        self.logger.warning(f"Category '{category}' not found in cat2devs.txt")
            else:
                self.logger.warning(f"Device category mapping file not found: {cat2devs_file}")
                sensitive_resources = {}
        except Exception as e:
            self.logger.error(f"Error loading device category mapping: {str(e)}")
            self.logger.error(f"Traceback: {traceback.format_exc()}")
            sensitive_resources = {}

        # Detect all sensitive events first
        if sensitive_resources:
            for event in events:
                _, sensitive_type = SensitiveDataUtils.is_filtered_sensitive(event, sensitive_resources, True)
                if sensitive_type:
                    all_sensitive_events[sensitive_type].append(event)

            # Log detection results with details
            for data_type, events_list in all_sensitive_events.items():
                if events_list:
                    self.logger.info(f"Access to {data_type} detected! Found {len(events_list)} events.")
                    # Log sample of events for verification
                    for i, event in enumerate(events_list[:3]):  # Show first 3 events
                        device_id = DeviceUtils.get_device_identifier(event)
                        pathname = event.get('details', {}).get('pathname', 'unknown')
                        self.logger.info(f"  Sample {i+1}: Device {device_id}, Path: {pathname}, Event: {event.get('event', 'unknown')}")
                else:
                    self.logger.info(f"No access to {data_type} detected in this trace.")

        # Remove API logging
        events_pruned = EventUtils.remove_apis(events)
        self.logger.info(f'After removing excess API logging: {len(events_pruned)} events')

        # Calculate step size
        step = window_size - overlap
        if step <= 0:
            raise ValueError("Overlap must be less than the window size.")

        if window_size > len(events_pruned):
            window_size = len(events_pruned)

        # Initialize event slicer
        event_slicer = EventSlicer(self.config)

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
                relevant_events = event_slicer.slice_events(window, target_pid, asynchronous)
                tcp_window = EventUtils.get_tcp_events(relevant_events)
                window_sensitive = {data_type: [] for data_type in sensitive_data_trace}

                # Detect sensitive data in this window
                if sensitive_resources:
                    sensitive_events_in_window = 0
                    for event in window:
                        _, sensitive_type = SensitiveDataUtils.is_filtered_sensitive(event, sensitive_resources, True)
                        if sensitive_type:
                            window_sensitive[sensitive_type].append(event)
                            sensitive_events_in_window += 1

                    # Log window-level detection for debugging
                    if sensitive_events_in_window > 0:
                        self.logger.debug(f"Window {window_count}: Found {sensitive_events_in_window} sensitive events")

                    for data_type in sensitive_data_trace:
                        sensitive_data_trace[data_type].append(window_sensitive[data_type])

                # Analyze devices and pathnames
                kdev2count_window = dict()
                kdev2pathname_window = dict()
                for e in relevant_events:
                    filtered = DeviceUtils.is_filtered_device(e)
                    if not filtered:
                        # Get device identifier - use stdev+inode for regular files, kdev for device nodes
                        device_id = DeviceUtils.get_device_identifier(e)
                        pathname = e['details'].get('pathname', 'unknown')
                        if device_id not in kdev2count_window:
                            kdev2count_window[device_id] = 1
                        else:
                            kdev2count_window[device_id] += 1
                        if device_id not in kdev2pathname_window:
                            kdev2pathname_window[device_id] = [pathname]
                        else:
                            if pathname not in kdev2pathname_window[device_id]:
                                kdev2pathname_window[device_id].append(pathname)

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

        result = {
            'dev2pathnames': kdev2pathnames,
            'kdevs_trace': kdevs_trace,
            'apis_trace': apis_trace,
            'TCP_trace': TCP_trace,
            'sensitive_data_trace': sensitive_data_trace,
            'all_sensitive_events': all_sensitive_events,
            'window_count': window_count,
            'events_processed': len(events_pruned)
        }

        # Make sure all data is JSON serializable (convert sets to lists)
        return self._make_json_serializable(result)

