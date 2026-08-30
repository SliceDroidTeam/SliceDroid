#!/usr/bin/env python3
"""
Correlate tcp/udp sendmsg/recvmsg events from a SliceDroid ftrace trace with
TCP/UDP packets from the tcpdump capture taken during the same session.

For each network event in the trace file the corresponding *_ret kretprobe
event is located first (giving the actual number of bytes transferred), then a
matching packet is searched for in the pcap: an exact single-packet match on
ports + size, with a TCP-segmentation fallback for large payloads.

Usage:
    python3 scripts/correlation/trace_pcap_correlator.py \
        --trace data/traces/trace.trace \
        --pcap data/traces/tcpdump.pcap \
        --output data/traces/correlations.csv

Both --trace and --pcap transparently accept gzipped files (.gz suffix, or the
plain path when only the .gz variant exists on disk).

scapy is an optional dependency, required only by this script:
    pip install scapy
"""

import argparse
import csv
import gzip
import logging
import os
import re
import sys
import tempfile
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

try:
    from scapy.all import rdpcap, TCP, IP, UDP
    SCAPY_AVAILABLE = True
    SCAPY_IMPORT_ERROR = None
except ImportError as exc:  # pragma: no cover - depends on environment
    SCAPY_AVAILABLE = False
    SCAPY_IMPORT_ERROR = exc

logger = logging.getLogger("trace_pcap_correlator")

DEFAULT_TRACE = os.path.join("data", "traces", "trace.trace")
DEFAULT_PCAP = os.path.join("data", "traces", "tcpdump.pcap")
DEFAULT_OUTPUT = os.path.join("data", "traces", "correlations.csv")


def convert_dst_port_endianness(port: int) -> int:
    """Convert destination port from little endian (ftrace) to big endian (network order)
    Only destination ports need conversion, source ports are already in correct format"""
    return ((port & 0xFF) << 8) | ((port >> 8) & 0xFF)


@dataclass
class NetworkEvent:
    """Represents a tcp/udp sendmsg or recvmsg event from the trace file"""
    timestamp: str
    process_name: str
    pid: int
    src_ip: int
    dst_ip: int
    src_port: int  # Source port - no conversion needed for sendmsg, converted for recvmsg
    dst_port: int  # Destination port - converted from little endian
    raw_src_port: int  # Raw source port from trace (for recvmsg)
    raw_dst_port: int  # Raw destination port from trace
    size: int
    event_type: str  # 'send' or 'recv'
    protocol: str  # 'tcp' or 'udp'
    ret_value: Optional[int] = None
    ret_timestamp: Optional[str] = None


@dataclass
class PcapMatch:
    """Represents a matching TCP/UDP packet from the pcap file"""
    timestamp: float
    src_ip: str
    dst_ip: str
    src_port: int
    dst_port: int
    size: int


def ip_int_to_str(ip_int: int) -> str:
    """Convert integer IP address to dotted decimal notation"""
    return f"{ip_int & 0xFF}.{(ip_int >> 8) & 0xFF}.{(ip_int >> 16) & 0xFF}.{(ip_int >> 24) & 0xFF}"


def resolve_input_path(path: str) -> str:
    """Return `path` if it exists; otherwise fall back to `path`.gz when present."""
    if os.path.exists(path):
        return path
    gz_path = path if path.endswith(".gz") else path + ".gz"
    if os.path.exists(gz_path):
        return gz_path
    raise FileNotFoundError(f"Input file not found: {path} (also tried {gz_path})")


def open_trace(path: str):
    """Open a trace file for text reading, transparently handling gzip."""
    if path.endswith(".gz"):
        return gzip.open(path, "rt", encoding="utf-8", errors="replace")
    return open(path, "r", encoding="utf-8", errors="replace")


def extract_gz_file(gz_path: str, temp_dir: str) -> str:
    """Extract a .gz file to a temporary directory and return the extracted path."""
    with gzip.open(gz_path, "rb") as gz_file:
        filename = os.path.basename(gz_path)[: -len(".gz")]
        temp_path = os.path.join(temp_dir, filename)
        with open(temp_path, "wb") as temp_file:
            temp_file.write(gz_file.read())
    return temp_path


def parse_trace_events(trace_file_path: str) -> Tuple[List[NetworkEvent], Dict[str, int]]:
    """Parse tcp/udp sendmsg and recvmsg events from trace file"""
    events = []
    pending_events = {}  # Key: (process_name, pid, event_type, protocol) -> NetworkEvent

    # Statistics tracking
    stats = {
        'tcp_send': 0, 'tcp_recv': 0, 'udp_send': 0, 'udp_recv': 0,
        'tcp_send_complete': 0, 'tcp_recv_complete': 0,
        'udp_send_complete': 0, 'udp_recv_complete': 0
    }

    # Regex patterns for parsing trace events
    tcp_sendmsg_pattern = re.compile(
        r'^\s*(\S+)\s+\(\s*(\d+)\)\s+\[.*?\]\s+.*?\s+(\d+\.\d+):\s+tcp_sendmsg:.*?'
        r'src_ip=(\d+)\s+dst_ip=(\d+)\s+src_port=(\d+)\s+dst_port=(\d+)\s+size=0x([0-9a-fA-F]+)'
    )

    tcp_sendmsg_ret_pattern = re.compile(
        r'^\s*(\S+)\s+\(\s*(\d+)\)\s+\[.*?\]\s+.*?\s+(\d+\.\d+):\s+tcp_sendmsg_ret:.*?ret=(-?\d+)'
    )

    tcp_recvmsg_pattern = re.compile(
        r'^\s*(\S+)\s+\(\s*(\d+)\)\s+\[.*?\]\s+.*?\s+(\d+\.\d+):\s+tcp_recvmsg:.*?'
        r'src_ip=(\d+)\s+dst_ip=(\d+)\s+src_port=(\d+)\s+dst_port=(\d+)\s+len=0x([0-9a-fA-F]+)'
    )

    tcp_recvmsg_ret_pattern = re.compile(
        r'^\s*(\S+)\s+\(\s*(\d+)\)\s+\[.*?\]\s+.*?\s+(\d+\.\d+):\s+tcp_recvmsg_ret:.*?ret=(-?\d+)'
    )

    # UDP patterns - different format with socket_addr and unbound_addr
    udp_sendmsg_pattern = re.compile(
        r'^\s*(\S+)\s+\(\s*(\d+)\)\s+\[.*?\]\s+.*?\s+(\d+\.\d+):\s+udp_sendmsg:.*?'
        r'socket_addr=\{([^}]+)\}\s+unbound_addr=\{([^}]+)\}\s+src_port=(\d+)\s+dst_port=(\d+)\s+len=(\d+)'
    )

    udp_sendmsg_ret_pattern = re.compile(
        r'^\s*(\S+)\s+\(\s*(\d+)\)\s+\[.*?\]\s+.*?\s+(\d+\.\d+):\s+udp_sendmsg_ret:.*?ret=(-?\d+)'
    )

    udp_recvmsg_pattern = re.compile(
        r'^\s*(\S+)\s+\(\s*(\d+)\)\s+\[.*?\]\s+.*?\s+(\d+\.\d+):\s+udp_recvmsg:.*?'
        r'src_ip=(\d+)\s+dst_ip=(\d+)\s+src_port=(\d+)\s+dst_port=(\d+)\s+len=0x([0-9a-fA-F]+)'
    )

    udp_recvmsg_ret_pattern = re.compile(
        r'^\s*(\S+)\s+\(\s*(\d+)\)\s+\[.*?\]\s+.*?\s+(\d+\.\d+):\s+udp_recvmsg_ret:.*?ret=(-?\d+)'
    )

    with open_trace(trace_file_path) as f:
        for line_num, line in enumerate(f, 1):

            # Check for tcp_sendmsg event
            match = tcp_sendmsg_pattern.match(line)
            if match:
                process_name = match.group(1)
                pid = int(match.group(2))
                timestamp = match.group(3)
                src_ip = int(match.group(4))
                dst_ip = int(match.group(5))
                src_port = int(match.group(6))
                dst_port_raw = int(match.group(7))
                size = int(match.group(8), 16)  # Convert hex to int

                # Only convert destination port from little endian to network byte order
                # Source ports are already in correct format for sendmsg
                dst_port = convert_dst_port_endianness(dst_port_raw)

                stats['tcp_send'] += 1

                event = NetworkEvent(
                    timestamp=timestamp,
                    process_name=process_name,
                    pid=pid,
                    src_ip=src_ip,
                    dst_ip=dst_ip,
                    src_port=src_port,  # No conversion for source port
                    dst_port=dst_port,
                    raw_src_port=src_port,  # Same as converted for sendmsg
                    raw_dst_port=dst_port_raw,
                    size=size,
                    event_type='send',
                    protocol='tcp'
                )

                # Store event waiting for its return value
                key = (process_name, pid, 'send', 'tcp')
                pending_events[key] = event
                continue

            # Check for tcp_recvmsg event
            match = tcp_recvmsg_pattern.match(line)
            if match:
                process_name = match.group(1)
                pid = int(match.group(2))
                timestamp = match.group(3)
                src_ip = int(match.group(4))
                dst_ip = int(match.group(5))
                src_port_raw = int(match.group(6))
                dst_port_raw = int(match.group(7))
                size = int(match.group(8), 16)  # Convert hex to int

                # For recvmsg: src_port is local (no conversion), dst_port is remote (needs conversion)
                src_port = src_port_raw  # local port (no conversion needed)
                dst_port = convert_dst_port_endianness(dst_port_raw)  # remote port (converted)

                stats['tcp_recv'] += 1

                event = NetworkEvent(
                    timestamp=timestamp,
                    process_name=process_name,
                    pid=pid,
                    src_ip=src_ip,
                    dst_ip=dst_ip,
                    src_port=src_port,
                    dst_port=dst_port,
                    raw_src_port=src_port_raw,
                    raw_dst_port=dst_port_raw,
                    size=size,
                    event_type='recv',
                    protocol='tcp'
                )

                # Store event waiting for its return value
                key = (process_name, pid, 'recv', 'tcp')
                pending_events[key] = event
                continue

            # Check for tcp_sendmsg_ret event
            match = tcp_sendmsg_ret_pattern.match(line)
            if match:
                process_name = match.group(1)
                pid = int(match.group(2))
                ret_timestamp = match.group(3)
                ret_value = int(match.group(4))

                key = (process_name, pid, 'send', 'tcp')
                if key in pending_events:
                    event = pending_events.pop(key)
                    event.ret_value = ret_value
                    event.ret_timestamp = ret_timestamp
                    events.append(event)
                    stats['tcp_send_complete'] += 1
                continue

            # Check for tcp_recvmsg_ret event
            match = tcp_recvmsg_ret_pattern.match(line)
            if match:
                process_name = match.group(1)
                pid = int(match.group(2))
                ret_timestamp = match.group(3)
                ret_value = int(match.group(4))

                key = (process_name, pid, 'recv', 'tcp')
                if key in pending_events:
                    event = pending_events.pop(key)
                    event.ret_value = ret_value
                    event.ret_timestamp = ret_timestamp
                    events.append(event)
                    stats['tcp_recv_complete'] += 1
                continue

            # Check for udp_sendmsg event
            match = udp_sendmsg_pattern.match(line)
            if match:
                process_name = match.group(1)
                pid = int(match.group(2))
                timestamp = match.group(3)
                socket_addr = match.group(4)  # e.g., "0,0,0,0"
                unbound_addr = match.group(5)  # e.g., "224,0,0,251"
                src_port = int(match.group(6))
                dst_port_raw = int(match.group(7))
                size = int(match.group(8))

                # Parse IP addresses from socket_addr and unbound_addr
                # socket_addr seems to be src_ip, unbound_addr seems to be dst_ip
                src_ip_parts = [int(x) for x in socket_addr.split(',')]
                dst_ip_parts = [int(x) for x in unbound_addr.split(',')]

                # Convert to integer IP representation
                src_ip = (src_ip_parts[3] << 24) | (src_ip_parts[2] << 16) | (src_ip_parts[1] << 8) | src_ip_parts[0]
                dst_ip = (dst_ip_parts[3] << 24) | (dst_ip_parts[2] << 16) | (dst_ip_parts[1] << 8) | dst_ip_parts[0]

                # For UDP, only convert destination port if needed (same logic as TCP)
                dst_port = convert_dst_port_endianness(dst_port_raw) if dst_port_raw > 0 else dst_port_raw

                stats['udp_send'] += 1

                event = NetworkEvent(
                    timestamp=timestamp,
                    process_name=process_name,
                    pid=pid,
                    src_ip=src_ip,
                    dst_ip=dst_ip,
                    src_port=src_port,
                    dst_port=dst_port,
                    raw_src_port=src_port,
                    raw_dst_port=dst_port_raw,
                    size=size,
                    event_type='send',
                    protocol='udp'
                )

                # Store event waiting for its return value
                key = (process_name, pid, 'send', 'udp')
                pending_events[key] = event
                continue

            # Check for udp_recvmsg event
            match = udp_recvmsg_pattern.match(line)
            if match:
                process_name = match.group(1)
                pid = int(match.group(2))
                timestamp = match.group(3)
                src_ip = int(match.group(4))
                dst_ip = int(match.group(5))
                src_port_raw = int(match.group(6))
                dst_port_raw = int(match.group(7))
                size = int(match.group(8), 16)  # Convert hex to int

                # For UDP recvmsg: similar logic to TCP
                src_port = src_port_raw  # local port (no conversion needed)
                dst_port = convert_dst_port_endianness(dst_port_raw) if dst_port_raw > 0 else dst_port_raw

                stats['udp_recv'] += 1

                event = NetworkEvent(
                    timestamp=timestamp,
                    process_name=process_name,
                    pid=pid,
                    src_ip=src_ip,
                    dst_ip=dst_ip,
                    src_port=src_port,
                    dst_port=dst_port,
                    raw_src_port=src_port_raw,
                    raw_dst_port=dst_port_raw,
                    size=size,
                    event_type='recv',
                    protocol='udp'
                )

                # Store event waiting for its return value
                key = (process_name, pid, 'recv', 'udp')
                pending_events[key] = event
                continue

            # Check for udp_sendmsg_ret event
            match = udp_sendmsg_ret_pattern.match(line)
            if match:
                process_name = match.group(1)
                pid = int(match.group(2))
                ret_timestamp = match.group(3)
                ret_value = int(match.group(4))

                key = (process_name, pid, 'send', 'udp')
                if key in pending_events:
                    event = pending_events.pop(key)
                    event.ret_value = ret_value
                    event.ret_timestamp = ret_timestamp
                    events.append(event)
                    stats['udp_send_complete'] += 1
                continue

            # Check for udp_recvmsg_ret event
            match = udp_recvmsg_ret_pattern.match(line)
            if match:
                process_name = match.group(1)
                pid = int(match.group(2))
                ret_timestamp = match.group(3)
                ret_value = int(match.group(4))

                key = (process_name, pid, 'recv', 'udp')
                if key in pending_events:
                    event = pending_events.pop(key)
                    event.ret_value = ret_value
                    event.ret_timestamp = ret_timestamp
                    events.append(event)
                    stats['udp_recv_complete'] += 1
                continue

    return events, stats


def find_tcp_segments(pcap_packets: List[PcapMatch], target_src_port: int, target_dst_port: int,
                      target_size: int, tolerance_window: float = 1.0) -> List[PcapMatch]:
    """
    Find TCP segments that together might make up a large payload.
    Returns list of packets with matching ports that could be segments.
    """
    # Find all packets with matching ports
    matching_packets = [p for p in pcap_packets
                        if p.src_port == target_src_port and p.dst_port == target_dst_port]

    if not matching_packets:
        return []

    # Sort by timestamp
    matching_packets.sort(key=lambda x: x.timestamp)

    # Try to find combinations that sum to target_size
    segments = []
    total_size = 0
    start_time = None

    for packet in matching_packets:
        if start_time is None:
            start_time = packet.timestamp
            segments = [packet]
            total_size = packet.size
        elif packet.timestamp - start_time <= tolerance_window:
            # Within time window, add to current combination
            segments.append(packet)
            total_size += packet.size

            if total_size == target_size:
                return segments
            elif total_size > target_size:
                # Overshot, start new combination from this packet
                start_time = packet.timestamp
                segments = [packet]
                total_size = packet.size
        else:
            # Outside time window, start new combination
            start_time = packet.timestamp
            segments = [packet]
            total_size = packet.size

    # If we have segments that are close to target size, return them
    if segments and abs(total_size - target_size) <= max(100, target_size * 0.1):
        return segments

    return []


def analyze_pcap_file(pcap_file_path: str) -> List[PcapMatch]:
    """Analyze pcap file and extract TCP and UDP packet information"""
    try:
        packets = rdpcap(pcap_file_path)
    except Exception as e:
        logger.error("Error reading pcap file: %s", e)
        return []

    network_packets = []
    tcp_count = 0
    udp_count = 0

    for i, packet in enumerate(packets):

        # Check if packet has IP layer
        if packet.haslayer(IP):
            ip_layer = packet[IP]

            # Handle TCP packets
            if packet.haslayer(TCP):
                tcp_layer = packet[TCP]
                payload_size = len(tcp_layer.payload) if tcp_layer.payload else 0

                # Only consider packets with payload (data packets)
                if payload_size > 0:
                    pcap_match = PcapMatch(
                        timestamp=float(packet.time),
                        src_ip=ip_layer.src,
                        dst_ip=ip_layer.dst,
                        src_port=tcp_layer.sport,
                        dst_port=tcp_layer.dport,
                        size=payload_size
                    )
                    network_packets.append(pcap_match)
                    tcp_count += 1

            # Handle UDP packets
            elif packet.haslayer(UDP):
                udp_layer = packet[UDP]
                payload_size = len(udp_layer.payload) if udp_layer.payload else 0

                # Only consider packets with payload (data packets)
                if payload_size > 0:
                    pcap_match = PcapMatch(
                        timestamp=float(packet.time),
                        src_ip=ip_layer.src,
                        dst_ip=ip_layer.dst,
                        src_port=udp_layer.sport,
                        dst_port=udp_layer.dport,
                        size=payload_size
                    )
                    network_packets.append(pcap_match)
                    udp_count += 1

    logger.info("Extracted %d TCP and %d UDP data packets from pcap", tcp_count, udp_count)
    return network_packets


def correlate_events(trace_events: List[NetworkEvent], pcap_packets: List[PcapMatch]) -> Tuple[List[Dict], Dict[str, int]]:
    """Correlate trace events with pcap packets"""
    correlations = []
    match_stats = {
        'tcp_send_exact': 0, 'tcp_send_segmented': 0, 'tcp_send_unmatched': 0,
        'tcp_recv_exact': 0, 'tcp_recv_segmented': 0, 'tcp_recv_unmatched': 0,
        'udp_send_exact': 0, 'udp_send_unmatched': 0,
        'udp_recv_exact': 0, 'udp_recv_unmatched': 0,
        'skipped_negative_ret': 0
    }

    for event in trace_events:
        if event.ret_value is None:
            continue

        # Skip events with negative return values (errors, no actual data)
        if event.ret_value < 0:
            match_stats['skipped_negative_ret'] += 1
            continue

        # Convert trace IP addresses to string format for comparison
        trace_src_ip = ip_int_to_str(event.src_ip)
        trace_dst_ip = ip_int_to_str(event.dst_ip)

        # First try: Look for exact single packet match
        found_match = False
        for packet in pcap_packets:
            # Port matching logic depends on protocol and event type
            if event.protocol == 'tcp':
                # For TCP: match both ports
                if event.event_type == 'send':
                    ports_match = (packet.src_port == event.src_port and packet.dst_port == event.dst_port)
                else:  # recv
                    ports_match = (packet.src_port == event.dst_port and packet.dst_port == event.src_port)
            else:  # UDP
                # For UDP: only match source port as requested
                if event.event_type == 'send':
                    ports_match = (packet.src_port == event.src_port)
                else:  # recv
                    ports_match = (packet.dst_port == event.src_port)  # received data goes to our source port

            if ports_match and packet.size == event.ret_value:
                match_stats[f"{event.protocol}_{event.event_type}_exact"] += 1

                correlation = {
                    'trace_timestamp': event.timestamp,
                    'trace_process': event.process_name,
                    'trace_pid': event.pid,
                    'trace_src_ip': trace_src_ip,
                    'trace_dst_ip': trace_dst_ip,
                    'trace_src_port': event.src_port,
                    'trace_dst_port': event.dst_port,
                    'trace_raw_src_port': event.raw_src_port,
                    'trace_raw_dst_port': event.raw_dst_port,
                    'trace_size': event.size,
                    'trace_ret_value': event.ret_value,
                    'trace_ret_timestamp': event.ret_timestamp,
                    'trace_event_type': event.event_type,
                    'pcap_timestamp': packet.timestamp,
                    'pcap_src_ip': packet.src_ip,
                    'pcap_dst_ip': packet.dst_ip,
                    'pcap_src_port': packet.src_port,
                    'pcap_dst_port': packet.dst_port,
                    'pcap_size': packet.size,
                    'match_type': 'exact'
                }
                correlations.append(correlation)
                found_match = True
                break  # Found a match, move to next trace event

        # FALLBACK: Look for TCP segmentation only if no exact match was found (only for TCP)
        if not found_match and event.protocol == 'tcp':
            # For recv events, swap the ports when looking for segments
            if event.event_type == 'send':
                segments = find_tcp_segments(pcap_packets, event.src_port, event.dst_port, event.ret_value)
            else:  # recv
                segments = find_tcp_segments(pcap_packets, event.dst_port, event.src_port, event.ret_value)

            if segments:
                total_segments_size = sum(s.size for s in segments)
                match_stats[f"{event.protocol}_{event.event_type}_segmented"] += 1

                # Create correlation entry with first segment timestamp, but note it's segmented
                correlation = {
                    'trace_timestamp': event.timestamp,
                    'trace_process': event.process_name,
                    'trace_pid': event.pid,
                    'trace_src_ip': trace_src_ip,
                    'trace_dst_ip': trace_dst_ip,
                    'trace_src_port': event.src_port,
                    'trace_dst_port': event.dst_port,
                    'trace_raw_src_port': event.raw_src_port,
                    'trace_raw_dst_port': event.raw_dst_port,
                    'trace_size': event.size,
                    'trace_ret_value': event.ret_value,
                    'trace_ret_timestamp': event.ret_timestamp,
                    'trace_event_type': event.event_type,
                    'trace_protocol': event.protocol,
                    'pcap_timestamp': segments[0].timestamp,
                    'pcap_src_ip': segments[0].src_ip,
                    'pcap_dst_ip': segments[0].dst_ip,
                    'pcap_src_port': segments[0].src_port,
                    'pcap_dst_port': segments[0].dst_port,
                    'pcap_size': total_segments_size,
                    'match_type': 'segmented',
                    'segment_count': len(segments),
                    'segment_sizes': ','.join(str(s.size) for s in segments)
                }
                correlations.append(correlation)
                found_match = True

        if not found_match:
            match_stats[f"{event.protocol}_{event.event_type}_unmatched"] += 1

    return correlations, match_stats


def write_csv_results(correlations: List[Dict], output_file: str):
    """Write correlation results to CSV file"""
    if not correlations:
        logger.warning("No correlations found to write to CSV")
        return

    fieldnames = [
        'trace_timestamp', 'trace_process', 'trace_pid',
        'trace_src_ip', 'trace_dst_ip', 'trace_src_port', 'trace_dst_port',
        'trace_raw_src_port', 'trace_raw_dst_port',
        'trace_size', 'trace_ret_value', 'trace_ret_timestamp', 'trace_event_type', 'trace_protocol',
        'pcap_timestamp', 'pcap_src_ip', 'pcap_dst_ip',
        'pcap_src_port', 'pcap_dst_port', 'pcap_size',
        'match_type', 'segment_count', 'segment_sizes'
    ]

    with open(output_file, 'w', newline='', encoding='utf-8') as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        for correlation in correlations:
            writer.writerow(correlation)


def run(trace_path: str, pcap_path: str, output_path: str) -> int:
    """Correlate a single trace/pcap pair and write the correlations CSV."""
    trace_path = resolve_input_path(trace_path)
    pcap_path = resolve_input_path(pcap_path)

    logger.info("Trace file: %s", trace_path)
    logger.info("Pcap file: %s", pcap_path)

    # Parse trace events
    trace_events, trace_stats = parse_trace_events(trace_path)
    if not trace_events:
        logger.error("No network events found in trace file")
        return 1

    # Analyze pcap file (extract gzipped captures to a temp dir first)
    with tempfile.TemporaryDirectory() as temp_dir:
        if pcap_path.endswith(".gz"):
            pcap_file = extract_gz_file(pcap_path, temp_dir)
        else:
            pcap_file = pcap_path
        pcap_packets = analyze_pcap_file(pcap_file)

    if not pcap_packets:
        logger.error("No network packets found in pcap file")
        return 1

    # Correlate events
    correlations, match_stats = correlate_events(trace_events, pcap_packets)

    # Calculate and print summary statistics
    tcp_total = trace_stats['tcp_send_complete'] + trace_stats['tcp_recv_complete']
    tcp_matched = match_stats['tcp_send_exact'] + match_stats['tcp_send_segmented'] + match_stats['tcp_recv_exact'] + match_stats['tcp_recv_segmented']
    tcp_percentage = (tcp_matched / tcp_total * 100) if tcp_total > 0 else 0

    # For UDP, only count events that were actually attempted for correlation (excluding negative return values)
    udp_attempted = (match_stats['udp_send_exact'] + match_stats['udp_send_unmatched'] +
                     match_stats['udp_recv_exact'] + match_stats['udp_recv_unmatched'])
    udp_matched = match_stats['udp_send_exact'] + match_stats['udp_recv_exact']
    udp_percentage = (udp_matched / udp_attempted * 100) if udp_attempted > 0 else 0

    print(f"Total Trace TCP Events: {tcp_total}")
    print(f"Total TCP Events Matched: {tcp_matched}")
    print(f"TCP Matching Percentage: {tcp_percentage:.1f}%")
    print(f"Total Trace UDP Events: {udp_attempted}")
    print(f"Total UDP Events Matched: {udp_matched}")
    print(f"UDP Matching Percentage: {udp_percentage:.1f}%")

    # Write results
    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
    write_csv_results(correlations, output_path)
    logger.info("Correlations written to %s", output_path)
    return 0


def main():
    parser = argparse.ArgumentParser(
        description="Correlate SliceDroid trace network events with a tcpdump capture."
    )
    parser.add_argument("--trace", default=DEFAULT_TRACE,
                        help=f"Path to the trace file, plain or gzipped (default: {DEFAULT_TRACE})")
    parser.add_argument("--pcap", default=DEFAULT_PCAP,
                        help=f"Path to the pcap file, plain or gzipped (default: {DEFAULT_PCAP})")
    parser.add_argument("--output", "-o", default=DEFAULT_OUTPUT,
                        help=f"Output correlations CSV path (default: {DEFAULT_OUTPUT})")
    parser.add_argument("-v", "--verbose", action="store_true",
                        help="Enable debug logging")
    args = parser.parse_args()

    logging.basicConfig(level=logging.DEBUG if args.verbose else logging.INFO,
                        format="%(levelname)s %(name)s: %(message)s")

    if not SCAPY_AVAILABLE:
        parser.exit(1, "Error: scapy is required for pcap correlation but is not installed.\n"
                       "Install it with: pip install scapy\n"
                       f"(import error: {SCAPY_IMPORT_ERROR})\n")

    try:
        sys.exit(run(args.trace, args.pcap, args.output))
    except FileNotFoundError as e:
        parser.exit(1, f"Error: {e}\n")


if __name__ == "__main__":
    main()
