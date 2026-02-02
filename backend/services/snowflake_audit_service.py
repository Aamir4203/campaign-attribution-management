#!/usr/bin/env python3
"""
Snowflake Audit Service for CAM Application
Handles Snowflake LPT account connections and audit-specific data upload operations
"""

import os
import logging
import snowflake.connector
from snowflake.connector import DictCursor
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple
from pathlib import Path
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import serialization
from config.config import get_config

logger = logging.getLogger(__name__)


class SnowflakeAuditService:
    """Service for handling Snowflake Audit (LPT Account) operations"""

    def __init__(self):
        """Initialize Snowflake Audit service with LPT account configuration"""
        self.config = get_config()
        self.audit_config = self.config.get_snowflake_audit_config()
        self.connection = None
        self.private_key_bytes = None

        # Get credentials from environment variables (SF_AUDIT_ prefix)
        self.account = os.getenv('SF_AUDIT_ACCOUNT')
        self.user = os.getenv('SF_AUDIT_USER')
        self.private_key_path = os.getenv('SF_AUDIT_PRIVATE_KEY_PATH')
        self.private_key_passphrase = os.getenv('SF_AUDIT_PRIVATE_KEY_PASSPHRASE')
        self.warehouse = os.getenv('SF_AUDIT_WAREHOUSE')
        self.database = os.getenv('SF_AUDIT_DATABASE')
        self.schema = os.getenv('SF_AUDIT_SCHEMA')
        self.role = os.getenv('SF_AUDIT_ROLE')

        # Validate credentials
        if not all([self.account, self.user, self.warehouse, self.database, self.schema]):
            logger.error("Missing required LPT Snowflake credentials in environment variables")
            raise ValueError("LPT Snowflake credentials not configured properly")

        if not self.private_key_path:
            logger.error("Private key path is required for LPT authentication")
            raise ValueError("Private key path not configured")

        # Load private key
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

            logger.debug(f"Loading private key from {key_path}")

            # Read encrypted private key
            with open(key_path, 'rb') as key_file:
                private_key_data = key_file.read()

            # Decrypt private key with passphrase
            passphrase_bytes = self.private_key_passphrase.encode() if self.private_key_passphrase else None

            private_key = serialization.load_pem_private_key(
                private_key_data,
                password=passphrase_bytes,
                backend=default_backend()
            )

            # Get the key in DER format for Snowflake
            self.private_key_bytes = private_key.private_bytes(
                encoding=serialization.Encoding.DER,
                format=serialization.PrivateFormat.PKCS8,
                encryption_algorithm=serialization.NoEncryption()
            )

            logger.info("LPT private key loaded successfully")

        except Exception as e:
            logger.error(f"Failed to load LPT private key: {e}")
            raise

    def connect(self) -> snowflake.connector.SnowflakeConnection:
        """
        Establish connection to LPT Snowflake account using private key authentication

        Returns:
            Snowflake connection object
        """
        try:
            if self.connection and not self.connection.is_closed():
                return self.connection

            logger.info(f"Connecting to LPT Snowflake: {self.account}")

            # Build connection parameters
            conn_params = {
                'account': self.account,
                'user': self.user,
                'warehouse': self.warehouse,
                'database': self.database,
                'schema': self.schema,
                'private_key': self.private_key_bytes
            }

            # Add role if specified
            if self.role:
                conn_params['role'] = self.role

            self.connection = snowflake.connector.connect(**conn_params)

            logger.info(f"Connected to LPT: {self.database}.{self.schema}")
            return self.connection

        except Exception as e:
            logger.error(f"LPT connection failed: {e}")
            raise

    def disconnect(self):
        """Close LPT Snowflake connection"""
        if self.connection and not self.connection.is_closed():
            self.connection.close()
            logger.info("LPT Snowflake connection closed")

    def analyze_dates_in_source(self, source_table: str) -> List[Dict[str, Any]]:
        """
        Analyze del_date column in source table and group by year/month

        Args:
            source_table: Source table name to analyze

        Returns:
            List of date groups with year, month, date range, and count
            Example: [
                {'year': 2026, 'month': 'JANUARY', 'month_num': 1,
                 'min_date': '2026-01-01', 'max_date': '2026-01-31', 'count': 1000},
                ...
            ]
        """
        try:
            logger.info(f"Analyzing dates in {source_table}")

            # Get source database connection (PostgreSQL)
            from db import get_db_connection, release_db_connection
            conn = get_db_connection()
            if not conn:
                raise Exception("Failed to get database connection")

            cursor = conn.cursor()

            # Get date analysis config
            date_config = self.audit_config.get('date_analysis', {})
            source_column = date_config.get('source_column', 'del_date')
            month_names = date_config.get('month_names', {})

            # Query to analyze dates (cast to DATE first to handle VARCHAR columns)
            query = f"""
            SELECT
                EXTRACT(YEAR FROM {source_column}::DATE)::INTEGER as year,
                EXTRACT(MONTH FROM {source_column}::DATE)::INTEGER as month_num,
                MIN({source_column}::DATE) as min_date,
                MAX({source_column}::DATE) as max_date,
                COUNT(*)::INTEGER as record_count
            FROM {source_table}
            WHERE {source_column} IS NOT NULL AND {source_column} != ''
            GROUP BY EXTRACT(YEAR FROM {source_column}::DATE), EXTRACT(MONTH FROM {source_column}::DATE)
            ORDER BY year, month_num
            """

            cursor.execute(query)
            results = cursor.fetchall()

            cursor.close()
            release_db_connection(conn)

            # Format results with month names
            date_groups = []
            for row in results:
                year, month_num, min_date, max_date, count = row
                month_name = month_names.get(month_num, f"MONTH_{month_num}")

                date_groups.append({
                    'year': year,
                    'month': month_name,
                    'month_num': month_num,
                    'min_date': str(min_date),
                    'max_date': str(max_date),
                    'count': count
                })

            logger.info(f"Found {len(date_groups)} date groups")
            for group in date_groups:
                logger.debug(f"{group['year']}-{group['month']}: {group['min_date']} to {group['max_date']} ({group['count']:,} records)")

            return date_groups

        except Exception as e:
            logger.error(f"Failed to analyze dates: {e}")
            raise

    def generate_audit_table_name(self, year: int, month: str) -> str:
        """
        Generate audit table name based on year and month

        Args:
            year: Year (e.g., 2026)
            month: Month name (e.g., "JANUARY")

        Returns:
            Table name (e.g., "CUSTOM_ZX_STATS_MASTER_2026_JANUARY")
        """
        table_config = self.audit_config.get('table', {})
        prefix = table_config.get('prefix', 'CUSTOM_ZX_STATS_MASTER')
        name_template = table_config.get('name_template', '{prefix}_{year}_{month}')

        table_name = name_template.format(
            prefix=prefix,
            year=year,
            month=month.upper()
        )

        logger.debug(f"Generated table name: {table_name}")
        return table_name

    def table_exists(self, table_name: str) -> bool:
        """
        Check if audit table exists in LPT Snowflake

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

            cursor.close()

            logger.debug(f"Table {table_name} exists: {exists}")
            return exists

        except Exception as e:
            logger.error(f"❌ Failed to check table existence: {e}")
            return False

    def create_audit_table(self, table_name: str) -> bool:
        """
        Create audit table with schema from config

        Args:
            table_name: Name of the table to create

        Returns:
            True if successful, False otherwise
        """
        try:
            conn = self.connect()
            cursor = conn.cursor()

            # Get table schema from config
            table_config = self.audit_config.get('table', {})
            cluster_by = table_config.get('cluster_by', '')
            columns_config = self.audit_config.get('columns', {})
            table_schema = columns_config.get('table_schema', [])

            if not table_schema:
                raise ValueError("Table schema not found in configuration")

            # Build CREATE TABLE statement
            column_defs = []
            for col in table_schema:
                col_def = f"{col['name']} {col['type']}"
                if col.get('autoincrement'):
                    col_def += " AUTOINCREMENT START 1 INCREMENT 1 ORDER"
                column_defs.append(col_def)

            # Add CLUSTER BY clause if specified
            cluster_clause = f" CLUSTER BY ({cluster_by})" if cluster_by else ""

            create_sql = f"""
                CREATE TABLE {table_name}{cluster_clause} (
                    {', '.join(column_defs)}
                )
            """

            logger.info(f"Creating audit table: {table_name}")
            logger.debug(f"SQL: {create_sql}")

            cursor.execute(create_sql)

            cursor.close()

            logger.info(f"Audit table created: {table_name}")
            return True

        except Exception as e:
            logger.error(f"Failed to create audit table {table_name}: {e}")
            return False

    def check_existing_data(self, table_name: str, client_name: str,
                           date_range: Tuple[str, str]) -> int:
        """
        Check for existing data in audit table for given client and date range

        Args:
            table_name: Audit table name
            client_name: Client name
            date_range: Tuple of (start_date, end_date)

        Returns:
            Number of existing records
        """
        try:
            conn = self.connect()
            cursor = conn.cursor()

            query = f"""
                SELECT COUNT(*)
                FROM {table_name}
                WHERE D_B_SEGMENT = '{client_name}'
                AND DELIVEREDDATE BETWEEN '{date_range[0]}' AND '{date_range[1]}'
            """

            cursor.execute(query)
            count = cursor.fetchone()[0]

            cursor.close()

            logger.info(f"Found {count:,} existing records for {client_name} ({date_range[0]} to {date_range[1]})")

            return count

        except Exception as e:
            logger.error(f"Failed to check existing data: {e}")
            return 0

    def remove_existing_data(self, table_name: str, client_name: str,
                            date_range: Tuple[str, str]) -> bool:
        """
        Remove existing data from audit table (Option A: Simple Delete)

        Args:
            table_name: Audit table name
            client_name: Client name
            date_range: Tuple of (start_date, end_date)

        Returns:
            True if successful, False otherwise
        """
        try:
            conn = self.connect()
            cursor = conn.cursor()

            delete_query = f"""
                DELETE FROM {table_name}
                WHERE D_B_SEGMENT = '{client_name}'
                AND DELIVEREDDATE BETWEEN '{date_range[0]}' AND '{date_range[1]}'
            """

            logger.info(f"Removing existing data for {client_name} ({date_range[0]} to {date_range[1]})")

            cursor.execute(delete_query)
            rows_deleted = cursor.rowcount

            cursor.close()

            logger.info(f"Deleted {rows_deleted:,} existing records")
            return True

        except Exception as e:
            logger.error(f"Failed to remove existing data: {e}")
            return False

    def write_audit_file(self, source_table: str, client_name: str,
                        date_range: Tuple[str, str], output_path: str) -> Dict[str, Any]:
        """
        Write audit file with fixed header from source table

        Args:
            source_table: Source PostgreSQL table name
            client_name: Client name
            date_range: Tuple of (start_date, end_date)
            output_path: Output file path

        Returns:
            Dict with file info (success, path, row_count, size)
        """
        try:
            logger.info(f"Writing audit file for {client_name} ({date_range[0]} to {date_range[1]})")

            # Get source database connection
            from db import get_db_connection, release_db_connection
            conn = get_db_connection()
            if not conn:
                raise Exception("Failed to get database connection")

            cursor = conn.cursor()

            # Get fixed header configuration
            columns_config = self.audit_config.get('columns', {})
            fixed_header = columns_config.get('fixed_header', [])
            file_delimiter = self.audit_config.get('file_delimiter', '|')

            # Build SELECT query from config
            select_columns = []
            header_names = []

            for col in fixed_header:
                source_col = col.get('source_column')
                col_name = col.get('name')
                transform = col.get('transform')
                is_param = col.get('is_parameter', False)
                alias = col.get('alias')

                if is_param:
                    # Replace parameter with actual value
                    if source_col == 'client_name':
                        select_columns.append(f"'{client_name}' as {col_name}")
                    elif source_col == 'source_table':
                        select_columns.append(f"'{source_table}' as {col_name}")
                    else:
                        # Default: use client_name for backward compatibility
                        select_columns.append(f"'{client_name}' as {col_name}")
                elif transform:
                    # Use transformation
                    if alias:
                        select_columns.append(f"({transform}) as {alias}")
                    else:
                        select_columns.append(f"({transform}) as {col_name}")
                else:
                    # Direct column
                    if alias:
                        select_columns.append(f"{source_col} as {alias}")
                    else:
                        select_columns.append(source_col)

                header_names.append(col_name)

            # Build query (cast del_date to DATE for proper comparison)
            query = f"""
                SELECT {', '.join(select_columns)}
                FROM {source_table}
                WHERE del_date::DATE BETWEEN '{date_range[0]}'::DATE AND '{date_range[1]}'::DATE
            """

            logger.debug(f"SQL Query: {query}")

            # Execute query
            cursor.execute(query)

            # Write file with header
            os.makedirs(os.path.dirname(output_path), exist_ok=True)

            row_count = 0
            with open(output_path, 'w') as f:
                # Write header
                f.write(file_delimiter.join(header_names) + '\n')

                # Write data rows
                batch_size = self.audit_config.get('batch_size', 50000)
                while True:
                    rows = cursor.fetchmany(batch_size)
                    if not rows:
                        break

                    for row in rows:
                        # Convert None to empty string, format values
                        formatted_row = []
                        for val in row:
                            if val is None:
                                formatted_row.append('')
                            elif isinstance(val, (datetime, )):
                                formatted_row.append(val.strftime('%Y-%m-%d'))
                            else:
                                formatted_row.append(str(val))

                        f.write(file_delimiter.join(formatted_row) + '\n')
                        row_count += 1

            cursor.close()
            release_db_connection(conn)

            # Get file size
            file_size = os.path.getsize(output_path)
            file_size_mb = file_size / (1024 * 1024)

            logger.info(f"Audit file written: {row_count:,} rows, {file_size_mb:.2f} MB")

            return {
                'success': True,
                'file_path': output_path,
                'row_count': row_count,
                'file_size': file_size,
                'file_size_mb': file_size_mb
            }

        except Exception as e:
            logger.error(f"Failed to write audit file: {e}")
            return {
                'success': False,
                'error': str(e)
            }

    def upload_file_to_audit(self, file_path: str, table_name: str) -> Dict[str, Any]:
        """
        Upload file to LPT Snowflake audit table

        Args:
            file_path: Path to the file to upload
            table_name: Target audit table name

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

            # Get file format options
            file_delimiter = self.audit_config.get('file_delimiter', '|')

            # Build file format string
            format_options = (
                f"TYPE = 'CSV', "
                f"FIELD_DELIMITER = '{file_delimiter}', "
                f"SKIP_HEADER = 1, "
                f"NULL_IF = ('NULL', 'null', ''), "
                f"EMPTY_FIELD_AS_NULL = TRUE, "
                f"FIELD_OPTIONALLY_ENCLOSED_BY = '\"', "
                f"ERROR_ON_COLUMN_COUNT_MISMATCH = FALSE"
            )

            # Stage the file
            stage_name = f"@~/{table_name}_audit_stage"
            file_size_mb = os.path.getsize(file_path) / (1024 * 1024)
            logger.info(f"Staging file ({file_size_mb:.2f} MB) to LPT")

            put_sql = f"PUT file://{file_path} {stage_name} AUTO_COMPRESS=TRUE OVERWRITE=TRUE"
            cursor.execute(put_sql)

            logger.info(f"File staged, copying to {table_name}")

            copy_sql = f"""
                COPY INTO {table_name}
                FROM {stage_name}
                FILE_FORMAT = ({format_options})
                ON_ERROR = 'CONTINUE'
            """

            cursor.execute(copy_sql)

            # Get copy results
            copy_results = cursor.fetchone()
            if copy_results:
                result['rows_parsed'] = copy_results[2]
                result['rows_loaded'] = copy_results[3]
                result['success'] = True

                logger.info(f"Data copy completed: {result['rows_loaded']:,} rows")

            # Clean up stage
            cursor.execute(f"REMOVE {stage_name}")
            logger.debug("Staging area cleaned")

            cursor.close()

            return result

        except Exception as e:
            logger.error(f"Failed to upload file to LPT: {e}")
            result['errors'].append(str(e))
            return result

    def upload_to_audit(self, request_id: int, client_name: str,
                       source_table: str) -> Dict[str, Any]:
        """
        Main method: Upload data to audit LPT Snowflake account with month-based splitting

        Args:
            request_id: Request ID
            client_name: Client name
            source_table: Source PostgreSQL table name

        Returns:
            Dict with upload results
        """
        result = {
            'success': False,
            'files_uploaded': 0,
            'total_rows': 0,
            'tables_created': [],
            'errors': []
        }

        try:
            logger.info(f"Starting audit delivery for request {request_id}, client {client_name}")

            # Step 1: Analyze dates in source table
            date_groups = self.analyze_dates_in_source(source_table)

            if not date_groups:
                logger.warning("No data found in source table")
                result['errors'].append("No data found in source table")
                return result

            # Step 2: Process each month group
            temp_dir = self.audit_config.get('temp_dir', '/tmp/snowflake_audit_uploads')
            os.makedirs(temp_dir, exist_ok=True)

            for group in date_groups:
                year = group['year']
                month = group['month']
                date_range = (group['min_date'], group['max_date'])

                logger.info(f"Processing {year}-{month}: {date_range[0]} to {date_range[1]} ({group['count']:,} records)")

                # Step 3: Generate table name
                audit_table = self.generate_audit_table_name(year, month)

                # Step 4: Check if table exists, create if not
                if not self.table_exists(audit_table):
                    if not self.create_audit_table(audit_table):
                        error = f"Failed to create table {audit_table}"
                        logger.error(error)
                        result['errors'].append(error)
                        continue
                    result['tables_created'].append(audit_table)

                # Step 5: Check for existing data
                table_config = self.audit_config.get('table', {})
                if table_config.get('validate_existing_data', True):
                    existing_count = self.check_existing_data(audit_table, client_name, date_range)

                    # Step 6: Remove old data if exists
                    if existing_count > 0 and table_config.get('remove_old_data', True):
                        if not self.remove_existing_data(audit_table, client_name, date_range):
                            error = f"Failed to remove existing data from {audit_table}"
                            logger.error(error)
                            result['errors'].append(error)
                            continue

                # Step 7: Write file with audit header
                file_naming = self.audit_config.get('file_naming', {})
                timestamp = datetime.now().strftime(file_naming.get('timestamp_format', '%Y%m%d_%H%M%S'))
                filename = file_naming.get('format', 'AUDIT_{client_name}_{year}_{month}_{timestamp}.csv').format(
                    prefix=file_naming.get('prefix', 'AUDIT'),
                    client_name=client_name,
                    year=year,
                    month=month,
                    timestamp=timestamp
                )
                file_path = os.path.join(temp_dir, filename)

                file_result = self.write_audit_file(source_table, client_name, date_range, file_path)

                if not file_result['success']:
                    error = f"Failed to write audit file: {file_result.get('error')}"
                    logger.error(error)
                    result['errors'].append(error)
                    continue

                # Step 8: Upload file to Snowflake
                upload_result = self.upload_file_to_audit(file_path, audit_table)

                if not upload_result['success']:
                    error = f"Failed to upload to {audit_table}: {upload_result.get('errors')}"
                    logger.error(error)
                    result['errors'].append(error)
                    continue

                # Update result
                result['files_uploaded'] += 1
                result['total_rows'] += upload_result['rows_loaded']

                # Clean up temp file if configured
                if self.audit_config.get('purge_temp_files', True):
                    try:
                        os.remove(file_path)
                        logger.debug(f"Cleaned up temp file: {filename}")
                    except Exception as e:
                        logger.warning(f"Failed to clean up temp file: {e}")

                logger.info(f"{year}-{month} completed: {upload_result['rows_loaded']:,} rows")

            # Final result
            if result['files_uploaded'] > 0:
                result['success'] = True

            logger.info(f"Audit delivery completed: {result['files_uploaded']} files, {result['total_rows']:,} rows, {len(result['errors'])} errors")

            return result

        except Exception as e:
            logger.error(f"Audit upload failed: {e}")
            result['errors'].append(str(e))
            return result
        finally:
            self.disconnect()
