"""
Request Routes for CAM Application
Handles request management, CRUD operations, and statistics
"""

from flask import Blueprint, jsonify, request, current_app as app, make_response
from datetime import datetime, timedelta
import logging
import subprocess
import os
from db import get_db_connection, release_db_connection
from config.config import get_config

logger = logging.getLogger(__name__)
config = get_config()

# Create blueprint
request_bp = Blueprint('request', __name__)


@request_bp.route('/api/requests', methods=['GET'])
def get_requests():
    """Get all requests with pagination and search"""
    try:
        # Get pagination config
        pagination_config = config.get_app_constants().get('pagination', {})
        default_page_size = pagination_config.get('defaultPageSize', 50)
        max_page_size = pagination_config.get('maxPageSize', 500)

        # Get query parameters
        page = int(request.args.get('page', 1))
        limit = min(int(request.args.get('limit', default_page_size)), max_page_size)
        search_term = request.args.get('search', '').strip()

        offset = (page - 1) * limit

        # Get database connection
        conn = get_db_connection()
        if not conn:
            return jsonify({
                'success': False,
                'error': 'Database connection failed'
            }), 500

        cursor = conn.cursor()
        requests_table = config.get_table_name('requests')
        clients_table = config.get_table_name('clients')
        qa_table = config.get_table_name('qa_stats')

        # Base query
        base_query = f"""
        SELECT
            a.request_id,
            lower(b.client_name) as client_name,
            lower(a.week) as week,
            lower(a.added_by) as added_by,
            COALESCE(c.rltp_file_count, 0) as trt_count,
            a.request_status,
            a.request_desc,
            COALESCE(a.execution_time, '-') as execution_time,
            a.request_validation,
            a.sf_upload_status,
            a.sf_table_name,
            a.sf_upload_time
        FROM {requests_table} a
        JOIN {clients_table} b ON a.client_id = b.client_id
        LEFT JOIN {qa_table} c ON a.request_id = c.request_id
        """

        # Add search conditions if search term provided
        where_clause = ""
        search_params = []
        if search_term:
            where_clause = """
            WHERE (
                CAST(a.request_id AS VARCHAR) ILIKE %s OR
                b.client_name ILIKE %s OR
                a.added_by ILIKE %s
            )
            """
            search_pattern = f"%{search_term}%"
            search_params = [search_pattern, search_pattern, search_pattern]

        # Count total records
        count_query = f"SELECT COUNT(*) FROM ({base_query} {where_clause}) as count_query"
        cursor.execute(count_query, search_params)
        total_count = cursor.fetchone()[0]

        # Get paginated requests
        full_query = f"""
        {base_query}
        {where_clause}
        ORDER BY a.request_id DESC
        LIMIT %s OFFSET %s
        """

        query_params = search_params + [limit, offset]
        cursor.execute(full_query, query_params)

        results = cursor.fetchall()

        # Format results
        requests = []
        for row in results:
            requests.append({
                'request_id': row[0],
                'client_name': row[1] or 'Unknown',
                'week': row[2] or '-',
                'added_by': row[3] or '-',
                'trt_count': row[4] or 0,
                'request_status': row[5] or 'W',
                'request_desc': row[6] or 'No description',
                'execution_time': row[7] or '-',
                'request_validation': row[8],  # Y, N, V, or NULL
                'sf_upload_status': row[9],  # NULL, 'success', 'failed'
                'sf_table_name': row[10],
                'sf_upload_time': row[11].isoformat() if row[11] else None
            })

        total_pages = (total_count + limit - 1) // limit

        cursor.close()
        release_db_connection(conn)

        return jsonify({
            'success': True,
            'requests': requests,
            'total': total_count,
            'page': page,
            'totalPages': total_pages,
            'limit': limit
        })

    except Exception as e:
        logger.error(f"Error fetching requests: {e}")
        return jsonify({
            'success': False,
            'error': f'Failed to fetch requests: {str(e)}'
        }), 500


@request_bp.route('/submit_form', methods=['POST'])
def submit_form():
    """Submit campaign attribution request form"""
    try:
        data = request.get_json()

        # Validate required fields
        required_fields = ['clientName', 'addedBy', 'requestType', 'startDate', 'endDate']
        missing_fields = [field for field in required_fields if not data.get(field)]

        if missing_fields:
            return jsonify({
                'success': False,
                'message': f'Missing required fields: {", ".join(missing_fields)}'
            }), 400

        # Validate residual date
        if data.get('residualStart'):
            from datetime import datetime as dt
            try:
                start_date = dt.strptime(data['startDate'], '%Y-%m-%d').date()
                end_date = dt.strptime(data['endDate'], '%Y-%m-%d').date()
                residual_date = dt.strptime(data['residualStart'], '%Y-%m-%d').date()

                if residual_date < end_date:
                    return jsonify({
                        'success': False,
                        'message': 'Residual date must be equal to or greater than end date'
                    }), 400

            except ValueError as ve:
                return jsonify({
                    'success': False,
                    'message': f'Invalid date format: {str(ve)}'
                }), 400

        # Get database connection
        conn = get_db_connection()
        if not conn:
            return jsonify({
                'success': False,
                'message': 'Database connection failed'
            }), 500

        cursor = conn.cursor()

        # Get client_id from client_name
        clients_table = config.get_table_name('clients')
        cursor.execute(
            f"SELECT client_id FROM {clients_table} WHERE LOWER(client_name) = LOWER(%s)",
            (data['clientName'],)
        )
        client_result = cursor.fetchone()

        if not client_result:
            cursor.close()
            release_db_connection(conn)
            return jsonify({
                'success': False,
                'message': f'Client "{data["clientName"]}" not found'
            }), 400

        client_id = client_result[0]

        # Prepare data for insertion
        start_date = data['startDate']
        end_date = data['endDate']
        residual_date = data.get('residualStart') if data.get('residualStart') else None

        # Get default old delivered percentage from configuration
        default_old_percentage = config.get_default_old_percentage()

        # Prepare suppression and priority data
        request_id_suppression = data.get('requestIdSuppressionList', '').strip() if data.get('requestIdSuppression') else None
        priority_file = data.get('priorityFile', '').strip() if data.get('priorityFile') else None
        timestamp_path = data.get('timeStampPath', '').strip() if data.get('addTimeStamp') else None
        priority_file_per = None

        # Process priority file percentage
        if data.get('priorityFilePer') is not None:
            priority_file_per_raw = data.get('priorityFilePer')

            try:
                if isinstance(priority_file_per_raw, str):
                    priority_file_per = int(priority_file_per_raw.strip())
                elif isinstance(priority_file_per_raw, (int, float)):
                    priority_file_per = int(priority_file_per_raw)
                else:
                    priority_file_per = int(float(str(priority_file_per_raw)))

                if priority_file_per < 1 or priority_file_per > 100:
                    priority_file_per = None

            except (ValueError, TypeError):
                priority_file_per = None

        # Insert into postback request details table
        requests_table = config.get_table_name('requests')
        insert_query = f"""
        INSERT INTO {requests_table}
        (client_id, added_by, type, old_delivered_per, unique_decile_report_path,
         from_date, end_date, residual_date, week, timestamp_append, ip_append,
         cpm_report_path, decile_wise_report_path, on_sent, offerid_unsub_supp,
         include_bounce_as_delivered, supp_path, query, request_id_supp,
         priority_file, priority_file_per, timestamp_report_path, created_date)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        RETURNING request_id
        """

        insert_data = (
            client_id,
            data['addedBy'],
            int(data['requestType']),
            default_old_percentage,
            data.get('filePath'),
            start_date,
            end_date,
            residual_date,
            data.get('week', ''),
            'Y' if data.get('addTimeStamp', False) else 'N',
            'Y' if data.get('addIpsLogs', False) else 'N',
            data.get('reportpath'),
            data.get('qspath'),
            'Y' if data.get('fileType') == 'Sent' else 'N',
            'Y' if data.get('offerSuppression', False) else 'N',
            'Y' if data.get('addBounce', False) else 'N',
            data.get('clientSuppressionPath') if data.get('clientSuppression') else None,
            data.get('input_query'),
            request_id_suppression,
            priority_file,
            priority_file_per,
            timestamp_path,
            datetime.now()
        )

        try:
            cursor.execute(insert_query, insert_data)
            request_id = cursor.fetchone()[0]

            conn.commit()
            cursor.close()
            release_db_connection(conn)

            return jsonify({
                'success': True,
                'message': 'Request submitted successfully to CAM database!',
                'request_id': request_id,
                'client_id': client_id,
                'client_name': data['clientName']
            })

        except Exception as db_error:
            conn.rollback()
            cursor.close()
            release_db_connection(conn)

            logger.error(f"Database insertion failed: {str(db_error)}")

            return jsonify({
                'success': False,
                'message': f'Database insertion failed: {str(db_error)}'
            }), 500

    except Exception as e:
        logger.error(f"Error submitting form: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'Failed to process form data: {str(e)}'
        }), 500


@request_bp.route('/add_request', methods=['POST'])
def add_request():
    """Add new campaign attribution request - modern API endpoint"""
    try:
        data = request.get_json()

        # Convert underscore-separated fields to camelCase
        converted_data = {
            'clientName': data.get('client_name'),
            'addedBy': data.get('added_by'),
            'requestType': str(data.get('request_type', '1')),
            'filePath': data.get('file_path'),
            'startDate': data.get('start_date'),
            'endDate': data.get('end_date'),
            'residualStart': data.get('residual_start'),
            'week': data.get('week'),
            'reportpath': data.get('report_path'),
            'qspath': data.get('decile_report_path'),
            'input_query': data.get('query'),
            'addTimeStamp': data.get('timestamp_append') == 'Y',
            'addIpsLogs': data.get('ip_append') == 'Y',
            'offerSuppression': data.get('offerid_unsub_supp') == 'Y',
            'addBounce': data.get('include_bounce_as_delivered') == 'Y',
            'clientSuppression': bool(data.get('supp_path')),
            'clientSuppressionPath': data.get('supp_path', ''),
            'requestIdSuppression': bool(data.get('request_id_supp')),
            'requestIdSuppressionList': data.get('request_id_supp', ''),
            'timeStampPath': data.get('timestamp_report_path', ''),
            'fileType': data.get('file_type', 'Delivered'),
            'priorityFile': data.get('priority_file', ''),
            'priorityFilePer': data.get('priority_file_per')
        }

        # Validate required fields
        required_fields = ['clientName', 'addedBy', 'requestType', 'startDate', 'endDate']
        missing_fields = [field for field in required_fields if not converted_data.get(field)]

        if missing_fields:
            return jsonify({
                'success': False,
                'message': f'Missing required fields: {", ".join(missing_fields)}'
            }), 400

        # Get database connection
        conn = get_db_connection()
        if not conn:
            return jsonify({
                'success': False,
                'message': 'Database connection failed'
            }), 500

        cursor = conn.cursor()

        # Get client_id from client_name
        clients_table = config.get_table_name('clients')
        cursor.execute(
            f"SELECT client_id FROM {clients_table} WHERE LOWER(client_name) = LOWER(%s)",
            (converted_data['clientName'],)
        )
        client_result = cursor.fetchone()

        if not client_result:
            cursor.close()
            release_db_connection(conn)
            return jsonify({
                'success': False,
                'message': f'Client "{converted_data["clientName"]}" not found in database'
            }), 400

        client_id = client_result[0]

        # Insert into requests table
        requests_table = config.get_table_name('requests')

        insert_query = f"""
            INSERT INTO {requests_table} (
                client_id, added_by, type, unique_decile_report_path, from_date, end_date,
                residual_date, week, cpm_report_path, decile_wise_report_path,
                offerid_unsub_supp, include_bounce_as_delivered, supp_path,
                request_id_supp, timestamp_report_path, timestamp_append, ip_append,
                query, priority_file, priority_file_per, on_sent, old_delivered_per
            ) VALUES (
                %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                %s, %s, %s, %s, %s, %s, %s
            ) RETURNING request_id
        """

        values = (
            client_id,
            converted_data['addedBy'],
            int(converted_data['requestType']),
            converted_data.get('filePath', ''),
            converted_data['startDate'],
            converted_data['endDate'],
            converted_data.get('residualStart'),
            converted_data.get('week', ''),
            converted_data.get('reportpath', ''),
            converted_data.get('qspath', ''),
            'Y' if converted_data.get('offerSuppression') else 'N',
            'Y' if converted_data.get('addBounce') else 'N',
            converted_data.get('clientSuppressionPath', ''),
            converted_data.get('requestIdSuppressionList', ''),
            converted_data.get('timeStampPath', ''),
            'Y' if converted_data.get('addTimeStamp') else 'N',
            'Y' if converted_data.get('addIpsLogs') else 'N',
            converted_data.get('input_query', ''),
            converted_data.get('priorityFile', ''),
            converted_data.get('priorityFilePer'),
            'Y' if converted_data.get('fileType') == 'Sent' else 'N',
            65  # default old_delivered_per
        )

        cursor.execute(insert_query, values)
        request_id = cursor.fetchone()[0]

        conn.commit()
        cursor.close()
        release_db_connection(conn)

        return jsonify({
            'success': True,
            'message': 'Request submitted successfully',
            'request_id': request_id
        })

    except Exception as e:
        logger.error(f"Error in add_request: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'Failed to process request: {str(e)}'
        }), 500


@request_bp.route('/update_request/<int:request_id>', methods=['POST'])
def update_request(request_id):
    """Update existing request with new form data and trigger rerun"""
    logger.info("=" * 80)
    logger.info(f"🔄 UPDATE REQUEST ENDPOINT CALLED: /update_request/{request_id}")

    try:
        data = request.get_json()
        logger.info(f"📦 Request data received: {list(data.keys())}")

        # Extract rerun module information
        rerun_module = data.get('rerun_module', 'TRT')
        logger.info(f"🎯 Rerun module: {rerun_module}")

        # Map rerun modules to error codes
        module_error_codes = {
            'TRT': 1,
            'Responders': 2,
            'Suppression': 3,
            'Source': 4,
            'Delivered Report': 5,
            'TimeStamp Appending': 6,
            'IP Appending': 7
        }
        error_code = module_error_codes.get(rerun_module, 1)
        logger.info(f"🔢 Error code mapped: {error_code}")

        # Get database connection
        conn = get_db_connection()
        if not conn:
            logger.error("❌ Database connection failed")
            return jsonify({'success': False, 'error': 'Database connection failed'}), 500

        cursor = conn.cursor()
        requests_table = config.get_table_name('requests')

        # Build dynamic UPDATE query based on provided fields
        update_fields = []
        update_values = []

        # Map frontend field names to database columns (matching what frontend sends)
        field_mapping = {
            # File paths
            'file_path': 'unique_decile_report_path',
            'report_path': 'cpm_report_path',
            'decile_report_path': 'decile_wise_report_path',
            'timestamp_report_path': 'timestamp_report_path',
            'supp_path': 'supp_path',
            'priority_file': 'priority_file',

            # Dates
            'start_date': 'from_date',
            'end_date': 'end_date',
            'residual_start': 'residual_date',

            # Basic fields
            'week': 'week',
            'query': 'query',
            'added_by': 'added_by',

            # Y/N flags
            'timestamp_append': 'timestamp_append',
            'ip_append': 'ip_append',
            'offerid_unsub_supp': 'offerid_unsub_supp',
            'include_bounce_as_delivered': 'include_bounce_as_delivered',

            # Other fields
            'request_id_supp': 'request_id_supp',
            'priority_file_per': 'priority_file_per',

            # Legacy field names (for backwards compatibility)
            'reportpath': 'cpm_report_path',
            'qspath': 'decile_wise_report_path',
            'timeStampPath': 'timestamp_report_path',
            'clientSuppressionPath': 'supp_path',
            'requestIdSuppressionList': 'request_id_supp',
            'priorityFilePercentage': 'priority_file_per',
            'oldDeliveredPercentage': 'old_delivered_per'
        }

        # Add updatable fields from request data
        for frontend_field, db_column in field_mapping.items():
            if frontend_field in data and data[frontend_field] is not None:
                update_fields.append(f"{db_column} = %s")
                update_values.append(data[frontend_field])
                logger.info(f"   📝 Updating {db_column}: {data[frontend_field]}")

        # Handle request_type -> type conversion
        if 'request_type' in data:
            update_fields.append("type = %s")
            update_values.append(int(data['request_type']))
            logger.info(f"   📝 Updating type: {data['request_type']}")

        # Handle file_type -> on_sent conversion ('Sent' = Y, 'Delivered' = N)
        if 'file_type' in data:
            on_sent_value = 'Y' if data['file_type'] == 'Sent' else 'N'
            update_fields.append("on_sent = %s")
            update_values.append(on_sent_value)
            logger.info(f"   📝 Updating on_sent: {on_sent_value} (from file_type: {data['file_type']})")

        # Always update rerun-related fields
        update_fields.extend([
            "request_status = %s",
            "error_code = %s",
            "request_validation = NULL",
            "request_desc = %s",
            "request_start_time = NOW()"
        ])

        description = f"Request updated and queued for rerun from {rerun_module} module"
        update_values.extend(['RE', error_code, description, request_id])

        logger.info(f"📋 Total fields to update: {len(update_fields)}")

        # Build and execute query
        update_query = f"""
            UPDATE {requests_table} SET
                {', '.join(update_fields)}
            WHERE request_id = %s
        """

        logger.info(f"🔍 Executing update query...")
        cursor.execute(update_query, tuple(update_values))

        if cursor.rowcount == 0:
            logger.error(f"❌ Request {request_id} not found")
            cursor.close()
            release_db_connection(conn)
            return jsonify({'success': False, 'error': 'Request not found'}), 404

        conn.commit()
        logger.info(f"✅ Request {request_id} updated successfully!")
        logger.info(f"   Status: RE (Rerun)")
        logger.info(f"   Error Code: {error_code} ({rerun_module})")
        logger.info(f"   Fields Updated: {cursor.rowcount}")
        logger.info("=" * 80)

        cursor.close()
        release_db_connection(conn)

        return jsonify({
            'success': True,
            'message': f'Request {request_id} updated and queued for rerun from {rerun_module} module',
            'request_id': request_id
        })

    except Exception as e:
        logger.error(f"❌ Exception during request update: {e}", exc_info=True)
        logger.info("=" * 80)
        return jsonify({'success': False, 'error': str(e)}), 500


@request_bp.route('/api/requests/<int:request_id>/details', methods=['GET'])
def get_request_details(request_id):
    """Get detailed information for a specific request"""
    try:
        conn = get_db_connection()
        if not conn:
            return jsonify({'success': False, 'error': 'Database connection failed'}), 500

        cursor = conn.cursor()
        requests_table = config.get_table_name('requests')
        clients_table = config.get_table_name('clients')
        qa_table = config.get_table_name('qa_stats')

        # Get full request details
        query = f"""
        SELECT a.*, b.client_name, COALESCE(c.rltp_file_count, 0) as trt_count
        FROM {requests_table} a
        JOIN {clients_table} b ON a.client_id = b.client_id
        LEFT JOIN {qa_table} c ON a.request_id = c.request_id
        WHERE a.request_id = %s
        """

        cursor.execute(query, (request_id,))
        result = cursor.fetchone()

        if not result:
            cursor.close()
            release_db_connection(conn)
            return jsonify({'success': False, 'error': 'Request not found'}), 404

        # Format result
        request_details = {
            'request_id': result[0],
            'client_name': result[-2],
            'status': result[9] if len(result) > 9 else 'Unknown',
            'created_date': str(result[2]) if len(result) > 2 and result[2] else None,
        }

        cursor.close()
        release_db_connection(conn)

        return jsonify({
            'success': True,
            'request': request_details
        })

    except Exception as e:
        logger.error(f"Error fetching request details: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@request_bp.route('/api/requests/<int:request_id>/stats', methods=['GET'])
def get_request_stats(request_id):
    """Get detailed statistics for a specific request"""
    try:
        conn = get_db_connection()
        if not conn:
            return jsonify({'success': False, 'error': 'Database connection failed'}), 500

        cursor = conn.cursor()
        requests_table = config.get_table_name('requests')
        clients_table = config.get_table_name('clients')
        qa_table = config.get_table_name('qa_stats')

        # Main request details query
        main_query = f"""
        WITH cte AS (
            SELECT a.REQUEST_ID,CLIENT_NAME,ADDED_BY,WEEK,RLTP_FILE_COUNT,REQUEST_STATUS,REQUEST_DESC,REQUEST_START_TIME,
                   execution_time EXECUTION_TIME,request_id_supp_count,POSTED_UNSUB_HARDS_SUPP_COUNT,OFFERID_UNSUB_SUPP_COUNT OFFERID_SUPPRESSED_COUNT,
                   SUPPRESSION_COUNT CLIENT_SUPPRESSION_COUNT,MAX_TOUCH_COUNT,LAST_WK_DEL_INSERT_CNT,LAST_WK_UNSUB_INSERT_CNT,
                   UNIQUE_DELIVERED_COUNT,TotalDeliveredCount,NEW_RECORD_CNT,NEW_ADDED_IP_CNT,TOTAL_RUNNING_UNIQ_CNT,
                   PREV_WEEK_PB_TABLE
            FROM {requests_table} a
            JOIN {clients_table} b ON a.CLIENT_ID=b.CLIENT_ID
            JOIN {qa_table} c ON a.REQUEST_ID=c.REQUEST_ID
            WHERE a.REQUEST_ID=%s
        )
        SELECT x.* FROM cte CROSS JOIN LATERAL (VALUES
            ( 'RequestID', REQUEST_ID::text ),
            ( 'ClientName', CLIENT_NAME::text ),
            ( 'User', ADDED_BY::text ),
            ( 'Week', WEEK::text ),
            ( 'TRTFileCount', RLTP_FILE_COUNT::text ),
            ( 'RequestStatus', REQUEST_STATUS::text ),
            ( 'RequestDescription', REQUEST_DESC::text ),
            ( 'StartTime', REQUEST_START_TIME::text ),
            ( 'TotalExecutionTime', EXECUTION_TIME::text ),
            ( 'RequestIdSuppressionCount', request_id_supp_count::text ),
            ( 'UnsubHardsSuppressionCount', POSTED_UNSUB_HARDS_SUPP_COUNT::text ),
            ( 'OfferIDSuppressionCount', OFFERID_SUPPRESSED_COUNT::text ),
            ( 'ClientSuppressionCount', CLIENT_SUPPRESSION_COUNT::text ),
            ( 'MaxTouchCount', MAX_TOUCH_COUNT::text ),
            ( 'LastWeekDeliveredInsertedCount', LAST_WK_DEL_INSERT_CNT::text ),
            ( 'UnsubInsertedCount', LAST_WK_UNSUB_INSERT_CNT::text ),
            ( 'UniqueDeliveredCount', UNIQUE_DELIVERED_COUNT::text ),
            ( 'TotalDeliveredCount', TotalDeliveredCount::text ),
            ( 'NewlyAddedRecordsCount', NEW_RECORD_CNT::text ),
            ( 'NewlyAddedIPCount', NEW_ADDED_IP_CNT::text ),
            ( 'TotalRunningUniqueCount', TOTAL_RUNNING_UNIQ_CNT::text ),
            ( 'DeliveredTable', PREV_WEEK_PB_TABLE::text )
        ) x(Header, Value)
        """

        cursor.execute(main_query, (request_id,))
        main_stats = cursor.fetchall()

        # Logs details query
        logs_query = f"""
        WITH cte AS (
            SELECT actuallogscount,actuallogstrtmatchcount,actuallogspbreportedcount,actualopenscount,
                   openstrtmatchcount,openspbreportedcount,actualclickscount,clickstrtmatchcount,
                   clickspbreportedcount,openstoopenspbreportedgencount,clickstoclickspbreportedgencount
            FROM {requests_table} a
            JOIN {clients_table} b ON a.CLIENT_ID=b.CLIENT_ID
            JOIN {qa_table} c ON a.REQUEST_ID=c.REQUEST_ID
            WHERE a.REQUEST_ID=%s
        )
        SELECT x.* FROM cte CROSS JOIN LATERAL (VALUES
            ( 'ActuaLogsCount', actuallogscount::text ),
            ( 'ActualLogsTRTmatchCount', actuallogstrtmatchcount::text ),
            ( 'ActualLogsPBreportedCount', actuallogspbreportedcount::text ),
            ( 'ActualOpensCount', actualopenscount::text ),
            ( 'OpensTRTmatchCount', openstrtmatchcount::text ),
            ( 'OpensPBreportedCount', openspbreportedcount::text ),
            ( 'ActualClicksCount', actualclickscount::text ),
            ( 'ClicksTRTmatchCount', clickstrtmatchcount::text ),
            ( 'ClicksPBreportedCount', clickspbreportedcount::text ),
            ( 'OpensToOpensPBreportedGenCount', openstoopenspbreportedgencount::text ),
            ( 'ClicksToClicksPBreportedGenCount', clickstoclickspbreportedgencount::text )
        ) x(Header, Value)
        """

        cursor.execute(logs_query, (request_id,))
        logs_stats = cursor.fetchall()

        # Format results
        request_details = []
        for row in main_stats:
            request_details.append({
                'header': row[0],
                'value': row[1] if row[1] is not None else 'N/A'
            })

        logs_details = []
        for row in logs_stats:
            logs_details.append({
                'header': row[0],
                'value': row[1] if row[1] is not None else 'N/A'
            })

        cursor.close()
        release_db_connection(conn)

        return jsonify({
            'success': True,
            'stats': {
                'request_details': request_details,
                'logs_details': logs_details
            }
        })

    except Exception as e:
        logger.error(f"Error fetching request stats: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@request_bp.route('/api/requests/<int:request_id>/stats/download', methods=['GET'])
def download_request_stats(request_id):
    """Download request statistics as Excel file"""
    try:
        import pandas as pd
        from io import BytesIO

        conn = get_db_connection()
        if not conn:
            return jsonify({'success': False, 'error': 'Database connection failed'}), 500

        cursor = conn.cursor()
        requests_table = config.get_table_name('requests')
        clients_table = config.get_table_name('clients')
        qa_table = config.get_table_name('qa_stats')

        # Same queries as get_request_stats
        main_query = f"""
        WITH cte AS (
            SELECT a.REQUEST_ID,CLIENT_NAME,ADDED_BY,WEEK,RLTP_FILE_COUNT,REQUEST_STATUS,REQUEST_DESC,REQUEST_START_TIME,
                   execution_time EXECUTION_TIME,request_id_supp_count,POSTED_UNSUB_HARDS_SUPP_COUNT,OFFERID_UNSUB_SUPP_COUNT OFFERID_SUPPRESSED_COUNT,
                   SUPPRESSION_COUNT CLIENT_SUPPRESSION_COUNT,MAX_TOUCH_COUNT,LAST_WK_DEL_INSERT_CNT,LAST_WK_UNSUB_INSERT_CNT,
                   UNIQUE_DELIVERED_COUNT,TotalDeliveredCount,NEW_RECORD_CNT,NEW_ADDED_IP_CNT,TOTAL_RUNNING_UNIQ_CNT,
                   PREV_WEEK_PB_TABLE
            FROM {requests_table} a
            JOIN {clients_table} b ON a.CLIENT_ID=b.CLIENT_ID
            JOIN {qa_table} c ON a.REQUEST_ID=c.REQUEST_ID
            WHERE a.REQUEST_ID=%s
        )
        SELECT x.* FROM cte CROSS JOIN LATERAL (VALUES
            ( 'RequestID', REQUEST_ID::text ),
            ( 'ClientName', CLIENT_NAME::text ),
            ( 'User', ADDED_BY::text ),
            ( 'Week', WEEK::text ),
            ( 'TRTFileCount', RLTP_FILE_COUNT::text ),
            ( 'RequestStatus', REQUEST_STATUS::text ),
            ( 'RequestDescription', REQUEST_DESC::text ),
            ( 'StartTime', REQUEST_START_TIME::text ),
            ( 'TotalExecutionTime', EXECUTION_TIME::text ),
            ( 'RequestIdSuppressionCount', request_id_supp_count::text ),
            ( 'UnsubHardsSuppressionCount', POSTED_UNSUB_HARDS_SUPP_COUNT::text ),
            ( 'OfferIDSuppressionCount', OFFERID_SUPPRESSED_COUNT::text ),
            ( 'ClientSuppressionCount', CLIENT_SUPPRESSION_COUNT::text ),
            ( 'MaxTouchCount', MAX_TOUCH_COUNT::text ),
            ( 'LastWeekDeliveredInsertedCount', LAST_WK_DEL_INSERT_CNT::text ),
            ( 'UnsubInsertedCount', LAST_WK_UNSUB_INSERT_CNT::text ),
            ( 'UniqueDeliveredCount', UNIQUE_DELIVERED_COUNT::text ),
            ( 'TotalDeliveredCount', TotalDeliveredCount::text ),
            ( 'NewlyAddedRecordsCount', NEW_RECORD_CNT::text ),
            ( 'NewlyAddedIPCount', NEW_ADDED_IP_CNT::text ),
            ( 'TotalRunningUniqueCount', TOTAL_RUNNING_UNIQ_CNT::text ),
            ( 'DeliveredTable', PREV_WEEK_PB_TABLE::text )
        ) x(Header, Value)
        """

        cursor.execute(main_query, (request_id,))
        main_stats = cursor.fetchall()

        logs_query = f"""
        WITH cte AS (
            SELECT actuallogscount,actuallogstrtmatchcount,actuallogspbreportedcount,actualopenscount,
                   openstrtmatchcount,openspbreportedcount,actualclickscount,clickstrtmatchcount,
                   clickspbreportedcount,openstoopenspbreportedgencount,clickstoclickspbreportedgencount
            FROM {requests_table} a
            JOIN {clients_table} b ON a.CLIENT_ID=b.CLIENT_ID
            JOIN {qa_table} c ON a.REQUEST_ID=c.REQUEST_ID
            WHERE a.REQUEST_ID=%s
        )
        SELECT x.* FROM cte CROSS JOIN LATERAL (VALUES
            ( 'ActuaLogsCount', actuallogscount::text ),
            ( 'ActualLogsTRTmatchCount', actuallogstrtmatchcount::text ),
            ( 'ActualLogsPBreportedCount', actuallogspbreportedcount::text ),
            ( 'ActualOpensCount', actualopenscount::text ),
            ( 'OpensTRTmatchCount', openstrtmatchcount::text ),
            ( 'OpensPBreportedCount', openspbreportedcount::text ),
            ( 'ActualClicksCount', actualclickscount::text ),
            ( 'ClicksTRTmatchCount', clickstrtmatchcount::text ),
            ( 'ClicksPBreportedCount', clickspbreportedcount::text ),
            ( 'OpensToOpensPBreportedGenCount', openstoopenspbreportedgencount::text ),
            ( 'ClicksToClicksPBreportedGenCount', clickstoclickspbreportedgencount::text )
        ) x(Header, Value)
        """

        cursor.execute(logs_query, (request_id,))
        logs_stats = cursor.fetchall()

        cursor.close()
        release_db_connection(conn)

        # Create DataFrames
        request_df = pd.DataFrame(main_stats, columns=['Name', 'Value'])
        logs_df = pd.DataFrame(logs_stats, columns=['Name', 'Value'])

        # Create Excel file
        output = BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            request_df.to_excel(writer, sheet_name='Request Details', index=False)
            logs_df.to_excel(writer, sheet_name='Logs Details', index=False)

        output.seek(0)

        # Create response
        response = make_response(output.read())
        response.headers['Content-Type'] = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        response.headers['Content-Disposition'] = f'attachment; filename=RequestDetails-{request_id}.xlsx'

        return response

    except Exception as e:
        logger.error(f"Error downloading request stats: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@request_bp.route('/api/requests/<int:request_id>/metrics/download', methods=['POST'])
def download_request_metrics(request_id):
    """Download metrics with custom or standard queries"""
    logger.info(f"📊 Download metrics endpoint called for request ID: {request_id}")

    try:
        import pandas as pd
        from io import BytesIO

        data = request.get_json()
        queries = data.get('queries', [])
        metric_type = data.get('metricType', 'standard')

        if not queries:
            return jsonify({'success': False, 'error': 'No queries provided'}), 400

        conn = get_db_connection()
        if not conn:
            return jsonify({'success': False, 'error': 'Database connection failed'}), 500

        cursor = conn.cursor()

        # Create Excel file with multiple sheets
        output = BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            for i, query_info in enumerate(queries):
                query_name = query_info.get('name', f'Query_{i+1}')
                query_sql = query_info.get('query', '')

                try:
                    cursor.execute(query_sql)
                    results = cursor.fetchall()

                    if results:
                        # Get column names
                        col_names = [desc[0] for desc in cursor.description]

                        # Create DataFrame
                        df = pd.DataFrame(results, columns=col_names)

                        # Write to Excel sheet
                        sheet_name = query_name[:31] if len(query_name) > 31 else query_name  # Excel sheet name limit
                        df.to_excel(writer, sheet_name=sheet_name, index=False)

                        logger.info(f"📋 Added sheet '{sheet_name}' with {len(results)} rows")
                    else:
                        # Create empty DataFrame for queries with no results
                        df = pd.DataFrame({'Message': ['No data found for this query']})
                        sheet_name = f'Empty_{i+1}'
                        df.to_excel(writer, sheet_name=sheet_name, index=False)

                except Exception as query_error:
                    logger.error(f"❌ Error executing query {i+1}: {query_error}")
                    # Add error sheet
                    error_df = pd.DataFrame({'Error': [f'Query execution failed: {str(query_error)}']})
                    error_sheet_name = f'Error_{i+1}'
                    error_df.to_excel(writer, sheet_name=error_sheet_name, index=False)

        cursor.close()
        release_db_connection(conn)

        output.seek(0)

        # Create response
        response = make_response(output.read())
        response.headers['Content-Type'] = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        response.headers['Content-Disposition'] = f'attachment; filename=Metrics-{request_id}.xlsx'

        logger.info(f"✅ Successfully created metrics Excel file for request {request_id}")
        return response

    except Exception as e:
        logger.error(f"❌ Error downloading metrics: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@request_bp.route('/api/requests/<int:request_id>/rerun', methods=['POST'])
def rerun_request(request_id):
    """Trigger rerun for a specific request with module selection"""
    logger.info(f"🔄 Rerun request endpoint called for ID: {request_id}")

    try:
        data = request.get_json()
        rerun_module = data.get('rerun_type', 'TRT')

        # Map rerun modules to error codes
        module_error_codes = {
            'TRT': 1,
            'Responders': 2,
            'Suppression': 3,
            'Source': 4,
            'Delivered Report': 5,
            'TimeStamp Appending': 6,
            'IP Appending': 7
        }

        error_code = module_error_codes.get(rerun_module, 1)  # Default to 1 if module not found

        logger.info(f"🔄 Rerun module: {rerun_module}, Error code: {error_code}")

        conn = get_db_connection()
        if not conn:
            return jsonify({'success': False, 'error': 'Database connection failed'}), 500

        cursor = conn.cursor()
        requests_table = config.get_table_name('requests')

        # Update request with RE status, error_code for module, and reset validation
        update_query = f"""
        UPDATE {requests_table}
        SET request_status = 'RE',
            error_code = %s,
            request_validation = NULL,
            request_desc = %s,
            request_start_time = NOW()
        WHERE request_id = %s
        """

        description = f"ReRun requested for {rerun_module} module"
        cursor.execute(update_query, (error_code, description, request_id))

        if cursor.rowcount == 0:
            cursor.close()
            release_db_connection(conn)
            return jsonify({'success': False, 'error': 'Request not found'}), 404

        conn.commit()
        cursor.close()
        release_db_connection(conn)

        logger.info(f"✅ Request {request_id} marked for rerun - Module: {rerun_module} (Error Code: {error_code})")

        return jsonify({
            'success': True,
            'message': f'Request {request_id} marked for rerun - {rerun_module} module'
        })

    except Exception as e:
        logger.error(f"❌ Error during rerun: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@request_bp.route('/api/requests/<int:request_id>/kill', methods=['POST'])
def kill_request(request_id):
    """Kill/Cancel a specific request"""
    try:
        conn = get_db_connection()
        if not conn:
            return jsonify({'success': False, 'error': 'Database connection failed'}), 500

        cursor = conn.cursor()
        requests_table = config.get_table_name('requests')

        # Get current request status
        status_query = f"SELECT request_status FROM {requests_table} WHERE request_id = %s"
        cursor.execute(status_query, (request_id,))
        result = cursor.fetchone()

        if not result:
            cursor.close()
            release_db_connection(conn)
            return jsonify({'success': False, 'error': 'Request not found'}), 404

        current_status = result[0]

        # Handle W (Waiting) state requests directly
        if current_status == 'W':
            update_query = f"""
            UPDATE {requests_table}
            SET request_status = 'E',
                request_desc = 'Cancelled by User',
                request_end_time = NOW()
            WHERE request_id = %s
            """
            cursor.execute(update_query, (request_id,))
            conn.commit()
            cursor.close()
            release_db_connection(conn)

            return jsonify({
                'success': True,
                'message': f'Request {request_id} cancelled',
                'edit_enabled': True,
                'direct_cancel': True
            })
        else:
            # For non-W state requests, use shell script
            cursor.close()
            release_db_connection(conn)

            # Use shell script for cancellation
            script_path = "/u1/techteam/PFM_CUSTOM_SCRIPTS/APT_TOOL_DB/SCRIPTS/cancelRequest.sh"

            if not os.path.exists(script_path):
                # Fallback to database-only cancellation
                conn = get_db_connection()
                if not conn:
                    return jsonify({'success': False, 'error': 'Database connection failed'}), 500

                cursor = conn.cursor()
                update_query = f"""
                UPDATE {requests_table}
                SET request_status = 'E',
                    request_desc = 'Cancelled (Script Not Found)',
                    request_end_time = NOW()
                WHERE request_id = %s AND request_status IN ('W', 'R', 'RE')
                """
                cursor.execute(update_query, (request_id,))

                if cursor.rowcount == 0:
                    cursor.close()
                    release_db_connection(conn)
                    return jsonify({'success': False, 'error': 'Request not found or cannot be cancelled'}), 400

                conn.commit()
                cursor.close()
                release_db_connection(conn)

                return jsonify({
                    'success': True,
                    'message': f'Request {request_id} cancelled',
                    'edit_enabled': True,
                    'fallback': True
                })

            # Execute shell script
            working_directory = "/u1/techteam/PFM_CUSTOM_SCRIPTS/APT_TOOL_DB/SCRIPTS"

            result = subprocess.run(
                ['bash', './cancelRequest.sh', str(request_id)],
                cwd=working_directory,
                capture_output=True,
                text=True,
                timeout=60
            )

            if result.returncode == 0:
                return jsonify({
                    'success': True,
                    'message': f'Request {request_id} cancelled successfully',
                    'edit_enabled': True,
                    'script_used': True
                })
            else:
                logger.error(f"Cancel script failed with return code: {result.returncode}")
                error_message = result.stderr.strip() if result.stderr else "Unknown error"

                # Provide user-friendly error messages
                user_friendly_error = f"Process cancellation failed. {error_message}"
                if "not found" in error_message.lower():
                    user_friendly_error = "No active processes found for this request."
                elif "timeout" in error_message.lower():
                    user_friendly_error = "Cancellation timeout. Please try again."
                elif "permission" in error_message.lower():
                    user_friendly_error = "Permission denied. Contact administrator."

                return jsonify({
                    'success': False,
                    'error': user_friendly_error,
                    'retry_available': True
                }), 500

    except subprocess.TimeoutExpired:
        logger.error(f"Cancel script timeout for request {request_id}")
        return jsonify({
            'success': False,
            'error': 'Cancellation timeout. Please try again.',
            'retry_available': True
        }), 500
    except Exception as e:
        logger.error(f"Error during kill request: {e}")
        return jsonify({
            'success': False,
            'error': f'Cancellation error: {str(e)}',
            'retry_available': True
        }), 500


@request_bp.route('/api/requests/<int:request_id>/download', methods=['GET'])
def download_request(request_id):
    """Download request files - placeholder"""
    return jsonify({
        'success': False,
        'error': 'Download functionality not yet implemented'
    }), 501


@request_bp.route('/api/requests/<int:request_id>/upload', methods=['POST'])
def upload_request_file(request_id):
    """Upload files for a request - redirect to new upload flow"""
    return jsonify({
        'success': False,
        'error': 'Please use /api/upload/save endpoint for file uploads',
        'redirect': '/api/upload/save'
    }), 400


@request_bp.route('/api/requests/status-counts', methods=['GET'])
def get_status_counts():
    """Get count of requests by status"""
    try:
        conn = get_db_connection()
        if not conn:
            return jsonify({'success': False, 'error': 'Database connection failed'}), 500

        cursor = conn.cursor()
        requests_table = config.get_table_name('requests')

        # Get status counts
        query = f"""
        SELECT request_status, COUNT(*) as count
        FROM {requests_table}
        GROUP BY request_status
        ORDER BY request_status
        """

        cursor.execute(query)
        results = cursor.fetchall()

        status_counts = {}
        for row in results:
            status_counts[row[0]] = row[1]

        cursor.close()
        release_db_connection(conn)

        return jsonify({
            'success': True,
            'status_counts': status_counts
        })

    except Exception as e:
        logger.error(f"Error fetching status counts: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@request_bp.route('/api/requests/<int:request_id>/client-name', methods=['GET'])
def get_client_name(request_id):
    """Get client name for a specific request"""
    try:
        conn = get_db_connection()
        if not conn:
            return jsonify({'success': False, 'error': 'Database connection failed'}), 500

        cursor = conn.cursor()
        clients_table = config.get_table_name('clients')
        requests_table = config.get_table_name('requests')

        query = f"""
        SELECT UPPER(client_name)
        FROM {clients_table} a
        JOIN {requests_table} b ON a.client_id = b.client_id
        WHERE request_id = %s
        """

        cursor.execute(query, (request_id,))
        result = cursor.fetchone()

        cursor.close()
        release_db_connection(conn)

        if result:
            return jsonify({
                'success': True,
                'clientName': result[0]
            })
        else:
            return jsonify({'success': False, 'error': 'Request not found'}), 404

    except Exception as e:
        logger.error(f"Error fetching client name: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@request_bp.route('/api/requests/<int:request_id>/week', methods=['GET'])
def get_week(request_id):
    """Get week for a specific request"""
    try:
        conn = get_db_connection()
        if not conn:
            return jsonify({'success': False, 'error': 'Database connection failed'}), 500

        cursor = conn.cursor()
        requests_table = config.get_table_name('requests')

        query = f"""
        SELECT UPPER(week)
        FROM {requests_table}
        WHERE request_id = %s
        """

        cursor.execute(query, (request_id,))
        result = cursor.fetchone()

        cursor.close()
        release_db_connection(conn)

        if result:
            return jsonify({
                'success': True,
                'week': result[0]
            })
        else:
            return jsonify({'success': False, 'error': 'Request not found'}), 404

    except Exception as e:
        logger.error(f"Error fetching week: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500
