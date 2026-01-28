#!/usr/bin/env python3
"""
Database Connection Management for CAM Application
Provides thread-safe connection pooling for PostgreSQL database
"""

import logging
import psycopg2
from psycopg2 import pool
from config.config import get_config

logger = logging.getLogger(__name__)

# Load configuration
config = get_config()
DB_CONFIG = config.get_database_credentials()

# Initialize database connection pool
db_pool = None

def initialize_pool():
    """
    Initialize database connection pool on application startup.
    Should be called once when the application starts.
    """
    global db_pool

    try:
        db_pool = pool.SimpleConnectionPool(
            minconn=2,
            maxconn=10,
            connect_timeout=5,
            **DB_CONFIG
        )
        logger.info("✅ Database connection pool initialized successfully")
        logger.info(f"   Pool configuration: min=2, max=10, timeout=5s")
        return True
    except Exception as e:
        logger.error(f"❌ Failed to initialize database connection pool: {e}")
        db_pool = None
        return False


def get_db_connection():
    """
    Get database connection from pool - thread-safe and performant.

    Returns:
        psycopg2.connection: Database connection from pool, or None if failed
    """
    try:
        if db_pool:
            # Get connection from pool (much faster than creating new connection)
            conn = db_pool.getconn()
            return conn
        else:
            # Fallback to direct connection if pool failed to initialize
            logger.warning("Connection pool not available, using direct connection")
            conn = psycopg2.connect(**DB_CONFIG, connect_timeout=5)
            return conn

    except psycopg2.OperationalError as e:
        logger.warning(f"Database connection failed: {e}")
        return None
    except Exception as e:
        logger.error(f"Database connection error: {e}")
        return None


def release_db_connection(conn):
    """
    Return connection to pool or close it.
    Always call this in a finally block to ensure connections are returned.

    Args:
        conn: Database connection to release
    """
    try:
        if db_pool and conn:
            db_pool.putconn(conn)
        elif conn:
            conn.close()
    except Exception as e:
        logger.error(f"Error releasing connection: {e}")


def close_pool():
    """
    Close all connections in the pool.
    Should be called on application shutdown.
    """
    global db_pool

    try:
        if db_pool:
            db_pool.closeall()
            logger.info("Database connection pool closed")
    except Exception as e:
        logger.error(f"Error closing connection pool: {e}")


def get_pool_status():
    """
    Get current pool status for monitoring.

    Returns:
        dict: Pool status information
    """
    if not db_pool:
        return {
            'initialized': False,
            'error': 'Pool not initialized'
        }

    # Note: SimpleConnectionPool doesn't expose detailed metrics
    # For production, consider using ThreadedConnectionPool with custom tracking
    return {
        'initialized': True,
        'pool_type': 'SimpleConnectionPool',
        'min_connections': 2,
        'max_connections': 10
    }
