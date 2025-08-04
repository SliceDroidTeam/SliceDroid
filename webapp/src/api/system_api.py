"""
System API Blueprint - Handles system configuration and health endpoints.
"""

from flask import Blueprint, jsonify, make_response, current_app
from pathlib import Path

system_bp = Blueprint('system_api', __name__)


@system_bp.route('/config')
def get_config():
    """API endpoint for client configuration"""
    return jsonify({
        'event_categories': current_app.config_class.EVENT_CATEGORIES,
        'timeline_max_events': current_app.config_class.TIMELINE_MAX_EVENTS,
        'default_zoom': current_app.config_class.TIMELINE_DEFAULT_ZOOM,
        'top_devices': current_app.config_class.CHART_TOP_N_DEVICES,
        'top_events': current_app.config_class.CHART_TOP_N_EVENTS
    })


@system_bp.route('/health')
def health_check():
    """Health check endpoint"""
    errors = current_app.config_class.validate_paths()
    status = 'healthy' if not errors else 'unhealthy'
    return jsonify({
        'status': status,
        'errors': errors,
        'data_file_exists': Path(current_app.config_class.PROCESSED_EVENTS_JSON).exists()
    })


@system_bp.route('/configuration')
def get_system_configuration():
    """System configuration endpoint (alias for /config)"""
    return get_config()


@system_bp.route('/status')
def get_system_status():
    """System status endpoint (alias for /health)"""
    return health_check()




