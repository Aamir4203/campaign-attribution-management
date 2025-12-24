/**
 * Custom hook for cross-validation functionality
 * Manages cross-validation between multiple uploaded files
 */

import { useState, useCallback, useEffect, useMemo } from 'react';
import CrossValidationService, { CrossValidationResult } from '../services/crossValidationService';

interface UseCrossValidationProps {
  clientName: string;
  weekName: string;
  onValidationComplete?: (result: CrossValidationResult) => void;
  autoValidate?: boolean; // New prop for auto-validation
}

interface CrossValidationState {
  isValidating: boolean;
  validationResult: CrossValidationResult | null;
  error: string | null;
}

export const useCrossValidation = ({
  clientName,
  weekName,
  onValidationComplete,
  autoValidate = false
}: UseCrossValidationProps) => {
  const [state, setState] = useState<CrossValidationState>({
    isValidating: false,
    validationResult: null,
    error: null
  });

  const crossValidationService = useMemo(() => new CrossValidationService(), []);

  const performCrossValidation = useCallback(async (
    files: { [key: string]: File },
    filePaths: { [key: string]: string }
  ) => {
    if (!clientName || !weekName) {
      setState(prev => ({
        ...prev,
        error: 'Client name and week name are required for cross-validation',
        validationResult: {
          valid: false,
          errors: ['Client name and week name are required'],
          warnings: [],
          validations_performed: []
        }
      }));
      return;
    }

    // Check if we should perform cross-validation
    if (!crossValidationService.shouldPerformCrossValidation(files, filePaths)) {
      setState(prev => ({
        ...prev,
        validationResult: {
          valid: true,
          errors: [],
          warnings: ['Need at least 2 files for cross-validation'],
          validations_performed: []
        }
      }));
      return;
    }

    setState(prev => ({
      ...prev,
      isValidating: true,
      error: null,
      validationResult: null
    }));

    try {
      const result = await crossValidationService.crossValidateFiles(
        files,
        filePaths,
        clientName,
        weekName
      );

      setState(prev => ({
        ...prev,
        isValidating: false,
        validationResult: result,
        error: result.valid ? null : result.errors.join(', ')
      }));

      // Call callback if provided
      if (onValidationComplete) {
        onValidationComplete(result);
      }

      return result;
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Cross-validation failed';
      const failedResult: CrossValidationResult = {
        valid: false,
        errors: [errorMessage],
        warnings: [],
        validations_performed: []
      };

      setState(prev => ({
        ...prev,
        isValidating: false,
        validationResult: failedResult,
        error: errorMessage
      }));

      throw error;
    }
  }, [clientName, weekName, onValidationComplete, crossValidationService]);

  const resetValidation = useCallback(() => {
    setState({
      isValidating: false,
      validationResult: null,
      error: null
    });
  }, []);

  // Auto-validation when files change
  const autoPerformCrossValidation = useCallback(async (
    files: { [key: string]: File },
    filePaths: { [key: string]: string }
  ) => {
    try {
      if (!autoValidate) return;

      // Check if we have at least 2 files for cross-validation
      const availableFilesCount = Object.keys(files).filter(key => files[key]).length +
                                 Object.keys(filePaths).filter(key => filePaths[key] && filePaths[key].trim() !== '').length;

      // If we have 2 or more files, auto-validate
      if (availableFilesCount >= 2) {
        await performCrossValidation(files, filePaths);
      } else {
        // If less than 2 files, reset validation
        resetValidation();
      }
    } catch (error) {
      console.error('Error in auto cross-validation:', error);
      // Reset on error to prevent stuck states
      resetValidation();
    }
  }, [autoValidate, performCrossValidation, resetValidation]);

  const shouldShowCrossValidation = useCallback((
    files: { [key: string]: File },
    filePaths: { [key: string]: string }
  ) => {
    return crossValidationService.shouldPerformCrossValidation(files, filePaths);
  }, [crossValidationService]);

  const getCrossValidationInfo = useCallback(() => {
    return crossValidationService.getCrossValidationInfo();
  }, [crossValidationService]);

  return {
    // State
    ...state,

    // Actions
    performCrossValidation,
    resetValidation,
    autoPerformCrossValidation, // New action for auto-validation

    // Utilities
    shouldShowCrossValidation,
    getCrossValidationInfo,

    // Computed values
    hasValidationResult: state.validationResult !== null,
    isValid: state.validationResult?.valid || false,
  };
};
