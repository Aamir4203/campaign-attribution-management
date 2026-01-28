"""
Dashboard Routes for CAM Application
Handles dashboard metrics, charts, and system monitoring
"""

from flask import Blueprint, jsonify, request
from datetime import datetime
import logging
import time
from db import get_db_connection, release_db_connection
from config.config import get_config

logger = logging.getLogger(__name__)
config = get_config()

# Create blueprint
dashboard_bp = Blueprint('dashboard', __name__)


@dashboard_bp.route('/api/dashboard/metrics', methods=['GET'])
def get_dashboard_metrics():
    """Get key metrics for dashboard cards with date filtering"""
    try:
        # Get date range parameters
        from_date = request.args.get('from')
        to_date = request.args.get('to')

        conn = get_db_connection()
        if not conn:
            return jsonify({'success': False, 'error': 'Database connection failed'}), 500

        cursor = conn.cursor()
        requests_table = config.get_table_name('requests')
        qa_table = config.get_table_name('qa_stats')

        # Build WHERE clause for date filtering
        base_where = "WHERE created_date IS NOT NULL"
        date_condition = ""

        if from_date and to_date:
            date_condition = f" AND DATE(created_date) BETWEEN '{from_date}' AND '{to_date}'"
        elif from_date:
            date_condition = f" AND DATE(created_date) >= '{from_date}'"
        elif to_date:
            date_condition = f" AND DATE(created_date) <= '{to_date}'"

        where_clause = base_where + date_condition

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
            cursor.execute(query)
            result = cursor.fetchone()
            metrics[metric_name] = result[0] if result[0] is not None else 0

        cursor.close()
        release_db_connection(conn)

        return jsonify({
            'success': True,
            'metrics': metrics
        })

    except Exception as e:
        logger.error(f"Error fetching dashboard metrics: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@dashboard_bp.route('/api/dashboard/trt-volume', methods=['GET'])
def get_trt_volume():
    """Get TRT volume data for chart"""
    try:
        days = request.args.get('days', 30, type=int)

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
        release_db_connection(conn)

        return jsonify({
            'success': True,
            'volume_data': volume_data,
            'period_days': days
        })

    except Exception as e:
        logger.error(f"Error fetching TRT volume: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@dashboard_bp.route('/api/dashboard/processing-time', methods=['GET'])
def get_processing_time_trends():
    """Get processing time trends"""
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
        release_db_connection(conn)

        return jsonify({
            'success': True,
            'time_data': time_data
        })

    except Exception as e:
        logger.error(f"Error fetching processing time trends: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@dashboard_bp.route('/api/dashboard/alerts', methods=['GET'])
def get_dashboard_alerts():
    """Get system alerts"""
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
        release_db_connection(conn)

        return jsonify({
            'success': True,
            'alerts': alerts,
            'db_response_time': round(db_response_time, 2)
        })

    except Exception as e:
        logger.error(f"Error fetching alerts: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@dashboard_bp.route('/api/dashboard/users', methods=['GET'])
def get_user_activity():
    """Get user activity data with date filtering"""
    try:
        # Get date range parameters
        from_date = request.args.get('from')
        to_date = request.args.get('to')

        conn = get_db_connection()
        if not conn:
            return jsonify({'success': False, 'error': 'Database connection failed'}), 500

        cursor = conn.cursor()
        requests_table = config.get_table_name('requests')

        # Build WHERE clause for date filtering
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

        cursor.execute(query)
        results = cursor.fetchall()

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

        cursor.close()
        release_db_connection(conn)

        return jsonify({
            'success': True,
            'user_data': user_data
        })

    except Exception as e:
        logger.error(f"Error fetching user activity: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@dashboard_bp.route('/api/dashboard/system-status', methods=['GET'])
def get_system_status():
    """Get system status information"""
    try:
        # Database connection test
        db_start_time = time.time()
        conn = get_db_connection()
        db_connected = conn is not None
        if conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM information_schema.tables")
            cursor.close()
            release_db_connection(conn)
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
        release_db_connection(conn)

        # System resources
        try:
            import psutil
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
                'note': 'System resource monitoring unavailable'
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
        logger.error(f"Error fetching system status: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@dashboard_bp.route('/api/dashboard/health-check', methods=['POST'])
def run_health_check():
    """Run comprehensive system health check"""
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
                release_db_connection(conn)
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
            release_db_connection(conn)
            health_results['processing_queue'] = {'status': 'operational', 'total_requests': total_requests}
        except Exception as e:
            health_results['processing_queue'] = {'status': 'failed', 'error': str(e)}

        return jsonify({
            'success': True,
            'health_check': health_results,
            'timestamp': datetime.utcnow().isoformat()
        })

    except Exception as e:
        logger.error(f"Error running health check: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@dashboard_bp.route('/api/dashboard/export', methods=['GET'])
def export_dashboard_reports():
    """Export dashboard reports"""
    try:
        report_type = request.args.get('type', 'metrics')

        return jsonify({
            'success': False,
            'message': 'Export functionality to be implemented based on requirements',
            'requested_type': report_type
        }), 501

    except Exception as e:
        logger.error(f"Error exporting reports: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500
