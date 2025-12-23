#!/usr/bin/env python3
"""
Upload Service for CAM Application
Handles file upload, naming, and storage operations
"""

import os
import logging
from pathlib import Path
from typing import Dict, Any, Optional
import shutil
from datetime import datetime

logger = logging.getLogger(__name__)

class UploadService:
    """
    Service class for handling file uploads and storage.
    """
    
    def __init__(self, config):
        """
        Initialize upload service with configuration.
        
        Args:
            config: Configuration manager instance
        """
        self.config = config
        self.upload_config = config.get_upload_config()
        self.base_path = self.upload_config.get('base_path', 'REPORT_FILES')
        self.naming_config = self.upload_config.get('naming', {})
        
        # Ensure upload directory exists
        self._ensure_upload_directory()
    
    def _ensure_upload_directory(self):
        """Create upload directory if it doesn't exist"""
        try:
            upload_dir = Path(self.base_path)
            upload_dir.mkdir(exist_ok=True)
            logger.info(f"Upload directory ready: {upload_dir.absolute()}")
        except Exception as e:
            logger.error(f"Failed to create upload directory: {e}")
            raise
    
    def generate_filename(self, file_type: str, client_name: str, week_name: str) -> str:
        """
        Generate filename based on configuration and parameters.
        
        Args:
            file_type: Type of file ('timestamp', 'cpm', 'decile')
            client_name: Client name from form
            week_name: Week name from form
            
        Returns:
            Generated filename
        """
        try:
            # Get prefix based on file type
            prefix_map = {
                'timestamp': self.naming_config.get('timestamp_prefix', 'TimeStampReport'),
                'cpm': self.naming_config.get('cpm_prefix', 'CPM_Report'),
                'decile': self.naming_config.get('decile_prefix', 'Decile_Report')
            }
            
            prefix = prefix_map.get(file_type, f'{file_type.title()}_Report')
            
            # Clean client name and week name for filename
            clean_client = self._clean_filename_part(client_name)
            clean_week = self._clean_filename_part(week_name)
            
            # Generate filename using configured format
            filename_format = self.naming_config.get('format', '{prefix}_{client_name}_{week_name}.csv')
            filename = filename_format.format(
                prefix=prefix,
                client_name=clean_client,
                week_name=clean_week
            )
            
            return filename
            
        except Exception as e:
            logger.error(f"Error generating filename: {e}")
            # Fallback to simple naming
            return f"{file_type}_{client_name}_{week_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    
    def _clean_filename_part(self, name: str) -> str:
        """
        Clean string for use in filename.
        
        Args:
            name: String to clean
            
        Returns:
            Cleaned string safe for filename
        """
        # Remove or replace invalid filename characters
        import re
        # Replace spaces and special characters with underscores
        cleaned = re.sub(r'[^\w\-_.]', '_', name)
        # Remove multiple consecutive underscores
        cleaned = re.sub(r'_{2,}', '_', cleaned)
        # Remove leading/trailing underscores
        cleaned = cleaned.strip('_')
        return cleaned
    
    def save_file(self, file_content: bytes, file_type: str, client_name: str, week_name: str, original_filename: str = None) -> Dict[str, Any]:
        """
        Save uploaded file to storage with proper naming.
        
        Args:
            file_content: File content as bytes
            file_type: Type of file ('timestamp', 'cpm', 'decile')
            client_name: Client name from form
            week_name: Week name from form
            original_filename: Original uploaded filename (optional)
            
        Returns:
            Dict with save results including file path
        """
        result = {
            'success': True,
            'file_path': '',
            'absolute_path': '',
            'filename': '',
            'errors': []
        }
        
        try:
            # Generate filename
            filename = self.generate_filename(file_type, client_name, week_name)
            result['filename'] = filename
            
            # Create full path
            file_path = Path(self.base_path) / filename
            result['file_path'] = str(file_path)
            result['absolute_path'] = str(file_path.absolute())
            
            # Check if file already exists (overwrite as per requirement)
            if file_path.exists():
                logger.info(f"Overwriting existing file: {file_path}")
            
            # Write file content
            with open(file_path, 'wb') as f:
                f.write(file_content)
            
            # Verify file was written
            if not file_path.exists():
                raise Exception("File was not written successfully")
            
            file_size = file_path.stat().st_size
            logger.info(f"File saved successfully: {file_path} ({file_size} bytes)")
            
            result['file_info'] = {
                'size_bytes': file_size,
                'size_mb': round(file_size / (1024 * 1024), 2),
                'created_at': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error saving file: {e}")
            result['success'] = False
            result['errors'].append(f"Failed to save file: {str(e)}")
        
        return result
    
    def get_file_path(self, file_type: str, client_name: str, week_name: str) -> str:
        """
        Get the expected file path for given parameters without saving.
        
        Args:
            file_type: Type of file ('timestamp', 'cpm', 'decile')
            client_name: Client name from form
            week_name: Week name from form
            
        Returns:
            Expected file path
        """
        filename = self.generate_filename(file_type, client_name, week_name)
        file_path = Path(self.base_path) / filename
        return str(file_path.absolute())
    
    def file_exists(self, file_type: str, client_name: str, week_name: str) -> bool:
        """
        Check if file already exists for given parameters.
        
        Args:
            file_type: Type of file ('timestamp', 'cpm', 'decile')
            client_name: Client name from form  
            week_name: Week name from form
            
        Returns:
            True if file exists
        """
        try:
            filename = self.generate_filename(file_type, client_name, week_name)
            file_path = Path(self.base_path) / filename
            return file_path.exists()
        except Exception as e:
            logger.error(f"Error checking file existence: {e}")
            return False
    
    def delete_file(self, file_type: str, client_name: str, week_name: str) -> bool:
        """
        Delete file for given parameters.
        
        Args:
            file_type: Type of file ('timestamp', 'cmp', 'decile')
            client_name: Client name from form
            week_name: Week name from form
            
        Returns:
            True if deletion successful
        """
        try:
            filename = self.generate_filename(file_type, client_name, week_name)
            file_path = Path(self.base_path) / filename
            
            if file_path.exists():
                file_path.unlink()
                logger.info(f"File deleted: {file_path}")
                return True
            else:
                logger.warning(f"File not found for deletion: {file_path}")
                return False
                
        except Exception as e:
            logger.error(f"Error deleting file: {e}")
            return False
    
    def cleanup_old_files(self, days_old: int = 30) -> int:
        """
        Clean up old uploaded files.
        
        Args:
            days_old: Delete files older than this many days
            
        Returns:
            Number of files deleted
        """
        deleted_count = 0
        try:
            upload_dir = Path(self.base_path)
            cutoff_time = datetime.now().timestamp() - (days_old * 24 * 60 * 60)
            
            for file_path in upload_dir.glob('*'):
                if file_path.is_file():
                    file_mod_time = file_path.stat().st_mtime
                    if file_mod_time < cutoff_time:
                        file_path.unlink()
                        deleted_count += 1
                        logger.info(f"Deleted old file: {file_path}")
            
            logger.info(f"Cleanup completed. Deleted {deleted_count} old files.")
            
        except Exception as e:
            logger.error(f"Error during cleanup: {e}")
        
        return deleted_count
