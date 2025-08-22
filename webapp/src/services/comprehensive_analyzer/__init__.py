"""
Comprehensive Analysis Engine Package
Modular analysis components for trace data analysis

- base_utils: Common utilities and base classes
- event_slicer: Advanced event slicing algorithms  
- file_analyzer: File system analysis with device categorization
- security_analyzer: Security threat detection
- network_analyzer: Network flow analysis
- process_analyzer: Process genealogy and activity analysis
- comprehensive_analyzer: Main orchestrator maintaining backward compatibility

All components work together through the main ComprehensiveAnalyzer interface
while maintaining full backward compatibility with existing code.
"""

from .comprehensive_analyzer import ComprehensiveAnalyzer
from .base_utils import BaseAnalyzer, DeviceUtils, SensitiveDataUtils, EventUtils
from .event_slicer import EventSlicer
from .file_analyzer import FileAnalyzer
from .network_analyzer import NetworkAnalyzer

__all__ = [
    'ComprehensiveAnalyzer',
    'BaseAnalyzer', 
    'DeviceUtils', 
    'SensitiveDataUtils', 
    'EventUtils',
    'EventSlicer',
    'FileAnalyzer',
    'NetworkAnalyzer',
]
