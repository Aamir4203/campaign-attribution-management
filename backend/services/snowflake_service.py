#!/usr/bin/env python3
"""
Snowflake Service for CAM Application
Handles Snowflake connections, table creation, and data upload operations
"""

import os
import logging
import snowflake.connector
from snowflake.connector import DictCursor
from datetime import datetime
from typing import Dict, List, Any, Optional
from pathlib import Path
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import serialization
from config.config import get_config

logger = logging.getLogger(__name__)

class SnowflakeService:
    """Service for handling Snowflake operations"""

    def __init__(self):
        """Initialize Snowflake service with configuration"""
        self.config = get_config()
        self.sf_config = self.config.get_snowflake_config()
        self.connection = None

        # Get credentials from environment variables
        self.account = os.getenv('SF_ACCOUNT')
        self.user = os.getenv('SF_USER')
        self.password = os.getenv('SF_PASSWORD')
        self.warehouse = os.getenv('SF_WAREHOUSE')
        self.database = os.getenv('SF_DATABASE')
        self.schema = os.getenv('SF_SCHEMA')
        self.role = os.getenv('SF_ROLE')

        # Private key authentication
        self.private_key_path = os.getenv('SF_PRIVATE_KEY_PATH')
        self.private_key_passphrase = os.getenv('SF_PRIVATE_KEY_PASSPHRASE')
        self.private_key = None

        # Validate credentials - need either password or private key
        if not all([self.account, self.user, self.warehouse]):
            logger.error("Missing required Snowflake credentials in environment variables")
            raise ValueError("Snowflake credentials not configured properly")

        if not self.password and not self.private_key_path:
            logger.error("Must provide either SF_PASSWORD or SF_PRIVATE_KEY_PATH")
            raise ValueError("No authentication method configured")

        # Load private key if configured
        if self.private_key_path:
            self._load_private_key()

    def _load_private_key(self):
        """Load and decrypt private key for authentication"""
        try:
            # Handle relative path from project root
            if not os.path.isabs(self.private_key_path):
                project_root = Path(__file__).parent.parent.parent
                key_path = project_root / self.private_key_path
            else:
                key_path = Path(self.private_key_path)

            if not key_path.exists():
                raise FileNotFoundError(f"Private key file not found: {key_path}")

            logger.info(f"Loading private key from: {key_path}")

            # Read encrypted private key
            with open(key_path, 'rb') as key_file:
                private_key_data = key_file.read()

            # Decrypt private key with passphrase
            passphrase_bytes = self.private_key_passphrase.encode() if self.private_key_passphrase else None

            self.private_key = serialization.load_pem_private_key(
                private_key_data,
                password=passphrase_bytes,
                backend=default_backend()
            )

            # Get the key in DER format for Snowflake
            self.private_key_bytes = self.private_key.private_bytes(
                encoding=serialization.Encoding.DER,
                format=serialization.PrivateFormat.PKCS8,
                encryption_algorithm=serialization.NoEncryption()
            )

            logger.info("Private key loaded and decrypted successfully")

        except Exception as e:
            logger.error(f"Failed to load private key: {e}")
            raise

    def connect(self) -> snowflake.connector.SnowflakeConnection:
        """
        Establish connection to Snowflake using password or private key authentication

        Returns:
            Snowflake connection object
        """
        try:
            if self.connection and not self.connection.is_closed():
                return self.connection

            logger.info(f"🔌 Establishing Snowflake connection ({self.account})...")

            # Build connection parameters
            conn_params = {
                'account': self.account,
                'user': self.user,
                'warehouse': self.warehouse,
                'database': self.database,
                'schema': self.schema
            }

            # Add role if specified
            if self.role:
                conn_params['role'] = self.role

            # Use private key authentication if available, otherwise use password
            if self.private_key_bytes:
                conn_params['private_key'] = self.private_key_bytes
            elif self.password:
                conn_params['password'] = self.password
            else:
                raise ValueError("No authentication method available")

            self.connection = snowflake.connector.connect(**conn_params)

            logger.info(f"✅ Connected to Snowflake: {self.database}.{self.schema}")
            return self.connection

        except Exception as e:
            logger.error(f"Failed to connect to Snowflake: {e}")
            raise

    def disconnect(self):
        """Close Snowflake connection"""
        if self.connection and not self.connection.is_closed():
            self.connection.close()
            logger.info("Snowflake connection closed")

    def generate_table_name(self, client_name: str, week: str) -> str:
        """
        Generate Snowflake table name based on template

        Args:
            client_name: Client name
            week: Week identifier

        Returns:
            Formatted table name
        """
        current_date = datetime.now().strftime('%Y%m%d')
        table_name = self.sf_config['table']['name_template'].format(
            client_name=client_name.upper(),
            week=week.upper(),
            date=current_date
        )
        return table_name + self.sf_config['table']['schema_suffix']

    def get_column_type(self, column_name: str, is_date_column: bool = False) -> str:
        """
        Determine Snowflake column type

        Args:
            column_name: Name of the column
            is_date_column: Whether this is a date column

        Returns:
            Snowflake data type
        """
        if is_date_column:
            return "DATE"
        return "VARCHAR"

    def get_table_info(self, table_name: str) -> Optional[Dict[str, Any]]:
        """
        Get table information including row count and creation date

        Args:
            table_name: Name of the table

        Returns:
            Dict with table info or None if table doesn't exist
        """
        try:
            conn = self.connect()
            cursor = conn.cursor()

            # Check if table exists and get metadata
            cursor.execute(f"SHOW TABLES LIKE '{table_name}'")
            table_info = cursor.fetchone()

            if not table_info:
                return None

            # Get row count
            cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
            row_count = cursor.fetchone()[0]

            # Parse table metadata (SHOW TABLES returns: created_on, name, schema_name, kind, ...)
            return {
                'exists': True,
                'created_on': table_info[0] if table_info else None,
                'name': table_info[1] if table_info and len(table_info) > 1 else table_name,
                'row_count': row_count
            }

        except Exception as e:
            logger.error(f"Failed to get table info: {e}")
            return None
        finally:
            if cursor:
                cursor.close()

    def create_table(self, table_name: str, columns: List[Dict[str, str]]) -> bool:
        """
        Create Snowflake table with specified columns

        Args:
            table_name: Name of the table to create
            columns: List of column definitions with 'name' and 'type'

        Returns:
            True if successful, False otherwise
        """
        try:
            conn = self.connect()
            cursor = conn.cursor()

            # Check if table exists and get info
            table_info = self.get_table_info(table_name)

            if table_info:
                created_date = table_info['created_on'].strftime('%Y-%m-%d %H:%M:%S') if table_info['created_on'] else 'unknown'
                row_count = table_info['row_count']

                if self.sf_config['table']['overwrite_on_reupload']:
                    logger.warning(f"⚠️ RE-UPLOAD DETECTED: Table '{table_name}' already exists")
                    logger.warning(f"⚠️ Original upload: {created_date} with {row_count:,} rows")
                    logger.warning(f"⚠️ Overwriting table (ALL EXISTING DATA WILL BE LOST)")

                    # Use CREATE OR REPLACE to make it atomic (safer than DROP then CREATE)
                    column_defs = [f"{col['name']} {col['type']}" for col in columns]
                    create_sql = f"""
                        CREATE OR REPLACE TABLE {table_name} (
                            {', '.join(column_defs)}
                        )
                    """

                    logger.info(f"🔄 Recreating table: {table_name}")
                    cursor.execute(create_sql)
                    logger.info(f"✅ Table recreated successfully")
                    return True
                else:
                    logger.warning(f"⚠️ RE-UPLOAD DETECTED: Table '{table_name}' already exists")
                    logger.warning(f"⚠️ Original upload: {created_date} with {row_count:,} rows")
                    logger.warning(f"⚠️ Skipping table creation (overwrite_on_reupload=false)")
                    logger.warning(f"⚠️ Schema mismatch may cause upload failure if columns don't match")
                    return True

            # Build CREATE TABLE statement for new table
            column_defs = [f"{col['name']} {col['type']}" for col in columns]
            create_sql = f"""
                CREATE TABLE {table_name} (
                    {', '.join(column_defs)}
                )
            """

            logger.info(f"📋 Creating new table: {table_name} ({len(columns)} columns)")
            cursor.execute(create_sql)

            logger.info(f"✅ Table created successfully")
            return True

        except Exception as e:
            logger.error(f"❌ Failed to create table {table_name}: {e}")
            return False
        finally:
            if cursor:
                cursor.close()

    def upload_file_to_snowflake(self, file_path: str, table_name: str,
                                   file_format_options: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Upload file to Snowflake table using PUT and COPY commands

        Args:
            file_path: Path to the file to upload
            table_name: Target Snowflake table name
            file_format_options: Optional file format options

        Returns:
            Dict with upload results
        """
        result = {
            'success': False,
            'rows_loaded': 0,
            'rows_parsed': 0,
            'errors': []
        }

        try:
            conn = self.connect()
            cursor = conn.cursor()

            # Default file format options
            if not file_format_options:
                file_format_options = {
                    'TYPE': 'CSV',
                    'FIELD_DELIMITER': self.sf_config['upload']['file_delimiter'],
                    'SKIP_HEADER': 1,
                    'NULL_IF': ['NULL', 'null', ''],
                    'EMPTY_FIELD_AS_NULL': True,
                    'FIELD_OPTIONALLY_ENCLOSED_BY': '"',
                    'ERROR_ON_COLUMN_COUNT_MISMATCH': False
                }

            # Build file format string
            def format_value(v):
                """Format value for Snowflake FILE_FORMAT"""
                if isinstance(v, str):
                    return f"'{v}'"
                elif isinstance(v, bool):
                    return str(v).upper()
                elif isinstance(v, list):
                    # Format list as ('val1', 'val2', 'val3')
                    formatted_items = ', '.join([f"'{item}'" for item in v])
                    return f"({formatted_items})"
                elif isinstance(v, (int, float)):
                    return str(v)
                else:
                    return str(v)

            format_options = ', '.join([f"{k} = {format_value(v)}"
                                       for k, v in file_format_options.items()])

            # Stage the file
            stage_name = f"@~/{table_name}_stage"
            file_size_mb = os.path.getsize(file_path) / (1024 * 1024)
            logger.info(f"📤 Staging file ({file_size_mb:.2f} MB) to Snowflake internal stage...")

            put_sql = f"PUT file://{file_path} {stage_name} AUTO_COMPRESS=TRUE OVERWRITE=TRUE"
            cursor.execute(put_sql)

            logger.info(f"✅ File staged successfully")

            # Copy data from stage to table
            logger.info(f"📥 Copying data to table {table_name}...")

            copy_sql = f"""
                COPY INTO {table_name}
                FROM {stage_name}
                FILE_FORMAT = ({format_options})
                ON_ERROR = 'CONTINUE'
            """

            cursor.execute(copy_sql)

            # Get copy results
            # COPY INTO returns: file, status, rows_parsed, rows_loaded, error_limit, errors_seen, ...
            copy_results = cursor.fetchone()
            if copy_results:
                result['rows_parsed'] = copy_results[2]  # rows_parsed column
                result['rows_loaded'] = copy_results[3]  # rows_loaded column (NOT column[1] which is status "LOADED")
                result['success'] = True

                logger.info(f"✅ Data copy completed: {result['rows_loaded']:,} rows loaded")

            # Clean up stage
            logger.info(f"🧹 Cleaning up staging area...")
            cursor.execute(f"REMOVE {stage_name}")
            logger.info(f"✅ Staging area cleaned")

            return result

        except Exception as e:
            logger.error(f"Failed to upload file to Snowflake: {e}")
            result['errors'].append(str(e))
            return result
        finally:
            if cursor:
                cursor.close()

    def get_table_columns(self, table_name: str) -> List[Dict[str, Any]]:
        """
        Get column information for a Snowflake table

        Args:
            table_name: Name of the table

        Returns:
            List of column information
        """
        try:
            conn = self.connect()
            cursor = conn.cursor(DictCursor)

            cursor.execute(f"DESC TABLE {table_name}")
            columns = cursor.fetchall()

            return columns

        except Exception as e:
            logger.error(f"Failed to get table columns: {e}")
            return []
        finally:
            if cursor:
                cursor.close()

    def execute_query(self, query: str) -> List[Dict[str, Any]]:
        """
        Execute a SQL query and return results

        Args:
            query: SQL query to execute

        Returns:
            Query results as list of dictionaries
        """
        try:
            conn = self.connect()
            cursor = conn.cursor(DictCursor)

            cursor.execute(query)
            results = cursor.fetchall()

            return results

        except Exception as e:
            logger.error(f"Failed to execute query: {e}")
            raise
        finally:
            if cursor:
                cursor.close()

    def table_exists(self, table_name: str) -> bool:
        """
        Check if table exists in Snowflake

        Args:
            table_name: Name of the table to check

        Returns:
            True if table exists, False otherwise
        """
        try:
            conn = self.connect()
            cursor = conn.cursor()

            cursor.execute(f"SHOW TABLES LIKE '{table_name}'")
            exists = cursor.fetchone() is not None

            return exists

        except Exception as e:
            logger.error(f"Failed to check table existence: {e}")
            return False
        finally:
            if cursor:
                cursor.close()

    def get_row_count(self, table_name: str) -> int:
        """
        Get row count for a table

        Args:
            table_name: Name of the table

        Returns:
            Number of rows in table
        """
        try:
            conn = self.connect()
            cursor = conn.cursor()

            cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
            count = cursor.fetchone()[0]

            return count

        except Exception as e:
            logger.error(f"Failed to get row count: {e}")
            return 0
        finally:
            if cursor:
                cursor.close()
