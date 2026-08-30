# 🐳 Docker Setup Guide

This guide provides detailed instructions for running SliceDroid inside a Docker container with different connection methods depending on your operating system.

## Prerequisites

Before starting, ensure you have:

1. **Installed Docker** (https://docs.docker.com/engine/install/)
2. **Git** installed for cloning the repository
3. **Android device** (only if you want to capture new traces)

---

## 🚀 **Step-by-Step Instructions: Running SliceDroid (No Host ADB Required)**

### **Method A: Full Tracing with Wireless ADB (Device Required)**

Complete workflow from device tracing to analysis.

**Step 1: Prepare Android Device**
```
1. Enable Developer Options on your Android device
2. Enable USB Debugging
3. Enable Wireless Debugging (Android 11+)
   - Settings → Developer Options → Wireless debugging
   - Turn ON "Wireless debugging"
   - Tap "Pair device with pairing code"
   - Note the IP address, pairing port, and pairing code
```

**Step 2: Clone and Build**

**Windows:**
```powershell
git clone https://github.com/SliceDroidTeam/SLICEDROID_APP
cd SLICEDROID_APP
docker build -t slicedroid .
```

**Linux/macOS:**
```bash
git clone https://github.com/SliceDroidTeam/SLICEDROID_APP
cd SLICEDROID_APP
docker build -t slicedroid .
```

**Step 3: Create Data Directory**

**Windows:**
```powershell
mkdir C:\slicedroid-data
```

**Linux/macOS:**
```bash
mkdir ~/slicedroid-data
```

**Step 4: Run Container with Network Access**

The device-tracing flow needs an interactive shell so you can run `adb connect`
first, so start the container with a `bash` override:

**Windows:**
```powershell
# Run container with a shell for the ADB + tracing workflow
docker run -it -v C:\slicedroid-data:/app/data -p 5000:5000 slicedroid bash
```

**Linux/macOS:**
```bash
# Run container with a shell for the ADB + tracing workflow
docker run -it -v ~/slicedroid-data:/app/data -p 5000:5000 slicedroid bash

# Alternative with host networking (Linux only):
docker run -it -v ~/slicedroid-data:/app/data --network host slicedroid bash
```

**Step 5: Connect Device Inside Container**
```bash
# Inside the container, connect to your device
# First, pair with the device (one-time only):
adb pair <device-ip>:<pairing-port>
# Enter the pairing code when prompted

# Then connect for data transfer:
adb connect <device-ip>:<connect-port>

# Verify connection:
adb devices
```

**Step 6: Run SliceDroid**
```bash
# Inside the container shell:
python3 run_slicedroid.py

# Choose option 2: "Trace Device + Dashboard"
# Follow the prompts to select apps and start tracing
# (or run:  python3 run_slicedroid.py trace  directly)
```

**Step 7: Access Dashboard**
- Open browser: `http://localhost:5000`
- Monitor live tracing or analyze completed traces

---

### **Method B: Using Pre-existing Traces**

Analyze traces you already have from previous sessions.

**Step 1: Prepare Existing Data**

**Windows:**
```powershell
# Copy your existing trace files to Windows
mkdir C:\slicedroid-data\traces
mkdir C:\slicedroid-data\mappings
mkdir C:\slicedroid-data\Exports

# Copy your files:
# - *.trace files → C:\slicedroid-data\traces\
# - cat2devs.txt → C:\slicedroid-data\mappings\
# - app_mapping.json → C:\slicedroid-data\
```

**Linux/macOS:**
```bash
# Copy your existing trace files
mkdir -p ~/slicedroid-data/traces
mkdir -p ~/slicedroid-data/mappings
mkdir -p ~/slicedroid-data/Exports

# Copy your files:
# - *.trace files → ~/slicedroid-data/traces/
# - cat2devs.txt → ~/slicedroid-data/mappings/
# - app_mapping.json → ~/slicedroid-data/
```

**Step 2: Run Container**

**Windows:**
```powershell
docker run -it -v C:\slicedroid-data:/app/data -p 5000:5000 slicedroid
```

**Linux/macOS:**
```bash
docker run -it -v ~/slicedroid-data:/app/data -p 5000:5000 slicedroid
```

**Step 3: Start Analysis**

The SliceDroid launcher starts automatically when the container runs. At the menu, choose **option 1: "Open Dashboard Only"** (no device needed).

**Step 4: Upload and Analyze**
- Go to `http://localhost:5000`
- Use the upload interface to select your trace files
- Pick the target with the **PID** tab (it lists the processes found in the trace), then **Analyze** — no device connection required

---

## Troubleshooting

### **Common Issues and Solutions**

**If Docker build fails:**

**Windows:**
```powershell
# Try with no cache
docker build --no-cache -t slicedroid .
```

**Linux/macOS:**
```bash
# Try with no cache
docker build --no-cache -t slicedroid .
```

**If port 5000 is busy:**

**Windows:**
```powershell
# Use different port
docker run -it -v C:\slicedroid-data:/app/data -p 5001:5000 slicedroid
# Then access at http://localhost:5001
```

**Linux/macOS:**
```bash
# Use different port
docker run -it -v ~/slicedroid-data:/app/data -p 5001:5000 slicedroid
# Then access at http://localhost:5001
```

**If volume mapping doesn't work:**

**Windows:**
```powershell
# Use absolute paths with forward slashes
docker run -it -v /c/slicedroid-data:/app/data -p 5000:5000 slicedroid

# Or try with double backslashes
docker run -it -v C:\\slicedroid-data:/app/data -p 5000:5000 slicedroid
```

**Linux/macOS:**
```bash
# Use absolute paths
docker run -it -v /home/$USER/slicedroid-data:/app/data -p 5000:5000 slicedroid

# Check permissions
sudo chown -R $USER:$USER ~/slicedroid-data
```

**For wireless ADB connection issues:**
```bash
# Inside container, if connection drops:
adb kill-server
adb start-server
adb connect <device-ip>:5555
```

**Android device connection problems:**
- **Authentication failures**: Ensure you've completed the pairing step with the pairing port first
- **Connection drops**: Android may disable wireless debugging after inactivity. Re-enable and reconnect if needed
- **USB passthrough issues on Windows/macOS**: Use Method B (Wireless ADB) instead

**Container access issues:**

**Windows:**
```powershell
# If you can't access the container shell:
docker exec -it <container-name> /bin/bash

# To see running containers:
docker ps
```

**Linux/macOS:**
```bash
# If you can't access the container shell:
docker exec -it <container-name> /bin/bash

# To see running containers:
docker ps

# If permission issues:
sudo docker exec -it <container-name> /bin/bash
```
