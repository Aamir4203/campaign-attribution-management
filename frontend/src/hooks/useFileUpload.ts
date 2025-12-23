/**
 * Custom hook for file upload functionality
 * Manages upload state, validation, and UI feedback
 */

import { useState, useCallback } from 'react';
import UploadService, { FileUploadRequest, ValidationResult, UploadResponse } from '../services/uploadService';

interface UseFileUploadProps {
  fileType: 'timestamp' | 'cpm' | 'decile';
  clientName: string;
  weekName: string;
  onUploadSuccess?: (filePath: string) => void;
  onValidationResult?: (result: ValidationResult) => void;
}

interface FileUploadState {
  isValidating: boolean;
  isUploading: boolean;
  isValid: boolean | null;
  validationResult: ValidationResult | null;
  uploadResult: UploadResponse | null;
  error: string | null;
  selectedFile: File | null;
}

export const useFileUpload = ({
  fileType,
  clientName,
  weekName,
  onUploadSuccess,
  onValidationResult
}: UseFileUploadProps) => {
  const [state, setState] = useState<FileUploadState>({
    isValidating: false,
    isUploading: false,
    isValid: null,
    validationResult: null,
    uploadResult: null,
    error: null,
    selectedFile: null,
  });

  const uploadService = new UploadService();

  const resetState = useCallback(() => {
    setState({
      isValidating: false,
      isUploading: false,
      isValid: null,
      validationResult: null,
      uploadResult: null,
      error: null,
      selectedFile: null,
    });
  }, []);

  const validateFile = useCallback(async (file: File) => {
    if (!clientName || !weekName) {
      setState(prev => ({
        ...prev,
        error: 'Client name and week name are required for validation',
        isValid: false
      }));
      return;
    }

    setState(prev => ({
      ...prev,
      isValidating: true,
      error: null,
      isValid: null,
      selectedFile: file
    }));

    try {
      const request: FileUploadRequest = {
        file,
        fileType,
        clientName,
        weekName
      };

      const result = await uploadService.validateFile(request);

      setState(prev => ({
        ...prev,
        isValidating: false,
        isValid: result.valid,
        validationResult: result,
        error: result.valid ? null : result.errors.join(', ')
      }));

      // Call callback if provided
      if (onValidationResult) {
        onValidationResult(result);
      }

      return result;
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Validation failed';
      setState(prev => ({
        ...prev,
        isValidating: false,
        isValid: false,
        error: errorMessage
      }));
      throw error;
    }
  }, [fileType, clientName, weekName, onValidationResult, uploadService]);

  const uploadFile = useCallback(async (file?: File) => {
    const fileToUpload = file || state.selectedFile;

    if (!fileToUpload) {
      setState(prev => ({ ...prev, error: 'No file selected' }));
      return;
    }

    if (!clientName || !weekName) {
      setState(prev => ({ ...prev, error: 'Client name and week name are required' }));
      return;
    }

    setState(prev => ({
      ...prev,
      isUploading: true,
      error: null
    }));

    try {
      const request: FileUploadRequest = {
        file: fileToUpload,
        fileType,
        clientName,
        weekName
      };

      const result = await uploadService.uploadFile(request);

      setState(prev => ({
        ...prev,
        isUploading: false,
        uploadResult: result,
        error: result.success ? null : result.error || 'Upload failed'
      }));

      // Call success callback if upload was successful
      if (result.success && result.file_path && onUploadSuccess) {
        onUploadSuccess(result.file_path);
      }

      return result;
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Upload failed';
      setState(prev => ({
        ...prev,
        isUploading: false,
        error: errorMessage
      }));
      throw error;
    }
  }, [state.selectedFile, fileType, clientName, weekName, onUploadSuccess, uploadService]);

  const uploadWithValidation = useCallback(async (file: File) => {
    if (!clientName || !weekName) {
      setState(prev => ({ ...prev, error: 'Client name and week name are required' }));
      return;
    }

    setState(prev => ({
      ...prev,
      isValidating: true,
      isUploading: false,
      error: null,
      selectedFile: file
    }));

    try {
      const request: FileUploadRequest = {
        file,
        fileType,
        clientName,
        weekName
      };

      const result = await uploadService.uploadWithValidation(
        request,
        (validationResult) => {
          setState(prev => ({
            ...prev,
            isValidating: false,
            isValid: validationResult.valid,
            validationResult,
            isUploading: validationResult.valid // Start uploading if valid
          }));

          if (onValidationResult) {
            onValidationResult(validationResult);
          }
        }
      );

      setState(prev => ({
        ...prev,
        isUploading: false,
        uploadResult: result,
        error: result.success ? null : result.error || 'Upload failed'
      }));

      // Call success callback if upload was successful
      if (result.success && result.file_path && onUploadSuccess) {
        onUploadSuccess(result.file_path);
      }

      return result;
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Upload failed';
      setState(prev => ({
        ...prev,
        isValidating: false,
        isUploading: false,
        error: errorMessage
      }));
      throw error;
    }
  }, [fileType, clientName, weekName, onUploadSuccess, onValidationResult, uploadService]);

  const getExpectedFilename = useCallback(() => {
    if (!clientName || !weekName) return null;
    return uploadService.generateExpectedFilename(fileType, clientName, weekName);
  }, [fileType, clientName, weekName, uploadService]);

  const isFileSupported = useCallback((filename: string) => {
    return uploadService.isSupportedFile(filename);
  }, [uploadService]);

  const validateFileSize = useCallback((file: File, maxSizeMB?: number) => {
    return uploadService.validateFileSize(file, maxSizeMB);
  }, [uploadService]);

  const formatFileSize = useCallback((bytes: number) => {
    return uploadService.formatFileSize(bytes);
  }, [uploadService]);

  return {
    // State
    ...state,

    // Actions
    validateFile,
    uploadFile,
    uploadWithValidation,
    resetState,

    // Utilities
    getExpectedFilename,
    isFileSupported,
    validateFileSize,
    formatFileSize,

    // Computed values
    isProcessing: state.isValidating || state.isUploading,
    canUpload: state.isValid && !state.isValidating && !state.isUploading,
    hasValidationResult: state.validationResult !== null,
    hasUploadResult: state.uploadResult !== null,
  };
};
