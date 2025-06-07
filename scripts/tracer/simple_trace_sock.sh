#/bin/sh

rm /data/local/tmp/trace.trace
rm /data/local/tmp/trace.trace.gz

# Configure tracing options
echo 102400 > /sys/kernel/tracing/buffer_size_kb
echo record-tgid > /sys/kernel/tracing/trace_options

#Define kprobe events
#echo 'p:write_probe vfs_write file=file buf=buf count=count pos=pos inode=file->f_inode->i_ino real_dev=file->f_inode->i_rdev content=buf:string' >> /sys/kernel/tracing/kprobe_events
#echo 'p:kprobes/write_probe vfs_write file=$arg1 buf=$arg2 count=$arg3 pos=$arg4 inode=+64(+32($arg1)):u64 k__dev=+76(+32($arg1)):u32 s_dev_inode=+16(+40(+32($arg1))):u32 s_dev_vfsmount=+16(+8(+16($arg1))):u32 pathname=+0(+40(+24($arg1))):string' >> /sys/kernel/tracing/kprobe_events
#echo 'p:kprobes/read_probe vfs_read file=$arg1 buf=$arg2 count=$arg3 pos=$arg4 inode=+64(+32($arg1)):u64 k__dev=+76(+32($arg1)):u32 s_dev_inode=+16(+40(+32($arg1))):u32 s_dev_vfsmount=+16(+8(+16($arg1))):u32 pathname=+0(+40(+24($arg1))):string' >> /sys/kernel/tracing/kprobe_events
#echo 'p:kprobes/ioctl_probe do_vfs_ioctl file=$arg1 inode=+64(+32($arg1)):u64 k__dev=+76(+32($arg1)):u32 s_dev_inode=+16(+40(+32($arg1))):u32 s_dev_vfsmount=+16(+8(+16($arg1))):u32 pathname=+0(+40(+24($arg1))):string' >> /sys/kernel/tracing/kprobe_events

# New version with i_mode, kuid, kgid
# First clear existing kprobes
# Disable all events
echo 0 > /sys/kernel/tracing/events/enable
echo > /sys/kernel/tracing/trace

# Clear kprobes and filters
echo > /sys/kernel/tracing/kprobe_events
#echo > /sys/kernel/tracing/events/kprobes/filter
echo > /sys/kernel/tracing/events/binder/filter

echo 'p:kprobes/write_probe vfs_write file=$arg1 buf=$arg2 count=$arg3 inode=+64(+32($arg1)):u64 k__dev=+76(+32($arg1)):u32 s_dev_inode=+16(+40(+32($arg1))):u32 i_mode=+0(+32($arg1)):u16 kuid=+4(+32($arg1)):u32 kgid=+8(+32($arg1)):u32 pathname=+0(+40(+24($arg1))):string' >> /sys/kernel/tracing/kprobe_events
echo 'p:kprobes/read_probe vfs_read file=$arg1 buf=$arg2 count=$arg3 inode=+64(+32($arg1)):u64 k__dev=+76(+32($arg1)):u32 s_dev_inode=+16(+40(+32($arg1))):u32 i_mode=+0(+32($arg1)):u16 kuid=+4(+32($arg1)):u32 kgid=+8(+32($arg1)):u32 pathname=+0(+40(+24($arg1))):string' >> /sys/kernel/tracing/kprobe_events
echo 'p:kprobes/ioctl_probe do_vfs_ioctl file=$arg1 inode=+64(+32($arg1)):u64 k__dev=+76(+32($arg1)):u32 s_dev_inode=+16(+40(+32($arg1))):u32 i_mode=+0(+32($arg1)):u16 kuid=+4(+32($arg1)):u32 kgid=+8(+32($arg1)):u32 pathname=+0(+40(+24($arg1))):string' >> /sys/kernel/tracing/kprobe_events
echo 'p:kprobes/unix_stream_sendmsg unix_stream_sendmsg sock=$arg1 msg=$arg2 len=$arg3 topid=+96(+592(+24($arg1))):u32 inode=+64(+32(+16($arg1))):u64 k__dev=+76(+32(+16($arg1))):u32 s_dev_inode=+16(+40(+32(+16($arg1)))):u32 i_mode=+0(+32(+16($arg1))):u16 kuid=+4(+32(+16($arg1))):u32 kgid=+8(+32(+16($arg1))):u32 pathname=+0(+40(+24(+16($arg1)))):string' >> /sys/kernel/tracing/kprobe_events
echo 'p:kprobes/unix_stream_recvmsg unix_stream_recvmsg sock=$arg1 msg=$arg2 len=$arg3 frompid=+96(+592(+24($arg1))):u32 inode=+64(+32(+16($arg1))):u64 k__dev=+76(+32(+16($arg1))):u32 s_dev_inode=+16(+40(+32(+16($arg1)))):u32 i_mode=+0(+32(+16($arg1))):u16 kuid=+4(+32(+16($arg1))):u32 kgid=+8(+32(+16($arg1))):u32 pathname=+0(+40(+24(+16($arg1)))):string' >> /sys/kernel/tracing/kprobe_events
echo 'p:kprobes/unix_dgram_sendmsg unix_dgram_sendmsg sock=$arg1 msg=$arg2 len=$arg3 inode=+64(+32(+16($arg1))):u64 k__dev=+76(+32(+16($arg1))):u32 s_dev_inode=+16(+40(+32(+16($arg1)))):u32 i_mode=+0(+32(+16($arg1))):u16 kuid=+4(+32(+16($arg1))):u32 kgid=+8(+32(+16($arg1))):u32 pathname=+0(+40(+24(+16($arg1)))):string' >> /sys/kernel/tracing/kprobe_events
echo 'p:kprobes/unix_dgram_recvmsg unix_dgram_recvmsg sock=$arg1 msg=$arg2 len=$arg3 inode=+64(+32(+16($arg1))):u64 k__dev=+76(+32(+16($arg1))):u32 s_dev_inode=+16(+40(+32(+16($arg1)))):u32 i_mode=+0(+32(+16($arg1))):u16 kuid=+4(+32(+16($arg1))):u32 kgid=+8(+32(+16($arg1))):u32 pathname=+0(+40(+24(+16($arg1)))):string' >> /sys/kernel/tracing/kprobe_events
echo 'p:kprobes/sock_queue_tail skb_queue_tail sk_receive_queue=$arg1 skb=$arg2 socket=+424($arg1):x64 inode=+64(+32(+16(+424($arg1)))):u64' >> /sys/kernel/tracing/kprobe_events
echo 'r:kprobes/sco_sock_sendmsg sco_sock_sendmsg error=$retval:u32' >> /sys/kernel/tracing/kprobe_events
echo 'r:kprobes/l2cap_sock_sendmsg l2cap_sock_sendmsg error=$retval:u32' >> /sys/kernel/tracing/kprobe_events
echo 'r:kprobes/hci_sock_sendmsg hci_sock_sendmsg error=$retval:u32' >> /sys/kernel/tracing/kprobe_events
echo 'r:kprobes/sock_sendmsg sock_sendmsg num=$retval:u32' >> /sys/kernel/tracing/kprobe_events
# Pixel-specific kprobe for AoC sensors
echo 'p:kprobes/aoc_service_write_message aoc_service_write_message service=$arg1 base=$arg2 dir=$arg3 size=$arg5 channel=+0($arg4):x32 sensor=+0($arg4):x32[36]' >> /sys/kernel/tracing/kprobe_events
# Start reading from the trace pipe in the background
cat /sys/kernel/tracing/trace_pipe > /data/local/tmp/trace.trace &
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
# Print the final PID string
#
# Clear filters and then add rules to filters
#
# echo "($pid_string)" > /sys/kernel/tracing/events/raw_syscalls/filter
echo "($pid_string)" > /sys/kernel/tracing/events/binder/filter
echo "($pid_string)" > /sys/kernel/tracing/events/kprobes/write_probe/filter
echo "($pid_string)" > /sys/kernel/tracing/events/kprobes/read_probe/filter
echo "($pid_string)" > /sys/kernel/tracing/events/kprobes/ioctl_probe/filter
echo "($pid_string)" > /sys/kernel/tracing/events/sock/inet_sock_set_state/filter
echo "($pid_string)" > /sys/kernel/tracing/events/kprobes/unix_dgram_sendmsg/filter
echo "($pid_string)" > /sys/kernel/tracing/events/kprobes/unix_dgram_recvmsg/filter
echo "($pid_string)" > /sys/kernel/tracing/events/kprobes/unix_stream_sendmsg/filter
echo "($pid_string)" > /sys/kernel/tracing/events/kprobes/unix_stream_recvmsg/filter
echo "($pid_string)" > /sys/kernel/tracing/events/kprobes/sock_queue_tail/filter
echo "($pid_string)" > /sys/kernel/tracing/events/kprobes/hci_sock_sendmsg/filter
echo "($pid_string)" > /sys/kernel/tracing/events/kprobes/sco_sock_sendmsg/filter
echo "($pid_string)" > /sys/kernel/tracing/events/kprobes/l2cap_sock_sendmsg/filter
echo "($pid_string)" > /sys/kernel/tracing/events/kprobes/sock_sendmsg/filter

# Add Pixel-specific filter for AoC sensors
echo "size == 0x90 || size == 0x5c || size == 0x40" > /sys/kernel/tracing/events/kprobes/aoc_service_write_message/filter

# Enable tracing raw system calls entry and exit points
#echo 0 > /sys/kernel/tracing/events/raw_syscalls/sys_enter/enable
#echo 0 > /sys/kernel/tracing/events/raw_syscalls/sys_exit/enable
# Enable kprobe events
echo 1 > /sys/kernel/tracing/events/kprobes/write_probe/enable
echo 1 > /sys/kernel/tracing/events/kprobes/read_probe/enable
echo 1 > /sys/kernel/tracing/events/kprobes/ioctl_probe/enable
echo 1 > /sys/kernel/tracing/events/kprobes/unix_dgram_sendmsg/enable
echo 1 > /sys/kernel/tracing/events/kprobes/unix_dgram_recvmsg/enable
echo 1 > /sys/kernel/tracing/events/kprobes/unix_stream_sendmsg/enable
echo 1 > /sys/kernel/tracing/events/kprobes/unix_stream_recvmsg/enable
echo 1 > /sys/kernel/tracing/events/kprobes/sock_queue_tail/enable
# Enable binder tracepoints
echo 1 > /sys/kernel/tracing/events/binder/binder_transaction/enable
echo 1 > /sys/kernel/tracing/events/binder/binder_transaction_received/enable
# Enable inet socket state transition tracing
echo 1 > /sys/kernel/tracing/events/sock/inet_sock_set_state/enable
# Enable Bluetooth sockets
echo 1 > /sys/kernel/tracing/events/kprobes/hci_sock_sendmsg/enable
echo 1 > /sys/kernel/tracing/events/kprobes/sco_sock_sendmsg/enable
echo 1 > /sys/kernel/tracing/events/kprobes/l2cap_sock_sendmsg/enable
# Added network sockets
echo 1 > /sys/kernel/tracing/events/kprobes/sock_sendmsg/enable
# Enable Pixel-specific AoC sensor identification
echo 1 > /sys/kernel/tracing/events/kprobes/aoc_service_write_message/enable

# Start Tracing
echo 1 > /sys/kernel/tracing/tracing_on

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
