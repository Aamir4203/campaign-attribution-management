/**
 * File Upload Component with Real-time Validation
 * Handles file selection, validation, and upload with visual feedback
 */

import React, { useCallback, useRef } from 'react';
import { useFileUpload } from '../../hooks/useFileUpload';
import ValidationIndicator from './ValidationIndicator';

interface FileUploadWithValidationProps {
  fileType: 'timestamp' | 'cpm' | 'decile';
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
    onValidationResult: (result) => {
      if (!result.valid && onValidationError) {
        onValidationError(result.errors.join(', '));
      }
    }
  });

  const handleFileSelect = useCallback(async (file: File) => {
    // Basic validation first
    if (!isFileSupported(file.name)) {
      onValidationError?.('Unsupported file type. Please use CSV, XLSX, or XLS files.');
      return;
    }

    if (!validateFileSize(file)) {
      onValidationError?.('File is too large. Maximum size is 50MB.');
      return;
    }

    // Perform validation
    try {
      await validateFile(file);
    } catch (error) {
      console.error('File validation error:', error);
    }
  }, [isFileSupported, validateFileSize, validateFile, onValidationError]);

  const handleFileInputChange = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files;
    if (files && files.length > 0) {
      handleFileSelect(files[0]);
    }
  }, [handleFileSelect]);

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
  const fileTypeLabel = fileType === 'cpm' ? 'CPM Report' : fileType === 'decile' ? 'Decile Report' : 'Timestamp Report';

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

      {/* Upload Progress and Action Buttons */}
      {selectedFile && !uploadResult?.success && canUpload && (
        <div className="flex gap-2 mt-2">
          <button
            onClick={handleUploadClick}
            disabled={isUploading}
            className="px-2 py-1 bg-blue-600 text-white rounded hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors text-sm flex items-center gap-2"
          >
            {isUploading && <div className="animate-spin rounded-full h-3 w-3 border-b-2 border-white"></div>}
            <span>{isUploading ? 'Uploading...' : 'Save File'}</span>
          </button>

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
