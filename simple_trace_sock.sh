#!/bin/sh

# Check if the script is running as root
if [ "$(id -u)" -ne 0 ]; then
  echo "Script must be run as root!"
  exit 1
fi

# Find the appropriate tracing path
if [ -d "/sys/kernel/tracing" ]; then
  TRACE_DIR="/sys/kernel/tracing"
elif [ -d "/sys/kernel/debug/tracing" ]; then
  TRACE_DIR="/sys/kernel/debug/tracing"
else
  echo "Cannot find a valid tracing directory. Exiting..."
  exit 1
fi

# Remove old traces
rm /data/local/tmp/trace.trace
rm /data/local/tmp/trace.trace.gz

# Configure tracing options
echo 102400 > $TRACE_DIR/buffer_size_kb
echo record-tgid > $TRACE_DIR/trace_options

# Disable all events
echo 0 > $TRACE_DIR/events/enable
echo > $TRACE_DIR/trace

# Clear kprobes and filters
echo > $TRACE_DIR/kprobe_events
echo > $TRACE_DIR/events/binder/filter

# Define kprobe events
#echo 'p:kprobes/write_probe vfs_write file=$arg1 buf=$arg2 count=$arg3 inode=+64(+32($arg1)):u64 k__dev=+76(+32($arg1)):u32 s_dev_inode=+16(+40(+32($arg1))):u32 i_mode=+0(+32($arg1)):u16 kuid=+4(+32($arg1)):u32 kgid=+8(+32($arg1)):u32 pathname=+0(+40(+24($arg1))):string' >> $TRACE_DIR/kprobe_events
echo 'p:kprobes/write_probe generic_file_write_iter file=$arg1 buf=$arg2 count=$arg3 inode=+64(+32($arg1)):u64 k__dev=+76(+32($arg1)):u32 s_dev_inode=+16(+40(+32($arg1))):u32 i_mode=+0(+32($arg1)):u16 kuid=+4(+32($arg1)):u32 kgid=+8(+32($arg1)):u32 pathname=+0(+40(+24($arg1))):string' >> $TRACE_DIR/kprobe_events
echo 'p:kprobes/read_probe generic_file_read_iter file=$arg1 buf=+24($arg2):x64 count=+16($arg2):u64 inode=+64(+32($arg1)):u64 k__dev=+76(+32($arg1)):u32 s_dev_inode=+16(+40(+32($arg1))):u32 i_mode=+0(+32($arg1)):u16 kuid=+4(+32($arg1)):u32 kgid=+8(+32($arg1)):u32 pathname=+0(+40(+24($arg1))):string' >> $TRACE_DIR/kprobe_events
#echo 'p:kprobes/read_probe vfs_read file=$arg1 buf=$arg2 count=$arg3 inode=+64(+32($arg1)):u64 k__dev=+76(+32($arg1)):u32 s_dev_inode=+16(+40(+32($arg1))):u32 i_mode=+0(+32($arg1)):u16 kuid=+4(+32($arg1)):u32 kgid=+8(+32($arg1)):u32 pathname=+0(+40(+24($arg1))):string' >> $TRACE_DIR/kprobe_events
echo 'p:kprobes/ioctl_probe do_vfs_ioctl file=$arg1 inode=+64(+32($arg1)):u64 k__dev=+76(+32($arg1)):u32 s_dev_inode=+16(+40(+32($arg1))):u32 i_mode=+0(+32($arg1)):u16 kuid=+4(+32($arg1)):u32 kgid=+8(+32($arg1)):u32 pathname=+0(+40(+24($arg1))):string' >> $TRACE_DIR/kprobe_events
echo 'p:kprobes/unix_stream_sendmsg unix_stream_sendmsg sock=$arg1 msg=$arg2 len=$arg3 topid=+96(+592(+24($arg1))):u32 inode=+64(+32(+16($arg1))):u64 k__dev=+76(+32(+16($arg1))):u32 s_dev_inode=+16(+40(+32(+16($arg1)))):u32 i_mode=+0(+32(+16($arg1))):u16 kuid=+4(+32(+16($arg1))):u32 kgid=+8(+32(+16($arg1))):u32 pathname=+0(+40(+24(+16($arg1)))):string' >> $TRACE_DIR/kprobe_events
echo 'p:kprobes/unix_stream_recvmsg unix_stream_recvmsg sock=$arg1 msg=$arg2 len=$arg3 frompid=+96(+592(+24($arg1))):u32 inode=+64(+32(+16($arg1))):u64 k__dev=+76(+32(+16($arg1))):u32 s_dev_inode=+16(+40(+32(+16($arg1)))):u32 i_mode=+0(+32(+16($arg1))):u16 kuid=+4(+32(+16($arg1))):u32 kgid=+8(+32(+16($arg1))):u32 pathname=+0(+40(+24(+16($arg1)))):string' >> $TRACE_DIR/kprobe_events
echo 'p:kprobes/unix_dgram_sendmsg unix_dgram_sendmsg sock=$arg1 msg=$arg2 len=$arg3 inode=+64(+32(+16($arg1))):u64 k__dev=+76(+32(+16($arg1))):u32 s_dev_inode=+16(+40(+32(+16($arg1)))):u32 i_mode=+0(+32(+16($arg1))):u16 kuid=+4(+32(+16($arg1))):u32 kgid=+8(+32(+16($arg1))):u32 pathname=+0(+40(+24(+16($arg1)))):string' >> $TRACE_DIR/kprobe_events
echo 'p:kprobes/unix_dgram_recvmsg unix_dgram_recvmsg sock=$arg1 msg=$arg2 len=$arg3 inode=+64(+32(+16($arg1))):u64 k__dev=+76(+32(+16($arg1))):u32 s_dev_inode=+16(+40(+32(+16($arg1)))):u32 i_mode=+0(+32(+16($arg1))):u16 kuid=+4(+32(+16($arg1))):u32 kgid=+8(+32(+16($arg1))):u32 pathname=+0(+40(+24(+16($arg1)))):string' >> $TRACE_DIR/kprobe_events
echo 'p:kprobes/sock_queue_tail skb_queue_tail sk_receive_queue=$arg1 skb=$arg2 socket=+424($arg1):x64 inode=+64(+32(+16(+424($arg1)))):u64' >> $TRACE_DIR/kprobe_events
echo 'r:kprobes/sco_sock_sendmsg sco_sock_sendmsg error=$retval:u32' >> $TRACE_DIR/kprobe_events
echo 'r:kprobes/l2cap_sock_sendmsg l2cap_sock_sendmsg error=$retval:u32' >> $TRACE_DIR/kprobe_events
echo 'r:kprobes/hci_sock_sendmsg hci_sock_sendmsg error=$retval:u32' >> $TRACE_DIR/kprobe_events
echo 'r:kprobes/sock_sendmsg sock_sendmsg num=$retval:u32' >> $TRACE_DIR/kprobe_events
# Pixel-specific kprobe for AoC sensors
#echo 'p:kprobes/aoc_service_write_message aoc_service_write_message service=$arg1 base=$arg2 dir=$arg3 size=$arg5 channel=+0($arg4):x32 sensor=+0($arg4):x32[36]' >> $TRACE_DIR/kprobe_events

# Start reading from the trace pipe in the background
cat $TRACE_DIR/trace_pipe > /data/local/tmp/trace.trace &
waitpid=$!

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

# Set filters
echo "($pid_string)" > $TRACE_DIR/events/binder/filter
echo "($pid_string)" > $TRACE_DIR/events/kprobes/write_probe/filter
echo "($pid_string)" > $TRACE_DIR/events/kprobes/read_probe/filter
echo "($pid_string)" > $TRACE_DIR/events/kprobes/ioctl_probe/filter
echo "($pid_string)" > $TRACE_DIR/events/sock/inet_sock_set_state/filter
echo "($pid_string)" > $TRACE_DIR/events/kprobes/unix_dgram_sendmsg/filter
echo "($pid_string)" > $TRACE_DIR/events/kprobes/unix_dgram_recvmsg/filter
echo "($pid_string)" > $TRACE_DIR/events/kprobes/unix_stream_sendmsg/filter
echo "($pid_string)" > $TRACE_DIR/events/kprobes/unix_stream_recvmsg/filter
echo "($pid_string)" > $TRACE_DIR/events/kprobes/sock_queue_tail/filter
echo "($pid_string)" > $TRACE_DIR/events/kprobes/hci_sock_sendmsg/filter
echo "($pid_string)" > $TRACE_DIR/events/kprobes/sco_sock_sendmsg/filter
echo "($pid_string)" > $TRACE_DIR/events/kprobes/l2cap_sock_sendmsg/filter
echo "($pid_string)" > $TRACE_DIR/events/kprobes/sock_sendmsg/filter

# Add Pixel-specific filter for AoC sensors
#echo "size == 0x90 || size == 0x5c || size == 0x40" > $TRACE_DIR/events/kprobes/aoc_service_write_message/filter

# Enable kprobe events
echo 1 > $TRACE_DIR/events/kprobes/write_probe/enable
echo 1 > $TRACE_DIR/events/kprobes/read_probe/enable
echo 1 > $TRACE_DIR/events/kprobes/ioctl_probe/enable
echo 1 > $TRACE_DIR/events/kprobes/unix_dgram_sendmsg/enable
echo 1 > $TRACE_DIR/events/kprobes/unix_dgram_recvmsg/enable
echo 1 > $TRACE_DIR/events/kprobes/unix_stream_sendmsg/enable
echo 1 > $TRACE_DIR/events/kprobes/unix_stream_recvmsg/enable
echo 1 > $TRACE_DIR/events/kprobes/sock_queue_tail/enable

# Enable binder tracepoints
echo 1 > $TRACE_DIR/events/binder/binder_transaction/enable
echo 1 > $TRACE_DIR/events/binder/binder_transaction_received/enable

# Enable inet socket state transition tracing
echo 1 > $TRACE_DIR/events/sock/inet_sock_set_state/enable

# Enable Bluetooth sockets
echo 1 > $TRACE_DIR/events/kprobes/hci_sock_sendmsg/enable
echo 1 > $TRACE_DIR/events/kprobes/sco_sock_sendmsg/enable
echo 1 > $TRACE_DIR/events/kprobes/l2cap_sock_sendmsg/enable

# Added network sockets
echo 1 > $TRACE_DIR/events/kprobes/sock_sendmsg/enable

# Enable Pixel-specific AoC sensor identification
echo 1 > $TRACE_DIR/events/kprobes/aoc_service_write_message/enable

# Start Tracing
echo 1 > $TRACE_DIR/tracing_on

# For simple tracing
read STOP

# Stop tracing
echo 0 > $TRACE_DIR/tracing_on

# Start a timer in the background
sleep 10 &
timeout_pid=$!

# Wait for either process to finish
wait -n $waitpid $timeout_pid 2>/dev/null

# Check if the timeout expired first
if kill -0 $waitpid 2>/dev/null; then
  echo "Timeout expired. Killing process $waitpid."
  kill $waitpid
else
  echo "Process $waitpid finished before the timeout."
fi

# Print output file size
ls -alh /data/local/tmp/trace.trace

echo 'Starting gzip'
gzip -f /data/local/tmp/trace.trace
echo 'Finished gzip'

# Print zipped file size
ls -alh /data/local/tmp/trace.trace.gz
