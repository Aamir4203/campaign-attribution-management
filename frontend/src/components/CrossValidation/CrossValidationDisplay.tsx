/**
 * Cross Validation Component
 * Shows cross-validation results between multiple files
 */

import React from 'react';
import { CrossValidationResult } from '../../services/crossValidationService';

interface CrossValidationDisplayProps {
  isValidating: boolean;
  validationResult: CrossValidationResult | null;
  className?: string;
}

const CrossValidationDisplay: React.FC<CrossValidationDisplayProps> = ({
  isValidating,
  validationResult,
  className = ''
}) => {
  try {
    // Show loading state
    if (isValidating) {
      return (
        <div className={`flex items-center space-x-2 ${className}`}>
          <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-blue-600"></div>
          <span className="text-sm text-blue-600">Cross-validating files...</span>
        </div>
      );
    }

    // No validation result yet
    if (!validationResult) {
      return null;
    }

  // Valid cross-validation - only show warnings if any
  if (validationResult.valid) {
    return (
      <div className={`${className}`}>
        {/* Show validations performed */}
        {validationResult.validations_performed.length > 0 && (
          <div className="p-3 bg-green-100 border border-green-300 rounded-lg mb-2">
            <div className="flex items-start space-x-2">
              <svg className="h-5 w-5 text-green-500 flex-shrink-0 mt-0.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
              <div className="flex-1">
                <p className="text-sm text-green-700 font-medium">✓ Cross-validation passed</p>
                <div className="text-xs text-green-600 mt-1">
                  <div>Validations performed:</div>
                  <ul className="mt-1 space-y-1">
                    {validationResult.validations_performed.map((validation, index) => (
                      <li key={index}>• {validation}</li>
                    ))}
                  </ul>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Show warnings if any */}
        {validationResult.warnings && validationResult.warnings.length > 0 && (
          <div className="p-3 bg-yellow-100 border border-yellow-300 rounded-lg">
            <div className="flex items-start space-x-2">
              <svg className="h-5 w-5 text-yellow-500 flex-shrink-0 mt-0.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.964-.833-2.732 0L3.732 16c-.77.833.192 2.5 1.732 2.5z" />
              </svg>
              <div className="flex-1">
                <p className="text-sm text-yellow-700 font-medium">Cross-validation warnings:</p>
                <ul className="text-sm text-yellow-600 mt-1 space-y-1">
                  {validationResult.warnings.map((warning, index) => (
                    <li key={index}>⚠️ {warning}</li>
                  ))}
                </ul>
              </div>
            </div>
          </div>
        )}
      </div>
    );
  }

  // Failed cross-validation
  return (
    <div className={`${className}`}>
      <div className="p-3 bg-red-100 border border-red-300 rounded-lg">
        <div className="flex items-start space-x-2">
          <svg className="h-5 w-5 text-red-500 flex-shrink-0 mt-0.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 14l2-2m0 0l2-2m-2 2l-2-2m2 2l2 2m7-2a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
          <div className="flex-1">
            <p className="text-sm text-red-700 font-medium">✗ Cross-validation failed</p>
            {validationResult.errors && validationResult.errors.length > 0 && (
              <ul className="text-sm text-red-600 mt-2 space-y-1">
                {validationResult.errors.map((error, index) => (
                  <li key={index} className="flex items-start space-x-1">
                    <span className="text-red-500 mt-0.5">•</span>
                    <span>{error}</span>
                  </li>
                ))}
              </ul>
            )}

            {/* Show what validations were attempted */}
            {validationResult.validations_performed.length > 0 && (
              <div className="text-xs text-red-500 mt-2">
                <div>Validations attempted:</div>
                <ul className="mt-1 space-y-1">
                  {validationResult.validations_performed.map((validation, index) => (
                    <li key={index}>• {validation}</li>
                  ))}
                </ul>
              </div>
            )}

            {/* Show warnings if any */}
            {validationResult.warnings && validationResult.warnings.length > 0 && (
              <div className="text-xs text-orange-600 mt-2">
                <div>Warnings:</div>
                <ul className="mt-1 space-y-1">
                  {validationResult.warnings.map((warning, index) => (
                    <li key={index}>⚠️ {warning}</li>
                  ))}
                </ul>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
  } catch (error) {
    console.error('Error in CrossValidationDisplay:', error);
    return (
      <div className={`p-3 bg-red-100 border border-red-300 rounded-lg ${className}`}>
        <div className="text-sm text-red-700">
          Error displaying cross-validation results. Please try again.
        </div>
      </div>
    );
  }
};

export default CrossValidationDisplay;
