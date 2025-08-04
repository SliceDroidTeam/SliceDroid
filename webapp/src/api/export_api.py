"""
Export API Blueprint - Handles data export endpoints.
"""

from flask import Blueprint, jsonify, request, make_response, current_app
from src.controllers import DataController, AnalysisController
import pandas as pd
import json
from io import StringIO

export_bp = Blueprint('export_api', __name__)


@export_bp.route('/events')
def export_events():
    """Export events data in specified format"""
    try:
        data_controller = DataController(current_app.config_class)
        
        events = data_controller.load_events_data()
        format_type = request.args.get('format', 'json')
        limit = request.args.get('limit')

        result = data_controller.export_events(events, format_type, limit)
        
        if 'error' in result:
            return jsonify(result), 400

        response = make_response(result['content'])
        response.headers['Content-Type'] = result['content_type']
        response.headers['Content-Disposition'] = f'attachment; filename={result["filename"]}'
        return response

    except Exception as e:
        print(f"Error in export events: {e}")
        return jsonify({'error': 'Internal server error'}), 500


@export_bp.route('/analysis')
def export_analysis():
    """Export analysis results in specified format"""
    try:
        data_controller = DataController(current_app.config_class)
        analysis_controller = AnalysisController(current_app.config_class)
        
        events = data_controller.load_events_data()
        pid = request.args.get('pid')
        format_type = request.args.get('format', 'json')
        window_size = int(request.args.get('window_size', 1000))
        overlap = int(request.args.get('overlap', 200))

        # Get analysis results
        analysis = analysis_controller.get_advanced_analytics(
            events, pid, window_size, overlap
        )
        
        if 'error' in analysis:
            return jsonify(analysis), 400

        # Generate filename
        timestamp = pd.Timestamp.now().strftime('%Y%m%d_%H%M%S')
        filename_parts = ['analysis']
        if pid:
            filename_parts.append(f'pid{pid}')
        filename_parts.append(timestamp)

        if format_type.lower() == 'csv':
            # Convert analysis to CSV format
            analysis_data = []
            for key, value in analysis.items():
                if isinstance(value, dict):
                    for subkey, subvalue in value.items():
                        analysis_data.append({
                            'category': key,
                            'metric': subkey,
                            'value': str(subvalue)
                        })
                else:
                    analysis_data.append({
                        'category': 'general',
                        'metric': key,
                        'value': str(value)
                    })

            df = pd.DataFrame(analysis_data)
            output = StringIO()
            df.to_csv(output, index=False)

            filename = '_'.join(filename_parts) + '.csv'
            response = make_response(output.getvalue())
            response.headers['Content-Type'] = 'text/csv'
            response.headers['Content-Disposition'] = f'attachment; filename={filename}'
            return response
        else:
            # JSON response
            filename = '_'.join(filename_parts) + '.json'
            response = make_response(json.dumps(analysis, indent=2))
            response.headers['Content-Type'] = 'application/json'
            response.headers['Content-Disposition'] = f'attachment; filename={filename}'
            return response

    except Exception as e:
        print(f"Error in export analysis: {e}")
        return jsonify({'error': 'Internal server error'}), 500