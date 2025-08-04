"""
Security Analyzer - Analyzes security-related events and patterns.

This module consolidates security analysis functionality to identify
potential security issues, sensitive data access, and suspicious patterns.
"""

from collections import defaultdict, Counter
from .base_analyzer import BaseAnalyzer, SensitiveDataUtils, DeviceUtils


class SecurityAnalyzer(BaseAnalyzer):
    """Security analysis for detecting sensitive data access and suspicious patterns"""
    
    def __init__(self, config_class):
        super().__init__(config_class, "SecurityAnalyzer")
    
    def analyze_security_patterns(self, events, target_pid=None, sensitive_resources=None):
        """
        Analyze security-related patterns in events
        
        Args:
            events: List of events to analyze
            target_pid: Optional target process ID to focus on
            sensitive_resources: Dictionary of sensitive resource mappings
            
        Returns:
            Dictionary containing security analysis results
        """
        try:
            if target_pid:
                events = [e for e in events if e.get('tgid') == target_pid]
            
            # Initialize analysis structure
            analysis = {
                'sensitive_data_access': [],
                'permission_patterns': {},
                'suspicious_activities': [],
                'file_access_patterns': {},
                'network_security': {},
                'privilege_escalation': [],
                'summary': {}
            }
            
            # Analyze different security aspects
            analysis['sensitive_data_access'] = self._analyze_sensitive_data_access(events, sensitive_resources)
            analysis['file_access_patterns'] = self._analyze_file_access_patterns(events)
            analysis['network_security'] = self._analyze_network_security(events)
            analysis['suspicious_activities'] = self._detect_suspicious_activities(events)
            analysis['privilege_escalation'] = self._detect_privilege_escalation(events)
            
            # Generate summary
            analysis['summary'] = self._generate_security_summary(analysis)
            
            return self._make_json_serializable(analysis)
            
        except Exception as e:
            self.logger.error(f"Error in security analysis: {str(e)}")
            return {'error': f'Security analysis failed: {str(e)}'}
    
    def _analyze_sensitive_data_access(self, events, sensitive_resources):
        """Analyze access to sensitive data sources"""
        sensitive_accesses = []
        
        if not sensitive_resources:
            return sensitive_accesses
        
        for event in events:
            sensitive_type = SensitiveDataUtils.check_sensitive_resource(
                event, sensitive_resources, self.logger
            )
            
            if sensitive_type:
                access_info = {
                    'timestamp': event.get('timestamp'),
                    'process': event.get('process', 'unknown'),
                    'pid': event.get('tgid'),
                    'event_type': event.get('event'),
                    'sensitive_type': sensitive_type,
                    'device_id': DeviceUtils.get_device_identifier(event),
                    'pathname': event.get('details', {}).get('pathname'),
                    'access_type': 'read' if 'read' in event.get('event', '') else 'write' if 'write' in event.get('event', '') else 'ioctl'
                }
                sensitive_accesses.append(access_info)
        
        return sensitive_accesses
    
    def _analyze_file_access_patterns(self, events):
        """Analyze file access patterns for security implications"""
        patterns = {
            'system_file_access': [],
            'config_file_access': [],
            'temp_file_creation': [],
            'hidden_file_access': [],
            'executable_access': []
        }
        
        system_paths = ['/system/', '/vendor/', '/data/system/', '/proc/', '/sys/']
        config_paths = ['/data/data/', '/sdcard/', '/storage/', '/etc/']
        temp_paths = ['/tmp/', '/data/local/tmp/', '/cache/']
        
        for event in events:
            details = event.get('details', {})
            pathname = details.get('pathname', '')
            
            if not pathname:
                continue
            
            event_info = {
                'timestamp': event.get('timestamp'),
                'process': event.get('process', 'unknown'),
                'pid': event.get('tgid'),
                'event_type': event.get('event'),
                'pathname': pathname,
                'access_type': 'read' if 'read' in event.get('event', '') else 'write' if 'write' in event.get('event', '') else 'other'
            }
            
            # Check for system file access
            if any(pathname.startswith(path) for path in system_paths):
                patterns['system_file_access'].append(event_info)
            
            # Check for config file access
            elif any(pathname.startswith(path) for path in config_paths):
                patterns['config_file_access'].append(event_info)
            
            # Check for temp file creation
            elif any(pathname.startswith(path) for path in temp_paths):
                patterns['temp_file_creation'].append(event_info)
            
            # Check for hidden files (starting with .)
            elif '.' in pathname and pathname.split('/')[-1].startswith('.'):
                patterns['hidden_file_access'].append(event_info)
            
            # Check for executable files
            elif pathname.endswith(('.so', '.bin', '.exe', '.apk')):
                patterns['executable_access'].append(event_info)
        
        # Limit results for performance
        for key in patterns:
            patterns[key] = patterns[key][:100]  # Keep top 100 of each type
        
        return patterns
    
    def _analyze_network_security(self, events):
        """Analyze network activity for security implications"""
        network_security = {
            'external_connections': [],
            'suspicious_ports': [],
            'connection_patterns': {},
            'data_exfiltration_risk': []
        }
        
        suspicious_ports = [22, 23, 443, 8080, 8443, 9999]  # Common suspicious ports
        
        for event in events:
            event_name = event.get('event', '')
            details = event.get('details', {})
            
            if 'inet_sock_set_state' in event_name:
                daddr = details.get('daddr', '')
                dport = details.get('dport', 0)
                saddr = details.get('saddr', '')
                sport = details.get('sport', 0)
                
                connection_info = {
                    'timestamp': event.get('timestamp'),
                    'process': event.get('process', 'unknown'),
                    'pid': event.get('tgid'),
                    'source_addr': saddr,
                    'source_port': sport,
                    'dest_addr': daddr,
                    'dest_port': dport,
                    'state_change': f"{details.get('oldstate', 'unknown')} -> {details.get('newstate', 'unknown')}"
                }
                
                # Check for external connections (non-loopback)
                if daddr and not daddr.startswith('127.') and not daddr.startswith('::1'):
                    network_security['external_connections'].append(connection_info)
                
                # Check for suspicious ports
                if dport in suspicious_ports or sport in suspicious_ports:
                    network_security['suspicious_ports'].append(connection_info)
            
            # Check for large data transfers (potential exfiltration)
            elif event_name in ['tcp_sendmsg', 'udp_sendmsg']:
                size = details.get('size', 0)
                if isinstance(size, str):
                    try:
                        size = int(size)
                    except ValueError:
                        size = 0
                
                if size > 1024 * 1024:  # > 1MB
                    network_security['data_exfiltration_risk'].append({
                        'timestamp': event.get('timestamp'),
                        'process': event.get('process', 'unknown'),
                        'pid': event.get('tgid'),
                        'size_bytes': size,
                        'size_mb': round(size / (1024 * 1024), 2),
                        'protocol': 'TCP' if 'tcp' in event_name else 'UDP'
                    })
        
        return network_security
    
    def _detect_suspicious_activities(self, events):
        """Detect various suspicious activity patterns"""
        suspicious_activities = []
        
        # Track process activities for pattern detection
        process_activities = defaultdict(list)
        for event in events:
            pid = event.get('tgid')
            if pid:
                process_activities[pid].append(event)
        
        for pid, activities in process_activities.items():
            process_name = activities[0].get('process', 'unknown') if activities else 'unknown'
            
            # Suspicious pattern 1: Rapid file system scanning
            file_accesses = [e for e in activities if e.get('event') in ['read_probe', 'ioctl_probe']]
            if len(file_accesses) > 1000:
                suspicious_activities.append({
                    'type': 'rapid_filesystem_scanning',
                    'pid': pid,
                    'process': process_name,
                    'description': f'Process accessed {len(file_accesses)} files rapidly',
                    'severity': 'medium',
                    'event_count': len(file_accesses)
                })
            
            # Suspicious pattern 2: Unusual network activity
            network_events = [e for e in activities if any(keyword in e.get('event', '').lower() 
                                                         for keyword in ['tcp', 'udp', 'inet', 'sock'])]
            if len(network_events) > 500:
                suspicious_activities.append({
                    'type': 'high_network_activity',
                    'pid': pid,
                    'process': process_name,
                    'description': f'Process generated {len(network_events)} network events',
                    'severity': 'medium',
                    'event_count': len(network_events)
                })
            
            # Suspicious pattern 3: Mixed read/write on system files
            system_writes = []
            for event in activities:
                if 'write' in event.get('event', ''):
                    pathname = event.get('details', {}).get('pathname', '')
                    if pathname and (pathname.startswith('/system/') or pathname.startswith('/vendor/')):
                        system_writes.append(event)
            
            if system_writes:
                suspicious_activities.append({
                    'type': 'system_file_modification',
                    'pid': pid,
                    'process': process_name,
                    'description': f'Process attempted to write to {len(system_writes)} system files',
                    'severity': 'high',
                    'event_count': len(system_writes)
                })
        
        return suspicious_activities
    
    def _detect_privilege_escalation(self, events):
        """Detect potential privilege escalation attempts"""
        escalation_attempts = []
        
        for event in events:
            event_name = event.get('event', '')
            details = event.get('details', {})
            
            # Look for su/sudo attempts
            if 'execve' in event_name:
                pathname = details.get('pathname', '')
                if pathname and ('su' in pathname or 'sudo' in pathname):
                    escalation_attempts.append({
                        'type': 'su_sudo_execution',
                        'timestamp': event.get('timestamp'),
                        'process': event.get('process', 'unknown'),
                        'pid': event.get('tgid'),
                        'executed_path': pathname,
                        'description': 'Attempted to execute privilege escalation binary'
                    })
            
            # Look for setuid/setgid operations
            elif 'setuid' in event_name or 'setgid' in event_name:
                escalation_attempts.append({
                    'type': 'uid_gid_change',
                    'timestamp': event.get('timestamp'),
                    'process': event.get('process', 'unknown'),
                    'pid': event.get('tgid'),
                    'operation': event_name,
                    'description': 'Attempted to change user/group ID'
                })
        
        return escalation_attempts
    
    def _generate_security_summary(self, analysis):
        """Generate security analysis summary"""
        summary = {
            'total_sensitive_accesses': len(analysis.get('sensitive_data_access', [])),
            'total_suspicious_activities': len(analysis.get('suspicious_activities', [])),
            'total_privilege_escalation_attempts': len(analysis.get('privilege_escalation', [])),
            'security_risk_level': 'low',
            'key_findings': []
        }
        
        # Determine risk level
        high_risk_indicators = 0
        medium_risk_indicators = 0
        
        # Count high-risk indicators
        if summary['total_sensitive_accesses'] > 10:
            high_risk_indicators += 1
            summary['key_findings'].append(f"High sensitive data access: {summary['total_sensitive_accesses']} accesses")
        
        if summary['total_privilege_escalation_attempts'] > 0:
            high_risk_indicators += 1
            summary['key_findings'].append(f"Privilege escalation attempts detected: {summary['total_privilege_escalation_attempts']}")
        
        # Count medium-risk indicators
        suspicious_activities = analysis.get('suspicious_activities', [])
        high_severity_suspicious = [a for a in suspicious_activities if a.get('severity') == 'high']
        if high_severity_suspicious:
            medium_risk_indicators += 1
            summary['key_findings'].append(f"High-severity suspicious activities: {len(high_severity_suspicious)}")
        
        network_security = analysis.get('network_security', {})
        if len(network_security.get('external_connections', [])) > 10:
            medium_risk_indicators += 1
            summary['key_findings'].append(f"Multiple external connections: {len(network_security.get('external_connections', []))}")
        
        # Determine overall risk level
        if high_risk_indicators >= 2:
            summary['security_risk_level'] = 'high'
        elif high_risk_indicators >= 1 or medium_risk_indicators >= 3:
            summary['security_risk_level'] = 'medium'
        elif medium_risk_indicators >= 1:
            summary['security_risk_level'] = 'low-medium'
        
        # Add general findings
        file_patterns = analysis.get('file_access_patterns', {})
        system_accesses = len(file_patterns.get('system_file_access', []))
        if system_accesses > 0:
            summary['key_findings'].append(f"System file accesses: {system_accesses}")
        
        return summary