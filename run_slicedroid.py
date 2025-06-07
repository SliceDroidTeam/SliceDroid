import subprocess
import gzip
import os
import sys
import webbrowser
import time
import re

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
    stdev_script = os.path.join("resources_resolver", "run_stdev_rdev_trace.py")
    subprocess.run(["python", stdev_script], check=True, stderr=subprocess.STDOUT)

# Push tracing script to the device
tracing_script = os.path.join("scripts", "cleaned_trace_sock.sh")
subprocess.run(
    ["adb", "push", tracing_script, "/data/local/tmp/cleaned_trace_sock.sh"],
    check=True
)

# Make the tracing script executable
subprocess.run(
    ["adb", "shell", "chmod", "+x", "/data/local/tmp/cleaned_trace_sock.sh"],
    check=True
)

# Convert the tracing script to Unix format
subprocess.run(
    ["adb", "shell", "su", "-c", "dos2unix /data/local/tmp/cleaned_trace_sock.sh"],
    check=True
)

# Push config files to the device
subprocess.run(
    ["adb", "push", "config_files", "/data/local/tmp/config_files"],
    check=True
)

# Start the tracing script as a subprocess that we can control
trace_process = subprocess.Popen(
    ["adb", "shell", "su", "-c", "/data/local/tmp/cleaned_trace_sock.sh"],
    stdin=subprocess.PIPE
)


print("Press a key when you want to stop the trace...")
input()

trace_process.stdin.write(b'\n')
trace_process.stdin.flush()
trace_process.wait()

subprocess.run(
    ["adb", "pull", "/data/local/tmp/trace.trace.gz", "data/traces/trace.trace.gz"],
    check=True
)

with gzip.open("data/traces/trace.trace.gz", "rb") as f_in, \
     open("data/traces/trace.trace", "wb") as f_out:
    f_out.write(f_in.read())

# ---------------------
# Detect and run with venv’s python if available
# ---------------------

venv_python = None

# Look for any directory whose name contains "venv"
for name in os.listdir("."):
    if os.path.isdir(name) and "venv" in name.lower():
        # On Windows, the venv python is in Scripts/python.exe
        if sys.platform.startswith("win"):
            candidate = os.path.join(name, "Scripts", "python.exe")
        else:
            # On Linux/macOS, it’s in bin/python
            candidate = os.path.join(name, "bin", "python")
        if os.path.isfile(candidate):
            venv_python = candidate
            break

dashboard = os.path.join("webapp", "app.py")

# Start the Flask app as a background process:
server_proc = subprocess.Popen(
    [venv_python or "python", dashboard],
    stderr=subprocess.STDOUT
)

# Give Flask a second to spin up
time.sleep(5)

# Open the dashboard in the default browser
webbrowser.open("http://127.0.0.1:5000")

# Wait for the server to exit before letting the script finish
server_proc.wait()