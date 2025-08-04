"""
SliceDroid Web Application - Clean Architecture Version

This is the main Flask application with clean separation of concerns:
- Routes handle HTTP requests/responses only
- Controllers handle business logic
- Services handle data processing
"""

from flask import Flask, render_template, request, jsonify, send_file, make_response
import os
from pathlib import Path
from config import Config

# Import controllers
from src.controllers import AnalysisController, DataController, AppController

# Import API blueprints
from src.api import register_api_blueprints


def create_app(config_name='default'):
    """Application factory pattern"""
    app = Flask(
        __name__,
        static_folder='src/static',
        template_folder='src/templates'
    )

    # Load configuration
    from config import config
    app.config.from_object(config[config_name])
    app.config_class = config[config_name]

    return app


app = create_app(os.getenv('FLASK_ENV', 'default'))

# Register API blueprints
register_api_blueprints(app)


# ============================================================================
# MAIN ROUTES
# ============================================================================

@app.route('/')
def index():
    """Main application page with optimized loading"""
    try:
        # Initialize data controller for main page
        data_controller = DataController(app.config_class)
        events = data_controller.load_events_data()

        # For very large datasets, use fast extraction
        if len(events) > 100000:
            # Sample for quick PID/device extraction
            sample_events = events[::max(1, len(events) // 10000)]
            pids = _get_unique_pids_fast(sample_events, events)
            devices = _get_unique_devices_fast(sample_events, events)
        else:
            pids = data_controller.get_unique_pids(events)
            devices = data_controller.get_unique_devices(events)

        return render_template('index.html', pids=pids, devices=devices,
                             events_count=len(events))
    except Exception as e:
        print(f"Error in index route: {e}")
        return render_template('index.html', pids=[], devices=[], events_count=0)



# Special route for serving category mapping file (not part of REST API)
@app.route('/data/mappings/cat2devs.txt')
def get_category_mapping():
    """Serve device category mapping file"""
    try:
        mapping_file = app.config_class.PROJECT_ROOT / 'data' / 'mappings' / 'cat2devs.txt'
        if mapping_file.exists():
            with open(mapping_file, 'r') as f:
                content = f.read()
            response = make_response(content)
            response.headers['Content-Type'] = 'application/json'
            return response
        else:
            return jsonify({'error': 'Category mapping file not found'}), 404
    except Exception as e:
        print(f"Error serving category mapping: {e}")
        return jsonify({'error': 'Internal server error'}), 500


# ============================================================================
# HELPER FUNCTIONS (Legacy compatibility)
# ============================================================================

def _get_unique_pids_fast(sample_events, full_events):
    """Fast PID extraction for large datasets using sampling"""
    pids = set()
    
    # Get PIDs from sample first
    for event in sample_events:
        if 'tgid' in event:
            pids.add(event['tgid'])

    # If sample seems incomplete, do a sparse scan of full dataset
    if len(pids) < 10:
        step = max(1, len(full_events) // 50000)
        for i in range(0, len(full_events), step):
            event = full_events[i]
            if 'tgid' in event:
                pids.add(event['tgid'])

    return sorted(list(pids))


def _get_unique_devices_fast(sample_events, full_events):
    """Fast device extraction for large datasets using sampling"""
    devices = set()
    
    # Get devices from sample first
    for event in sample_events:
        details = event.get('details')
        if details:
            device_id = details.get('k_dev') or details.get('k__dev')
            if device_id and device_id != 0:
                devices.add(device_id)

    # If sample seems incomplete, do a sparse scan of full dataset
    if len(devices) < 5:
        step = max(1, len(full_events) // 50000)
        for i in range(0, len(full_events), step):
            event = full_events[i]
            details = event.get('details')
            if details:
                device_id = details.get('k_dev') or details.get('k__dev')
                if device_id and device_id != 0:
                    devices.add(device_id)

    return sorted(list(devices))


# ============================================================================
# APPLICATION STARTUP
# ============================================================================

if __name__ == '__main__':
    # Validate configuration on startup
    config_errors = app.config_class.validate_paths()
    if config_errors:
        print("Configuration warnings:")
        for error in config_errors:
            print(f"  - {error}")

    # Check for preloaded trace file
    try:
        default_trace_path = app.config_class.PROJECT_ROOT / 'data' / 'traces' / 'trace.trace'
        if default_trace_path.exists():
            print(f"Found default trace file: {default_trace_path}")
        else:
            print(f"No default trace file found at: {default_trace_path}")
    except Exception as e:
        print(f"Error checking trace file: {e}")

    app.run(
        host=app.config_class.HOST,
        port=app.config_class.PORT,
        debug=app.config_class.DEBUG
    )