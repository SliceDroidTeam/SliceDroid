#/bin/sh

rm /data/local/tmp/trace.trace
rm /data/local/tmp/trace.trace.gz

# Configure tracing options
echo 102400 > /sys/kernel/tracing/buffer_size_kb
echo record-tgid > /sys/kernel/tracing/trace_options

# Disable all events
echo 0 > /sys/kernel/tracing/events/enable
echo > /sys/kernel/tracing/trace

# Clear kprobes and filters
echo > /sys/kernel/tracing/kprobe_events
#echo > /sys/kernel/tracing/events/kprobes/filter
echo > /sys/kernel/tracing/events/binder/filter

while read -r probe; do
    echo "$probe" >> /sys/kernel/tracing/kprobe_events
done < config_files/kprobes.txt

device_tag="generic"
if [[ "$(getprop ro.product.brand)" == "google" ]]; then
    device_tag="pixel"
fi
# Enable brand-specific kprobes
while IFS='->' read -r tag probe; do
    [[ "$tag" == "$device_tag" ]] && echo "$probe" >> /sys/kernel/tracing/kprobe_events
done < config_files/kprobes_conditional.txt

# Start reading from the trace pipe in the background
cat /sys/kernel/tracing/trace_pipe > /data/local/tmp/trace.trace &
waitpid=$!

# Initialize an empty list of PIDs
all_pids=""

# Read the list and run appropriate pgrep
while IFS=',' read -r mode name; do
    if [[ "$mode" == "-x" ]]; then
        pids=$(pgrep -x "$name")
    else
        # If only one field, it's the name without -x
        pids=$(pgrep "$mode")
    fi

    all_pids+=" $pids"
done < config_files/pid_targets.txt

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

# Add PIDs to the filter
while read -r event; do
    echo "($pid_string)" > /sys/kernel/tracing/$event/filter
done < config_files/events_to_filter.txt

# Enable events
while read -r event; do
    echo 1 > "/sys/kernel/tracing/$event/enable"
done < config_files/events_to_enable.txt

# Execute monkey
#monkey -p $1 --ignore-crashes --ignore-timeouts --pct-majornav 0 --pct-motion 0 --throttle 500 1000
#monkey --ignore-crashes --ignore-timeouts --throttle 500 800

# For simple tracing
read STOP

# Stop tracing
echo 0 > /sys/kernel/tracing/tracing_on

# Start a timer in the background
sleep 10 &
timeout_pid=$!

# Wait for either process to finish
wait -n $waitpid $timeout_pid 2>/dev/null

# Check if the timeout expired first
if kill -0 $waitpid 2>/dev/null; then
  echo "Timeout expired. Killing process $bg_pid."
  kill $waitpid
else
  echo "Process $waitpid finished before the timeout."
fi
#
#if ! timeout 10s wait $waitpid; then
#  echo "Command timed out, terminating."
#  kill -9 $waitpid 2>/dev/null
#fi
#
# Print output file size
ls -alh /data/local/tmp/trace.trace

echo 'Starting gzip'
gzip -f /data/local/tmp/trace.trace
echo 'Finished gzip'
# Print zipped file size
ls -alh /data/local/tmp/trace.trace.gz
