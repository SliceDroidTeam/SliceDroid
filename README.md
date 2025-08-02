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

## 🏃 How to run SliceDroid

### Source Installation

For development or if you prefer running directly on your system:

**Download required packages:**
```bash
pip install -r requirements.txt
```
* If you want to run end-to-end example by tracing the android device and inspecting the results.
Skip steps 1-3 if your device is already connected through adb.

    1. **Enable Wireless Debugging on your Android device (Android 11+):**
       - Go to **Settings** → **Developer Options** → **Wireless debugging**
       - Turn on **Wireless debugging**
       - Tap **Pair device with pairing code**
       - Note the **IP address**, **pairing port**, and **pairing code**
       
    2. **Pair your Android device (first time only):**  
        ```bash
        adb pair <device-ip>:<pairing-port>
        ```
        *Enter the pairing code when prompted*
        
    3. **Connect to the device over ADB (port 5555):**
        ```bash
        adb connect <device-ip>:5555
        ```
        *Note: After initial pairing, you can skip step 2 and connect directly*
        
        **Alternative setup:**
        ```bash
        # Enable TCP mode while connected via USB
        adb tcpip 5555
        # Find device IP address
        adb shell ip route | grep wlan
        # Disconnect USB and connect wirelessly
        adb connect <device-ip>:5555
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

### Docker Installation (Recommended)

For a containerized setup that works across all platforms:

**Follow the detailed setup guide:** [DOCKER.md](DOCKER.md)

---

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

## 🤝 Contributing

We welcome contributions to SliceDroid! Please see our [Contributing Guide](docs/CONTRIBUTING.md) for:

- Development setup instructions
- Code standards and guidelines
- Testing requirements
- Pull request process
- Issue reporting templates

---

## 📄 License

This project is licensed under the Apache License 2.0 - see the [LICENSE](LICENSE) file for details.
