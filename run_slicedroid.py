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
║                     🤖 Android System Call Tracer 🔍                      ║
║                          Dynamic Analysis Tool                             ║
╚════════════════════════════════════════════════════════════════════════════╝
"""
    print(banner)

print_banner()
print("[*] Starting SYSDROID SliceDroid...")

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

# if file exists in /data/mappings, then skip the rdevs
mapping_dir = "data/mappings"
skip_rdev = True
if os.path.isdir(mapping_dir):
    for filename in os.listdir(mapping_dir):
        if re.match(r"cat2devs.txt", filename):
            found = False
            break

if skip_rdev:
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

# Start the tracing script as a subprocess that we can control
print("[*] Starting trace script on device...")
trace_process = subprocess.Popen(
    [adb_command, "shell", "su", "-c", "/data/local/tmp/cleaned_trace_sock.sh"],
    stdin=subprocess.PIPE
)

print("Press a key when you want to stop the trace...")
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

# ---------------------
# Detect and run with venv's python if available
# ---------------------

venv_python = None

# Look for any directory whose name contains "venv"
for name in os.listdir("."):
    if os.path.isdir(name) and "venv" in name.lower():
        # On Windows, the venv python is in Scripts/python.exe
        if sys.platform.startswith("win"):
            candidate = os.path.join(name, "Scripts", "python.exe")
        else:
            # On Linux/macOS, it's in bin/python
            candidate = os.path.join(name, "bin", "python")
        if os.path.isfile(candidate):
            venv_python = candidate
            break

dashboard = os.path.join("webapp", "app.py")

print("[*] Starting web dashboard...")
# Start the Flask app as a background process:
server_proc = subprocess.Popen(
    [venv_python or "python", dashboard],
    stderr=subprocess.STDOUT
)

# Give Flask a second to spin up
time.sleep(5)

# Open the dashboard in the default browser
print("[*] Opening dashboard in browser...")
webbrowser.open("http://127.0.0.1:5000")

# Wait for the server to exit before letting the script finish
server_proc.wait()