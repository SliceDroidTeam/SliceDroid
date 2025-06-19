#!/usr/bin/env python3
"""
Network Traffic Aggregator Script for SliceDroid
Runs tcpdump and provides aggregated network statistics
"""

import subprocess
import time
import signal
import sys
import json
import os
from collections import defaultdict, Counter
from datetime import datetime
import threading

class NetworkAggregator:
    def __init__(self, interface="any", duration=None):
        self.interface = interface
        self.duration = duration
        self.stats = {
            'total_packets': 0,
            'total_bytes': 0,
            'protocol_stats': defaultdict(lambda: {'packets': 0, 'bytes': 0}),
            'host_stats': defaultdict(lambda: {'packets': 0, 'bytes': 0}),
            'port_stats': defaultdict(lambda: {'packets': 0, 'bytes': 0}),
            'connections': defaultdict(int),
            'start_time': None,
            'end_time': None
        }
        self.tcpdump_process = None
        self.running = False
        
    def signal_handler(self, signum, frame):
        """Handle Ctrl+C gracefully"""
        print("\n[*] Stopping network capture...")
        self.stop_capture()
        self.print_summary()
        sys.exit(0)
        
    def parse_tcpdump_line(self, line):
        """Parse a tcpdump output line and extract statistics"""
        try:
            # Skip empty lines and header lines
            if not line.strip() or line.startswith('tcpdump:') or line.startswith('listening'):
                return
                
            # Basic parsing for common tcpdump formats
            # Example: "12:34:56.789 IP 192.168.1.1.80 > 192.168.1.2.443: tcp 1234"
            parts = line.split()
            if len(parts) < 6:
                return
                
            # Extract timestamp, protocol, source, destination
            timestamp = parts[0]
            protocol = parts[1].lower()
            
            # Look for size information (usually at the end)
            size = 0
            for part in reversed(parts):
                if part.isdigit():
                    size = int(part)
                    break
            
            # Extract source and destination
            if '>' in line:
                src_dst = line.split('>', 1)
                if len(src_dst) == 2:
                    src_part = src_dst[0].split()[-1]  # Last part before '>'
                    dst_part = src_dst[1].split()[0]   # First part after '>'
                    
                    # Extract host information
                    src_host = src_part.split('.')[0] if '.' in src_part else src_part
                    dst_host = dst_part.split('.')[0] if '.' in dst_part else dst_part
                    
                    # Extract port information
                    src_port = src_part.split('.')[-1] if '.' in src_part else 'unknown'
                    dst_port = dst_part.split('.')[-1] if '.' in dst_part else 'unknown'
                    
                    # Update statistics
                    self.stats['total_packets'] += 1
                    self.stats['total_bytes'] += size
                    
                    self.stats['protocol_stats'][protocol]['packets'] += 1
                    self.stats['protocol_stats'][protocol]['bytes'] += size
                    
                    self.stats['host_stats'][src_host]['packets'] += 1
                    self.stats['host_stats'][src_host]['bytes'] += size
                    
                    self.stats['port_stats'][src_port]['packets'] += 1
                    self.stats['port_stats'][src_port]['bytes'] += size
                    
                    # Track connections
                    connection = f"{src_host}:{src_port} -> {dst_host}:{dst_port}"
                    self.stats['connections'][connection] += 1
                    
        except Exception as e:
            # Silently skip parsing errors
            pass
    
    def format_bytes(self, bytes_val):
        """Format bytes in human readable format"""
        if bytes_val >= 1024 * 1024 * 1024:
            return f"{bytes_val / (1024**3):.2f}GB"
        elif bytes_val >= 1024 * 1024:
            return f"{bytes_val / (1024**2):.2f}MB"
        elif bytes_val >= 1024:
            return f"{bytes_val / 1024:.2f}KB"
        else:
            return f"{bytes_val}B"
    
    def print_real_time_stats(self):
        """Print real-time statistics"""
        while self.running:
            os.system('clear' if os.name == 'posix' else 'cls')
            print("=" * 60)
            print("NETWORK TRAFFIC AGGREGATOR - Real-time Stats")
            print("=" * 60)
            print(f"Total Packets: {self.stats['total_packets']}")
            print(f"Total Data: {self.format_bytes(self.stats['total_bytes'])}")
            
            if self.stats['protocol_stats']:
                print("\nTop Protocols:")
                for proto, data in sorted(self.stats['protocol_stats'].items(), 
                                        key=lambda x: x[1]['packets'], reverse=True)[:5]:
                    print(f"  {proto.upper()}: {data['packets']} packets, {self.format_bytes(data['bytes'])}")
            
            if self.stats['host_stats']:
                print("\nTop Hosts:")
                for host, data in sorted(self.stats['host_stats'].items(), 
                                       key=lambda x: x[1]['packets'], reverse=True)[:5]:
                    print(f"  {host}: {data['packets']} packets, {self.format_bytes(data['bytes'])}")
            
            print("\nPress Ctrl+C to stop and view full summary")
            time.sleep(2)
    
    def start_capture(self):
        """Start tcpdump capture"""
        try:
            # Build tcpdump command
            cmd = ['tcpdump', '-i', self.interface, '-n', '-l']
            if self.duration:
                cmd.extend(['-G', str(self.duration), '-W', '1'])
            
            print(f"[*] Starting tcpdump on interface {self.interface}...")
            print(f"[*] Command: {' '.join(cmd)}")
            
            self.stats['start_time'] = datetime.now()
            self.running = True
            
            # Start real-time stats display in a separate thread
            stats_thread = threading.Thread(target=self.print_real_time_stats)
            stats_thread.daemon = True
            stats_thread.start()
            
            # Start tcpdump process
            self.tcpdump_process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1
            )
            
            # Process output line by line
            for line in iter(self.tcpdump_process.stdout.readline, ''):
                if not self.running:
                    break
                self.parse_tcpdump_line(line.strip())
            
        except KeyboardInterrupt:
            self.stop_capture()
        except Exception as e:
            print(f"[!] Error starting tcpdump: {e}")
            print("[!] Make sure you have tcpdump installed and sufficient privileges")
            sys.exit(1)
    
    def stop_capture(self):
        """Stop tcpdump capture"""
        self.running = False
        self.stats['end_time'] = datetime.now()
        
        if self.tcpdump_process:
            self.tcpdump_process.terminate()
            try:
                self.tcpdump_process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.tcpdump_process.kill()
    
    def print_summary(self):
        """Print final summary statistics"""
        os.system('clear' if os.name == 'posix' else 'cls')
        print("=" * 80)
        print("NETWORK TRAFFIC SUMMARY")
        print("=" * 80)
        
        if self.stats['start_time'] and self.stats['end_time']:
            duration = self.stats['end_time'] - self.stats['start_time']
            print(f"Capture Duration: {duration.total_seconds():.2f} seconds")
        
        print(f"Total Packets Captured: {self.stats['total_packets']}")
        print(f"Total Data Volume: {self.format_bytes(self.stats['total_bytes'])}")
        
        if self.stats['total_packets'] > 0:
            avg_packet_size = self.stats['total_bytes'] / self.stats['total_packets']
            print(f"Average Packet Size: {self.format_bytes(avg_packet_size)}")
        
        # Protocol statistics
        if self.stats['protocol_stats']:
            print("\n" + "=" * 40)
            print("PROTOCOL BREAKDOWN")
            print("=" * 40)
            for proto, data in sorted(self.stats['protocol_stats'].items(), 
                                    key=lambda x: x[1]['packets'], reverse=True):
                percentage = (data['packets'] / self.stats['total_packets']) * 100
                print(f"{proto.upper():10} | {data['packets']:8} packets ({percentage:5.1f}%) | {self.format_bytes(data['bytes']):>10}")
        
        # Top hosts
        if self.stats['host_stats']:
            print("\n" + "=" * 40)
            print("TOP 10 HOSTS BY TRAFFIC")
            print("=" * 40)
            for host, data in sorted(self.stats['host_stats'].items(), 
                                   key=lambda x: x[1]['bytes'], reverse=True)[:10]:
                print(f"{host:20} | {data['packets']:8} packets | {self.format_bytes(data['bytes']):>10}")
        
        # Top ports
        if self.stats['port_stats']:
            print("\n" + "=" * 40)
            print("TOP 10 PORTS BY TRAFFIC")
            print("=" * 40)
            for port, data in sorted(self.stats['port_stats'].items(), 
                                   key=lambda x: x[1]['packets'], reverse=True)[:10]:
                print(f"Port {port:10} | {data['packets']:8} packets | {self.format_bytes(data['bytes']):>10}")
        
        # Top connections
        if self.stats['connections']:
            print("\n" + "=" * 50)
            print("TOP 10 CONNECTIONS BY PACKET COUNT")
            print("=" * 50)
            for conn, count in sorted(self.stats['connections'].items(), 
                                    key=lambda x: x[1], reverse=True)[:10]:
                print(f"{conn:40} | {count:8} packets")
    
    def save_summary_json(self, filename):
        """Save summary to JSON file"""
        summary = {
            'start_time': self.stats['start_time'].isoformat() if self.stats['start_time'] else None,
            'end_time': self.stats['end_time'].isoformat() if self.stats['end_time'] else None,
            'total_packets': self.stats['total_packets'],
            'total_bytes': self.stats['total_bytes'],
            'protocol_stats': dict(self.stats['protocol_stats']),
            'host_stats': dict(self.stats['host_stats']),
            'port_stats': dict(self.stats['port_stats']),
            'top_connections': dict(sorted(self.stats['connections'].items(), 
                                         key=lambda x: x[1], reverse=True)[:20])
        }
        
        with open(filename, 'w') as f:
            json.dump(summary, f, indent=2)
        print(f"\n[*] Summary saved to {filename}")

def main():
    parser = argparse.ArgumentParser(
        description="Network Traffic Aggregator for SliceDroid",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    parser.add_argument('-i', '--interface', default='any',
                       help='Network interface to monitor (default: any)')
    parser.add_argument('-t', '--time', type=int,
                       help='Capture duration in seconds')
    parser.add_argument('-o', '--output',
                       help='Save summary to JSON file')
    
    args = parser.parse_args()
    
    aggregator = NetworkAggregator(
        interface=args.interface,
        duration=args.time
    )
    
    # Set up signal handler for graceful shutdown
    signal.signal(signal.SIGINT, aggregator.signal_handler)
    
    try:
        aggregator.start_capture()
        aggregator.print_summary()
        
        if args.output:
            aggregator.save_summary_json(args.output)
            
    except Exception as e:
        print(f"[!] An error occurred: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()