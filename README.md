# 📱 Android Tracing and Analysis Toolkit - SliseDroid App

A modular toolchain for tracing Android kernel events using kprobes, parsing ftrace logs, and analyzing app behavior with advanced visualization. Ideal for dynamic analysis, app auditing, and research.

---

## 🚀 Features

- 🐚 **Shell tracing script** using `kprobes` for I/O, IPC, Bluetooth, Camera, Audio, and TCP events
- 🧠 **Python parser** that extracts structured event data from ftrace logs
- 🌐 **Web app UI** to upload `.trace` files and explore results visually

---

## 🏃 How to run SlideDroid

### Source Installation
Download required packages:
```bash
pip install -r requirements.txt
```
* If you want to run end-to-end example by tracing the android device and inspecting the results:
    ```bash
    python run_slicedroid.py
    ```

* If you want to upload a trace file to be analyzed:
    ```bash
    python app.py
    ```
    Then, in the menu, upload the trace.
---

### Use PyTrim inside a Docker container

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

5. Run docker container:
    ```bash
    docker run --network=host --it slicedroid
    ```

6. Then, you are ready to run slicedroid:
    * If you want to trace your device and run the webapp run:
        ```bash
        python3 run_slicedroid.py
        ```
    * If you want to upload your trace to be analyzed:
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

## 🛠️ Prerequisites
```yaml
- Rooted Android device
- Python 3.8+ and pip
- Optional: adb for device communication
```

---

## 📊 Sample Output
Sample visualizations available in `Figures/` folder after processing traces.

---

## 📄 License
```

```
