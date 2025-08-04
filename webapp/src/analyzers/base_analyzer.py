"""
Base Analyzer - Consolidated utilities and base classes for all analyzers.

This module merges functionality from the previous base_utils.py files
to eliminate duplication and provide a clean foundation for all analyzers.
"""

import logging
from pathlib import Path
from collections import defaultdict
from ..services.utils import get_device_identifier, is_legitimate_sensitive_access, make_json_serializable


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
    def check_sensitive_resource(event, sensitive_resources, logger):
        """Check if event accesses a sensitive resource using device ID matching with pathname validation"""
        try:
            # Only check events that are actual file/device access operations
            if event.get('event', '') not in ['read_probe', 'write_probe', 'ioctl_probe']:
                return None
            
            # Get the appropriate device identifier
            device_id = get_device_identifier(event)
            
            if device_id:
                for data_type, device_list in sensitive_resources.items():
                    # Check if device ID matches any in the sensitive category
                    device_id_str = str(device_id)
                    if device_id_str in device_list:
                        # Verify this is actually accessing sensitive data, not just any file on same device
                        pathname = event.get('details', {}).get('pathname', '').lower()
                        if is_legitimate_sensitive_access(pathname, data_type):
                            mapped_type = 'call_logs' if data_type == 'callogger' else data_type
                            logger.debug(f"Confirmed sensitive access: {mapped_type} via device {device_id_str} path {pathname}")
                            return mapped_type
                        else:
                            logger.debug(f"Device {device_id_str} matches {data_type} but path {pathname} doesn't appear to be sensitive data")
                            
            return None
            
        except Exception as e:
            logger.warning(f"Error checking sensitive resource: {str(e)}")
            return None
    
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
    
    @staticmethod
    def categorize_event(event_type):
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


class SocketAnalysisUtils:
    """Utilities for socket and network analysis"""
    
    @staticmethod
    def analyze_socket_types(events):
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