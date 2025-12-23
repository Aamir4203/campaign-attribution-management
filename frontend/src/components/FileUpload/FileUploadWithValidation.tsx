/**
 * File Upload Component with Real-time Validation
 * Handles file selection, validation, and upload with visual feedback
 */

import React, { useCallback, useRef, useState } from 'react';
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
  const [dragActive, setDragActive] = useState(false);

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

  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    if (!disabled && !uploadResult?.success) {
      setDragActive(true);
    }
  }, [disabled, uploadResult?.success]);

  const handleDragLeave = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);
  }, []);

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);

    if (disabled || uploadResult?.success) return;

    const files = e.dataTransfer.files;
    if (files && files.length > 0) {
      handleFileSelect(files[0]);
    }
  }, [disabled, uploadResult?.success, handleFileSelect]);

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
    <div className={`space-y-3 ${className}`}>
      {/* File Input Area - Hide when successfully uploaded */}
      {!uploadResult?.success && (
        <div
          className={`
            relative border-2 border-dashed rounded-lg p-6 text-center transition-colors
            ${dragActive ? 'border-blue-400 bg-blue-50' : 'border-gray-300'}
            ${disabled ? 'opacity-50 cursor-not-allowed' : 'hover:border-gray-400 cursor-pointer'}
            ${isValid === true && !uploadResult?.success ? 'border-green-400 bg-green-50' : ''}
            ${isValid === false ? 'border-red-400 bg-red-50' : ''}
          `}
          onDragOver={handleDragOver}
          onDragLeave={handleDragLeave}
          onDrop={handleDrop}
          onClick={() => !disabled && !uploadResult?.success && fileInputRef.current?.click()}
        >
          <input
            ref={fileInputRef}
            type="file"
            accept=".csv,.xlsx,.xls"
            onChange={handleFileInputChange}
            className="hidden"
            disabled={disabled}
          />

          <div className="space-y-2">
            <div className="flex justify-center">
              {isProcessing ? (
                <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
              ) : isValid === true ? (
                <svg className="h-8 w-8 text-green-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
              ) : isValid === false ? (
                <svg className="h-8 w-8 text-red-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 14l2-2m0 0l2-2m-2 2l-2-2m2 2l2 2m7-2a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
              ) : (
                <svg className="h-8 w-8 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
                </svg>
              )}
            </div>

            <div>
              <p className="text-sm font-medium text-gray-700">
                {selectedFile ? selectedFile.name : `Upload ${fileTypeLabel}`}
              </p>
              <p className="text-xs text-gray-500 mt-1">
                Drag and drop or click to select • CSV, XLSX, XLS • Max 50MB
              </p>
            </div>

            {selectedFile && (
              <div className="text-xs text-gray-600">
                Size: {formatFileSize(selectedFile.size)}
              </div>
            )}
          </div>
        </div>
      )}

      {/* Validation Result - Hide when successfully uploaded */}
      {!uploadResult?.success && (
        <ValidationIndicator
          isValidating={isValidating}
          validationResult={validationResult}
          className="min-h-[60px]"
        />
      )}

      {/* Action Buttons or File Path Display */}
      {uploadResult?.success ? (
        // Show file path text box with re-upload option after successful upload
        <div className="space-y-2">
          <div>
            <label className="block text-xs font-medium text-gray-700 mb-1">
              Uploaded File Path
            </label>
            <div className="flex gap-2 items-center">
              <input
                type="text"
                value={uploadResult.file_path || ''}
                readOnly
                className="w-60 px-2 py-1 border border-gray-300 rounded focus:outline-none focus:ring-2 focus:ring-blue-500 bg-white text-sm text-gray-700"
              />
              <button
                onClick={handleReset}
                className="px-2 py-1 bg-green-600 hover:bg-green-700 text-white rounded transition-colors text-sm"
                title="Upload new file"
              >
                Upload
              </button>
            </div>
          </div>
        </div>
      ) : selectedFile ? (
        // Show upload/clear buttons before upload
        <div className="flex gap-2">
          {canUpload && (
            <button
              onClick={handleUploadClick}
              disabled={isUploading}
              className="px-2 py-1 bg-green-600 text-white rounded hover:bg-green-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors text-sm flex items-center gap-2"
            >
              {isUploading && <div className="animate-spin rounded-full h-3 w-3 border-b-2 border-white"></div>}
              <span>{isUploading ? 'Uploading...' : 'Upload File'}</span>
            </button>
          )}

          <button
            onClick={handleReset}
            disabled={isProcessing}
            className="px-2 py-1 bg-gray-600 text-white rounded hover:bg-gray-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors text-sm"
          >
            Clear
          </button>
        </div>
      ) : null}


      {/* Error Display */}
      {error && (
        <div className="p-3 bg-red-100 border border-red-300 rounded-lg">
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
