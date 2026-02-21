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
            # Read CSV without header (header=None means no header row, all rows are data)
            # Headers are already removed during upload, so first row is data
            content_str = file_content.decode('utf-8')
            df = pd.read_csv(io.StringIO(content_str), sep=self.csv_delimiter, header=None, thousands=",")

            # Validate column count ONLY (no header name validation as per user requirement)
            validation_result['file_info']['rows'] = len(df)  # Data rows (excludes header)
            validation_result['file_info']['columns'] = len(df.columns)

            # Check column count (should be 14 for CPM report)
            if len(df.columns) != 14:
                validation_result['valid'] = False
                validation_result['errors'].append(f"CPM report should have 14 columns, found {len(df.columns)}")
                return validation_result

            # Use positional column references (no header name dependency)
            # Column positions: 0=Campaign, 1=Date, 2=Delivered, 3=Opens, 4=Clicks, 5=Unsubs,
            #                   6=SB, 7=HB, 8=Subject, 9=Creative, 10=CreativeID,
            #                   11=OfferID, 12=Segment, 13=SubSegment

            # Clean string columns
            df = df.applymap(lambda x: x.strip() if isinstance(x, str) else x)

            # Validate date format (column 1 = Date)
            invalid_dates = ~df.iloc[:, 1].apply(self._is_valid_date)
            if invalid_dates.any():
                validation_result['valid'] = False
                validation_result['errors'].append("Invalid date format found. Expected: YYYY-MM-DD")
                validation_result['errors'].append(f"Invalid dates in rows: {df[invalid_dates].index.tolist()[:5]}")  # Show first 5

            # Validate numeric columns (columns 2-7: Delivered, Opens, Clicks, Unsubs, SB, HB)
            numeric_col_indices = [2, 3, 4, 5, 6, 7]
            numeric_col_names = ["Delivered", "Opens", "Clicks", "Unsubs", "SB", "HB"]

            for idx, col_name in zip(numeric_col_indices, numeric_col_names):
                if not df.iloc[:, idx].apply(self._validate_dtype).all():
                    validation_result['valid'] = False
                    validation_result['errors'].append(f"Invalid numeric values found in column {idx+1} ({col_name})")

            # Check for duplicate rows (columns 1,12,13,8,9,11 = Date,Segment,SubSeg,Subject,Creative,OfferID)
            key_col_indices = [1, 12, 13, 8, 9, 11]
            duplicates = df.iloc[:, key_col_indices].duplicated(keep=False)
            if duplicates.any():
                duplicate_count = duplicates.sum()
                validation_result['valid'] = False
                validation_result['errors'].append(f"Found {duplicate_count} duplicate rows based on key columns")

            # Additional validations
            if validation_result['valid']:
                # Enhanced apostrophe validation for PostgreSQL compatibility
                # Columns 0,8,9 = Campaign, Subject Line, Creative
                text_col_indices = [0, 8, 9]
                text_col_names = ["Campaign", "Subject Line", "Creative"]
                apostrophe_issues = []

                for idx, col_name in zip(text_col_indices, text_col_names):
                    # Count single apostrophes (not already escaped double apostrophes)
                    single_quotes = df.iloc[:, idx].astype(str).str.contains("'", regex=False, na=False)
                    already_escaped = df.iloc[:, idx].astype(str).str.contains("''", regex=False, na=False)

                    unescaped_count = single_quotes.sum() - already_escaped.sum()
                    if unescaped_count > 0:
                        apostrophe_issues.append(f"{col_name} ({unescaped_count} rows)")

                if apostrophe_issues:
                    validation_result['warnings'].append(f"Single quotes detected in: {', '.join(apostrophe_issues)}. These will be automatically converted to double quotes ('') for PostgreSQL compatibility.")

                # Get date range from column 1 (Date)
                try:
                    date_col = pd.to_datetime(df.iloc[:, 1])
                    validation_result['file_info']['date_range'] = {
                        'start': date_col.min().strftime('%Y-%m-%d'),
                        'end': date_col.max().strftime('%Y-%m-%d')
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
            # Read CSV without header (header=None means no header row, all rows are data)
            # Headers are already removed during upload, so first row is data
            content_str = file_content.decode('utf-8')
            df = pd.read_csv(io.StringIO(content_str), sep=self.csv_delimiter, header=None, thousands=",")

            # Validate column count ONLY (no header name validation)
            validation_result['file_info']['rows'] = len(df)  # Data rows (excludes header)
            validation_result['file_info']['columns'] = len(df.columns)

            # Check column count (should be exactly 8 for decile report)
            if len(df.columns) != 8:
                validation_result['valid'] = False
                validation_result['errors'].append(f"Decile report should have exactly 8 columns, found {len(df.columns)}")
                return validation_result

            # Use positional column references
            # Column positions: 0=Delivered, 1=Opens, 2=Clicks, 3=Unsubs,
            #                   4=Segment, 5=SubSegment, 6=Decile, 7=OldPercentage

            # Clean string columns
            df = df.applymap(lambda x: x.strip() if isinstance(x, str) else x)

            # Check if file is empty
            if len(df) == 0:
                validation_result['valid'] = False
                validation_result['errors'].append("Decile report is empty")
                return validation_result

            # Validate numeric columns (columns 0-3,7: Delivered, Opens, Clicks, Unsubs, OldPercentage)
            numeric_col_indices = [0, 1, 2, 3, 7]
            numeric_col_names = ["Delivered", "Opens", "Clicks", "Unsubs", "OldPercentage"]

            for idx, col_name in zip(numeric_col_indices, numeric_col_names):
                if not df.iloc[:, idx].apply(self._validate_dtype).all():
                    validation_result['valid'] = False
                    validation_result['errors'].append(f"Invalid numeric values found in column {idx+1} ({col_name})")

            # Validate old_percentage column (column 7, should be > 0 and not null)
            if validation_result['valid']:
                old_percentage = df.iloc[:, 7].dropna()
                if old_percentage.empty:
                    validation_result['valid'] = False
                    validation_result['errors'].append("OldPercentage column (column 8) contains null values")
                elif not (old_percentage > 0).all():
                    validation_result['valid'] = False
                    validation_result['errors'].append("OldPercentage values should be greater than 0")

            # Check for required columns presence (columns 4,5,6: Segment, SubSegment, Decile)
            required_col_indices = [4, 5, 6]
            required_col_names = ["Segment", "SubSegment", "Decile"]

            for idx, col_name in zip(required_col_indices, required_col_names):
                if df.iloc[:, idx].isnull().all():
                    validation_result['valid'] = False
                    validation_result['errors'].append(f"Required column '{col_name}' (column {idx+1}) is empty")

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
            # Read CSV with header row
            content_str = file_content.decode('utf-8')

            # Detect delimiter (timestamp files might use tabs instead of pipes)
            sample_lines = content_str.split('\n')[:3]
            sample_text = '\n'.join(sample_lines)
            delimiters = ['\t', '|', ',', ';']
            detected_delimiter = '\t'  # Default to tab
            max_columns = 0

            for delimiter in delimiters:
                try:
                    df_test = pd.read_csv(io.StringIO(sample_text), sep=delimiter, header=None, nrows=1)
                    if len(df_test.columns) > max_columns:
                        max_columns = len(df_test.columns)
                        detected_delimiter = delimiter
                except:
                    continue

            # Read with detected delimiter (no header - headers already removed during upload)
            df = pd.read_csv(io.StringIO(content_str), sep=detected_delimiter, header=None)

            # Validate column count ONLY (no header name validation)
            validation_result['file_info']['rows'] = len(df)  # Data rows
            validation_result['file_info']['columns'] = len(df.columns)

            # Check if file is empty
            if len(df) == 0:
                validation_result['valid'] = False
                validation_result['errors'].append("Timestamp report has no data rows")
                return validation_result

            # Check column count (should have exactly 3 columns)
            if len(df.columns) != 3:
                validation_result['valid'] = False
                validation_result['errors'].append(f"Timestamp report should have exactly 3 columns, found {len(df.columns)}")
                return validation_result

            # Use positional column references
            # Column positions: 0=DeliveryDate (YYYY-MM-DD), 1=StartTime (YYYY-MM-DD HH:MM:SS),
            #                   2=EndTime (YYYY-MM-DD HH:MM:SS)

            # Validate formats
            try:
                # Column 0: must be YYYY-MM-DD format
                col1_values = df.iloc[:, 0].astype(str)
                date_pattern = r'^\d{4}-\d{2}-\d{2}$'
                invalid_col1 = ~col1_values.str.match(date_pattern, na=False)

                if invalid_col1.any():
                    validation_result['valid'] = False
                    validation_result['errors'].append(f"Column 1 must be in YYYY-MM-DD format. Found {invalid_col1.sum()} invalid dates.")
                    return validation_result

                # Columns 1 and 2: must be YYYY-MM-DD HH:MM:SS format
                datetime_pattern = r'^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}$'

                col2_values = df.iloc[:, 1].astype(str)
                invalid_col2 = ~col2_values.str.match(datetime_pattern, na=False)
                if invalid_col2.any():
                    validation_result['valid'] = False
                    validation_result['errors'].append(f"Column 2 (StartTime) must be in YYYY-MM-DD HH:MM:SS format. Found {invalid_col2.sum()} invalid timestamps.")
                    return validation_result

                col3_values = df.iloc[:, 2].astype(str)
                invalid_col3 = ~col3_values.str.match(datetime_pattern, na=False)
                if invalid_col3.any():
                    validation_result['valid'] = False
                    validation_result['errors'].append(f"Column 3 (EndTime) must be in YYYY-MM-DD HH:MM:SS format. Found {invalid_col3.sum()} invalid timestamps.")
                    return validation_result

                # Validate date consistency across all 3 columns
                col1_dates = pd.to_datetime(df.iloc[:, 0])
                col2_dates = pd.to_datetime(df.iloc[:, 1])
                col3_dates = pd.to_datetime(df.iloc[:, 2])

                dates_match = (
                    (col1_dates == col2_dates.dt.date) &
                    (col2_dates.dt.date == col3_dates.dt.date)
                ).all()

                if not dates_match:
                    validation_result['valid'] = False
                    validation_result['errors'].append("Date consistency failed: dates in column 1 must match dates in columns 2 and 3")
                    return validation_result

            except Exception as date_error:
                validation_result['valid'] = False
                validation_result['errors'].append(f"Timestamp format validation failed: {str(date_error)}")


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
            file_type: Type of file ('cpm', 'decile', 'unique_decile', 'timestamp')

        Returns:
            Dict with validation results
        """
        logger.info(f"Validating {file_type} file: {filename}")

        if file_type == 'cpm':
            return self.validate_cpm_report(file_content, filename)
        elif file_type == 'decile' or file_type == 'unique_decile':
            # Both decile and unique_decile have the same structure (8 columns)
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
                            # Read without header (headers already removed during upload)
                            df = pd.read_csv(io.StringIO(content_str), sep=self.csv_delimiter, header=None, thousands=",")
                            if len(df.columns) == 14:
                                parsed_files['cpm'] = df
                            else:
                                cross_validation_result['warnings'].append(f"CPM file has {len(df.columns)} columns, expected 14")

                        elif file_type == 'decile' or file_type == 'unique_decile':
                            # Read without header (headers already removed during upload)
                            df = pd.read_csv(io.StringIO(content_str), sep=self.csv_delimiter, header=None, thousands=",")
                            if len(df.columns) == 8:
                                parsed_files[file_type] = df
                            else:
                                cross_validation_result['warnings'].append(f"{file_type} file has {len(df.columns)} columns, expected 8")

                        elif file_type == 'timestamp':
                            # Auto-detect delimiter for timestamp files
                            sample_lines = content_str.split('\n')[:3]
                            sample_text = '\n'.join(sample_lines)

                            delimiters = ['\t', '|', ',', ';']
                            detected_delimiter = '\t'
                            max_columns = 0

                            for delimiter in delimiters:
                                try:
                                    df_test = pd.read_csv(io.StringIO(sample_text), sep=delimiter, header=None, nrows=1)
                                    if len(df_test.columns) > max_columns:
                                        max_columns = len(df_test.columns)
                                        detected_delimiter = delimiter
                                except:
                                    continue

                            # Read without header (headers already removed during upload)
                            df = pd.read_csv(io.StringIO(content_str), sep=detected_delimiter, header=None)
                            parsed_files['timestamp'] = df

                    except Exception as e:
                        cross_validation_result['warnings'].append(f"Could not parse {file_type} file for cross-validation: {str(e)}")

            # Cross-validation 1: CPM and Decile segment/sub_seg matching
            if 'cpm' in parsed_files and 'decile' in parsed_files:
                cross_validation_result['validations_performed'].append('CPM-Decile Segment Matching')

                cpm_df = parsed_files['cpm']
                decile_df = parsed_files['decile']

                try:
                    # Get unique (Segment, SubSegment) combinations from both reports
                    # Use column indices: 12=Segment, 13=SubSegment for CPM
                    #                     4=Segment, 5=SubSegment for Decile
                    cpm_combinations = set(
                        tuple(x) for x in cpm_df.iloc[:, [12, 13]].drop_duplicates().values
                    )
                    decile_combinations = set(
                        tuple(x) for x in decile_df.iloc[:, [4, 5]].drop_duplicates().values
                    )

                    # Check if sets are identical
                    if cpm_combinations == decile_combinations:
                        logger.info("✅ Segments and sub-segments match exactly between CPM and Decile reports")
                    else:
                        cross_validation_result['valid'] = False
                        cross_validation_result['errors'].append("CPM - Decile - Segment Comparison: Failed")

                except Exception as e:
                    cross_validation_result['warnings'].append(f"Could not validate segment matching: {str(e)}")

            # Cross-validation 1.5: CPM and Decile Delivered Sum Comparison
            if 'cpm' in parsed_files and 'decile' in parsed_files:
                cross_validation_result['validations_performed'].append('CPM-Decile Delivered Sum Comparison')

                cpm_df = parsed_files['cpm']
                decile_df = parsed_files['decile']

                try:
                    # Sum Delivered by (Segment, SubSegment) from CPM
                    # CPM columns: 12=Segment, 13=SubSegment, 2=Delivered
                    cpm_df_clean = cpm_df.copy()
                    cpm_df_clean.iloc[:, 2] = pd.to_numeric(cpm_df_clean.iloc[:, 2].astype(str).str.replace(',', ''), errors='coerce').fillna(0).astype(int)
                    cpm_sums = cpm_df_clean.groupby([cpm_df_clean.iloc[:, 12], cpm_df_clean.iloc[:, 13]]).apply(
                        lambda x: x.iloc[:, 2].sum()
                    ).reset_index()
                    cpm_sums.columns = ['segment', 'subseg', 'delivered_cpm']

                    # Sum Delivered by (Segment, SubSegment) from Decile
                    # Decile columns: 4=Segment, 5=SubSegment, 0=Delivered
                    decile_df_clean = decile_df.copy()
                    decile_df_clean.iloc[:, 0] = pd.to_numeric(decile_df_clean.iloc[:, 0].astype(str).str.replace(',', ''), errors='coerce').fillna(0).astype(int)
                    decile_sums = decile_df_clean.groupby([decile_df_clean.iloc[:, 4], decile_df_clean.iloc[:, 5]]).apply(
                        lambda x: x.iloc[:, 0].sum()
                    ).reset_index()
                    decile_sums.columns = ['segment', 'subseg', 'delivered_decile']

                    # Merge and compare
                    comparison = pd.merge(cpm_sums, decile_sums, on=['segment', 'subseg'], how='outer')
                    comparison['difference'] = comparison['delivered_cpm'].fillna(0) - comparison['delivered_decile'].fillna(0)

                    mismatches = comparison[comparison['difference'] != 0]

                    if len(mismatches) == 0:
                        logger.info("✅ CPM and Decile Delivered totals match exactly")
                    else:
                        cross_validation_result['valid'] = False
                        mismatch_details = []
                        for _, row in mismatches.iterrows():
                            mismatch_details.append(f"{row['segment']}/{row['subseg']}: CPM={int(row['delivered_cpm'])} vs Decile={int(row['delivered_decile'])}")
                        cross_validation_result['errors'].append(f"CPM - Decile - Delivered Sum Comparison: Failed. Mismatches: {'; '.join(mismatch_details[:3])}")
                        logger.error(f"❌ CPM and Decile Delivered totals do not match: {mismatch_details}")

                except Exception as e:
                    cross_validation_result['warnings'].append(f"Could not validate delivered sum comparison: {str(e)}")

            # Cross-validation 2: Unique Decile and Decile matching (OPTIONAL - Type 2 only)
            if 'unique_decile' in parsed_files and 'decile' in parsed_files:
                cross_validation_result['validations_performed'].append('Unique-Decile-Decile Matching')

                unique_decile_df = parsed_files['unique_decile']
                decile_df = parsed_files['decile']

                try:
                    # Get unique (Segment, SubSegment, Decile, OldPercentage) combinations
                    # Columns 4,5,6,7 for both reports
                    unique_decile_combinations = set(
                        tuple(x) for x in unique_decile_df.iloc[:, [4, 5, 6, 7]].drop_duplicates().values
                    )
                    decile_combinations = set(
                        tuple(x) for x in decile_df.iloc[:, [4, 5, 6, 7]].drop_duplicates().values
                    )

                    # Check if unique_decile is a subset of decile
                    if unique_decile_combinations.issubset(decile_combinations):
                        logger.info("✅ Unique Decile and Decile reports match exactly")
                    else:
                        cross_validation_result['valid'] = False
                        cross_validation_result['errors'].append("Unique Decile - Decile - Comparison: Failed")

                except Exception as e:
                    cross_validation_result['warnings'].append(f"Could not validate unique decile matching: {str(e)}")

            # Cross-validation 3: Timestamp first column dates vs CPM report dates
            if 'timestamp' in parsed_files and 'cpm' in parsed_files:
                cross_validation_result['validations_performed'].append('Timestamp-CPM Date Matching')

                timestamp_df = parsed_files['timestamp']
                cpm_df = parsed_files['cpm']

                try:
                    # Get unique dates from timestamp report (column 0)
                    timestamp_dates = set(pd.to_datetime(timestamp_df.iloc[:, 0]).dt.date)
                    logger.info(f"🔍 Timestamp delivered dates: {sorted(timestamp_dates)}")

                    # Get unique dates from CPM report (column 1)
                    cpm_dates = set(pd.to_datetime(cpm_df.iloc[:, 1]).dt.date)
                    logger.info(f"🔍 CPM delivered dates: {sorted(cpm_dates)}")

                    # Check if date sets are identical
                    if timestamp_dates == cpm_dates:
                        logger.info("✅ Delivered dates match exactly between Timestamp and CPM reports")
                    else:
                        cross_validation_result['valid'] = False
                        missing_in_cpm = timestamp_dates - cpm_dates
                        missing_in_timestamp = cpm_dates - timestamp_dates

                        error_msg = f"❌ Delivered dates do not match exactly between Timestamp and CPM reports. Missing in CPM: {sorted(missing_in_cpm)}. Missing in Timestamp: {sorted(missing_in_timestamp)}"
                        logger.error(error_msg)
                        cross_validation_result['errors'].append("CPM - TimeStamp - Date Comparison: Failed")

                except Exception as e:
                    cross_validation_result['warnings'].append(f"Could not validate date matching: {str(e)}")

            # Log final result
            if cross_validation_result['valid']:
                logger.info("🔍 Cross-validation PASSED")
                logger.info(f"   Validations performed: {cross_validation_result['validations_performed']}")
            else:
                logger.info("🔍 Cross-validation FAILED")
                logger.info(f"   Validations performed: {cross_validation_result['validations_performed']}")
                logger.error(f"   Errors: {cross_validation_result['errors']}")

        except Exception as e:
            logger.error(f"Error in cross-validation: {e}")
            cross_validation_result['warnings'].append(f"Cross-validation error: {str(e)}")

        return cross_validation_result
