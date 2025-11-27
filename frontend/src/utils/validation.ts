import * as yup from 'yup';

// Validation schema for the Add Request form
// Updated with all form fields and ZETA organization requirements

export const addRequestSchema = yup.object({
  // Client Information
  clientName: yup
    .string()
    .required('Client name is required')
    .min(2, 'Client name must be at least 2 characters')
    .max(100, 'Client name must not exceed 100 characters')
    .matches(/^[a-zA-Z0-9\s_-]+$/, 'Client name contains invalid characters'),

  addedBy: yup
    .string()
    .optional(), // Will be set automatically by login system

  // Request Configuration
  requestType: yup
    .string()
    .required('Request type is required')
    .oneOf(['1', '2', '3'], 'Please select a valid request type'),


  filePath: yup
    .string()
    .when('requestType', {
      is: '2',
      then: (schema) => schema.required('File path is required for Type 2 requests'),
      otherwise: (schema) => schema.optional()
    }),

  // Date Configuration
  startDate: yup
    .string()
    .required('Start date is required')
    .matches(/^\d{4}-\d{2}-\d{2}$/, 'Start date must be in YYYY-MM-DD format'),

  endDate: yup
    .string()
    .required('End date is required')
    .matches(/^\d{4}-\d{2}-\d{2}$/, 'End date must be in YYYY-MM-DD format')
    .test('end-after-start', 'End date must be after start date', function(value) {
      const { startDate } = this.parent;
      if (startDate && value) {
        return new Date(value) > new Date(startDate);
      }
      return true;
    }),

  residualStart: yup
    .string()
    .nullable()
    .test('valid-residual-date', 'Residual date must be in YYYY-MM-DD format', function(value) {
      if (!value) return true; // optional field
      return /^\d{4}-\d{2}-\d{2}$/.test(value);
    })
    .test('residual-after-end', 'Residual date must be equal to or greater than end date', function(value) {
      const { endDate } = this.parent;
      if (endDate && value) {
        const endDateObj = new Date(endDate);
        const residualDateObj = new Date(value);
        return residualDateObj >= endDateObj;
      }
      return true;
    }),

  week: yup
    .string()
    .optional()
    .min(1, 'Week must not be empty if provided'),

  // File Settings & Options
  fileType: yup
    .string()
    .oneOf(['Sent', 'Delivered'], 'Please select a valid file type'),

  addTimeStamp: yup.boolean(),
  addIpsLogs: yup.boolean(),
  addBounce: yup.boolean(),

  timeStampPath: yup
    .string()
    .when('addTimeStamp', {
      is: true,
      then: (schema) => schema.required('TimeStamp file path is required when Add TimeStamp is enabled'),
      otherwise: (schema) => schema.optional()
    })
    .max(500, 'TimeStamp file path cannot exceed 500 characters'),

  // Suppression Options (moved from file options)
  offerSuppression: yup.boolean(),
  clientSuppression: yup.boolean(),
  requestIdSuppression: yup.boolean(),

  clientSuppressionPath: yup
    .string()
    .when('clientSuppression', {
      is: true,
      then: (schema) => schema.required('Client suppression file path is required when Client Suppression is enabled'),
      otherwise: (schema) => schema.optional()
    })
    .max(500, 'Client suppression path cannot exceed 500 characters'),

  requestIdSuppressionList: yup
    .string()
    .when('requestIdSuppression', {
      is: true,
      then: (schema) => schema
        .required('Request IDs are required when Request ID Suppression is enabled')
        .matches(/^[\d,\s]+$/, 'Request IDs must be comma-separated numbers (e.g., 1234,5678)')
        .test('valid-ids', 'Request IDs must be valid numbers separated by commas', function(value) {
          if (!value) return true;
          const ids = value.split(',').map(id => id.trim()).filter(id => id);
          return ids.every(id => /^\d+$/.test(id) && parseInt(id) > 0);
        }),
      otherwise: (schema) => schema.optional()
    })
    .max(1000, 'Request ID list cannot exceed 1000 characters'),

  // Data Priority Settings
  priorityFile: yup
    .string()
    .optional()
    .max(500, 'Priority file path cannot exceed 500 characters'),

  priorityFilePer: yup
    .mixed()
    .when('priorityFile', {
      is: (value: string) => value && value.trim().length > 0,
      then: (schema) => schema
        .required('Priority percentage is required when priority file is specified')
        .test('valid-number', 'Priority percentage must be a number between 1 and 100', function(value) {
          if (value === null || value === undefined || value === '') return false;

          const numValue = Number(value);
          return !isNaN(numValue) && Number.isInteger(numValue) && numValue >= 1 && numValue <= 100;
        }),
      otherwise: (schema) => schema.optional()
    }),

  // Report Paths
  reportpath: yup
    .string()
    .optional()
    .max(500, 'Report path cannot exceed 500 characters'),

  qspath: yup
    .string()
    .optional()
    .max(500, 'QS path cannot exceed 500 characters'),

  // SQL Query
  input_query: yup
    .string()
    .optional()
    .max(5000, 'Query cannot exceed 5000 characters'),

  // Legacy fields for compatibility
  options: yup.string().optional(),
  Offer_option: yup.string().optional(),
  bounce_option: yup.string().optional(),
  cs_option: yup.string().optional(),
});

// TypeScript interface for form data
export interface AddRequestFormData {
  // Client Information
  clientName: string;
  addedBy?: string; // Optional - will be set by login system

  // Request Configuration
  requestType: string;
  filePath?: string;

  // Date Configuration
  startDate: string;
  endDate: string;
  residualStart?: string;
  week?: string;

  // File Settings & Options
  fileType?: string;
  addTimeStamp?: boolean;
  addIpsLogs?: boolean;
  addBounce?: boolean;
  timeStampPath?: string;

  // Suppression Options
  offerSuppression?: boolean;
  clientSuppression?: boolean;
  requestIdSuppression?: boolean;
  clientSuppressionPath?: string;
  requestIdSuppressionList?: string;

  // Data Priority Settings
  priorityFile?: string;
  priorityFilePer?: number | string;

  // Report Paths
  reportpath?: string;
  qspath?: string;

  // SQL Query
  input_query?: string;

  // Legacy fields for compatibility
  options?: string;
  Offer_option?: string;
  bounce_option?: string;
  cs_option?: string;
}
