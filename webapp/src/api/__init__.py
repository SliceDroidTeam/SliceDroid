"""
API Package - Clean API layer with organized blueprints.

This package provides a structured approach to API endpoints,
separating concerns and improving maintainability.
"""

from flask import Blueprint
from .data_api import data_bp
from .analysis_api import analysis_bp
from .app_api import app_bp
from .upload_api import upload_bp
from .export_api import export_bp
from .system_api import system_bp


def register_api_blueprints(app):
    """Register all API blueprints with the Flask application"""
    app.register_blueprint(data_bp, url_prefix='/api')
    app.register_blueprint(analysis_bp, url_prefix='/api/analysis')
    app.register_blueprint(app_bp, url_prefix='/api/apps')
    app.register_blueprint(upload_bp, url_prefix='/api/upload')
    app.register_blueprint(export_bp, url_prefix='/api/export')
    app.register_blueprint(system_bp, url_prefix='/api/system')


__all__ = [
    'register_api_blueprints',
    'data_bp',
    'analysis_bp', 
    'app_bp',
    'upload_bp',
    'export_bp',
    'system_bp'
]