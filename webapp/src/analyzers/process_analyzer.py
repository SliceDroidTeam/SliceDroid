"""
Process Analyzer - Analyzes process genealogy and relationships.

This module consolidates process analysis functionality to understand
process hierarchies, relationships, and execution patterns.
"""

from collections import defaultdict, Counter
from .base_analyzer import BaseAnalyzer


class ProcessAnalyzer(BaseAnalyzer):
    """Process genealogy and relationship analysis"""
    
    def __init__(self, config_class):
        super().__init__(config_class, "ProcessAnalyzer")
    
    def analyze_process_genealogy(self, events, target_pid=None):
        """
        Analyze process relationships and genealogy
        
        Args:
            events: List of events to analyze
            target_pid: Optional target process ID to focus on
            
        Returns:
            Dictionary containing process analysis results
        """
        try:
            # Initialize analysis structure
            analysis = {
                'process_tree': {},
                'process_stats': {},
                'relationships': [],
                'execution_patterns': {},
                'suspicious_patterns': [],
                'summary': {}
            }
            
            # Track processes and their relationships
            processes = {}
            parent_child_relationships = defaultdict(list)
            process_activities = defaultdict(list)
            
            # Extract process information from events
            for event in events:
                if target_pid and event.get('tgid') != target_pid:
                    continue
                
                pid = event.get('tgid')
                tid = event.get('tid')
                process_name = event.get('process', 'unknown')
                event_type = event.get('event', 'unknown')
                timestamp = event.get('timestamp')
                
                if pid:
                    # Track process information
                    if pid not in processes:
                        processes[pid] = {
                            'pid': pid,
                            'name': process_name,
                            'first_seen': timestamp,
                            'last_seen': timestamp,
                            'event_count': 0,
                            'event_types': set(),
                            'threads': set()
                        }
                    
                    # Update process info
                    processes[pid]['last_seen'] = timestamp
                    processes[pid]['event_count'] += 1
                    processes[pid]['event_types'].add(event_type)
                    
                    if tid:
                        processes[pid]['threads'].add(tid)
                    
                    # Track process activities
                    process_activities[pid].append({
                        'timestamp': timestamp,
                        'event': event_type,
                        'tid': tid
                    })
                
                # Look for process creation/termination events
                if event_type in ['fork', 'clone', 'execve', 'exit']:
                    details = event.get('details', {})
                    if event_type in ['fork', 'clone']:
                        child_pid = details.get('child_pid') or details.get('ret')
                        if child_pid and child_pid > 0:
                            parent_child_relationships[pid].append(child_pid)
            
            # Build process tree
            analysis['process_tree'] = self._build_process_tree(parent_child_relationships, processes)
            
            # Generate process statistics
            analysis['process_stats'] = self._generate_process_stats(processes)
            
            # Analyze execution patterns
            analysis['execution_patterns'] = self._analyze_execution_patterns(process_activities)
            
            # Detect suspicious patterns
            analysis['suspicious_patterns'] = self._detect_suspicious_patterns(processes, process_activities)
            
            # Generate summary
            analysis['summary'] = self._generate_process_summary(processes, parent_child_relationships)
            
            return self._make_json_serializable(analysis)
            
        except Exception as e:
            self.logger.error(f"Error in process analysis: {str(e)}")
            return {'error': f'Process analysis failed: {str(e)}'}
    
    def _build_process_tree(self, relationships, processes):
        """Build hierarchical process tree"""
        tree = {}
        
        # Find root processes (those without parents in our data)
        all_children = set()
        for children in relationships.values():
            all_children.update(children)
        
        root_pids = set(relationships.keys()) - all_children
        
        def build_node(pid):
            if pid not in processes:
                return None
            
            node = {
                'pid': pid,
                'name': processes[pid]['name'],
                'event_count': processes[pid]['event_count'],
                'thread_count': len(processes[pid]['threads']),
                'children': []
            }
            
            # Add children recursively
            for child_pid in relationships.get(pid, []):
                child_node = build_node(child_pid)
                if child_node:
                    node['children'].append(child_node)
            
            return node
        
        # Build tree from roots
        for root_pid in root_pids:
            node = build_node(root_pid)
            if node:
                tree[root_pid] = node
        
        # Add orphaned processes
        for pid in processes:
            if pid not in all_children and pid not in root_pids:
                node = build_node(pid)
                if node:
                    tree[pid] = node
        
        return tree
    
    def _generate_process_stats(self, processes):
        """Generate detailed process statistics"""
        if not processes:
            return {}
        
        # Convert sets to lists for JSON serialization
        process_stats = []
        for pid, info in processes.items():
            stats = {
                'pid': pid,
                'name': info['name'],
                'event_count': info['event_count'],
                'thread_count': len(info['threads']),
                'unique_event_types': len(info['event_types']),
                'event_types': list(info['event_types']),
                'threads': list(info['threads']),
                'first_seen': info['first_seen'],
                'last_seen': info['last_seen']
            }
            
            # Calculate activity duration
            if info['first_seen'] and info['last_seen']:
                try:
                    first = float(info['first_seen']) if isinstance(info['first_seen'], str) else info['first_seen']
                    last = float(info['last_seen']) if isinstance(info['last_seen'], str) else info['last_seen']
                    stats['duration_seconds'] = last - first
                except (ValueError, TypeError):
                    stats['duration_seconds'] = 0
            else:
                stats['duration_seconds'] = 0
            
            process_stats.append(stats)
        
        # Sort by event count (most active first)
        process_stats.sort(key=lambda x: x['event_count'], reverse=True)
        
        return {
            'processes': process_stats,
            'total_processes': len(processes),
            'most_active_process': process_stats[0] if process_stats else None
        }
    
    def _analyze_execution_patterns(self, process_activities):
        """Analyze process execution patterns"""
        patterns = {
            'burst_activities': [],
            'long_running_processes': [],
            'frequent_context_switches': [],
            'thread_patterns': {}
        }
        
        for pid, activities in process_activities.items():
            if len(activities) < 5:  # Skip processes with too few events
                continue
            
            # Sort activities by timestamp
            try:
                activities.sort(key=lambda x: float(x['timestamp']) if isinstance(x['timestamp'], str) else x['timestamp'])
            except (ValueError, TypeError):
                continue
            
            # Analyze for burst activity (many events in short time)
            if len(activities) > 100:
                # Check if 80% of events happen in 20% of the time span
                try:
                    first_time = float(activities[0]['timestamp']) if isinstance(activities[0]['timestamp'], str) else activities[0]['timestamp']
                    last_time = float(activities[-1]['timestamp']) if isinstance(activities[-1]['timestamp'], str) else activities[-1]['timestamp']
                    duration = last_time - first_time
                    
                    if duration > 0:
                        # Count events in first 20% of time
                        burst_threshold = first_time + (duration * 0.2)
                        burst_events = sum(1 for a in activities 
                                         if (float(a['timestamp']) if isinstance(a['timestamp'], str) else a['timestamp']) <= burst_threshold)
                        
                        if burst_events > len(activities) * 0.8:
                            patterns['burst_activities'].append({
                                'pid': pid,
                                'total_events': len(activities),
                                'burst_events': burst_events,
                                'burst_percentage': (burst_events / len(activities)) * 100
                            })
                except (ValueError, TypeError):
                    continue
            
            # Analyze thread patterns
            threads = set(a['tid'] for a in activities if a['tid'])
            if len(threads) > 1:
                patterns['thread_patterns'][pid] = {
                    'thread_count': len(threads),
                    'threads': list(threads),
                    'events_per_thread': {tid: sum(1 for a in activities if a['tid'] == tid) for tid in threads}
                }
        
        return patterns
    
    def _detect_suspicious_patterns(self, processes, process_activities):
        """Detect potentially suspicious process patterns"""
        suspicious = []
        
        for pid, info in processes.items():
            activities = process_activities.get(pid, [])
            
            # Suspicious pattern 1: Very high event count in short time
            if info['event_count'] > 10000:
                try:
                    if info['first_seen'] and info['last_seen']:
                        first = float(info['first_seen']) if isinstance(info['first_seen'], str) else info['first_seen']
                        last = float(info['last_seen']) if isinstance(info['last_seen'], str) else info['last_seen']
                        duration = last - first
                        
                        if duration > 0 and duration < 10:  # Less than 10 seconds
                            suspicious.append({
                                'type': 'high_frequency_activity',
                                'pid': pid,
                                'process': info['name'],
                                'description': f"Very high activity: {info['event_count']} events in {duration:.2f} seconds",
                                'severity': 'medium'
                            })
                except (ValueError, TypeError):
                    pass
            
            # Suspicious pattern 2: Unusual event type combinations
            event_types = info['event_types']
            if 'execve' in event_types and 'exit' in event_types and len(event_types) < 5:
                suspicious.append({
                    'type': 'short_lived_execution',
                    'pid': pid,
                    'process': info['name'],
                    'description': f"Short-lived process with exec/exit pattern",
                    'severity': 'low'
                })
            
            # Suspicious pattern 3: Many threads
            if len(info['threads']) > 50:
                suspicious.append({
                    'type': 'high_thread_count',
                    'pid': pid,
                    'process': info['name'],
                    'description': f"High thread count: {len(info['threads'])} threads",
                    'severity': 'low'
                })
        
        return suspicious
    
    def _generate_process_summary(self, processes, relationships):
        """Generate process analysis summary"""
        if not processes:
            return {}
        
        total_processes = len(processes)
        total_events = sum(p['event_count'] for p in processes.values())
        total_threads = sum(len(p['threads']) for p in processes.values())
        
        # Most active process
        most_active = max(processes.items(), key=lambda x: x[1]['event_count'])
        
        # Process with most threads
        most_threaded = max(processes.items(), key=lambda x: len(x[1]['threads']))
        
        # Relationship stats
        total_relationships = sum(len(children) for children in relationships.values())
        
        return {
            'total_processes': total_processes,
            'total_events': total_events,
            'total_threads': total_threads,
            'total_relationships': total_relationships,
            'average_events_per_process': total_events / total_processes if total_processes > 0 else 0,
            'average_threads_per_process': total_threads / total_processes if total_processes > 0 else 0,
            'most_active_process': {
                'pid': most_active[0],
                'name': most_active[1]['name'],
                'event_count': most_active[1]['event_count']
            },
            'most_threaded_process': {
                'pid': most_threaded[0],
                'name': most_threaded[1]['name'],
                'thread_count': len(most_threaded[1]['threads'])
            }
        }