"""
Main Comprehensive Analyzer
Orchestrates all analysis components and provides the main interface
"""

from .base_utils import BaseAnalyzer
from .event_slicer import EventSlicer
from .file_analyzer import FileAnalyzer
from .network_analyzer import NetworkAnalyzer


class ComprehensiveAnalyzer(BaseAnalyzer):
    """
    Main comprehensive analysis engine that orchestrates all analysis components
    Maintains backward compatibility with the original interface
    """

    def __init__(self, config_class):
        super().__init__(config_class, "ComprehensiveAnalyzer")
        
        # Initialize all analyzer components
        self.event_slicer = EventSlicer(config_class)
        self.file_analyzer = FileAnalyzer(config_class)
        self.network_analyzer = NetworkAnalyzer(config_class)

    def slice_events(self, events, t_pid, asynchronous=True):
        """
        Advanced bidirectional event slicing algorithm
        Delegates to EventSlicer component
        """
        return self.event_slicer.slice_events(events, t_pid, asynchronous)

    def slice_file_analysis(self, events, target_pid, window_size=5000, overlap=1000, asynchronous=True):
        """
        Complete file analysis with windowed approach
        Delegates to FileAnalyzer component
        """
        return self.file_analyzer.slice_file_analysis(events, target_pid, window_size, overlap, asynchronous)

    def analyze_network_flows(self, events, target_pid=None):
        """
        Analyze network-related events to detect communication patterns
        Delegates to NetworkAnalyzer component
        """
        return self.network_analyzer.analyze_network_flows(events, target_pid)

    # Keep all the private helper methods for backward compatibility
    def _make_json_serializable(self, obj):
        """Convert sets and other non-serializable objects to JSON-serializable format"""
        return super()._make_json_serializable(obj)

    def _remove_apis(self, events):
        """Remove API logging events"""
        from .base_utils import EventUtils
        return EventUtils.remove_apis(events)
