from collections import defaultdict
from ..utils import get_device_identifier, is_legitimate_sensitive_access

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