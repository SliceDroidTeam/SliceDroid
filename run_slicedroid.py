import subprocess
import gzip
import os
import sys
import webbrowser
import time
import re
import urllib.request
import zipfile
import shutil
import argparse
import json
from pathlib import Path

def check_adb_installed():
    """Check if ADB is available in the system PATH"""
    try:
        result = subprocess.run(["adb", "version"], capture_output=True, text=True)
        return result.returncode == 0
    except FileNotFoundError:
        return False

def download_and_setup_adb():
    """Download and setup ADB platform tools"""
    print("[*] ADB not found. Downloading Android Platform Tools...")

    # Create platform-tools directory in current folder
    platform_tools_dir = os.path.join(os.getcwd(), "platform-tools")

    if os.path.exists(platform_tools_dir):
        print("[*] Platform tools directory already exists, skipping download...")
        return platform_tools_dir

    # Download URL for Windows platform tools
    if sys.platform.startswith("win"):
        download_url = "https://dl.google.com/android/repository/platform-tools-latest-windows.zip"
        zip_filename = "platform-tools-windows.zip"
    elif sys.platform.startswith("linux"):
        download_url = "https://dl.google.com/android/repository/platform-tools-latest-linux.zip"
        zip_filename = "platform-tools-linux.zip"
    elif sys.platform.startswith("darwin"):  # macOS
        download_url = "https://dl.google.com/android/repository/platform-tools-latest-darwin.zip"
        zip_filename = "platform-tools-darwin.zip"
    else:
        raise Exception("Unsupported operating system")

    try:
        # Download the zip file
        print(f"[*] Downloading from {download_url}...")
        urllib.request.urlretrieve(download_url, zip_filename)

        # Extract the zip file
        print("[*] Extracting platform tools...")
        with zipfile.ZipFile(zip_filename, 'r') as zip_ref:
            zip_ref.extractall()

        # Clean up the zip file
        os.remove(zip_filename)

        print(f"[*] Platform tools extracted to: {platform_tools_dir}")
        return platform_tools_dir

    except Exception as e:
        print(f"[!] Error downloading/extracting platform tools: {e}")
        raise

def setup_adb_path(platform_tools_dir):
    """Add platform tools to PATH for current session"""
    if sys.platform.startswith("win"):
        adb_path = os.path.join(platform_tools_dir, "adb.exe")
    else:
        adb_path = os.path.join(platform_tools_dir, "adb")

    # Add to PATH for current session
    current_path = os.environ.get("PATH", "")
    if platform_tools_dir not in current_path:
        os.environ["PATH"] = platform_tools_dir + os.pathsep + current_path

    return adb_path

def ensure_adb_available():
    """Ensure ADB is available, download if necessary"""
    if check_adb_installed():
        print("[*] ADB is already installed and available")
        return "adb"

    print("[!] ADB not found in system PATH")

    # Try to find local platform-tools
    platform_tools_dir = os.path.join(os.getcwd(), "platform-tools")
    if os.path.exists(platform_tools_dir):
        print("[*] Found local platform-tools directory")
        adb_path = setup_adb_path(platform_tools_dir)
        return adb_path

    # Download and setup ADB
    platform_tools_dir = download_and_setup_adb()
    adb_path = setup_adb_path(platform_tools_dir)

    # Verify installation
    try:
        result = subprocess.run([adb_path, "version"], capture_output=True, text=True)
        if result.returncode == 0:
            print("[*] ADB successfully installed and verified")
            print(f"[*] ADB Version: {result.stdout.strip()}")
            return adb_path
        else:
            raise Exception("ADB installation verification failed")
    except Exception as e:
        print(f"[!] Error verifying ADB installation: {e}")
        raise

def check_device_connection(adb_command):
    """Check if any devices are connected"""
    try:
        result = subprocess.run([adb_command, "devices"], capture_output=True, text=True)
        if result.returncode == 0:
            lines = result.stdout.strip().split('\n')[1:]  # Skip header
            devices = [line for line in lines if line.strip() and '\tdevice' in line]
            return len(devices) > 0, devices
        return False, []
    except Exception as e:
        print(f"[!] Error checking device connection: {e}")
        return False, []

def should_create_app_mapping():
    """Check if app_mapping.json is missing or empty"""
    app_mapping_file = os.path.join("data", "app_mapping.json")
    
    # File doesn't exist
    if not os.path.exists(app_mapping_file):
        return True
    
    # File exists but is empty or contains empty JSON
    try:
        with open(app_mapping_file, 'r', encoding='utf-8') as f:
            content = f.read().strip()
            if not content or content == '{}' or content == '[]':
                return True
        
        # Try to parse JSON and check if it has meaningful content
        with open(app_mapping_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
            if not data or len(data) == 0:
                return True
                
    except (json.JSONDecodeError, Exception):
        # File is corrupted, needs recreation
        return True
    
    return False

# Main script starts here
def print_banner():
    """Print ASCII art banner"""
    banner = """
╔════════════════════════════════════════════════════════════════════════════╗
║   ███████╗██╗     ██╗ ██████╗███████╗██████╗ ██████╗  ██████╗ ██╗██████╗   ║
║   ██╔════╝██║     ██║██╔════╝██╔════╝██╔══██╗██╔══██╗██╔═══██╗██║██╔══██╗  ║
║   ███████╗██║     ██║██║     █████╗  ██║  ██║██████╔╝██║   ██║██║██║  ██║  ║
║   ╚════██║██║     ██║██║     ██╔══╝  ██║  ██║██╔══██╗██║   ██║██║██║  ██║  ║
║   ███████║███████╗██║╚██████╗███████╗██████╔╝██║  ██║╚██████╔╝██║██████╔╝  ║
║   ╚══════╝╚══════╝╚═╝ ╚═════╝╚══════╝╚═════╝ ╚═╝  ╚═╝ ╚═════╝ ╚═╝╚═════╝   ║
║                                                                            ║
║                     Android System Call Tracer                             ║
║                          Dynamic Analysis Tool                             ║
╚════════════════════════════════════════════════════════════════════════════╝
"""
    print(banner)

print_banner()
print("[*] Starting SliceDroid...")

# Ensure ADB is available
try:
    adb_command = ensure_adb_available()
except Exception as e:
    print(f"[!] Failed to setup ADB: {e}")
    print("[!] Please install ADB manually or check your internet connection")
    sys.exit(1)

# Check device connection
print("[*] Checking device connection...")
is_connected, devices = check_device_connection(adb_command)

if not is_connected:
    print("[!] No Android devices found!")
    print("[*] Please ensure:")
    print("    1. Your device is connected via USB")
    print("    2. USB Debugging is enabled")
    print("    3. You've authorized this computer on your device")
    print("    4. You're using a data cable (not just charging cable)")
    print("\n[*] Run 'adb devices' to check connection status")

    # Give user a chance to connect device
    input("[*] Connect your device and press Enter to continue...")

    is_connected, devices = check_device_connection(adb_command)
    if not is_connected:
        print("[!] Still no devices found. Exiting...")
        sys.exit(1)

print(f"[*] Found {len(devices)} connected device(s):")
for device in devices:
    print(f"    - {device}")

# Create app mapping from connected device if needed
if should_create_app_mapping():
    print("[*] App mapping is missing or empty - creating from connected device...")
    app_mapper_script = os.path.join("scripts", "tracker", "app_mapper.py")
    if os.path.exists(app_mapper_script):
        try:
            print("[*] Analyzing installed apps to extract commercial names...")
            output_path = os.path.join("data", "app_mapping.json")
            # Ensure data directory exists
            os.makedirs("data", exist_ok=True)
            subprocess.run([
                sys.executable, app_mapper_script,
                "--create", 
                "--output", output_path,
                "--limit", "50",
                "--include-system"
            ], check=True, timeout=500, cwd=os.getcwd())
            print("[*] App mapping completed successfully")
        except subprocess.TimeoutExpired:
            print("[!] App mapping timed out, continuing without app mapping...")
        except subprocess.CalledProcessError as e:
            print(f"[!] App mapping failed: {e}, continuing without app mapping...")
        except Exception as e:
            print(f"[!] App mapping error: {e}, continuing without app mapping...")
    else:
        print("[!] App mapper script not found, skipping app mapping...")
else:
    print("[*] App mapping already exists and contains data - skipping creation")

# Check if rdevs.txt and regularfiles.txt exist to skip the script
mapping_dir = "data/mappings"
skip_rdev = False
if os.path.isdir(mapping_dir):
    rdevs_file = os.path.join(mapping_dir, "rdevs.txt")
    regularfiles_file = os.path.join(mapping_dir, "regularfiles.txt")
    
    if os.path.exists(rdevs_file) and os.path.exists(regularfiles_file):
        print("[*] Found existing rdevs.txt and regularfiles.txt, skipping resource resolution script...")
        skip_rdev = True
    else:
        for filename in os.listdir(mapping_dir):
            if re.match(r"cat2devs.txt", filename):
                skip_rdev = True
                break

if not skip_rdev:
    # Collect st_devs and r_devs
    stdev_script = os.path.join("scripts", "resources_resolver", "run_stdev_rdev_trace.py")
    subprocess.run(["python", stdev_script], check=True, stderr=subprocess.STDOUT)

# Push tracing script to the device
print("[*] Pushing tracing script to device...")
tracing_script = os.path.join("scripts", "tracer", "cleaned_trace_sock.sh")
subprocess.run(
    [adb_command, "push", tracing_script, "/data/local/tmp/cleaned_trace_sock.sh"],
    check=True
)

# Make the tracing script executable
print("[*] Making tracing script executable...")
subprocess.run(
    [adb_command, "shell", "chmod", "+x", "/data/local/tmp/cleaned_trace_sock.sh"],
    check=True
)

# Convert the tracing script to Unix format
print("[*] Converting script to Unix format...")
subprocess.run(
    [adb_command, "shell", "su", "-c", "dos2unix /data/local/tmp/cleaned_trace_sock.sh"],
    check=True
)

# Push config files to the device
print("[*] Pushing config files to device...")
subprocess.run(
    [adb_command, "push", "scripts/tracer/config_files", "/data/local/tmp/config_files"],
    check=True
)

print("[*] Converting configuration files to Unix format...")
subprocess.run(
    [
        adb_command, "shell", "su", "-c",
        # cd into the folder, find all files, and run dos2unix on each one
        "cd /data/local/tmp/config_files && " 
        "find /data/local/tmp/config_files -type f | while IFS= read -r f; do "
        "dos2unix \"$f\"; "
        "done"
    ],
    check=True
)

print("Setting selinux permissive mode. Don't forget to set it back to enforcing after tracing!")
subprocess.run(
    [adb_command, "shell", "su", "-c", "setenforce 0"],
    check=True
)
# Ensure the data directory exists
os.makedirs(os.path.join("data", "traces"), exist_ok=True)

# Start the tracing script as a subprocess that we can control
print("[*] Initializing system call tracer...")
print("[*] Ready to capture system activity. Tracer is now waiting for your commands.")
trace_process = subprocess.Popen(
    [adb_command, "shell", "su", "-c", "/data/local/tmp/cleaned_trace_sock.sh"],
    stdin=subprocess.PIPE
)

print("\n" + "="*70)
print("[*] TRACING ACTIVE - Use your Android device now!")
print("[*] Perform the actions you want to analyze...")
print("[*] Press ENTER when finished to stop tracing and analyze results")
print("="*70 + "\n")
input()

trace_process.stdin.write(b'\n')
trace_process.stdin.flush()
trace_process.wait()

print("[*] Pulling trace file from device...")
subprocess.run(
    [adb_command, "pull", "/data/local/tmp/trace.trace.gz", "data/traces/trace.trace.gz"],
    check=True
)

print("[*] Extracting trace file...")
with gzip.open("data/traces/trace.trace.gz", "rb") as f_in, \
     open("data/traces/trace.trace", "wb") as f_out:
    f_out.write(f_in.read())

#make sure exports directory exists
exports_dir = os.path.join("data", "Exports")
os.makedirs(exports_dir, exist_ok=True)

dashboard = os.path.join("webapp", "app.py")

print("[*] Starting web dashboard...")
# Start the Flask app as a background process:
server_proc = subprocess.Popen(
    [sys.executable, dashboard],
    stderr=subprocess.STDOUT
)

# Give Flask a second to spin up
time.sleep(5)

# Open the dashboard in the default browser
print("[*] Opening dashboard in browser...")
webbrowser.open("http://0.0.0.0:5000")

# Wait for the server to exit before letting the script finish
server_proc.wait()

# Handle command line arguments
def handle_args():
    """Handle command line arguments"""
    parser = argparse.ArgumentParser(
        description="SliceDroid - Android Security Analysis Tool",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python run_slicedroid.py                    # Run normal SliceDroid analysis
  python run_slicedroid.py --network          # Run network traffic aggregator
  python run_slicedroid.py --network -t 60    # Run network aggregator for 60 seconds
  python run_slicedroid.py --network -i eth0  # Monitor specific interface
        """
    )
    
    parser.add_argument('--network', action='store_true',
                       help='Run network traffic aggregator instead of normal analysis')
    parser.add_argument('-i', '--interface', default='any',
                       help='Network interface to monitor (default: any)')
    parser.add_argument('-t', '--duration', type=int,
                       help='Network capture duration in seconds')
    parser.add_argument('-o', '--output',
                       help='Save network summary to JSON file')
    
    args = parser.parse_args()
    
    # If network flag is set, run network aggregator instead
    if args.network:
        print("\n" + "="*60)
        print("NETWORK TRAFFIC AGGREGATOR MODE")
        print("="*60)
        
        # Build command for network aggregator
        aggregator_script = os.path.join("scripts", "network_aggregator.py")
        cmd = [sys.executable, aggregator_script]
        
        if args.interface:
            cmd.extend(['-i', args.interface])
        if args.duration:
            cmd.extend(['-t', str(args.duration)])
        if args.output:
            cmd.extend(['-o', args.output])
        
        print(f"[*] Running: {' '.join(cmd)}")
        
        try:
            subprocess.run(cmd)
        except KeyboardInterrupt:
            print("\n[*] Network aggregation stopped by user")
        except Exception as e:
            print(f"[!] Error running network aggregator: {e}")
        
        sys.exit(0)

# Check for network flag before running normal flow
if __name__ == "__main__":
    handle_args()
    # Continue with normal execution if no network flag