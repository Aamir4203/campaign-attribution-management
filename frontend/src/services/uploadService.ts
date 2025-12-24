/**
 * Upload Service for CAM Application
 * Handles file upload operations and API communication
 */

interface FileUploadRequest {
  file: File;
  fileType: 'timestamp' | 'cpm' | 'decile';
  clientName: string;
  weekName: string;
}

interface ValidationResult {
  valid: boolean;
  errors: string[];
  warnings: string[];
  file_info: any;
  expected_filename?: string;
  file_exists?: boolean;
}

interface UploadResponse {
  success: boolean;
  error?: string;
  file_path?: string;
  filename?: string;
  file_info?: any;
  validation?: ValidationResult;
}

class UploadService {
  private baseUrl: string;

  constructor() {
    this.baseUrl = import.meta.env.VITE_API_BASE_URL || 'http://localhost:5000';
  }

  /**
   * Validate file without saving
   */
  async validateFile(request: FileUploadRequest): Promise<ValidationResult> {
    const formData = new FormData();
    formData.append('file', request.file);
    formData.append('file_type', request.fileType);
    formData.append('client_name', request.clientName);
    formData.append('week_name', request.weekName);

    try {
      const response = await fetch(`${this.baseUrl}/api/upload/validate`, {
        method: 'POST',
        body: formData,
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.error || 'Validation failed');
      }

      if (!data.success) {
        throw new Error(data.error || 'Unknown validation error');
      }

      return data.validation;
    } catch (error) {
      console.error('File validation error:', error);
      return {
        valid: false,
        errors: [error instanceof Error ? error.message : 'Validation failed'],
        warnings: [],
        file_info: {}
      };
    }
  }

  /**
   * Upload and save file
   */
  async uploadFile(request: FileUploadRequest): Promise<UploadResponse> {
    const formData = new FormData();
    formData.append('file', request.file);
    formData.append('file_type', request.fileType);
    formData.append('client_name', request.clientName);
    formData.append('week_name', request.weekName);

    try {
      const response = await fetch(`${this.baseUrl}/api/upload/save`, {
        method: 'POST',
        body: formData,
      });

      const data = await response.json();

      if (!response.ok) {
        return {
          success: false,
          error: data.error || `HTTP ${response.status}`,
          validation: data.validation
        };
      }

      return data;
    } catch (error) {
      console.error('File upload error:', error);
      return {
        success: false,
        error: error instanceof Error ? error.message : 'Upload failed'
      };
    }
  }

  /**
   * Upload file with real-time validation
   */
  async uploadWithValidation(
    request: FileUploadRequest,
    onValidationComplete?: (result: ValidationResult) => void
  ): Promise<UploadResponse> {
    try {
      // First validate
      const validationResult = await this.validateFile(request);

      // Call validation callback if provided
      if (onValidationComplete) {
        onValidationComplete(validationResult);
      }

      // If validation fails, return early
      if (!validationResult.valid) {
        return {
          success: false,
          error: 'File validation failed',
          validation: validationResult
        };
      }

      // If validation passes, upload the file
      return await this.uploadFile(request);
    } catch (error) {
      console.error('Upload with validation error:', error);
      return {
        success: false,
        error: error instanceof Error ? error.message : 'Upload failed'
      };
    }
  }

  /**
   * Get expected filename for given parameters
   */
  generateExpectedFilename(fileType: string, clientName: string, weekName: string): string {
    const prefixMap = {
      timestamp: 'TimeStampReport',
      cpm: 'CPM_Report',
      decile: 'Decile_Report'
    };

    const prefix = prefixMap[fileType as keyof typeof prefixMap] || `${fileType}_Report`;
    const cleanClient = this.cleanFilename(clientName);
    const cleanWeek = this.cleanFilename(weekName);

    return `${prefix}_${cleanClient}_${cleanWeek}.csv`;
  }

  /**
   * Clean string for filename usage
   */
  private cleanFilename(name: string): string {
    return name
      .replace(/[^\w\-_.]/g, '_')
      .replace(/_+/g, '_')
      .replace(/^_+|_+$/g, '');
  }

  /**
   * Check if file extension is supported
   */
  isSupportedFile(filename: string): boolean {
    const supportedExtensions = ['csv', 'xlsx', 'xls'];
    const extension = filename.toLowerCase().split('.').pop();
    return supportedExtensions.includes(extension || '');
  }

  /**
   * Get file size in human readable format
   */
  formatFileSize(bytes: number): string {
    if (bytes === 0) return '0 Bytes';

    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));

    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
  }

  /**
   * Validate file size
   */
  validateFileSize(file: File, maxSizeMB: number = 50): boolean {
    const maxBytes = maxSizeMB * 1024 * 1024;
    return file.size <= maxBytes;
  }
}

export default UploadService;
export type { FileUploadRequest, ValidationResult, UploadResponse };
