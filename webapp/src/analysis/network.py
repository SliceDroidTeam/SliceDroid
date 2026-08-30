"""
Network helpers and metrics.

IP helpers, private-IP filtering and network metric accumulation ported
from the canonical replication-package notebook.  Byte counts come from
the ``*_ret`` kretprobe events (``ret`` values); only peers with public IP
addresses are counted.

Struct-sock semantics (verified against scripts/tracer/config_files/
kprobes.txt): the tcp/udp sendmsg/recvmsg kprobes read all fields from
``struct sock`` ($arg1):

- ``dst_ip``   = +0  (skc_daddr)      -> REMOTE peer address
- ``src_ip``   = +4  (skc_rcv_saddr)  -> LOCAL device address
- ``dst_port`` = +12 (skc_dport)      -> REMOTE port, big-endian
- ``src_port`` = +14 (skc_num)        -> LOCAL port, host byte order

So for BOTH send and recv events the remote peer is ``dst_ip``/``dst_port``
and the local endpoint is ``src_ip``/``src_port``.

Byte-order note (see DESIGN.md "IP BYTE ORDER"): the kernel socket fields
(skc_daddr/skc_rcv_saddr) are __be32 values read as u32 by the kprobes on a
little-endian CPU, so the integer printed in the trace is byte-swapped.
:func:`int_to_ip` therefore decodes little-endian (LSB is the first octet),
and :func:`is_private_ip` classifies the DECODED address so that display
and private-filtering always agree.  ``dst_port`` is likewise byte-swapped
(use :func:`convert_port_endianness`), while ``src_port`` is already in
host byte order.
"""

from __future__ import annotations

import ipaddress
import logging
from functools import lru_cache
from typing import Any

logger = logging.getLogger(__name__)

Event = dict[str, Any]

#: Events carrying src_ip/dst_ip details
NETWORK_DATA_EVENTS = ('tcp_sendmsg', 'tcp_recvmsg', 'udp_sendmsg', 'udp_recvmsg')


def int_to_ip(ip_int: int) -> str:
    """
    Convert a raw trace IP integer to dotted decimal notation.

    The kprobes read network-byte-order (__be32) socket fields as u32 on a
    little-endian CPU, so the least significant byte of the integer is the
    first octet of the address.
    """
    if ip_int == 0:
        return "0.0.0.0"
    if not 0 <= ip_int <= 0xFFFFFFFF:
        return f"invalid_ip_{ip_int}"
    return f"{ip_int & 0xFF}.{(ip_int >> 8) & 0xFF}.{(ip_int >> 16) & 0xFF}.{(ip_int >> 24) & 0xFF}"


@lru_cache(maxsize=4096)
def is_private_ip(ip_int: int) -> bool:
    """
    Check if a raw trace IP integer denotes a private IP address.

    The check runs on the correctly decoded dotted-quad address (see
    :func:`int_to_ip`), never on the raw byte-swapped integer.
    """
    if ip_int == 0:
        return True  # Treat 0.0.0.0 as private
    decoded = int_to_ip(ip_int)
    try:
        return ipaddress.ip_address(decoded).is_private
    except ValueError:
        return True  # Treat invalid IPs as private (to be safe)


def has_private_ip(event: Event) -> bool:
    """
    Return True when the event's REMOTE endpoint is a non-zero private IP.

    Per the kprobe struct-sock layout (see module docstring), ``dst_ip``
    (skc_daddr) is the remote peer for both send and recv events, while
    ``src_ip`` (skc_rcv_saddr) is the device's own LOCAL address.  The
    local address is deliberately ignored: on WiFi it is essentially
    always private (192.168.x.y), so filtering on it would silently drop
    every network event of a real trace.
    """
    dst_ip = event.get('details', {}).get('dst_ip', 0)
    return dst_ip != 0 and is_private_ip(dst_ip)


def filter_private_ip_events(events: list[Event]) -> list[Event]:
    """
    Filter out network events whose REMOTE endpoint (dst_ip) is a non-zero
    private IP address, including their corresponding ``*_ret`` events.

    The local endpoint (src_ip) is never considered: it is the device's
    own address and is private on any WiFi network (see module docstring).
    """
    if not events:
        return events

    filtered_events = []
    skip_next_ret: set[str] = set()  # Track which ret events to skip

    for event in events:
        event_type = event['event']

        # Check if this is a ret event we should skip
        if event_type.endswith('_ret'):
            base_event = event_type[:-4]  # Remove '_ret' suffix
            if base_event in skip_next_ret:
                skip_next_ret.discard(base_event)
                continue  # Skip this ret event

        # Check if this is a network event with IP addresses
        if event_type in NETWORK_DATA_EVENTS:
            if has_private_ip(event):
                # Mark the corresponding ret event to be skipped
                skip_next_ret.add(event_type)
                continue  # Skip this event

        filtered_events.append(event)

    return filtered_events


def convert_port_endianness(port: int) -> int:
    """
    Convert a 16-bit port between big-endian (as read by the ftrace kprobes
    from the network-byte-order ``skc_dport`` field) and host byte order.

    The operation is its own inverse (a byte swap).  Apply it to raw
    ``dst_port`` detail values to obtain the human-readable port number;
    ``src_port`` (skc_num) is already in host byte order and must NOT be
    converted.
    """
    return ((port & 0xFF) << 8) | ((port >> 8) & 0xFF)


#: Dispatch table for NetworkAccumulator.update:
#: {event name: (protocol, direction, is_ret, buffer-size detail field)}.
#: The size field names the entry probe's requested buffer length detail
#: ('size' for tcp_sendmsg, 'len' for the other three); actual byte counts
#: come from the *_ret events, and buffer sizes are not part of the frozen
#: contract, so the field is documentation only.
_EVENT_DISPATCH: dict[str, tuple] = {
    'tcp_sendmsg':     ('tcp', 'send', False, 'size'),
    'tcp_sendmsg_ret': ('tcp', 'send', True, None),
    'tcp_recvmsg':     ('tcp', 'recv', False, 'len'),
    'tcp_recvmsg_ret': ('tcp', 'recv', True, None),
    'udp_sendmsg':     ('udp', 'send', False, 'len'),
    'udp_sendmsg_ret': ('udp', 'send', True, None),
    'udp_recvmsg':     ('udp', 'recv', False, 'len'),
    'udp_recvmsg_ret': ('udp', 'recv', True, None),
}


class NetworkAccumulator:
    """
    Accumulates network activity from a deduplicated event sequence.

    Tracks unique connections and peers (public REMOTE addresses only; the
    remote peer is always dst_ip/dst_port, see module docstring) and actual
    bytes from ``*_ret`` events.  Additionally attributes ret bytes to the
    peer/connection of the immediately preceding sendmsg/recvmsg on the
    same thread (a kretprobe fires on the same tid as its entry probe), and
    tracks first/last timestamps per connection.

    Feed it each event exactly once: callers must deduplicate events
    collected from overlapping analysis windows before calling
    :meth:`update`, otherwise bytes and connection counts are inflated.
    """

    def __init__(self) -> None:
        self.tcp_connections: set[tuple] = set()
        self.udp_connections: set[tuple] = set()
        self.tcp_peers: set[int] = set()
        self.udp_peers: set[int] = set()
        # {ip_int: {'ports': set, 'connections': int, 'bytes_sent': int, 'bytes_received': int}}
        self.detailed_tcp_peers: dict[int, dict[str, Any]] = {}
        self.detailed_udp_peers: dict[int, dict[str, Any]] = {}
        # {(protocol, 4-tuple): {'bytes_sent', 'bytes_received', 'first_ts', 'last_ts'}}
        self.connection_stats: dict[tuple, dict[str, Any]] = {}
        # (tid, protocol, direction) -> (peer_ip, connection key) awaiting a *_ret event
        self._pending: dict[tuple[int, str, str], tuple[int, tuple]] = {}
        self.tcp_bytes_sent = 0
        self.tcp_bytes_received = 0
        self.udp_bytes_sent = 0
        self.udp_bytes_received = 0

    @staticmethod
    def _track_peer(detailed: dict[int, dict[str, Any]], ip: int, port: int) -> None:
        if ip not in detailed:
            detailed[ip] = {'ports': set(), 'connections': 0, 'bytes_sent': 0, 'bytes_received': 0}
        detailed[ip]['ports'].add(port)
        detailed[ip]['connections'] += 1

    def _track_connection(self, protocol: str, conn: tuple, timestamp: float) -> tuple:
        key = (protocol, conn)
        stats = self.connection_stats.get(key)
        if stats is None:
            self.connection_stats[key] = {
                'bytes_sent': 0,
                'bytes_received': 0,
                'first_ts': timestamp,
                'last_ts': timestamp,
            }
        else:
            stats['first_ts'] = min(stats['first_ts'], timestamp)
            stats['last_ts'] = max(stats['last_ts'], timestamp)
        return key

    def _attribute_ret(self, tid: int, protocol: str, direction: str,
                       ret_value: int, timestamp: float) -> None:
        """Attribute a *_ret byte count to the pending peer/connection of this tid."""
        pending = self._pending.pop((tid, protocol, direction), None)
        if pending is None:
            return
        peer_ip, conn_key = pending
        field = 'bytes_sent' if direction == 'send' else 'bytes_received'
        detailed = self.detailed_tcp_peers if protocol == 'tcp' else self.detailed_udp_peers
        if peer_ip in detailed:
            detailed[peer_ip][field] += ret_value
        stats = self.connection_stats.get(conn_key)
        if stats is not None:
            stats[field] += ret_value
            stats['last_ts'] = max(stats['last_ts'], timestamp)

    def _handle_data_event(self, protocol: str, direction: str,
                           details: dict[str, Any], tid: int, timestamp: float) -> None:
        """
        Track connection and peer state for a sendmsg/recvmsg entry probe.

        The REMOTE peer is dst_ip/dst_port and the LOCAL endpoint is
        src_ip/src_port for BOTH directions (struct-sock field layout, see
        module docstring), so send and recv events of the same socket
        collapse to a single (src_ip, src_port, dst_ip, dst_port) tuple.
        """
        dst_ip = details.get('dst_ip', 0)
        if is_private_ip(dst_ip):
            return  # only public remote peers are tracked
        src_ip = details.get('src_ip', 0)
        src_port = details.get('src_port', 0)
        dst_port = details.get('dst_port', 0)

        conn = (src_ip, src_port, dst_ip, dst_port)
        if protocol == 'tcp':
            connections, peers, detailed = (
                self.tcp_connections, self.tcp_peers, self.detailed_tcp_peers)
        else:
            connections, peers, detailed = (
                self.udp_connections, self.udp_peers, self.detailed_udp_peers)

        connections.add(conn)
        peers.add(dst_ip)
        self._track_peer(detailed, dst_ip, dst_port)
        conn_key = self._track_connection(protocol, conn, timestamp)
        self._pending[(tid, protocol, direction)] = (dst_ip, conn_key)

    def update(self, relevant_events: list[Event]) -> None:
        """Accumulate network activity from a deduplicated event sequence."""
        for event in relevant_events:
            dispatch = _EVENT_DISPATCH.get(event['event'])
            if dispatch is None:
                continue
            protocol, direction, is_ret, _size_field = dispatch
            details = event.get('details', {})
            tid = event.get('tid', 0)
            timestamp = event.get('timestamp', 0.0)

            if is_ret:
                ret_value = details.get('ret', 0)
                if ret_value > 0:  # negative ret values are errors
                    counter = f"{protocol}_bytes_{'sent' if direction == 'send' else 'received'}"
                    setattr(self, counter, getattr(self, counter) + ret_value)
                    self._attribute_ret(tid, protocol, direction, ret_value, timestamp)
            else:
                self._handle_data_event(protocol, direction, details, tid, timestamp)

    def _peers_list(self, detailed: dict[int, dict[str, Any]], protocol: str) -> list[dict[str, Any]]:
        peers = []
        for ip_int, info in detailed.items():
            peers.append({
                'ip': int_to_ip(ip_int),
                'protocol': protocol,
                # peer ports are always dst_port values (big-endian) -> convert
                'ports': sorted(convert_port_endianness(p) for p in info['ports']),
                'connections': info['connections'],
                'bytes_sent': info['bytes_sent'],
                'bytes_received': info['bytes_received'],
            })
        return peers

    def _connections_list(self) -> list[dict[str, Any]]:
        result = []
        for (protocol, conn), stats in sorted(self.connection_stats.items()):
            src_ip, src_port, dst_ip, dst_port = conn
            result.append({
                'protocol': protocol,
                'src': int_to_ip(src_ip),
                'sport': src_port,  # skc_num is host byte order: emit raw
                'dst': int_to_ip(dst_ip),
                'dport': convert_port_endianness(dst_port),  # skc_dport is big-endian
                'bytes_sent': stats['bytes_sent'],
                'bytes_received': stats['bytes_received'],
                'first_ts': stats['first_ts'],
                'last_ts': stats['last_ts'],
            })
        return result

    def summary(self) -> dict[str, Any]:
        """Build the ``network`` section of the analysis JSON contract."""
        return {
            'metrics': {
                'tcp_connections': len(self.tcp_connections),
                'udp_connections': len(self.udp_connections),
                'unique_tcp_peers': len(self.tcp_peers),
                'unique_udp_peers': len(self.udp_peers),
                'tcp_bytes_sent': self.tcp_bytes_sent,
                'tcp_bytes_received': self.tcp_bytes_received,
                'udp_bytes_sent': self.udp_bytes_sent,
                'udp_bytes_received': self.udp_bytes_received,
            },
            'peers': (self._peers_list(self.detailed_tcp_peers, 'tcp')
                      + self._peers_list(self.detailed_udp_peers, 'udp')),
            'connections': self._connections_list(),
        }
