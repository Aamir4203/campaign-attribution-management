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
                # Enhanced apostrophe validation for PostgreSQL compatibility
                text_columns = ["Campaign", "Subject Line", "Creative"]
                apostrophe_issues = []

                for col in text_columns:
                    if col in df.columns:
                        # Count single apostrophes (not already escaped double apostrophes)
                        single_quotes = df[col].astype(str).str.contains("'", regex=False, na=False)
                        already_escaped = df[col].astype(str).str.contains("''", regex=False, na=False)

                        unescaped_count = single_quotes.sum() - already_escaped.sum()
                        if unescaped_count > 0:
                            apostrophe_issues.append(f"{col} ({unescaped_count} rows)")

                if apostrophe_issues:
                    validation_result['warnings'].append(f"Single quotes detected in: {', '.join(apostrophe_issues)}. These will be automatically converted to double quotes ('') for PostgreSQL compatibility.")

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
                # First column validation: must be YYYY-MM-DD format
                col1_values = df.iloc[:, 0].astype(str)
                date_pattern = r'^\d{4}-\d{2}-\d{2}$'

                invalid_col1_dates = ~col1_values.str.match(date_pattern, na=False)
                if invalid_col1_dates.any():
                    invalid_count = invalid_col1_dates.sum()
                    validation_result['valid'] = False
                    validation_result['errors'].append(f"Column 1 must be in YYYY-MM-DD format. Found {invalid_count} invalid dates.")
                    return validation_result

                # Columns 2 and 3 validation: must be YYYY-MM-DD hh:mm:ss format
                datetime_pattern = r'^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}$'

                if len(df.columns) >= 2:
                    col2_values = df.iloc[:, 1].astype(str)
                    invalid_col2_datetime = ~col2_values.str.match(datetime_pattern, na=False)
                    if invalid_col2_datetime.any():
                        invalid_count = invalid_col2_datetime.sum()
                        validation_result['valid'] = False
                        validation_result['errors'].append(f"Column 2 (starttime) must be in YYYY-MM-DD hh:mm:ss format. Found {invalid_count} invalid timestamps.")
                        return validation_result

                if len(df.columns) >= 3:
                    col3_values = df.iloc[:, 2].astype(str)
                    invalid_col3_datetime = ~col3_values.str.match(datetime_pattern, na=False)
                    if invalid_col3_datetime.any():
                        invalid_count = invalid_col3_datetime.sum()
                        validation_result['valid'] = False
                        validation_result['errors'].append(f"Column 3 (endtime) must be in YYYY-MM-DD hh:mm:ss format. Found {invalid_count} invalid timestamps.")
                        return validation_result

                # Now validate the parsed dates for consistency
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
                    validation_result['errors'].append("Date consistency failed: dates across first 3 columns do not match")
                else:
                    validation_result['file_info']['date_validation'] = 'passed'
                    validation_result['file_info']['format_validation'] = 'passed'

            except Exception as date_error:
                validation_result['valid'] = False
                validation_result['errors'].append(f"Timestamp format validation failed: {str(date_error)}")

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

    def cross_validate_files(self, files_data: Dict[str, bytes], filenames: Dict[str, str]) -> Dict[str, Any]:
        """
        Perform cross-validation between multiple uploaded files.

        Args:
            files_data: Dict with keys 'cpm', 'decile', 'timestamp' and file content as values
            filenames: Dict with keys 'cpm', 'decile', 'timestamp' and filenames as values

        Returns:
            Dict with cross-validation results
        """
        cross_validation_result = {
            'valid': True,
            'errors': [],
            'warnings': [],
            'validations_performed': []
        }

        try:
            # Parse available files
            parsed_files = {}

            for file_type, content in files_data.items():
                if content:
                    try:
                        content_str = content.decode('utf-8')

                        if file_type == 'cpm':
                            df = pd.read_csv(io.StringIO(content_str), sep=self.csv_delimiter, header=None, thousands=",")
                            if len(df.columns) >= 14:
                                df.columns = [
                                    "Campaign", "Date", "Delivered", "Unique Opens", "Clicks",
                                    "Unsubs", "sb", "hb", "Subject Line", "Creative",
                                    "Creative ID", "Offer ID", "segment", "sub_seg"
                                ]
                                parsed_files['cpm'] = df

                        elif file_type == 'decile':
                            df = pd.read_csv(io.StringIO(content_str), sep=self.csv_delimiter, header=None, thousands=",")
                            if len(df.columns) >= 8:
                                df.columns = [
                                    "Delivered", "Opens", "clicks", "unsubs",
                                    "segment", "sub_seg", "decile", "old_delivered_per"
                                ]
                                parsed_files['decile'] = df

                        elif file_type == 'timestamp':
                            # Auto-detect delimiter for timestamp files
                            sample_lines = content_str.split('\n')[:3]
                            sample_text = '\n'.join(sample_lines)

                            delimiters = ['\t', '|', ',', ';']
                            detected_delimiter = '\t'
                            max_columns = 0

                            for delimiter in delimiters:
                                try:
                                    df_test = pd.read_csv(io.StringIO(sample_text), sep=delimiter, header=0, nrows=1)
                                    if len(df_test.columns) > max_columns:
                                        max_columns = len(df_test.columns)
                                        detected_delimiter = delimiter
                                except:
                                    continue

                            df = pd.read_csv(io.StringIO(content_str), sep=detected_delimiter, header=0)
                            parsed_files['timestamp'] = df

                    except Exception as e:
                        cross_validation_result['warnings'].append(f"Could not parse {file_type} file for cross-validation: {str(e)}")

            # Cross-validation 1: CPM and Decile segment/sub_seg matching
            if 'cpm' in parsed_files and 'decile' in parsed_files:
                cross_validation_result['validations_performed'].append('CPM-Decile Segment Matching')

                cpm_df = parsed_files['cpm']
                decile_df = parsed_files['decile']

                try:
                    # Check segment matching
                    cpm_segments = cpm_df["segment"].drop_duplicates().sort_values().reset_index(drop=True)
                    decile_segments = decile_df["segment"].drop_duplicates().sort_values().reset_index(drop=True)

                    segments_match = (cpm_segments == decile_segments).all() if len(cpm_segments) == len(decile_segments) else False

                    # Check sub_seg matching
                    cpm_subseg = cpm_df["sub_seg"].drop_duplicates().sort_values().reset_index(drop=True)
                    decile_subseg = decile_df["sub_seg"].drop_duplicates().sort_values().reset_index(drop=True)

                    subseg_match = (cpm_subseg == decile_subseg).all() if len(cpm_subseg) == len(decile_subseg) else False

                    if not (segments_match and subseg_match):
                        cross_validation_result['valid'] = False
                        cross_validation_result['errors'].append("Segments and sub-segments between CPM and Decile reports do not match")

                except Exception as e:
                    cross_validation_result['warnings'].append(f"Could not validate segment matching: {str(e)}")

            # Cross-validation 2: Timestamp first column dates vs CPM report dates
            if 'timestamp' in parsed_files and 'cpm' in parsed_files:
                cross_validation_result['validations_performed'].append('Timestamp-CPM Date Matching')

                timestamp_df = parsed_files['timestamp']
                cpm_df = parsed_files['cpm']

                try:
                    # Get timestamp dates (first column)
                    timestamp_dates = pd.to_datetime(timestamp_df.iloc[:, 0]).dt.date
                    timestamp_date_range = {
                        'min': timestamp_dates.min(),
                        'max': timestamp_dates.max()
                    }

                    # Get CPM report dates
                    cmp_dates = pd.to_datetime(cpm_df["Date"]).dt.date
                    cpm_date_range = {
                        'min': cmp_dates.min(),
                        'max': cmp_dates.max()
                    }

                    # Check if date ranges overlap or are compatible
                    dates_compatible = (
                        timestamp_date_range['min'] <= cpm_date_range['max'] and
                        timestamp_date_range['max'] >= cpm_date_range['min']
                    )

                    if not dates_compatible:
                        cross_validation_result['valid'] = False
                        cross_validation_result['errors'].append(
                            f"Timestamp date range ({timestamp_date_range['min']} to {timestamp_date_range['max']}) "
                            f"does not overlap with CPM report date range ({cpm_date_range['min']} to {cpm_date_range['max']})"
                        )

                except Exception as e:
                    cross_validation_result['warnings'].append(f"Could not validate date matching: {str(e)}")

        except Exception as e:
            logger.error(f"Error in cross-validation: {e}")
            cross_validation_result['warnings'].append(f"Cross-validation error: {str(e)}")

        return cross_validation_result
