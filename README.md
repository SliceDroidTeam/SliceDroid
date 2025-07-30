# 📱 Android Tracing and Analysis Toolkit - SliceDroid App

A modular toolchain for tracing Android kernel events using kprobes, parsing ftrace logs, and analyzing app behavior with advanced visualization. Ideal for dynamic analysis, app auditing, and research.

---

## 🚀 Features

- 🐚 **Shell tracing script** using `kprobes` for I/O, IPC, Bluetooth, Camera, Audio, and TCP events
- 🧠 **Python parser** that extracts structured event data from ftrace logs
- 🌐 **Web app UI** to upload `.trace` files and explore results visually

---

## 🛠️ Prerequisites
```yaml
- Rooted Android device with Developer settings enabled
- Python 3.8+ and pip
- adb for device communication if installation if from source
```

---

## 🏃 How to run SlideDroid

### Source Installation
Download required packages:
```bash
pip install -r requirements.txt
```
* If you want to run end-to-end example by tracing the android device and inspecting the results.
Skip steps 1-3 if your device is already connected through adb.


    1. **Pair your Android device (Android 11+):**  
        ```bash
        adb pair <device-ip>:<pairing-port>
        ```
    2. **Enter the pairing code when prompted.**
    3. **Connect to the device over ADB**
        ```bash
        adb connect <device-ip>:<adb-port>
        ```
    4. 
    * If you want to trace your device and run the webapp run:
        ```bash
        python3 run_slicedroid.py
        ```
    * Otherwise, if you want to upload your trace to be analyzed:
        ```bash
        python3 webapp/app.py
        ```
---

### Use SliceDroid inside a Docker container

1. **Install Docker** (https://docs.docker.com/engine/install/)

2. **Clone this repository:**
   ```bash
   git clone https://github.com/SliceDroidTeam/SLICEDROID_APP
   cd SLICEDROID_APP
   ```

3. **Build Docker image:**
   ```bash
   docker build -t slicedroid .
   ```

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

**Note:** The `--privileged` flag and USB volume mounting are required for ADB to access your Android device from within the container. Option B saves device mappings and traces between container runs.


## 📁 Project Structure
```
├── run_slicedroid.py           # Main orchestrator script
├── webapp/
│   ├── app.py                  # Flask web dashboard
│   ├── src/                    # Web app source code
│   │   ├── services/           # Analysis services
│   │   ├── static/             # CSS/JS/assets
│   │   └── templates/          # HTML templates
├── scripts/
│   ├── tracer/                 # System call tracing scripts
│   ├── tracker/                # App mapping utilities
│   ├── resources_resolver/     # Device mapping scripts
│   └── network_aggregator.py   # Network analysis
├── data/                       # Generated at runtime (device-specific)
│   ├── traces/                 # System call traces
│   ├── mappings/               # Device mappings
│   ├── nodes_and_files_data/   # File system mappings
│   ├── Exports/                # Analysis exports
│   └── app_mapping.json        # App name mappings
├── docs/                       # Documentation
├── Dockerfile                  # Container configuration
├── requirements.txt            # Python dependencies
└── README.md                   # Project documentation
```

**Note:** The `data/` directory is created automatically when you run SliceDroid and contains device-specific mappings and traces.

---


## 📊 Sample Output
Sample visualizations available in `Figures/` folder after processing traces.

---

## 📄 License
```

```
