# Tracing with SliceDroid

SliceDroid captures kernel activity on a rooted Android device using ftrace
kprobes (`scripts/tracer/cleaned_trace_sock.sh`) and, in parallel, records the
device's network traffic with `tcpdump`. Both artefacts are pulled to
`data/traces/` and can optionally be correlated to recover the real network
endpoints of UDP events.

---

## 1. Prerequisites

- **ADB installed**: `run_slicedroid.py` downloads platform-tools automatically
  if `adb` is not on your PATH.
- **USB debugging enabled** on the device (Developer Options).
- **Root access**: the device must be rooted (`su` available).
- **tcpdump on the device**: available in the PATH of the root shell (most
  rooted ROMs ship one; otherwise push a static binary). Without it you still
  get the ftrace trace, just no packet capture.
- **Optional (host)**: `pip install scapy` for the correlation step.

---

## 2. The easy way: `run_slicedroid.py`

The entry point exposes subcommands (run with no arguments for the
interactive menu):

```bash
# One-time device setup: app mapping + resource resolution
python run_slicedroid.py setup

# Capture a trace (+ tcpdump pcap) from the connected device
python run_slicedroid.py trace

# Same, then correlate the trace with the pcap (requires scapy)
python run_slicedroid.py trace --correlate

# Trace only, do not pull the tcpdump capture
python run_slicedroid.py trace --skip-pcap

# Launch the web dashboard on http://localhost:5000
python run_slicedroid.py dashboard
```

`trace` performs the full workflow:

1. Checks ADB and the device connection.
2. Pushes `scripts/tracer/cleaned_trace_sock.sh` and
   `scripts/tracer/config_files/` to `/data/local/tmp/`.
3. Sets SELinux to permissive (`setenforce 0`) — remember to set it back to
   enforcing afterwards.
4. Runs the tracer as root. Interact with the device, then press **ENTER** in
   the terminal to stop.
5. Pulls `/data/local/tmp/trace.trace.gz` and
   `/data/local/tmp/tcpdump.pcap.gz` into `data/traces/` and unpacks the trace
   to `data/traces/trace.trace`.

---

## 3. What `cleaned_trace_sock.sh` does on the device

- Sets a 100 MB ftrace ring buffer and enables the `record-tgid` option.
- Loads the kprobes/kretprobes from `config_files/kprobes.txt` (VFS
  read/write/ioctl, unix sockets, binder, tcp/udp send/recv + return probes).
- Starts a background `cat /sys/kernel/tracing/trace_pipe > trace.trace`
  reader and takes a `ps -A` snapshot (`ps_snapshot.txt`).
- Builds a single `common_pid != ...` exclusion filter for helper processes
  (the `cat` reader, the tracer shell, `adbd`, `monkey`, `tcpdump`) and applies
  it to every event listed in `config_files/events_to_filter.txt`.
- Enables the events listed in `config_files/events_to_enable.txt`.
- Starts `tcpdump -i any -w /data/local/tmp/tcpdump.pcap -s 0 -U` as root and
  gives it ~3 seconds of warmup.
- Only then sets `tracing_on=1`, so the trace and the pcap cover the same
  window.
- On **ENTER**: stops tracing, SIGTERMs tcpdump (flushing its buffers), drains
  the trace pipe, and gzips **both** `trace.trace` and `tcpdump.pcap`.

---

## 4. Optional: trace/pcap correlation

The kernel reports UDP addresses/ports in a form that is often unusable
(unbound sockets, byte-order differences). The correlation step matches each
tcp/udp send/recv event (via its kretprobe return value) against the packets
in the pcap and rewrites the UDP events with the real endpoints.

`python run_slicedroid.py trace --correlate` does this automatically. To run
it manually:

```bash
# 1. Match trace events against pcap packets -> correlations.csv
python scripts/correlation/trace_pcap_correlator.py \
    --trace data/traces/trace.trace \
    --pcap data/traces/tcpdump.pcap \
    --output data/traces/correlations.csv

# 2. Rewrite UDP events using the correlations -> trace_corrected.trace
python scripts/correlation/update_udp_events.py \
    --trace data/traces/trace.trace \
    --correlations data/traces/correlations.csv \
    --output data/traces/trace_corrected.trace
```

Both scripts accept gzipped inputs (`.gz`), and fall back to the `.gz` variant
automatically when the plain file is absent. The correlator tries an exact
single-packet match first (ports + transferred size) and falls back to
combining TCP segments for large payloads. `update_udp_events.py` removes UDP
lines that could not be correlated as well as `*_ret` lines with negative
return values.

---

## 5. Manual tracing via ADB (no Python)

```bash
adb push scripts/tracer/cleaned_trace_sock.sh /data/local/tmp/
adb push scripts/tracer/config_files /data/local/tmp/
adb shell chmod +x /data/local/tmp/cleaned_trace_sock.sh
adb shell su -c 'dos2unix /data/local/tmp/cleaned_trace_sock.sh'
adb shell su -c setenforce 0
adb shell su -c /data/local/tmp/cleaned_trace_sock.sh
# ... use the device, press ENTER to stop ...
adb pull /data/local/tmp/trace.trace.gz data/traces/
adb pull /data/local/tmp/tcpdump.pcap.gz data/traces/
gunzip -k data/traces/trace.trace.gz
```

---

## 6. Troubleshooting

### Missing tracefs entries (`/sys/kernel/tracing/...` errors)
Check which kprobe events your kernel exposes:

```bash
adb shell su -c 'ls /sys/kernel/tracing/events/kprobes/'
```

If a probe from `config_files/kprobes.txt` fails to register (symbol not
present or different struct offsets on your kernel), remove or adapt that line.

### No pcap produced
`tcpdump` must be executable by the root shell. Verify with:

```bash
adb shell su -c 'tcpdump --version'
```

If it is missing, push a static `tcpdump` binary to the device and make sure
it is on root's PATH, or run with `--skip-pcap`.

### Script format issues (`^M` / `\r` errors)
The scripts are converted with `dos2unix` automatically by
`run_slicedroid.py`; when pushing manually run:

```bash
adb shell su -c 'dos2unix /data/local/tmp/cleaned_trace_sock.sh'
```

### SELinux
Tracing requires permissive mode. Restore enforcing mode when you are done:

```bash
adb shell su -c setenforce 1
```
