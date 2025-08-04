"""
Upload API Blueprint - Handles file upload endpoints.
"""

from flask import Blueprint, jsonify, request, current_app
from src.controllers import AppController

upload_bp = Blueprint('upload_api', __name__)


@upload_bp.route('/trace', methods=['POST'])
def upload_trace():
    """Upload and process a trace file"""
    try:
        app_controller = AppController(current_app.config_class)
        
        if 'file' not in request.files:
            return jsonify({'error': 'No file provided'}), 400

        file = request.files['file']
        
        result = app_controller.upload_trace(file)
        
        if 'error' in result:
            return jsonify(result), 400
        
        # Ensure success field is present for frontend
        result['success'] = True
        return jsonify(result)

    except Exception as e:
        return jsonify({'error': f'Upload failed: {str(e)}'}), 500


@upload_bp.route('/progress/<upload_id>')
def upload_progress_check(upload_id):
    """Check upload progress"""
    try:
        app_controller = AppController(current_app.config_class)
        
        result = app_controller.get_upload_progress(upload_id)
        
        if 'error' in result:
            return jsonify(result), 404
        
        return jsonify(result)
        
    except Exception as e:
        return jsonify({'error': 'Internal server error'}), 500


@upload_bp.route('/preloaded-file')
def preloaded_file_info():
    """Return information about the preloaded file if one exists"""
    try:
        app_controller = AppController(current_app.config_class)
        
        result = app_controller.check_preloaded_file()
        return jsonify(result)
        
    except Exception as e:
        return jsonify({'error': 'Internal server error'}), 500