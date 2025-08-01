# 🤝 Contributing to SliceDroid

Thank you for your interest in contributing to SliceDroid! This document provides guidelines and information for contributors to help maintain code quality and project consistency.

---

## 📋 Table of Contents

- [Getting Started](#getting-started)
- [Development Setup](#development-setup)
- [Contributing Guidelines](#contributing-guidelines)
- [Code Standards](#code-standards)
- [Testing](#testing)
- [Submitting Changes](#submitting-changes)
- [Issue Reporting](#issue-reporting)
- [Documentation](#documentation)

---

## 🚀 Getting Started

### Prerequisites

Before contributing, ensure you have:

- **Rooted Android device** with Developer Options enabled
- **Python 3.8+** and pip
- **Git** for version control
- **Docker** (optional, for containerized development)
- **ADB** (Android Debug Bridge)

### Understanding the Project

SliceDroid is a modular Android tracing toolkit consisting of:

- **Kernel tracing scripts** using kprobes
- **Python parsers** for ftrace log analysis
- **Web interface** for visualization and analysis
- **Device mapping utilities** for file system and network analysis

---

## 🛠️ Development Setup

### 1. Fork and Clone

```bash
# Fork the repository on GitHub, then clone your fork
git clone https://github.com/YOUR_USERNAME/SLICEDROID_APP.git
cd SLICEDROID_APP

# Add upstream remote
git remote add upstream https://github.com/SliceDroidTeam/SLICEDROID_APP.git
```

### 2. Environment Setup

**Local Development (Recommended)**
```bash
# Install dependencies
pip install -r requirements.txt

# Optional: Set up development tools
pip install black flake8 pytest pre-commit

# Set up pre-commit hooks (recommended)
pre-commit install
```

**Why Local Development?**
- **Direct ADB access** to Android devices
- **Faster development** cycle
- **Better IDE integration**
- **Easier debugging** and testing

### 3. Verify Setup

```bash
# Test basic functionality
python3 run_slicedroid.py --help

# Run web interface
python3 webapp/app.py
```

---

## 📝 Contributing Guidelines

### Types of Contributions

We welcome various types of contributions:

- 🐛 **Bug fixes** and issue resolutions
- ✨ **New features** and enhancements
- 📚 **Documentation** improvements
- 🧪 **Tests** and quality assurance
- 🔧 **Build and deployment** improvements
- 🎨 **UI/UX** enhancements

### Contribution Process

1. **Check existing issues** before starting work
2. **Create an issue** for new features or major changes
3. **Fork the repository** and create a feature branch
4. **Make your changes** following our code standards
5. **Test thoroughly** on Android devices if needed
6. **Submit a pull request** with clear description

### Branch Naming

Use descriptive branch names:

- `feature/network-analysis-enhancement`
- `bugfix/trace-parsing-memory-leak`
- `docs/api-documentation-update`
- `refactor/webapp-service-layer`

---

## 🎯 Code Standards

### Python Code Style

We follow PEP 8 with some project-specific guidelines:

```python
# Use meaningful variable names
trace_events = parse_ftrace_log(trace_file)
network_data = aggregate_network_traffic(trace_events)

# Add docstrings for functions and classes
def parse_system_calls(trace_data: List[Dict]) -> Dict[str, Any]:
    """
    Parse system call events from trace data.
    
    Args:
        trace_data: List of raw trace events
        
    Returns:
        Dictionary containing parsed system call information
    """
    pass

# Use type hints where applicable
from typing import Dict, List, Optional, Union
```

### JavaScript/Web Code

For web interface components:

```javascript
// Use modern ES6+ syntax
const processTraceData = (data) => {
    return data.map(event => ({
        timestamp: new Date(event.timestamp),
        type: event.event_type,
        details: parseEventDetails(event)
    }));
};

// Add JSDoc comments for functions
/**
 * Renders network traffic visualization
 * @param {Object} networkData - Processed network events
 * @param {string} containerId - DOM element ID for chart
 */
function renderNetworkChart(networkData, containerId) {
    // Implementation
}
```

### Shell Scripts

For tracing and utility scripts:

```bash
#!/bin/bash
# Script description and usage

set -euo pipefail  # Enable strict error handling

# Use meaningful variable names
readonly TRACE_OUTPUT_DIR="/data/local/tmp/traces"
readonly KPROBE_EVENTS="/sys/kernel/debug/tracing/kprobe_events"

# Add comments for complex operations
# Enable network tracing kprobes
echo 'p:tcp_sendmsg tcp_sendmsg' > "$KPROBE_EVENTS"
```

---

## 🧪 Testing

### Testing Requirements

Before submitting changes:

1. **Test on real Android devices** - Emulators may not accurately reflect kernel behavior
2. **Verify trace parsing** with various Android versions
3. **Check web interface** functionality
4. **Test Docker deployment** if applicable

### Manual Testing Checklist

- [ ] Tracing scripts work on target Android version
- [ ] Trace files are properly generated and parsed
- [ ] Web interface displays data correctly
- [ ] No memory leaks during long traces
- [ ] Docker containers build and run successfully

### Automated Testing

```bash
# Run basic validation tests
python3 -m pytest tests/ -v

# Check code formatting
black --check .
flake8 .

# Validate shell scripts
shellcheck scripts/**/*.sh
```

---

## 📥 Submitting Changes

### Pull Request Process

1. **Update your branch** with latest upstream changes:
   ```bash
   git fetch upstream
   git rebase upstream/main
   ```

2. **Create a descriptive PR** with:
   - Clear title summarizing the change
   - Detailed description of what was changed and why
   - Reference to related issues
   - Screenshots for UI changes
   - Testing details

3. **PR Template** (use this format):
   ```markdown
   ## Description
   Brief description of changes

   ## Type of Change
   - [ ] Bug fix
   - [ ] New feature
   - [ ] Documentation update
   - [ ] Refactoring

   ## Testing
   - [ ] Tested on Android device (specify version)
   - [ ] Web interface verified
   - [ ] Docker build successful

   ## Screenshots (if applicable)

   ## Related Issues
   Closes #issue_number
   ```

### Code Review Process

- All submissions require review from project maintainers
- Address feedback promptly and professionally
- Be open to suggestions and improvements
- Squash commits before merging if requested

---

## 🐛 Issue Reporting

### Bug Reports

When reporting bugs, include:

```markdown
**Android Device Info:**
- Device model: 
- Android version:
- Kernel version: 

**SliceDroid Version:**
- Commit hash or release version

**Steps to Reproduce:**
1. 
2. 
3. 

**Expected Behavior:**

**Actual Behavior:**

**Logs/Traces:**
```

### Feature Requests

For new features, describe:
- **Problem** you're trying to solve
- **Proposed solution** with technical details
- **Use cases** and benefits
- **Implementation considerations**

---

## 📚 Documentation

### Documentation Guidelines

- Update README.md for user-facing changes
- Add inline code comments for complex logic
- Update DOCKER.md for container-related changes
- Include docstrings for all public functions
- Add examples for new APIs or features

### API Documentation

For new analysis services or web APIs:

```python
class TraceAnalyzer:
    """
    Analyzes Android trace data for security patterns.
    
    Example:
        analyzer = TraceAnalyzer()
        results = analyzer.analyze_trace('trace.log')
        security_events = results.get_security_events()
    """
    
    def analyze_trace(self, trace_file: str) -> AnalysisResult:
        """
        Analyze trace file for security patterns.
        
        Args:
            trace_file: Path to ftrace log file
            
        Returns:
            AnalysisResult containing security findings
            
        Raises:
            TraceParseError: If trace file is malformed
        """
        pass
```

---

## 🙋‍♀️ Getting Help

### Communication Channels

- **GitHub Issues**: For bugs and feature requests
- **GitHub Discussions**: For questions and community discussion
- **Pull Request Reviews**: For code-specific feedback

### Development Questions

When asking for help:

1. Search existing issues and discussions first
2. Provide context about your development environment
3. Include relevant code snippets or logs
4. Be specific about what you're trying to achieve

---

## 🏆 Recognition

Contributors will be recognized in:

- **CONTRIBUTORS.md** file (auto-generated from Git history)
- **Release notes** for significant contributions
- **README.md** acknowledgments section

---

## 📄 License

By contributing to SliceDroid, you agree that your contributions will be licensed under the same license as the project.

---

**Thank you for contributing to SliceDroid! 🎉**

Your contributions help make Android security analysis more accessible to researchers and developers worldwide.
