"""Trace/pcap correlation utilities for SliceDroid.

- trace_pcap_correlator: match tcp/udp sendmsg/recvmsg ftrace events against
  packets in a tcpdump capture and emit a correlations CSV.
- update_udp_events: rewrite UDP trace events with the correlated pcap
  addresses/ports and drop uncorrelated UDP lines.
"""
