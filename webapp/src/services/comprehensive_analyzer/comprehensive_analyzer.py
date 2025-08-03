"""
Main Comprehensive Analyzer
Orchestrates all analysis components and provides the main interface
"""

from .base_utils import BaseAnalyzer
from .event_slicer import EventSlicer
from .file_analyzer import FileAnalyzer
from .security_analyzer import SecurityAnalyzer
from .network_analyzer import NetworkAnalyzer
from .process_analyzer import ProcessAnalyzer
from .api_analyzer import APIAnalyzer


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
        self.security_analyzer = SecurityAnalyzer(config_class)
        self.network_analyzer = NetworkAnalyzer(config_class)
        self.process_analyzer = ProcessAnalyzer(config_class)
        self.api_analyzer = APIAnalyzer(config_class)

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

    def produce_comprehensive_stats(self, analysis_results):
        """
        Produce comprehensive statistics from analysis results
        Delegates to FileAnalyzer component
        """
        return self.file_analyzer.produce_comprehensive_stats(analysis_results)

    def extract_api_instances(self, parsed_events, target_pid=None):
        """
        Extract API instances from parsed events
        Delegates to APIAnalyzer component
        """
        return self.api_analyzer.extract_api_instances(parsed_events, target_pid)

    def extract_relevant_api_instances(self, parsed_events, target_pid):
        """
        Extract all relevant API instances for a target PID
        Delegates to APIAnalyzer component
        """
        return self.api_analyzer.extract_relevant_api_instances(parsed_events, target_pid)

    def slice_log_advanced(self, api_instances, parsed_events, tgid_slicing=False):
        """
        Advanced log slicing with IPC tracking
        Delegates to APIAnalyzer component
        """
        return self.api_analyzer.slice_log_advanced(api_instances, parsed_events, tgid_slicing)

    def create_unique_io_patterns(self, flows, withpath=False):
        """
        Create unique I/O patterns from flow analysis
        Delegates to APIAnalyzer component
        """
        return self.api_analyzer.create_unique_io_patterns(flows, withpath)

    def analyze_security_events(self, events, target_pid=None):
        """
        Analyze security-related events for threat detection
        Delegates to SecurityAnalyzer component
        """
        return self.security_analyzer.analyze_security_events(events, target_pid)

    def analyze_network_flows(self, events, target_pid=None):
        """
        Analyze network-related events to detect communication patterns
        Delegates to NetworkAnalyzer component
        """
        return self.network_analyzer.analyze_network_flows(events, target_pid)

    def analyze_process_genealogy(self, events, target_pid=None):
        """
        Analyze process patterns and genealogy
        Delegates to ProcessAnalyzer component
        """
        return self.process_analyzer.analyze_process_genealogy(events, target_pid)

    # Keep all the private helper methods for backward compatibility
    def _make_json_serializable(self, obj):
        """Convert sets and other non-serializable objects to JSON-serializable format"""
        return super()._make_json_serializable(obj)

    def _is_filtered_sensitive(self, e, sensitive_resources=None, track_sensitive=False):
        """Check if event is filtered and detect sensitive type"""
        from .base_utils import SensitiveDataUtils
        return SensitiveDataUtils.is_filtered_sensitive(e, sensitive_resources, track_sensitive)

    def _is_legitimate_sensitive_access(self, pathname, data_type):
        """Validate that the pathname actually represents access to sensitive data"""
        from .base_utils import SensitiveDataUtils
        return SensitiveDataUtils.is_legitimate_sensitive_access(pathname, data_type)

    def _is_filtered_device(self, e):
        """Check if event should be filtered for device analysis"""
        from .base_utils import DeviceUtils
        return DeviceUtils.is_filtered_device(e)

    def _get_device_identifier(self, e):
        """Get device identifier - use stdev+inode for regular files, kdev for device nodes"""
        from .base_utils import DeviceUtils
        return DeviceUtils.get_device_identifier(e)

    def _remove_apis(self, events):
        """Remove API logging events"""
        from .base_utils import EventUtils
        return EventUtils.remove_apis(events)

    def _get_tcp_events(self, window):
        """Extract TCP events from window"""
        from .base_utils import EventUtils
        return EventUtils.get_tcp_events(window)

    def _calculate_risk_level_from_file_analysis(self, security_analysis):
        """Calculate risk level based on file access analysis"""
        return self.security_analyzer._calculate_risk_level_from_file_analysis(security_analysis)

    def _calculate_risk_level(self, security_analysis):
        """Calculate overall risk level based on security events"""
        return self.security_analyzer._calculate_risk_level(security_analysis)

    def _process_communication_flows(self, communication_flows):
        """Process communication flows to identify relationships"""
        return self.network_analyzer._process_communication_flows(communication_flows)

    def _analyze_network_patterns(self, network_analysis):
        """Analyze network communication patterns"""
        return self.network_analyzer._analyze_network_patterns(network_analysis)

    def _build_communication_tree(self, process_activities, ipc_events):
        """Build a tree structure based on communication patterns"""
        return self.process_analyzer._build_communication_tree(process_activities, ipc_events)

    def _analyze_process_patterns_from_activities(self, process_activities, ipc_events, file_operations, target_pid):
        """Analyze process patterns from activity data"""
        return self.process_analyzer._analyze_process_patterns_from_activities(
            process_activities, ipc_events, file_operations, target_pid
        )

    def _build_process_tree(self, parent_child_map, process_info):
        """Build hierarchical process tree"""
        return self.process_analyzer._build_process_tree(parent_child_map, process_info)

    def _analyze_process_patterns(self, genealogy_analysis, target_pid):
        """Analyze process creation and execution patterns"""
        return self.process_analyzer._analyze_process_patterns(genealogy_analysis, target_pid)
