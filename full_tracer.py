from bcc import BPF
import time
import socket
import os
import struct
import subprocess

bpf_text = """
#include <uapi/linux/ptrace.h>
#include <linux/sched.h>
#include <net/sock.h>
#include <linux/inet.h>
#include <linux/udp.h>

struct data_t {
    u32 pid;
    u32 uid;
    char comm[TASK_COMM_LEN];
    char event[16];
};

struct ipv4_data_t {
    u32 pid;
    u32 uid;
    u32 saddr;
    u32 daddr;
    u16 sport;
    u16 dport;
    char comm[TASK_COMM_LEN];
};

BPF_PERF_OUTPUT(events);
BPF_PERF_OUTPUT(ipv4_events);

int trace_generic(struct pt_regs *ctx) {
    struct data_t data = {};
    data.pid = bpf_get_current_pid_tgid() >> 32;
    data.uid = bpf_get_current_uid_gid();
    bpf_get_current_comm(&data.comm, sizeof(data.comm));
    bpf_probe_read_str(&data.event, sizeof(data.event), "GENERIC");
    events.perf_submit(ctx, &data, sizeof(data));
    return 0;
}

int trace_tcp_connect(struct pt_regs *ctx, struct sock *sk) {
    struct ipv4_data_t data = {};
    u16 dport = 0, sport = 0;

    bpf_probe_read(&data.saddr, sizeof(u32), &sk->__sk_common.skc_rcv_saddr);
    bpf_probe_read(&data.daddr, sizeof(u32), &sk->__sk_common.skc_daddr);
    bpf_probe_read(&dport, sizeof(dport), &sk->__sk_common.skc_dport);
    bpf_probe_read(&sport, sizeof(sport), &sk->__sk_common.skc_num);
    data.dport = ntohs(dport);
    data.sport = sport;
    data.pid = bpf_get_current_pid_tgid() >> 32;
    data.uid = bpf_get_current_uid_gid();
    bpf_get_current_comm(&data.comm, sizeof(data.comm));

    ipv4_events.perf_submit(ctx, &data, sizeof(data));
    return 0;
}

int trace_udp_sendmsg(struct pt_regs *ctx, struct sock *sk) {
    u16 dport = 0;
    u32 daddr = 0;
    bpf_probe_read(&dport, sizeof(dport), &sk->__sk_common.skc_dport);
    bpf_probe_read(&daddr, sizeof(daddr), &sk->__sk_common.skc_daddr);
    if (ntohs(dport) == 53) {
        struct data_t data = {};
        data.pid = bpf_get_current_pid_tgid() >> 32;
        data.uid = bpf_get_current_uid_gid();
        bpf_get_current_comm(&data.comm, sizeof(data.comm));
        bpf_probe_read_str(&data.event, sizeof(data.event), "DNS_QUERY");
        events.perf_submit(ctx, &data, sizeof(data));
    }
    return 0;
}
"""

b = BPF(text=bpf_text)

tracepoints = [
    "vfs_read", "vfs_write", "do_sys_open", "do_sys_openat2",
    "sys_socket", "sys_connect", "sys_sendto", "sys_recvfrom", "sys_bind",
    "tcp_connect", "tcp_sendmsg", "tcp_recvmsg", "inet_sock_set_state",
    "binder_transaction", "binder_transaction_received",
    "kmalloc", "kfree", "wake_up_new_task", "do_exit", "schedule",
    "mutex_lock", "mutex_unlock", "sched_switch", "sched_wakeup",
    "cpu_frequency", "irq_handler_entry", "irq_handler_exit",
    "blk_account_io_start", "blk_account_io_done",
    "pm_runtime_get", "pm_runtime_put"
]

for syscall in tracepoints:
    try:
        b.attach_kprobe(event=syscall, fn_name="trace_generic")
    except:
        pass

try:
    b.attach_kprobe(event="tcp_connect", fn_name="trace_tcp_connect")
except:
    pass

try:
    b.attach_kprobe(event="udp_sendmsg", fn_name="trace_udp_sendmsg")
except:
    pass

def detect_foreground(pid):
    try:
        oom_score_adj = open(f"/proc/{pid}/oom_score_adj").read().strip()
        if oom_score_adj == "0":
            return "FG"
        else:
            return "BG"
    except:
        return "?"

def get_package_name(pid):
    try:
        out = subprocess.check_output(["ps", "-p", str(pid), "-o", "cmd="], stderr=subprocess.DEVNULL)
        cmdline = out.decode().strip()
        if "/" in cmdline:
            return os.path.basename(cmdline.split()[0])
        return cmdline
    except:
        return "?"

def print_event(cpu, data, size):
    event = b["events"].event(data)
    pid = event.pid
    uid = event.uid
    comm = event.comm.decode('utf-8', 'replace')
    evt = event.event.decode('utf-8', 'replace')
    fg_bg = detect_foreground(pid)
    pkg = get_package_name(pid)
    print(f"[{time.strftime('%H:%M:%S')}] EVENT={evt} PID={pid} UID={uid} COMM={comm} PKG={pkg} FG/BG={fg_bg}")

def handle_ipv4_event(cpu, data, size):
    event = b["ipv4_events"].event(data)
    saddr = socket.inet_ntoa(struct.pack("I", event.saddr))
    daddr = socket.inet_ntoa(struct.pack("I", event.daddr))
    comm = event.comm.decode('utf-8', 'replace')
    pkg = get_package_name(event.pid)
    print(f"[NET] PID={event.pid} UID={event.uid} COMM={comm} PKG={pkg} {saddr}:{event.sport} -> {daddr}:{event.dport}")

b["events"].open_perf_buffer(print_event)
b["ipv4_events"].open_perf_buffer(handle_ipv4_event)

print("Tracing everything (with network detail, DNS and package tracking)... Press Ctrl-C to stop.")
try:
    while True:
        b.perf_buffer_poll()
except KeyboardInterrupt:
    print("Detaching...")
