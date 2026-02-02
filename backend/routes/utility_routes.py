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
        # Validate table name to prevent SQL injection
        import re
        if not re.match(r'^[a-zA-Z0-9_]+$', table_name):
            logger.error(f"❌ Invalid table name format: {table_name}")
            return jsonify({'success': False, 'error': 'Invalid table name format'}), 400

        conn = get_db_connection()
        if not conn:
            logger.error("❌ Database connection failed")
            return jsonify({'success': False, 'error': 'Database connection failed'}), 500

        cursor = conn.cursor()

        # First check if table exists
        check_query = """
            SELECT EXISTS (
                SELECT FROM information_schema.tables
                WHERE table_schema = 'public'
                AND table_name = %s
            )
        """
        cursor.execute(check_query, (table_name.lower(),))
        table_exists = cursor.fetchone()[0]

        if not table_exists:
            logger.error(f"❌ Table {table_name} does not exist in public schema")
            cursor.close()
            release_db_connection(conn)
            return jsonify({'success': False, 'error': f'Table {table_name} not found'}), 404

        logger.info(f"✅ Table {table_name} exists, fetching columns...")

        # Use direct query to get column names - more reliable than information_schema
        # Table name is validated above, so f-string is safe here
        query = f"SELECT * FROM {table_name} LIMIT 0"

        logger.info(f"Executing query: {query}")
        cursor.execute(query)
        columns = [desc[0] for desc in cursor.description]

        cursor.close()
        release_db_connection(conn)

        logger.info(f"✅ Found {len(columns)} columns: {columns}")

        if columns:
            return jsonify({
                'success': True,
                'columns': columns
            })
        else:
            logger.error("❌ No columns found")
            return jsonify({'success': False, 'error': 'No columns found'}), 404

    except Exception as e:
        logger.error(f"❌ Error fetching table columns: {e}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        return jsonify({'success': False, 'error': str(e)}), 500
