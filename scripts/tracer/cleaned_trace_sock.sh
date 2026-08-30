#!/system/bin/sh
#
# SliceDroid on-device tracer.
#
# Configures ftrace/kprobes, starts a background trace_pipe reader, builds a
# single common_pid exclusion filter for helper processes, starts tcpdump for a
# correlated packet capture, then enables tracing. Press ENTER (stdin newline)
# to stop: tracing is disabled, tcpdump is terminated, and BOTH the ftrace log
# and the pcap are gzipped for retrieval.
#
# POSIX /system/bin/sh (mksh) only -- no bashisms.

CONFIG_DIR="/data/local/tmp/config_files"
TRACE_DIR="/sys/kernel/tracing"
TMP_DIR="/data/local/tmp"

# Clean up any artefacts from a previous run
rm -f $TMP_DIR/trace.trace
rm -f $TMP_DIR/trace.trace.gz
rm -f $TMP_DIR/ps_snapshot.txt
rm -f $TMP_DIR/tcpdump.pcap
rm -f $TMP_DIR/tcpdump.pcap.gz

# Configure tracing options (100 MB ring buffer, record thread-group id)
echo 102400 > $TRACE_DIR/buffer_size_kb
echo record-tgid > $TRACE_DIR/trace_options

# Disable all events and clear old data
echo 0 > $TRACE_DIR/tracing_on
echo 0 > $TRACE_DIR/events/enable
echo > $TRACE_DIR/trace
echo > $TRACE_DIR/kprobe_events
echo > $TRACE_DIR/events/binder/filter

# Disable raw_syscalls that cause excessive events
echo 0 > $TRACE_DIR/events/raw_syscalls/sys_enter/enable 2>/dev/null || true
echo 0 > $TRACE_DIR/events/raw_syscalls/sys_exit/enable 2>/dev/null || true

# Load kprobes
if [ -f "$CONFIG_DIR/kprobes.txt" ]; then
    while read -r probe; do
        [ -n "$probe" ] || continue
        echo "$probe" >> $TRACE_DIR/kprobe_events
    done < "$CONFIG_DIR/kprobes.txt"
fi

# Start trace_pipe background read
cat $TRACE_DIR/trace_pipe > $TMP_DIR/trace.trace &
waitpid=$!

# Take process snapshot (useful for offline pid -> package resolution)
echo "Taking process snapshot..."
ps -A > $TMP_DIR/ps_snapshot.txt

# Start tcpdump BEFORE building the pid exclusion filter so its PID can be
# excluded from the ftrace capture. The script already runs as root (invoked
# via `su -c`), so tcpdump is started directly and $! is its real PID. Give it
# a short warmup so it is fully initialised before we turn tracing on.
echo "Starting tcpdump for network capture..."
tcpdump -i any -w $TMP_DIR/tcpdump.pcap -s 0 -U &
tcpdump_pid=$!
sleep 3
if kill -0 $tcpdump_pid 2>/dev/null; then
    echo "tcpdump running (PID: $tcpdump_pid)"
else
    echo "Warning: tcpdump did not start; continuing without packet capture"
    tcpdump_pid=""
fi

# Collect helper-process PIDs to exclude from the trace so they do not pollute
# the taint analysis: the background cat reader, our own shell, adbd, monkey
# and the tcpdump we just started.
cat_pids=$(pgrep cat)
sh_pids=$(pgrep -x sh)
monkey_pids=$(pgrep monkey)
adbd_pids=$(pgrep -x adbd)
all_pids="$cat_pids $sh_pids $adbd_pids $monkey_pids $tcpdump_pid"

# Build the "common_pid != <pid> && ..." exclusion filter ONCE
pid_string=""
for pid in $all_pids; do
    [ -n "$pid_string" ] && pid_string="$pid_string && "
    pid_string="${pid_string}common_pid != $pid"
done

# Apply the exclusion filter to every event directory listed in events_to_filter.txt
if [ -f "$CONFIG_DIR/events_to_filter.txt" ]; then
    while read -r event; do
        [ -n "$event" ] || continue
        if [ -d "$TRACE_DIR/$event" ] && [ -w "$TRACE_DIR/$event/filter" ]; then
            echo "($pid_string)" > $TRACE_DIR/$event/filter 2>/dev/null
        fi
    done < "$CONFIG_DIR/events_to_filter.txt"
fi

# Enable selected events
if [ -f "$CONFIG_DIR/events_to_enable.txt" ]; then
    while read -r event; do
        [ -n "$event" ] || continue
        if [ -d "$TRACE_DIR/$event" ] && [ -w "$TRACE_DIR/$event/enable" ]; then
            echo 1 > "$TRACE_DIR/$event/enable" 2>/dev/null
        fi
    done < "$CONFIG_DIR/events_to_enable.txt"
fi

# IMPORTANT: enable tracing AFTER all configuration is done
echo 1 > $TRACE_DIR/tracing_on
echo "Tracing enabled. Starting data collection..."

echo "Trace collection active. Press ENTER to stop..."

# Wait for the caller (run_slicedroid.py) to send a newline
read STOP

echo "Stopping trace collection..."

# Stop tracing
echo 0 > $TRACE_DIR/tracing_on

# Stop tcpdump cleanly and WAIT until it has exited so all buffered packets
# are flushed before the pcap is compressed.
echo "Stopping tcpdump..."
if [ -n "$tcpdump_pid" ] && kill -0 $tcpdump_pid 2>/dev/null; then
    kill -TERM $tcpdump_pid
    tries=0
    while kill -0 $tcpdump_pid 2>/dev/null && [ $tries -lt 10 ]; do
        sleep 1
        tries=$((tries + 1))
    done
    if kill -0 $tcpdump_pid 2>/dev/null; then
        echo "tcpdump did not exit after ${tries}s; killing it."
        kill -KILL $tcpdump_pid 2>/dev/null
        sleep 1
    fi
    echo "tcpdump stopped (PID: $tcpdump_pid)"
else
    echo "tcpdump process not found (may have already stopped)"
fi

# Give the background trace_pipe reader a chance to drain, then reap it
sleep 10 &
timeout_pid=$!
wait -n $waitpid $timeout_pid 2>/dev/null

if kill -0 $waitpid 2>/dev/null; then
    echo "Timeout expired. Killing trace_pipe (pid $waitpid)."
    kill $waitpid
else
    echo "Trace collection completed before timeout."
fi

# Report artefact sizes
echo "Trace file info:"
ls -alh $TMP_DIR/trace.trace
echo "Process snapshot file:"
ls -alh $TMP_DIR/ps_snapshot.txt
echo "tcpdump file info:"
ls -alh $TMP_DIR/tcpdump.pcap 2>/dev/null || echo "  (no pcap captured)"

# Gzip both artefacts for retrieval
echo "Starting gzip compression..."
gzip -f $TMP_DIR/trace.trace
echo "Trace compression completed."

if [ -f "$TMP_DIR/tcpdump.pcap" ]; then
    echo "Compressing tcpdump capture..."
    gzip -f $TMP_DIR/tcpdump.pcap
    echo "tcpdump compression completed."
fi

echo "Final compressed trace file:"
ls -alh $TMP_DIR/trace.trace.gz
echo "Final compressed tcpdump file:"
ls -alh $TMP_DIR/tcpdump.pcap.gz 2>/dev/null || echo "  (no pcap captured)"

echo "Script completed successfully."
exit 0
