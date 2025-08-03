from collections import Counter
from ..utils import make_json_serializable
from .network_analyser import NetworkAnalyser
from .chart_creator import ChartCreator
from .descriptives_analyser import DescriptivesAnalyser
from . import get_logger
from ..comprehensive_analyzer import ComprehensiveAnalyzer
from .insights_generator import generate_category_insights, generate_device_insights, generate_network_insights, generate_sensitive_data_insights

class AdvancedAnalytics:
    """Advanced analytics for trace data with high-level insights"""
    
    def __init__(self, config_class):
        self.config = config_class
        self.logger = get_logger("AdvancedAnalytics")
        self.network_analyser = NetworkAnalyser()
        self.chart_creator = ChartCreator(config_class)
        self.descriptives_analyser = DescriptivesAnalyser(config_class)

        try:
            self.comprehensive_analyzer = ComprehensiveAnalyzer(config_class)
        except ImportError:
            self.logger.warning("ComprehensiveAnalyzer not available")
            self.comprehensive_analyzer = None
    
    
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
            time_range = self.descriptives_analyser.analyze_time_range(events)
            process_analysis = self.descriptives_analyser.analyze_processes(events)
            device_analysis = self.descriptives_analyser.analyze_devices(events)
            category_analysis = self.descriptives_analyser.analyze_categories(events)
            sensitive_data_analysis = self.descriptives_analyser.analyze_sensitive_data(events)
            temporal_patterns = self.descriptives_analyser.analyze_temporal_patterns(events, target_pid)
            network_analysis = self.network_analyser.analyze_network_events(events)
            charts = self.chart_creator.generate_charts(events, target_pid, window_size, overlap)
            
            # Add comprehensive analysis for behavior timeline
            comprehensive_analytics = None
            if self.comprehensive_analyzer and target_pid:
                try:
                    comprehensive_analytics = self.comprehensive_analyzer.slice_file_analysis(
                        events, target_pid, window_size=window_size, overlap=overlap
                    )
                except Exception as e:
                    self.logger.warning(f"Comprehensive analysis failed: {str(e)}")
            
            analysis = {
                'target_pid': target_pid,
                'total_events': len(events),
                'time_range': time_range,
                'process_analysis': process_analysis,
                'device_analysis': device_analysis,
                'category_analysis': category_analysis,
                'network_analysis': network_analysis,
                'sensitive_data_analysis': sensitive_data_analysis,
                'temporal_patterns': temporal_patterns,
                'charts': charts,
                'comprehensive_analytics': comprehensive_analytics,
                'detailed_insights': self._generate_detailed_insights({
                    'device_analysis': device_analysis,
                    'category_analysis': category_analysis,
                    'network_analysis': network_analysis,
                    'sensitive_data_analysis': sensitive_data_analysis
                })
            }
            
            # Ensure all data is JSON serializable before returning
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
    
    
    def _generate_detailed_insights(self, analysis_data):
        """Generate detailed insights based on analysis results"""
        insights = {}
        
        # Device Analysis Insights
        if analysis_data.get('device_analysis'):
            insights['device'] = generate_device_insights(analysis_data['device_analysis'])

        # Category Analysis Insights
        if analysis_data.get('category_analysis'):
            insights['category'] = generate_category_insights(analysis_data['category_analysis'])
        
        # Network Analysis Insights
        if analysis_data.get('network_analysis') and not analysis_data['network_analysis'].get('no_network_events'):
            insights['network'] = generate_network_insights(analysis_data['network_analysis'])

        # Sensitive Data Insights
        if analysis_data.get('sensitive_data_analysis') and analysis_data['sensitive_data_analysis'].get('total_sensitive_events', 0) > 0:
            insights['sensitive'] = generate_sensitive_data_insights(analysis_data['sensitive_data_analysis'])

        return insights