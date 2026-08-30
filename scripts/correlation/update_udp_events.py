#!/usr/bin/env python3
"""
Rewrite UDP events in a SliceDroid trace using the correlations CSV produced by
trace_pcap_correlator.py.

For every udp_sendmsg/udp_recvmsg line whose timestamp has an exact match in
the correlations CSV, the socket addresses and ports are replaced with the
real values observed in the tcpdump capture. UDP lines with no correlation are
removed, together with their *_ret lines; *_ret lines with negative return
values (errors) are removed as well. All non-UDP lines are kept untouched.

Usage:
    python3 scripts/correlation/update_udp_events.py \
        --trace data/traces/trace.trace \
        --correlations data/traces/correlations.csv \
        --output data/traces/trace_corrected.trace

--trace transparently accepts a gzipped file (.gz suffix, or the plain path
when only the .gz variant exists on disk). The output is written uncompressed.
"""

import argparse
import csv
import gzip
import logging
import os
import re
import sys
from typing import Dict, Optional

logger = logging.getLogger("update_udp_events")

DEFAULT_TRACE = os.path.join("data", "traces", "trace.trace")
DEFAULT_CORRELATIONS = os.path.join("data", "traces", "correlations.csv")
DEFAULT_OUTPUT = os.path.join("data", "traces", "trace_corrected.trace")


# Shared gz-aware IO helpers live in the correlator module (same package);
# importing it is safe — its scapy dependency is only loaded when correlation
# actually runs.
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from trace_pcap_correlator import open_trace, resolve_input_path  # noqa: E402


def read_correlation_csv(csv_path: str) -> Dict[float, Dict]:
    """
    Read correlation CSV file and create a timestamp-indexed dictionary.
    """
    correlations = {}

    try:
        with open(csv_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                timestamp = float(row['trace_timestamp'])
                correlations[timestamp] = {
                    'pcap_src_ip': row['pcap_src_ip'],
                    'pcap_dst_ip': row['pcap_dst_ip'],
                    'pcap_src_port': row['pcap_src_port'],
                    'pcap_dst_port': row['pcap_dst_port'],
                    'trace_event_type': row['trace_event_type']
                }
    except Exception as e:
        logger.error("Error reading CSV %s: %s", csv_path, e)
        return {}

    return correlations


def find_exact_timestamp(target_timestamp: float, correlations: Dict[float, Dict]) -> Optional[Dict]:
    """
    Find the correlation entry with the exact timestamp match.
    """
    return correlations.get(target_timestamp, None)


def ip_to_trace_int(ip: str) -> str:
    """
    Encode a dotted-quad IP as the little-endian u32 integer the kprobes emit
    (first octet = least-significant byte). This is the exact inverse of the
    analysis pipeline's ``int_to_ip`` decoder, so corrected traces parse back
    to the same dotted quad.
    Example: "192.168.1.1" -> str(192 | 168<<8 | 1<<16 | 1<<24) = "16951488"
    """
    a, b, c, d = (int(part) for part in ip.split('.'))
    return str(a | (b << 8) | (c << 16) | (d << 24))


def port_to_trace_be(port: str) -> str:
    """
    Encode a real (host-order) port as the byte-swapped u16 the kprobes emit
    for ``dst_port`` (network byte order read as host-order u16). The analysis
    pipeline applies ``convert_port_endianness`` on dst_port, recovering the
    real port. src_port is host-order in traces and is written as-is.
    """
    value = int(port)
    return str(((value & 0xFF) << 8) | ((value >> 8) & 0xFF))


def process_udp_sendmsg_line(line: str, correlation: Dict) -> str:
    """
    Process a udp_sendmsg line and replace socket_addr/unbound_addr with src_ip/dst_ip and ports.
    """
    # Extract the timestamp from the line
    timestamp_match = re.search(r'\[\d+\]\s+[\w\.]+\s+(\d+\.\d+):', line)
    if not timestamp_match:
        return line

    # Replace socket_addr with src_ip (kprobe little-endian u32 encoding)
    socket_addr_pattern = r'socket_addr=\{[^}]+\}'
    if correlation['pcap_src_ip']:
        new_src_ip = f"src_ip={ip_to_trace_int(correlation['pcap_src_ip'])}"
        line = re.sub(socket_addr_pattern, new_src_ip, line)

    # Replace unbound_addr with dst_ip (kprobe little-endian u32 encoding)
    unbound_addr_pattern = r'unbound_addr=\{[^}]+\}'
    if correlation['pcap_dst_ip']:
        new_dst_ip = f"dst_ip={ip_to_trace_int(correlation['pcap_dst_ip'])}"
        line = re.sub(unbound_addr_pattern, new_dst_ip, line)

    # Replace src_port (host order, as the kprobes emit it)
    src_port_pattern = r'src_port=\d+'
    if correlation['pcap_src_port']:
        new_src_port = f"src_port={correlation['pcap_src_port']}"
        line = re.sub(src_port_pattern, new_src_port, line)

    # Replace dst_port (byte-swapped, so downstream endianness conversion
    # recovers the real port)
    dst_port_pattern = r'dst_port=\d+'
    if correlation['pcap_dst_port']:
        new_dst_port = f"dst_port={port_to_trace_be(correlation['pcap_dst_port'])}"
        line = re.sub(dst_port_pattern, new_dst_port, line)

    return line


def process_udp_recvmsg_line(line: str, correlation: Dict) -> str:
    """
    Process a udp_recvmsg line and replace src_ip, dst_ip, and ports.

    The kprobe fields follow struct-sock semantics: dst_* is ALWAYS the remote
    peer, src_* the local endpoint, regardless of direction. For a received
    packet the pcap source is the remote sender, so the pcap src/dst pair is
    swapped when written back into the trace fields.
    """
    # Local endpoint (pcap destination) -> src_ip / src_port
    src_ip_pattern = r'src_ip=0x[0-9a-fA-F]+|src_ip=\d+'
    if correlation['pcap_dst_ip']:
        new_src_ip = f"src_ip={ip_to_trace_int(correlation['pcap_dst_ip'])}"
        line = re.sub(src_ip_pattern, new_src_ip, line)

    # Remote peer (pcap source) -> dst_ip / dst_port
    dst_ip_pattern = r'dst_ip=0x[0-9a-fA-F]+|dst_ip=\d+'
    if correlation['pcap_src_ip']:
        new_dst_ip = f"dst_ip={ip_to_trace_int(correlation['pcap_src_ip'])}"
        line = re.sub(dst_ip_pattern, new_dst_ip, line)

    # src_port: host order, as the kprobes emit it
    src_port_pattern = r'src_port=\d+'
    if correlation['pcap_dst_port']:
        new_src_port = f"src_port={correlation['pcap_dst_port']}"
        line = re.sub(src_port_pattern, new_src_port, line)

    # dst_port: byte-swapped, so downstream endianness conversion recovers it
    dst_port_pattern = r'dst_port=\d+'
    if correlation['pcap_src_port']:
        new_dst_port = f"dst_port={port_to_trace_be(correlation['pcap_src_port'])}"
        line = re.sub(dst_port_pattern, new_dst_port, line)

    return line


#: Matches the leading "process-tid" column of an ftrace line.
_TID_PATTERN = re.compile(r'^\s*\S+-(\d+)\s')


def _line_tid(line: str) -> Optional[str]:
    match = _TID_PATTERN.match(line)
    return match.group(1) if match else None


def process_trace_file(trace_path: str, output_path: str, correlations: Dict[float, Dict]):
    """
    Process a single trace file and create the modified version.

    A kretprobe fires on the same thread as its entry probe, so whether a
    ``udp_*_ret`` line is kept follows the fate of the most recent
    ``udp_sendmsg``/``udp_recvmsg`` line from the same tid.
    """
    # (tid, kind) -> True if the most recent main event from this thread was
    # kept, False if it was removed (uncorrelated).
    pending: Dict[tuple, bool] = {}

    kept = removed_main = removed_ret = 0

    with open_trace(trace_path) as f, open(output_path, 'w', encoding='utf-8') as out:
        for line in f:
            # Check if this is a UDP event line
            if 'udp_sendmsg:' in line or 'udp_recvmsg:' in line:
                kind = 'send' if 'udp_sendmsg:' in line else 'recv'
                tid = _line_tid(line)
                timestamp_match = re.search(r'\[\d+\]\s+[\w\.]+\s+(\d+\.\d+):', line)
                if timestamp_match:
                    timestamp = float(timestamp_match.group(1))
                    correlation = find_exact_timestamp(timestamp, correlations)
                    if correlation:
                        if kind == 'send':
                            line = process_udp_sendmsg_line(line, correlation)
                        else:
                            line = process_udp_recvmsg_line(line, correlation)
                        out.write(line)
                        kept += 1
                        if tid is not None:
                            pending[(tid, kind)] = True
                    else:
                        removed_main += 1
                        if tid is not None:
                            pending[(tid, kind)] = False
                # If timestamp extraction failed, drop the line.
            # Check if this is a UDP return event line
            elif 'udp_sendmsg_ret:' in line or 'udp_recvmsg_ret:' in line:
                kind = 'send' if 'udp_sendmsg_ret:' in line else 'recv'
                tid = _line_tid(line)
                ret_match = re.search(r'ret=(-?\d+)', line)
                main_kept = pending.pop((tid, kind), False) if tid is not None else False
                if ret_match and int(ret_match.group(1)) >= 0 and main_kept:
                    out.write(line)
                else:
                    removed_ret += 1
            else:
                # For non-UDP lines, keep them as is
                out.write(line)

    logger.info("Processed: %s -> %s (udp kept=%d, removed=%d, ret removed=%d)",
                trace_path, output_path, kept, removed_main, removed_ret)


def run(trace_path: str, correlations_path: str, output_path: str) -> int:
    """Rewrite UDP events in a single trace using its correlations CSV."""
    trace_path = resolve_input_path(trace_path)

    if not os.path.exists(correlations_path):
        logger.error("Correlations CSV not found: %s", correlations_path)
        return 1

    correlations = read_correlation_csv(correlations_path)
    if not correlations:
        logger.error("No correlations found in %s", correlations_path)
        return 1

    logger.info("Loaded %d correlations from %s", len(correlations), correlations_path)

    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
    process_trace_file(trace_path, output_path, correlations)

    print(f"Corrected trace written to {output_path}")
    return 0


def main():
    parser = argparse.ArgumentParser(
        description="Rewrite UDP trace events with correlated pcap addresses/ports."
    )
    parser.add_argument("--trace", default=DEFAULT_TRACE,
                        help=f"Path to the trace file, plain or gzipped (default: {DEFAULT_TRACE})")
    parser.add_argument("--correlations", default=DEFAULT_CORRELATIONS,
                        help=f"Path to the correlations CSV (default: {DEFAULT_CORRELATIONS})")
    parser.add_argument("--output", "-o", default=DEFAULT_OUTPUT,
                        help=f"Output corrected trace path (default: {DEFAULT_OUTPUT})")
    parser.add_argument("-v", "--verbose", action="store_true",
                        help="Enable debug logging")
    args = parser.parse_args()

    logging.basicConfig(level=logging.DEBUG if args.verbose else logging.INFO,
                        format="%(levelname)s %(name)s: %(message)s")

    try:
        sys.exit(run(args.trace, args.correlations, args.output))
    except FileNotFoundError as e:
        parser.exit(1, f"Error: {e}\n")


if __name__ == "__main__":
    main()
