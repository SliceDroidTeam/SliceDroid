"""
Chart Generator - Creates visualization data for frontend charts.

This module provides chart data generation functionality, simplified from
the previous chart_creator to focus on essential chart data preparation.
"""

from .base_analyzer import BaseAnalyzer, EventUtils
from collections import defaultdict, Counter


class ChartGenerator(BaseAnalyzer):
    """Generates chart data for frontend visualization"""
    
    def __init__(self, config_class):
        super().__init__(config_class, "ChartGenerator")
    
    def generate_charts(self, events, target_pid=None, data_transfer=None, window_size=1000, overlap=200):
        """
        Generate chart data for visualization
        
        Args:
            events: List of events
            target_pid: Target process ID
            data_transfer: Network data transfer info
            window_size: Analysis window size
            overlap: Window overlap
            
        Returns:
            Dictionary containing chart data
        """
        try:
            charts = {
                'behavior_timeline': self._generate_behavior_timeline(events, target_pid, window_size, overlap),
                'category_distribution': self._generate_category_chart(events),
                'device_usage': self._generate_device_chart(events),
                'network_activity': self._generate_network_chart(events, data_transfer),
                'process_activity': self._generate_process_chart(events),
                'temporal_heatmap': self._generate_temporal_heatmap(events)
            }
            
            return self._make_json_serializable(charts)
            
        except Exception as e:
            self.logger.error(f"Error generating charts: {str(e)}")
            return {'error': f'Chart generation failed: {str(e)}'}
    
    def _generate_behavior_timeline(self, events, target_pid=None, window_size=1000, overlap=200):
        """Generate behavior timeline data"""
        if target_pid:
            events = [e for e in events if e.get('tgid') == target_pid]
        
        if not events:
            return {'error': 'No events for behavior timeline'}
        
        # Create windows
        windows = []
        step_size = window_size - overlap
        
        for i in range(0, len(events), step_size):
            window = events[i:i + window_size]
            if len(window) >= window_size // 2:  # At least half the window size
                windows.append(window)
        
        # Analyze each window
        timeline_data = []
        for i, window in enumerate(windows):
            # Count categories in this window
            category_counts = Counter()
            for event in window:
                category = EventUtils.categorize_event(event.get('event', 'unknown'))
                category_counts[category] += 1
            
            window_data = {
                'window_id': i,
                'start_event': i * step_size,
                'end_event': min((i * step_size) + window_size, len(events)),
                'event_count': len(window),
                'categories': dict(category_counts),
                'dominant_category': category_counts.most_common(1)[0][0] if category_counts else 'none'
            }
            timeline_data.append(window_data)
        
        return {
            'windows': timeline_data,
            'window_size': window_size,
            'overlap': overlap,
            'total_windows': len(timeline_data)
        }
    
    def _generate_category_chart(self, events):
        """Generate category distribution chart data"""
        category_counts = Counter()
        
        for event in events:
            category = EventUtils.categorize_event(event.get('event', 'unknown'))
            category_counts[category] += 1
        
        # Convert to chart format
        chart_data = [
            {
                'category': category,
                'count': count,
                'percentage': round((count / len(events)) * 100, 2)
            }
            for category, count in category_counts.most_common()
        ]
        
        return {
            'data': chart_data,
            'total_events': len(events),
            'total_categories': len(category_counts)
        }
    
    def _generate_device_chart(self, events):
        """Generate device usage chart data"""
        device_counts = Counter()
        device_paths = defaultdict(set)
        
        for event in events:
            details = event.get('details', {})
            device_id = details.get('k_dev') or details.get('k__dev')
            
            if device_id and device_id != 0:
                device_counts[device_id] += 1
                
                # Track paths for this device
                pathname = details.get('pathname')
                if pathname:
                    device_paths[device_id].add(pathname)
        
        # Convert to chart format
        chart_data = [
            {
                'device_id': device_id,
                'access_count': count,
                'unique_paths': len(device_paths[device_id]),
                'percentage': round((count / sum(device_counts.values())) * 100, 2) if device_counts else 0
            }
            for device_id, count in device_counts.most_common(10)
        ]
        
        return {
            'data': chart_data,
            'total_accesses': sum(device_counts.values()),
            'unique_devices': len(device_counts)
        }
    
    def _generate_network_chart(self, events, data_transfer=None):
        """Generate network activity chart data"""
        if not data_transfer:
            data_transfer = {
                'tcp_sent_mb': 0,
                'tcp_received_mb': 0,
                'udp_sent_mb': 0,
                'udp_received_mb': 0,
                'total_mb': 0
            }
        
        # Count network events by type
        network_events = Counter()
        protocol_data = defaultdict(int)
        
        for event in events:
            event_name = event.get('event', '').lower()
            
            if any(keyword in event_name for keyword in ['tcp', 'udp', 'inet', 'sock']):
                network_events[event_name] += 1
                
                if 'tcp' in event_name:
                    protocol_data['TCP'] += 1
                elif 'udp' in event_name:
                    protocol_data['UDP'] += 1
                elif 'unix' in event_name:
                    protocol_data['Unix Socket'] += 1
                else:
                    protocol_data['Other'] += 1
        
        return {
            'data_transfer': data_transfer,
            'protocol_distribution': dict(protocol_data),
            'network_events': dict(network_events.most_common(10)),
            'total_network_events': sum(network_events.values())
        }
    
    def _generate_process_chart(self, events):
        """Generate process activity chart data"""
        process_counts = Counter()
        pid_to_process = {}
        
        for event in events:
            pid = event.get('tgid')
            process = event.get('process', 'unknown')
            
            if pid:
                process_counts[pid] += 1
                pid_to_process[pid] = process
        
        # Convert to chart format
        chart_data = [
            {
                'pid': pid,
                'process_name': pid_to_process.get(pid, 'unknown'),
                'event_count': count,
                'percentage': round((count / len(events)) * 100, 2)
            }
            for pid, count in process_counts.most_common(10)
        ]
        
        return {
            'data': chart_data,
            'total_processes': len(process_counts),
            'total_events': len(events)
        }
    
    def _generate_temporal_heatmap(self, events):
        """Generate temporal activity heatmap data"""
        if not events:
            return {'error': 'No events for temporal heatmap'}
        
        # Extract timestamps and categorize by time periods
        hourly_activity = defaultdict(int)
        category_by_hour = defaultdict(lambda: defaultdict(int))
        
        for event in events:
            timestamp = event.get('timestamp')
            if not timestamp:
                continue
            
            try:
                # Convert timestamp to hour (simplified - assumes timestamp is in seconds)
                if isinstance(timestamp, str):
                    timestamp = float(timestamp)
                
                # Get hour (0-23) - simplified calculation
                hour = int(timestamp) % 86400 // 3600  # seconds in day / seconds in hour
                
                hourly_activity[hour] += 1
                
                # Track categories by hour
                category = EventUtils.categorize_event(event.get('event', 'unknown'))
                category_by_hour[hour][category] += 1
                
            except (ValueError, TypeError):
                continue
        
        # Convert to heatmap format
        heatmap_data = [
            {
                'hour': hour,
                'activity_count': count,
                'categories': dict(category_by_hour[hour])
            }
            for hour, count in sorted(hourly_activity.items())
        ]
        
        return {
            'data': heatmap_data,
            'peak_hour': max(hourly_activity.items(), key=lambda x: x[1])[0] if hourly_activity else 0,
            'total_hours_active': len(hourly_activity)
        }