# Comprehensive Analyzer Package

This package provides a modular, comprehensive analysis engine for Android system trace data.

## Architecture

The package is organized into the following modules:

### Core Components

1. **`base_utils.py`** - Common utilities and base classes
   - `BaseAnalyzer`: Base class with common functionality
   - `DeviceUtils`: Device identification and categorization utilities
   - `SensitiveDataUtils`: Sensitive data detection utilities 
   - `EventUtils`: Event processing utilities

2. **`event_slicer.py`** - Advanced event slicing algorithms
   - `EventSlicer`: Bidirectional event slicing with IPC tracking
   - Tracks process relationships through Binder, Unix sockets, and network protocols

3. **`file_analyzer.py`** - File system analysis
   - `FileAnalyzer`: Windowed file analysis with device categorization
   - Sensitive data detection and device mapping integration
4. **`network_analyzer.py`** - Network flow analysis
   - `NetworkAnalyzer`: Communication pattern detection
   - Unix sockets, TCP/UDP analysis, and flow relationship mapping

5. **`process_analyzer.py`** - Process genealogy analysis
   - `ProcessAnalyzer`: Process activity and communication patterns
   - IPC relationship mapping and suspicious behavior detection

6. **`main_analyzer.py`** - Main orchestrator
   - `ComprehensiveAnalyzer`: Main interface maintaining backward compatibility
   - Delegates to specialized components while preserving existing API

## Usage

### Basic Usage (Backward Compatible)

```python
from src.services.comprehensive_analyzer import ComprehensiveAnalyzer
from src.config import Config

# Create analyzer instance
analyzer = ComprehensiveAnalyzer(Config)

# Use exactly as before - all existing methods work unchanged
events = [...]  # Your parsed events
target_pid = 1234

# Main analysis method
results = analyzer.slice_file_analysis(events, target_pid)

# Other analysis methods
security_results = analyzer.analyze_security_events(events, target_pid)
network_results = analyzer.analyze_network_flows(events, target_pid)
process_results = analyzer.analyze_process_genealogy(events, target_pid)
```

### Advanced Usage (Direct Component Access)

```python
from src.services.comprehensive_analyzer import (
    EventSlicer, FileAnalyzer,
    NetworkAnalyzer, ProcessAnalyzer
)
from src.config import Config


network_analyzer = NetworkAnalyzer(Config)
network_results = network_analyzer.analyze_network_flows(events, target_pid)
```

### Utility Functions

```python
from src.services.comprehensive_analyzer import DeviceUtils, SensitiveDataUtils

# Device identification
device_id = DeviceUtils.get_device_identifier(event)

# Sensitive data validation  
is_sensitive = SensitiveDataUtils.is_legitimate_sensitive_access(pathname, data_type)
```

## Component Dependencies

```
main_analyzer.py
├── event_slicer.py
├── file_analyzer.py (uses event_slicer)
├── security_analyzer.py  
├── network_analyzer.py
├── process_analyzer.py
└── base_utils.py (used by all components)
```

## File Structure

```
comprehensive_analyzer/
├── __init__.py              # Package exports
├── base_utils.py           # Common utilities
├── event_slicer.py         # Event slicing algorithms  
├── file_analyzer.py        # File system analysis
├── security_analyzer.py    # Security threat detection
├── network_analyzer.py     # Network flow analysis
├── process_analyzer.py     # Process genealogy analysis
└── main_analyzer.py        # Main orchestrator
```

## Logging

Each component has its own logger for better debugging and monitoring:

- `BaseAnalyzer`: Base functionality
- `EventSlicer`: Event slicing operations
- `FileAnalyzer`: File analysis operations  
- `NetworkAnalyzer`: Network analysis
- `ProcessAnalyzer`: Process analysis
- `ComprehensiveAnalyzer`: Main coordination

## Error Handling

All components inherit robust error handling from `BaseAnalyzer` and implement specific error handling for their domains. The main analyzer ensures graceful degradation if any component fails.

## Configuration

All components use the same configuration class passed during initialization, ensuring consistent behavior across the entire analysis pipeline.
