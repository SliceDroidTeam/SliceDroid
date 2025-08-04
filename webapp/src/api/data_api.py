"""
Data API Blueprint - Handles basic data retrieval endpoints.
"""

from flask import Blueprint, jsonify, current_app
from src.controllers import DataController

data_bp = Blueprint('data_api', __name__)


@data_bp.route('/timeline')
def timeline_data():
    """API endpoint for timeline data"""
    try:
        data_controller = DataController(current_app.config_class)
        events = data_controller.load_events_data()
        timeline_data = data_controller.create_timeline_data(events)
        return jsonify(timeline_data)
    except Exception as e:
        print(f"Error in timeline_data: {e}")
        return jsonify({'error': 'Internal server error'}), 500


@data_bp.route('/device_stats')
def device_stats():
    """API endpoint for device statistics"""
    try:
        data_controller = DataController(current_app.config_class)
        events = data_controller.load_events_data()
        stats = data_controller.create_device_stats(events)
        return jsonify(stats)
    except Exception as e:
        print(f"Error in device_stats: {e}")
        return jsonify({'error': 'Internal server error'}), 500


@data_bp.route('/event_stats')
def event_stats():
    """API endpoint for event type statistics"""
    try:
        data_controller = DataController(current_app.config_class)
        events = data_controller.load_events_data()
        stats = data_controller.create_event_stats(events)
        return jsonify(stats)
    except Exception as e:
        print(f"Error in event_stats: {e}")
        return jsonify({'error': 'Internal server error'}), 500


@data_bp.route('/device_chart_data')
def device_chart_data():
    """API endpoint for device usage chart data"""
    try:
        data_controller = DataController(current_app.config_class)
        events = data_controller.load_events_data()
        device_stats = data_controller.create_device_stats(events)

        top_n = current_app.config_class.CHART_TOP_N_DEVICES
        top_devices = device_stats[:top_n]
        
        # Return pure data for frontend chart generation
        chart_data = [
            {
                'label': f"Device {d['device']}",
                'value': d['count'],
                'device_id': d['device'],
                'percentage': round((d['count'] / sum(dev['count'] for dev in device_stats)) * 100, 1) if device_stats else 0
            }
            for d in top_devices
        ]

        return jsonify({
            'data': chart_data,
            'title': f'Top {top_n} Devices by Usage',
            'total_devices': len(device_stats),
            'total_accesses': sum(d['count'] for d in device_stats)
        })
    except Exception as e:
        print(f"Error in device_chart_data: {e}")
        return jsonify({'error': 'Internal server error'}), 500


@data_bp.route('/event_chart_data')
def event_chart_data():
    """API endpoint for event type chart data"""
    try:
        data_controller = DataController(current_app.config_class)
        events = data_controller.load_events_data()
        event_stats = data_controller.create_event_stats(events)

        top_n = current_app.config_class.CHART_TOP_N_EVENTS
        top_events = event_stats[:top_n]
        
        # Return pure data for frontend chart generation
        total_events = sum(e['count'] for e in event_stats)
        chart_data = [
            {
                'label': e['event'],
                'value': e['count'],
                'percentage': round((e['count'] / total_events) * 100, 1) if total_events > 0 else 0
            }
            for e in top_events
        ]

        return jsonify({
            'data': chart_data,
            'title': f'Top {top_n} Event Types',
            'total_events': total_events,
            'unique_event_types': len(event_stats)
        })
    except Exception as e:
        print(f"Error in event_chart_data: {e}")
        return jsonify({'error': 'Internal server error'}), 500


@data_bp.route('/tcp_stats')
def tcp_stats():
    """API endpoint for TCP statistics"""
    try:
        data_controller = DataController(current_app.config_class)
        events = data_controller.load_events_data()
        tcp_events = data_controller.process_tcp_events(events)
        return jsonify(tcp_events)
    except Exception as e:
        print(f"Error in tcp_stats: {e}")
        return jsonify({'error': 'Internal server error'}), 500