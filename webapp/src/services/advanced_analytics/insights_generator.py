from .base_utils import analyze_socket_types

def get_event_size(event):
    """Helper method to extract size information from an event"""
    if not event or 'details' not in event:
        return 0
        
    details = event.get('details', {})
    
    # Try different field names for size
    size = details.get('size', details.get('len', 0))
    
    # Convert to integer if it's a string
    if isinstance(size, str):
        try:
            size = int(size)
        except ValueError:
            size = 0
    elif not isinstance(size, (int, float)):
        size = 0
        
    # Sanity check: reject unreasonably large values
    if size > 100 * 1024 * 1024:  # > 100MB
        return 0
        
    return size
    
def generate_network_insights(network_analysis):
    """Generate network analysis insights including socket type information"""
    insights = []
    
    insights.append({
        'icon': '🌐',
        'text': f"<strong>{network_analysis['network_events_count']}</strong> network events detected"
    })
    
    if network_analysis.get('tcp_state_transitions') and network_analysis['tcp_state_transitions']:
        states = list(network_analysis['tcp_state_transitions'].keys())
        insights.append({
            'icon': '🔄',
            'text': f"TCP states observed: <strong>{', '.join(states)}</strong>"
        })
    
    if network_analysis.get('connection_destinations') and network_analysis['connection_destinations']:
        dest_count = len(network_analysis['connection_destinations'])
        insights.append({
            'icon': '🎯',
            'text': f"<strong>{dest_count}</strong> unique connection destinations"
        })
    
    # Add data transfer insights
    if network_analysis.get('data_transfer'):
        data_transfer = network_analysis['data_transfer']
        
        # Add metadata insight if available
        if data_transfer.get('metadata') and data_transfer['metadata'].get('unique_packets'):
            insights.append({
                'icon': '📦',
                'text': f"<strong>{data_transfer['metadata']['unique_packets']}</strong> unique network packets analyzed"
            })
        
        # Total data transfer
        total_mb = data_transfer.get('total', {}).get('total_mb', 0)
        total_sent_mb = data_transfer.get('total', {}).get('sent_mb', 0)
        total_received_mb = data_transfer.get('total', {}).get('received_mb', 0)
        
        if total_mb > 0.01:  # Only show if significant
            insights.append({
                'icon': '📊',
                'text': f"Total data transferred: <strong>{total_mb:.2f} MB</strong> " +
                       f"(↑ {total_sent_mb:.2f} MB, ↓ {total_received_mb:.2f} MB)"
            })
        elif total_mb > 0:
            insights.append({
                'icon': '📊',
                'text': "Minimal data transfer detected (< 0.01 MB)"
            })
        
        # TCP data transfer
        tcp_total_mb = data_transfer.get('tcp', {}).get('total_mb', 0)
        tcp_sent_mb = data_transfer.get('tcp', {}).get('sent_mb', 0)
        tcp_received_mb = data_transfer.get('tcp', {}).get('received_mb', 0)
        
        if tcp_total_mb > 0.01:  # Only show if significant
            insights.append({
                'icon': '📡',
                'text': f"TCP data: <strong>{tcp_total_mb:.2f} MB</strong> " +
                       f"(↑ {tcp_sent_mb:.2f} MB, ↓ {tcp_received_mb:.2f} MB)"
            })
        elif tcp_total_mb > 0:
            insights.append({
                'icon': '📡',
                'text': "TCP data: minimal transfer detected (< 0.01 MB)"
            })
        
        # UDP data transfer
        udp_total_mb = data_transfer.get('udp', {}).get('total_mb', 0)
        udp_sent_mb = data_transfer.get('udp', {}).get('sent_mb', 0)
        udp_received_mb = data_transfer.get('udp', {}).get('received_mb', 0)
        
        if udp_total_mb > 0.01:  # Only show if significant
            insights.append({
                'icon': '📶',
                'text': f"UDP data: <strong>{udp_total_mb:.2f} MB</strong> " +
                       f"(↑ {udp_sent_mb:.2f} MB, ↓ {udp_received_mb:.2f} MB)"
            })
        elif udp_total_mb > 0:
            insights.append({
                'icon': '📶',
                'text': "UDP data: minimal transfer detected (< 0.01 MB)"
            })
        
        # Top destination by data transfer
        tcp_destinations = data_transfer['tcp']['per_destination']
        if tcp_destinations:
            top_tcp_dest = max(tcp_destinations.items(), key=lambda x: x[1]['total_bytes'], default=(None, None))
            if top_tcp_dest[0] and top_tcp_dest[1]['total_mb'] > 0:
                insights.append({
                    'icon': '🔝',
                    'text': f"Top TCP destination: <strong>{top_tcp_dest[0]}</strong> " +
                           f"({top_tcp_dest[1]['total_mb']:.2f} MB)"
                })
    
    # Add socket type insights
    socket_types = analyze_socket_types(network_analysis.get('_events', []))
    
    # If no socket types detected, try to infer from network events
    if socket_types['total_sockets'] == 0 and network_analysis.get('_events'):
        events = network_analysis.get('_events', [])
        has_tcp = any('tcp' in e.get('event', '').lower() for e in events)
        has_udp = any('udp' in e.get('event', '').lower() for e in events)
        
        if has_tcp:
            socket_types['types']['SOCK_STREAM'] = {
                'count': sum(1 for e in events if 'tcp' in e.get('event', '').lower()),
                'data_bytes': sum(get_event_size(e) for e in events if 'tcp' in e.get('event', '').lower()),
                'data_mb': 0.0,
                'description': 'TCP'
            }
            socket_types['total_sockets'] += 1
        
        if has_udp:
            socket_types['types']['SOCK_DGRAM'] = {
                'count': sum(1 for e in events if 'udp' in e.get('event', '').lower()),
                'data_bytes': sum(get_event_size(e) for e in events if 'udp' in e.get('event', '').lower()),
                'data_mb': 0.0,
                'description': 'UDP'
            }
            socket_types['total_sockets'] += 1
        
        # Calculate MB values
        bytes_to_mb = lambda b: round(b / (1024 * 1024), 2)
        for socket_type in socket_types['types']:
            socket_types['types'][socket_type]['data_mb'] = bytes_to_mb(socket_types['types'][socket_type]['data_bytes'])
    
    # Add insights based on socket types
    if socket_types['types']:
        # Get the most common socket type
        most_common_type = max(socket_types['types'].items(), key=lambda x: x[1]['count'], default=(None, None))
        if most_common_type[0]:
            socket_type, data = most_common_type
            data_mb = data.get('data_mb', 0)
            
            if data_mb > 0.01:
                insights.append({
                    'icon': '🧩',
                    'text': f"Most used socket type: <strong>{socket_type}</strong> ({data['description']}) - " +
                           f"{data['count']} sockets, {data_mb:.2f} MB transferred"
                })
            else:
                insights.append({
                    'icon': '🧩',
                    'text': f"Most used socket type: <strong>{socket_type}</strong> ({data['description']}) - " +
                           f"{data['count']} sockets, minimal data transfer"
                })
        
        # Add insight about total socket count
        insights.append({
            'icon': '🔌',
            'text': f"<strong>{socket_types['total_sockets']}</strong> total sockets created"
        })
    else:
        # Fallback if no socket types detected
        insights.append({
            'icon': '🔌',
            'text': "Network activity detected but socket types could not be determined"
        })
    
    return {
        'title': 'Network Analysis',
        'insights': insights
    }