import subprocess
import os

# === Configuration ===
SCRIPT_LOCAL = os.path.join("resources_resolver","find_rdev_stdev_inode.sh")
SCRIPT_DEVICE = "/data/local/tmp/find_rdev_stdev_inode.sh"
OUTPUT_FILES = ["regular_files.txt", "rdevs.txt"]
DEVICE_OUTPUT_DIR = "/data/local/tmp"
LOCAL_OUTPUT_DIR = os.path.join("data", "nodes_and_files_data")
PYTHON_PROCESSOR = os.path.join("resources_resolver","create_cat2_devs.py")
manufacturer = subprocess.run(["adb", "shell", "getprop", "ro.product.manufacturer"], capture_output=True, text=True).stdout.strip()

# === Prepare Output Directory ===
os.makedirs(LOCAL_OUTPUT_DIR, exist_ok=True)

# === Push Shell Script to Device ===
print("[*] Pushing script to device...")
subprocess.run(["adb", "push", SCRIPT_LOCAL, SCRIPT_DEVICE], check=True)

# === Make Script Executable ===
print("[*] Making script executable...")
subprocess.run(["adb", "shell", "chmod", "+x", SCRIPT_DEVICE], check=True)

# === Convert Script to Unix Format ===
print("[*] Converting script to Unix format...")    
subprocess.run(["adb", "shell", "su", "-c", f"dos2unix {SCRIPT_DEVICE}"], check=True)

# === Execute Script on Device ===
print("[*] Running script on device...")
subprocess.run(["adb", "shell", "su", "-c", f"sh {SCRIPT_DEVICE}"], check=True)

# === Pull Output Files ===
for filename in OUTPUT_FILES:
    local_path = os.path.join(LOCAL_OUTPUT_DIR, filename)
    # Use forward slashes for Android paths, don't use os.path.join
    device_path = f"{DEVICE_OUTPUT_DIR}/{filename}"
    print(f"[*] Pulling {filename} from device...")
    subprocess.run(["adb", "pull", device_path, local_path], check=True)

# === Run Python Processor ===
print("[*] Running Python processor script...")
subprocess.run(["python", PYTHON_PROCESSOR, manufacturer], check=True)

print("[✓] Done.")