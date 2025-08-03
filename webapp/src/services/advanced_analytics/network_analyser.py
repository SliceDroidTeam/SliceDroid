from collections import defaultdict
from . import get_logger
from .utils import analyze_socket_types

class NetworkAnalyser:
    def __init__(self):
        self.logger = get_logger("NetworkAnalyser")
    
    # Helper function to safely parse size values
    @staticmethod
    def _safe_parse_size(size_value):
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
    
    def analyze_network_events(self, events):
        """Analyze network-related events"""
        network_events = [e for e in events if 'inet' in e.get('event', '') or 'sock' in e.get('event', '') or 'tcp' in e.get('event', '').lower() or 'udp' in e.get('event', '').lower()]
        
        if not network_events:
            return {'no_network_events': True}
        
        tcp_states = defaultdict(int)
        connections = defaultdict(int)
        
        # Track data transfer
        data_transfer = self._analyze_data_transfer(events)
        
        # Analyze socket types
        socket_types = analyze_socket_types(network_events)

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
                size = self._safe_parse_size(details.get('size', details.get('len', 0)))
                
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
                size = self._safe_parse_size(details.get('len', details.get('size', 0)))
                
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
                size = self._safe_parse_size(details.get('len', details.get('size', 0)))
                
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
                size = self._safe_parse_size(details.get('len', details.get('size', 0)))

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
