"""
Network Analyzer - Consolidated network analysis functionality.

This module combines network analysis capabilities from both previous
network analyzer modules to provide comprehensive network flow analysis.
"""

from collections import defaultdict
from .base_analyzer import BaseAnalyzer, SocketAnalysisUtils


class NetworkAnalyzer(BaseAnalyzer):
    """Comprehensive network flow analysis"""
    
    def __init__(self, config_class):
        super().__init__(config_class, "NetworkAnalyzer")
    
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
    
    def analyze_network_flows(self, events, target_pid=None):
        """
        Comprehensive network flow analysis
        
        Args:
            events: List of parsed events
            target_pid: Optional target process ID to filter
            
        Returns:
            Dictionary with comprehensive network analysis results
        """
        # Filter network events
        network_events = [
            e for e in events 
            if any(keyword in e.get('event', '').lower() for keyword in 
                  ['inet', 'sock', 'tcp', 'udp', 'unix', 'bluetooth'])
        ]
        
        if not network_events:
            return {'no_network_events': True}
        
        # Initialize analysis structure
        analysis = {
            'unix_stream_connections': [],
            'unix_dgram_communications': [],
            'tcp_connections': [],
            'udp_communications': [],
            'socket_operations': [],
            'bluetooth_activity': [],
            'connection_timeline': [],
            'flow_relationships': [],
            'data_transfer': {
                'tcp_sent_mb': 0,
                'tcp_received_mb': 0,
                'udp_sent_mb': 0,
                'udp_received_mb': 0,
                'total_mb': 0
            },
            'socket_types': {},
            'summary': {}
        }
        
        # Track connection states and relationships
        active_sockets = {}
        process_connections = {}
        communication_flows = []
        tcp_states = defaultdict(int)
        connections = defaultdict(int)
        
        # Data transfer tracking
        tcp_sent_bytes = 0
        tcp_received_bytes = 0
        udp_sent_bytes = 0
        udp_received_bytes = 0
        
        # Process events
        for event in network_events:
            if target_pid and event.get('tgid') != target_pid:
                continue
                
            event_name = event.get('event', '')
            timestamp = event.get('timestamp')
            process = event.get('process')
            details = event.get('details', {})
            pid = event.get('tgid')
            
            # TCP state analysis
            if event_name == "inet_sock_set_state":
                old_state = details.get('oldstate', 'unknown')
                new_state = details.get('newstate', 'unknown')
                tcp_states[f"{old_state} -> {new_state}"] += 1
                
                # Track TCP connections
                connection_info = {
                    'timestamp': timestamp,
                    'process': process,
                    'pid': pid,
                    'old_state': old_state,
                    'new_state': new_state,
                    'saddr': details.get('saddr', 'unknown'),
                    'daddr': details.get('daddr', 'unknown'),
                    'sport': details.get('sport', 'unknown'),
                    'dport': details.get('dport', 'unknown')
                }
                analysis['tcp_connections'].append(connection_info)
                
                # Create connection timeline entry
                analysis['connection_timeline'].append({
                    'time': timestamp,
                    'type': 'TCP',
                    'event': 'state_change',
                    'details': f"{old_state} -> {new_state}",
                    'process': process
                })
            
            # Data transfer analysis
            elif event_name in ['tcp_sendmsg', 'tcp_recvmsg', 'udp_sendmsg', 'udp_recvmsg']:
                size = self._safe_parse_size(details.get('size', details.get('len', 0)))
                
                if 'tcp' in event_name:
                    if 'send' in event_name:
                        tcp_sent_bytes += size
                    else:
                        tcp_received_bytes += size
                elif 'udp' in event_name:
                    if 'send' in event_name:
                        udp_sent_bytes += size
                    else:
                        udp_received_bytes += size
            
            # Socket operations
            elif 'socket' in event_name or 'bind' in event_name or 'connect' in event_name:
                socket_op = {
                    'timestamp': timestamp,
                    'operation': event_name,
                    'process': process,
                    'pid': pid,
                    'details': details
                }
                analysis['socket_operations'].append(socket_op)
            
            # Unix domain socket communications
            elif 'unix' in event_name:
                unix_comm = {
                    'timestamp': timestamp,
                    'type': 'unix_stream' if 'stream' in event_name else 'unix_dgram',
                    'process': process,
                    'pid': pid,
                    'details': details
                }
                
                if 'stream' in event_name:
                    analysis['unix_stream_connections'].append(unix_comm)
                else:
                    analysis['unix_dgram_communications'].append(unix_comm)
            
            # UDP communications
            elif 'udp' in event_name:
                udp_comm = {
                    'timestamp': timestamp,
                    'process': process,
                    'pid': pid,
                    'operation': event_name,
                    'details': details
                }
                analysis['udp_communications'].append(udp_comm)
            
            # Bluetooth activity
            elif 'bluetooth' in event_name.lower():
                bt_activity = {
                    'timestamp': timestamp,
                    'process': process,
                    'pid': pid,
                    'operation': event_name,
                    'details': details
                }
                analysis['bluetooth_activity'].append(bt_activity)
        
        # Convert bytes to MB
        bytes_to_mb = lambda b: round(b / (1024 * 1024), 2)
        analysis['data_transfer'] = {
            'tcp_sent_mb': bytes_to_mb(tcp_sent_bytes),
            'tcp_received_mb': bytes_to_mb(tcp_received_bytes),
            'udp_sent_mb': bytes_to_mb(udp_sent_bytes),
            'udp_received_mb': bytes_to_mb(udp_received_bytes),
            'total_mb': bytes_to_mb(tcp_sent_bytes + tcp_received_bytes + udp_sent_bytes + udp_received_bytes)
        }
        
        # Analyze socket types
        analysis['socket_types'] = SocketAnalysisUtils.analyze_socket_types(network_events)
        
        # Generate summary
        analysis['summary'] = {
            'total_network_events': len(network_events),
            'tcp_connections_count': len(analysis['tcp_connections']),
            'udp_communications_count': len(analysis['udp_communications']),
            'unix_connections_count': len(analysis['unix_stream_connections']) + len(analysis['unix_dgram_communications']),
            'socket_operations_count': len(analysis['socket_operations']),
            'bluetooth_activities_count': len(analysis['bluetooth_activity']),
            'tcp_state_changes': dict(tcp_states),
            'data_transfer_summary': analysis['data_transfer'],
            'has_network_activity': len(network_events) > 0
        }
        
        return self._make_json_serializable(analysis)
    
    def analyze_network_events(self, events):
        """
        Legacy method for compatibility - simplified network event analysis
        
        Args:
            events: List of events to analyze
            
        Returns:
            Basic network analysis results
        """
        # Filter for network events
        network_events = [
            e for e in events 
            if any(keyword in e.get('event', '').lower() for keyword in 
                  ['inet', 'sock', 'tcp', 'udp'])
        ]
        
        if not network_events:
            return {'no_network_events': True}
        
        tcp_states = defaultdict(int)
        connections = defaultdict(int)
        
        # Basic analysis
        for event in network_events:
            event_name = event.get('event', '')
            
            if event_name == "inet_sock_set_state":
                details = event.get('details', {})
                old_state = details.get('oldstate', 'unknown')
                new_state = details.get('newstate', 'unknown')
                tcp_states[f"{old_state} -> {new_state}"] += 1
                
                # Count unique connections
                connection_key = f"{details.get('saddr', 'unknown')}:{details.get('sport', 'unknown')} -> {details.get('daddr', 'unknown')}:{details.get('dport', 'unknown')}"
                connections[connection_key] += 1
        
        # Analyze socket types
        socket_analysis = SocketAnalysisUtils.analyze_socket_types(network_events)
        
        return self._make_json_serializable({
            'network_events_count': len(network_events),
            'tcp_state_changes': dict(tcp_states),
            'unique_connections': len(connections),
            'connections': dict(connections),
            'socket_analysis': socket_analysis
        })