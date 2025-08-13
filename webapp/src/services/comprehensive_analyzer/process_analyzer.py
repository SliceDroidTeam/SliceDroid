"""
Process Analysis Module
Analyzes process creation, execution patterns and genealogy
"""

from .base_utils import BaseAnalyzer


class ProcessAnalyzer(BaseAnalyzer):
    """Process genealogy and activity analysis"""
    
    def __init__(self, config_class):
        super().__init__(config_class, "ProcessAnalyzer")
    
    def analyze_process_genealogy(self, events, target_pid=None):
        """
        Analyze process patterns based on available events (file access and IPC)

        Args:
            events: List of parsed events
            target_pid: Optional target process ID to filter

        Returns:
            Dictionary with process analysis results
        """
        genealogy_analysis = {
            'process_creations': [],
            'process_executions': [],
            'elf_loads': [],
            'process_tree': {},
            'execution_timeline': [],
            'process_activities': [],
            'ipc_communications': [],
            'summary': {}
        }

        # Track process activities and patterns
        process_activities = {}
        unique_processes = set()
        ipc_events = []
        file_operations = []

        for event in events:
            event_name = event.get('event', '')
            timestamp = event.get('timestamp')
            pid = event.get('tgid')
            tid = event.get('tid')
            process = event.get('process', '')
            details = event.get('details', {})

            unique_processes.add(pid)

            # Track process activity patterns
            if pid not in process_activities:
                process_activities[pid] = {
                    'process_name': process,
                    'first_seen': timestamp,
                    'last_seen': timestamp,
                    'total_events': 0,
                    'read_operations': 0,
                    'write_operations': 0,
                    'ioctl_operations': 0,
                    'binder_transactions': 0,
                    'unix_communications': 0,
                    'accessed_files': set(),
                    'communication_partners': set()
                }

            activity = process_activities[pid]
            activity['last_seen'] = timestamp
            activity['total_events'] += 1

            # Analyze different event types
            if event_name == 'read_probe':
                activity['read_operations'] += 1
                if details.get('pathname'):
                    activity['accessed_files'].add(details['pathname'])
                file_operations.append({
                    'timestamp': timestamp,
                    'pid': pid,
                    'process': process,
                    'operation': 'read',
                    'pathname': details.get('pathname', ''),
                    'details': details
                })

            elif event_name == 'write_probe':
                activity['write_operations'] += 1
                if details.get('pathname'):
                    activity['accessed_files'].add(details['pathname'])
                file_operations.append({
                    'timestamp': timestamp,
                    'pid': pid,
                    'process': process,
                    'operation': 'write',
                    'pathname': details.get('pathname', ''),
                    'details': details
                })

            elif event_name == 'ioctl_probe':
                activity['ioctl_operations'] += 1
                if details.get('pathname'):
                    activity['accessed_files'].add(details['pathname'])
                file_operations.append({
                    'timestamp': timestamp,
                    'pid': pid,
                    'process': process,
                    'operation': 'ioctl',
                    'pathname': details.get('pathname', ''),
                    'details': details
                })

            elif event_name == 'binder_transaction':
                activity['binder_transactions'] += 1
                ipc_events.append({
                    'timestamp': timestamp,
                    'pid': pid,
                    'process': process,
                    'type': 'binder',
                    'transaction': details.get('transaction'),
                    'details': details
                })

            elif event_name in ['unix_stream_sendmsg', 'unix_stream_recvmsg', 'unix_dgram_sendmsg', 'unix_dgram_recvmsg']:
                activity['unix_communications'] += 1
                peer_pid = details.get('topid') or details.get('frompid')
                if peer_pid:
                    activity['communication_partners'].add(peer_pid)

                ipc_events.append({
                    'timestamp': timestamp,
                    'pid': pid,
                    'process': process,
                    'type': event_name,
                    'peer_pid': peer_pid,
                    'details': details
                })

        # Convert sets to lists and calculate durations
        for pid, activity in process_activities.items():
            activity['accessed_files'] = list(activity['accessed_files'])
            activity['communication_partners'] = list(activity['communication_partners'])
            # Safe duration calculation with null checks
            if activity['last_seen'] is not None and activity['first_seen'] is not None:
                activity['duration'] = activity['last_seen'] - activity['first_seen']
            else:
                activity['duration'] = 0
            activity['files_accessed_count'] = len(activity['accessed_files'])
            activity['partners_count'] = len(activity['communication_partners'])

        # Build simplified process tree based on communication patterns
        process_tree = self._build_communication_tree(process_activities, ipc_events)

        genealogy_analysis['process_activities'] = list(process_activities.values())
        genealogy_analysis['ipc_communications'] = ipc_events
        genealogy_analysis['process_tree'] = process_tree

        # Generate summary
        genealogy_analysis['summary'] = self._analyze_process_patterns_from_activities(
            process_activities, ipc_events, file_operations, target_pid
        )

        return self._make_json_serializable(genealogy_analysis)

    def _build_communication_tree(self, process_activities, ipc_events):
        """Build a tree structure based on communication patterns"""
        tree = {}

        # Create nodes for each process
        for pid, activity in process_activities.items():
            tree[pid] = {
                'pid': pid,
                'process_name': activity['process_name'],
                'total_events': activity['total_events'],
                'duration': activity['duration'],
                'communication_partners': activity['communication_partners'],
                'children': []
            }

        # Add communication relationships as edges
        for event in ipc_events:
            if event['type'] in ['unix_stream_sendmsg', 'unix_dgram_sendmsg']:
                from_pid = event['pid']
                to_pid = event.get('peer_pid')
                if from_pid in tree and to_pid in tree:
                    # Add as child relationship (simplified)
                    if to_pid not in [child['pid'] for child in tree[from_pid]['children']]:
                        tree[from_pid]['children'].append({
                            'pid': to_pid,
                            'relationship': 'communication_target'
                        })

        return tree

    def _analyze_process_patterns_from_activities(self, process_activities, ipc_events, file_operations, target_pid):
        """Analyze process patterns from activity data"""
        total_processes = len(process_activities)
        total_file_ops = len(file_operations)
        total_ipc_events = len(ipc_events)

        # Find most active process
        most_active = None
        max_events = 0
        for pid, activity in process_activities.items():
            if activity['total_events'] > max_events:
                max_events = activity['total_events']
                most_active = {'pid': pid, 'events': max_events, 'name': activity['process_name']}

        # Detect interesting patterns
        interesting_patterns = []

        for pid, activity in process_activities.items():
            # High file access activity
            if activity['files_accessed_count'] > 50:
                interesting_patterns.append({
                    'type': 'high_file_access',
                    'description': f'Process {pid} ({activity["process_name"]}) accessed {activity["files_accessed_count"]} different files'
                })

            # Imbalanced read/write ratio
            total_rw = activity['read_operations'] + activity['write_operations']
            if total_rw > 100:
                read_ratio = activity['read_operations'] / total_rw
                if read_ratio > 0.9:
                    interesting_patterns.append({
                        'type': 'excessive_reading',
                        'description': f'Process {pid} has unusually high read activity ({activity["read_operations"]} reads vs {activity["write_operations"]} writes)'
                    })
                elif read_ratio < 0.1:
                    interesting_patterns.append({
                        'type': 'excessive_writing',
                        'description': f'Process {pid} has unusually high write activity ({activity["write_operations"]} writes vs {activity["read_operations"]} reads)'
                    })

            # High communication activity
            if activity['partners_count'] > 5:
                interesting_patterns.append({
                    'type': 'high_communication_activity',
                    'description': f'Process {pid} communicates with {activity["partners_count"]} different processes'
                })

        # Calculate activity frequency
        if total_file_ops > 1000:
            activity_frequency = 'HIGH'
        elif total_file_ops > 200:
            activity_frequency = 'MEDIUM'
        else:
            activity_frequency = 'LOW'

        return {
            'total_processes': total_processes,
            'total_file_operations': total_file_ops,
            'total_ipc_events': total_ipc_events,
            'total_forks': 0,  # Not available in current trace
            'total_execs': 0,  # Not available in current trace
            'process_tree_depth': min(3, total_processes),  # Simplified depth
            'most_active_process': most_active,
            'activity_frequency': activity_frequency,
            'interesting_patterns': interesting_patterns,
            'unique_processes': total_processes
        }

    def _build_process_tree(self, parent_child_map, process_info):
        """Build hierarchical process tree"""
        def build_subtree(pid, visited=None):
            if visited is None:
                visited = set()

            if pid in visited:
                return None  # Prevent infinite loops

            visited.add(pid)

            node = {
                'pid': pid,
                'info': process_info.get(pid, {}),
                'children': []
            }

            if pid in parent_child_map:
                for child_pid in parent_child_map[pid]:
                    child_node = build_subtree(child_pid, visited.copy())
                    if child_node:
                        node['children'].append(child_node)

            return node

        # Find root processes (those without parents in our data)
        all_children = set()
        for children in parent_child_map.values():
            all_children.update(children)

        root_pids = set(parent_child_map.keys()) - all_children

        tree = {}
        for root_pid in root_pids:
            tree[root_pid] = build_subtree(root_pid)

        return tree

    def _analyze_process_patterns(self, genealogy_analysis, target_pid):
        """Analyze process creation and execution patterns"""
        summary = {
            'total_forks': len(genealogy_analysis['process_creations']),
            'total_execs': len(genealogy_analysis['process_executions']),
            'total_elf_loads': len(genealogy_analysis['elf_loads']),
            'process_tree_depth': 0,
            'most_active_parent': None,
            'execution_frequency': 'LOW',
            'interesting_patterns': []
        }

        # Calculate tree depth
        def calculate_depth(tree, current_depth=0):
            max_depth = current_depth
            for node in tree.values():
                if node and 'children' in node:
                    for child in node['children']:
                        depth = calculate_depth({child['pid']: child}, current_depth + 1)
                        max_depth = max(max_depth, depth)
            return max_depth

        summary['process_tree_depth'] = calculate_depth(genealogy_analysis['process_tree'])

        # Find most active parent (most forks)
        parent_activity = {}
        for creation in genealogy_analysis['process_creations']:
            parent_pid = creation['parent_pid']
            if parent_pid not in parent_activity:
                parent_activity[parent_pid] = 0
            parent_activity[parent_pid] += 1

        if parent_activity:
            most_active_pid = max(parent_activity, key=parent_activity.get)
            summary['most_active_parent'] = {
                'pid': most_active_pid,
                'fork_count': parent_activity[most_active_pid]
            }

        # Calculate execution frequency
        total_execution_events = (summary['total_execs'] + summary['total_elf_loads'])
        if total_execution_events > 50:
            summary['execution_frequency'] = 'HIGH'
        elif total_execution_events > 10:
            summary['execution_frequency'] = 'MEDIUM'
        else:
            summary['execution_frequency'] = 'LOW'

        # Detect interesting patterns
        if summary['process_tree_depth'] > 5:
            summary['interesting_patterns'].append({
                'type': 'deep_process_tree',
                'description': f'Unusually deep process tree (depth: {summary["process_tree_depth"]})'
            })

        if summary['most_active_parent'] and summary['most_active_parent']['fork_count'] > 10:
            summary['interesting_patterns'].append({
                'type': 'excessive_forking',
                'description': f'Process {summary["most_active_parent"]["pid"]} created {summary["most_active_parent"]["fork_count"]} child processes'
            })

        if total_execution_events > 100:
            summary['interesting_patterns'].append({
                'type': 'high_execution_activity',
                'description': f'High number of execution events ({total_execution_events})'
            })

        return summary
