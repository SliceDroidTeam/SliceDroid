"""
Advanced bidirectional event slicing.

Ports the canonical replication-package slicing algorithm unchanged:

- forward pass collects output events (write_probe, ioctl_probe,
  inet_sock_set_state, tcp/udp_sendmsg and their *_ret events) of the
  target process and of processes tainted by it,
- backward pass collects input events (read_probe, ioctl_probe,
  inet_sock_set_state, tcp/udp_recvmsg and their *_ret events),
- taint propagates over binder transactions (transaction ids carrying
  source-tid sets), unix stream sockets (topid/frompid) and unix datagram
  sockets (sock_queue_tail inode binding),
- ``asynchronous=False`` restricts taint to per-thread synchronous calls
  via the tgid2source_tids bookkeeping,
- both passes are merged in raw index order, deduplicated, and binder
  plumbing events are filtered out.
"""

from __future__ import annotations

import logging
from typing import Any

from .network import filter_private_ip_events

logger = logging.getLogger(__name__)

Event = dict[str, Any]


def find_process(events: list[Event], target_app: str) -> int:
    """
    Find the tgid of the target application in a parsed event list.

    Android truncates process names (comm) to the last 15-16 characters of
    the package name, so both the full name and its truncated suffixes are
    tried.  Returns 0 if the process is not found.
    """
    candidates = []
    for name in (target_app, target_app[-16:], target_app[-15:]):
        name = name.lower()
        if name and name not in candidates:
            candidates.append(name)

    for e in events:
        process = e['process'].lower()
        for candidate in candidates:
            if candidate in process:
                return e['tgid']
    return 0


def remove_apis(events: list[Event]) -> list[Event]:
    """
    Remove API-logging marker events (write_probe pathname="null" with
    count > 999999) and all events from monkey processes.  Annotates every
    event with its raw index in the input list (in place) and returns
    references to the input events, not copies.
    """
    cleaned_events = []
    for i, e in enumerate(events):
        e['raw'] = i
        try:
            if (not (e['event'] == 'write_probe'
                     and e['details']['pathname'] == 'null'
                     and e['details']['count'] > 999999)
                    and 'monkey' not in e['process']):
                cleaned_events.append(e)
        except (KeyError, TypeError):
            logger.warning("Dropping malformed event during API pruning: %s", e)
    return cleaned_events


#: Bluetooth socket send probes
_BLUETOOTH_EVENTS = ('hci_sock_sendmsg', 'sco_sock_sendmsg', 'l2cap_sock_sendmsg')


def categorize_event(event: Event) -> str:
    """
    Categorize an event for summary/statistics purposes.

    Returns one of: binder, file_read, file_write, ioctl, network_tcp,
    network_udp, unix_socket, bluetooth, other.
    """
    name = event['event']
    if 'binder' in name:
        return 'binder'
    if name == 'read_probe':
        return 'file_read'
    if name == 'write_probe':
        return 'file_write'
    if name == 'ioctl_probe':
        return 'ioctl'
    if name in _BLUETOOTH_EVENTS:
        return 'bluetooth'
    if name.startswith('tcp_') or name == 'inet_sock_set_state':
        return 'network_tcp'
    if name.startswith('udp_'):
        return 'network_udp'
    if name.startswith('unix_') or name == 'sock_queue_tail':
        return 'unix_socket'
    return 'other'


def get_tcp_events(window: list[Event]) -> list[Event]:
    """
    Extract TCP socket state transition events from a window.

    Returns references to the window's events, not copies.
    """
    return [e for e in window if e['event'] == 'inet_sock_set_state']


def is_filtered(e: Event) -> bool:
    """
    Return True if an event should be ignored for device analysis.

    Probe events are kept (not filtered) when they carry a non-zero k_dev
    (device-level access) or a non-zero s_dev_inode plus inode (file-level
    access).
    """
    filtered = True

    if e['event'] in ('read_probe', 'write_probe', 'ioctl_probe'):
        details = e.get('details', {})

        has_k_dev = 'k_dev' in details
        has_s_dev_inode_and_inode = 's_dev_inode' in details and 'inode' in details

        if has_k_dev or has_s_dev_inode_and_inode:
            # If k_dev exists and is not 0, use it (device level)
            if has_k_dev and details['k_dev'] != 0:
                filtered = False
            # If k_dev is 0 or missing but we have s_dev_inode and inode,
            # use that (file level)
            elif has_s_dev_inode_and_inode and details['s_dev_inode'] != 0:
                filtered = False

    return filtered


def slice_events(events: list[Event], t_pid: int, asynchronous: bool = True,
                 prefiltered: bool = False) -> list[Event]:
    """
    Advanced bidirectional event slicing algorithm.

    Tracks process relationships through IPC mechanisms and completely
    ignores network events whose remote endpoint is a private IP address.

    Args:
        events: List of parsed events.
        t_pid: Target process ID (tgid).
        asynchronous: Whether to allow asynchronous taint propagation.
        prefiltered: Set to True when the caller has already run
            :func:`network.filter_private_ip_events` on the events (the
            windowed driver filters once up front) to skip the redundant
            per-call re-filtering.

    Returns:
        List of relevant events (references, not copies) attributed to the
        target process.
    """
    # Filter out private-remote network events (unless already done)
    if not prefiltered:
        events = filter_private_ip_events(events)

    if not events:
        return []

    # Relevant processes are tracked dynamically
    pid_set = {t_pid}
    binders: dict[Any, set[int]] = dict()
    unix_streams: dict[Any, set[int]] = dict()
    unix_dgrams_waiting: set[int] = set()
    unix_dgrams: dict[Any, set[int]] = dict()

    tgid2source_tids: dict[int, set[int]] = dict()

    out_flows_slice: list[int] = []
    in_flows_slice: list[int] = []

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
            elif ((event == 'write_probe' and e['details'].get('pathname', 'null') != 'null') or
                  (event == 'ioctl_probe') or (event == 'inet_sock_set_state') or
                  (event == 'tcp_sendmsg') or (event == 'udp_sendmsg') or
                  (event == 'tcp_sendmsg_ret') or (event == 'udp_sendmsg_ret')):
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
            elif (event == 'read_probe' or event == 'ioctl_probe' or (event == 'inet_sock_set_state') or
                  (event == 'tcp_recvmsg') or (event == 'udp_recvmsg') or
                  (event == 'tcp_recvmsg_ret') or (event == 'udp_recvmsg_ret')):
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

    # Merge everything to one sequence in ascending index order.  The
    # backward pass appended indices in descending order, so reverse them
    # first: the merge below assumes both inputs are ascending (otherwise
    # e.g. a tcp_recvmsg_ret would precede its tcp_recvmsg in the slice).
    in_flows_slice.reverse()

    merged: list[int] = []
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
    seen: set[int] = set()
    for e_index in merged:
        if e_index not in seen:
            seen.add(e_index)
            merged_unique_index.append(e_index)

    merged_unique = [events[e_index] for e_index in merged_unique_index]

    filtered_events = []
    for e in merged_unique:
        # Filter out remnant api logging and binder transactions
        if ((e['event'] == 'write_probe' and e['details'].get('pathname', 'null') != 'null') or
                (e['event'] == 'ioctl_probe' and
                 e['details'].get('pathname', 'unknown') != 'binder' and
                 e['details'].get('pathname', 'unknown') != 'hwbinder') or
                (e['event'] != 'write_probe' and e['event'] != 'ioctl_probe' and 'binder' not in e['event'])):
            # Keep all event information, not just event and details
            filtered_events.append(e)

    return filtered_events
