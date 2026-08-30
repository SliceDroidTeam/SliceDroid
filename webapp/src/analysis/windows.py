"""
Windowed slicing driver.

Ports the canonical windowed analysis loop: slides an overlapping window
over the pruned event sequence, slices each window with the advanced
bidirectional algorithm, and accumulates per-window traces (device access
counts, network activity counts, sensitive-access occurrences).

Global network accumulation is NOT done here: overlapping windows (and the
final-window re-anchor) revisit the same events, so the pipeline
deduplicates ``all_relevant_events`` by 'raw' index and feeds a
:class:`~.network.NetworkAccumulator` exactly once.
"""

from __future__ import annotations

import logging
from typing import Any, Optional

from .devices import get_device_identifier, sensitive_category
from .network import filter_private_ip_events
from .slicer import categorize_event, is_filtered, slice_events

logger = logging.getLogger(__name__)

Event = dict[str, Any]


def run_windowed_analysis(
    events_pruned: list[Event],
    t_pid: int,
    window_size: int = 500,
    overlap: int = 100,
    asynchronous: bool = True,
    cat2devs: Optional[dict[str, list[str]]] = None,
) -> dict[str, Any]:
    """
    Run the windowed slicing analysis over a pruned event sequence.

    Args:
        events_pruned: Parsed events with API-logging markers removed
            (see :func:`slicer.remove_apis`).
        t_pid: Target process ID (tgid).
        window_size: Number of events per analysis window.
        overlap: Number of events shared between consecutive windows.
        asynchronous: Whether to allow asynchronous taint propagation.
        cat2devs: Optional {category: [device ids]} mapping used for
            per-window sensitive access detection.

    Returns:
        Dict with:
        - all_relevant_events: sliced events from every window (may contain
          duplicates across overlapping windows; each carries its 'raw' index)
        - kdevs_trace: per-window device access counts
        - network_trace: per-window tcp/udp sliced event counts
          [{'window', 'tcp', 'udp'}]
        - sensitive_hits: sensitive access occurrences
          [{'window', 'category', 'process', 'tgid', 'identifier',
            'pathname', 'timestamp'}] (deduplicated across window overlaps)
        - window_count: number of processed windows
        - events_duration: timestamp span of the relevant events
    """
    step = window_size - overlap
    if step <= 0:
        raise ValueError("Overlap must be less than the window size.")

    cat2devs = cat2devs or {}

    # Filter private-remote network events once, up front; windows are
    # sliced with prefiltered=True so this is the single filtering point.
    events_pruned = filter_private_ip_events(events_pruned)
    logger.info("After filtering private IP events: %d events", len(events_pruned))

    kdevs_trace: list[dict[str, int]] = []
    network_trace: list[dict[str, int]] = []
    sensitive_hits: list[dict[str, Any]] = []
    seen_sensitive: set[tuple] = set()
    all_relevant_events: list[Event] = []
    window_count = 0

    if window_size > len(events_pruned):
        window_size = len(events_pruned)

    # Slide the window over the event sequence
    i = 0
    while i < len(events_pruned):
        end = i + window_size
        begin = i
        if end > len(events_pruned):
            end = len(events_pruned)
            if len(events_pruned) - window_size >= 0:
                begin = len(events_pruned) - window_size
            else:
                begin = 0
        window = events_pruned[begin:end]

        try:
            relevant_events = slice_events(window, t_pid, asynchronous, prefiltered=True)

            # Collect relevant events (the 'raw' index tracks uniqueness)
            for event in relevant_events:
                if 'raw' in event:
                    all_relevant_events.append(event)
        except Exception:
            logger.exception("Error slicing window %d (%d-%d)", window_count, begin, end)
            if end == len(events_pruned):
                i = end
            else:
                i += step
            continue

        # Per-window tcp/udp sliced event counts for the timeline
        tcp_count = 0
        udp_count = 0
        for e in relevant_events:
            category = categorize_event(e)
            if category == 'network_tcp':
                tcp_count += 1
            elif category == 'network_udp':
                udp_count += 1
        network_trace.append({'window': window_count, 'tcp': tcp_count, 'udp': udp_count})

        # Per-window sensitive access detection (dedup across window overlaps)
        if cat2devs:
            for e in relevant_events:
                category = sensitive_category(e, cat2devs)
                if not category:
                    continue
                key = (e.get('raw'), category)
                if key in seen_sensitive:
                    continue
                seen_sensitive.add(key)
                sensitive_hits.append({
                    'window': window_count,
                    'category': category,
                    'process': e['process'],
                    'tgid': e['tgid'],
                    'identifier': str(get_device_identifier(e)),
                    'pathname': e['details'].get('pathname'),
                    'timestamp': e['timestamp'],
                })

        # Per-window device accounting
        kdev2count_window: dict[str, int] = dict()
        for e in relevant_events:
            if is_filtered(e):
                continue
            identifier = get_device_identifier(e)
            if identifier is None:
                continue
            kdev = str(identifier)
            kdev2count_window[kdev] = kdev2count_window.get(kdev, 0) + 1

        kdevs_trace.append(kdev2count_window)
        window_count += 1

        if end == len(events_pruned):
            i = end
        else:
            i += step

    if all_relevant_events:
        first_timestamp = min(event['timestamp'] for event in all_relevant_events)
        last_timestamp = max(event['timestamp'] for event in all_relevant_events)
        events_duration = last_timestamp - first_timestamp
    else:
        events_duration = 0.0

    logger.info("Processed %d windows, %d relevant events", window_count, len(all_relevant_events))

    return {
        'all_relevant_events': all_relevant_events,
        'kdevs_trace': kdevs_trace,
        'network_trace': network_trace,
        'sensitive_hits': sensitive_hits,
        'window_count': window_count,
        'events_duration': events_duration,
    }
