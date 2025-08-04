"""
Insights Generator - Generates human-readable insights from analysis data.

This module creates meaningful insights and recommendations from the
various analysis results to help users understand their trace data.
"""

from .base_analyzer import BaseAnalyzer


class InsightsGenerator(BaseAnalyzer):
    """Generates insights and recommendations from analysis data"""
    
    def __init__(self, config_class):
        super().__init__(config_class, "InsightsGenerator")
    
    def generate_insights(self, analysis_data):
        """
        Generate comprehensive insights from analysis results
        
        Args:
            analysis_data: Dictionary containing various analysis results
            
        Returns:
            Dictionary containing categorized insights
        """
        insights = {}
        
        try:
            # Device Analysis Insights
            if analysis_data.get('device_analysis'):
                insights['device'] = self._generate_device_insights(analysis_data['device_analysis'])

            # Category Analysis Insights
            if analysis_data.get('category_analysis'):
                insights['category'] = self._generate_category_insights(analysis_data['category_analysis'])
            
            # Network Analysis Insights
            if analysis_data.get('network_analysis') and not analysis_data['network_analysis'].get('no_network_events'):
                insights['network'] = self._generate_network_insights(analysis_data['network_analysis'])

            return self._make_json_serializable(insights)
            
        except Exception as e:
            self.logger.error(f"Error generating insights: {str(e)}")
            return {'error': f'Insight generation failed: {str(e)}'}
    
    def _generate_device_insights(self, device_analysis):
        """Generate insights about device usage patterns"""
        insights = []
        
        total_accesses = device_analysis.get('total_device_accesses', 0)
        unique_devices = device_analysis.get('unique_devices', 0)
        top_devices = device_analysis.get('top_devices', [])
        device_types = device_analysis.get('device_types', {})
        
        # Overall device activity
        if total_accesses > 0:
            insights.append({
                'icon': '💾',
                'text': f"<strong>{total_accesses:,}</strong> total device accesses across <strong>{unique_devices}</strong> unique devices"
            })
        
        # Top device usage
        if top_devices:
            top_device = top_devices[0]
            insights.append({
                'icon': '🔝',
                'text': f"Most accessed device: <strong>Device {top_device['device_id']}</strong> with <strong>{top_device['access_count']:,}</strong> accesses ({top_device['percentage']:.1f}%)"
            })
        
        # Device type distribution
        if device_types:
            system_count = device_types.get('system', 0)
            storage_count = device_types.get('storage', 0)
            other_count = device_types.get('other', 0)
            
            if system_count > 0:
                insights.append({
                    'icon': '⚙️',
                    'text': f"System device accesses: <strong>{system_count:,}</strong>"
                })
            
            if storage_count > 0:
                insights.append({
                    'icon': '💿',
                    'text': f"Storage device accesses: <strong>{storage_count:,}</strong>"
                })
            
            if other_count > 0:
                insights.append({
                    'icon': '🔧',
                    'text': f"Other device accesses: <strong>{other_count:,}</strong>"
                })
        
        # Device access intensity
        if unique_devices > 0 and total_accesses > 0:
            avg_accesses_per_device = total_accesses / unique_devices
            if avg_accesses_per_device > 100:
                insights.append({
                    'icon': '⚡',
                    'text': f"High device activity detected - average <strong>{avg_accesses_per_device:.0f}</strong> accesses per device"
                })
            elif avg_accesses_per_device < 10:
                insights.append({
                    'icon': '📉',
                    'text': "Low device activity - mostly sparse device access patterns"
                })
        
        return insights
    
    def _generate_category_insights(self, category_analysis):
        """Generate insights about event category distribution"""
        insights = []
        
        total_events = category_analysis.get('total_events', 0)
        categories = category_analysis.get('categories', [])
        
        if not categories:
            return insights
        
        # Overall event distribution
        insights.append({
            'icon': '📊',
            'text': f"<strong>{total_events:,}</strong> total events across <strong>{len(categories)}</strong> categories"
        })
        
        # Dominant category
        if categories:
            dominant = categories[0]
            insights.append({
                'icon': '👑',
                'text': f"Dominant activity: <strong>{dominant['category'].upper()}</strong> operations ({dominant['percentage']:.1f}% of all events)"
            })
        
        # Category-specific insights
        for category in categories[:3]:  # Top 3 categories
            cat_name = category['category']
            count = category['count']
            percentage = category['percentage']
            
            if cat_name == 'read':
                insights.append({
                    'icon': '📚',
                    'text': f"Read operations: <strong>{count:,}</strong> events ({percentage:.1f}%)"
                })
            elif cat_name == 'write':
                insights.append({
                    'icon': '✏️',
                    'text': f"Write operations: <strong>{count:,}</strong> events ({percentage:.1f}%)"
                })
            elif cat_name == 'network':
                insights.append({
                    'icon': '🌐',
                    'text': f"Network activity: <strong>{count:,}</strong> events ({percentage:.1f}%)"
                })
            elif cat_name == 'ioctl':
                insights.append({
                    'icon': '🔧',
                    'text': f"Device control operations: <strong>{count:,}</strong> events ({percentage:.1f}%)"
                })
            elif cat_name == 'binder':
                insights.append({
                    'icon': '🔗',
                    'text': f"IPC communications: <strong>{count:,}</strong> events ({percentage:.1f}%)"
                })
        
        # Activity pattern insights
        if len(categories) > 1:
            read_write_ratio = 0
            read_count = next((c['count'] for c in categories if c['category'] == 'read'), 0)
            write_count = next((c['count'] for c in categories if c['category'] == 'write'), 0)
            
            if write_count > 0:
                read_write_ratio = read_count / write_count
                
                if read_write_ratio > 3:
                    insights.append({
                        'icon': '📖',
                        'text': f"Read-heavy workload detected (read/write ratio: {read_write_ratio:.1f}:1)"
                    })
                elif read_write_ratio < 0.5:
                    insights.append({
                        'icon': '✍️',
                        'text': f"Write-heavy workload detected (read/write ratio: {read_write_ratio:.1f}:1)"
                    })
                else:
                    insights.append({
                        'icon': '⚖️',
                        'text': f"Balanced read/write activity (ratio: {read_write_ratio:.1f}:1)"
                    })
        
        return insights
    
    def _generate_network_insights(self, network_analysis):
        """Generate insights about network activity"""
        insights = []
        
        summary = network_analysis.get('summary', {})
        data_transfer = network_analysis.get('data_transfer', {})
        socket_types = network_analysis.get('socket_types', {})
        
        # Overall network activity
        total_events = summary.get('total_network_events', 0)
        if total_events > 0:
            insights.append({
                'icon': '🌐',
                'text': f"<strong>{total_events:,}</strong> network events detected"
            })
        
        # Connection counts
        tcp_count = summary.get('tcp_connections_count', 0)
        udp_count = summary.get('udp_communications_count', 0)
        unix_count = summary.get('unix_connections_count', 0)
        
        if tcp_count > 0:
            insights.append({
                'icon': '🔗',
                'text': f"TCP connections: <strong>{tcp_count}</strong>"
            })
        
        if udp_count > 0:
            insights.append({
                'icon': '📡',
                'text': f"UDP communications: <strong>{udp_count}</strong>"
            })
        
        if unix_count > 0:
            insights.append({
                'icon': '🔌',
                'text': f"Unix socket connections: <strong>{unix_count}</strong>"
            })
        
        # Data transfer insights
        total_mb = data_transfer.get('total_mb', 0)
        tcp_sent_mb = data_transfer.get('tcp_sent_mb', 0)
        tcp_received_mb = data_transfer.get('tcp_received_mb', 0)
        udp_sent_mb = data_transfer.get('udp_sent_mb', 0)
        udp_received_mb = data_transfer.get('udp_received_mb', 0)
        
        if total_mb > 0.01:  # Significant data transfer
            insights.append({
                'icon': '📊',
                'text': f"Total data transferred: <strong>{total_mb:.2f} MB</strong>"
            })
            
            # Protocol breakdown
            tcp_total = tcp_sent_mb + tcp_received_mb
            udp_total = udp_sent_mb + udp_received_mb
            
            if tcp_total > 0.01:
                insights.append({
                    'icon': '📈',
                    'text': f"TCP data: <strong>{tcp_total:.2f} MB</strong> (↑ {tcp_sent_mb:.2f} MB, ↓ {tcp_received_mb:.2f} MB)"
                })
            
            if udp_total > 0.01:
                insights.append({
                    'icon': '📊',
                    'text': f"UDP data: <strong>{udp_total:.2f} MB</strong> (↑ {udp_sent_mb:.2f} MB, ↓ {udp_received_mb:.2f} MB)"
                })
                
            # Data flow direction insights
            total_sent = tcp_sent_mb + udp_sent_mb
            total_received = tcp_received_mb + udp_received_mb
            
            if total_sent > total_received * 2:
                insights.append({
                    'icon': '📤',
                    'text': "Upload-heavy network activity detected"
                })
            elif total_received > total_sent * 2:
                insights.append({
                    'icon': '📥',
                    'text': "Download-heavy network activity detected"
                })
            else:
                insights.append({
                    'icon': '🔄',
                    'text': "Balanced bidirectional network activity"
                })
        
        elif total_mb > 0:
            insights.append({
                'icon': '📉',
                'text': "Minimal data transfer detected (< 0.01 MB)"
            })
        
        # Socket type insights
        if socket_types and socket_types.get('types'):
            socket_count = socket_types.get('total_sockets', 0)
            if socket_count > 0:
                insights.append({
                    'icon': '🔌',
                    'text': f"<strong>{socket_count}</strong> sockets created"
                })
                
                # Most used socket type
                types = socket_types['types']
                if types:
                    most_used = max(types.items(), key=lambda x: x[1].get('count', 0))
                    socket_type, type_data = most_used
                    count = type_data.get('count', 0)
                    description = type_data.get('description', socket_type)
                    
                    insights.append({
                        'icon': '🏆',
                        'text': f"Primary socket type: <strong>{description}</strong> ({count} sockets)"
                    })
        
        # TCP state change insights
        tcp_states = summary.get('tcp_state_changes', {})
        if tcp_states:
            state_count = len(tcp_states)
            total_transitions = sum(tcp_states.values())
            insights.append({
                'icon': '🔄',
                'text': f"TCP state transitions: <strong>{total_transitions}</strong> across {state_count} state changes"
            })
        
        return insights