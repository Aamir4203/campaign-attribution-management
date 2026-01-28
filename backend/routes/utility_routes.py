"""
Utility Routes for CAM Application
Handles health checks and table metadata endpoints
"""

from flask import Blueprint, jsonify
from datetime import datetime
import logging
from db import get_db_connection, release_db_connection

logger = logging.getLogger(__name__)

# Create blueprint
utility_bp = Blueprint('utility', __name__)


@utility_bp.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.utcnow().isoformat(),
        'service': 'CAM API'
    })


@utility_bp.route('/api/tables/<table_name>/columns', methods=['GET'])
def get_table_columns(table_name):
    """Get columns for a specific table"""
    logger.info(f"📋 Table columns endpoint called for table: {table_name}")

    try:
        conn = get_db_connection()
        if not conn:
            return jsonify({'success': False, 'error': 'Database connection failed'}), 500

        cursor = conn.cursor()

        # Get table columns from information_schema
        query = """
        SELECT column_name
        FROM information_schema.columns
        WHERE table_name = %s
        ORDER BY ordinal_position
        """

        cursor.execute(query, (table_name.lower(),))
        results = cursor.fetchall()

        cursor.close()
        release_db_connection(conn)

        if results:
            columns = [row[0] for row in results]
            return jsonify({
                'success': True,
                'columns': columns
            })
        else:
            return jsonify({'success': False, 'error': 'Table not found or no columns'}), 404

    except Exception as e:
        logger.error(f"❌ Error fetching table columns: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500
