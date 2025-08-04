"""
App API Blueprint - Handles app selection and analysis endpoints.
"""

from flask import Blueprint, jsonify, request, current_app
from src.controllers import AppController, DataController, AnalysisController

app_bp = Blueprint('app_api', __name__)


@app_bp.route('')
def get_apps():
    """API endpoint for getting available apps"""
    try:
        app_controller = AppController(current_app.config_class)
        
        category = request.args.get('category')
        search = request.args.get('search')

        result = app_controller.get_apps(category, search)
        
        if 'error' in result:
            return jsonify(result), 500
        
        return jsonify(result)

    except Exception as e:
        print(f"Error in get_apps: {e}")
        return jsonify({'error': 'Internal server error'}), 500


@app_bp.route('/search')
def search_apps():
    """API endpoint for searching apps"""
    try:
        app_controller = AppController(current_app.config_class)
        
        query = request.args.get('q', '')
        
        result = app_controller.search_apps(query)
        
        if 'error' in result:
            return jsonify(result), 500
        
        return jsonify(result)

    except Exception as e:
        print(f"Error in search_apps: {e}")
        return jsonify({'error': 'Internal server error'}), 500


@app_bp.route('/refresh', methods=['POST'])
def refresh_apps():
    """API endpoint for refreshing app mapping from device"""
    try:
        app_controller = AppController(current_app.config_class)
        
        result = app_controller.refresh_apps()
        
        if 'error' in result:
            return jsonify(result), 400
        
        return jsonify(result)

    except Exception as e:
        print(f"Error in refresh_apps: {e}")
        return jsonify({'error': 'Internal server error'}), 500


@app_bp.route('/generate-targets', methods=['POST'])
def generate_process_targets():
    """API endpoint for generating process targets from selected apps"""
    try:
        app_controller = AppController(current_app.config_class)
        
        data = request.get_json()
        selected_apps = data.get('selected_apps', [])

        result = app_controller.generate_process_targets(selected_apps)
        
        if 'error' in result:
            return jsonify(result), 400
        
        return jsonify(result)

    except Exception as e:
        print(f"Error in generate_process_targets: {e}")
        return jsonify({'error': 'Internal server error'}), 500


@app_bp.route('/analyze', methods=['POST'])
def analyze_app():
    """API endpoint for processing trace and analyzing specific app"""
    try:
        data_controller = DataController(current_app.config_class)
        app_controller = AppController(current_app.config_class)
        analysis_controller = AnalysisController(current_app.config_class)
        
        data = request.get_json()
        app_id = data.get('app_id')

        if not app_id:
            return jsonify({'error': 'No app specified'}), 400

        # Load current events for PID lookup
        events = data_controller.load_events_data()
        
        # Delegate to app controller
        result = app_controller.analyze_app(app_id, events)
        
        if 'error' in result:
            return jsonify(result), 400
        
        # If successful, also slice the events for the dashboard
        if result.get('success'):
            target_pid = result.get('target_pid')
            sliced_events = analysis_controller.slice_events_for_app(events, target_pid)
            
            if isinstance(sliced_events, list):
                # Save sliced events for dashboard
                data_controller.data_manager.save_events(sliced_events)
                result['events_count'] = len(sliced_events)
                result['message'] = f"Analysis complete for {result.get('app_name')}. Found {len(sliced_events)} relevant events."
        
        return jsonify(result)

    except Exception as e:
        print(f"Error in analyze_app: {e}")
        return jsonify({'error': f'Analysis failed: {str(e)}'}), 500