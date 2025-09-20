#!/system/bin/sh

CONFIG_DIR="/data/local/tmp/config_files"
TRACE_DIR="/sys/kernel/tracing"
TMP_DIR="/data/local/tmp"

rm -f $TMP_DIR/trace.trace
rm -f $TMP_DIR/trace.trace.gz
rm -f $TMP_DIR/ps_snapshot.txt

# Configure tracing options
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

# Load basic kprobes
if [ -f "$CONFIG_DIR/kprobes.txt" ]; then
    while read -r probe; do
        echo "$probe" >> $TRACE_DIR/kprobe_events
    done < "$CONFIG_DIR/kprobes.txt"
fi

# Start trace_pipe background read
cat $TRACE_DIR/trace_pipe > $TMP_DIR/trace.trace &
waitpid=$!

# Take process snapshot
echo "Taking process snapshot..."
ps -A > $TMP_DIR/ps_snapshot.txt

# Get PIDs for processes that contain "cat"
cat_pids=$(pgrep cat)

# Get PIDs for processes that exactly match "sh"
sh_pids=$(pgrep -x sh)

# Get PIDs for processes that contain "monkey"
monkey_pids=$(pgrep monkey)

# Get PIDs for processes that exactly match "adbd"
adbd_pids=$(pgrep -x adbd)
# Combine both sets of PIDs
all_pids="$cat_pids $sh_pids $adbd_pids $monkey_pids"

# Initialize an empty string to hold the PIDs
pid_string=""

# Loop through the PIDs and append them to the string
for pid in $all_pids; do
    # If pid_string is not empty, append ' && ' first
    if [ -n "$pid_string" ]; then
        pid_string+=" && "
    fi
    pid_string+="common_pid != $pid"
done

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

# IMPORTANT: Enable tracing AFTER all configuration is done
echo 1 > $TRACE_DIR/tracing_on
echo "Tracing enabled. Starting data collection..."


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

# Show process snapshot file
echo "Process snapshot file:"
ls -alh $TMP_DIR/ps_snapshot.txt

# Gzip the trace
echo "Starting gzip compression..."
gzip -f $TMP_DIR/trace.trace
echo "Compression completed."

# Show gzipped file
echo "Final compressed trace file:"
ls -alh $TMP_DIR/trace.trace.gz