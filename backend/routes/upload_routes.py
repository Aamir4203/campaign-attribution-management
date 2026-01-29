"""
Upload Routes for CAM Application
Handles file upload, validation, and cross-validation
"""

from flask import Blueprint, jsonify, request
import logging
from config.config import get_config
from services.file_validation_service import FileValidationService
from services.upload_service import UploadService
from utils.file_utils import FileUtils

logger = logging.getLogger(__name__)
config = get_config()

# Initialize services
file_validator = FileValidationService(config)
upload_service = UploadService(config)

# Create blueprint
upload_bp = Blueprint('upload', __name__)


@upload_bp.route('/api/upload/validate', methods=['POST'])
def validate_file_upload():
    """Real-time file validation endpoint"""
    logger.info("=" * 80)
    logger.info("📋 VALIDATION ENDPOINT CALLED: /api/upload/validate")

    try:
        # Check if feature is enabled
        if not config.is_feature_enabled('file_upload_enabled'):
            logger.warning("❌ File upload feature is not enabled")
            return jsonify({
                'success': False,
                'error': 'File upload feature is not enabled'
            }), 403

        # Validate request
        if 'file' not in request.files:
            logger.error("❌ No file in request")
            return jsonify({
                'success': False,
                'error': 'No file provided'
            }), 400

        file = request.files['file']
        if file.filename == '':
            logger.error("❌ Empty filename")
            return jsonify({
                'success': False,
                'error': 'No file selected'
            }), 400

        # Get file type and parameters
        file_type = request.form.get('file_type')
        client_name = request.form.get('client_name', '')
        week_name = request.form.get('week_name', '')

        logger.info(f"📄 File: {file.filename}")
        logger.info(f"📦 Type: {file_type}")
        logger.info(f"👤 Client: {client_name}")
        logger.info(f"📅 Week: {week_name}")

        if not file_type:
            logger.error("❌ File type is required")
            return jsonify({
                'success': False,
                'error': 'File type is required'
            }), 400

        if file_type not in ['timestamp', 'cpm', 'decile', 'unique_decile']:
            logger.error(f"❌ Invalid file type: {file_type}")
            return jsonify({
                'success': False,
                'error': 'Invalid file type. Must be: timestamp, cpm, decile, or unique_decile'
            }), 400

        # Read file content
        file_content = file.read()
        filename = file.filename
        logger.info(f"📏 File size: {len(file_content)} bytes")

        # Normalize file content (convert Excel to CSV if needed)
        try:
            logger.info("🔄 Normalizing file content...")
            normalized_content = FileUtils.normalize_file_content(file_content, filename, '|')
            logger.info(f"✅ Content normalized: {len(normalized_content)} bytes")
        except Exception as e:
            logger.error(f"❌ File normalization error: {e}")
            return jsonify({
                'success': False,
                'error': f'File format error: {str(e)}'
            }), 400

        # Validate file
        logger.info(f"🔍 Starting validation for {file_type} file...")
        validation_result = file_validator.validate_file(normalized_content, filename, file_type)

        logger.info(f"📊 Validation Result:")
        logger.info(f"   Valid: {validation_result['valid']}")
        logger.info(f"   Errors: {len(validation_result.get('errors', []))}")
        logger.info(f"   Warnings: {len(validation_result.get('warnings', []))}")
        if validation_result.get('errors'):
            for error in validation_result['errors']:
                logger.error(f"   ❌ {error}")
        if validation_result.get('warnings'):
            for warning in validation_result['warnings']:
                logger.warning(f"   ⚠️ {warning}")

        # Add expected filename info
        if client_name and week_name:
            expected_filename = upload_service.generate_filename(file_type, client_name, week_name)
            validation_result['expected_filename'] = expected_filename
            validation_result['file_exists'] = upload_service.file_exists(file_type, client_name, week_name)

        logger.info(f"{'✅ VALIDATION PASSED' if validation_result['valid'] else '❌ VALIDATION FAILED'}")
        logger.info("=" * 80)

        return jsonify({
            'success': True,
            'validation': validation_result
        })

    except Exception as e:
        logger.error(f"❌ Exception in file validation: {e}", exc_info=True)
        logger.info("=" * 80)
        return jsonify({
            'success': False,
            'error': f'Validation error: {str(e)}'
        }), 500


@upload_bp.route('/api/upload/save', methods=['POST'])
def save_uploaded_file():
    """Save validated file to storage"""
    logger.info("=" * 80)
    logger.info("💾 SAVE ENDPOINT CALLED: /api/upload/save")

    try:
        # Check if feature is enabled
        if not config.is_feature_enabled('file_upload_enabled'):
            logger.warning("❌ File upload feature is not enabled")
            return jsonify({
                'success': False,
                'error': 'File upload feature is not enabled'
            }), 403

        # Validate request
        if 'file' not in request.files:
            logger.error("❌ No file in request")
            return jsonify({
                'success': False,
                'error': 'No file provided'
            }), 400

        file = request.files['file']
        if file.filename == '':
            logger.error("❌ Empty filename")
            return jsonify({
                'success': False,
                'error': 'No file selected'
            }), 400

        # Get required parameters
        file_type = request.form.get('file_type')
        client_name = request.form.get('client_name', '')
        week_name = request.form.get('week_name', '')

        logger.info(f"📄 File: {file.filename}")
        logger.info(f"📦 Type: {file_type}")
        logger.info(f"👤 Client: {client_name}")
        logger.info(f"📅 Week: {week_name}")

        if not all([file_type, client_name, week_name]):
            logger.error("❌ Missing required parameters")
            return jsonify({
                'success': False,
                'error': 'file_type, client_name, and week_name are required'
            }), 400

        # Read and normalize file content
        file_content = file.read()
        filename = file.filename
        logger.info(f"📏 File size: {len(file_content)} bytes")

        try:
            logger.info("🔄 Normalizing file content...")
            normalized_content = FileUtils.normalize_file_content(file_content, filename, '|')
            logger.info(f"✅ Content normalized: {len(normalized_content)} bytes")
        except Exception as e:
            logger.error(f"❌ File normalization error: {e}")
            return jsonify({
                'success': False,
                'error': f'File format error: {str(e)}'
            }), 400

        # Validate file first (if realtime validation is enabled)
        validation_result = None
        if config.is_feature_enabled('realtime_validation'):
            logger.info("🔍 Performing validation before save...")
            validation_result = file_validator.validate_file(normalized_content, filename, file_type)

            logger.info(f"📊 Validation Result:")
            logger.info(f"   Valid: {validation_result['valid']}")
            logger.info(f"   Errors: {len(validation_result.get('errors', []))}")

            if not validation_result['valid']:
                logger.error("❌ File validation failed before save")
                for error in validation_result.get('errors', []):
                    logger.error(f"   ❌ {error}")
                return jsonify({
                    'success': False,
                    'error': 'File validation failed',
                    'validation': validation_result
                }), 400

            logger.info("✅ Validation passed - proceeding with save")

        # Save file
        logger.info("💾 Saving file to storage...")
        save_result = upload_service.save_file(normalized_content, file_type, client_name, week_name, filename)

        if not save_result['success']:
            logger.error(f"❌ Save failed: {save_result.get('errors')}")
            return jsonify({
                'success': False,
                'error': 'Failed to save file',
                'details': save_result['errors']
            }), 500

        logger.info(f"✅ FILE SAVED SUCCESSFULLY!")
        logger.info(f"   Path: {save_result['file_path']}")
        logger.info(f"   Absolute Path: {save_result['absolute_path']}")
        logger.info(f"   Filename: {save_result['filename']}")
        logger.info("=" * 80)

        return jsonify({
            'success': True,
            'file_path': save_result['absolute_path'],
            'filename': save_result['filename'],
            'file_info': save_result.get('file_info', {}),
            'validation': validation_result  # Return validation result if performed
        })

    except Exception as e:
        logger.error(f"❌ Exception during save: {e}", exc_info=True)
        logger.info("=" * 80)
        return jsonify({
            'success': False,
            'error': f'Upload error: {str(e)}'
        }), 500


@upload_bp.route('/api/upload/cross-validate', methods=['POST'])
def cross_validate_files():
    """Cross-validate multiple uploaded files"""
    logger.info("=" * 80)
    logger.info("🔗 CROSS-VALIDATION ENDPOINT CALLED: /api/upload/cross-validate")

    try:
        # Check if feature is enabled
        if not config.is_feature_enabled('file_upload_enabled'):
            logger.warning("❌ File upload feature is not enabled")
            return jsonify({
                'success': False,
                'error': 'File upload feature is not enabled'
            }), 403

        # Get uploaded files
        files_data = {}
        filenames = {}

        logger.info("📂 Checking for uploaded files in request...")
        # Check for each file type
        for file_type in ['cpm', 'decile', 'timestamp', 'unique_decile']:
            if file_type in request.files:
                file = request.files[file_type]
                if file and file.filename:
                    files_data[file_type] = file.read()
                    filenames[file_type] = file.filename
                    logger.info(f"   ✅ Found {file_type}: {file.filename}")

        # Also check for file paths if files are already uploaded
        client_name = request.form.get('client_name', '')
        week_name = request.form.get('week_name', '')

        logger.info("📁 Checking for file paths in request...")
        # Read from uploaded files if paths are provided
        for file_type in ['cpm', 'decile', 'timestamp', 'unique_decile']:
            file_path = request.form.get(f'{file_type}_path')
            if file_path and file_type not in files_data:
                try:
                    logger.info(f"   Reading {file_type} from path: {file_path}")
                    with open(file_path, 'rb') as f:
                        files_data[file_type] = f.read()
                        filenames[file_type] = file_path.split('/')[-1]
                    logger.info(f"   ✅ Loaded {file_type} from path")
                except Exception as e:
                    logger.warning(f"   ⚠️ Could not read {file_type} file from path {file_path}: {e}")

        if not files_data:
            logger.error("❌ No files provided for cross-validation")
            return jsonify({
                'success': False,
                'error': 'No files provided for cross-validation'
            }), 400

        logger.info(f"🔍 Starting cross-validation with {len(files_data)} file(s):")
        for file_type in files_data.keys():
            logger.info(f"   - {file_type}: {filenames.get(file_type, 'unknown')}")

        # Perform cross-validation
        cross_validation_result = file_validator.cross_validate_files(files_data, filenames)

        logger.info(f"📊 Cross-Validation Result:")
        logger.info(f"   Valid: {cross_validation_result['valid']}")
        logger.info(f"   Validations Performed: {cross_validation_result['validations_performed']}")
        logger.info(f"   Errors: {len(cross_validation_result.get('errors', []))}")
        logger.info(f"   Warnings: {len(cross_validation_result.get('warnings', []))}")

        if cross_validation_result.get('errors'):
            for error in cross_validation_result['errors']:
                logger.error(f"   ❌ {error}")
        if cross_validation_result.get('warnings'):
            for warning in cross_validation_result['warnings']:
                logger.warning(f"   ⚠️ {warning}")

        logger.info(f"{'✅ CROSS-VALIDATION PASSED' if cross_validation_result['valid'] else '❌ CROSS-VALIDATION FAILED'}")
        logger.info("=" * 80)

        return jsonify({
            'success': True,
            'cross_validation': cross_validation_result
        })

    except Exception as e:
        logger.error(f"❌ Exception in cross-validation: {e}", exc_info=True)
        logger.info("=" * 80)
        return jsonify({
            'success': False,
            'error': f'Cross-validation error: {str(e)}'
        }), 500
