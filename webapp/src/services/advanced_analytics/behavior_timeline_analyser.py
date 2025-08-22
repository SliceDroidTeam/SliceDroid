import json
from ..utils import get_device_identifier
from . import get_logger
from .base_utils import check_sensitive_resource

class BehaviourTimelineAnalyser:
    def __init__(self, config):
        self.config = config
        self.logger = get_logger("BehaviourTimelineAnalyser")

    def _load_device_category_mappings(self):
        # Load device category mappings (use OnePlus specific file for more accuracy)
        try:
            # Try OnePlus specific mapping first
            cat2devs_file = self.config.MAPPINGS_DIR / 'cat2devs_oneplus.txt'
            if not cat2devs_file.exists():
                # Fallback to generic mapping
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
                        dev2cat[dev] = cat
            else:
                dev2cat = {}
        except:
            dev2cat = {}
        return dev2cat
    
    def _load_device_category_from_txt(self):
        # Load device categories from cat2devs.txt (unified mapping file)
        try:
            cat2devs_file = self.config.MAPPINGS_DIR / 'cat2devs.txt'
            if cat2devs_file.exists():
                with open(cat2devs_file, 'r') as f:
                    category_mapping = json.load(f)
                
                # Extract sensitive categories for analysis
                sensitive_resources = {}
                sensitive_categories = ['contacts', 'sms', 'calendar', 'call_logs']
                for category in sensitive_categories:
                    if category in category_mapping:
                        sensitive_resources[category] = category_mapping[category]
            else:
                sensitive_resources = {}
        except:
            sensitive_resources = {}
        return sensitive_resources
    
    def _get_cats2windows(self, sensitive_data_trace, cats2windows):
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
        return cats2windows
    
    def analyse_for_behavior_timeline_chart(self, events, target_pid, window_size=1000, overlap=200):
        """Create high-level behavior timeline chart based on notebook cell 11"""
        # Define event markers and colors at the beginning
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
        
        try:
            dev2cat = self._load_device_category_mappings()
            sensitive_resources = self._load_device_category_from_txt()
            # Define event types without "other" category
            event_types = ["camera", "audio_in", "TCP", "bluetooth", "nfc", "gnss", "contacts", "sms", "calendar", "call_logs"]
            
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
                        # Get device identifier - use stdev+inode for regular files, kdev for device nodes
                        device_id = get_device_identifier(event)
                        if device_id and device_id in dev2cat:
                            cat = dev2cat[device_id]
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
                        sensitive_type = check_sensitive_resource(event, sensitive_resources, self.logger)
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
            
            cats2windows = self._get_cats2windows(sensitive_data_trace, cats2windows)
            
            # Prepare data for plotting
            x_values, y_values, markers, colors, annotations = [], [], [], [], []
            
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
            return (x_values, y_values, markers, colors, annotations, event_types, target_pid, event_markers, N)

        except Exception as e:
            self.logger.error(f"Error analysing behavior timeline : {str(e)}")
            return None