"""
Security Analysis Module
Analyzes security-related events for threat detection
"""

from .base_utils import BaseAnalyzer


class SecurityAnalyzer(BaseAnalyzer):
    """Security event analysis for threat detection"""
    
    def __init__(self, config_class):
        super().__init__(config_class, "SecurityAnalyzer")
    
    def analyze_security_events(self, events, target_pid=None):
        """
        Analyze security-related events for threat detection based on available events

        Args:
            events: List of parsed events
            target_pid: Optional target process ID to filter

        Returns:
            Dictionary with security analysis results
        """
        security_analysis = {
            'suspicious_file_access': [],
            'sensitive_data_access': [],
            'binder_communications': [],
            'ioctl_operations': [],
            'privilege_escalation': [],
            'debugging_attempts': [],
            'memory_protection_changes': [],
            'capability_changes': [],
            'suspicious_activity': [],
            'summary': {}
        }

        # Track suspicious patterns based on available events
        suspicious_paths = set()
        binder_activity = []
        ioctl_activity = []
        file_access_patterns = {}

        for event in events:
            if target_pid and event.get('tgid') != target_pid:
                continue

            event_name = event.get('event', '')
            details = event.get('details', {})
            pathname = details.get('pathname', '')
            timestamp = event.get('timestamp')
            pid = event.get('tgid')
            process = event.get('process', '')

            # Analyze file access patterns
            if event_name in ['read_probe', 'write_probe']:
                # Check for suspicious file paths
                if pathname and any(suspicious in pathname.lower() for suspicious in [
                    'passwd', 'shadow', 'sudoers', 'keys', 'private', 'secret',
                    'credential', 'token', 'config', 'etc', 'system'
                ]):
                    security_analysis['suspicious_file_access'].append({
                        'type': f'suspicious_{event_name}',
                        'timestamp': timestamp,
                        'pid': pid,
                        'process': process,
                        'pathname': pathname,
                        'operation': event_name.replace('_probe', ''),
                        'details': details
                    })
                    suspicious_paths.add(pathname)

                # Track file access frequency per process
                if pid not in file_access_patterns:
                    file_access_patterns[pid] = {'read': 0, 'write': 0, 'paths': set()}

                if event_name == 'read_probe':
                    file_access_patterns[pid]['read'] += 1
                else:
                    file_access_patterns[pid]['write'] += 1

                file_access_patterns[pid]['paths'].add(pathname)

            # Analyze Binder communications (Android IPC)
            elif event_name == 'binder_transaction':
                binder_activity.append({
                    'timestamp': timestamp,
                    'pid': pid,
                    'process': process,
                    'transaction': details.get('transaction'),
                    'details': details
                })

                # Check for excessive binder activity (potential malicious IPC)
                if len(binder_activity) > 50:  # Threshold for suspicious activity
                    security_analysis['suspicious_activity'].append({
                        'type': 'excessive_binder_activity',
                        'timestamp': timestamp,
                        'process': process,
                        'details': f'High frequency of binder transactions detected'
                    })

            # Analyze IOCTL operations
            elif event_name == 'ioctl_probe':
                ioctl_activity.append({
                    'timestamp': timestamp,
                    'pid': pid,
                    'process': process,
                    'pathname': pathname,
                    'details': details
                })

                # Check for potentially dangerous device access
                if pathname and any(device in pathname.lower() for device in [
                    'mem', 'kmem', 'port', 'random', 'urandom', 'zero', 'null'
                ]):
                    security_analysis['ioctl_operations'].append({
                        'type': 'device_access',
                        'timestamp': timestamp,
                        'pid': pid,
                        'process': process,
                        'device': pathname,
                        'details': details
                    })

        # Analyze file access patterns for anomalies
        for pid, patterns in file_access_patterns.items():
            # High read/write ratio might indicate data exfiltration
            total_operations = patterns['read'] + patterns['write']
            if total_operations > 100:  # High activity threshold
                read_ratio = patterns['read'] / total_operations
                if read_ratio > 0.8:  # More than 80% reads
                    security_analysis['suspicious_activity'].append({
                        'type': 'potential_data_exfiltration',
                        'timestamp': timestamp,
                        'pid': pid,
                        'details': f'High read activity: {patterns["read"]} reads, {patterns["write"]} writes'
                    })
                elif patterns['write'] > patterns['read'] * 3:  # Much more writes than reads
                    security_analysis['suspicious_activity'].append({
                        'type': 'potential_data_corruption',
                        'timestamp': timestamp,
                        'pid': pid,
                        'details': f'High write activity: {patterns["write"]} writes, {patterns["read"]} reads'
                    })

            # Access to many different paths might indicate reconnaissance
            if len(patterns['paths']) > 20:
                security_analysis['suspicious_activity'].append({
                    'type': 'broad_file_system_access',
                    'timestamp': timestamp,
                    'pid': pid,
                    'details': f'Access to {len(patterns["paths"])} different file paths'
                })

        # Store binder and ioctl data
        security_analysis['binder_communications'] = binder_activity
        security_analysis['ioctl_operations'] = ioctl_activity

        # Generate summary
        security_analysis['summary'] = {
            'total_suspicious_file_access': len(security_analysis['suspicious_file_access']),
            'total_binder_transactions': len(binder_activity),
            'total_ioctl_operations': len(ioctl_activity),
            'total_privilege_escalations': len(security_analysis['privilege_escalation']),
            'total_debugging_attempts': len(security_analysis['debugging_attempts']),
            'total_memory_changes': len(security_analysis['memory_protection_changes']),
            'total_capability_changes': len(security_analysis['capability_changes']),
            'total_suspicious_activities': len(security_analysis['suspicious_activity']),
            'suspicious_paths_count': len(suspicious_paths),
            'risk_level': self._calculate_risk_level_from_file_analysis(security_analysis)
        }

        return self._make_json_serializable(security_analysis)

    def _calculate_risk_level_from_file_analysis(self, security_analysis):
        """Calculate risk level based on file access analysis"""
        score = 0

        # Suspicious file access is medium risk
        score += len(security_analysis['suspicious_file_access']) * 5

        # Excessive binder activity is high risk
        score += len(security_analysis['binder_communications']) * 3

        # IOCTL operations on sensitive devices is high risk
        score += len(security_analysis['ioctl_operations']) * 8

        # General suspicious activities
        score += len(security_analysis['suspicious_activity']) * 6

        if score >= 30:
            return 'HIGH'
        elif score >= 15:
            return 'MEDIUM'
        elif score > 0:
            return 'LOW'
        else:
            return 'NONE'

    def _calculate_risk_level(self, security_analysis):
        """Calculate overall risk level based on security events"""
        score = 0

        # Privilege escalation is high risk
        score += len(security_analysis['privilege_escalation']) * 10

        # Debugging attempts are medium risk
        score += len(security_analysis['debugging_attempts']) * 5

        # Suspicious memory operations are high risk
        score += len(security_analysis['suspicious_activity']) * 8

        # Capability changes are medium risk
        score += len(security_analysis['capability_changes']) * 3

        if score >= 20:
            return 'HIGH'
        elif score >= 10:
            return 'MEDIUM'
        elif score > 0:
            return 'LOW'
        else:
            return 'NONE'
