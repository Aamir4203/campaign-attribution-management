#!/usr/bin/env python3
"""
Campaign Attribution Management (CAM) - Main Application
Modular Flask application with blueprint-based architecture
"""

from flask import Flask, jsonify
from flask_cors import CORS
import logging
from datetime import datetime
import signal
import sys

# Import configuration
from config.config import get_config

# Import database module
import db

# Load configuration
config = get_config()

# Configure logging
logging_config = config.get_logging_config()
logging.basicConfig(
    level=getattr(logging, logging_config.get('level', 'DEBUG')),
    format=logging_config.get('format', '%(asctime)s [%(levelname)s] %(name)s: %(message)s')
)
logger = logging.getLogger(__name__)

# Validate configuration on startup
if not config.validate_config():
    logger.error("❌ Configuration validation failed - exiting")
    sys.exit(1)

logger.info("✅ Configuration loaded and validated")

# Create Flask application
app = Flask(__name__)

# Enable CORS with configuration
cors_origins = config.get_cors_origins()
cors_config = config.get_cors_config()
CORS(app,
     origins=cors_origins,
     allow_headers=cors_config.get('allowedHeaders', ['Content-Type', 'Accept', 'Authorization']),
     methods=cors_config.get('allowedMethods', ['GET', 'POST', 'OPTIONS'])
)

logger.info(f"✅ CORS configured for origins: {cors_origins}")

# Initialize database connection pool
if not db.initialize_pool():
    logger.error("❌ Failed to initialize database pool - exiting")
    sys.exit(1)


# Register route blueprints
def register_blueprints():
    """
    Register all route blueprints with the Flask application.
    Routes are organized by domain/functionality.
    """
    try:
        # Import blueprints (only import ones that exist)
        from routes.utility_routes import utility_bp
        from routes.auth_routes import auth_bp
        from routes.client_routes import client_bp
        from routes.upload_routes import upload_bp

        # Register blueprints
        app.register_blueprint(utility_bp)
        logger.info("✅ Registered utility routes")

        app.register_blueprint(auth_bp)
        logger.info("✅ Registered auth routes")

        app.register_blueprint(client_bp)
        logger.info("✅ Registered client routes")

        app.register_blueprint(upload_bp)
        logger.info("✅ Registered upload routes")

        # Import and register request and dashboard blueprints when ready
        try:
            from routes.request_routes import request_bp
            app.register_blueprint(request_bp)
            logger.info("✅ Registered request routes")
        except ImportError as e:
            logger.warning(f"⚠️ Request routes not available: {e}")

        try:
            from routes.dashboard_routes import dashboard_bp
            app.register_blueprint(dashboard_bp)
            logger.info("✅ Registered dashboard routes")
        except ImportError as e:
            logger.warning(f"⚠️ Dashboard routes not available: {e}")

        logger.info("✅ All available blueprints registered successfully")
        return True

    except Exception as e:
        logger.error(f"❌ Error registering blueprints: {e}")
        return False


# Register blueprints
if not register_blueprints():
    logger.error("❌ Failed to register blueprints - exiting")
    sys.exit(1)


# Log startup information
def log_startup_info():
    """Log application startup information"""
    logger.info("=" * 60)
    logger.info("🚀 CAM API Application Started")
    logger.info("=" * 60)
    logger.info(f"   Environment: {config.get_environment()}")
    logger.info(f"   Debug Mode: {config.is_debug()}")
    logger.info(f"   Database: {config.get_database_credentials()['host']}")
    logger.info(f"   CORS Origins: {len(cors_origins)} configured")
    logger.info("=" * 60)


# Call startup logging immediately
log_startup_info()


# Global error handlers
@app.errorhandler(404)
def not_found(error):
    """Handle 404 errors"""
    return jsonify({
        'success': False,
        'error': 'Endpoint not found',
        'path': error.description if hasattr(error, 'description') else 'Unknown'
    }), 404


@app.errorhandler(500)
def internal_error(error):
    """Handle 500 errors"""
    logger.error(f"Internal server error: {error}")
    return jsonify({
        'success': False,
        'error': 'Internal server error'
    }), 500


@app.errorhandler(Exception)
def handle_exception(e):
    """Handle all unhandled exceptions"""
    logger.error(f"Unhandled exception: {e}", exc_info=True)
    return jsonify({
        'success': False,
        'error': 'An unexpected error occurred'
    }), 500


# Graceful shutdown handler
def signal_handler(sig, frame):
    """Handle graceful shutdown on SIGINT/SIGTERM"""
    logger.info("🛑 Shutdown signal received, closing database pool...")
    db.close_pool()
    logger.info("✅ Graceful shutdown complete")
    sys.exit(0)


# Register signal handlers
signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)


# Main entry point
if __name__ == '__main__':
    # Get backend configuration
    backend_config = config.get_backend_config()
    development_config = backend_config.get('development', {})

    host = development_config.get('host', '0.0.0.0')
    port = development_config.get('port', 5000)
    debug = backend_config.get('debug', True)
    use_reloader = backend_config.get('reloader', False)
    threaded = backend_config.get('threading', True)

    logger.info(f"🌐 Starting Flask server on {host}:{port}")
    logger.info(f"   Debug: {debug}")
    logger.info(f"   Threaded: {threaded}")
    logger.info(f"   Reloader: {use_reloader}")

    try:
        app.run(
            host=host,
            port=port,
            debug=debug,
            use_reloader=use_reloader,
            threaded=threaded
        )
    except Exception as e:
        logger.error(f"❌ Failed to start server: {e}")
        db.close_pool()
        sys.exit(1)
