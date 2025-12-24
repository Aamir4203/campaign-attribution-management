#!/usr/bin/env python3
"""
File Utilities for CAM Application
Helper functions for file operations and conversions
"""

import pandas as pd
import io
import logging
from typing import Dict, Any, Optional, Union
from pathlib import Path
import openpyxl
from openpyxl import load_workbook

logger = logging.getLogger(__name__)

class FileUtils:
    """
    Utility class for file operations and conversions.
    """

    @staticmethod
    def excel_to_csv(file_content: bytes, delimiter: str = '|') -> bytes:
        """
        Convert Excel file content to CSV format.

        Args:
            file_content: Excel file content as bytes
            delimiter: CSV delimiter to use

        Returns:
            CSV content as bytes
        """
        try:
            # Read Excel file from bytes
            excel_file = io.BytesIO(file_content)

            # Try to read with pandas (handles both .xls and .xlsx)
            df = pd.read_excel(excel_file, engine='openpyxl')

            # Convert to CSV with specified delimiter
            csv_buffer = io.StringIO()
            df.to_csv(csv_buffer, sep=delimiter, index=False, header=False)
            csv_content = csv_buffer.getvalue()

            return csv_content.encode('utf-8')

        except Exception as e:
            logger.error(f"Error converting Excel to CSV: {e}")
            raise Exception(f"Failed to convert Excel file: {str(e)}")

    @staticmethod
    def detect_file_type(filename: str) -> str:
        """
        Detect file type from filename.

        Args:
            filename: Name of the file

        Returns:
            File type ('csv', 'excel', 'unknown')
        """
        extension = filename.lower().split('.')[-1]

        if extension == 'csv':
            return 'csv'
        elif extension in ['xlsx', 'xls']:
            return 'excel'
        else:
            return 'unknown'

    @staticmethod
    def normalize_file_content(file_content: bytes, filename: str, target_delimiter: str = '|') -> bytes:
        """
        Normalize file content to CSV format with specified delimiter.

        Args:
            file_content: Original file content as bytes
            filename: Original filename
            target_delimiter: Target CSV delimiter

        Returns:
            Normalized CSV content as bytes
        """
        file_type = FileUtils.detect_file_type(filename)

        if file_type == 'excel':
            logger.info(f"Converting Excel file to CSV: {filename}")
            return FileUtils.excel_to_csv(file_content, target_delimiter)
        elif file_type == 'csv':
            # If it's already CSV, check if we need to change delimiter
            try:
                content_str = file_content.decode('utf-8')

                # Try to detect current delimiter
                sample_lines = content_str.split('\n')[:5]
                sample_text = '\n'.join(sample_lines)

                # Common delimiters to check (including tab)
                delimiters = ['\t', '|', ',', ';']
                detected_delimiter = '\t'  # default to tab since many timestamp files use tabs

                max_columns = 0
                for delimiter in delimiters:
                    try:
                        df_test = pd.read_csv(io.StringIO(sample_text), sep=delimiter, header=None, nrows=2)
                        if len(df_test.columns) > max_columns:
                            max_columns = len(df_test.columns)
                            detected_delimiter = delimiter
                    except:
                        continue

                logger.info(f"Detected CSV delimiter: '{detected_delimiter}' for {filename}")

                # If detected delimiter is different from target, convert
                if detected_delimiter != target_delimiter:
                    df = pd.read_csv(io.StringIO(content_str), sep=detected_delimiter, header=None)
                    csv_buffer = io.StringIO()
                    df.to_csv(csv_buffer, sep=target_delimiter, index=False, header=False)
                    return csv_buffer.getvalue().encode('utf-8')
                else:
                    return file_content

            except Exception as e:
                logger.warning(f"Could not process CSV delimiter conversion: {e}")
                return file_content
        else:
            raise Exception(f"Unsupported file type: {file_type}")

    @staticmethod
    def get_file_info(file_content: bytes, filename: str) -> Dict[str, Any]:
        """
        Get information about the file content.

        Args:
            file_content: File content as bytes
            filename: Original filename

        Returns:
            Dict with file information
        """
        info = {
            'filename': filename,
            'size_bytes': len(file_content),
            'size_mb': round(len(file_content) / (1024 * 1024), 2),
            'type': FileUtils.detect_file_type(filename),
            'rows': 0,
            'columns': 0,
            'encoding': 'unknown'
        }

        try:
            # Try to detect encoding
            try:
                content_str = file_content.decode('utf-8')
                info['encoding'] = 'utf-8'
            except UnicodeDecodeError:
                try:
                    content_str = file_content.decode('latin-1')
                    info['encoding'] = 'latin-1'
                except:
                    info['encoding'] = 'unknown'
                    return info

            # If it's a CSV-like file, get row/column info
            if info['type'] in ['csv', 'unknown']:
                try:
                    # Try common delimiters
                    for delimiter in [',', ';', '\t', '|']:
                        try:
                            df = pd.read_csv(io.StringIO(content_str), sep=delimiter, header=None, nrows=100)
                            if len(df.columns) > info['columns']:
                                info['rows'] = len(df)
                                info['columns'] = len(df.columns)
                                info['delimiter'] = delimiter
                        except:
                            continue
                except Exception as e:
                    logger.debug(f"Could not analyze CSV structure: {e}")

            elif info['type'] == 'excel':
                try:
                    df = pd.read_excel(io.BytesIO(file_content), nrows=100)
                    info['rows'] = len(df)
                    info['columns'] = len(df.columns)
                except Exception as e:
                    logger.debug(f"Could not analyze Excel structure: {e}")

        except Exception as e:
            logger.error(f"Error getting file info: {e}")

        return info

    @staticmethod
    def validate_csv_structure(file_content: bytes, expected_columns: int = None, delimiter: str = '|') -> Dict[str, Any]:
        """
        Validate CSV file structure.

        Args:
            file_content: CSV file content as bytes
            expected_columns: Expected number of columns (optional)
            delimiter: CSV delimiter

        Returns:
            Dict with validation results
        """
        result = {
            'valid': True,
            'errors': [],
            'warnings': [],
            'info': {}
        }

        try:
            content_str = file_content.decode('utf-8')
            df = pd.read_csv(io.StringIO(content_str), sep=delimiter, header=None)

            result['info'] = {
                'rows': len(df),
                'columns': len(df.columns),
                'empty_rows': df.isnull().all(axis=1).sum(),
                'empty_columns': df.isnull().all(axis=0).sum()
            }

            # Check expected columns
            if expected_columns and len(df.columns) != expected_columns:
                result['valid'] = False
                result['errors'].append(f"Expected {expected_columns} columns, found {len(df.columns)}")

            # Check for completely empty file
            if len(df) == 0:
                result['valid'] = False
                result['errors'].append("File is empty")

            # Check for rows with all empty values
            if result['info']['empty_rows'] > 0:
                result['warnings'].append(f"Found {result['info']['empty_rows']} empty rows")

            # Check for columns with all empty values
            if result['info']['empty_columns'] > 0:
                result['warnings'].append(f"Found {result['info']['empty_columns']} empty columns")

        except UnicodeDecodeError:
            result['valid'] = False
            result['errors'].append("File encoding not supported")
        except Exception as e:
            result['valid'] = False
            result['errors'].append(f"CSV validation error: {str(e)}")

        return result
