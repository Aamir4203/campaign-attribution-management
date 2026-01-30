"""
Snowflake Upload Routes for CAM Application
Handles Snowflake upload operations, progress tracking, and status management
"""

from flask import Blueprint, jsonify, request
import logging
import threading
from datetime import datetime
from db import get_db_connection, release_db_connection
from config.config import get_config
from services.snowflake_service import SnowflakeService
from utils.file_generator import FileGenerator
from utils.progress_tracker import get_progress_tracker

logger = logging.getLogger(__name__)
config = get_config()

# Create blueprint
snowflake_bp = Blueprint('snowflake', __name__)

# Progress tracker
progress_tracker = get_progress_tracker()

# Upload concurrency limiter (semaphore to prevent RAM exhaustion)
sf_config = config.get_snowflake_config()
max_concurrent = sf_config['upload'].get('max_concurrent_uploads', 2)
upload_semaphore = threading.Semaphore(max_concurrent)
active_uploads_count = 0
active_uploads_lock = threading.Lock()

logger.info(f"🔒 Snowflake upload concurrency limit: {max_concurrent} simultaneous uploads")


# Note: This endpoint is deprecated - frontend now uses /api/tables/<table_name>/columns
# Keeping for backwards compatibility
@snowflake_bp.route('/api/snowflake/columns/<int:request_id>', methods=['GET'])
def get_postback_columns(request_id):
    """Get available columns from postback table (DEPRECATED - use /api/tables/<table_name>/columns)"""
    logger.info(f"📊 Get columns endpoint called for request ID: {request_id}")

    try:
        # Get client name and week from request
        client_name = request.args.get('client_name')
        week = request.args.get('week')

        logger.info(f"Parameters received - client_name: {client_name}, week: {week}")

        if not client_name or not week:
            error_msg = 'client_name and week parameters are required'
            logger.error(f"❌ {error_msg}")
            return jsonify({
                'success': False,
                'error': error_msg
            }), 400

        # Generate table name - use same format as MetricsModal (no lowercase)
        table_name = f"apt_custom_{request_id}_{client_name}_{week}_postback_table"
        logger.info(f"Generated table name: {table_name}")

        # Get columns
        file_generator = FileGenerator()
        all_columns = file_generator.get_table_columns(table_name)

        logger.info(f"Retrieved {len(all_columns)} columns from table")

        if not all_columns:
            error_msg = f'Table {table_name} not found or has no columns'
            logger.error(f"❌ {error_msg}")
            return jsonify({
                'success': False,
                'error': error_msg
            }), 404

        # Get standard and excluded columns
        standard_header_defs = file_generator.get_standard_header_columns()
        standard_columns = [col['name'] for col in standard_header_defs]
        excluded_columns = file_generator.get_excluded_columns()

        # Extract source column names from standard header expressions
        # These are the actual DB columns used in the standard header (with aliases)
        source_columns_in_standard = []
        for col_def in standard_header_defs:
            expr = col_def['expr']
            # Extract simple column names (not case expressions)
            if not expr.startswith('(case') and expr != col_def['name']:
                source_columns_in_standard.append(expr.lower())

        # Additional known source columns from case expressions
        source_columns_in_standard.append('flag')  # used in DeliveredFlag case expression

        logger.info(f"Standard columns: {standard_columns}")
        logger.info(f"Source columns in standard header: {source_columns_in_standard}")
        logger.info(f"Excluded columns: {excluded_columns}")

        # Combine all columns to exclude
        all_excluded = (
            [sc.lower() for sc in standard_columns] +
            [ec.lower() for ec in excluded_columns] +
            source_columns_in_standard
        )

        # Filter available custom columns
        available_custom_columns = [
            col for col in all_columns
            if col.lower() not in all_excluded
        ]

        logger.info(f"✅ Found {len(available_custom_columns)} custom columns: {available_custom_columns}")

        return jsonify({
            'success': True,
            'columns': {
                'standard': standard_columns,
                'custom': available_custom_columns,
                'excluded': excluded_columns
            }
        })

    except Exception as e:
        logger.error(f"❌ Error getting columns: {e}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@snowflake_bp.route('/api/snowflake/upload/<int:request_id>', methods=['POST'])
def start_snowflake_upload(request_id):
    """Start Snowflake upload process"""
    logger.info(f"🚀 Start upload endpoint called for request ID: {request_id}")

    try:
        data = request.get_json()

        client_name = data.get('client_name')
        week = data.get('week')
        header_type = data.get('header_type', 'standard')  # 'standard' or 'custom'
        custom_columns = data.get('custom_columns', [])

        if not client_name or not week:
            return jsonify({
                'success': False,
                'error': 'client_name and week are required'
            }), 400

        # Check concurrent upload limit
        global active_uploads_count
        with active_uploads_lock:
            if active_uploads_count >= max_concurrent:
                logger.warning(f"⚠️ Upload limit reached: {active_uploads_count}/{max_concurrent} active uploads")
                return jsonify({
                    'success': False,
                    'error': f'Maximum concurrent uploads ({max_concurrent}) reached. Please wait for an upload to complete.'
                }), 429  # 429 Too Many Requests

        # Generate task ID
        task_id = f"sf_upload_{request_id}_{datetime.now().strftime('%Y%m%d%H%M%S')}"

        # Create progress task
        progress_tracker.create_task(
            task_id=task_id,
            total_steps=100,
            description=f"Uploading to Snowflake - Request {request_id}"
        )

        # Start upload in background thread
        upload_thread = threading.Thread(
            target=_process_snowflake_upload,
            args=(task_id, request_id, client_name, week, header_type, custom_columns)
        )
        upload_thread.daemon = True
        upload_thread.start()

        with active_uploads_lock:
            active_uploads_count += 1

        logger.info(f"✅ Upload task {task_id} started ({active_uploads_count}/{max_concurrent} active)")

        return jsonify({
            'success': True,
            'task_id': task_id,
            'message': 'Upload started successfully'
        })

    except Exception as e:
        logger.error(f"❌ Error starting upload: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@snowflake_bp.route('/api/snowflake/progress/<task_id>', methods=['GET'])
def get_upload_progress(task_id):
    """Get progress of an upload task"""
    try:
        task_status = progress_tracker.get_task_status(task_id)

        if not task_status:
            return jsonify({
                'success': False,
                'error': 'Task not found'
            }), 404

        return jsonify({
            'success': True,
            'task': task_status
        })

    except Exception as e:
        logger.error(f"❌ Error getting progress: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


def _process_snowflake_upload(task_id: str, request_id: int, client_name: str,
                               week: str, header_type: str, custom_columns: list):
    """
    Background process to handle Snowflake upload

    Args:
        task_id: Progress tracker task ID
        request_id: Request ID
        client_name: Client name
        week: Week identifier
        header_type: 'standard' or 'custom'
        custom_columns: List of custom columns to include
    """
    file_path = None

    try:
        logger.info(f"🔄 Processing Snowflake upload for task {task_id}")

        # Step 1: Generate file (0-50%)
        progress_tracker.update_progress(task_id, 5, "Generating file from database...")

        file_generator = FileGenerator()

        def file_progress_callback(progress):
            """Callback to update file generation progress"""
            # Map file generation progress to 5-50% of total
            total_progress = 5 + int(progress * 0.45)
            progress_tracker.update_progress(
                task_id,
                total_progress,
                f"Writing data... ({progress}%)"
            )

        # Determine columns to include
        include_standard = (header_type == 'standard' or header_type == 'custom')

        file_result = file_generator.generate_file(
            request_id=request_id,
            client_name=client_name,
            week=week,
            custom_columns=custom_columns if header_type == 'custom' else None,
            include_standard=include_standard,
            progress_callback=file_progress_callback
        )

        if not file_result['success']:
            raise Exception(f"File generation failed: {', '.join(file_result['errors'])}")

        file_path = file_result['file_path']
        logger.info(f"✅ File generated: {file_path} ({file_result['row_count']} rows)")

        # Step 2: Connect to Snowflake (50-55%)
        progress_tracker.update_progress(task_id, 50, "Connecting to Snowflake...")

        sf_service = SnowflakeService()
        sf_service.connect()

        progress_tracker.update_progress(task_id, 55, "Connected to Snowflake")

        # Step 3: Create table (55-65%)
        progress_tracker.update_progress(task_id, 55, "Creating Snowflake table...")

        table_name = sf_service.generate_table_name(client_name, week)

        # Determine all columns for table creation
        all_columns = []

        if include_standard:
            standard_cols = file_generator.get_standard_header_columns()
            all_columns.extend([col['name'] for col in standard_cols])

        if custom_columns:
            all_columns.extend(custom_columns)

        # Generate column definitions
        column_defs = file_generator.get_column_definitions(all_columns)

        # Create table
        table_created = sf_service.create_table(table_name, column_defs)

        if not table_created:
            raise Exception("Failed to create Snowflake table")

        progress_tracker.update_progress(task_id, 65, f"Table {table_name} created")

        # Step 4: Upload file to Snowflake (65-95%)
        progress_tracker.update_progress(task_id, 65, "Uploading file to Snowflake...")

        upload_result = sf_service.upload_file_to_snowflake(file_path, table_name)

        if not upload_result['success']:
            raise Exception(f"Snowflake upload failed: {', '.join(upload_result['errors'])}")

        progress_tracker.update_progress(
            task_id,
            95,
            f"Data uploaded: {upload_result['rows_loaded']} rows"
        )

        # Step 5: Verify upload (95-100%)
        progress_tracker.update_progress(task_id, 95, "Verifying upload...")

        row_count = sf_service.get_row_count(table_name)

        logger.info(f"🔍 Row count validation: {row_count:,} rows in Snowflake table")

        # Validate row counts match
        if row_count == upload_result['rows_loaded']:
            logger.info(f"✅ Validation successful: Row counts match")
        else:
            logger.warning(f"⚠️ Row count mismatch: {upload_result['rows_loaded']:,} uploaded vs {row_count:,} in table")

        # Complete task
        progress_tracker.complete_task(task_id, {
            'table_name': table_name,
            'rows_uploaded': upload_result['rows_loaded'],
            'rows_verified': row_count,
            'file_size': file_result.get('file_size', 0)
        })

        file_size_mb = file_result.get('file_size', 0) / (1024 * 1024)
        logger.info(f"🎉 Upload completed successfully: {row_count:,} rows, {file_size_mb:.2f} MB → {table_name}")

        # Update database with successful upload status
        try:
            conn = get_db_connection()
            if conn:
                cursor = conn.cursor()
                requests_table = config.get_table_name('requests')

                update_sql = f"""
                    UPDATE {requests_table}
                    SET sf_upload_status = 'success',
                        sf_table_name = %s,
                        sf_upload_time = NOW()
                    WHERE request_id = %s
                """

                cursor.execute(update_sql, (table_name, request_id))
                conn.commit()
                cursor.close()
                release_db_connection(conn)

                logger.info(f"✅ Updated database with upload status for request {request_id}")
        except Exception as db_error:
            logger.error(f"⚠️ Failed to update database with upload status: {db_error}")

    except Exception as e:
        logger.error(f"❌ Upload task {task_id} failed: {e}")
        progress_tracker.fail_task(task_id, str(e))

        # Update database with failed upload status (store error in request_desc)
        try:
            conn = get_db_connection()
            if conn:
                cursor = conn.cursor()
                requests_table = config.get_table_name('requests')

                error_message = f"Snowflake upload failed: {str(e)[:450]}"

                update_sql = f"""
                    UPDATE {requests_table}
                    SET sf_upload_status = 'failed',
                        sf_upload_time = NOW(),
                        request_desc = %s
                    WHERE request_id = %s
                """

                cursor.execute(update_sql, (error_message, request_id))
                conn.commit()
                cursor.close()
                release_db_connection(conn)

                logger.info(f"✅ Updated database with failed status for request {request_id}")
        except Exception as db_error:
            logger.error(f"⚠️ Failed to update database with failed status: {db_error}")

    finally:
        # Decrement active upload counter
        global active_uploads_count
        with active_uploads_lock:
            active_uploads_count -= 1
            logger.info(f"📊 Upload slot released ({active_uploads_count}/{max_concurrent} active)")

        # Clean up temporary file
        if file_path:
            try:
                file_generator = FileGenerator()
                file_generator.cleanup_file(file_path)
            except Exception as cleanup_error:
                logger.warning(f"Failed to cleanup file: {cleanup_error}")

        # Disconnect from Snowflake
        try:
            if 'sf_service' in locals():
                sf_service.disconnect()
        except Exception as disconnect_error:
            logger.warning(f"Failed to disconnect from Snowflake: {disconnect_error}")


@snowflake_bp.route('/api/snowflake/test-connection', methods=['GET'])
def test_snowflake_connection():
    """Test Snowflake connection"""
    logger.info("🔌 Testing Snowflake connection...")

    try:
        sf_service = SnowflakeService()
        conn = sf_service.connect()

        if conn and not conn.is_closed():
            sf_service.disconnect()

            return jsonify({
                'success': True,
                'message': 'Snowflake connection successful',
                'account': sf_service.account,
                'database': sf_service.database,
                'schema': sf_service.schema
            })
        else:
            return jsonify({
                'success': False,
                'error': 'Failed to establish connection'
            }), 500

    except Exception as e:
        logger.error(f"❌ Connection test failed: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@snowflake_bp.route('/api/snowflake/upload-status/<int:request_id>', methods=['GET'])
def get_upload_status(request_id):
    """Get Snowflake upload status for a request"""
    logger.info(f"📊 Get upload status for request: {request_id}")

    try:
        conn = get_db_connection()
        if not conn:
            return jsonify({
                'success': False,
                'error': 'Database connection failed'
            }), 500

        cursor = conn.cursor()
        requests_table = config.get_table_name('requests')

        query = f"""
            SELECT sf_upload_status, sf_table_name, sf_upload_time, request_desc
            FROM {requests_table}
            WHERE request_id = %s
        """

        cursor.execute(query, (request_id,))
        result = cursor.fetchone()

        cursor.close()
        release_db_connection(conn)

        if not result:
            return jsonify({
                'success': False,
                'error': 'Request not found'
            }), 404

        upload_status = {
            'status': result[0],  # NULL, 'success', 'failed'
            'table_name': result[1],
            'upload_time': result[2].isoformat() if result[2] else None,
            'error': result[3] if result[0] == 'failed' else None  # request_desc contains error for failed uploads
        }

        logger.info(f"✅ Upload status for request {request_id}: {upload_status['status']}")

        return jsonify({
            'success': True,
            'upload_status': upload_status
        })

    except Exception as e:
        logger.error(f"❌ Error getting upload status: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@snowflake_bp.route('/api/snowflake/cancel/<task_id>', methods=['POST'])
def cancel_upload(task_id):
    """Cancel an ongoing upload task"""
    logger.info(f"🛑 Cancel requested for task: {task_id}")

    try:
        task_status = progress_tracker.get_task_status(task_id)

        if not task_status:
            return jsonify({
                'success': False,
                'error': 'Task not found'
            }), 404

        if task_status['status'] in ['completed', 'failed']:
            return jsonify({
                'success': False,
                'error': 'Task already finished'
            }), 400

        # Mark task as failed with cancellation message
        progress_tracker.fail_task(task_id, "Upload cancelled by user")

        return jsonify({
            'success': True,
            'message': 'Upload cancelled'
        })

    except Exception as e:
        logger.error(f"❌ Error cancelling task: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500
