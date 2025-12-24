/**
 * Cross-validation Service for CAM Application
 * Handles cross-validation between multiple uploaded files
 */

interface CrossValidationResult {
  valid: boolean;
  errors: string[];
  warnings: string[];
  validations_performed: string[];
}

interface CrossValidationResponse {
  success: boolean;
  error?: string;
  cross_validation?: CrossValidationResult;
}

class CrossValidationService {
  private baseUrl: string;

  constructor() {
    // Simple approach: directly access import.meta.env with fallback
    // Vite will handle this properly in build environments
    this.baseUrl = import.meta.env?.VITE_API_BASE_URL || 'http://localhost:5000';
  }

  /**
   * Cross-validate multiple files
   */
  async crossValidateFiles(
    files: { [key: string]: File },
    filePaths: { [key: string]: string },
    clientName: string,
    weekName: string
  ): Promise<CrossValidationResult> {
    const formData = new FormData();

    // Add files if provided
    Object.entries(files).forEach(([fileType, file]) => {
      if (file) {
        formData.append(fileType, file);
      }
    });

    // Add file paths if provided
    Object.entries(filePaths).forEach(([fileType, path]) => {
      if (path) {
        formData.append(`${fileType}_path`, path);
      }
    });

    formData.append('client_name', clientName);
    formData.append('week_name', weekName);

    try {
      const response = await fetch(`${this.baseUrl}/api/upload/cross-validate`, {
        method: 'POST',
        body: formData,
      });

      const data: CrossValidationResponse = await response.json();

      if (!response.ok) {
        throw new Error(data.error || 'Cross-validation failed');
      }

      if (!data.success) {
        throw new Error(data.error || 'Unknown cross-validation error');
      }

      return data.cross_validation || {
        valid: false,
        errors: ['No cross-validation result received'],
        warnings: [],
        validations_performed: []
      };
    } catch (error) {
      console.error('Cross-validation error:', error);
      return {
        valid: false,
        errors: [error instanceof Error ? error.message : 'Cross-validation failed'],
        warnings: [],
        validations_performed: []
      };
    }
  }

  /**
   * Check if cross-validation should be performed
   */
  shouldPerformCrossValidation(
    files: { [key: string]: File },
    filePaths: { [key: string]: string }
  ): boolean {
    // Check if we have at least 2 files to cross-validate
    const availableFilesCount = Object.keys(files).filter(key => files[key]).length +
                               Object.keys(filePaths).filter(key => filePaths[key] && filePaths[key].trim() !== '').length;

    return availableFilesCount >= 2;
  }

  /**
   * Get cross-validation requirements message
   */
  getCrossValidationInfo(): string {
    return `Cross-validation checks:
• CPM & Decile Reports: Segment and sub-segment matching
• Timestamp & CPM Reports: Date range compatibility`;
  }
}

export default CrossValidationService;
export type { CrossValidationResult, CrossValidationResponse };
