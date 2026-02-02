"""
Client Routes for CAM Application
Handles client management and delivery data operations
"""

from flask import Blueprint, jsonify, request
import logging
from db import get_db_connection, release_db_connection
from config.config import get_config

logger = logging.getLogger(__name__)
config = get_config()

# Create blueprint
client_bp = Blueprint('client', __name__)


@client_bp.route('/api/clients', methods=['GET'])
def get_clients():
    """Get all clients for dropdown"""
    try:
        conn = get_db_connection()
        if not conn:
            return jsonify({
                'success': False,
                'error': 'Database connection failed'
            }), 500

        cursor = conn.cursor()
        clients_table = config.get_table_name('clients')
        query = f"""
            SELECT lower(client_name) as client_name
            FROM {clients_table}
            ORDER BY client_name
        """

        cursor.execute(query)
        results = cursor.fetchall()

        clients = [{'client_name': row[0]} for row in results]
        cursor.close()
        release_db_connection(conn)

        return jsonify({
            'success': True,
            'clients': clients
        })

    except Exception as e:
        logger.error(f"Error fetching clients: {e}")
        return jsonify({
            'success': False,
            'error': 'Failed to fetch clients from database'
        }), 500


@client_bp.route('/check_client', methods=['POST'])
def check_client():
    """Check if client exists in database"""
    try:
        data = request.get_json()
        if not data or 'client_name' not in data:
            return jsonify({'error': 'client_name is required'}), 400

        client_name = data['client_name'].strip()

        conn = get_db_connection()
        if not conn:
            return jsonify({
                'exists': False,
                'message': 'Database connection unavailable'
            })

        cursor = conn.cursor()
        clients_table = config.get_table_name('clients')
        cursor.execute(
            f"SELECT client_id FROM {clients_table} WHERE LOWER(client_name) = LOWER(%s)",
            (client_name,)
        )
        result = cursor.fetchone()

        cursor.close()
        release_db_connection(conn)

        return jsonify({
            'exists': bool(result),
            'client_id': result[0] if result else None
        })

    except Exception as e:
        logger.error(f"Error checking client: {e}")
        return jsonify({'error': 'Failed to check client'}), 500


@client_bp.route('/add_client', methods=['POST'])
def add_client():
    """Add new client to database - replicates addClient.sh script logic"""
    try:
        data = request.get_json()
        if not data or 'client_name' not in data:
            return jsonify({'error': 'client_name is required'}), 400

        client_name = data['client_name'].strip().upper()  # Script converts to uppercase
        if not client_name:
            return jsonify({'error': 'client_name cannot be empty'}), 400

        logger.info(f"📝 Adding new client: {client_name}")

        conn = get_db_connection()
        if not conn:
            return jsonify({
                'success': False,
                'message': 'Database connection unavailable'
            }), 500

        cursor = conn.cursor()
        clients_table = config.get_table_name('clients')

        # Check if client already exists
        cursor.execute(
            f"SELECT client_id FROM {clients_table} WHERE LOWER(client_name) = LOWER(%s)",
            (client_name,)
        )
        existing = cursor.fetchone()

        if existing:
            cursor.close()
            release_db_connection(conn)
            logger.warning(f"⚠️ Client {client_name} already exists")
            return jsonify({
                'success': False,
                'message': f'Client "{client_name}" already exists'
            })

        # Generate table names (matching addClient.sh script pattern)
        total_delivered_table = f"apt_custom_{client_name.lower()}_total_delivered_dnd"
        posted_unsub_table = f"apt_custom_{client_name.lower()}_posted_unsub_dnd"
        prev_postback_table = f"apt_adhoc_{client_name.lower()}_prev_postback_dnd"

        logger.info(f"📊 Creating tables for client {client_name}")
        logger.info(f"  - Total Delivered: {total_delivered_table}")
        logger.info(f"  - Posted Unsub: {posted_unsub_table}")
        logger.info(f"  - Prev Postback: {prev_postback_table}")

        try:
            # Create total delivered table
            cursor.execute(f"""
                CREATE TABLE {total_delivered_table} (
                    email VARCHAR UNIQUE,
                    segment VARCHAR,
                    del_date VARCHAR,
                    week VARCHAR DEFAULT '#',
                    touch INT DEFAULT 0
                )
            """)
            logger.info(f"✅ Created table: {total_delivered_table}")

            # Create posted unsub/hards table
            cursor.execute(f"""
                CREATE TABLE {posted_unsub_table} (
                    email VARCHAR UNIQUE,
                    segment VARCHAR,
                    del_date VARCHAR,
                    unsub_date VARCHAR,
                    flag VARCHAR
                )
            """)
            logger.info(f"✅ Created table: {posted_unsub_table}")

            # Create previous postback table
            cursor.execute(f"""
                CREATE TABLE {prev_postback_table} (
                    email VARCHAR UNIQUE,
                    del_date VARCHAR,
                    open_date VARCHAR,
                    click_date VARCHAR,
                    unsub_date VARCHAR,
                    segment VARCHAR,
                    flag VARCHAR
                )
            """)
            logger.info(f"✅ Created table: {prev_postback_table}")

            # Insert client record with table references
            cursor.execute(f"""
                INSERT INTO {clients_table} (
                    client_name,
                    total_delivered_table,
                    posted_unsub_hards_table,
                    prev_week_pb_table,
                    bkp_prev_pb_table
                ) VALUES (%s, %s, %s, %s, %s)
                RETURNING client_id
            """, (
                client_name,
                total_delivered_table,
                posted_unsub_table,
                prev_postback_table,
                prev_postback_table  # bkp uses same as prev
            ))

            client_id = cursor.fetchone()[0]
            conn.commit()

            logger.info(f"✅ Client '{client_name}' added successfully with ID: {client_id}")

            cursor.close()
            release_db_connection(conn)

            return jsonify({
                'success': True,
                'client_id': client_id,
                'message': f'Client "{client_name}" added successfully',
                'tables_created': {
                    'total_delivered': total_delivered_table,
                    'posted_unsub': posted_unsub_table,
                    'prev_postback': prev_postback_table
                }
            })

        except Exception as table_error:
            conn.rollback()
            cursor.close()
            release_db_connection(conn)
            logger.error(f"❌ Failed to create tables: {table_error}")
            return jsonify({
                'success': False,
                'message': f'Failed to create tables: {str(table_error)}'
            }), 500

    except Exception as e:
        logger.error(f"❌ Error adding client: {e}")
        return jsonify({
            'success': False,
            'message': f'Failed to add client: {str(e)}'
        }), 500


@client_bp.route('/api/clients/<client_name>/flush-delivery-data', methods=['POST'])
def flush_client_delivery_data(client_name):
    """Flush (truncate) total delivery data for a client when week contains W1/W2"""
    logger.info(f"🗑️ Flush delivery data request for client: {client_name}")

    try:
        # Get database connection
        conn = get_db_connection()
        if not conn:
            logger.error("❌ Database connection failed for flush operation")
            return jsonify({
                'success': False,
                'error': 'Database connection failed'
            }), 500

        cursor = conn.cursor()
        clients_table = config.get_table_name('clients')

        logger.info(f"🔍 Looking up client '{client_name}' in table: {clients_table}")

        # First, let's check what clients exist (for debugging)
        debug_query = f"SELECT client_id, client_name, total_delivered_table FROM {clients_table} LIMIT 10"
        cursor.execute(debug_query)
        all_clients = cursor.fetchall()
        logger.info(f"📋 Available clients (first 10): {[client[1] for client in all_clients]}")

        # Get client information including total_delivered_table
        query = f"""
        SELECT client_id, client_name, total_delivered_table
        FROM {clients_table}
        WHERE LOWER(client_name) = LOWER(%s)
        """

        logger.info(f"🔍 Executing query: {query} with parameter: {client_name}")
        cursor.execute(query, (client_name,))
        result = cursor.fetchone()

        if not result:
            cursor.close()
            release_db_connection(conn)
            logger.error(f"❌ Client '{client_name}' not found in database")
            logger.info(f"💡 Available clients: {[client[1] for client in all_clients]}")
            return jsonify({
                'success': False,
                'error': f'Client "{client_name}" not found. Available clients: {[client[1] for client in all_clients[:5]]}'
            }), 404

        client_id, client_name_db, total_delivered_table = result
        logger.info(f"✅ Found client: ID={client_id}, Name='{client_name_db}', Table='{total_delivered_table}'")

        if not total_delivered_table:
            cursor.close()
            release_db_connection(conn)
            logger.error(f"❌ No total delivered table configured for client '{client_name}'")
            return jsonify({
                'success': False,
                'error': f'No total delivered table configured for client "{client_name}"'
            }), 400

        # Log the operation
        logger.info(f"📊 Client ID: {client_id}, Table to flush: {total_delivered_table}")

        # Check if table exists before truncating
        check_table_query = """
        SELECT EXISTS (
            SELECT FROM information_schema.tables
            WHERE table_schema = 'public'
            AND table_name = LOWER(%s)
        )
        """
        cursor.execute(check_table_query, (total_delivered_table,))
        table_exists = cursor.fetchone()[0]

        if not table_exists:
            cursor.close()
            release_db_connection(conn)
            logger.error(f"❌ Total delivered table '{total_delivered_table}' does not exist")
            return jsonify({
                'success': False,
                'error': f'Total delivered table "{total_delivered_table}" does not exist'
            }), 400

        # Get row count before truncation
        count_query = f"SELECT COUNT(*) FROM {total_delivered_table}"
        cursor.execute(count_query)
        row_count_before = cursor.fetchone()[0]
        logger.info(f"📊 Records to flush: {row_count_before}")

        # Truncate the table
        truncate_query = f"TRUNCATE TABLE {total_delivered_table}"
        logger.info(f"🗑️ Executing: {truncate_query}")
        cursor.execute(truncate_query)

        # Commit the transaction
        conn.commit()
        cursor.close()
        release_db_connection(conn)

        logger.info(f"✅ Successfully flushed {row_count_before} records from {total_delivered_table}")

        return jsonify({
            'success': True,
            'message': f'Successfully flushed total delivery data for client "{client_name}"',
            'details': {
                'client_id': client_id,
                'table_name': total_delivered_table,
                'records_flushed': row_count_before
            }
        })

    except Exception as e:
        logger.error(f"❌ Error flushing delivery data: {e}")
        logger.error(f"❌ Error details: {str(e)}")
        return jsonify({
            'success': False,
            'error': f'Failed to flush delivery data: {str(e)}'
        }), 500
