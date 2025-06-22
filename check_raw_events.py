"""
This script processes network traffic events from a JSON file and aggregates the total bytes sent and received for
TCP and UDP protocols. It reads the events from a specified file, calculates the total bytes for each event type, and prints the results in megabytes.
It is used to validate the correctness of dashboard data by comparing raw event data with processed event data.
Also, it is useful for the debugging of tcp/upd slicing.
"""
import json
def count_network_traffic(file):
    with open(file, 'r') as file:
        raw_events = json.load(file)
    aggregated_bytes_tcp_send = 0
    aggregated_bytes_tcp_receive = 0
    aggregated_bytes_udp_send = 0
    aggregated_bytes_udp_receive = 0
    for event in raw_events:
        if event['event'] == 'tcp_sendmsg':
            aggregated_bytes_tcp_send += int(event['details']['size'])
        elif event['event'] == 'tcp_recvmsg':
            aggregated_bytes_tcp_receive += int(event['details']['len'])
        elif event['event'] == 'udp_sendmsg':
            aggregated_bytes_udp_send += int(event['details']['len'])
        elif event['event'] == 'udp_recvmsg':
            aggregated_bytes_udp_receive += int(event['details']['len'])
    # format to megabytes
    print(f'Total bytes sent in tcp_sendmsg events: {round(aggregated_bytes_tcp_send/(1024*1024),2)} mb')
    print(f'Total bytes received in tcp_recvmsg events: {round(aggregated_bytes_tcp_receive/(1024*1024),2)} mb')
    print(f'Total bytes sent in events: {round(aggregated_bytes_udp_send/(1024*1024),2)} mb')
    print(f'Total bytes received in udp_recvmsg events: {round(aggregated_bytes_udp_receive/(1024*1024),2)} mb \n\n')

count_network_traffic('raw_events.json')
count_network_traffic('data\Exports\processed_events.json')