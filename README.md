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

1. Install `docker` (https://docs.docker.com/engine/install/)

2. Clone this repository:
      ```bash
      git clone https://github.com/SliceDroidTeam/SLICEDROID_APP
      ```

3. Enter the source code directory:

      ```bash
      cd SLICEDROID_APP
      ```

4.  Build docker image:
    ```bash
    docker build -t slicedroid .
    ```
5. Pair your Android :
    ```bash
    adb pair <device-ip>:<pairing-port>
    ```

6. Enter the pairing code or scan QR code when prompted.

7. Connect to the device over ADB
    ```bash
    adb connect <device-ip>:<adb-port>
    ```

8. Run docker container:
    ```bash
    docker run -it -p 5000:5000 --env "ANDROID_ADB_SERVER_ADDRESS=host.docker.internal"--add-host=host.docker.internal:host-gateway slicedroid
    ```

9. Then, you are one step away from running SliceDroid:
    * If you want to trace your device and run the webapp run:
        ```bash
        python3 run_slicedroid.py
        ```
    * Otherwise, if you want to upload your trace to be analyzed:
        ```bash
        python3 webapp/app.py
        ```


## 📁 Project Structure
```
├── trace_script.sh      # Main shell script for ftrace and kprobe setup
├── myutils.py           # Utility functions (cleaning, slicing, export)
├── webapp/
│   ├── app.py           # Web server backend (Flask/Streamlit/Dash)
│   ├── templates/       # HTML templates (if Flask)
│   └── static/          # CSS/JS/assets
├── Exports/             # Processed CSV/JSON event exports
├── Figures/             # Generated PDF visualizations
├── cat2devs.txt         # Device category mapping
├── README.md            # Project documentation
└── requirements.txt     # Python dependencies
```

---


## 📊 Sample Output
Sample visualizations available in `Figures/` folder after processing traces.

---

## 📄 License
```

```
