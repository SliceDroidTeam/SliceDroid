# 🐳 Docker Setup Guide

This guide provides detailed instructions for running SliceDroid inside a Docker container with different connection methods depending on your operating system.

## Prerequisites

Before starting, ensure you have completed the following from the main README:

1. **Installed Docker** (https://docs.docker.com/engine/install/)
2. **Cloned this repository** and built the Docker image:
   ```bash
   git clone https://github.com/SliceDroidTeam/SLICEDROID_APP
   cd SLICEDROID_APP
   docker build -t slicedroid .
   ```
3. **Enabled Developer Options and USB Debugging** on your Android device

---
## Connection Methods

### **Method 1: USB Connection via Docker USB Passthrough (Linux)**

This method works best on Linux systems where Docker can directly access USB devices.


1. **Connect your Android device via USB** and enable USB Debugging

2. **Run Docker container with USB access:**
   ```bash
   docker run -it --privileged -v /dev/bus/usb:/dev/bus/usb -v <path/to/data/folder>:/app/data -p 5000:5000 slicedroid
   ```

3. **Inside the container, run SliceDroid:**
   ```bash
   python3 run_slicedroid.py
   ```

---

### **Method 2: Wireless ADB Connection (Windows/macOS/Linux)**

This method is recommended for Windows and macOS, or when USB passthrough is not available.

1. **Connect your Android device via USB** and enable USB Debugging

2. **Enable Wireless Debugging on your Android device** (Android 11+)
   - Go to **Settings** → **Developer Options** → **Wireless debugging**
   - Turn on **Wireless debugging**
   - Tap **Pair device with pairing code**
   - Note the **IP address**, **pairing port** (e.g., 37029), and **pairing code**

3. **Pair and connect to the device over ADB:**
   ```bash
   adb connect <device-ip>:5555
   ```
   
   *Note: If this fails with "failed to authenticate", first pair using the pairing port:*
   ```bash
   adb pair <device-ip>:<pairing-port>
   # Enter pairing code when prompted, then retry: adb connect <device-ip>:5555
   ```
   
   **Alternative method:**
   ```bash
   # While connected via USB, enable TCP mode
   adb tcpip 5555
   # Find device IP address
   adb shell ip route
   # Disconnect USB and connect wirelessly
   adb connect <device-ip>:5555
   ```
   
   **Port clarification:**
   - **Pairing port** (e.g., 37029): Used once for authentication only
   - **Data port** (5555): Used for all subsequent ADB connections
   - **You only need to pair once** — future connections can use `adb connect` directly

4. **Run Docker container (no USB mounting needed):**
   ```bash
   docker run -it -v <path/to/data/folder>:/app/data -p 5000:5000 slicedroid
   ```

5. **Inside the container, connect and run SliceDroid:**
   ```bash
   adb connect <device-ip>:5555
   python3 run_slicedroid.py
   ```

---

## Run only the dashboard
If you already have a `data` folder with cat2devs.txt, app_mappings.json and trace files, you can skip adb connection and just use the dashboard.

1. **Run docker container:**
```bash
docker run -it -v <path/to/data/folder>:/app/data -p 5000:5000 slicedroid
```

2. **Run SliceDroid:**
```bash
   python3 run_slicedroid.py
```

---

## Troubleshooting

- **USB passthrough issues on Windows/macOS**: Use Method 2 (Wireless ADB) instead
- **Authentication failures**: Ensure you've completed the pairing step with the pairing port first
- **Connection drops**: Android may disable wireless debugging after inactivity. Re-enable and reconnect if needed
- **Port conflicts**: If port 5000 is in use, change the mapping: `-p 5001:5000` and access at `localhost:5001`