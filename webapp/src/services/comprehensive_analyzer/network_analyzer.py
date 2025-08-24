"""
Network Flow Analysis Module
Analyzes network communication patterns and relationships
"""

from .base_utils import BaseAnalyzer


class NetworkAnalyzer(BaseAnalyzer):
    """Network flow analysis for communication pattern detection"""
    
    def __init__(self, config_class):
        super().__init__(config_class, "NetworkAnalyzer")
    
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
            'tcp_connections': [],
            'udp_communications': [],
            'socket_operations': [],
            'bluetooth_activity': [],
            'connection_timeline': [],
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

            # TCP communications (if present)
            if event_name == 'tcp_sendmsg':
                tcp_send = {
                    'timestamp': timestamp,
                    'pid': pid,
                    'process': process,
                    'socket': details.get('sk'),
                    'size': details.get('size'),
                    'size_formatted': details.get('size_formatted'),
                    'src_ip': details.get('src_ip'),
                    'src_ip_readable': details.get('src_ip_readable'),
                    'dst_ip': details.get('dst_ip'),
                    'dst_ip_readable': details.get('dst_ip_readable'),
                    'src_port': details.get('src_port'),
                    'dst_port': details.get('dst_port'),
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
                    'len_formatted': details.get('len_formatted'),
                    'src_ip': details.get('src_ip'),
                    'src_ip_readable': details.get('src_ip_readable'),
                    'dst_ip': details.get('dst_ip'),
                    'dst_ip_readable': details.get('dst_ip_readable'),
                    'src_port': details.get('src_port'),
                    'dst_port': details.get('dst_port'),
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
                    'len_formatted': details.get('len_formatted'),
                    'src_ip': details.get('src_ip'),
                    'src_ip_readable': details.get('src_ip_readable'),
                    'dst_ip': details.get('dst_ip'),
                    'dst_ip_readable': details.get('dst_ip_readable'),
                    'src_port': details.get('src_port'),
                    'dst_port': details.get('dst_port'),
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
                    'len_formatted': details.get('len_formatted'),
                    'src_ip': details.get('src_ip'),
                    'src_ip_readable': details.get('src_ip_readable'),
                    'dst_ip': details.get('dst_ip'),
                    'dst_ip_readable': details.get('dst_ip_readable'),
                    'src_port': details.get('src_port'),
                    'dst_port': details.get('dst_port'),
                    'direction': 'receive',
                    'details': details
                }
                network_analysis['udp_communications'].append(udp_recv)

            # TCP connect events
            elif event_name == 'tcp_connect':
                tcp_connect = {
                    'timestamp': timestamp,
                    'pid': pid,
                    'process': process,
                    'src_ip': details.get('src_ip'),
                    'src_ip_readable': details.get('src_ip_readable'),
                    'dst_ip': details.get('dst_ip'),
                    'dst_ip_readable': details.get('dst_ip_readable'),
                    'src_port': details.get('src_port'),
                    'dst_port': details.get('dst_port'),
                    'direction': 'connect',
                    'details': details
                }
                network_analysis['tcp_connections'].append(tcp_connect)

            # Socket state changes
            elif event_name == 'inet_sock_set_state':
                state_change = {
                    'timestamp': timestamp,
                    'pid': pid,
                    'process': process,
                    'details': details
                }
                network_analysis['connection_timeline'].append(state_change)

                # Also count as TCP connection for summary
                tcp_connection = {
                    'timestamp': timestamp,
                    'pid': pid,
                    'process': process,
                    'protocol': details.get('protocol', 'TCP'),
                    'state': details.get('newstate', 'UNKNOWN'),
                    'src_addr': details.get('saddr') or details.get('saddrv6'),
                    'dst_addr': details.get('daddr') or details.get('daddrv6'),
                    'src_port': details.get('sport'),
                    'dst_port': details.get('dport'),
                    'direction': 'state_change',
                    'details': details
                }
                network_analysis['tcp_connections'].append(tcp_connection)

                # Create communication flow for TCP connections
                tcp_state = details.get('newstate', 'UNKNOWN')
                dest_addr = details.get('daddr') or details.get('daddrv6', 'unknown')

                # Only create flows for outbound connections (SYN_SENT, ESTABLISHED, etc.)
                if tcp_state in ['TCP_SYN_SENT', 'TCP_ESTABLISHED', 'TCP_FIN_WAIT1', 'TCP_CLOSE_WAIT']:
                    communication_flow = {
                        'timestamp': timestamp,
                        'from_pid': pid,
                        'to_pid': 'external',  # External destination
                        'type': 'tcp_connection',
                        'direction': 'outbound',
                        'destination': dest_addr,
                        'state': tcp_state,
                        'process': process
                    }
                    communication_flows.append(communication_flow)

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

        # Analyze patterns
        network_analysis['summary'] = self._analyze_network_patterns(network_analysis)

        return self._make_json_serializable(network_analysis)

    def _analyze_network_patterns(self, network_analysis):
        """Analyze network communication patterns"""
        summary = {
            'total_tcp_events': len(network_analysis['tcp_connections']),
            'total_udp_events': len(network_analysis['udp_communications']),
            'total_bluetooth_events': len(network_analysis['bluetooth_activity']),
            'total_connection_timeline_events': len(network_analysis['connection_timeline']),
            'tcp_send_count': 0,
            'tcp_recv_count': 0,
            'udp_send_count': 0,
            'udp_recv_count': 0
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

        return summary
