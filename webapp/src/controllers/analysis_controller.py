"""
Analysis Controller - Handles all analysis-related business logic.
"""

from .base_controller import BaseController
from ..analyzers.advanced_analytics import AdvancedAnalytics
from ..analyzers.network_analyzer import NetworkAnalyzer
from ..analyzers.process_analyzer import ProcessAnalyzer


class AnalysisController(BaseController):
    """Controller for analysis operations."""
    
    def __init__(self, config_class):
        super().__init__(config_class)
        self.advanced_analytics = AdvancedAnalytics(config_class)
        self.network_analyzer = NetworkAnalyzer(config_class)
        self.process_analyzer = ProcessAnalyzer(config_class)
    
    def get_advanced_analytics(self, events, pid=None, window_size=1000, overlap=200):
        """
        Perform advanced analytics on events.
        
        Args:
            events: List of events to analyze
            pid: Target PID (optional)
            window_size: Analysis window size
            overlap: Window overlap
            
        Returns:
            dict: Analysis results or error
        """
        try:
            # Validate parameters
            params = self.validate_parameters(
                pid=pid,
                window_size=window_size,
                overlap=overlap
            )
            
            target_pid = params.get('pid')
            window_size = params.get('window_size', 1000)
            overlap = params.get('overlap', 200)
            
            # Validate window parameters
            if overlap >= window_size:
                return {'error': 'Overlap must be less than window size'}
            
            # Perform analysis
            analysis = self.advanced_analytics.analyze_trace_data(
                events, target_pid, window_size, overlap
            )
            
            return analysis
            
        except Exception as e:
            return self.handle_error(e, "Advanced analytics")
    
    def get_network_analysis(self, events, pid=None):
        """
        Perform network analysis on events.
        
        Args:
            events: List of events to analyze
            pid: Target PID (optional)
            
        Returns:
            dict: Network analysis results or error
        """
        try:
            target_pid = self.validate_pid(pid) if pid else None
            
            # Perform network analysis
            network_analysis = self.network_analyzer.analyze_network_flows(
                events, target_pid
            )
            
            return {'network_analysis': network_analysis}
            
        except Exception as e:
            return self.handle_error(e, "Network analysis")
    
    def get_process_analysis(self, events, pid=None):
        """
        Perform process analysis on events.
        
        Args:
            events: List of events to analyze
            pid: Target PID (optional)
            
        Returns:
            dict: Process analysis results or error
        """
        try:
            target_pid = self.validate_pid(pid) if pid else None
            
            # Perform process genealogy analysis
            process_analysis = self.process_analyzer.analyze_process_genealogy(
                events, target_pid
            )
            
            return {'process_analysis': process_analysis}
            
        except Exception as e:
            return self.handle_error(e, "Process analysis")
    
    def slice_events_for_app(self, events, target_pid):
        """
        Slice events for a specific app/PID.
        
        Args:
            events: List of events to slice
            target_pid: Target PID to slice for
            
        Returns:
            list: Sliced events or error dict
        """
        try:
            if not target_pid:
                return {'error': 'Target PID is required for slicing'}
            
            # For now, return a filtered list by PID
            # TODO: Implement proper event slicing in analyzers
            if target_pid:
                sliced_events = [e for e in events if e.get('tgid') == target_pid]
            else:
                sliced_events = events
            
            return sliced_events
            
        except Exception as e:
            return self.handle_error(e, "Event slicing")