"""
Route blueprints for CAM Application
Modular API endpoint organization
"""

from flask import Blueprint

# Import all route blueprints
from .auth_routes import auth_bp
from .client_routes import client_bp
from .request_routes import request_bp
from .upload_routes import upload_bp
from .dashboard_routes import dashboard_bp
from .utility_routes import utility_bp


def register_blueprints(app):
    """
    Register all route blueprints with the Flask application.

    Args:
        app: Flask application instance
    """
    app.register_blueprint(utility_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(client_bp)
    app.register_blueprint(request_bp)
    app.register_blueprint(upload_bp)
    app.register_blueprint(dashboard_bp)
