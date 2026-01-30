#!/usr/bin/env python3
"""
File Generator Utility for CAM Application
Generates pipe-separated files from PostgreSQL postback tables for Snowflake upload
"""

import os
import logging
import tempfile
import shutil
from typing import List, Dict, Any, Optional, Callable
from pathlib import Path
from db import get_db_connection, release_db_connection
from config.config import get_config

logger = logging.getLogger(__name__)

class FileGenerator:
    """Generate pipe-separated files from postback tables"""

    def __init__(self):
        """Initialize file generator with configuration"""
        self.config = get_config()
        self.sf_config = self.config.get_snowflake_config()
        self.delimiter = self.sf_config['upload']['file_delimiter']

    def get_standard_header_columns(self) -> List[Dict[str, str]]:
        """
        Get standard header column definitions

        Returns:
            List of standard column definitions with name and SQL expression
        """
        return [
            {'name': 'Md5hash', 'expr': 'Md5hash'},
            {'name': 'Segment', 'expr': 'Segment'},
            {'name': 'SubSeg', 'expr': 'SubSeg'},
            {'name': 'Decile', 'expr': 'Decile'},
            {'name': 'DeliveredFlag', 'expr': "(case when flag is null then 'Y' else flag end)"},
            {'name': 'DeliveredDate', 'expr': 'del_date'},
            {'name': 'Subject', 'expr': 'Subject'},
            {'name': 'Creative', 'expr': 'Creative'},
            {'name': 'OpenDate', 'expr': 'open_date'},
            {'name': 'ClickDate', 'expr': 'click_date'},
            {'name': 'UnsubDate', 'expr': 'unsub_date'}
        ]

    def get_excluded_columns(self) -> List[str]:
        """
        Get list of columns to exclude from custom selection

        Returns:
            List of excluded column names
        """
        return self.sf_config['columns']['excluded_columns']

    def get_table_columns(self, table_name: str) -> List[str]:
        """
        Get all available columns from the postback table

        Args:
            table_name: Name of the postback table

        Returns:
            List of column names
        """
        conn = None
        try:
            logger.info(f"Attempting to get columns for table: {table_name}")

            conn = get_db_connection()
            if not conn:
                raise Exception("Failed to get database connection")

            cursor = conn.cursor()

            # First, check if table exists
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
                logger.error(f"Table {table_name} does not exist in public schema")
                cursor.close()
                return []

            logger.info(f"Table {table_name} exists, fetching columns...")

            # Use a direct query approach which is more reliable
            # This gets the actual column names from the table
            query = f"""
                SELECT * FROM {table_name} LIMIT 0
            """

            cursor.execute(query)
            columns = [desc[0] for desc in cursor.description]

            cursor.close()

            logger.info(f"Successfully found {len(columns)} columns in table {table_name}: {columns}")

            return columns

        except Exception as e:
            logger.error(f"Failed to get table columns for {table_name}: {e}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            return []
        finally:
            if conn:
                release_db_connection(conn)

    def generate_file(self, request_id: int, client_name: str, week: str,
                      custom_columns: Optional[List[str]] = None,
                      include_standard: bool = True,
                      progress_callback: Optional[Callable[[int], None]] = None) -> Dict[str, Any]:
        """
        Generate pipe-separated file from postback table

        Args:
            request_id: Request ID
            client_name: Client name
            week: Week identifier
            custom_columns: Optional list of custom columns to include
            include_standard: Whether to include standard header columns
            progress_callback: Optional callback function to report progress

        Returns:
            Dict with file information and results
        """
        result = {
            'success': False,
            'file_path': '',
            'row_count': 0,
            'column_count': 0,
            'errors': []
        }

        conn = None
        temp_file = None

        try:
            # Generate table name - use same format as MetricsModal (no lowercase)
            table_name = f"apt_custom_{request_id}_{client_name}_{week}_postback_table"

            logger.info(f"Generating file from table: {table_name}")

            # Build column list
            columns = []

            if include_standard:
                standard_cols = self.get_standard_header_columns()
                columns.extend(standard_cols)

            if custom_columns:
                # Add custom columns that are not in standard header
                standard_names = [col['name'].lower() for col in self.get_standard_header_columns()]
                for custom_col in custom_columns:
                    if custom_col.lower() not in standard_names:
                        columns.append({'name': custom_col, 'expr': custom_col})

            if not columns:
                raise ValueError("No columns selected for export")

            result['column_count'] = len(columns)

            # Build SELECT statement
            select_exprs = [f"{col['expr']} AS {col['name']}" for col in columns]
            header_names = [col['name'] for col in columns]

            # Create temporary file
            temp_dir = self.sf_config['upload'].get('temp_dir', tempfile.gettempdir())
            os.makedirs(temp_dir, exist_ok=True)

            # Check disk space (require at least 5GB free)
            disk_stats = shutil.disk_usage(temp_dir)
            free_gb = disk_stats.free / (1024**3)
            if free_gb < 5:
                raise Exception(f"Insufficient disk space: {free_gb:.2f}GB free (minimum 5GB required)")

            logger.info(f"💾 Disk space check: {free_gb:.2f}GB available")

            temp_file_path = os.path.join(
                temp_dir,
                f"sf_upload_{request_id}_{client_name}_{week}_{os.getpid()}.csv"
            )

            # Get database connection
            conn = get_db_connection()
            if not conn:
                raise Exception("Failed to get database connection")

            # First, get total row count for progress tracking (use regular cursor)
            cursor_count = conn.cursor()
            count_query = f"SELECT COUNT(*) FROM {table_name}"
            cursor_count.execute(count_query)
            total_rows = cursor_count.fetchone()[0]
            cursor_count.close()

            logger.info(f"Total rows to export: {total_rows}")

            # Use server-side cursor for large result sets (streaming)
            cursor = conn.cursor(name=f'sf_upload_cursor_{request_id}_{os.getpid()}')

            # Build and execute SELECT query
            select_query = f"""
                SELECT {', '.join(select_exprs)}
                FROM {table_name}
            """

            logger.info(f"Executing query: {select_query[:200]}...")
            logger.info(f"⏳ Query executing... (this may take several minutes for large datasets)")
            cursor.execute(select_query)
            logger.info(f"✅ Query executed successfully, beginning data fetch...")

            # Write to file with progress tracking
            logger.info(f"📝 File writing initiated: {temp_file_path} ({total_rows} rows)")

            with open(temp_file_path, 'w', encoding='utf-8') as f:
                # Write header
                f.write(self.delimiter.join(header_names) + '\n')

                # Write data rows
                row_count = 0
                batch_size = self.sf_config['upload'].get('batch_size', 10000)
                last_logged_percentage = 0
                log_thresholds = [25, 50, 75, 100]  # Only log at these percentages

                while True:
                    rows = cursor.fetchmany(batch_size)
                    if not rows:
                        break

                    for row in rows:
                        # Convert None to empty string and handle special characters
                        cleaned_row = []
                        for value in row:
                            if value is None:
                                cleaned_row.append('')
                            else:
                                # Convert to string and escape delimiter if present
                                str_value = str(value)
                                if self.delimiter in str_value:
                                    str_value = f'"{str_value}"'
                                cleaned_row.append(str_value)

                        f.write(self.delimiter.join(cleaned_row) + '\n')
                        row_count += 1

                    # Report progress
                    current_percentage = int((row_count / total_rows) * 100)

                    if progress_callback:
                        progress_callback(current_percentage)

                    # Only log at specific thresholds (25%, 50%, 75%, 100%)
                    for threshold in log_thresholds:
                        if current_percentage >= threshold and last_logged_percentage < threshold:
                            logger.info(f"📊 File writing progress: {threshold}% ({row_count:,}/{total_rows:,} rows)")
                            last_logged_percentage = threshold
                            break

            cursor.close()

            # Verify file was created
            if not os.path.exists(temp_file_path):
                raise Exception("File was not created successfully")

            file_size = os.path.getsize(temp_file_path)
            file_size_mb = file_size / (1024 * 1024)
            logger.info(f"✅ File generation completed: {row_count:,} rows, {file_size_mb:.2f} MB")

            result['success'] = True
            result['file_path'] = temp_file_path
            result['row_count'] = row_count
            result['file_size'] = file_size

            return result

        except Exception as e:
            logger.error(f"Failed to generate file: {e}")
            result['errors'].append(str(e))

            # Clean up temp file on error
            if temp_file_path and os.path.exists(temp_file_path):
                try:
                    os.remove(temp_file_path)
                except:
                    pass

            return result
        finally:
            if conn:
                release_db_connection(conn)

    def cleanup_file(self, file_path: str):
        """
        Clean up temporary file

        Args:
            file_path: Path to file to delete
        """
        try:
            if os.path.exists(file_path):
                os.remove(file_path)
                logger.info(f"Cleaned up temporary file: {file_path}")
        except Exception as e:
            logger.warning(f"Failed to clean up file {file_path}: {e}")

    def get_column_definitions(self, columns: List[str]) -> List[Dict[str, str]]:
        """
        Generate Snowflake column definitions for selected columns

        Args:
            columns: List of column names

        Returns:
            List of column definitions with name and type
        """
        date_columns = self.sf_config['columns'].get('date_columns', [])

        column_defs = []
        for col_name in columns:
            col_type = 'DATE' if col_name in date_columns else 'VARCHAR'
            column_defs.append({
                'name': col_name,
                'type': col_type
            })

        return column_defs
