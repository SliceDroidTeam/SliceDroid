#### **Method 1: USB Connection via Docker USB Passthrough (Linux)**

4. **Connect your Android device via USB** and enable USB Debugging

5. **Run Docker container with USB access:**
   
   **Option A: Temporary data (lost when container stops)**
   ```bash
   docker run -it --privileged -v /dev/bus/usb:/dev/bus/usb -p 5000:5000 slicedroid
   ```
   
   **Option B: Persistent data with volume (recommended)**
   ```bash
   docker volume create slicedroid-data
   docker run -it --privileged -v /dev/bus/usb:/dev/bus/usb -v slicedroid-data:/app/data -p 5000:5000 slicedroid
   ```

6. **Inside the container, run SliceDroid:**
   ```bash
   python3 run_slicedroid.py
   ```

#### **Method 2: USB Connection via Wireless ADB (Windows/macOS)**

4. **Connect your Android device via USB** and enable USB Debugging

5. **Enable Wireless Debugging on your Android device** (Android 11+)
   - Go to **Settings** → **Developer Options** → **Wireless debugging**
   - Turn on **Wireless debugging**
   - Tap **Pair device with pairing code**
   - Note the **IP address**, **pairing port** (e.g., 37029), and **pairing code**

6. **Connect to the device over ADB:**
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
   adb shell ip route | grep wlan
   # Disconnect USB and connect wirelessly
   adb connect <device-ip>:5555
   ```
   
   **Port clarification:**
   - **Pairing port** (e.g., 37029): Used once for authentication only
   - **Data port** (5555): Used for all subsequent ADB connections
   - **You only need to pair once** — future connections can use `adb connect` directly

7. **Run Docker container (no USB mounting needed):**
   
   **Option A: Temporary data**
   ```bash
   docker run -it --network host -p 5000:5000 slicedroid
   ```
   
   **Option B: Persistent data with volume (recommended)**
   ```bash
   docker volume create slicedroid-data
   docker run -it -v slicedroid-data:/app/data -p 5000:5000 slicedroid
   ```

8. **Inside the container, connect and run SliceDroid:**
   ```bash
   adb connect <device-ip>:<adb-port>
   python3 run_slicedroid.py
   ```