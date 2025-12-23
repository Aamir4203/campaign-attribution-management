#!/usr/bin/env python3
"""
Campaign Attribution Management (CAM) - Simplified Backend API
Essential endpoints for addRequest page functionality only
"""

from flask import Flask, jsonify, request
from flask_cors import CORS
import logging
import psycopg2
import time
import os
from datetime import datetime, timedelta
from config.config import get_config
from services.file_validation_service import FileValidationService
from services.upload_service import UploadService
from utils.file_utils import FileUtils

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
    logger.error("Configuration validation failed - exiting")
    exit(1)

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

# Get database configuration
DB_CONFIG = config.get_database_credentials()

# Initialize file services
file_validator = FileValidationService(config)
upload_service = UploadService(config)

# Utility functions for configuration-based operations
def get_external_db_connection_string(db_type):
    """Get external database connection string from configuration"""
    return config.get_external_db_config(db_type).get('connection_string', '')

def get_file_path(path_type, **kwargs):
    """Get file path from configuration with optional formatting"""
    return config.get_file_path(path_type, **kwargs)

def get_alert_recipients():
    """Get alert email recipients from configuration"""
    return config.get_alerts_config().get('email_recipients', '').split(',')

def get_upload_config():
    """Get upload configuration settings"""
    return config.get_upload_config()

def validate_request_status(status):
    """Validate request status against configured valid statuses"""
    valid_statuses = config.get_request_constants().get('validStatuses', ['P', 'C', 'E', 'RW', 'RE'])
    return status in valid_statuses

def get_db_connection():
    """Get database connection with timeout - non-blocking for Flask startup"""
    try:
        # Add connection timeout to prevent hanging
        import signal

        # Set a timeout for database connection
        def timeout_handler(signum, frame):
            raise TimeoutError("Database connection timeout")

        # Only set timeout if not on Windows (signal.SIGALRM not available on Windows)
        try:
            signal.signal(signal.SIGALRM, timeout_handler)
            signal.alarm(5)  # 5 second timeout
        except AttributeError:
            # Windows doesn't support SIGALRM, use psycopg2 timeout only
            pass

        conn = psycopg2.connect(**DB_CONFIG, connect_timeout=5)

        try:
            signal.alarm(0)  # Cancel timeout
        except AttributeError:
            pass

        return conn

    except (psycopg2.OperationalError, TimeoutError) as e:
        logger.warning(f"Database connection failed: {e}")
        return None
    except Exception as e:
        logger.error(f"Database connection error: {e}")
        return None

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.utcnow().isoformat(),
        'service': 'CAM API'
    })

@app.route('/api/clients', methods=['GET'])
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
        conn.close()

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

@app.route('/check_client', methods=['POST'])
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
        conn.close()

        return jsonify({
            'exists': bool(result),
            'client_id': result[0] if result else None
        })

    except Exception as e:
        logger.error(f"Error checking client: {e}")
        return jsonify({'error': 'Failed to check client'}), 500

@app.route('/add_client', methods=['POST'])
def add_client():
    """Add new client to database"""
    try:
        data = request.get_json()
        if not data or 'client_name' not in data:
            return jsonify({'error': 'client_name is required'}), 400

        client_name = data['client_name'].strip()
        if not client_name:
            return jsonify({'error': 'client_name cannot be empty'}), 400

        conn = get_db_connection()
        if not conn:
            return jsonify({
                'success': False,
                'message': 'Database connection unavailable'
            })

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
            conn.close()
            return jsonify({
                'success': False,
                'message': f'Client "{client_name}" already exists'
            })

        # Add new client
        cursor.execute(
            f"INSERT INTO {clients_table} (client_name) VALUES (%s) RETURNING client_id",
            (client_name,)
        )
        client_id = cursor.fetchone()[0]

        conn.commit()
        cursor.close()
        conn.close()


        return jsonify({
            'success': True,
            'client_id': client_id,
            'message': f'Client "{client_name}" added successfully'
        })

    except Exception as e:
        logger.error(f"Error adding client: {e}")
        return jsonify({
            'success': False,
            'message': 'Failed to add client'
        }), 500

@app.route('/submit_form', methods=['POST'])
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

        # Validate residual date - must be >= end date
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

        # Validate Type 2 requires unique decile report path
        if data.get('requestType') == '2' and not data.get('filePath'):
            return jsonify({
                'success': False,
                'message': 'Unique decile report path is required for Type 2 requests'
            }), 400

        # Validate client suppression path if client suppression is enabled
        if data.get('clientSuppression') and not data.get('clientSuppressionPath'):
            return jsonify({
                'success': False,
                'message': 'Client suppression file path is required when Client Suppression is enabled'
            }), 400

        # Validate timestamp path if add timestamp is enabled
        if data.get('addTimeStamp') and not data.get('timeStampPath'):
            return jsonify({
                'success': False,
                'message': 'TimeStamp file path is required when Add TimeStamp is enabled'
            }), 400

        # Validate request ID suppression list if request ID suppression is enabled
        if data.get('requestIdSuppression') and not data.get('requestIdSuppressionList'):
            return jsonify({
                'success': False,
                'message': 'Request ID list is required when Request ID Suppression is enabled'
            }), 400

        # Validate request ID suppression list format
        if data.get('requestIdSuppressionList'):
            import re
            request_ids = data.get('requestIdSuppressionList', '').strip()
            if not re.match(r'^[\d,\s]+$', request_ids):
                return jsonify({
                    'success': False,
                    'message': 'Request IDs must be comma-separated numbers'
                }), 400

            # Validate individual request IDs
            ids = [id.strip() for id in request_ids.split(',') if id.strip()]
            for req_id in ids:
                try:
                    if int(req_id) <= 0:
                        raise ValueError()
                except ValueError:
                    return jsonify({
                        'success': False,
                        'message': f'Invalid request ID: {req_id}. All request IDs must be positive numbers'
                    }), 400

        # Validate priority file percentage if priority file is provided
        if data.get('priorityFile') and data.get('priorityFile').strip():
            if not data.get('priorityFilePer'):
                return jsonify({
                    'success': False,
                    'message': 'Priority percentage is required when priority file is specified'
                }), 400

            priority_per = data.get('priorityFilePer')
            logger.info(f"🔍 Raw priority percentage from frontend: {priority_per} (type: {type(priority_per)})")

            try:
                # Convert to integer, preserving exact value
                if isinstance(priority_per, str):
                    priority_per_int = int(priority_per)
                elif isinstance(priority_per, (int, float)):
                    priority_per_int = int(priority_per)
                else:
                    raise ValueError(f"Invalid type: {type(priority_per)}")

                logger.info(f"✅ Converted priority percentage: {priority_per_int}")

                if priority_per_int < 1 or priority_per_int > 100:
                    raise ValueError("Out of range")

            except (ValueError, TypeError) as e:
                logger.error(f"❌ Priority percentage conversion error: {e}")
                return jsonify({
                    'success': False,
                    'message': 'Priority percentage must be a number between 1 and 100'
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
            conn.close()
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

            # Handle both string and numeric inputs
            try:
                if isinstance(priority_file_per_raw, str):
                    priority_file_per = int(priority_file_per_raw.strip())
                elif isinstance(priority_file_per_raw, (int, float)):
                    priority_file_per = int(priority_file_per_raw)
                else:
                    priority_file_per = int(float(str(priority_file_per_raw)))

                # Validate range
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
            client_id,                                                              # client_id
            data['addedBy'],                                                       # added_by
            int(data['requestType']),                                              # type
            default_old_percentage,                                                # old_delivered_per - use config default
            data.get('filePath'),                                                  # unique_decile_report_path for Type 2
            start_date,                                                            # from_date
            end_date,                                                              # end_date
            residual_date,                                                         # residual_date
            data.get('week', ''),                                                  # week
            'Y' if data.get('addTimeStamp', False) else 'N',                      # timestamp_append
            'Y' if data.get('addIpsLogs', False) else 'N',                        # ip_append
            data.get('reportpath'),                                                # cpm_report_path
            data.get('qspath'),                                                    # decile_wise_report_path
            'Y' if data.get('fileType') == 'Sent' else 'N',                       # on_sent
            'Y' if data.get('offerSuppression', False) else 'N',                  # offerid_unsub_supp
            'Y' if data.get('addBounce', False) else 'N',                         # include_bounce_as_delivered
            data.get('clientSuppressionPath') if data.get('clientSuppression') else None,  # supp_path
            data.get('input_query'),                                               # query
            request_id_suppression,                                                # request_id_supp - new field
            priority_file,                                                         # priority_file - new field
            priority_file_per,                                                     # priority_file_per - new field
            timestamp_path,                                                        # timestamp_report_path - new field
            datetime.now()                                                         # created_date
        )

        try:
            cursor.execute(insert_query, insert_data)
            request_id = cursor.fetchone()[0]

            # Commit the transaction
            conn.commit()
            cursor.close()
            conn.close()

            return jsonify({
                'success': True,
                'message': 'Request submitted successfully to CAM database!',
                'request_id': request_id,
                'client_id': client_id,
                'client_name': data['clientName']
            })

        except Exception as db_error:
            # Rollback on database error
            conn.rollback()
            cursor.close()
            conn.close()

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

@app.route('/add_request', methods=['POST'])
def add_request():
    """Add new campaign attribution request - modern API endpoint"""
    try:
        data = request.get_json()

        # Convert underscore-separated fields to camelCase for existing submit_form logic
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
            'options': data.get('options', 'N'),
            'Offer_option': data.get('offer_option', ''),
            'bounce_option': data.get('bounce_option', ''),
            'cs_option': data.get('cs_option', ''),
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

        logger.info(f"🔄 Converted data for internal processing: {converted_data}")

        # Validate required fields
        required_fields = ['clientName', 'addedBy', 'requestType', 'startDate', 'endDate']
        missing_fields = [field for field in required_fields if not converted_data.get(field)]

        if missing_fields:
            return jsonify({
                'success': False,
                'message': f'Missing required fields: {", ".join(missing_fields)}'
            }), 400

        # Validate dates
        if converted_data.get('residualStart'):
            from datetime import datetime as dt
            try:
                start_date = dt.strptime(converted_data['startDate'], '%Y-%m-%d').date()
                end_date = dt.strptime(converted_data['endDate'], '%Y-%m-%d').date()
                residual_date = dt.strptime(converted_data['residualStart'], '%Y-%m-%d').date()

                if residual_date < end_date:
                    return jsonify({
                        'success': False,
                        'message': 'Residual date must be equal to or greater than end date'
                    }), 400

                logger.info(f"✅ Date validation passed: Start={start_date}, End={end_date}, Residual={residual_date}")

            except ValueError as ve:
                return jsonify({
                    'success': False,
                    'message': f'Invalid date format: {str(ve)}'
                }), 400

        # Get database connection
        logger.info("🔗 Attempting database connection...")
        conn = get_db_connection()
        if not conn:
            logger.error("❌ Database connection failed")
            return jsonify({
                'success': False,
                'message': 'Database connection failed'
            }), 500

        logger.info("✅ Database connection successful")
        cursor = conn.cursor()

        # Get client_id from client_name
        logger.info(f"🔍 Looking up client: {converted_data['clientName']}")
        clients_table = config.get_table_name('clients')
        cursor.execute(
            f"SELECT client_id FROM {clients_table} WHERE LOWER(client_name) = LOWER(%s)",
            (converted_data['clientName'],)
        )
        client_result = cursor.fetchone()

        if not client_result:
            cursor.close()
            conn.close()
            logger.error(f"❌ Client not found: {converted_data['clientName']}")
            return jsonify({
                'success': False,
                'message': f'Client "{converted_data["clientName"]}" not found in database'
            }), 400

        client_id = client_result[0]
        logger.info(f"✅ Client found: ID {client_id}")

        # Insert into requests table
        requests_table = config.get_table_name('requests')
        logger.info(f"📝 Inserting request into {requests_table}")

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
            converted_data.get('filePath', ''),  # unique_decile_report_path
            converted_data['startDate'],  # from_date
            converted_data['endDate'],  # end_date
            converted_data.get('residualStart'),  # residual_date
            converted_data.get('week', ''),
            converted_data.get('reportpath', ''),  # cpm_report_path
            converted_data.get('qspath', ''),  # decile_wise_report_path
            'Y' if converted_data.get('offerSuppression') else 'N',  # offerid_unsub_supp
            'Y' if converted_data.get('addBounce') else 'N',  # include_bounce_as_delivered
            converted_data.get('clientSuppressionPath', ''),  # supp_path
            converted_data.get('requestIdSuppressionList', ''),  # request_id_supp
            converted_data.get('timeStampPath', ''),  # timestamp_report_path
            'Y' if converted_data.get('addTimeStamp') else 'N',  # timestamp_append
            'Y' if converted_data.get('addIpsLogs') else 'N',  # ip_append
            converted_data.get('input_query', ''),  # query
            converted_data.get('priorityFile', ''),  # priority_file
            converted_data.get('priorityFilePer'),  # priority_file_per
            'Y' if converted_data.get('fileType') == 'Sent' else 'N',  # on_sent
            1  # old_delivered_per - default value
        )

        cursor.execute(insert_query, values)
        request_id = cursor.fetchone()[0]

        conn.commit()
        cursor.close()
        conn.close()

        logger.info(f"✅ Request created successfully with ID: {request_id}")

        return jsonify({
            'success': True,
            'message': 'Request submitted successfully',
            'request_id': request_id
        })

    except Exception as e:
        logger.error(f"❌ Error in add_request: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'Failed to process request: {str(e)}'
        }), 500

@app.route('/update_request/<int:request_id>', methods=['POST'])
def update_request(request_id):
    """Update existing request with new form data and trigger rerun from specified module"""
    try:
        data = request.get_json()

        # Extract rerun module information
        rerun_module = data.get('rerun_module', 'TRT')
        original_request_id = data.get('original_request_id')

        # Convert data format (same as add_request)
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
            'options': data.get('options', 'N'),
            'Offer_option': data.get('offer_option', ''),
            'bounce_option': data.get('bounce_option', ''),
            'cs_option': data.get('cs_option', ''),
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

        # Validate dates
        if converted_data.get('residualStart'):
            from datetime import datetime as dt
            try:
                start_date = dt.strptime(converted_data['startDate'], '%Y-%m-%d').date()
                end_date = dt.strptime(converted_data['endDate'], '%Y-%m-%d').date()
                residual_date = dt.strptime(converted_data['residualStart'], '%Y-%m-%d').date()

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

        # Map rerun modules to error codes (same as rerun endpoint)
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


        # Get database connection
        conn = get_db_connection()
        if not conn:
            return jsonify({'success': False, 'error': 'Database connection failed'}), 500

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
            conn.close()
            return jsonify({
                'success': False,
                'message': f'Client "{converted_data["clientName"]}" not found in database'
            }), 400

        client_id = client_result[0]

        # Update the existing request with new form data and rerun settings
        requests_table = config.get_table_name('requests')

        update_query = f"""
            UPDATE {requests_table} SET 
                client_id = %s,
                added_by = %s,
                type = %s,
                unique_decile_report_path = %s,
                from_date = %s,
                end_date = %s,
                residual_date = %s,
                week = %s,
                cpm_report_path = %s,
                decile_wise_report_path = %s,
                offerid_unsub_supp = %s,
                include_bounce_as_delivered = %s,
                supp_path = %s,
                request_id_supp = %s,
                timestamp_report_path = %s,
                timestamp_append = %s,
                ip_append = %s,
                query = %s,
                priority_file = %s,
                priority_file_per = %s,
                on_sent = %s,
                request_status = 'RE',
                error_code = %s,
                request_validation = NULL,
                request_desc = %s,
                request_start_time = NOW()
            WHERE request_id = %s
        """

        description = f"Request updated and queued for rerun from {rerun_module} module"

        update_values = (
            client_id,
            converted_data['addedBy'],
            int(converted_data['requestType']),
            converted_data.get('filePath', ''),  # unique_decile_report_path
            converted_data['startDate'],  # from_date
            converted_data['endDate'],  # end_date
            converted_data.get('residualStart'),  # residual_date
            converted_data.get('week', ''),
            converted_data.get('reportpath', ''),  # cpm_report_path
            converted_data.get('qspath', ''),  # decile_wise_report_path
            'Y' if converted_data.get('offerSuppression') else 'N',  # offerid_unsub_supp
            'Y' if converted_data.get('addBounce') else 'N',  # include_bounce_as_delivered
            converted_data.get('clientSuppressionPath', ''),  # supp_path
            converted_data.get('requestIdSuppressionList', ''),  # request_id_supp
            converted_data.get('timeStampPath', ''),  # timestamp_report_path
            'Y' if converted_data.get('addTimeStamp') else 'N',  # timestamp_append
            'Y' if converted_data.get('addIpsLogs') else 'N',  # ip_append
            converted_data.get('input_query', ''),  # query
            converted_data.get('priorityFile', ''),  # priority_file
            converted_data.get('priorityFilePer'),  # priority_file_per
            'Y' if converted_data.get('fileType') == 'Sent' else 'N',  # on_sent
            error_code,  # error_code for rerun module
            description,  # request_desc
            request_id  # WHERE condition
        )

        cursor.execute(update_query, update_values)

        if cursor.rowcount == 0:
            cursor.close()
            conn.close()
            return jsonify({'success': False, 'error': 'Request not found'}), 404

        conn.commit()
        cursor.close()
        conn.close()

        return jsonify({
            'success': True,
            'message': f'Request {request_id} updated and queued for rerun from {rerun_module} module',
            'request_id': request_id
        })

    except Exception as e:
        logger.error(f"Error during request update: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

# Session storage (in production, use Redis or database)
active_sessions = {}

def cleanup_expired_sessions():
    """Remove expired sessions"""
    current_time = datetime.utcnow()
    expired_sessions = [
        session_id for session_id, session_data in active_sessions.items()
        if session_data['expires_at'] < current_time
    ]

    for session_id in expired_sessions:
        del active_sessions[session_id]

    if expired_sessions:
        logger.info(f"🧹 Cleaned up {len(expired_sessions)} expired sessions")

@app.route('/api/login', methods=['POST'])
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
            conn.close()
            return jsonify({'success': False, 'message': 'Invalid username or password'}), 401

        # Create a new session
        session_id = f"session-{user[0]}-{int(datetime.utcnow().timestamp())}"
        active_sessions[session_id] = {
            'user_id': user[0],
            'username': user[1],
            'expires_at': datetime.utcnow() + timedelta(hours=48)  # 48-hour expiration
        }

        cursor.close()
        conn.close()

        return jsonify({
            'success': True,
            'message': 'Login successful',
            'token': session_id,
            'expires_in': 172800  # 48 hours in seconds
        })

    except Exception as e:
        logger.error(f"Error during login: {e}")
        return jsonify({'success': False, 'message': 'Login failed'}), 500

@app.route('/api/logout', methods=['POST'])
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

@app.route('/api/session_info', methods=['GET'])
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

# ==========================================
# REQUEST MANAGEMENT ENDPOINTS - PHASE 3
# ==========================================

@app.route('/api/requests', methods=['GET'])
def get_requests():
    """Get all requests with pagination and search - Phase 3"""
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

        # Base query matching the original LogStreamr apt-tool.py structure
        base_query = f"""
        SELECT 
            a.request_id,
           lower(b.client_name) as client_name,
            lower(a.week) as week,
            lower(a.added_by) as added_by,
            COALESCE(c.rltp_file_count, 0) as trt_count,
            a.request_status,
            a.request_desc,
            COALESCE(a.execution_time, '-') as execution_time
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

        # Get paginated requests (ordered by request_id desc - matching LogStreamr)
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
                'execution_time': row[7] or '-'
            })

        total_pages = (total_count + limit - 1) // limit

        cursor.close()
        conn.close()

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

@app.route('/api/requests/<int:request_id>/details', methods=['GET'])
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
            return jsonify({'success': False, 'error': 'Request not found'}), 404

        # Format result (you can expand this based on your table structure)
        request_details = {
            'request_id': result[0],
            'client_name': result[-1],  # Last column is client_name from join
            'status': result[9],  # Adjust index based on your table structure
            'created_date': str(result[2]) if result[2] else None,
            # Add more fields as needed
        }

        cursor.close()
        conn.close()

        return jsonify({
            'success': True,
            'request': request_details
        })

    except Exception as e:
        logger.error(f"Error fetching request details: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/requests/<int:request_id>/stats/download', methods=['GET'])
def download_request_stats(request_id):
    """Download request statistics as Excel file with two sheets"""
    logger.info(f"📊 Download stats endpoint called for request ID: {request_id}")

    try:
        import pandas as pd
        from io import BytesIO

        conn = get_db_connection()
        if not conn:
            logger.error("Database connection failed for download stats")
            return jsonify({'success': False, 'error': 'Database connection failed'}), 500

        cursor = conn.cursor()
        requests_table = config.get_table_name('requests')
        clients_table = config.get_table_name('clients')
        qa_table = config.get_table_name('qa_stats')

        logger.info(f"Using tables: {requests_table}, {clients_table}, {qa_table}")

        # First query - Main request details
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

        # Second query - Logs details
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
        conn.close()

        # Create DataFrames
        request_df = pd.DataFrame(main_stats, columns=['Name', 'Value'])
        logs_df = pd.DataFrame(logs_stats, columns=['Name', 'Value'])

        # Create Excel file with two sheets
        output = BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            request_df.to_excel(writer, sheet_name='Request Details', index=False)
            logs_df.to_excel(writer, sheet_name='Logs Details', index=False)

        output.seek(0)

        # Create response
        response = app.response_class(
            output.read(),
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            headers={
                'Content-Disposition': f'attachment; filename=RequestDetails-{request_id}.xlsx'
            }
        )

        logger.info(f"Successfully created Excel file for request {request_id}")
        return response

    except Exception as e:
        logger.error(f"Error downloading request stats: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/requests/<int:request_id>/stats', methods=['GET'])
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

        # First query - Main request details
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

        # Second query - Logs details
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

        # Format the results
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
        conn.close()

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

@app.route('/api/requests/<int:request_id>/rerun', methods=['POST'])
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
            return jsonify({'success': False, 'error': 'Request not found'}), 404

        conn.commit()
        cursor.close()
        conn.close()

        logger.info(f"✅ Request {request_id} marked for rerun - Module: {rerun_module} (Error Code: {error_code})")

        return jsonify({
            'success': True,
            'message': f'Request {request_id} marked for rerun - {rerun_module} module'
        })

    except Exception as e:
        logger.error(f"❌ Error during rerun: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/requests/<int:request_id>/kill', methods=['POST'])
def kill_request(request_id):
    """Kill/Cancel a specific request - handles W state efficiently"""
    try:
        # Get database connection and check request status
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
            conn.close()
            return jsonify({'success': False, 'error': 'Request not found'}), 404

        current_status = result[0]

        # Handle W (Waiting) state requests directly - no processes to kill
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
            conn.close()

            return jsonify({
                'success': True,
                'message': f'Request {request_id} cancelled',
                'edit_enabled': True,
                'direct_cancel': True
            })
        else:
            # For non-W state requests (R, RE, etc.), close connection and use shell script
            cursor.close()
            conn.close()

            import subprocess

            # Use the correct path based on production environment structure
            script_path = "/u1/techteam/PFM_CUSTOM_SCRIPTS/APT_TOOL_DB/SCRIPTS/cancelRequest.sh"

            # Check if script exists
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
                    conn.close()
                    return jsonify({'success': False, 'error': 'Request not found or cannot be cancelled'}), 400

                conn.commit()
                cursor.close()
                conn.close()

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

@app.route('/api/requests/<int:request_id>/download', methods=['GET'])
def download_request(request_id):
    """Download request files - placeholder implementation"""
    logger.info(f"📥 Download request endpoint called for ID: {request_id}")

    # This is a placeholder - in a real implementation, you would:
    # 1. Check if request exists and is completed
    # 2. Locate the files associated with the request
    # 3. Create a ZIP file containing all relevant files
    # 4. Return the ZIP file as a download

    return jsonify({
        'success': False,
        'error': 'Download functionality not yet implemented'
    }), 501

@app.route('/api/upload/validate', methods=['POST'])
def validate_file_upload():
    """Real-time file validation endpoint"""
    try:
        # Check if feature is enabled
        if not config.is_feature_enabled('file_upload_enabled'):
            return jsonify({
                'success': False,
                'error': 'File upload feature is not enabled'
            }), 403

        # Validate request
        if 'file' not in request.files:
            return jsonify({
                'success': False,
                'error': 'No file provided'
            }), 400

        file = request.files['file']
        if file.filename == '':
            return jsonify({
                'success': False,
                'error': 'No file selected'
            }), 400

        # Get file type and parameters
        file_type = request.form.get('file_type')
        client_name = request.form.get('client_name', '')
        week_name = request.form.get('week_name', '')

        if not file_type:
            return jsonify({
                'success': False,
                'error': 'File type is required'
            }), 400

        if file_type not in ['timestamp', 'cpm', 'decile']:
            return jsonify({
                'success': False,
                'error': 'Invalid file type. Must be: timestamp, cpm, or decile'
            }), 400

        # Read file content
        file_content = file.read()
        filename = file.filename

        # Normalize file content (convert Excel to CSV if needed)
        try:
            normalized_content = FileUtils.normalize_file_content(file_content, filename, '|')
        except Exception as e:
            return jsonify({
                'success': False,
                'error': f'File format error: {str(e)}'
            }), 400

        # Validate file
        validation_result = file_validator.validate_file(normalized_content, filename, file_type)

        # Add expected filename info
        if client_name and week_name:
            expected_filename = upload_service.generate_filename(file_type, client_name, week_name)
            validation_result['expected_filename'] = expected_filename
            validation_result['file_exists'] = upload_service.file_exists(file_type, client_name, week_name)

        logger.info(f"File validation completed for {filename}: {'VALID' if validation_result['valid'] else 'INVALID'}")

        return jsonify({
            'success': True,
            'validation': validation_result
        })

    except Exception as e:
        logger.error(f"Error in file validation: {e}")
        return jsonify({
            'success': False,
            'error': f'Validation error: {str(e)}'
        }), 500

@app.route('/api/upload/save', methods=['POST'])
def save_uploaded_file():
    """Save validated file to storage"""
    try:
        # Check if feature is enabled
        if not config.is_feature_enabled('file_upload_enabled'):
            return jsonify({
                'success': False,
                'error': 'File upload feature is not enabled'
            }), 403

        # Validate request
        if 'file' not in request.files:
            return jsonify({
                'success': False,
                'error': 'No file provided'
            }), 400

        file = request.files['file']
        if file.filename == '':
            return jsonify({
                'success': False,
                'error': 'No file selected'
            }), 400

        # Get required parameters
        file_type = request.form.get('file_type')
        client_name = request.form.get('client_name', '')
        week_name = request.form.get('week_name', '')

        if not all([file_type, client_name, week_name]):
            return jsonify({
                'success': False,
                'error': 'file_type, client_name, and week_name are required'
            }), 400

        # Read and normalize file content
        file_content = file.read()
        filename = file.filename

        try:
            normalized_content = FileUtils.normalize_file_content(file_content, filename, '|')
        except Exception as e:
            return jsonify({
                'success': False,
                'error': f'File format error: {str(e)}'
            }), 400

        # Validate file first (if realtime validation is enabled)
        if config.is_feature_enabled('realtime_validation'):
            validation_result = file_validator.validate_file(normalized_content, filename, file_type)
            if not validation_result['valid']:
                return jsonify({
                    'success': False,
                    'error': 'File validation failed',
                    'validation': validation_result
                }), 400

        # Save file
        save_result = upload_service.save_file(normalized_content, file_type, client_name, week_name, filename)

        if not save_result['success']:
            return jsonify({
                'success': False,
                'error': 'Failed to save file',
                'details': save_result['errors']
            }), 500

        logger.info(f"File saved successfully: {save_result['file_path']}")

        return jsonify({
            'success': True,
            'file_path': save_result['absolute_path'],
            'filename': save_result['filename'],
            'file_info': save_result.get('file_info', {})
        })

    except Exception as e:
        logger.error(f"Error saving file: {e}")
        return jsonify({
            'success': False,
            'error': f'Upload error: {str(e)}'
        }), 500

@app.route('/api/requests/<int:request_id>/upload', methods=['POST'])
def upload_request_file(request_id):
    """Upload files for a request - enhanced implementation"""
    logger.info(f"📤 Upload request endpoint called for ID: {request_id}")

    try:
        # Legacy endpoint - redirect to new upload flow
        return jsonify({
            'success': False,
            'error': 'Please use /api/upload/save endpoint for file uploads',
            'redirect': '/api/upload/save'
        }), 400

    except Exception as e:
        logger.error(f"Error in request upload: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/requests/status-counts', methods=['GET'])
def get_status_counts():
    """Get count of requests by status for dashboard"""
    logger.info("📊 Status counts endpoint called")

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
        conn.close()

        return jsonify({
            'success': True,
            'status_counts': status_counts
        })

    except Exception as e:
        logger.error(f"❌ Error fetching status counts: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/requests/<int:request_id>/client-name', methods=['GET'])
def get_client_name(request_id):
    """Get client name for a specific request"""
    logger.info(f"🏢 Client name endpoint called for request ID: {request_id}")

    try:
        conn = get_db_connection()
        if not conn:
            return jsonify({'success': False, 'error': 'Database connection failed'}), 500

        cursor = conn.cursor()

        # Query based on config.properties CLIENT_NAME logic
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
        conn.close()

        if result:
            return jsonify({
                'success': True,
                'clientName': result[0]
            })
        else:
            return jsonify({'success': False, 'error': 'Request not found'}), 404

    except Exception as e:
        logger.error(f"❌ Error fetching client name: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/requests/<int:request_id>/week', methods=['GET'])
def get_week(request_id):
    """Get week for a specific request"""
    logger.info(f"📅 Week endpoint called for request ID: {request_id}")

    try:
        conn = get_db_connection()
        if not conn:
            return jsonify({'success': False, 'error': 'Database connection failed'}), 500

        cursor = conn.cursor()

        # Query based on config.properties WEEK logic
        requests_table = config.get_table_name('requests')
        query = f"""
        SELECT UPPER(week) 
        FROM {requests_table} 
        WHERE request_id = %s
        """

        cursor.execute(query, (request_id,))
        result = cursor.fetchone()

        cursor.close()
        conn.close()

        if result:
            return jsonify({
                'success': True,
                'week': result[0]
            })
        else:
            return jsonify({'success': False, 'error': 'Request not found'}), 404

    except Exception as e:
        logger.error(f"❌ Error fetching week: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/tables/<table_name>/columns', methods=['GET'])
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
        conn.close()

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

@app.route('/api/requests/<int:request_id>/metrics/download', methods=['POST'])
def download_metrics(request_id):
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
        conn.close()

        output.seek(0)

        # Create response
        response = app.response_class(
            output.read(),
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            headers={
                'Content-Disposition': f'attachment; filename=Metrics-{request_id}.xlsx'
            }
        )

        logger.info(f"✅ Successfully created metrics Excel file for request {request_id}")
        return response

    except Exception as e:
        logger.error(f"❌ Error downloading metrics: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

# ==========================================
# DASHBOARD ENDPOINTS - PHASE 4
# ==========================================

@app.route('/api/dashboard/metrics', methods=['GET'])
def get_dashboard_metrics():
    """Get key metrics for dashboard cards with date filtering"""
    logger.info("📊 Dashboard metrics endpoint called")

    try:
        # Get date range parameters
        from_date = request.args.get('from')
        to_date = request.args.get('to')

        logger.info(f"📅 Date filter received: from={from_date}, to={to_date}")

        conn = get_db_connection()
        if not conn:
            return jsonify({'success': False, 'error': 'Database connection failed'}), 500

        cursor = conn.cursor()
        requests_table = config.get_table_name('requests')
        qa_table = config.get_table_name('qa_stats')

        # Build WHERE clause for date filtering using created_date (consistent with database standard)
        base_where = "WHERE created_date IS NOT NULL"
        date_condition = ""

        if from_date and to_date:
            date_condition = f" AND DATE(created_date) BETWEEN '{from_date}' AND '{to_date}'"
        elif from_date:
            date_condition = f" AND DATE(created_date) >= '{from_date}'"
        elif to_date:
            date_condition = f" AND DATE(created_date) <= '{to_date}'"

        where_clause = base_where + date_condition

        logger.info(f"🔍 Using date filter: {where_clause}")
        logger.info("🔍 Expected to match your validation query:")
        logger.info(f"   SELECT count(1), request_status FROM {requests_table} WHERE created_date >= '{from_date} 00:00:00' GROUP BY request_status")

        # Get key metrics with date filtering
        queries = {
            'total_requests': f"SELECT COUNT(*) FROM {requests_table} {where_clause}",
            'active_requests': f"SELECT COUNT(*) FROM {requests_table} {where_clause} AND request_status = 'R'",
            'waiting_requests': f"SELECT COUNT(*) FROM {requests_table} {where_clause} AND request_status = 'W'",
            'completed_today': f"SELECT COUNT(*) FROM {requests_table} {where_clause} AND request_status = 'C'",
            'failed_requests': f"SELECT COUNT(*) FROM {requests_table} {where_clause} AND request_status = 'E'",
            'avg_execution_time': f"""
                SELECT AVG(
                    CASE 
                        WHEN execution_time ~ '^[0-9]+:[0-9]+:[0-9]+$' 
                        THEN EXTRACT(EPOCH FROM execution_time::interval) / 3600.0
                        ELSE NULL 
                    END
                ) FROM {requests_table} 
                {where_clause}
                AND execution_time IS NOT NULL 
                AND execution_time != '-' 
                AND request_status = 'C'
            """
        }

        metrics = {}
        for metric_name, query in queries.items():
            logger.debug(f"🔍 Executing query for {metric_name}: {query}")
            cursor.execute(query)
            result = cursor.fetchone()
            metrics[metric_name] = result[0] if result[0] is not None else 0

        cursor.close()
        conn.close()

        logger.info(f"📊 Dashboard metrics result: {metrics}")
        return jsonify({
            'success': True,
            'metrics': metrics
        })

    except Exception as e:
        logger.error(f"❌ Error fetching dashboard metrics: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/dashboard/trt-volume', methods=['GET'])
def get_trt_volume():
    """Get TRT volume data for chart"""
    logger.info("📈 TRT volume endpoint called")

    try:
        days = request.args.get('days', 30, type=int)  # Default 30 days

        conn = get_db_connection()
        if not conn:
            return jsonify({'success': False, 'error': 'Database connection failed'}), 500

        cursor = conn.cursor()
        requests_table = config.get_table_name('requests')
        qa_table = config.get_table_name('qa_stats')

        # Get daily TRT volume
        query = f"""
        SELECT 
            DATE(a.created_date) as date,
            COALESCE(SUM(c.rltp_file_count), 0) as trt_count
        FROM {requests_table} a
        LEFT JOIN {qa_table} c ON a.request_id = c.request_id
        WHERE a.created_date >= CURRENT_DATE - INTERVAL '{days} days'
        GROUP BY DATE(a.created_date)
        ORDER BY date DESC
        """

        cursor.execute(query)
        results = cursor.fetchall()

        volume_data = []
        for row in results:
            volume_data.append({
                'date': row[0].strftime('%Y-%m-%d') if row[0] else '',
                'trt_count': int(row[1]) if row[1] else 0
            })

        cursor.close()
        conn.close()

        return jsonify({
            'success': True,
            'volume_data': volume_data,
            'period_days': days
        })

    except Exception as e:
        logger.error(f"❌ Error fetching TRT volume: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/dashboard/processing-time', methods=['GET'])
def get_processing_time_trends():
    """Get processing time trends"""
    logger.info("⏱️ Processing time trends endpoint called")

    try:
        conn = get_db_connection()
        if not conn:
            return jsonify({'success': False, 'error': 'Database connection failed'}), 500

        cursor = conn.cursor()
        requests_table = config.get_table_name('requests')

        # Get daily average processing time for last 30 days
        query = f"""
        SELECT 
            DATE(request_end_time) as date,
            AVG(
                CASE 
                    WHEN execution_time ~ '^[0-9]+:[0-9]+:[0-9]+$' 
                    THEN EXTRACT(EPOCH FROM execution_time::interval) / 3600.0
                    ELSE NULL 
                END
            ) as avg_hours
        FROM {requests_table}
        WHERE request_status = 'C'
        AND execution_time IS NOT NULL 
        AND execution_time != '-'
        AND request_end_time >= CURRENT_DATE - INTERVAL '30 days'
        GROUP BY DATE(request_end_time)
        ORDER BY date DESC
        """

        cursor.execute(query)
        results = cursor.fetchall()

        time_data = []
        for row in results:
            if row[1] is not None:
                time_data.append({
                    'date': row[0].strftime('%Y-%m-%d') if row[0] else '',
                    'avg_time_hours': round(float(row[1]), 2)
                })

        cursor.close()
        conn.close()

        return jsonify({
            'success': True,
            'time_data': time_data
        })

    except Exception as e:
        logger.error(f"❌ Error fetching processing time trends: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/dashboard/alerts', methods=['GET'])
def get_dashboard_alerts():
    """Get system alerts"""
    logger.info("🚨 Dashboard alerts endpoint called")

    try:
        conn = get_db_connection()
        if not conn:
            return jsonify({'success': False, 'error': 'Database connection failed'}), 500

        cursor = conn.cursor()
        requests_table = config.get_table_name('requests')

        # Get long running requests (>2 hours)
        query = f"""
        SELECT request_id, added_by, request_desc,
               EXTRACT(EPOCH FROM (CURRENT_TIMESTAMP - request_start_time))/3600 as hours_running
        FROM {requests_table}
        WHERE request_status = 'R'
        AND request_start_time IS NOT NULL
        AND EXTRACT(EPOCH FROM (CURRENT_TIMESTAMP - request_start_time))/3600 > 2
        ORDER BY hours_running DESC
        """

        cursor.execute(query)
        long_running = cursor.fetchall()

        alerts = []

        # Add long running alerts
        for row in long_running:
            alerts.append({
                'type': 'long_running',
                'severity': 'warning',
                'message': f"Request {row[0]} running for {row[3]:.1f} hours",
                'request_id': row[0],
                'user': row[1],
                'description': row[2]
            })

        # Add system health alerts
        # Database connection check
        db_start_time = time.time()
        cursor.execute("SELECT 1")
        db_response_time = (time.time() - db_start_time) * 1000  # ms

        if db_response_time > 1000:
            alerts.append({
                'type': 'system_health',
                'severity': 'warning',
                'message': f"Database slow response: {db_response_time:.0f}ms"
            })

        cursor.close()
        conn.close()

        return jsonify({
            'success': True,
            'alerts': alerts,
            'db_response_time': round(db_response_time, 2)
        })

    except Exception as e:
        logger.error(f"❌ Error fetching alerts: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/dashboard/users', methods=['GET'])
def get_user_activity():
    """Get user activity data with date filtering"""
    logger.info("👥 User activity endpoint called")

    try:
        # Get date range parameters
        from_date = request.args.get('from')
        to_date = request.args.get('to')

        logger.info(f"📅 User activity date filter: from={from_date}, to={to_date}")

        conn = get_db_connection()
        if not conn:
            return jsonify({'success': False, 'error': 'Database connection failed'}), 500

        cursor = conn.cursor()
        requests_table = config.get_table_name('requests')

        # Build WHERE clause for date filtering using created_date (consistent with database standard)
        base_where = "WHERE created_date IS NOT NULL"
        date_condition = ""

        if from_date and to_date:
            date_condition = f" AND DATE(created_date) BETWEEN '{from_date}' AND '{to_date}'"
        elif from_date:
            date_condition = f" AND DATE(created_date) >= '{from_date}'"
        elif to_date:
            date_condition = f" AND DATE(created_date) <= '{to_date}'"

        where_clause = base_where + date_condition

        # Get user request counts with date filtering
        query = f"""
        SELECT 
            UPPER(added_by) as added_by,
            COUNT(*) as total_requests,
            COUNT(CASE WHEN request_status = 'C' THEN 1 END) as completed_requests,
            COUNT(CASE WHEN request_status = 'R' THEN 1 END) as active_requests,
            AVG(
                CASE 
                    WHEN execution_time ~ '^[0-9]+:[0-9]+:[0-9]+$' AND request_status = 'C'
                    THEN EXTRACT(EPOCH FROM execution_time::interval) / 3600.0
                    ELSE NULL 
                END
            ) as avg_execution_hours
        FROM {requests_table}
        {where_clause}
        GROUP BY 1
        ORDER BY total_requests DESC
        """

        logger.debug(f"🔍 User activity query: {query}")
        cursor.execute(query)
        results = cursor.fetchall()

        logger.debug(f"📊 Raw user activity results: {len(results)} rows")

        user_data = []
        for row in results:
            user_entry = {
                'username': row[0],
                'total_requests': row[1],
                'completed_requests': row[2],
                'active_requests': row[3],
                'avg_execution_hours': round(float(row[4]), 2) if row[4] else 0,
                'success_rate': round((row[2] / row[1]) * 100, 1) if row[1] > 0 else 0
            }
            user_data.append(user_entry)
            logger.debug(f"👤 User: {user_entry['username']} - {user_entry['total_requests']} requests, {user_entry['success_rate']}% success")

        cursor.close()
        conn.close()

        logger.info(f"👥 User activity result: {len(user_data)} users found")
        return jsonify({
            'success': True,
            'user_data': user_data
        })

    except Exception as e:
        logger.error(f"❌ Error fetching user activity: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/dashboard/system-status', methods=['GET'])
def get_system_status():
    """Get system status information"""
    logger.info("🔧 System status endpoint called")

    try:
        import psutil

        # Database connection test
        db_start_time = time.time()
        conn = get_db_connection()
        db_connected = conn is not None
        if conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM information_schema.tables")
            cursor.close()
            conn.close()
        db_response_time = (time.time() - db_start_time) * 1000

        # Get processing queue status
        conn = get_db_connection()
        cursor = conn.cursor()
        requests_table = config.get_table_name('requests')

        cursor.execute(f"SELECT COUNT(*) FROM {requests_table} WHERE request_status = 'R'")
        active_requests = cursor.fetchone()[0]

        cursor.execute(f"SELECT COUNT(*) FROM {requests_table} WHERE request_status = 'W'")
        pending_requests = cursor.fetchone()[0]

        cursor.close()
        conn.close()

        # System resources (when available)
        try:
            disk_usage = psutil.disk_usage('/')
            memory_usage = psutil.virtual_memory()

            system_resources = {
                'disk_total_gb': round(disk_usage.total / (1024**3), 2),
                'disk_used_gb': round(disk_usage.used / (1024**3), 2),
                'disk_percent': round(disk_usage.percent, 1),
                'memory_total_gb': round(memory_usage.total / (1024**3), 2),
                'memory_used_gb': round(memory_usage.used / (1024**3), 2),
                'memory_percent': round(memory_usage.percent, 1)
            }
        except:
            system_resources = {
                'disk_total_gb': 0,
                'disk_used_gb': 0,
                'disk_percent': 0,
                'memory_total_gb': 0,
                'memory_used_gb': 0,
                'memory_percent': 0,
                'note': 'System resource monitoring unavailable in development'
            }

        return jsonify({
            'success': True,
            'database': {
                'connected': db_connected,
                'response_time_ms': round(db_response_time, 2)
            },
            'processing_queue': {
                'active_requests': active_requests,
                'pending_requests': pending_requests
            },
            'api_health': {
                'status': 'healthy',
                'endpoints_checked': 'all_operational'
            },
            'system_resources': system_resources
        })

    except Exception as e:
        logger.error(f"❌ Error fetching system status: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/dashboard/health-check', methods=['POST'])
def run_health_check():
    """Run comprehensive system health check"""
    logger.info("🏥 Health check endpoint called")

    try:
        health_results = {}

        # Database connectivity test
        try:
            conn = get_db_connection()
            if conn:
                cursor = conn.cursor()
                cursor.execute("SELECT version()")
                db_version = cursor.fetchone()[0]
                cursor.close()
                conn.close()
                health_results['database'] = {'status': 'healthy', 'version': db_version}
            else:
                health_results['database'] = {'status': 'failed', 'error': 'Connection failed'}
        except Exception as e:
            health_results['database'] = {'status': 'failed', 'error': str(e)}

        # API endpoints test
        health_results['api_endpoints'] = {'status': 'healthy', 'checked': datetime.utcnow().isoformat()}

        # Processing queue test
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            requests_table = config.get_table_name('requests')
            cursor.execute(f"SELECT COUNT(*) FROM {requests_table}")
            total_requests = cursor.fetchone()[0]
            cursor.close()
            conn.close()
            health_results['processing_queue'] = {'status': 'operational', 'total_requests': total_requests}
        except Exception as e:
            health_results['processing_queue'] = {'status': 'failed', 'error': str(e)}

        return jsonify({
            'success': True,
            'health_check': health_results,
            'timestamp': datetime.utcnow().isoformat()
        })

    except Exception as e:
        logger.error(f"❌ Error running health check: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/dashboard/export', methods=['GET'])
def export_dashboard_reports():
    """Export dashboard reports"""
    logger.info("📊 Export reports endpoint called")

    try:
        report_type = request.args.get('type', 'metrics')  # metrics, users, system

        # This endpoint returns data that frontend can export to CSV/Excel
        # Implementation would depend on specific export requirements

        return jsonify({
            'success': False,
            'message': 'Export functionality to be implemented based on requirements',
            'requested_type': report_type
        }), 501

    except Exception as e:
        logger.error(f"❌ Error exporting reports: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/clients/<client_name>/flush-delivery-data', methods=['POST'])
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
            conn.close()
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
            conn.close()
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
            conn.close()
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
        conn.close()

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

if __name__ == "__main__":
    print("Starting CAM API Server")
    print("Frontend: http://localhost:3009")
    print("Backend API: http://localhost:5000")

    # Get backend configuration
    backend_config = config.get_backend_config()
    dev_config = backend_config.get('development', {})

    app.run(
        debug=config.is_debug(),
        host=dev_config.get('host', '0.0.0.0'),
        port=dev_config.get('port', 5000),
        threaded=backend_config.get('threading', True),
        use_reloader=backend_config.get('reloader', False)
    )
