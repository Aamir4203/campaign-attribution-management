"""
Authentication Routes for CAM Application
Handles user login, logout, and session management
"""

from flask import Blueprint, jsonify, request
from datetime import datetime, timedelta
import logging
from db import get_db_connection, release_db_connection
from config.config import get_config

logger = logging.getLogger(__name__)
config = get_config()

# Create blueprint
auth_bp = Blueprint('auth', __name__)

# In-memory session storage (for simple session management)
active_sessions = {}


def cleanup_expired_sessions():
    """Clean up expired sessions"""
    current_time = datetime.utcnow()
    expired_tokens = [
        token for token, session in active_sessions.items()
        if session['expires_at'] < current_time
    ]
    for token in expired_tokens:
        del active_sessions[token]
    if expired_tokens:
        logger.info(f"Cleaned up {len(expired_tokens)} expired sessions")


@auth_bp.route('/api/login', methods=['POST'])
def login():
    """User login - create a new session"""
    try:
        data = request.get_json()

        # Validate input
        if not data or 'username' not in data or 'password' not in data:
            return jsonify({'success': False, 'message': 'Username and password are required'}), 400

        username = data['username']
        password = data['password']

        # For development, allow admin/password directly
        if username == 'admin' and password == 'password':
            return jsonify({
                'success': True,
                'message': 'Login successful',
                'token': 'admin-token-please-change',
                'expires_in': 3600
            })

        # Get database connection
        conn = get_db_connection()
        if not conn:
            return jsonify({'success': False, 'message': 'Database connection failed'}), 500

        cursor = conn.cursor()

        # Check user credentials
        users_table = config.get_table_name('users')

        # Check user credentials using correct column names: id, username, password
        cursor.execute(
            f"SELECT id, username FROM {users_table} WHERE username = %s AND password = %s",
            (username, password)
        )
        user = cursor.fetchone()

        if not user:
            cursor.close()
            release_db_connection(conn)
            return jsonify({'success': False, 'message': 'Invalid username or password'}), 401

        # Create a new session
        session_id = f"session-{user[0]}-{int(datetime.utcnow().timestamp())}"
        active_sessions[session_id] = {
            'user_id': user[0],
            'username': user[1],
            'expires_at': datetime.utcnow() + timedelta(hours=48)  # 48-hour expiration
        }

        cursor.close()
        release_db_connection(conn)

        return jsonify({
            'success': True,
            'message': 'Login successful',
            'token': session_id,
            'expires_in': 172800  # 48 hours in seconds
        })

    except Exception as e:
        logger.error(f"Error during login: {e}")
        return jsonify({'success': False, 'message': 'Login failed'}), 500


@auth_bp.route('/api/logout', methods=['POST'])
def logout():
    """User logout - destroy the session"""
    try:
        data = request.get_json()
        token = data.get('token')

        if not token or token not in active_sessions:
            return jsonify({'success': False, 'message': 'Invalid or expired token'}), 401

        # Remove the session
        del active_sessions[token]

        return jsonify({
            'success': True,
            'message': 'Logout successful'
        })

    except Exception as e:
        logger.error(f"Error during logout: {e}")
        return jsonify({'success': False, 'message': 'Logout failed'}), 500


@auth_bp.route('/api/session_info', methods=['GET'])
def session_info():
    """Get current session information"""
    try:
        # Clean up expired sessions first
        cleanup_expired_sessions()

        token = request.headers.get('Authorization')

        if not token or token not in active_sessions:
            return jsonify({'success': False, 'message': 'Invalid or expired token'}), 401

        session = active_sessions[token]

        # Check if session has expired
        if session['expires_at'] < datetime.utcnow():
            del active_sessions[token]
            return jsonify({'success': False, 'message': 'Session expired'}), 401

        return jsonify({
            'success': True,
            'user_id': session['user_id'],
            'username': session['username'],
            'expires_at': session['expires_at'].isoformat()
        })

    except Exception as e:
        logger.error(f"Error fetching session info: {e}")
        return jsonify({'success': False, 'message': 'Failed to get session info'}), 500
