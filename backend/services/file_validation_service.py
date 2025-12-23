#!/usr/bin/env python3
"""
File Validation Service for CAM Application
Handles validation of timestamp, CPM, and decile report files
Based on requestValidation.py logic
"""

import pandas as pd
import io
import logging
from typing import Dict, List, Tuple, Any, Optional
from datetime import datetime
import re

logger = logging.getLogger(__name__)

class FileValidationService:
    """
    Service class for validating uploaded report files.
    Implements validation logic from requestValidation.py
    """

    def __init__(self, config):
        """
        Initialize validation service with configuration.

        Args:
            config: Configuration manager instance
        """
        self.config = config
        self.upload_config = config.get_upload_config()
        self.validation_config = self.upload_config.get('validation', {})

        # Validation settings
        self.csv_delimiter = self.validation_config.get('csv_delimiter', '|')
        self.max_size_mb = self.upload_config.get('max_size_mb', 50)
        self.allowed_extensions = self.upload_config.get('allowed_extensions', ['csv', 'xlsx', 'xls'])

    def validate_file_basic(self, file_content: bytes, filename: str) -> Dict[str, Any]:
        """
        Perform basic file validation (size, extension, format).

        Args:
            file_content: File content as bytes
            filename: Original filename

        Returns:
            Dict with validation results
        """
        validation_result = {
            'valid': True,
            'errors': [],
            'warnings': [],
            'file_info': {}
        }

        try:
            # Check file size
            file_size_mb = len(file_content) / (1024 * 1024)
            validation_result['file_info']['size_mb'] = round(file_size_mb, 2)

            if file_size_mb > self.max_size_mb:
                validation_result['valid'] = False
                validation_result['errors'].append(f"File size ({file_size_mb:.1f}MB) exceeds limit ({self.max_size_mb}MB)")

            # Check file extension
            file_extension = filename.lower().split('.')[-1]
            validation_result['file_info']['extension'] = file_extension

            if file_extension not in self.allowed_extensions:
                validation_result['valid'] = False
                validation_result['errors'].append(f"File extension '{file_extension}' not allowed. Allowed: {', '.join(self.allowed_extensions)}")

            # Check if file is empty
            if len(file_content) == 0:
                validation_result['valid'] = False
                validation_result['errors'].append("File is empty")

        except Exception as e:
            logger.error(f"Error in basic file validation: {e}")
            validation_result['valid'] = False
            validation_result['errors'].append(f"File validation error: {str(e)}")

        return validation_result

    def _is_valid_date(self, date_str: str) -> bool:
        """Check if date string is valid YYYY-MM-DD format"""
        try:
            pd.to_datetime(date_str, format="%Y-%m-%d", errors="raise")
            return True
        except ValueError:
            return False

    def _validate_dtype(self, value) -> bool:
        """Check if value is valid numeric type"""
        return isinstance(value, (int, float)) or (isinstance(value, str) and value.replace(',', '').replace('.', '').isdigit())

    def validate_cpm_report(self, file_content: bytes, filename: str) -> Dict[str, Any]:
        """
        Validate CPM report file based on requestValidation.py logic.

        Args:
            file_content: File content as bytes
            filename: Original filename

        Returns:
            Dict with validation results
        """
        # Start with basic validation
        validation_result = self.validate_file_basic(file_content, filename)
        if not validation_result['valid']:
            return validation_result

        try:
            # Try to read as CSV with pipe delimiter
            content_str = file_content.decode('utf-8')
            df = pd.read_csv(io.StringIO(content_str), sep=self.csv_delimiter, header=None, thousands=",")

            validation_result['file_info']['rows'] = len(df)
            validation_result['file_info']['columns'] = len(df.columns)

            # Check column count (should be 14 for CPM report)
            if len(df.columns) != 14:
                validation_result['valid'] = False
                validation_result['errors'].append(f"CPM report should have 14 columns, found {len(df.columns)}")
                return validation_result

            # Assign column names
            df.columns = [
                "Campaign", "Date", "Delivered", "Unique Opens", "Clicks", "Unsubs",
                "sb", "hb", "Subject Line", "Creative", "Creative ID",
                "Offer ID", "segment", "sub_seg"
            ]

            # Clean string columns
            df = df.applymap(lambda x: x.strip() if isinstance(x, str) else x)

            # Validate date format
            invalid_dates = ~df["Date"].apply(self._is_valid_date)
            if invalid_dates.any():
                validation_result['valid'] = False
                validation_result['errors'].append("Invalid date format found. Expected: YYYY-MM-DD")
                validation_result['errors'].append(f"Invalid dates in rows: {df[invalid_dates].index.tolist()[:5]}")  # Show first 5

            # Validate numeric columns
            numeric_columns = ["Delivered", "Unique Opens", "Clicks", "Unsubs", "sb", "hb"]
            for col in numeric_columns:
                if not df[col].apply(self._validate_dtype).all():
                    validation_result['valid'] = False
                    validation_result['errors'].append(f"Invalid numeric values found in column: {col}")

            # Check for duplicate rows
            key_columns = ["Date", "segment", "sub_seg", "Subject Line", "Creative", "Offer ID"]
            duplicates = df.duplicated(subset=key_columns, keep=False)
            if duplicates.any():
                duplicate_count = duplicates.sum()
                validation_result['valid'] = False
                validation_result['errors'].append(f"Found {duplicate_count} duplicate rows based on key columns")

            # Additional validations
            if validation_result['valid']:
                # Check Subject Line format
                if df["Subject Line"].str.contains("'").any() and not df["Subject Line"].str.contains("''").any():
                    validation_result['warnings'].append("Subject lines contain single quotes - will be escaped during processing")

                # Get date range
                try:
                    df['Date'] = pd.to_datetime(df['Date'])
                    validation_result['file_info']['date_range'] = {
                        'start': df['Date'].min().strftime('%Y-%m-%d'),
                        'end': df['Date'].max().strftime('%Y-%m-%d')
                    }
                except:
                    pass

        except UnicodeDecodeError:
            validation_result['valid'] = False
            validation_result['errors'].append("File encoding not supported. Please use UTF-8 encoding.")
        except Exception as e:
            logger.error(f"Error validating CPM report: {e}")
            validation_result['valid'] = False
            validation_result['errors'].append(f"CPM report validation error: {str(e)}")

        return validation_result

    def validate_decile_report(self, file_content: bytes, filename: str) -> Dict[str, Any]:
        """
        Validate decile report file based on requestValidation.py logic.

        Args:
            file_content: File content as bytes
            filename: Original filename

        Returns:
            Dict with validation results
        """
        # Start with basic validation
        validation_result = self.validate_file_basic(file_content, filename)
        if not validation_result['valid']:
            return validation_result

        try:
            # Try to read as CSV with pipe delimiter
            content_str = file_content.decode('utf-8')
            df = pd.read_csv(io.StringIO(content_str), sep=self.csv_delimiter, header=None, thousands=",")

            validation_result['file_info']['rows'] = len(df)
            validation_result['file_info']['columns'] = len(df.columns)

            # Check column count (should be exactly 8 for decile report)
            if len(df.columns) != 8:
                validation_result['valid'] = False
                validation_result['errors'].append(f"Decile report should have exactly 8 columns, found {len(df.columns)}")
                return validation_result

            # Assign column names as per requestValidation.py
            df.columns = [
                "Delivered", "Opens", "clicks", "unsubs",
                "segment", "sub_seg", "decile", "old_delivered_per"
            ]

            # Clean string columns
            df = df.applymap(lambda x: x.strip() if isinstance(x, str) else x)

            # Check if file is empty
            if len(df) == 0:
                validation_result['valid'] = False
                validation_result['errors'].append("Decile report is empty")
                return validation_result

            # Validate numeric columns
            numeric_columns = ["Delivered", "Opens", "clicks", "unsubs", "old_delivered_per"]
            for col in numeric_columns:
                if not df[col].apply(self._validate_dtype).all():
                    validation_result['valid'] = False
                    validation_result['errors'].append(f"Invalid numeric values found in column: {col}")

            # Validate old_delivered_per column (should be > 0 and not null)
            if validation_result['valid']:
                old_delivered_per = df["old_delivered_per"].dropna()
                if old_delivered_per.empty:
                    validation_result['valid'] = False
                    validation_result['errors'].append("old_delivered_per column contains null values")
                elif not (old_delivered_per > 0).all():
                    validation_result['valid'] = False
                    validation_result['errors'].append("old_delivered_per values should be greater than 0")

            # Check for required columns presence
            required_columns = ["segment", "sub_seg", "decile"]
            for col in required_columns:
                if df[col].isnull().all():
                    validation_result['valid'] = False
                    validation_result['errors'].append(f"Required column '{col}' is empty")

        except UnicodeDecodeError:
            validation_result['valid'] = False
            validation_result['errors'].append("File encoding not supported. Please use UTF-8 encoding.")
        except Exception as e:
            logger.error(f"Error validating decile report: {e}")
            validation_result['valid'] = False
            validation_result['errors'].append(f"Decile report validation error: {str(e)}")

        return validation_result

    def validate_timestamp_report(self, file_content: bytes, filename: str) -> Dict[str, Any]:
        """
        Validate timestamp report file based on requestValidation.py logic.

        Args:
            file_content: File content as bytes
            filename: Original filename

        Returns:
            Dict with validation results
        """
        # Start with basic validation
        validation_result = self.validate_file_basic(file_content, filename)
        if not validation_result['valid']:
            return validation_result

        try:
            # First, count total rows including header
            content_str = file_content.decode('utf-8')
            total_lines = len([line for line in content_str.split('\n') if line.strip()])

            # Detect delimiter for timestamp files (they might use tabs instead of pipes)
            sample_lines = content_str.split('\n')[:3]
            sample_text = '\n'.join(sample_lines)

            # Common delimiters to check for timestamp files
            delimiters = ['\t', '|', ',', ';']
            detected_delimiter = '\t'  # Default to tab for timestamp files
            max_columns = 0

            for delimiter in delimiters:
                try:
                    df_test = pd.read_csv(io.StringIO(sample_text), sep=delimiter, header=0, nrows=1)
                    if len(df_test.columns) > max_columns:
                        max_columns = len(df_test.columns)
                        detected_delimiter = delimiter
                except:
                    continue

            logger.info(f"Detected delimiter for timestamp file: '{detected_delimiter}' ({repr(detected_delimiter)})")

            # Try to read as CSV with detected delimiter and headers
            df = pd.read_csv(io.StringIO(content_str), sep=detected_delimiter, header=0)

            # Report total rows (including header) instead of just data rows
            validation_result['file_info']['rows'] = total_lines  # Total rows including header
            validation_result['file_info']['data_rows'] = len(df)  # Data rows only
            validation_result['file_info']['columns'] = len(df.columns)

            # Check if file is empty
            if len(df) == 0:
                validation_result['valid'] = False
                validation_result['errors'].append("Timestamp report has no data rows")
                return validation_result

            # Check minimum columns (should have at least 3 date columns)
            if len(df.columns) < 3:
                validation_result['valid'] = False
                validation_result['errors'].append("Timestamp report should have at least 3 columns for date validation")
                return validation_result

            # Validate timestamp date consistency (first 3 columns should be date-related)
            try:
                # Convert first 3 columns to datetime
                col1_dates = pd.to_datetime(df.iloc[:, 0])
                col2_dates = pd.to_datetime(df.iloc[:, 1])
                col3_dates = pd.to_datetime(df.iloc[:, 2])

                # Check if dates match as per requestValidation.py logic
                dates_match = (
                    (col1_dates == col2_dates.dt.date) &
                    (col2_dates.dt.date == col3_dates.dt.date)
                ).all()

                if not dates_match:
                    validation_result['valid'] = False
                    validation_result['errors'].append("Timestamp dates across first 3 columns do not match")
                else:
                    validation_result['file_info']['date_validation'] = 'passed'

            except Exception as date_error:
                validation_result['valid'] = False
                validation_result['errors'].append(f"Date validation failed: first 3 columns should contain valid dates")

            # Improved timestamp-related column name detection
            column_names = [col.lower().replace(' ', '').replace('_', '') for col in df.columns]
            timestamp_indicators = ['timestamp', 'time', 'date', 'created', 'sent', 'delivered', 'deldate', 'starttime', 'endtime']

            detected_indicators = []
            for col in column_names:
                for indicator in timestamp_indicators:
                    if indicator in col:
                        detected_indicators.append(indicator)
                        break

            if len(detected_indicators) > 0:
                validation_result['file_info']['detected_time_columns'] = detected_indicators
            else:
                validation_result['warnings'].append("No obvious timestamp-related column names detected")

        except UnicodeDecodeError:
            validation_result['valid'] = False
            validation_result['errors'].append("File encoding not supported. Please use UTF-8 encoding.")
        except Exception as e:
            logger.error(f"Error validating timestamp report: {e}")
            validation_result['valid'] = False
            validation_result['errors'].append(f"Timestamp report validation error: {str(e)}")

        return validation_result

    def validate_file(self, file_content: bytes, filename: str, file_type: str) -> Dict[str, Any]:
        """
        Main validation method that routes to specific validators.

        Args:
            file_content: File content as bytes
            filename: Original filename
            file_type: Type of file ('cpm', 'decile', 'timestamp')

        Returns:
            Dict with validation results
        """
        logger.info(f"Validating {file_type} file: {filename}")

        if file_type == 'cpm':
            return self.validate_cpm_report(file_content, filename)
        elif file_type == 'decile':
            return self.validate_decile_report(file_content, filename)
        elif file_type == 'timestamp':
            return self.validate_timestamp_report(file_content, filename)
        else:
            return {
                'valid': False,
                'errors': [f"Unknown file type: {file_type}"],
                'warnings': [],
                'file_info': {}
            }
