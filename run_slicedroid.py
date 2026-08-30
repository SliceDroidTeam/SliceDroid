#!/usr/bin/env python3
"""
SliceDroid entry point.

Subcommands:
    trace       Capture an ftrace + tcpdump session from a connected device.
    dashboard   Launch the web dashboard (webapp/app.py) and open a browser.
    setup       One-time device setup: app mapping + resource resolution.

Running with no arguments starts the interactive menu.
"""

import argparse
import gzip
import json
import os
import re
import shutil
import subprocess
import sys
import time
import urllib.request
import webbrowser
import zipfile

try:
    import colorama
except ImportError:  # colorama is optional: fall back to uncolored output
    class _NoColor:
        def __getattr__(self, _name):
            return ""

    class _ColoramaStub:
        Fore = _NoColor()
        Style = _NoColor()

        @staticmethod
        def init(*args, **kwargs):
            pass

    colorama = _ColoramaStub()

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))

TRACER_SCRIPT = os.path.join(PROJECT_ROOT, "scripts", "tracer", "cleaned_trace_sock.sh")
TRACER_CONFIG_DIR = os.path.join(PROJECT_ROOT, "scripts", "tracer", "config_files")
CORRELATOR_SCRIPT = os.path.join(PROJECT_ROOT, "scripts", "correlation", "trace_pcap_correlator.py")
UDP_UPDATER_SCRIPT = os.path.join(PROJECT_ROOT, "scripts", "correlation", "update_udp_events.py")
APP_MAPPER_SCRIPT = os.path.join(PROJECT_ROOT, "scripts", "tracker", "app_mapper.py")
STDEV_SCRIPT = os.path.join(PROJECT_ROOT, "scripts", "resources_resolver", "run_stdev_rdev_trace.py")
DASHBOARD_SCRIPT = os.path.join(PROJECT_ROOT, "webapp", "app.py")

DATA_DIR = os.path.join(PROJECT_ROOT, "data")
TRACES_DIR = os.path.join(DATA_DIR, "traces")

DEVICE_SCRIPT_PATH = "/data/local/tmp/cleaned_trace_sock.sh"
DEVICE_CONFIG_DIR = "/data/local/tmp/config_files"
DEVICE_TRACE_GZ = "/data/local/tmp/trace.trace.gz"
DEVICE_PCAP_GZ = "/data/local/tmp/tcpdump.pcap.gz"

LOCAL_TRACE_GZ = os.path.join(TRACES_DIR, "trace.trace.gz")
LOCAL_TRACE = os.path.join(TRACES_DIR, "trace.trace")
LOCAL_PCAP_GZ = os.path.join(TRACES_DIR, "tcpdump.pcap.gz")
LOCAL_CORRELATIONS = os.path.join(TRACES_DIR, "correlations.csv")
LOCAL_TRACE_CORRECTED = os.path.join(TRACES_DIR, "trace_corrected.trace")


# ---------------------------------------------------------------------------
# ADB helpers
# ---------------------------------------------------------------------------

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
        print(f"[*] Downloading from {download_url}...")
        urllib.request.urlretrieve(download_url, zip_filename)

        print("[*] Extracting platform tools...")
        with zipfile.ZipFile(zip_filename, 'r') as zip_ref:
            zip_ref.extractall()

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
        return setup_adb_path(platform_tools_dir)

    # Download and setup ADB
    platform_tools_dir = download_and_setup_adb()
    adb_path = setup_adb_path(platform_tools_dir)

    # Verify installation
    result = subprocess.run([adb_path, "version"], capture_output=True, text=True)
    if result.returncode != 0:
        raise Exception("ADB installation verification failed")
    print("[*] ADB successfully installed and verified")
    print(f"[*] ADB Version: {result.stdout.strip()}")
    return adb_path


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


def require_device(adb_command):
    """Ensure at least one device is connected; prompt once for a retry."""
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

        input("[*] Connect your device and press Enter to continue...")

        is_connected, devices = check_device_connection(adb_command)
        if not is_connected:
            print("[!] Still no devices found. Exiting...")
            sys.exit(1)

    print(f"[*] Found {len(devices)} connected device(s):")
    for device in devices:
        print(f"    - {device}")
    return devices


# ---------------------------------------------------------------------------
# Setup flow (app mapping + resource resolution)
# ---------------------------------------------------------------------------

def should_create_app_mapping():
    """Check if app_mapping.json is missing or empty"""
    app_mapping_file = os.path.join(DATA_DIR, "app_mapping.json")

    if not os.path.exists(app_mapping_file):
        return True

    try:
        with open(app_mapping_file, 'r', encoding='utf-8') as f:
            content = f.read().strip()
            if not content or content == '{}' or content == '[]':
                return True

        with open(app_mapping_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
            if not data or len(data) == 0:
                return True

    except (json.JSONDecodeError, Exception):
        # File is corrupted, needs recreation
        return True

    return False


def run_setup():
    """Create the app mapping and resolve device resources (st_dev/r_dev)."""
    adb_command = ensure_adb_available()
    require_device(adb_command)

    # Create app mapping from connected device if needed
    if should_create_app_mapping():
        print("[*] App mapping is missing or empty - creating from connected device...")
        if os.path.exists(APP_MAPPER_SCRIPT):
            try:
                print("[*] Analyzing installed apps to extract commercial names...")
                output_path = os.path.join(DATA_DIR, "app_mapping.json")
                os.makedirs(DATA_DIR, exist_ok=True)
                subprocess.run([
                    sys.executable, APP_MAPPER_SCRIPT,
                    "--create",
                    "--output", output_path,
                    "--limit", "50",
                    "--include-system"
                ], check=True, timeout=500, cwd=PROJECT_ROOT)
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

    # Check if rdevs.txt and regular_files.txt exist to skip the script
    mapping_dir = os.path.join(DATA_DIR, "mappings")
    skip_rdev = False
    if os.path.isdir(mapping_dir):
        rdevs_file = os.path.join(mapping_dir, "rdevs.txt")
        regularfiles_file = os.path.join(mapping_dir, "regular_files.txt")

        if os.path.exists(rdevs_file) and os.path.exists(regularfiles_file):
            print("[*] Found existing rdevs.txt and regular_files.txt, skipping resource resolution script...")
            skip_rdev = True
        else:
            for filename in os.listdir(mapping_dir):
                if re.match(r"cat2devs.txt", filename):
                    skip_rdev = True
                    break

    if not skip_rdev:
        # Collect st_devs and r_devs
        subprocess.run([sys.executable, STDEV_SCRIPT], check=True,
                       stderr=subprocess.STDOUT, cwd=PROJECT_ROOT)
    else:
        print("[*] Resource resolution artefacts already present - skipping")

    print("[*] Setup completed.")


# ---------------------------------------------------------------------------
# Trace flow
# ---------------------------------------------------------------------------

def push_tracer_to_device(adb_command):
    """Push the tracer script and its config files to the device."""
    print("[*] Pushing tracing script to device...")
    subprocess.run(
        [adb_command, "push", TRACER_SCRIPT, DEVICE_SCRIPT_PATH],
        check=True
    )

    print("[*] Making tracing script executable...")
    subprocess.run(
        [adb_command, "shell", "chmod", "+x", DEVICE_SCRIPT_PATH],
        check=True
    )

    print("[*] Converting script to Unix format...")
    subprocess.run(
        [adb_command, "shell", "su", "-c", f"dos2unix {DEVICE_SCRIPT_PATH}"],
        check=True
    )

    print("[*] Pushing config files to device...")
    subprocess.run(
        [adb_command, "shell", "su", "-c", f"mkdir -p {DEVICE_CONFIG_DIR}"],
        check=True
    )
    subprocess.run(
        [adb_command, "push", TRACER_CONFIG_DIR, "/data/local/tmp/"],
        check=True
    )

    print("[*] Converting configuration files to Unix format...")
    subprocess.run(
        [
            adb_command, "shell", "su", "-c",
            f"cd {DEVICE_CONFIG_DIR} && "
            f"find {DEVICE_CONFIG_DIR} -type f | while IFS= read -r f; do "
            "dos2unix \"$f\"; "
            "done"
        ],
        check=True
    )


def clean_previous_artifacts(adb_command):
    """Remove stale trace/pcap artefacts locally and on the device."""
    os.makedirs(TRACES_DIR, exist_ok=True)

    for stale in [LOCAL_TRACE, LOCAL_TRACE_GZ, LOCAL_PCAP_GZ,
                  LOCAL_CORRELATIONS, LOCAL_TRACE_CORRECTED]:
        if os.path.exists(stale):
            os.remove(stale)

    subprocess.run(
        [adb_command, "shell", "su", "-c",
         "rm -f /data/local/tmp/trace.trace* /data/local/tmp/tcpdump.pcap*"],
        check=False  # Don't fail if files don't exist
    )


def run_correlation():
    """Run the trace/pcap correlator and the UDP event rewriter."""
    print("[*] Correlating trace with tcpdump capture...")
    result = subprocess.run([
        sys.executable, CORRELATOR_SCRIPT,
        "--trace", LOCAL_TRACE,
        "--pcap", LOCAL_PCAP_GZ,
        "--output", LOCAL_CORRELATIONS,
    ], cwd=PROJECT_ROOT)
    if result.returncode != 0:
        print("[!] Correlation failed (is scapy installed? pip install scapy)")
        return False

    print("[*] Rewriting UDP events with correlated addresses...")
    result = subprocess.run([
        sys.executable, UDP_UPDATER_SCRIPT,
        "--trace", LOCAL_TRACE,
        "--correlations", LOCAL_CORRELATIONS,
        "--output", LOCAL_TRACE_CORRECTED,
    ], cwd=PROJECT_ROOT)
    if result.returncode != 0:
        print("[!] UDP event rewrite failed")
        return False

    print(f"[*] Corrected trace available at {LOCAL_TRACE_CORRECTED}")
    return True


def run_trace(correlate=False, skip_pcap=False):
    """Full tracing workflow: push tracer, run it, pull and unpack artefacts."""
    adb_command = ensure_adb_available()
    require_device(adb_command)

    push_tracer_to_device(adb_command)

    print("Setting selinux permissive mode. Don't forget to set it back to enforcing after tracing!")
    subprocess.run(
        [adb_command, "shell", "su", "-c", "setenforce 0"],
        check=True
    )

    clean_previous_artifacts(adb_command)

    # Start the tracing script as a subprocess that we can control
    print("[*] Initializing system call tracer...")
    print("[*] Ready to capture system activity. Tracer is now waiting for your commands.")
    trace_process = subprocess.Popen(
        [adb_command, "shell", "su", "-c", DEVICE_SCRIPT_PATH],
        stdin=subprocess.PIPE
    )

    print("\n" + "=" * 70)
    print("[*] TRACING ACTIVE - Use your Android device now!")
    print("[*] Perform the actions you want to analyze...")
    print("[*] Press ENTER when finished to stop tracing and analyze results")
    print("=" * 70 + "\n")
    input()

    # A newline on the tracer's stdin makes its `read STOP` return
    trace_process.stdin.write(b'\n')
    trace_process.stdin.flush()
    trace_process.wait()

    print("[*] Pulling trace file from device...")
    subprocess.run(
        [adb_command, "pull", DEVICE_TRACE_GZ, LOCAL_TRACE_GZ],
        check=True
    )

    if not skip_pcap:
        print("[*] Pulling tcpdump capture from device...")
        pull_pcap = subprocess.run(
            [adb_command, "pull", DEVICE_PCAP_GZ, LOCAL_PCAP_GZ],
            check=False
        )
        if pull_pcap.returncode != 0:
            print("[!] Could not pull tcpdump capture (was tcpdump available on the device?)")
    else:
        print("[*] Skipping tcpdump capture pull (--skip-pcap)")

    print("[*] Extracting trace file...")
    with gzip.open(LOCAL_TRACE_GZ, "rb") as f_in, open(LOCAL_TRACE, "wb") as f_out:
        shutil.copyfileobj(f_in, f_out)

    print(f"[*] Trace available at {LOCAL_TRACE}")

    if correlate:
        if skip_pcap or not os.path.exists(LOCAL_PCAP_GZ):
            print("[!] Cannot correlate without a tcpdump capture - skipping correlation")
        else:
            run_correlation()


# ---------------------------------------------------------------------------
# Dashboard flow
# ---------------------------------------------------------------------------

def open_dashboard():
    """Open the dashboard in the default browser"""
    if not os.path.exists('/.dockerenv'):
        print("[*] Opening dashboard in browser...")
        webbrowser.open("http://localhost:5000")
    print("Please visit http://localhost:5000 in your browser")


def run_dashboard():
    """Start the web dashboard and open a browser tab."""
    # Make sure the exports directory exists for the webapp
    os.makedirs(os.path.join(DATA_DIR, "Exports"), exist_ok=True)

    print("[*] Starting web dashboard...")
    server_proc = subprocess.Popen(
        [sys.executable, DASHBOARD_SCRIPT],
        stderr=subprocess.STDOUT,
        cwd=PROJECT_ROOT
    )

    # Give Flask a moment to spin up
    time.sleep(5)

    open_dashboard()

    # Wait for the server to exit before letting the script finish
    try:
        server_proc.wait()
    except KeyboardInterrupt:
        print("\n[*] Stopping dashboard...")
        server_proc.terminate()


# ---------------------------------------------------------------------------
# Interactive menu
# ---------------------------------------------------------------------------

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


def check_necessary_files():
    """Check if all necessary files exist for dashboard functionality"""
    status = {
        'app_mapping': os.path.exists(os.path.join(DATA_DIR, "app_mapping.json")),
        'cat2devs': os.path.exists(os.path.join(DATA_DIR, "mappings", "cat2devs.txt")),
        'trace_file': False,
    }

    # Check for any .trace file in traces directory
    if os.path.exists(TRACES_DIR):
        for file in os.listdir(TRACES_DIR):
            if file.endswith('.trace'):
                status['trace_file'] = True
                break

    return status, all(status.values())


def display_menu():
    """Display the main menu and get user choice"""
    file_status, all_files_exist = check_necessary_files()

    print("\n" + "=" * 70)
    print("                           SLICEDROID MENU")
    print("=" * 70)

    # Display file status
    print("\nData Files Status:")
    status_icon = lambda exists: colorama.Fore.GREEN + "OK" + colorama.Style.RESET_ALL if exists else colorama.Fore.RED + "Missing" + colorama.Style.RESET_ALL
    print(f"   {status_icon(file_status['app_mapping'])} App Mapping (app_mapping.json)")
    print(f"   {status_icon(file_status['cat2devs'])} Device Categories (mappings/cat2devs.txt)")
    print(f"   {status_icon(file_status['trace_file'])} Trace File (traces/*.trace)")

    if all_files_exist:
        print(colorama.Fore.GREEN + "All necessary files are available!" + colorama.Style.RESET_ALL)
    else:
        print(colorama.Fore.RED + "Some files are missing" + colorama.Style.RESET_ALL)

    print("\nChoose your action:")
    print("┌─────────────────────────────────────────────────────────────────────┐")
    print("│ 1. Open Dashboard Only                                              │")
    print("│    └─ Use existing data files, start web interface immediately      │")
    print("│                                                                     │")
    print("│ 2. Trace Device + Dashboard                                         │")
    print("│    └─ Capture new trace from device, then start dashboard           │")
    print("│                                                                     │")
    print("│ 3. Full Setup + Trace + Dashboard                                   │")
    print("│    └─ Complete flow: setup, device analysis, trace, dashboard       │")
    print("└─────────────────────────────────────────────────────────────────────┘")

    while True:
        try:
            choice = input("\n👉 Enter your choice (1-3): ").strip()
            if choice in ['1', '2', '3']:
                return int(choice)
            else:
                print("Invalid choice. Please enter 1, 2, or 3.")
        except KeyboardInterrupt:
            print("\n\nGoodbye!")
            sys.exit(0)


def run_interactive():
    """Interactive menu (default when no subcommand is given)."""
    user_choice = display_menu()

    if user_choice == 1:
        run_dashboard()
    elif user_choice == 2:
        print("\n📱 Starting device tracing + dashboard flow...")
        run_trace()
        run_dashboard()
    elif user_choice == 3:
        print("\n🔧 Starting full setup flow...")
        run_setup()
        run_trace()
        run_dashboard()


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def build_parser():
    parser = argparse.ArgumentParser(
        prog="run_slicedroid.py",
        description="SliceDroid - Android Security Analysis Tool",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python run_slicedroid.py                       # Interactive menu
  python run_slicedroid.py trace                 # Capture a trace + pcap
  python run_slicedroid.py trace --correlate     # ... and correlate them
  python run_slicedroid.py trace --skip-pcap     # Trace only, no pcap pull
  python run_slicedroid.py dashboard             # Launch the web dashboard
  python run_slicedroid.py setup                 # Device setup (app mapping, resources)
        """
    )

    subparsers = parser.add_subparsers(dest="command")

    trace_parser = subparsers.add_parser(
        "trace",
        help="Capture an ftrace + tcpdump session from a connected device"
    )
    trace_parser.add_argument(
        "--correlate", action="store_true",
        help="After pulling the artefacts, correlate the trace with the pcap "
             "and produce data/traces/trace_corrected.trace (requires scapy)"
    )
    trace_parser.add_argument(
        "--skip-pcap", action="store_true",
        help="Do not pull the tcpdump capture from the device"
    )

    subparsers.add_parser(
        "dashboard",
        help="Launch the web dashboard and open it in a browser"
    )

    subparsers.add_parser(
        "setup",
        help="One-time device setup: app mapping and resource resolution"
    )

    return parser


def main(argv=None):
    colorama.init()

    parser = build_parser()
    args = parser.parse_args(argv)

    print_banner()

    if args.command == "trace":
        run_trace(correlate=args.correlate, skip_pcap=args.skip_pcap)
    elif args.command == "dashboard":
        run_dashboard()
    elif args.command == "setup":
        run_setup()
    else:
        run_interactive()


if __name__ == "__main__":
    main()
