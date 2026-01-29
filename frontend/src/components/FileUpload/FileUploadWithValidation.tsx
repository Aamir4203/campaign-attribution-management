/**
 * File Upload Component with Real-time Validation
 * Handles file selection, validation, and upload with visual feedback
 */

import React, { useCallback, useRef } from 'react';
import { useFileUpload } from '../../hooks/useFileUpload';
import ValidationIndicator from './ValidationIndicator';

interface FileUploadWithValidationProps {
  fileType: 'timestamp' | 'cpm' | 'decile' | 'unique_decile';
  clientName: string;
  weekName: string;
  onFileValidated: (filePath: string) => void;
  onValidationError?: (error: string) => void;
  className?: string;
  disabled?: boolean;
}

const FileUploadWithValidation: React.FC<FileUploadWithValidationProps> = ({
  fileType,
  clientName,
  weekName,
  onFileValidated,
  onValidationError,
  className = '',
  disabled = false
}) => {
  const fileInputRef = useRef<HTMLInputElement>(null);

  const {
    isValidating,
    isUploading,
    isValid,
    validationResult,
    uploadResult,
    error,
    selectedFile,
    validateFile,
    uploadFile,
    uploadWithValidation,
    resetState,
    getExpectedFilename,
    isFileSupported,
    validateFileSize,
    formatFileSize,
    isProcessing,
    canUpload
  } = useFileUpload({
    fileType,
    clientName,
    weekName,
    onUploadSuccess: onFileValidated,
    // Don't use onValidationResult to call onValidationError - ValidationIndicator handles display
    onValidationResult: undefined
  });

  const handleFileSelect = useCallback(async (file: File) => {
    console.log(`━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━`);
    console.log(`📂 FileUploadWithValidation: New file selected - ${fileType}`);
    console.log(`   Filename: ${file.name}`);
    console.log(`   Size: ${file.size} bytes`);
    console.log(`   Type: ${file.type}`);
    console.log(`   Last Modified: ${file.lastModified}`);

    // Read first few bytes to verify we're getting new content (not browser cache)
    try {
      const reader = new FileReader();
      const slice = file.slice(0, 100); // Read first 100 bytes
      reader.onload = (e) => {
        const preview = e.target?.result as string;
        console.log(`   📄 File content preview (first 100 chars):`, preview.substring(0, 100));
      };
      reader.readAsText(slice);
    } catch (err) {
      console.log(`   ⚠️ Could not preview file content:`, err);
    }

    // CRITICAL: Clear previous upload result when selecting new file
    console.log(`🗑️ Clearing previous state...`);
    resetState();

    // Basic validation first
    if (!isFileSupported(file.name)) {
      console.log(`❌ File type not supported: ${file.name}`);
      if (onValidationError) {
        onValidationError('Unsupported file type. Please use CSV, XLSX, or XLS files.');
      }
      return;
    }

    if (!validateFileSize(file)) {
      console.log(`❌ File too large: ${file.name}`);
      if (onValidationError) {
        onValidationError('File is too large. Maximum size is 50MB.');
      }
      return;
    }

    // Clear any previous errors before validation
    if (onValidationError) {
      onValidationError('');
    }

    console.log(`🔍 Starting validation for ${fileType}...`);

    // Perform validation with auto-upload on success
    try {
      const result = await validateFile(file, true); // Enable auto-upload after validation passes
      console.log(`✅ Validation completed for ${fileType}:`, result?.valid ? 'VALID' : 'INVALID');
    } catch (error) {
      console.error('❌ File validation error:', error);
      // Only report system errors, not validation failures
      if (onValidationError && error instanceof Error) {
        onValidationError(`System error: ${error.message}`);
      }
    }
    console.log(`━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━`);
  }, [isFileSupported, validateFileSize, validateFile, onValidationError, resetState, fileType]);

  const handleFileInputChange = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files;
    console.log(`📥 File input changed, files:`, files?.length);

    if (files && files.length > 0) {
      // Clear any previous errors immediately when new file is selected
      if (onValidationError) {
        onValidationError('');
      }
      handleFileSelect(files[0]);
    }

    // IMPORTANT: Clear the input value after processing to allow re-selecting same filename
    // This ensures onChange fires even if user selects the same file again
    if (fileInputRef.current) {
      // Clear after a small delay to ensure the file has been processed
      setTimeout(() => {
        if (fileInputRef.current) {
          fileInputRef.current.value = '';
          console.log(`🔄 File input value cleared - ready for re-upload`);
        }
      }, 100);
    }
  }, [handleFileSelect, onValidationError]);

  const handleUploadClick = useCallback(async () => {
    if (selectedFile && canUpload) {
      try {
        await uploadFile();
      } catch (error) {
        console.error('Upload error:', error);
      }
    }
  }, [selectedFile, canUpload, uploadFile]);

  const handleReset = useCallback(() => {
    resetState();
    if (fileInputRef.current) {
      fileInputRef.current.value = '';
    }
  }, [resetState]);

  const expectedFilename = getExpectedFilename();
  const fileTypeLabel = fileType === 'cpm'
    ? 'CPM Report'
    : fileType === 'decile'
      ? 'Decile Report'
      : fileType === 'unique_decile'
        ? 'Unique Decile Report'
        : 'Timestamp Report';

  return (
    <div className={`${className}`}>
      {/* Simple Text Box and Upload Button Layout */}
      <div className="flex gap-2 items-center">
        <input
          type="text"
          value={uploadResult?.file_path ? uploadResult.file_path : (selectedFile ? selectedFile.name : '')}
          readOnly
          placeholder={uploadResult?.success ? 'File uploaded successfully' : `Select ${fileTypeLabel} file`}
          className="w-60 px-2 py-1 border border-gray-300 rounded focus:outline-none focus:ring-2 focus:ring-purple-500 bg-white text-sm"
        />
        <button
          type="button"
          onClick={() => fileInputRef.current?.click()}
          disabled={disabled}
          className="px-2 py-1 bg-green-600 hover:bg-green-700 text-white rounded transition-colors text-sm disabled:opacity-50 disabled:cursor-not-allowed"
          title="Select file to upload"
        >
          Upload
        </button>
      </div>

      {/* Hidden File Input */}
      <input
        ref={fileInputRef}
        type="file"
        accept=".csv,.xlsx,.xls"
        onChange={handleFileInputChange}
        className="hidden"
        disabled={disabled}
      />

      {/* File Size Display */}
      {selectedFile && !uploadResult?.success && (
        <p className="text-xs text-gray-500 mt-1">
          Selected: {selectedFile.name} ({formatFileSize(selectedFile.size)})
        </p>
      )}

      {/* Validation Result - Only show when validating or if there are errors/warnings */}
      {(isValidating || (validationResult && (!validationResult.valid || (validationResult.warnings && validationResult.warnings.length > 0)))) && !uploadResult?.success && (
        <div className="mt-2">
          <ValidationIndicator
            isValidating={isValidating}
            validationResult={validationResult}
            className=""
          />
        </div>
      )}

      {/* Upload Progress - Auto-upload after validation */}
      {isUploading && (
        <div className="flex items-center gap-2 mt-2 text-sm text-blue-600">
          <div className="animate-spin rounded-full h-4 w-4 border-2 border-blue-600 border-t-transparent"></div>
          <span>Saving file...</span>
        </div>
      )}

      {/* Clear button (only show if file selected but not uploaded yet, and not currently uploading) */}
      {selectedFile && !uploadResult?.success && !isUploading && (
        <div className="mt-2">
          <button
            onClick={handleReset}
            disabled={isProcessing}
            className="px-2 py-1 bg-gray-600 text-white rounded hover:bg-gray-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors text-sm"
          >
            Clear
          </button>
        </div>
      )}

      {/* Error Display */}
      {error && (
        <div className="mt-2 p-3 bg-red-100 border border-red-300 rounded-lg">
          <div className="flex items-start space-x-2">
            <svg className="h-5 w-5 text-red-500 flex-shrink-0 mt-0.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
            <span className="text-sm text-red-700">{error}</span>
          </div>
        </div>
      )}
    </div>
  );
};

export default FileUploadWithValidation;
