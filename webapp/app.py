from flask import Flask, render_template, request, jsonify
import os
import json
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib
matplotlib.use('Agg')
import numpy as np
import base64
from io import BytesIO
import re
from pathlib import Path
from config import Config

def create_app(config_name='default'):
    """Application factory pattern"""
    app = Flask(
        __name__,
        static_folder='static',
        template_folder='templates'
    )
    
    # Load configuration
    from config import config
    app.config.from_object(config[config_name])
    app.config_class = config[config_name]
    
    return app

app = create_app(os.getenv('FLASK_ENV', 'default'))

def load_data():
    """Load the processed events from JSON file"""
    events_file = app.config_class.PROCESSED_EVENTS_JSON
    try:
        if Path(events_file).exists():
            with open(events_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                if not isinstance(data, list):
                    return []
                return data
    except (json.JSONDecodeError, IOError) as e:
        print(f"Error loading data from {events_file}: {e}")
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
        if 'details' in event:
            # Check for both k_dev and k__dev (double underscore)
            device_key = None
            if 'k_dev' in event['details']:
                device_key = 'k_dev'
            elif 'k__dev' in event['details']:
                device_key = 'k__dev'
            
            if device_key and event['details'][device_key] != 0:
                devices.add(event['details'][device_key])
    return sorted(list(devices))

def filter_events(events, pid=None, device=None):
    """Filter events by PID and/or device"""
    if not isinstance(events, list):
        return []
        
    filtered = events
    
    if pid:
        try:
            pid_int = int(pid)
            filtered = [e for e in filtered if isinstance(e, dict) and 'tgid' in e and e['tgid'] == pid_int]
        except (ValueError, TypeError):
            return []
    
    if device:
        try:
            device_int = int(device)
            def has_matching_device(event):
                if not isinstance(event, dict) or 'details' not in event:
                    return False
                details = event['details']
                if not isinstance(details, dict):
                    return False
                # Check both k_dev and k__dev
                device_value = details.get('k_dev') or details.get('k__dev')
                return device_value == device_int
            
            filtered = [e for e in filtered if has_matching_device(e)]
        except (ValueError, TypeError):
            return []
            
    return filtered

def create_timeline_data(events):
    """Create timeline data for visualization"""
    timeline_data = []
    max_events = app.config_class.TIMELINE_MAX_EVENTS
    
    # Limit events for performance
    events_to_process = events[:max_events] if len(events) > max_events else events
    
    for idx, event in enumerate(events_to_process):
        if not isinstance(event, dict):
            continue
            
        event_type = event.get('event', 'unknown')
        category = app.config_class.get_event_category(event_type)

        # Get device info
        device = None
        pathname = None
        if 'details' in event and isinstance(event['details'], dict):
            # Check both k_dev and k__dev
            device = event['details'].get('k_dev') or event['details'].get('k__dev')
            pathname = event['details'].get('pathname', None)

        timeline_data.append({
            'id': idx,
            'time': idx,
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
        if 'details' in event:
            # Check both k_dev and k__dev
            device = event['details'].get('k_dev') or event['details'].get('k__dev')
            if not device or device == 0:
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
    if not data or not labels or len(data) != len(labels):
        return None
        
    try:
        plt.figure(figsize=(8, 6))
        plt.pie(data, labels=labels, autopct='%1.1f%%', startangle=90)
        plt.axis('equal')
        plt.title(title)

        buffer = BytesIO()
        plt.savefig(buffer, format='png', dpi=100, bbox_inches='tight')
        buffer.seek(0)
        plt.close()

        img_str = base64.b64encode(buffer.getvalue()).decode('utf-8')
        return img_str
    except Exception as e:
        print(f"Error creating pie chart: {e}")
        plt.close()
        return None

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
    try:
        events = load_data()
        pid = request.args.get('pid')
        device = request.args.get('device')

        # Validate input parameters
        if pid and not pid.isdigit():
            return jsonify({'error': 'Invalid PID parameter'}), 400
        if device and not device.isdigit():
            return jsonify({'error': 'Invalid device parameter'}), 400

        filtered_events = filter_events(events, pid, device)
        timeline_data = create_timeline_data(filtered_events)

        return jsonify(timeline_data)
    except Exception as e:
        print(f"Error in timeline_data: {e}")
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/api/device_stats')
def device_stats():
    """API endpoint for device statistics"""
    try:
        events = load_data()
        pid = request.args.get('pid')

        # Validate input parameters
        if pid and not pid.isdigit():
            return jsonify({'error': 'Invalid PID parameter'}), 400

        filtered_events = filter_events(events, pid)
        stats = create_device_stats(filtered_events)

        return jsonify(stats)
    except Exception as e:
        print(f"Error in device_stats: {e}")
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/api/event_stats')
def event_stats():
    """API endpoint for event type statistics"""
    try:
        events = load_data()
        pid = request.args.get('pid')
        device = request.args.get('device')

        # Validate input parameters
        if pid and not pid.isdigit():
            return jsonify({'error': 'Invalid PID parameter'}), 400
        if device and not device.isdigit():
            return jsonify({'error': 'Invalid device parameter'}), 400

        filtered_events = filter_events(events, pid, device)
        stats = create_event_stats(filtered_events)

        return jsonify(stats)
    except Exception as e:
        print(f"Error in event_stats: {e}")
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/api/device_pie_chart')
def device_pie_chart():
    """API endpoint for device usage pie chart"""
    try:
        events = load_data()
        pid = request.args.get('pid')

        # Validate input parameters
        if pid and not pid.isdigit():
            return jsonify({'error': 'Invalid PID parameter'}), 400

        filtered_events = filter_events(events, pid)
        device_stats = create_device_stats(filtered_events)

        # Use configurable number of top devices for chart
        top_n = app.config_class.CHART_TOP_N_DEVICES
        top_devices = device_stats[:top_n]
        counts = [d['count'] for d in top_devices]
        labels = [f"Device {d['device']}" for d in top_devices]

        img_str = create_pie_chart_base64(counts, labels, f'Top {top_n} Devices by Usage')
        
        if img_str is None:
            return jsonify({'error': 'Failed to generate chart'}), 500

        return jsonify({'image': f'data:image/png;base64,{img_str}'})
    except Exception as e:
        print(f"Error in device_pie_chart: {e}")
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/api/event_pie_chart')
def event_pie_chart():
    """API endpoint for event type pie chart"""
    try:
        events = load_data()
        pid = request.args.get('pid')
        device = request.args.get('device')

        # Validate input parameters
        if pid and not pid.isdigit():
            return jsonify({'error': 'Invalid PID parameter'}), 400
        if device and not device.isdigit():
            return jsonify({'error': 'Invalid device parameter'}), 400

        filtered_events = filter_events(events, pid, device)
        event_stats = create_event_stats(filtered_events)

        # Use configurable number of top events for chart
        top_n = app.config_class.CHART_TOP_N_EVENTS
        top_events = event_stats[:top_n]
        counts = [e['count'] for e in top_events]
        labels = [e['event'] for e in top_events]

        img_str = create_pie_chart_base64(counts, labels, f'Top {top_n} Event Types')
        
        if img_str is None:
            return jsonify({'error': 'Failed to generate chart'}), 500

        return jsonify({'image': f'data:image/png;base64,{img_str}'})
    except Exception as e:
        print(f"Error in event_pie_chart: {e}")
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/api/tcp_stats')
def tcp_stats():
    """API endpoint for TCP statistics"""
    try:
        events = load_data()
        pid = request.args.get('pid')

        # Validate input parameters
        if pid and not pid.isdigit():
            return jsonify({'error': 'Invalid PID parameter'}), 400

        filtered_events = filter_events(events, pid)
        tcp_events = process_tcp_events(filtered_events)

        return jsonify(tcp_events)
    except Exception as e:
        print(f"Error in tcp_stats: {e}")
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/api/config')
def get_config():
    """API endpoint for client configuration"""
    return jsonify({
        'event_categories': app.config_class.EVENT_CATEGORIES,
        'timeline_max_events': app.config_class.TIMELINE_MAX_EVENTS,
        'default_zoom': app.config_class.TIMELINE_DEFAULT_ZOOM,
        'top_devices': app.config_class.CHART_TOP_N_DEVICES,
        'top_events': app.config_class.CHART_TOP_N_EVENTS
    })

@app.route('/api/health')
def health_check():
    """Health check endpoint"""
    errors = app.config_class.validate_paths()
    status = 'healthy' if not errors else 'unhealthy'
    return jsonify({
        'status': status,
        'errors': errors,
        'data_file_exists': Path(app.config_class.PROCESSED_EVENTS_JSON).exists()
    })

if __name__ == '__main__':
    # Validate configuration on startup
    config_errors = app.config_class.validate_paths()
    if config_errors:
        print("Configuration warnings:")
        for error in config_errors:
            print(f"  - {error}")
    
    app.run(
        host=app.config_class.HOST,
        port=app.config_class.PORT,
        debug=app.config_class.DEBUG
    )