from flask import Flask, render_template, request, jsonify, send_file, make_response
import os
import json
import pandas as pd
import csv
from io import StringIO
import matplotlib.pyplot as plt
import matplotlib
matplotlib.use('Agg')
import numpy as np
import base64
from io import BytesIO
import re
from pathlib import Path
from config import Config
import tempfile
import threading
import uuid
from werkzeug.utils import secure_filename
from trace_processor import TraceProcessor
from advanced_analytics import AdvancedAnalytics
from comprehensive_analyzer import ComprehensiveAnalyzer
import shutil

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

# Global variables for upload tracking
upload_progress = {}
trace_processor = TraceProcessor(app.config_class)
advanced_analytics = AdvancedAnalytics(app.config_class)
comprehensive_analyzer = ComprehensiveAnalyzer(app.config_class)

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

@app.route('/api/upload', methods=['POST'])
def upload_trace():
    """Upload and process a trace file"""
    try:
        if 'trace_file' not in request.files:
            return jsonify({'error': 'No file provided'}), 400
        
        file = request.files['trace_file']
        if file.filename == '':
            return jsonify({'error': 'No file selected'}), 400
        
        if not file.filename.endswith('.trace'):
            return jsonify({'error': 'File must have .trace extension'}), 400
        
        # Generate unique upload ID
        upload_id = str(uuid.uuid4())
        
        # Save uploaded file temporarily
        filename = secure_filename(file.filename)
        temp_dir = tempfile.mkdtemp()
        temp_file_path = os.path.join(temp_dir, filename)
        file.save(temp_file_path)
        
        # Initialize progress tracking
        upload_progress[upload_id] = {
            'progress': 0,
            'status': 'Starting...',
            'completed': False,
            'error': None,
            'result': None
        }
        
        # Start processing in background thread
        def process_file():
            def progress_callback(progress, status):
                upload_progress[upload_id]['progress'] = progress
                upload_progress[upload_id]['status'] = status
            
            try:
                result = trace_processor.process_trace_file(temp_file_path, progress_callback)
                upload_progress[upload_id]['result'] = result
                upload_progress[upload_id]['completed'] = True
                
                if not result['success']:
                    upload_progress[upload_id]['error'] = result.get('error', 'Unknown error')
                    
            except Exception as e:
                upload_progress[upload_id]['error'] = str(e)
                upload_progress[upload_id]['completed'] = True
            finally:
                # Clean up temporary file
                try:
                    shutil.rmtree(temp_dir)
                except:
                    pass
        
        thread = threading.Thread(target=process_file)
        thread.daemon = True
        thread.start()
        
        return jsonify({
            'upload_id': upload_id,
            'message': 'Upload started, processing in background'
        })
        
    except Exception as e:
        return jsonify({'error': f'Upload failed: {str(e)}'}), 500

@app.route('/api/upload/progress/<upload_id>')
def upload_progress_check(upload_id):
    """Check upload progress"""
    if upload_id not in upload_progress:
        return jsonify({'error': 'Upload ID not found'}), 404
    
    progress_data = upload_progress[upload_id]
    
    # Clean up completed uploads after returning status
    if progress_data['completed']:
        # Keep for a short time then clean up
        def cleanup():
            import time
            time.sleep(60)  # Keep for 1 minute
            if upload_id in upload_progress:
                del upload_progress[upload_id]
        
        cleanup_thread = threading.Thread(target=cleanup)
        cleanup_thread.daemon = True
        cleanup_thread.start()
    
    return jsonify(progress_data)

@app.route('/api/advanced-analytics')
def get_advanced_analytics():
    """API endpoint for advanced analytics"""
    try:
        events = load_data()
        pid = request.args.get('pid')
        window_size = int(request.args.get('window_size', 1000))
        overlap = int(request.args.get('overlap', 200))
        
        # Validate PID parameter
        target_pid = None
        if pid:
            if not pid.isdigit():
                return jsonify({'error': 'Invalid PID parameter'}), 400
            target_pid = int(pid)
        
        # Validate window parameters
        if overlap >= window_size:
            return jsonify({'error': 'Overlap must be less than window size'}), 400
        
        # Perform advanced analysis with custom parameters
        analysis = advanced_analytics.analyze_trace_data(events, target_pid, window_size, overlap)
        
        return jsonify(analysis)
        
    except Exception as e:
        print(f"Error in advanced analytics: {e}")
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/api/comprehensive-analysis')
def get_comprehensive_analysis():
    """API endpoint for comprehensive analysis including event slicing and API instances"""
    try:
        events = load_data()
        pid = request.args.get('pid')
        window_size = int(request.args.get('window_size', 5000))
        overlap = int(request.args.get('overlap', 1000))
        asynchronous = request.args.get('asynchronous', 'true').lower() == 'true'
        
        # Validate PID parameter
        target_pid = None
        if pid:
            if not pid.isdigit():
                return jsonify({'error': 'Invalid PID parameter'}), 400
            target_pid = int(pid)
        else:
            # Find most active PID if not provided
            pid_counts = {}
            for event in events:
                if 'tgid' in event and event['tgid'] > 0:
                    pid_counts[event['tgid']] = pid_counts.get(event['tgid'], 0) + 1
            if pid_counts:
                target_pid = max(pid_counts, key=pid_counts.get)
            else:
                return jsonify({'error': 'No valid PIDs found in events'}), 400
        
        # Perform comprehensive file analysis
        analysis_results = comprehensive_analyzer.slice_file_analysis(
            events, target_pid, window_size, overlap, asynchronous
        )
        
        # Generate comprehensive statistics
        comprehensive_stats = comprehensive_analyzer.produce_comprehensive_stats(analysis_results)
        
        return jsonify({
            'target_pid': target_pid,
            'analysis_results': analysis_results,
            'comprehensive_stats': comprehensive_stats,
            'parameters': {
                'window_size': window_size,
                'overlap': overlap,
                'asynchronous': asynchronous
            }
        })
        
    except Exception as e:
        print(f"Error in comprehensive analysis: {e}")
        return jsonify({'error': f'Comprehensive analysis failed: {str(e)}'}), 500

@app.route('/api/api-instances')
def get_api_instances():
    """API endpoint for API instance extraction"""
    try:
        events = load_data()
        pid = request.args.get('pid')
        
        # Validate PID parameter
        target_pid = None
        if pid:
            if not pid.isdigit():
                return jsonify({'error': 'Invalid PID parameter'}), 400
            target_pid = int(pid)
        
        # Extract API instances
        api_instances = comprehensive_analyzer.extract_api_instances(events, target_pid)
        
        # Get relevant API instances for target PID
        if target_pid:
            relevant_apis = comprehensive_analyzer.extract_relevant_api_instances(events, target_pid)
        else:
            relevant_apis = set()
        
        return jsonify({
            'api_instances': api_instances,
            'relevant_apis': list(relevant_apis),
            'target_pid': target_pid
        })
        
    except Exception as e:
        print(f"Error in API instances analysis: {e}")
        return jsonify({'error': f'API instances analysis failed: {str(e)}'}), 500

@app.route('/api/event-slicing')
def get_event_slicing():
    """API endpoint for advanced event slicing"""
    try:
        events = load_data()
        pid = request.args.get('pid')
        asynchronous = request.args.get('asynchronous', 'false').lower() == 'true'
        
        # Validate PID parameter
        if not pid or not pid.isdigit():
            return jsonify({'error': 'Valid PID parameter required'}), 400
        
        target_pid = int(pid)
        
        # Perform event slicing
        sliced_events = comprehensive_analyzer.slice_events(events, target_pid, asynchronous)
        
        return jsonify({
            'target_pid': target_pid,
            'original_events_count': len(events),
            'sliced_events_count': len(sliced_events),
            'sliced_events': sliced_events[:1000],  # Limit for performance
            'parameters': {
                'asynchronous': asynchronous
            }
        })
        
    except Exception as e:
        print(f"Error in event slicing: {e}")
        return jsonify({'error': f'Event slicing failed: {str(e)}'}), 500

@app.route('/api/export/events')
def export_events():
    """Export processed events in CSV or JSON format"""
    try:
        format_type = request.args.get('format', 'json').lower()
        pid = request.args.get('pid')
        device = request.args.get('device')
        limit = request.args.get('limit', type=int)
        
        # Validate format
        if format_type not in ['csv', 'json']:
            return jsonify({'error': 'Format must be csv or json'}), 400
        
        # Load and filter events
        events = load_data()
        if not events:
            return jsonify({'error': 'No events found'}), 404
        
        # Apply filters
        filtered_events = filter_events(events, pid, device)
        
        # Apply limit if specified
        if limit and limit > 0:
            filtered_events = filtered_events[:limit]
        
        # Generate filename
        filename_parts = ['events']
        if pid:
            filename_parts.append(f'pid{pid}')
        if device:
            filename_parts.append(f'dev{device}')
        if limit:
            filename_parts.append(f'limit{limit}')
        
        base_filename = '_'.join(filename_parts)
        
        if format_type == 'csv':
            return export_events_csv(filtered_events, base_filename)
        else:
            return export_events_json(filtered_events, base_filename)
            
    except Exception as e:
        print(f"Error in export events: {e}")
        return jsonify({'error': f'Export failed: {str(e)}'}), 500

def export_events_csv(events, base_filename):
    """Export events as CSV"""
    output = StringIO()
    
    if not events:
        fieldnames = ['event', 'tgid', 'tid', 'process', 'timestamp']
    else:
        # Get all possible field names
        fieldnames = set(['event', 'tgid', 'tid', 'process', 'timestamp'])
        for event in events:
            fieldnames.update(event.keys())
            if 'details' in event and isinstance(event['details'], dict):
                for detail_key in event['details'].keys():
                    fieldnames.add(f'details_{detail_key}')
        fieldnames = sorted(list(fieldnames))
    
    writer = csv.DictWriter(output, fieldnames=fieldnames)
    writer.writeheader()
    
    for event in events:
        row = {}
        for field in fieldnames:
            if field.startswith('details_'):
                detail_key = field[8:]  # Remove 'details_' prefix
                if 'details' in event and isinstance(event['details'], dict):
                    row[field] = event['details'].get(detail_key, '')
                else:
                    row[field] = ''
            else:
                row[field] = event.get(field, '')
        writer.writerow(row)
    
    output.seek(0)
    
    # Create response
    response = make_response(output.getvalue())
    response.headers['Content-Type'] = 'text/csv'
    response.headers['Content-Disposition'] = f'attachment; filename="{base_filename}.csv"'
    
    return response

def export_events_json(events, base_filename):
    """Export events as JSON"""
    # Create response
    response = make_response(json.dumps(events, indent=2))
    response.headers['Content-Type'] = 'application/json'
    response.headers['Content-Disposition'] = f'attachment; filename="{base_filename}.json"'
    
    return response

@app.route('/api/export/analysis')
def export_analysis():
    """Export comprehensive analysis results"""
    try:
        format_type = request.args.get('format', 'json').lower()
        pid = request.args.get('pid')
        window_size = int(request.args.get('window_size', 5000))
        overlap = int(request.args.get('overlap', 1000))
        asynchronous = request.args.get('asynchronous', 'true').lower() == 'true'
        
        # Validate format
        if format_type not in ['csv', 'json']:
            return jsonify({'error': 'Format must be csv or json'}), 400
        
        # Load events
        events = load_data()
        if not events:
            return jsonify({'error': 'No events found'}), 404
        
        # Find target PID if not provided
        target_pid = None
        if pid:
            if not pid.isdigit():
                return jsonify({'error': 'Invalid PID parameter'}), 400
            target_pid = int(pid)
        else:
            pid_counts = {}
            for event in events:
                if 'tgid' in event and event['tgid'] > 0:
                    pid_counts[event['tgid']] = pid_counts.get(event['tgid'], 0) + 1
            if pid_counts:
                target_pid = max(pid_counts, key=pid_counts.get)
            else:
                return jsonify({'error': 'No valid PIDs found in events'}), 400
        
        # Perform comprehensive analysis
        analysis_results = comprehensive_analyzer.slice_file_analysis(
            events, target_pid, window_size, overlap, asynchronous
        )
        
        # Generate comprehensive statistics
        comprehensive_stats = comprehensive_analyzer.produce_comprehensive_stats(analysis_results)
        
        # Combine results
        export_data = {
            'target_pid': target_pid,
            'parameters': {
                'window_size': window_size,
                'overlap': overlap,
                'asynchronous': asynchronous
            },
            'analysis_results': analysis_results,
            'comprehensive_stats': comprehensive_stats
        }
        
        # Generate filename
        filename = f'analysis_pid{target_pid}_ws{window_size}_ol{overlap}'
        
        if format_type == 'csv':
            return export_analysis_csv(export_data, filename)
        else:
            return export_analysis_json(export_data, filename)
            
    except Exception as e:
        print(f"Error in export analysis: {e}")
        return jsonify({'error': f'Analysis export failed: {str(e)}'}), 500

def export_analysis_csv(analysis_data, base_filename):
    """Export analysis results as CSV (flattened)"""
    output = StringIO()
    
    # Write comprehensive stats as CSV
    writer = csv.writer(output)
    
    # Header
    writer.writerow(['Analysis Results Export'])
    writer.writerow(['Generated by SYSDROID Web App'])
    writer.writerow([])
    
    # Parameters
    writer.writerow(['Parameters'])
    for key, value in analysis_data['parameters'].items():
        writer.writerow([key, value])
    writer.writerow([])
    
    # Comprehensive Stats
    writer.writerow(['Comprehensive Statistics'])
    stats = analysis_data['comprehensive_stats']
    for key, value in stats.items():
        if isinstance(value, dict):
            writer.writerow([key])
            for sub_key, sub_value in value.items():
                writer.writerow(['', sub_key, sub_value])
        elif isinstance(value, list):
            writer.writerow([key])
            for i, item in enumerate(value):
                if isinstance(item, list):
                    writer.writerow(['', f'Item {i+1}', ', '.join(map(str, item))])
                else:
                    writer.writerow(['', f'Item {i+1}', item])
        else:
            writer.writerow([key, value])
    
    output.seek(0)
    
    # Create response
    response = make_response(output.getvalue())
    response.headers['Content-Type'] = 'text/csv'
    response.headers['Content-Disposition'] = f'attachment; filename="{base_filename}.csv"'
    
    return response

def export_analysis_json(analysis_data, base_filename):
    """Export analysis results as JSON"""
    # Convert sets to lists for JSON serialization
    def convert_sets(obj):
        if isinstance(obj, set):
            return list(obj)
        elif isinstance(obj, dict):
            return {k: convert_sets(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [convert_sets(item) for item in obj]
        return obj
    
    serializable_data = convert_sets(analysis_data)
    
    # Create response
    response = make_response(json.dumps(serializable_data, indent=2))
    response.headers['Content-Type'] = 'application/json'
    response.headers['Content-Disposition'] = f'attachment; filename="{base_filename}.json"'
    
    return response

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