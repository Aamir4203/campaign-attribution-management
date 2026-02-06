"""
Automation API routes - Emergency stop and status endpoints
"""
from flask import Blueprint, jsonify
import logging
from services import automation

logger = logging.getLogger(__name__)

automation_bp = Blueprint('automation', __name__)


@automation_bp.route('/api/automation/status', methods=['GET'])
def get_status():
    """Get automation status"""
    try:
        status = automation.status()
        return jsonify({
            'success': True,
            'automation': status
        })
    except Exception as e:
        logger.error(f"Error getting automation status: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@automation_bp.route('/api/automation/stop', methods=['POST'])
def stop_automation():
    """Emergency stop endpoint"""
    try:
        success = automation.stop()
        if success:
            return jsonify({
                'success': True,
                'message': 'Automation stopped'
            })
        else:
            return jsonify({
                'success': False,
                'message': 'Automation was not running'
            })
    except Exception as e:
        logger.error(f"Error stopping automation: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500
