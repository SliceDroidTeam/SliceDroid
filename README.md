# SliceDroid - Behavioral Analysis of Android Applications

A modular toolchain for tracing Android kernel events with `ftrace`, slicing logs, and analyzing app behavior with integrated visualization. Useful for malware analysis, app auditing, and research.


## Features

- **Shell tracing script** using `kprobes` and `tracepoints` via `ftrace` for I/O events (IPC, Bluetooth, Camera, Audio, TCP)
- **Python parser** that extracts structured event data from ftrace logs and slices them to extract high-level behaviors
- **Web app UI** to upload `.trace` files and explore results visually

## Prerequisites
```yaml
- Rooted Android device with Developer settings enabled
- Python 3.8+ and pip
- adb for device communication if installing from source
- A docker version is also available (see below)
```

## How to run SliceDroid

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

### Docker Installation (Recommended)

For a containerized setup that works across many platforms:

**Follow the setup guide:** [DOCKER.md](docs/DOCKER.md)

## Project Structure
```
├── run_slicedroid.py           # Main orchestrator script
├── webapp/
│   ├── app.py                  # Flask web dashboard
│   ├── .env.example            # Environment configuration template
│   └── src/                    # Web app source code
│       ├── services/           # Analysis services
│       │   ├── advanced_analytics/    # First analysis package
│       │   ├── comprehensive_analyzer/ # Second analysis package
│       │   ├── app_mapper_service.py  # App mapping service
│       │   ├── trace_processor.py     # Trace processing
│       │   └── utils.py               # Utility functions
│       ├── static/             # CSS/JS/assets
│       │   ├── css/            # Stylesheets
│       │   └── js/             # JavaScript files
│       ├── templates/          # HTML templates
│       └── config.py           # Configuration settings
├── scripts/
│   ├── tracer/                 # System call tracing scripts
│   │   ├── cleaned_trace_sock.sh      # Main tracing script
│   │   └── config_files/              # Tracing configuration
│   ├── tracker/                # App mapping utilities
│   │   └── app_mapper.py              # App name mapping
│   ├── resources_resolver/     # Device mapping scripts
│   │   ├── create_cat2_devs.py        # Device categorization
│   │   ├── find_rdev_stdev_inode.sh   # Device discovery
│   │   └── run_stdev_rdev_trace.py    # Device mapping runner
│   └── network_aggregator.py   # Network analysis
├── data/                       # Generated at runtime (device-specific)
│   ├── traces/                 # System call traces
│   ├── mappings/               # Device mappings
│   ├── Exports/                # Analysis exports
│   └── app_mapping.json        # App name mappings
├── docs/                       # Documentation
│   ├── CONTRIBUTING.md         # Contributing guidelines
│   ├── DOCKER.md               # Docker setup guide
│   ├── TRACING.md              # Tracing documentation
│   └── normal-reproduction-low-resolution.jpg # EU funding logo
├── .github/                    # GitHub configuration
├── .dockerignore               # Docker ignore rules
├── .gitignore                  # Git ignore rules
├── Dockerfile                  # Container configuration
├── requirements.txt            # Python dependencies
├── LICENSE                     # Apache 2.0 license
└── README.md                   # Project documentation
```

**Note:** The `data/` directory is created automatically when you run SliceDroid and contains device-specific mappings and traces.
If you want to provide your traces or mappings you can include them in that directory.
You can skip running device-mappings script each time by choosing option 1 or option 2 from the terminal when running `python run_slicedroid.py`.

## Sample Output
Sample visualizations are saved in the `Figures/` directory after processing traces.

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