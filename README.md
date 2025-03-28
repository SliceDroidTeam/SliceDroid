# 📱 Android Tracing and Analysis Toolkit - SYSDROID_APP

A modular toolchain for tracing Android kernel events using kprobes, parsing ftrace logs, and analyzing app behavior with advanced visualization. Ideal for dynamic analysis, app auditing, and research.

---

## 🚀 Features

- 🐚 **Shell tracing script** using `kprobes` for I/O, IPC, Bluetooth, Camera, Audio, and TCP events
- 🧠 **Python parser** that extracts structured event data from ftrace logs
- 📊 **Windowed analysis** to track device usage, API behavior, and TCP communication per app
- 🌐 **Web app UI** to upload `.trace` files and explore results visually

---

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
