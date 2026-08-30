"""
Plain-text insight generation.

Produces between 3 and 6 short, factual insights about an analysis run,
each shaped as {"level": "info"|"warning", "text": str} per the analysis
JSON contract.  No HTML, no speculation: every statement is derived
directly from the computed results.  Sensitive-data access and large
outbound transfers are reported as warnings.
"""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)

MIN_INSIGHTS = 3
MAX_INSIGHTS = 6

#: Outbound byte count above which a transfer is flagged as a warning
LARGE_EXFIL_BYTES = 1_000_000


def _info(text: str) -> dict[str, str]:
    return {'level': 'info', 'text': text}


def _warning(text: str) -> dict[str, str]:
    return {'level': 'warning', 'text': text}


def generate_insights(meta: dict[str, Any], devices: dict[str, Any], network: dict[str, Any]) -> list[dict[str, str]]:
    """
    Generate 3-6 factual insights from the analysis results.

    Args:
        meta: The 'meta' section of the analysis contract.
        devices: The internal device summary (device_counts, categories,
            sensitive) built by :func:`devices.build_device_summary`.
        network: The 'network' section of the contract ({'metrics', ...}).

    Returns:
        List of {"level": "info"|"warning", "text": str} dicts.
    """
    insights: list[dict[str, str]] = []
    metrics = network.get('metrics', {})
    target = meta.get('target', {})

    insights.append(_info(
        "Attributed {slice} of {total} trace events to '{name}' "
        "(PID {pids}) across {windows} analysis window(s).".format(
            slice=meta.get('sliced_events', 0),
            total=meta.get('total_events', 0),
            name=target.get('package') or target.get('name') or 'target process',
            pids=', '.join(str(p) for p in target.get('pids', [])) or 'unknown',
            windows=meta.get('windows', 0),
        )
    ))

    # Sensitive data access (warnings)
    sensitive = devices.get('sensitive', {})
    detected = [
        (category, info) for category, info in sensitive.items() if info.get('detected')
    ]
    if detected:
        for category, info in detected[:2]:  # at most two sensitive insights
            insights.append(_warning(
                "Access to {category} data detected: {count} event(s) touching {path}.".format(
                    category=category.replace('_', ' '),
                    count=info.get('event_count', 0),
                    path=', '.join(info.get('pathnames', [])[:2]) or 'unknown path',
                )
            ))
    else:
        insights.append(_info(
            "No access to sensitive data (contacts, SMS, calendar, call logs) "
            "was detected in the slice."
        ))

    # Network activity (public peers only)
    tcp_active = (metrics.get('tcp_bytes_sent', 0) or metrics.get('tcp_bytes_received', 0)
                  or metrics.get('unique_tcp_peers', 0))
    udp_active = (metrics.get('udp_bytes_sent', 0) or metrics.get('udp_bytes_received', 0)
                  or metrics.get('unique_udp_peers', 0))
    bytes_out = metrics.get('tcp_bytes_sent', 0) + metrics.get('udp_bytes_sent', 0)

    if bytes_out > LARGE_EXFIL_BYTES:
        insights.append(_warning(
            "Large outbound transfer: {sent} byte(s) sent to public peers "
            "({tcp} unique TCP, {udp} unique UDP peer(s)).".format(
                sent=bytes_out,
                tcp=metrics.get('unique_tcp_peers', 0),
                udp=metrics.get('unique_udp_peers', 0),
            )
        ))
    if tcp_active:
        insights.append(_info(
            "TCP traffic to public peers: {sent} byte(s) sent and {recv} byte(s) received "
            "across {conns} connection(s) to {peers} unique peer(s).".format(
                sent=metrics.get('tcp_bytes_sent', 0),
                recv=metrics.get('tcp_bytes_received', 0),
                conns=metrics.get('tcp_connections', 0),
                peers=metrics.get('unique_tcp_peers', 0),
            )
        ))
    if udp_active:
        insights.append(_info(
            "UDP traffic to public peers: {sent} byte(s) sent and {recv} byte(s) received "
            "to {peers} unique peer(s).".format(
                sent=metrics.get('udp_bytes_sent', 0),
                recv=metrics.get('udp_bytes_received', 0),
                peers=metrics.get('unique_udp_peers', 0),
            )
        ))
    if not tcp_active and not udp_active:
        insights.append(_info(
            "No network traffic to public IP addresses was observed in the slice; "
            "traffic to private addresses is excluded from analysis."
        ))

    # Device/file footprint
    device_counts = devices.get('device_counts', {})
    categories = devices.get('categories', {})
    if device_counts:
        insights.append(_info(
            "The slice accessed {devices} distinct device/file identifier(s), "
            "{categorized} of which map to known resource categories ({names}).".format(
                devices=len(device_counts),
                categorized=sum(categories.values()),
                names=', '.join(sorted(categories)) or 'none',
            )
        ))

    return insights[:MAX_INSIGHTS]
