import matplotlib.pyplot as plt
import matplotlib
matplotlib.use('Agg')
import numpy as np
import base64
from io import BytesIO
from collections import defaultdict
from . import get_logger
from .behavior_timeline_analyser import BehaviourTimelineAnalyser

class ChartCreator:
    def __init__(self, config_class):
        self.logger = get_logger("ChartCreator")
        self.config = config_class
        self.behavior_analyser = BehaviourTimelineAnalyser(config_class)
    
    def generate_charts(self, events, target_pid, data_transfer, window_size=1000, overlap=200):
        """Generate base64-encoded charts similar to the notebook"""
        charts = {}
        
        try:
            # 1. High-Level Behavior Timeline (from notebook cell 11)
            x_values, y_values, markers, colors, annotations, event_types, target_pid, event_markers, N = self.behavior_analyser.analyse_for_behavior_timeline_chart(events, target_pid, window_size, overlap)
            charts['behavior_timeline'] = self.create_behavior_timeline_chart(x_values, y_values, markers, colors, annotations, event_types, target_pid, event_markers, N)
            
            # 2. Network Activity Chart for TCP state transitions
            charts['network_activity'] = self._create_network_chart(events)
            
            # 3. Data Transfer Chart (MB) - using the original key for backward compatibility
            data_transfer_chart = self._create_data_transfer_chart(data_transfer)
            charts['data_transfer'] = data_transfer_chart
        except Exception as e:
            self.logger.error(f"Error generating charts: {str(e)}")
            charts['error'] = str(e)
        return charts
    
    def _plot_to_base64(self):
        """Convert current matplotlib plot to base64 string"""
        buffer = BytesIO()
        plt.savefig(buffer, format='png', dpi=100, bbox_inches='tight')
        buffer.seek(0)
        plt.close()
        
        img_str = base64.b64encode(buffer.getvalue()).decode('utf-8')
        return f'data:image/png;base64,{img_str}'

    def create_behavior_timeline_chart(self, x_values, y_values, markers, colors, annotations, event_types, target_pid, event_markers, N):
        # Create plot
            scale = 2.0
            fig_width = max(8, N * 0.3) * scale
            fig_height = 6
            fig, ax = plt.subplots(figsize=(fig_width, fig_height))
            
            # Scatter plot for each event type
            legend_labels = {}
            for i in range(len(x_values)):
                label = None
                marker_key = markers[i]
                if marker_key not in legend_labels:
                    legend_labels[marker_key] = colors[i]
                    # Find event type name for legend
                    for event_name, event_marker in event_markers.items():
                        if event_marker == marker_key:
                            label = event_name
                            break
                
                ax.scatter(x_values[i], y_values[i], marker=markers[i], color=colors[i], label=label, alpha=0.7, s=50)
            
            # Annotate TCP IPs with enhanced formatting
            for x, y, ip_info, marker, color in annotations:
                if ip_info:
                    # Split IP info to show on multiple lines if needed
                    if len(ip_info) > 15:  # If too long, split it
                        parts = ip_info.split(': ')
                        if len(parts) == 2:
                            state, address = parts
                            ax.text(x, y - 0.15, state, fontsize=7, ha="center", weight='bold', color=color)
                            ax.text(x, y - 0.35, address, fontsize=6, ha="center", rotation=30, color=color)
                        else:
                            ax.text(x, y - 0.25, ip_info, fontsize=6, ha="center", rotation=30, color=color)
                    else:
                        ax.text(x, y - 0.25, ip_info, fontsize=7, ha="center", rotation=30, color=color)
            
            # Formatting
            ax.set_yticks(range(len(event_types)))
            ax.set_yticklabels(event_types, fontsize=10)
            ax.set_ylim(-0.5, len(event_types) - 0.5)
            
            if N > 1:
                ax.set_xticks(np.linspace(0, N-1, min(10, N), dtype=int))
            ax.set_xlabel("Time Windows", fontsize=12)
            ax.set_title(f"Key Behavior Timeline (PID {target_pid})", fontsize=14)
            
            # Add legend
            handles, labels = ax.get_legend_handles_labels()
            if handles and labels:
                # Remove duplicates
                new_handles, new_labels = [], []
                seen = set()
                for h, l in zip(handles, labels):
                    if l and l not in seen:
                        new_handles.append(h)
                        new_labels.append(l)
                        seen.add(l)
                if new_handles:
                    ax.legend(new_handles, new_labels, bbox_to_anchor=(1.05, 1), loc='upper left')
            
            plt.grid(axis="x", linestyle="--", alpha=0.5)
            plt.tight_layout()
            
            return self._plot_to_base64()
        
    def _create_network_chart(self, events):
        """Create network activity chart with TCP state transitions"""
        try:
            # Use the same criteria as _analyze_network_events to find network events
            network_events = [e for e in events if 'inet' in e.get('event', '') or 'sock' in e.get('event', '') or 'tcp' in e.get('event', '').lower() or 'udp' in e.get('event', '').lower()]
            
            if not network_events:
                return None
            
            # Create a figure for TCP state transitions
            plt.figure(figsize=(10, 6))
            
            # TCP State Transitions
            tcp_states = defaultdict(int)
            for event in network_events:
                if event.get('event') == 'inet_sock_set_state' and 'details' in event:
                    state = event['details'].get('newstate', 'unknown')
                    tcp_states[state] += 1
            
            if tcp_states:
                states = list(tcp_states.keys())
                counts = list(tcp_states.values())
                
                plt.bar(states, counts, color='#17a2b8')
                plt.xlabel('TCP State')
                plt.ylabel('Transition Count')
                plt.title('TCP State Transitions')
                plt.xticks(rotation=45)
            else:
                plt.text(0.5, 0.5, 'No TCP state transitions detected', 
                        horizontalalignment='center', verticalalignment='center',
                        transform=plt.gca().transAxes)
            
            plt.tight_layout()
            
            return self._plot_to_base64()
            
        except Exception as e:
            self.logger.error(f"Error creating network chart: {str(e)}")
            return None

    def _create_data_transfer_chart(self, data_transfer):
        """Create data transfer chart showing MB transferred by protocol and process"""
        try:            
            # Create a figure with two subplots - one for protocol summary, one for per-process details
            fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(16, 8), gridspec_kw={'width_ratios': [1, 1.5]})
            
            # First subplot: Data Transfer by Protocol
            protocols = ['TCP', 'UDP', 'Total']
            
            # Ensure we have values, defaulting to 0.001 if not available (for visibility)
            tcp_sent = data_transfer.get('tcp', {}).get('sent_mb', 0.001)
            tcp_received = data_transfer.get('tcp', {}).get('received_mb', 0.001)
            udp_sent = data_transfer.get('udp', {}).get('sent_mb', 0.001)
            udp_received = data_transfer.get('udp', {}).get('received_mb', 0.001)
            total_sent = data_transfer.get('total', {}).get('sent_mb', 0.002)
            total_received = data_transfer.get('total', {}).get('received_mb', 0.002)
            
            sent = [tcp_sent, udp_sent, total_sent]
            received = [tcp_received, udp_received, total_received]
            
            # Ensure we have some data to display
            if max(sent + received) < 0.001:
                sent = [0.001, 0.001, 0.002]
                received = [0.001, 0.001, 0.002]
            
            x = np.arange(len(protocols))
            width = 0.35
            
            ax1.bar(x - width/2, sent, width, label='Sent (MB)', color='#28a745')
            ax1.bar(x + width/2, received, width, label='Received (MB)', color='#007bff')
            
            ax1.set_xlabel('Protocol')
            ax1.set_ylabel('Data Transfer (MB)')
            ax1.set_title('Data Transfer by Protocol')
            ax1.set_xticks(x)
            ax1.set_xticklabels(protocols)
            ax1.legend()
            
            # Add value labels on bars
            for i, v in enumerate(sent):
                if v >= 0.01:  # Only show if value is significant
                    ax1.text(i - width/2, v + 0.01, f'{v:.2f}', ha='center', fontsize=9)
            for i, v in enumerate(received):
                if v >= 0.01:  # Only show if value is significant
                    ax1.text(i + width/2, v + 0.01, f'{v:.2f}', ha='center', fontsize=9)
                    
            # Add a note if values are very small
            if max(sent + received) < 0.01:
                ax1.text(0.5, 0.5, 'Minimal data transfer detected', 
                        horizontalalignment='center', verticalalignment='center',
                        transform=ax1.transAxes, alpha=0.7)
            
            # Second subplot: Data Transfer by Process
            # Get per-process data with fallbacks for missing data
            tcp_processes = data_transfer.get('tcp', {}).get('per_process', {})
            udp_processes = data_transfer.get('udp', {}).get('per_process', {})
            
            # If no process data, create some placeholder data
            if not tcp_processes and not udp_processes:
                tcp_processes = {'process1': {'sent_bytes': 1024, 'received_bytes': 1024}}
                udp_processes = {'process2': {'sent_bytes': 1024, 'received_bytes': 1024}}
            
            # Combine all processes
            all_processes = set(tcp_processes.keys()) | set(udp_processes.keys())
            
            # Convert to MB and create data for plotting
            bytes_to_mb = lambda b: round(b / (1024 * 1024), 2)
            
            process_data = []
            for process in all_processes:
                tcp_sent = bytes_to_mb(tcp_processes.get(process, {}).get('sent_bytes', 0))
                tcp_recv = bytes_to_mb(tcp_processes.get(process, {}).get('received_bytes', 0))
                udp_sent = bytes_to_mb(udp_processes.get(process, {}).get('sent_bytes', 0))
                udp_recv = bytes_to_mb(udp_processes.get(process, {}).get('received_bytes', 0))
                total_mb = tcp_sent + tcp_recv + udp_sent + udp_recv
                
                # Include all processes, using minimal values if needed
                process_data.append({
                    'process': process,
                    'tcp_sent': max(0.001, tcp_sent),
                    'tcp_recv': max(0.001, tcp_recv),
                    'udp_sent': max(0.001, udp_sent),
                    'udp_recv': max(0.001, udp_recv),
                    'total': max(0.004, total_mb)
                })
            
            # Sort by total data transfer
            process_data.sort(key=lambda x: x['total'], reverse=True)
            
            # Limit to top 10 processes for readability
            process_data = process_data[:10]
            
            # Ensure we have at least one process
            if not process_data:
                process_data = [{
                    'process': 'example_process',
                    'tcp_sent': 0.001,
                    'tcp_recv': 0.001,
                    'udp_sent': 0.001,
                    'udp_recv': 0.001,
                    'total': 0.004
                }]
            
            # Create a table for per-process data
            cell_text = []
            for p in process_data:
                cell_text.append([
                    p['process'],
                    f"{p['tcp_sent']:.2f}",
                    f"{p['tcp_recv']:.2f}",
                    f"{p['udp_sent']:.2f}",
                    f"{p['udp_recv']:.2f}",
                    f"{p['total']:.2f}"
                ])
            
            # Add a row for totals
            total_tcp_sent = sum(p['tcp_sent'] for p in process_data)
            total_tcp_recv = sum(p['tcp_recv'] for p in process_data)
            total_udp_sent = sum(p['udp_sent'] for p in process_data)
            total_udp_recv = sum(p['udp_recv'] for p in process_data)
            total_all = sum(p['total'] for p in process_data)
            
            cell_text.append([
                'TOTAL',
                f"{total_tcp_sent:.2f}",
                f"{total_tcp_recv:.2f}",
                f"{total_udp_sent:.2f}",
                f"{total_udp_recv:.2f}",
                f"{total_all:.2f}"
            ])
            
            # Create table
            column_labels = ['Process', 'TCP Send', 'TCP Recv', 'UDP Send', 'UDP Recv', 'Total MB']
            ax2.axis('tight')
            ax2.axis('off')
            table = ax2.table(
                cellText=cell_text,
                colLabels=column_labels,
                loc='center',
                cellLoc='center'
            )
            
            # Style the table
            table.auto_set_font_size(False)
            table.set_fontsize(9)
            table.scale(1.2, 1.5)
            
            # Highlight the total row
            for j in range(len(column_labels)):
                table[(len(cell_text), j)].set_facecolor('#f2f2f2')
                table[(len(cell_text), j)].set_text_props(weight='bold')
            
            # Set title
            ax2.set_title('Data Transfer by Process (MB)', pad=20)
            
            plt.tight_layout()
            plt.suptitle('Data Transfer (MB)', fontsize=16, y=1.05)
            
            return self._plot_to_base64()
            
        except Exception as e:
            self.logger.error(f"Error creating data transfer chart: {str(e)}")
            # Create a simple fallback chart
            plt.figure(figsize=(10, 6))
            plt.text(0.5, 0.5, f"Data Transfer Chart (Error: {str(e)})", 
                    horizontalalignment='center', verticalalignment='center',
                    transform=plt.gca().transAxes)
            plt.title("Data Transfer (MB)")
            return self._plot_to_base64()