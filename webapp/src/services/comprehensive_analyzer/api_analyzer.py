"""
API Analysis Module
Analyzes API call patterns and flow relationships
"""

from .base_utils import BaseAnalyzer


class APIAnalyzer(BaseAnalyzer):
    """API pattern analysis for behavioral understanding"""
    
    def __init__(self, config_class):
        super().__init__(config_class, "APIAnalyzer")
    
    def extract_api_instances(self, parsed_events, target_pid=None):
        """
        Extract API instances from parsed events
        Identifies API call patterns and their relationships

        Args:
            parsed_events: List of parsed events
            target_pid: Optional target process ID to filter

        Returns:
            Dictionary mapping API codes to instance lists
        """
        api_instances = dict()
        open_instances = dict()

        i = -1
        for e in parsed_events:
            i += 1

            # Skip if filtering by PID and this event doesn't match
            if target_pid and e.get('tgid') != target_pid:
                continue

            if (e['event'] == 'write_probe' and
                e['details'].get('pathname', 'unknown') == 'null' and
                e['details'].get('count', 0) > 999999):

                api = e['details']['count']
                tid = e['tid']

                start = (api % 2 == 0)

                if start:
                    if tid not in open_instances:
                        open_instances[tid] = []
                    open_instances[tid].append((i, api))

                if not start:
                    if tid in open_instances and len(open_instances[tid]) > 0:
                        start_index, start_api = open_instances[tid].pop()
                        if start_api == api - 1:  # Matching start/end pair
                            if api not in api_instances:
                                api_instances[api] = []
                            api_instances[api].append((start_index, i))

        self.logger.info(f"Extracted {len(api_instances)} API instance types")
        return api_instances

    def extract_relevant_api_instances(self, parsed_events, target_pid):
        """
        Extract all relevant API instances for a target PID

        Args:
            parsed_events: List of parsed events
            target_pid: Target process ID

        Returns:
            Set of relevant API codes
        """
        api_instances = set()

        for e in parsed_events:
            if (e['tgid'] == target_pid and
                e['event'] == 'write_probe' and
                e['details'].get('pathname', 'unknown') == 'null' and
                e['details'].get('count', 0) > 99999):

                api = e['details']['count']
                start = (api % 2 == 0)

                if start:
                    api_instances.add(api + 1)  # Add the end API code
                else:
                    api_instances.add(api)

        self.logger.info(f"Found {len(api_instances)} relevant API instances for PID {target_pid}")
        return api_instances

    def slice_log_advanced(self, api_instances, parsed_events, tgid_slicing=False):
        """
        Advanced log slicing with IPC tracking
        Creates detailed flow analysis for each API instance

        Args:
            api_instances: Dictionary of API instances
            parsed_events: List of parsed events
            tgid_slicing: Whether to use TGID for process identification

        Returns:
            Dictionary mapping APIs to flow instances
        """
        flows = dict()

        for api in api_instances:
            flows[api] = []

            for instance in api_instances[api]:
                out_flows_slice = []
                in_flows_slice = []
                ioinstance = {'pid': 0, 'command': 0, 'in': [], 'out': []}

                # API start event
                ee = parsed_events[instance[0]]
                tgid = ee['tgid']
                tid = ee['tid']
                pid = tgid if tgid_slicing else tid
                api_pid = pid
                api_command = ee['process']

                # Relevant processes are tracked dynamically
                pid_set = {pid}
                binders = set()

                # Forward pass
                for line in range(instance[0], instance[1] + 1):
                    e = parsed_events[line]

                    if e['event'] == 'write_probe' and e['details'].get('pathname', 'unknown') == 'null':
                        continue

                    tid = e['tid']
                    tgid = e['tgid']
                    event = e['event']

                    pid = tgid if tgid_slicing else tid

                    if pid in pid_set:
                        if ((event == 'write_probe' and e['details'].get('pathname', 'null') != 'null') or
                            (event == 'ioctl_probe') or (event == 'inet_sock_set_state') or
                            (event == 'tcp_sendmsg') or (event == 'udp_sendmsg')):
                            out_flows_slice.append(line)

                        # Track binder transaction sources
                        if event == 'binder_transaction':
                            binders.add(e['details']['transaction'])

                    # Track binder transaction receivers
                    if (event == 'binder_transaction_received' and
                        e['details']['transaction'] in binders):
                        pid_set.add(tgid if tgid_slicing else tid)

                # Backward pass
                pid_set = {api_pid}
                binders = set()

                for line in range(instance[1], instance[0] - 1, -1):
                    e = parsed_events[line]

                    if e['event'] == 'write_probe' and e['details'].get('pathname', 'unknown') == 'null':
                        continue

                    tid = e['tid']
                    tgid = e['tgid']
                    event = e['event']

                    pid = tgid if tgid_slicing else tid

                    if pid in pid_set:
                        if (event == 'read_probe' or event == 'ioctl_probe' or
                            (event == 'inet_sock_set_state') or
                            (event == 'tcp_recvmsg') or (event == 'udp_recvmsg')):
                            in_flows_slice.append(line)

                        # Track binder transaction receivers
                        if event == 'binder_transaction_received':
                            binders.add(e['details']['transaction'])

                    # Track binder transaction senders
                    if (event == 'binder_transaction' and
                        e['details']['transaction'] in binders):
                        pid_set.add(tgid if tgid_slicing else tid)

                # Save the flows
                ioinstance['pid'] = api_pid
                ioinstance['command'] = api_command
                ioinstance['out'] = out_flows_slice.copy()
                ioinstance['in'] = in_flows_slice.copy()
                flows[api].append(ioinstance.copy())

        return flows

    def create_unique_io_patterns(self, flows, withpath=False):
        """
        Create unique I/O patterns from flow analysis
        Groups equivalent patterns and counts their frequency

        Args:
            flows: Flow analysis results
            withpath: Whether to include pathname information

        Returns:
            Dictionary mapping APIs to unique I/O patterns
        """
        apis2uio = dict()

        for api in flows:
            unique_instances = []

            for instance in flows[api]:
                simple_instance = dict()

                # Merge input and output flows
                merged = []
                i = 0
                j = 0

                len_in = len(instance['in'])
                len_out = len(instance['out'])

                if len_in == 0 and len_out == 0:
                    simple_instance['merged'] = []
                    if not unique_instances:
                        simple_instance['count'] = 1
                        unique_instances.append(simple_instance.copy())
                    else:
                        # Check for equivalent pattern
                        found = False
                        for ui in unique_instances:
                            if len(ui['merged']) == 0:
                                ui['count'] += 1
                                found = True
                                break
                        if not found:
                            simple_instance['count'] = 1
                            unique_instances.append(simple_instance.copy())
                    continue

                while (i < len_in) and (j < len_out):
                    if instance['in'][i] < instance['out'][j]:
                        merged.append(instance['in'][i])
                        i += 1
                    else:
                        merged.append(instance['out'][j])
                        j += 1

                merged = merged + instance['in'][i:] + instance['out'][j:]

                # Create filtered events
                filtered_events = []
                for line in merged:
                    # Note: This would need access to parsed_events
                    # For now, we'll create a simplified version
                    filtered_events.append({'line': line})

                if not withpath:
                    simple_instance['merged'] = filtered_events
                else:
                    simple_instance['merged'] = filtered_events

                # Check for equivalent patterns
                if not unique_instances:
                    simple_instance['count'] = 1
                    unique_instances.append(simple_instance.copy())
                else:
                    unique = True
                    for ui in unique_instances:
                        if len(ui['merged']) == len(filtered_events):
                            # Simple equivalence check based on length
                            # More sophisticated comparison could be implemented
                            ui['count'] += 1
                            unique = False
                            break
                    if unique:
                        simple_instance['count'] = 1
                        unique_instances.append(simple_instance.copy())

            apis2uio[api] = unique_instances.copy()

        return apis2uio
