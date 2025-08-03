"""
Event Slicing Module
Advanced bidirectional event slicing algorithms for process relationship tracking
"""

from .base_utils import BaseAnalyzer


class EventSlicer(BaseAnalyzer):
    """Advanced event slicing for process relationship analysis"""
    
    def __init__(self, config_class):
        super().__init__(config_class, "EventSlicer")
    
    def slice_events(self, events, t_pid, asynchronous=True):
        """
        Advanced bidirectional event slicing algorithm
        Tracks process relationships through IPC mechanisms

        Args:
            events: List of parsed events
            t_pid: Target process ID
            asynchronous: Whether to allow asynchronous analysis

        Returns:
            List of filtered relevant events
        """
        # Relevant processes are tracked dynamically
        pid_set = {t_pid}
        binders = dict()
        unix_streams = dict()
        unix_dgrams_waiting = set()
        unix_dgrams = dict()

        tgid2source_tids = dict()

        out_flows_slice = []
        in_flows_slice = []

        # Forward slicing for output operations
        e_index = 0
        for e in events:
            tgid = e['tgid']
            tid = e['tid']
            event = e['event']

            # Force only per-thread-synchronous calls
            if tgid == t_pid and not asynchronous:
                for pids in list(tgid2source_tids.keys()):
                    if tid in tgid2source_tids[pids]:
                        tgid2source_tids[pids].remove(tid)
                        if len(tgid2source_tids[pids]) == 0:
                            pid_set.discard(pids)

            if tgid in pid_set:
                # If the process is associated with the examined process
                if tgid == t_pid:
                    sources = set([tid])
                else:
                    sources = tgid2source_tids[tgid]

                if event == 'binder_transaction':
                    binders[e['details']['transaction']] = sources
                elif event == 'unix_stream_sendmsg':
                    if e['details']['topid'] in unix_streams:
                        unix_streams[e['details']['topid']] = unix_streams[e['details']['topid']].union(sources)
                    else:
                        unix_streams[e['details']['topid']] = sources
                elif event == 'unix_dgram_sendmsg':
                    unix_dgrams_waiting.add(tid)
                elif event == 'sock_queue_tail' and tid in unix_dgrams_waiting:
                    if e['details']['inode'] in unix_dgrams:
                        unix_dgrams[e['details']['inode']] = unix_dgrams[e['details']['inode']].union(sources)
                    else:
                        unix_dgrams[e['details']['inode']] = sources
                    unix_dgrams_waiting.remove(tid)
                elif ((event == 'write_probe' and e['details'].get('pathname', 'null') != 'null') or \
                      (event == 'ioctl_probe') or (event == 'inet_sock_set_state') or \
                      (event == 'tcp_sendmsg') or (event == 'udp_sendmsg')):
                    # Add event as output event for this instance
                    out_flows_slice.append(e_index)

            # If a process receives a binder transaction originating from a tracked process
            if event == 'binder_transaction_received' and e['details']['transaction'] in binders:
                if tgid not in pid_set:
                    pid_set.add(tgid)
                if tgid in tgid2source_tids:
                    tgid2source_tids[tgid] = tgid2source_tids[tgid].union(binders[e['details']['transaction']])
                else:
                    tgid2source_tids[tgid] = binders[e['details']['transaction']]
                del binders[e['details']['transaction']]
            elif event == 'unix_stream_recvmsg' and e['details'].get('topid') in unix_streams:
                if tgid not in pid_set:
                    pid_set.add(tgid)
                if tgid in tgid2source_tids:
                    tgid2source_tids[tgid] = tgid2source_tids[tgid].union(unix_streams[e['details']['topid']])
                else:
                    tgid2source_tids[tgid] = unix_streams[e['details']['topid']]
                del unix_streams[e['details']['topid']]
            elif event == 'unix_dgram_recvmsg' and e['details']['inode'] in unix_dgrams:
                if tgid not in pid_set:
                    pid_set.add(tgid)
                if tgid in tgid2source_tids:
                    tgid2source_tids[tgid] = tgid2source_tids[tgid].union(unix_dgrams[e['details']['inode']])
                else:
                    tgid2source_tids[tgid] = unix_dgrams[e['details']['inode']]
                del unix_dgrams[e['details']['inode']]

            e_index += 1

        # Backward slicing for input operations
        pid_set = {t_pid}
        binders = dict()
        unix_streams = dict()
        unix_dgrams_waiting = set()
        unix_dgrams = dict()
        tgid2source_tids = dict()

        e_index = len(events) - 1
        for e in reversed(events):
            tgid = e['tgid']
            tid = e['tid']
            event = e['event']

            # Same as the forward path
            if tgid == t_pid and not asynchronous:
                for pids in list(tgid2source_tids.keys()):
                    if tid in tgid2source_tids[pids]:
                        tgid2source_tids[pids].remove(tid)
                        if len(tgid2source_tids[pids]) == 0:
                            pid_set.discard(pids)

            if tgid in pid_set:
                if tgid == t_pid:
                    sources = set([tid])
                else:
                    sources = tgid2source_tids[tgid]

                if event == 'binder_transaction_received':
                    binders[e['details']['transaction']] = sources
                elif event == 'unix_stream_recvmsg':
                    if e['details'].get('frompid') in unix_streams:
                        unix_streams[e['details']['frompid']] = unix_streams[e['details']['frompid']].union(sources)
                    else:
                        unix_streams[e['details']['frompid']] = sources
                elif event == 'unix_dgram_recvmsg':
                    if e['details']['inode'] in unix_dgrams:
                        unix_dgrams[e['details']['inode']] = unix_dgrams[e['details']['inode']].union(sources)
                    else:
                        unix_dgrams[e['details']['inode']] = sources
                elif (event == 'read_probe' or event == 'ioctl_probe' or (event == 'inet_sock_set_state') or \
                      (event == 'tcp_recvmsg') or (event == 'udp_recvmsg')):
                    # Add event as input event for this instance
                    in_flows_slice.append(e_index)

            # If a process sends a binder transaction to a tracked process
            if event == 'binder_transaction' and e['details']['transaction'] in binders:
                if tgid not in pid_set:
                    pid_set.add(tgid)
                if tgid in tgid2source_tids:
                    tgid2source_tids[tgid] = tgid2source_tids[tgid].union(binders[e['details']['transaction']])
                else:
                    tgid2source_tids[tgid] = binders[e['details']['transaction']]
                del binders[e['details']['transaction']]
            if event == 'unix_stream_sendmsg' and e['details'].get('topid') in unix_streams:
                if tgid not in pid_set:
                    pid_set.add(tgid)
                if tgid in tgid2source_tids:
                    tgid2source_tids[tgid] = tgid2source_tids[tgid].union(unix_streams[e['details']['topid']])
                else:
                    tgid2source_tids[tgid] = unix_streams[e['details']['topid']]
                del unix_streams[e['details']['topid']]
            elif event == 'sock_queue_tail' and e['details']['inode'] in unix_dgrams:
                if tgid not in pid_set:
                    pid_set.add(tgid)
                if tgid in tgid2source_tids:
                    tgid2source_tids[tgid] = tgid2source_tids[tgid].union(unix_dgrams[e['details']['inode']])
                else:
                    tgid2source_tids[tgid] = unix_dgrams[e['details']['inode']]

            e_index -= 1
        
        # Merge everything to one sequence
        merged = []
        i = 0
        j = 0

        len_in = len(in_flows_slice)
        len_out = len(out_flows_slice)

        while (i < len_in) and (j < len_out):
            if in_flows_slice[i] < out_flows_slice[j]:
                merged.append(in_flows_slice[i])
                i += 1
            else:
                merged.append(out_flows_slice[j])
                j += 1

        merged = merged + in_flows_slice[i:] + out_flows_slice[j:]

        # Eliminate duplicate ioctl entries
        merged_unique_index = []
        seen = set()
        for e_index in merged:
            if e_index not in seen:
                seen.add(e_index)
                merged_unique_index.append(e_index)

        merged_unique = []
        for e_index in merged_unique_index:
            merged_unique.append(events[e_index])

        filtered_events = []
        for e in merged_unique:
            # Filter out remnant api logging and binder transactions
            if ((e['event'] == 'write_probe' and e['details'].get('pathname', 'null') != 'null') or
                (e['event'] == 'ioctl_probe' and
                 e['details'].get('pathname', 'unknown') != 'binder' and
                 e['details'].get('pathname', 'unknown') != 'hwbinder') or
                (e['event'] != 'write_probe' and e['event'] != 'ioctl_probe' and 'binder' not in e['event'])):
                # Keep all event information, not just event and details
                filtered_events.append(e.copy())

        new_events = filtered_events
        return new_events
