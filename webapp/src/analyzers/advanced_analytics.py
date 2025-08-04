"""
Advanced Analytics - Core analytics functionality for trace data analysis.

This module provides comprehensive analysis capabilities, consolidating
functionality from the previous advanced_analytics module.
"""

from collections import Counter
from .base_analyzer import BaseAnalyzer
from .network_analyzer import NetworkAnalyzer
from .chart_generator import ChartGenerator
from .insights_generator import InsightsGenerator
from ..services.utils import make_json_serializable


class AdvancedAnalytics(BaseAnalyzer):
    """Advanced analytics for trace data with high-level insights"""
    
    def __init__(self, config_class):
        super().__init__(config_class, "AdvancedAnalytics")
        self.network_analyzer = NetworkAnalyzer(config_class)
        self.chart_generator = ChartGenerator(config_class)
        self.insights_generator = InsightsGenerator(config_class)
    
    def analyze_trace_data(self, events, target_pid=None, window_size=1000, overlap=200):
        """
        Perform comprehensive analysis of trace data
        
        Args:
            events: List of parsed events
            target_pid: Target process ID for analysis
            window_size: Size of analysis windows for behavior timeline
            overlap: Overlap between analysis windows
            
        Returns:
            dict: Comprehensive analysis results
        """
        try:
            if not events:
                return {'error': 'No events to analyze'}
            
            # If no target PID provided, find it
            if target_pid is None:
                target_pid = self._find_target_pid(events)
            
            # Perform different types of analysis
            time_range = self._analyze_time_range(events)
            process_analysis = self._analyze_processes(events)
            device_analysis = self._analyze_devices(events)
            category_analysis = self._analyze_categories(events)
            temporal_patterns = self._analyze_temporal_patterns(events, target_pid)
            network_analysis = self.network_analyzer.analyze_network_flows(events, target_pid)
            
            # Generate charts and visualizations
            charts = self.chart_generator.generate_charts(
                events, target_pid, network_analysis.get('data_transfer', {}), 
                window_size, overlap
            )
            
            # Compile analysis results
            analysis = {
                'target_pid': target_pid,
                'total_events': len(events),
                'time_range': time_range,
                'process_analysis': process_analysis,
                'device_analysis': device_analysis,
                'category_analysis': category_analysis,
                'network_analysis': network_analysis,
                'temporal_patterns': temporal_patterns,
                'charts': charts,
                'detailed_insights': self.insights_generator.generate_insights({
                    'device_analysis': device_analysis,
                    'category_analysis': category_analysis,
                    'network_analysis': network_analysis
                })
            }
            
            # Ensure all data is JSON serializable
            return make_json_serializable(analysis)
            
        except Exception as e:
            self.logger.error(f"Error in advanced analysis: {str(e)}")
            return {'error': f'Analysis failed: {str(e)}'}
    
    def _find_target_pid(self, events):
        """Find the most active PID in the trace"""
        pid_counts = Counter(e.get('tgid', 0) for e in events if e.get('tgid', 0) > 0)
        if pid_counts:
            return pid_counts.most_common(1)[0][0]
        return 0
    
    def _analyze_time_range(self, events):
        """Analyze time range of events"""
        if not events:
            return {'error': 'No events to analyze'}
        
        timestamps = [e.get('timestamp') for e in events if e.get('timestamp')]
        if not timestamps:
            return {'error': 'No valid timestamps found'}
        
        # Convert timestamps to numeric values for analysis
        numeric_timestamps = []
        for ts in timestamps:
            if isinstance(ts, (int, float)):
                numeric_timestamps.append(ts)
            elif isinstance(ts, str):
                try: 
                    numeric_timestamps.append(float(ts))
                except ValueError:
                    continue
        
        if not numeric_timestamps:
            return {'error': 'No valid numeric timestamps found'}
        
        return {
            'start_time': min(numeric_timestamps),
            'end_time': max(numeric_timestamps),
            'duration_seconds': max(numeric_timestamps) - min(numeric_timestamps),
            'total_events': len(events),
            'events_with_timestamps': len(numeric_timestamps)
        }
    
    def _analyze_processes(self, events):
        """Analyze process information"""
        process_counts = Counter()
        pid_to_process = {}
        
        for event in events:
            pid = event.get('tgid')
            process = event.get('process', 'unknown')
            
            if pid:
                process_counts[pid] += 1
                pid_to_process[pid] = process
        
        # Convert to list of dictionaries
        processes = [
            {
                'pid': pid,
                'process_name': pid_to_process.get(pid, 'unknown'),
                'event_count': count,
                'percentage': round((count / len(events)) * 100, 2)
            }
            for pid, count in process_counts.most_common(10)
        ]
        
        return {
            'total_processes': len(process_counts),
            'top_processes': processes,
            'process_distribution': dict(process_counts)
        }
    
    def _analyze_devices(self, events):
        """Analyze device access patterns"""
        device_counts = Counter()
        device_types = Counter()
        
        for event in events:
            details = event.get('details', {})
            device_id = details.get('k_dev') or details.get('k__dev')
            
            if device_id and device_id != 0:
                device_counts[device_id] += 1
                
                # Categorize device types based on common device IDs
                if device_id < 10:
                    device_types['system'] += 1
                elif 200 <= device_id <= 300:
                    device_types['storage'] += 1
                else:
                    device_types['other'] += 1
        
        # Top devices
        top_devices = [
            {
                'device_id': device_id,
                'access_count': count,
                'percentage': round((count / sum(device_counts.values())) * 100, 2) if device_counts else 0
            }
            for device_id, count in device_counts.most_common(10)
        ]
        
        return {
            'total_device_accesses': sum(device_counts.values()),
            'unique_devices': len(device_counts),
            'top_devices': top_devices,
            'device_types': dict(device_types)
        }
    
    def _analyze_categories(self, events):
        """Analyze event categories"""
        from .base_analyzer import EventUtils
        
        category_counts = Counter()
        
        for event in events:
            event_type = event.get('event', 'unknown')
            category = EventUtils.categorize_event(event_type)
            category_counts[category] += 1
        
        # Convert to percentages
        total_events = len(events)
        categories = [
            {
                'category': category,
                'count': count,
                'percentage': round((count / total_events) * 100, 2)
            }
            for category, count in category_counts.most_common()
        ]
        
        return {
            'total_events': total_events,
            'categories': categories,
            'category_distribution': dict(category_counts)
        }
    
    def _analyze_temporal_patterns(self, events, target_pid=None):
        """Analyze temporal patterns in events"""
        if target_pid:
            events = [e for e in events if e.get('tgid') == target_pid]
        
        if not events:
            return {'error': 'No events for temporal analysis'}
        
        # Basic temporal analysis
        timestamps = []
        for event in events:
            ts = event.get('timestamp')
            if isinstance(ts, (int, float)):
                timestamps.append(ts)
            elif isinstance(ts, str):
                try:
                    timestamps.append(float(ts))
                except ValueError:
                    continue
        
        if len(timestamps) < 2:
            return {'error': 'Insufficient timestamp data for temporal analysis'}
        
        # Calculate intervals between events
        intervals = [timestamps[i+1] - timestamps[i] for i in range(len(timestamps)-1)]
        
        return {
            'event_count': len(events),
            'time_span': max(timestamps) - min(timestamps) if timestamps else 0,
            'average_interval': sum(intervals) / len(intervals) if intervals else 0,
            'min_interval': min(intervals) if intervals else 0,
            'max_interval': max(intervals) if intervals else 0,
            'events_per_second': len(events) / (max(timestamps) - min(timestamps)) if timestamps and max(timestamps) > min(timestamps) else 0
        }