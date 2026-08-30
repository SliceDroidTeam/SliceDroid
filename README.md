# SliceDroid - Behavioral Analysis of Android Applications

A modular toolchain for tracing Android kernel events with `ftrace`, slicing the trace to the behavior of a single app, and exploring the results in a web dashboard. Useful for malware analysis, app auditing, privacy forensics, and research.

## Features

- **On-device tracer** using `kprobes` and `tracepoints` via `ftrace` for file/device I/O, binder and UNIX-socket IPC, Bluetooth, and TCP/UDP — plus a parallel `tcpdump` packet capture
- **Taint-based event slicer** that follows the target app across process boundaries (binder transactions, UNIX stream/datagram sockets) and extracts only the events caused by the app
- **Trace ↔ pcap correlation** that recovers real IP addresses and ports (UDP addresses in ftrace are otherwise unusable) and confirms byte counts against actual packets
- **Sensitive-access detection**: reads of contacts / SMS / calendar / call-log databases and camera / microphone / GNSS / NFC / Bluetooth devices, attributed to the app through IPC
- **Web dashboard** with a per-window behavior timeline, public-peer network accounting (bytes from kretprobe return values), sensitive-access findings, and JSON/CSV export

## Prerequisites
```yaml
- Rooted Android device with Developer settings enabled
- Python 3.9+ and pip
- adb for device communication if installing from source
- Optional: scapy (only for the trace↔pcap correlation step)
- A docker version is also available (see below)
```

## How to run SliceDroid

### Source Installation

**Download required packages:**
```bash
pip install -r requirements.txt
```

* If you want to run the end-to-end example by tracing the android device and inspecting the results,
skip steps 1-3 if your device is already connected through adb.

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

    4. **Run SliceDroid:**
        ```bash
        python3 run_slicedroid.py            # interactive menu
        ```
        or use the subcommands directly:
        ```bash
        python3 run_slicedroid.py setup      # one-time: app mapping + device-category mapping
        python3 run_slicedroid.py trace      # record a trace (+ tcpdump); add --correlate to fix UDP addresses
        python3 run_slicedroid.py dashboard  # start the web dashboard
        ```
    * If you already have a trace and only want to analyze it:
        ```bash
        python3 webapp/app.py
        ```
        then open `http://localhost:5000`, upload the `.trace` file in the dashboard, pick the target app or PID (the **PID** tab lists the processes found in the trace), and press **Analyze**.

        > **macOS note:** port 5000 is used by the AirPlay Receiver. If the dashboard won't load, run on another port with `SLICEDROID_PORT=5001 python3 webapp/app.py` (then use `http://localhost:5001`), or disable *System Settings → General → AirDrop & Handoff → AirPlay Receiver*.

See [docs/TRACING.md](docs/TRACING.md) for the full tracing workflow, including the optional trace↔pcap correlation step.

### Docker Installation (Recommended)

For a containerized setup that works across many platforms:

**Follow the setup guide:** [DOCKER.md](docs/DOCKER.md)

## Project Structure
```
├── run_slicedroid.py           # CLI: setup / trace / dashboard subcommands
├── webapp/
│   ├── app.py                  # Flask API + dashboard
│   └── src/
│       ├── analysis/           # Unified analysis package
│       │   ├── parser.py       #   ftrace log parser
│       │   ├── slicer.py       #   taint-based event slicer (binder + UNIX sockets)
│       │   ├── windows.py      #   sliding-window driver
│       │   ├── devices.py      #   device categorization + sensitive-access detection
│       │   ├── network.py      #   TCP/UDP metrics, per-peer byte accounting
│       │   ├── insights.py     #   plain-language findings
│       │   └── pipeline.py     #   run_analysis() orchestrator
│       ├── services/
│       │   ├── app_mapper_service.py  # App mapping service
│       │   └── utils.py               # Shared utilities
│       ├── static/             # Dashboard CSS/JS (Chart.js, ES modules)
│       ├── templates/          # index.html
│       └── config.py           # Paths & configuration
├── scripts/
│   ├── tracer/                 # On-device ftrace + tcpdump script and configs
│   ├── correlation/            # trace ↔ pcap correlator, UDP address rewrite
│   ├── tracker/                # App-name mapping (androguard)
│   └── resources_resolver/     # Device/category mapping scripts
├── tests/                      # pytest suite + synthetic trace fixture
├── data/                       # Generated at runtime (device-specific)
│   ├── traces/                 # Traces, pcap, correlations
│   ├── mappings/               # cat2devs.txt device categories
│   └── Exports/                # analysis.json, sliced_events.json
└── docs/                       # TRACING.md, DOCKER.md, CONTRIBUTING.md
```

**Note:** The `data/` directory is created automatically when you run SliceDroid and contains device-specific mappings and traces.
If you want to provide your own traces or mappings you can place them in that directory.

## Contributing

We welcome contributions to SliceDroid! Please see our [Contributing Guide](docs/CONTRIBUTING.md).

## License

This project is licensed under the Apache License 2.0 - see the [LICENSE](LICENSE) file for details.

## Initial Contributors

- [@nikalexo](https://github.com/nikalexo) – Research Lead – Initial Codebase
- [@karyotakisg](https://github.com/karyotakisg) – Initial Codebase
- [@foivospro](https://github.com/foivospro) – Initial Codebase
- [@vtalos](https://github.com/vtalos) – Initial Codebase

## Acknowledgements

<img src="docs/normal-reproduction-low-resolution.jpg" alt="" width="100"/>

- Funded by the European Union: The project is a result of the Horizon Europe Project [SPUCS: Software architectures for Secure, Private, User-Controlled Smart devices](https://doi.org/10.3030/101108713) aiming for more transparent and trustworthy personal devices.
