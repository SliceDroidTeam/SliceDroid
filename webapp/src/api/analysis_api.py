"""
Analysis API Blueprint - Handles advanced analysis endpoints.
"""

from flask import Blueprint, jsonify, request, current_app
from src.controllers import AnalysisController, DataController, AppController

analysis_bp = Blueprint('analysis_api', __name__)


@analysis_bp.route('/advanced-analytics')
def get_advanced_analytics():
    """API endpoint for advanced analytics"""
    try:
        data_controller = DataController(current_app.config_class)
        analysis_controller = AnalysisController(current_app.config_class)
        
        events = data_controller.load_events_data()
        pid = request.args.get('pid')
        window_size = int(request.args.get('window_size', 1000))
        overlap = int(request.args.get('overlap', 200))

        result = analysis_controller.get_advanced_analytics(
            events, pid, window_size, overlap
        )
        
        if 'error' in result:
            return jsonify(result), 400
        
        return jsonify(result)

    except Exception as e:
        print(f"Error in advanced analytics: {e}")
        return jsonify({'error': f'Internal server error: {str(e)}'}), 500


@analysis_bp.route('/network-analysis')
def get_network_analysis():
    """API endpoint for network analysis"""
    try:
        data_controller = DataController(current_app.config_class)
        analysis_controller = AnalysisController(current_app.config_class)
        
        events = data_controller.load_events_data()
        pid = request.args.get('pid')

        result = analysis_controller.get_network_analysis(events, pid)
        
        if 'error' in result:
            return jsonify(result), 500
        
        return jsonify(result)

    except Exception as e:
        print(f"Error in network analysis: {e}")
        return jsonify({'error': 'Internal server error'}), 500


@analysis_bp.route('/process-analysis')
def get_process_analysis():
    """API endpoint for process analysis"""
    try:
        data_controller = DataController(current_app.config_class)
        analysis_controller = AnalysisController(current_app.config_class)
        
        events = data_controller.load_events_data()
        pid = request.args.get('pid')

        result = analysis_controller.get_process_analysis(events, pid)
        
        if 'error' in result:
            return jsonify(result), 500
        
        return jsonify(result)

    except Exception as e:
        print(f"Error in process analysis: {e}")
        return jsonify({'error': 'Internal server error'}), 500


@analysis_bp.route('/analyze', methods=['POST'])
def analyze_app():
    """Start app analysis - frontend expects this endpoint"""
    try:
        app_controller = AppController(current_app.config_class)
        
        data = request.get_json() or {}
        app_id = data.get('app_id')
        generate_targets = data.get('generate_targets', True)
        
        if not app_id:
            return jsonify({'error': 'app_id is required'}), 400
        
        result = app_controller.analyze_app(app_id, generate_targets)
        
        if 'error' in result:
            return jsonify(result), 400
        
        return jsonify(result)
        
    except Exception as e:
        print(f"Error in app analysis: {e}")
        return jsonify({'error': f'Analysis failed: {str(e)}'}), 500


@analysis_bp.route('/statistics')
def get_analysis_statistics():
    """Get analysis statistics - alias for device/event stats"""
    try:
        data_controller = DataController(current_app.config_class)
        
        # Load events and create statistics
        events = data_controller.load_events_data()
        device_stats = data_controller.create_device_stats(events)
        event_stats = data_controller.create_event_stats(events)
        
        return jsonify({
            'device_stats': device_stats,
            'event_stats': event_stats,
            'success': True
        })
        
    except Exception as e:
        print(f"Error in statistics: {e}")
        return jsonify({'error': f'Statistics failed: {str(e)}'}), 500


@analysis_bp.route('/advanced', methods=['POST'])
def post_advanced_analytics():
    """POST version of advanced analytics with config in body"""
    try:
        data_controller = DataController(current_app.config_class)
        analysis_controller = AnalysisController(current_app.config_class)
        
        events = data_controller.load_events_data()
        
        # Get config from POST body
        data = request.get_json() or {}
        pid = data.get('pid')
        window_size = int(data.get('window_size', 1000))
        overlap = int(data.get('overlap', 200))

        result = analysis_controller.get_advanced_analytics(
            events, pid, window_size, overlap
        )
        
        if 'error' in result:
            return jsonify(result), 400
        
        return jsonify(result)

    except Exception as e:
        print(f"Error in advanced analytics: {e}")
        return jsonify({'error': f'Internal server error: {str(e)}'}), 500


@analysis_bp.route('/network')
def get_network():
    """Network analysis with /analysis prefix (alias)"""
    return get_network_analysis()


@analysis_bp.route('/process')
def get_process():
    """Process analysis with /analysis prefix (alias)"""
    return get_process_analysis()