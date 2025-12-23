/**
 * Validation Indicator Component
 * Shows real-time validation status with visual feedback
 */

import React from 'react';
import { ValidationResult } from '../../services/uploadService';

interface ValidationIndicatorProps {
  isValidating: boolean;
  validationResult: ValidationResult | null;
  className?: string;
}

const ValidationIndicator: React.FC<ValidationIndicatorProps> = ({
  isValidating,
  validationResult,
  className = ''
}) => {
  // Show loading state
  if (isValidating) {
    return (
      <div className={`flex items-center space-x-2 ${className}`}>
        <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-blue-600"></div>
        <span className="text-sm text-blue-600">Validating...</span>
      </div>
    );
  }

  // No validation result yet
  if (!validationResult) {
    return null;
  }

  // Valid file - only show warnings if any, otherwise show nothing
  if (validationResult.valid) {
    // Only show warnings if they exist
    if (validationResult.warnings && validationResult.warnings.length > 0) {
      return (
        <div className={`flex items-start space-x-2 ${className}`}>
          <div className="flex-shrink-0">
            <svg className="h-5 w-5 text-yellow-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.964-.833-2.732 0L3.732 16c-.77.833.192 2.5 1.732 2.5z" />
            </svg>
          </div>
          <div className="flex-1">
            <p className="text-sm text-yellow-700 font-medium">Warnings:</p>
            <ul className="text-sm text-yellow-600 mt-1 space-y-1">
              {validationResult.warnings.map((warning, index) => (
                <li key={index}>⚠️ {warning}</li>
              ))}
            </ul>
          </div>
        </div>
      );
    }

    // If valid and no warnings, show nothing
    return null;
  }

  // Invalid file
  return (
    <div className={`flex items-start space-x-2 ${className}`}>
      <div className="flex-shrink-0">
        <svg className="h-5 w-5 text-red-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 14l2-2m0 0l2-2m-2 2l-2-2m2 2l2 2m7-2a9 9 0 11-18 0 9 9 0 0118 0z" />
        </svg>
      </div>
      <div className="flex-1">
        <p className="text-sm text-red-700 font-medium">✗ Validation failed</p>
        {validationResult.errors && validationResult.errors.length > 0 && (
          <div className="mt-2">
            <ul className="text-sm text-red-600 space-y-1">
              {validationResult.errors.map((error, index) => (
                <li key={index} className="flex items-start space-x-1">
                  <span className="text-red-500 mt-0.5">•</span>
                  <span>{error}</span>
                </li>
              ))}
            </ul>
          </div>
        )}
        {validationResult.file_info && Object.keys(validationResult.file_info).length > 0 && (
          <div className="text-xs text-gray-500 mt-2 space-y-1">
            {validationResult.file_info.rows && (
              <div>Detected rows: {validationResult.file_info.rows.toLocaleString()}</div>
            )}
            {validationResult.file_info.columns && (
              <div>Detected columns: {validationResult.file_info.columns}</div>
            )}
            {validationResult.file_info.size_mb && (
              <div>File size: {validationResult.file_info.size_mb} MB</div>
            )}
          </div>
        )}
      </div>
    </div>
  );
};

export default ValidationIndicator;
