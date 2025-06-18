#!/system/bin/sh

CONFIG_DIR="/data/local/tmp/config_files"
TRACE_DIR="/sys/kernel/tracing"
TMP_DIR="/data/local/tmp"

rm -f $TMP_DIR/trace.trace
rm -f $TMP_DIR/trace.trace.gz

# Configure tracing options
echo 102400 > $TRACE_DIR/buffer_size_kb
echo record-tgid > $TRACE_DIR/trace_options

# Disable all events and clear old data
echo 0 > $TRACE_DIR/tracing_on
echo 0 > $TRACE_DIR/events/enable
echo > $TRACE_DIR/trace
echo > $TRACE_DIR/kprobe_events
echo > $TRACE_DIR/events/binder/filter

# Load basic kprobes
if [ -f "$CONFIG_DIR/kprobes.txt" ]; then
    while read -r probe; do
        echo "$probe" >> $TRACE_DIR/kprobe_events
    done < "$CONFIG_DIR/kprobes.txt"
fi

# Load conditional kprobes by device tag
device_tag="generic"
if [ "$(getprop ro.product.brand)" = "google" ]; then
    device_tag="pixel"
fi

if [ -f "$CONFIG_DIR/kprobes_conditional.txt" ]; then
    while IFS='->' read -r tag probe; do
        [ "$tag" = "$device_tag" ] && echo "$probe" >> $TRACE_DIR/kprobe_events
    done < "$CONFIG_DIR/kprobes_conditional.txt"
fi

# Collect PIDs
all_pids=""
if [ -f "$CONFIG_DIR/pid_targets.txt" ]; then
    while IFS=',' read -r mode name; do
        if [ "$mode" = "-x" ]; then
            pids=$(pgrep -x "$name")
        else
            pids=$(pgrep "$mode")
        fi
        all_pids="$all_pids $pids"
    done < "$CONFIG_DIR/pid_targets.txt"
fi

# Create filter string
pid_string=""
for pid in $all_pids; do
    [ -n "$pid_string" ] && pid_string="$pid_string && "
    pid_string="${pid_string}common_pid != $pid"
done

# Apply event filters
if [ -f "$CONFIG_DIR/events_to_filter.txt" ]; then
    while read -r event; do
        if [ -d "$TRACE_DIR/$event" ] && [ -w "$TRACE_DIR/$event/filter" ]; then
            echo "($pid_string)" > $TRACE_DIR/$event/filter 2>/dev/null
        fi
    done < "$CONFIG_DIR/events_to_filter.txt"
fi

# Enable selected events
if [ -f "$CONFIG_DIR/events_to_enable.txt" ]; then
    while read -r event; do
        if [ -d "$TRACE_DIR/$event" ] && [ -w "$TRACE_DIR/$event/enable" ]; then
            echo 1 > "$TRACE_DIR/$event/enable" 2>/dev/null
        fi
    done < "$CONFIG_DIR/events_to_enable.txt"
fi

# Enable vendor-specific events
if [ -f "$CONFIG_DIR/events_to_enable_conditional.txt" ]; then
    while IFS='->' read -r tag event; do
        if [ "$tag" = "$device_tag" ] && [ -d "$TRACE_DIR/$event" ] && [ -w "$TRACE_DIR/$event/enable" ]; then
            echo 1 > "$TRACE_DIR/$event/enable" 2>/dev/null
        fi
    done < "$CONFIG_DIR/events_to_enable_conditional.txt"
fi

# Start trace_pipe background read BEFORE enabling tracing
cat $TRACE_DIR/trace_pipe > $TMP_DIR/trace.trace &
waitpid=$!

# IMPORTANT: Enable tracing AFTER trace_pipe is ready
echo 1 > $TRACE_DIR/tracing_on
echo "Tracing enabled. Data collection active..."

echo "Trace collection active. Press ENTER to stop..."

# Wait for user to stop
read STOP

echo "Stopping trace collection..."

# Stop tracing
echo 0 > $TRACE_DIR/tracing_on

# Background sleep for timeout
sleep 10 &
timeout_pid=$!

# Wait for either process to finish
wait -n $waitpid $timeout_pid 2>/dev/null

if kill -0 $waitpid 2>/dev/null; then
    echo "Timeout expired. Killing trace_pipe (pid $waitpid)."
    kill $waitpid
else
    echo "Trace collection completed before timeout."
fi

# Show output trace file
echo "Trace file info:"
ls -alh $TMP_DIR/trace.trace

# Gzip the trace
echo "Starting gzip compression..."
gzip -f $TMP_DIR/trace.trace
echo "Compression completed."

# Show gzipped file
echo "Final compressed trace file:"
ls -alh $TMP_DIR/trace.trace.gz