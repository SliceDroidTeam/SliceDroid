FROM python:3.11-slim

# Install dependencies and the latest ADB
RUN apt-get update && apt-get install -y \
    wget unzip libusb-1.0-0 adb \
 && wget https://dl.google.com/android/repository/platform-tools-latest-linux.zip \
 && unzip platform-tools-latest-linux.zip \
 && mv platform-tools /opt/platform-tools \
 && ln -s /opt/platform-tools/adb /usr/local/bin/adb \
 && rm platform-tools-latest-linux.zip \
 && apt-get clean

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY scripts/ scripts/
COPY webapp/ webapp/
COPY run_slicedroid.py .

# Create empty data directory structure using explicit paths
RUN mkdir -p data && \
    mkdir -p data/traces && \
    mkdir -p data/mappings && \
    mkdir -p data/nodes_and_files_data && \
    mkdir -p data/Exports

# Create volume for persistent data storage
VOLUME ["/app/data"]

EXPOSE 5000

CMD ["/bin/bash"]