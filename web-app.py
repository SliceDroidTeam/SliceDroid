# app.py
from flask import Flask, render_template, request, jsonify
import os
import json
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib
matplotlib.use('Agg')  # Use non-interactive backend
import numpy as np
import base64
from io import BytesIO
import re

app = Flask(__name__)

# Set data paths
DATA_DIR = 'Exports'
PROCESSED_EVENTS_JSON = os.path.join(DATA_DIR, 'processed_events.json')

# Helper functions
def load_data():
    """Load the processed events from JSON file"""
    if os.path.exists(PROCESSED_EVENTS_JSON):
        with open(PROCESSED_EVENTS_JSON, 'r') as f:
            return json.load(f)
    return []

def get_unique_pids(events):
    """Extract unique PIDs from events"""
    pids = set()
    for event in events:
        if 'tgid' in event:
            pids.add(event['tgid'])
    return sorted(list(pids))

def get_unique_devices(events):
    """Extract unique devices from events"""
    devices = set()
    for event in events:
        if 'details' in event and 'k_dev' in event['details']:
            if event['details']['k_dev'] != 0:
                devices.add(event['details']['k_dev'])
    return sorted(list(devices))

def filter_events(events, pid=None, device=None):
    """Filter events by PID and/or device"""
    filtered = events
    if pid:
        filtered = [e for e in filtered if 'tgid' in e and e['tgid'] == int(pid)]
    if device:
        filtered = [e for e in filtered if 'details' in e and 'k_dev' in e['details']
                   and e['details']['k_dev'] == int(device)]
    return filtered

def create_timeline_data(events):
    """Create timeline data for visualization"""
    timeline_data = []
    for idx, event in enumerate(events):
        event_type = event.get('event', 'unknown')

        # Determine category based on event type
        category = 'other'
        if 'read' in event_type:
            category = 'read'
        elif 'write' in event_type:
            category = 'write'
        elif 'ioctl' in event_type:
            category = 'ioctl'
        elif 'binder' in event_type:
            category = 'binder'
        elif 'unix' in event_type or 'sock' in event_type or 'inet' in event_type:
            category = 'network'

        # Get device info
        device = None
        pathname = None
        if 'details' in event:
            device = event['details'].get('k_dev', None)
            pathname = event['details'].get('pathname', None)

        timeline_data.append({
            'id': idx,
            'time': idx,  # Using index as time for now
            'event': event_type,
            'category': category,
            'device': device,
            'pathname': pathname,
            'pid': event.get('tgid', None),
            'tid': event.get('tid', None),
        })

    return timeline_data

def create_device_stats(events):
    """Create device usage statistics"""
    device_counts = {}
    device_paths = {}

    for event in events:
        if 'details' in event and 'k_dev' in event['details']:
            device = event['details']['k_dev']
            if device == 0:
                continue

            # Count device usage
            if device not in device_counts:
                device_counts[device] = 0
            device_counts[device] += 1

            # Track pathnames for each device
            if 'pathname' in event['details'] and event['details']['pathname']:
                if device not in device_paths:
                    device_paths[device] = set()
                device_paths[device].add(event['details']['pathname'])

    # Convert to list of dictionaries for easy rendering
    device_stats = []
    for device, count in sorted(device_counts.items(), key=lambda x: x[1], reverse=True):
        paths = list(device_paths.get(device, []))
        device_stats.append({
            'device': device,
            'count': count,
            'paths': paths,
            'path_count': len(paths)
        })

    return device_stats

def create_event_stats(events):
    """Create event type statistics"""
    event_counts = {}

    for event in events:
        event_type = event.get('event', 'unknown')
        if event_type not in event_counts:
            event_counts[event_type] = 0
        event_counts[event_type] += 1

    return [{'event': k, 'count': v} for k, v in
            sorted(event_counts.items(), key=lambda x: x[1], reverse=True)]

def create_pie_chart_base64(data, labels, title):
    """Create a base64 encoded pie chart"""
    plt.figure(figsize=(8, 6))
    plt.pie(data, labels=labels, autopct='%1.1f%%', startangle=90)
    plt.axis('equal')
    plt.title(title)

    # Save to BytesIO object
    buffer = BytesIO()
    plt.savefig(buffer, format='png')
    buffer.seek(0)
    plt.close()

    # Convert to base64
    img_str = base64.b64encode(buffer.getvalue()).decode('utf-8')
    return img_str

def process_tcp_events(events):
    """Extract and process TCP state events"""
    tcp_events = []
    for event in events:
        if event.get('event') == "inet_sock_set_state":
            tcp_events.append({
                'time': tcp_events[-1]['time'] + 1 if tcp_events else 0,
                'state': event['details'].get('newstate', 'unknown'),
                'daddr': event['details'].get('daddr', 'unknown'),
                'saddr': event['details'].get('saddr', 'unknown'),
                'sport': event['details'].get('sport', 'unknown'),
                'dport': event['details'].get('dport', 'unknown'),
                'pid': event.get('tgid', None),
                'tid': event.get('tid', None),
            })
    return tcp_events

# Routes
@app.route('/')
def index():
    """Main application page"""
    events = load_data()
    pids = get_unique_pids(events)
    devices = get_unique_devices(events)
    return render_template('index.html', pids=pids, devices=devices)

@app.route('/api/timeline')
def timeline_data():
    """API endpoint for timeline data"""
    events = load_data()
    pid = request.args.get('pid')
    device = request.args.get('device')

    filtered_events = filter_events(events, pid, device)
    timeline_data = create_timeline_data(filtered_events)

    return jsonify(timeline_data)

@app.route('/api/device_stats')
def device_stats():
    """API endpoint for device statistics"""
    events = load_data()
    pid = request.args.get('pid')

    filtered_events = filter_events(events, pid)
    stats = create_device_stats(filtered_events)

    return jsonify(stats)

@app.route('/api/event_stats')
def event_stats():
    """API endpoint for event type statistics"""
    events = load_data()
    pid = request.args.get('pid')
    device = request.args.get('device')

    filtered_events = filter_events(events, pid, device)
    stats = create_event_stats(filtered_events)

    return jsonify(stats)

@app.route('/api/device_pie_chart')
def device_pie_chart():
    """API endpoint for device usage pie chart"""
    events = load_data()
    pid = request.args.get('pid')

    filtered_events = filter_events(events, pid)
    device_stats = create_device_stats(filtered_events)

    # Use top 10 devices for chart
    top_devices = device_stats[:10]
    counts = [d['count'] for d in top_devices]
    labels = [f"Device {d['device']}" for d in top_devices]

    img_str = create_pie_chart_base64(counts, labels, 'Top 10 Devices by Usage')

    return jsonify({'image': f'data:image/png;base64,{img_str}'})

@app.route('/api/event_pie_chart')
def event_pie_chart():
    """API endpoint for event type pie chart"""
    events = load_data()
    pid = request.args.get('pid')
    device = request.args.get('device')

    filtered_events = filter_events(events, pid, device)
    event_stats = create_event_stats(filtered_events)

    # Use top 10 event types for chart
    top_events = event_stats[:10]
    counts = [e['count'] for e in top_events]
    labels = [e['event'] for e in top_events]

    img_str = create_pie_chart_base64(counts, labels, 'Top 10 Event Types')

    return jsonify({'image': f'data:image/png;base64,{img_str}'})

@app.route('/api/tcp_stats')
def tcp_stats():
    """API endpoint for TCP statistics"""
    events = load_data()
    pid = request.args.get('pid')

    filtered_events = filter_events(events, pid)
    tcp_events = process_tcp_events(filtered_events)

    return jsonify(tcp_events)

if __name__ == '__main__':
    app.run(debug=True)