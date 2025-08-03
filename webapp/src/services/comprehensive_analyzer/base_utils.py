"""
Base utilities and common functions for comprehensive analysis
"""

import logging
from pathlib import Path
from collections import defaultdict
from ..utils import get_device_identifier, is_legitimate_sensitive_access, make_json_serializable


class BaseAnalyzer:
    """Base class for all analyzer components"""
    
    def __init__(self, config_class, logger_name="BaseAnalyzer"):
        self.config = config_class
        self.logger = self._setup_logger(logger_name)
    
    def _setup_logger(self, logger_name):
        """Setup logging"""
        logger = logging.getLogger(logger_name)
        logger.setLevel(logging.INFO)

        if not logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
            handler.setFormatter(formatter)
            logger.addHandler(handler)

        return logger
    
    def _make_json_serializable(self, obj):
        """Convert sets and other non-serializable objects to JSON-serializable format"""
        return make_json_serializable(obj)


class DeviceUtils:
    """Utilities for device identification and categorization"""
    
    @staticmethod
    def get_device_identifier(event):
        """Get device identifier - use stdev+inode for regular files, kdev for device nodes"""
        return get_device_identifier(event)
    
    @staticmethod
    def is_filtered_device(event):
        """Check if event should be filtered for device analysis"""
        filtered_pathnames = []

        if 'details' in event:
            # Check if this is a valid file/device access event
            if event['event'] in ['read_probe', 'write_probe', 'ioctl_probe']:
                kdev = event['details'].get('k_dev') or event['details'].get('k__dev')
                stdev = event['details'].get('s_dev_inode')
                inode = event['details'].get('inode')

                # For regular files (kdev=0), check if we have stdev and inode
                # For device nodes (kdev!=0), use kdev
                if (kdev and kdev != 0) or (stdev and inode):
                    try:
                        if 'pathname' in event['details'] and event['details']['pathname'] in filtered_pathnames:
                            return True
                        return False
                    except:
                        return True
        return True


class SensitiveDataUtils:
    """Utilities for sensitive data detection"""
    
    @staticmethod
    def is_legitimate_sensitive_access(pathname, data_type):
        """Check if pathname represents a legitimate sensitive data access based on data type"""
        return is_legitimate_sensitive_access(pathname, data_type)
    
    @staticmethod
    def is_filtered_sensitive(event, sensitive_resources=None, track_sensitive=False):
        """Check if event is filtered and detect sensitive type"""
        filtered = True
        sensitive_type = None
        filtered_pathnames = []

        if 'details' in event:
            device = event['details'].get('k_dev') or event['details'].get('k__dev')
            if (event['event'] in ['read_probe', 'write_probe', 'ioctl_probe']) and device and device != 0:
                filtered = False
                try:
                    if 'pathname' in event['details'] and event['details']['pathname'] in filtered_pathnames:
                        filtered = True
                except:
                    filtered = True

        if track_sensitive and sensitive_resources and 'details' in event:
            try:
                # Only check events that are actual file/device access operations
                if event['event'] not in ['read_probe', 'write_probe', 'ioctl_probe']:
                    if not track_sensitive:
                        return filtered
                    return filtered, None

                # Get the appropriate device identifier
                device_id = DeviceUtils.get_device_identifier(event)
                if device_id:
                    for dtype in ['contacts', 'sms', 'calendar', 'callogger']:
                        if dtype in sensitive_resources:
                            device_list = sensitive_resources[dtype]
                            # Exact string match for device identifiers
                            device_id_str = str(device_id)

                            # Check direct match in device list
                            if device_id_str in device_list:
                                # Verify this is actually accessing sensitive data, not just any file on same device
                                pathname = event['details'].get('pathname', '').lower()
                                if SensitiveDataUtils.is_legitimate_sensitive_access(pathname, dtype):
                                    sensitive_type = 'call_logs' if dtype == 'callogger' else dtype
                                    break

                            if sensitive_type:
                                break
            except Exception:
                pass

        if not track_sensitive:
            return filtered

        return filtered, sensitive_type


class EventUtils:
    """Utilities for event processing"""
    
    @staticmethod
    def remove_apis(events):
        """Remove API logging events"""
        cleaned_events = []
        i = -1
        for e in events:
            i += 1
            e['raw'] = i
            # Remove API logging and monkey process operations
            try:
                if (not (e['event'] == 'write_probe' and
                        e['details'].get('pathname', 'unknown') == 'null' and
                        e['details'].get('count', 0) > 999999) and
                    'monkey' not in e.get('process', '')):
                    cleaned_events.append(e.copy())
            except:
                pass
        return cleaned_events
    
    @staticmethod
    def get_tcp_events(window):
        """Extract TCP events from window"""
        tcp_events = []
        for e in window:
            if e['event'] == "inet_sock_set_state":
                tcp_events.append(e.copy())
        return tcp_events
