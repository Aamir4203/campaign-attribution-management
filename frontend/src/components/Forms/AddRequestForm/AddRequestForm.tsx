import React, { useState, useEffect, useCallback } from 'react';
import { useForm } from 'react-hook-form';
import { yupResolver } from '@hookform/resolvers/yup';
import { addRequestSchema, AddRequestFormData } from '../../../utils/validation';
import ClientService from '../../../services/clientService';
import api from '../../../services/api';
import { useAuth } from '../../Auth';
import FlushDeliveryDataModal from '../../Modal/FlushDeliveryDataModal';
import SuccessModal from '../../Modal/SuccessModal';
import ErrorModal from '../../Modal/ErrorModal';
import HybridFileInput from '../../HybridFileInput/HybridFileInput';
import { useCrossValidation } from '../../../hooks/useCrossValidation';

// Simple AlertModal component
const AlertModal: React.FC<{
  isOpen: boolean;
  onClose: () => void;
  title: string;
  message: string;
  type?: 'info' | 'success' | 'error' | 'warning';
}> = ({ isOpen, onClose, title, message, type = 'info' }) => {
  if (!isOpen) return null;

  const getTypeStyles = () => {
    switch (type) {
      case 'success': return { icon: '✅', titleColor: 'text-green-800', bgColor: 'bg-green-50', borderColor: 'border-green-200' };
      case 'error': return { icon: '❌', titleColor: 'text-red-800', bgColor: 'bg-red-50', borderColor: 'border-red-200' };
      case 'warning': return { icon: '⚠️', titleColor: 'text-yellow-800', bgColor: 'bg-yellow-50', borderColor: 'border-yellow-200' };
      default: return { icon: 'ℹ️', titleColor: 'text-blue-800', bgColor: 'bg-blue-50', borderColor: 'border-blue-200' };
    }
  };

  const styles = getTypeStyles();

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div className="bg-white rounded-lg shadow-xl p-6 max-w-md w-full mx-4 border-l-4 border-l-blue-500">
        <div className={`flex items-center space-x-3 mb-4 ${styles.bgColor} ${styles.borderColor} border rounded-lg p-3`}>
          <span className="text-2xl">{styles.icon}</span>
          <h3 className={`text-lg font-semibold ${styles.titleColor}`}>{title}</h3>
        </div>
        <p className="text-gray-700 mb-6 leading-relaxed">{message}</p>
        <div className="flex justify-end">
          <button
            onClick={onClose}
            className="px-6 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors font-medium"
          >
            OK
          </button>
        </div>
      </div>
    </div>
  );
};

interface AddRequestFormProps {
  onComplete?: () => void;
  editMode?: boolean;
  initialData?: any;
}

const AddRequestForm: React.FC<AddRequestFormProps> = ({ onComplete, editMode = false, initialData = null }) => {
  const { getUsername } = useAuth();
  const [clients, setClients] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [showAddClient, setShowAddClient] = useState(false);
  const [newClientName, setNewClientName] = useState('');
  const [filteredClientsInModal, setFilteredClientsInModal] = useState<any[]>([]);
  const [showConfirmAddClient, setShowConfirmAddClient] = useState(false);
  const [showAlertModal, setShowAlertModal] = useState(false);
  const [alertMessage, setAlertMessage] = useState('');
  const [addingClient, setAddingClient] = useState(false);
  const [showFilePath, setShowFilePath] = useState(false);
  const [showClientSuppressionPath, setShowClientSuppressionPath] = useState(false);
  const [showRequestIdSuppressionList, setShowRequestIdSuppressionList] = useState(false);
  const [showPriorityFields, setShowPriorityFields] = useState(false);
  const [showTimeStampPath, setShowTimeStampPath] = useState(false);
  const [backendConnected, setBackendConnected] = useState(false);
  const [showSuccessModal, setShowSuccessModal] = useState(false);
  const [lastSubmittedRequestId, setLastSubmittedRequestId] = useState<string | number | null>(null);

  // Flush delivery data modal states
  const [showFlushModal, setShowFlushModal] = useState(false);
  const [flushLoading, setFlushLoading] = useState(false);
  const [weekTriggerTimeout, setWeekTriggerTimeout] = useState<NodeJS.Timeout | null>(null);
  const [weekTriggerPending, setWeekTriggerPending] = useState(false);

  // Success and Error modal states
  const [showFlushSuccessModal, setShowFlushSuccessModal] = useState(false);
  const [flushSuccessMessage, setFlushSuccessMessage] = useState('');
  const [showFlushErrorModal, setShowFlushErrorModal] = useState(false);
  const [flushErrorMessage, setFlushErrorMessage] = useState('');

  // Collapsible sections state
  const [expandedSections, setExpandedSections] = useState<Set<number>>(new Set([1])); // Section 1 open by default

  const toggleSection = (sectionNumber: number) => {
    const newExpanded = new Set(expandedSections);
    if (newExpanded.has(sectionNumber)) {
      newExpanded.delete(sectionNumber);
    } else {
      newExpanded.add(sectionNumber);
    }
    setExpandedSections(newExpanded);
  };

  const toggleAllSections = () => {
    const maxSections = editMode ? 8 : 7;
    const allExpanded = expandedSections.size === maxSections;
    if (allExpanded) {
      setExpandedSections(new Set()); // Collapse all
    } else {
      const allSectionNumbers = Array.from({ length: maxSections }, (_, i) => i + 1);
      setExpandedSections(new Set(allSectionNumbers)); // Expand all
    }
  };

  const form = useForm<AddRequestFormData>({
    resolver: yupResolver(addRequestSchema),
    mode: 'onChange',
    defaultValues: {
      clientName: '',
      addedBy: getUsername() || 'Unknown',
      requestType: '1',
      filePath: '',
      startDate: '',
      endDate: '',
      residualStart: '',
      week: '',
      reportpath: '',
      qspath: '',
      options: 'N',
      Offer_option: '',
      bounce_option: '',
      cs_option: '',
      input_query: '',
      addTimeStamp: false,
      addIpsLogs: false,
      offerSuppression: false,
      addBounce: false,
      clientSuppression: false,
      requestIdSuppression: false,
      clientSuppressionPath: '',
      requestIdSuppressionList: '',
      timeStampPath: '',
      fileType: 'Delivered',
      priorityFile: '',
      priorityFilePer: undefined
    },
  });


  const { register, handleSubmit, formState: { errors }, watch, setValue, setError, clearErrors } = form;
  const requestType = watch('requestType');

  // ========================================================================
  // Cross-validation hook - RE-ENABLED with new state management
  // ========================================================================
  const {
    isValidating: isCrossValidating,
    validationResult: crossValidationResult,
    error: crossValidationError,
    performCrossValidation,
    resetValidation: resetCrossValidation,
    shouldShowCrossValidation,
    hasValidationResult: hasCrossValidationResult
  } = useCrossValidation({
    clientName: watch('clientName') || '',
    weekName: watch('week') || '',
    autoValidate: false, // Manual validation only
    onValidationComplete: (result) => {
      console.log('🔍 Cross-validation completed:', result);

      // Update cross-validation state
      setCrossValidationState({
        performed: true,
        passed: result.valid,
        errors: result.errors || [],
        validationsPerformed: result.validations_performed || []
      });

      if (!result.valid) {
        console.warn('❌ Cross-validation failed:', result.errors);
      } else {
        console.log('✅ Cross-validation passed');
      }
    }
  });
  // ========================================================================
  // END: Cross-validation hook
  // ========================================================================

  // ========================================================================
  // PHASE 3: Enhanced File Validation State Management
  // ========================================================================

  /**
   * Comprehensive file validation state for all 4 file types
   * Tracks: upload status, validation status, enabled/disabled state, file paths
   */
  interface FileValidationState {
    uploaded: boolean;          // File was selected and uploaded
    saved: boolean;             // File saved to server
    valid: boolean | null;      // Individual validation passed (null = not validated yet)
    filePath: string;           // Server file path
    enabled: boolean;           // User enabled this file (checkbox/request type)
    validationError: string | null;
    validationWarnings: string[];
  }

  const [fileStates, setFileStates] = useState<{
    cpm: FileValidationState;
    decile: FileValidationState;
    timestamp: FileValidationState;
    unique_decile: FileValidationState;
  }>({
    cpm: {
      uploaded: false,
      saved: false,
      valid: null,
      filePath: '',
      enabled: true,  // Always enabled (mandatory)
      validationError: null,
      validationWarnings: []
    },
    decile: {
      uploaded: false,
      saved: false,
      valid: null,
      filePath: '',
      enabled: true,  // Always enabled (mandatory)
      validationError: null,
      validationWarnings: []
    },
    timestamp: {
      uploaded: false,
      saved: false,
      valid: null,
      filePath: '',
      enabled: false, // Disabled by default (optional checkbox)
      validationError: null,
      validationWarnings: []
    },
    unique_decile: {
      uploaded: false,
      saved: false,
      valid: null,
      filePath: '',
      enabled: false, // Disabled by default (optional, Type-2 only)
      validationError: null,
      validationWarnings: []
    }
  });

  // Track cross-validation state separately
  const [crossValidationState, setCrossValidationState] = useState<{
    performed: boolean;
    passed: boolean | null;
    errors: string[];
    validationsPerformed: string[];
  }>({
    performed: false,
    passed: null,
    errors: [],
    validationsPerformed: []
  });

  // ========================================================================
  // END: Enhanced File Validation State Management
  // ========================================================================

  // ========================================================================
  // File Upload Event Handlers
  // ========================================================================

  /**
   * Trigger cross-validation if we have the required files
   * Mandatory: CPM + Decile
   * Optional: Timestamp (if enabled), Unique Decile (if enabled)
   */
  const triggerCrossValidationIfReady = useCallback(async (currentFileStates: typeof fileStates) => {
    // Check if we have the required files
    const hasCPM = currentFileStates.cpm.saved && currentFileStates.cpm.valid;
    const hasDecile = currentFileStates.decile.saved && currentFileStates.decile.valid;

    // Must have both mandatory files
    if (!hasCPM || !hasDecile) {
      console.log('⏸️ Not ready for cross-validation - missing mandatory files');
      return;
    }

    // Collect enabled file paths
    const filePaths: Record<string, string> = {};

    // Always include mandatory files
    if (hasCPM) filePaths.cpm = currentFileStates.cpm.filePath;
    if (hasDecile) filePaths.decile = currentFileStates.decile.filePath;

    // Include optional files if enabled and valid
    if (currentFileStates.timestamp.enabled && currentFileStates.timestamp.saved && currentFileStates.timestamp.valid) {
      filePaths.timestamp = currentFileStates.timestamp.filePath;
    }

    if (currentFileStates.unique_decile.enabled && currentFileStates.unique_decile.saved && currentFileStates.unique_decile.valid) {
      filePaths.unique_decile = currentFileStates.unique_decile.filePath;
    }

    console.log('🔄 Triggering cross-validation with files:', Object.keys(filePaths));

    try {
      await performCrossValidation({}, filePaths);
    } catch (error) {
      console.error('❌ Cross-validation error:', error);
    }
  }, [performCrossValidation]);

  /**
   * Handle file uploaded and validated successfully
   * Updates file state and triggers cross-validation if needed
   */
  const handleFileValidated = useCallback((
    fileType: 'cpm' | 'decile' | 'timestamp' | 'unique_decile',
    filePath: string,
    isValid: boolean,
    error: string | null = null,
    warnings: string[] = []
  ) => {
    console.log(`📁 File validated: ${fileType}`, { filePath, isValid, error });

    setFileStates(prev => {
      const newState = {
        ...prev,
        [fileType]: {
          ...prev[fileType],
          uploaded: true,
          saved: !!filePath,
          valid: isValid,
          filePath: filePath,
          validationError: error,
          validationWarnings: warnings
        }
      };

      // Update form value
      const formFieldMap: Record<string, string> = {
        cpm: 'reportpath',
        decile: 'qspath',
        timestamp: 'timeStampPath',
        unique_decile: 'filePath'
      };

      const formField = formFieldMap[fileType];
      if (formField) {
        setValue(formField as any, filePath);
      }

      // ⚠️ ONLY trigger cross-validation if individual file validation SUCCEEDED
      if (isValid && filePath) {
        setTimeout(() => {
          triggerCrossValidationIfReady(newState);
        }, 100);
      } else {
        console.log(`⚠️ File ${fileType} validation failed - skipping cross-validation`);
        // Clear cross-validation state since we have invalid files
        setCrossValidationState({
          performed: false,
          passed: null,
          errors: [],
          validationsPerformed: []
        });
      }

      return newState;
    });
  }, [setValue, triggerCrossValidationIfReady]);

  /**
   * Handle checkbox or request type changes that enable/disable optional files
   */
  const handleFileEnabledChange = useCallback((
    fileType: 'timestamp' | 'unique_decile',
    enabled: boolean
  ) => {
    setFileStates(prev => {
      // Check if the enabled state has actually changed
      if (prev[fileType].enabled === enabled) {
        // No change, return previous state without triggering updates
        return prev;
      }

      console.log(`⚙️ File enabled state changed: ${fileType} = ${enabled}`);

      const newState = {
        ...prev,
        [fileType]: {
          ...prev[fileType],
          enabled: enabled
        }
      };

      // If disabled, clear form field (but keep file state for potential re-enable)
      if (!enabled) {
        const formFieldMap: Record<string, string> = {
          timestamp: 'timeStampPath',
          unique_decile: 'filePath'
        };

        const formField = formFieldMap[fileType];
        if (formField) {
          setValue(formField as any, '');
        }

        // Clear cross-validation state (will re-validate without this file)
        setCrossValidationState({
          performed: false,
          passed: null,
          errors: [],
          validationsPerformed: []
        });
      }

      // Trigger cross-validation re-run with new enabled state
      setTimeout(() => {
        triggerCrossValidationIfReady(newState);
      }, 100);

      return newState;
    });
  }, [setValue, triggerCrossValidationIfReady]);

  /**
   * Clear file state when file is removed/re-uploaded
   */
  const handleFileClear = useCallback((
    fileType: 'cpm' | 'decile' | 'timestamp' | 'unique_decile'
  ) => {
    console.log(`🗑️ File cleared: ${fileType}`);

    setFileStates(prev => ({
      ...prev,
      [fileType]: {
        ...prev[fileType],
        uploaded: false,
        saved: false,
        valid: null,
        filePath: '',
        validationError: null,
        validationWarnings: []
      }
    }));

    // Clear cross-validation (needs re-validation)
    setCrossValidationState({
      performed: false,
      passed: null,
      errors: [],
      validationsPerformed: []
    });
  }, []);

  // ========================================================================
  // END: File Upload Event Handlers
  // ========================================================================

  // LEGACY: Track uploaded files state to only validate when files are actually uploaded
  // TODO: Remove this after full migration to fileStates
  const [uploadedFiles, setUploadedFiles] = useState({
    cpm: false,
    decile: false,
    timestamp: false
  });

  // Watch file paths for changes (but don't auto-validate on every change)
  const reportPath = watch('reportpath');
  const qsPath = watch('qspath');
  const timeStampPath = watch('timeStampPath');
  const addTimeStamp = watch('addTimeStamp');

  // ========================================================================
  // Watchers for Enabled State Changes
  // ========================================================================

  /**
   * Watch for timestamp checkbox changes
   * Update timestamp file enabled state
   */
  useEffect(() => {
    const enabled = !!addTimeStamp;
    handleFileEnabledChange('timestamp', enabled);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [addTimeStamp]);

  /**
   * Watch for request type changes
   * Update unique_decile file enabled state (enabled when Type-2)
   */
  useEffect(() => {
    const enabled = requestType === '2';
    handleFileEnabledChange('unique_decile', enabled);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [requestType]);

  // ========================================================================
  // END: Watchers for Enabled State Changes
  // ========================================================================

  // Function to handle file upload completion and trigger validation
  const handleFileUploaded = useCallback((fileType: 'cpm' | 'decile' | 'timestamp', filePath: string) => {
    setUploadedFiles(prev => {
      const newState = { ...prev, [fileType]: !!filePath };

      // Count uploaded files (respecting timestamp checkbox)
      const uploadCount = [
        newState.cpm,
        newState.decile,
        addTimeStamp ? newState.timestamp : false
      ].filter(Boolean).length;

      // Only trigger validation if we have 2+ files uploaded
      if (uploadCount >= 2) {
        setTimeout(async () => {
          try {
            resetCrossValidation();

            // Collect current file paths
            const filePaths = {
              cpm: reportPath || '',
              decile: qsPath || '',
              timestamp: addTimeStamp ? (timeStampPath || '') : ''
            };

            // Filter out empty paths
            const validPaths = Object.fromEntries(
              Object.entries(filePaths).filter(([_, path]) => path && path.trim() !== '')
            );

            if (Object.keys(validPaths).length >= 2) {
              await performCrossValidation({}, validPaths);
            }
          } catch (error) {
            console.error('Auto cross-validation error:', error);
          }
        }, 100); // Small delay to ensure state is updated
      } else {
        // Clear validation if insufficient files
        resetCrossValidation();
      }

      return newState;
    });
  }, [addTimeStamp, resetCrossValidation, performCrossValidation, reportPath, qsPath, timeStampPath]);

  // Reset file uploaded state when paths are cleared
  useEffect(() => {
    const newUploadedState = {
      cpm: !!reportPath,
      decile: !!qsPath,
      timestamp: !!(addTimeStamp && timeStampPath)
    };

    setUploadedFiles(prev => {
      const hasChanged = Object.keys(newUploadedState).some(
        key => prev[key as keyof typeof prev] !== newUploadedState[key as keyof typeof newUploadedState]
      );

      if (hasChanged) {
        // If files were removed, clear validation
        const uploadCount = Object.values(newUploadedState).filter(Boolean).length;
        if (uploadCount < 2) {
          resetCrossValidation();
        }
        return newUploadedState;
      }

      return prev;
    });
  }, [reportPath, qsPath, timeStampPath, addTimeStamp, resetCrossValidation]);

  // Other form watches
  const clientSuppression = watch('clientSuppression');
  const requestIdSuppression = watch('requestIdSuppression');
  const priorityFile = watch('priorityFile');
  const endDate = watch('endDate');
  const residualStart = watch('residualStart');
  const weekValue = watch('week');
  const clientName = watch('clientName');

  // W1/W2 Detection Logic with Debouncing
  useEffect(() => {
    // Clear any existing timeout and reset pending state
    if (weekTriggerTimeout) {
      clearTimeout(weekTriggerTimeout);
      setWeekTriggerPending(false);
    }

    if (weekValue && clientName) {
      // Improved regex to detect W1 or W2 more precisely
      // This will match w1, w2 but NOT w11, w12, w21, etc.
      // Handles separators like underscores, spaces, etc.
      const w1w2Regex = /(?:^|[^a-zA-Z0-9])w[12](?![0-9])/i;

      if (w1w2Regex.test(weekValue)) {
        console.log('🔍 W1/W2 pattern detected, waiting 3 seconds...', weekValue);
        setWeekTriggerPending(true);

        // Set a 3-second delay before showing modal
        const timeout = setTimeout(() => {
          // Double-check the pattern still matches after 3 seconds
          if (weekValue && w1w2Regex.test(weekValue) && clientName) {
            console.log('✅ Triggering flush modal after 3-second delay');
            setWeekTriggerPending(false);
            setShowFlushModal(true);
          } else {
            setWeekTriggerPending(false);
          }
        }, 3000);

        setWeekTriggerTimeout(timeout);
      } else {
        setWeekTriggerPending(false);
        console.log('📝 Week value changed but no W1/W2 pattern:', weekValue);
      }
    } else {
      setWeekTriggerPending(false);
    }

    // Cleanup function
    return () => {
      if (weekTriggerTimeout) {
        clearTimeout(weekTriggerTimeout);
        setWeekTriggerPending(false);
      }
    };
  }, [weekValue, clientName]);

  // Cleanup timeout on component unmount
  useEffect(() => {
    return () => {
      if (weekTriggerTimeout) {
        clearTimeout(weekTriggerTimeout);
        setWeekTriggerPending(false);
      }
    };
  }, []);


  // Load data on mount
  useEffect(() => {
    loadFormData();
  }, []);

  // Handle edit mode initialization
  useEffect(() => {
    if (editMode && initialData) {
      console.log('🔧 Edit mode: Pre-filling form with data:', initialData);

      // Section 1: Client Information
      if (initialData.client_name) {
        setValue('clientName', initialData.client_name);
        console.log('✅ Set clientName:', initialData.client_name);
      }
      if (initialData.added_by) {
        setValue('addedBy', initialData.added_by);
        console.log('✅ Set addedBy:', initialData.added_by);
      }
      if (initialData.request_type) {
        setValue('requestType', initialData.request_type.toString());
        console.log('✅ Set requestType:', initialData.request_type);
      }

      // Section 2: Date Configuration - trying multiple possible field names
      if (initialData.start_date) {
        setValue('startDate', initialData.start_date);
        console.log('✅ Set startDate:', initialData.start_date);
      }
      if (initialData.end_date) {
        setValue('endDate', initialData.end_date);
        console.log('✅ Set endDate:', initialData.end_date);
      }
      if (initialData.residual_start) {
        setValue('residualStart', initialData.residual_start);
        console.log('✅ Set residualStart:', initialData.residual_start);
      }
      if (initialData.week) {
        setValue('week', initialData.week);
        console.log('✅ Set week:', initialData.week);
      }

      // Section 3: File Settings and Report Paths
      if (initialData.file_path) {
        setValue('filePath', initialData.file_path);
        console.log('✅ Set filePath:', initialData.file_path);
      }
      if (initialData.file_type) {
        setValue('fileType', initialData.file_type);
        console.log('✅ Set fileType:', initialData.file_type);
      }
      if (initialData.report_path) {
        setValue('reportpath', initialData.report_path);
        console.log('✅ Set reportpath:', initialData.report_path);
      }
      if (initialData.decile_report_path) {
        setValue('qspath', initialData.decile_report_path);
        console.log('✅ Set qspath:', initialData.decile_report_path);
      }

      // Section 4: Options & Toggles
      if (initialData.timestamp_append !== undefined) {
        const timestampValue = initialData.timestamp_append === 'Y' || initialData.timestamp_append === true;
        setValue('addTimeStamp', timestampValue);
        console.log('✅ Set addTimeStamp:', timestampValue);
      }
      if (initialData.ip_append !== undefined) {
        const ipValue = initialData.ip_append === 'Y' || initialData.ip_append === true;
        setValue('addIpsLogs', ipValue);
        console.log('✅ Set addIpsLogs:', ipValue);
      }
      if (initialData.offerid_unsub_supp !== undefined) {
        const offerValue = initialData.offerid_unsub_supp === 'Y' || initialData.offerid_unsub_supp === true;
        setValue('offerSuppression', offerValue);
        console.log('✅ Set offerSuppression:', offerValue);
      }
      if (initialData.include_bounce_as_delivered !== undefined) {
        const bounceValue = initialData.include_bounce_as_delivered === 'Y' || initialData.include_bounce_as_delivered === true;
        setValue('addBounce', bounceValue);
        console.log('✅ Set addBounce:', bounceValue);
      }

      // Section 5: Suppression Settings
      if (initialData.supp_path) {
        setValue('clientSuppression', true);
        setValue('clientSuppressionPath', initialData.supp_path);
        console.log('✅ Set clientSuppression and path:', initialData.supp_path);
      }
      if (initialData.request_id_supp) {
        setValue('requestIdSuppression', true);
        setValue('requestIdSuppressionList', initialData.request_id_supp);
        console.log('✅ Set requestIdSuppression and list:', initialData.request_id_supp);
      }
      if (initialData.timestamp_report_path) {
        setValue('timeStampPath', initialData.timestamp_report_path);
        console.log('✅ Set timeStampPath:', initialData.timestamp_report_path);
      }

      // Section 6: Data Priority
      if (initialData.priority_file) {
        setValue('priorityFile', initialData.priority_file);
        console.log('✅ Set priorityFile:', initialData.priority_file);
      }
      if (initialData.priority_file_per) {
        setValue('priorityFilePer', initialData.priority_file_per);
        console.log('✅ Set priorityFilePer:', initialData.priority_file_per);
      }

      // Section 7: SQL Query
      if (initialData.query) {
        setValue('input_query', initialData.query);
        console.log('✅ Set input_query:', initialData.query);
      }

      // Legacy fields
      if (initialData.options) setValue('options', initialData.options);
      if (initialData.offer_option) setValue('Offer_option', initialData.offer_option);
      if (initialData.bounce_option) setValue('bounce_option', initialData.bounce_option);
      if (initialData.cs_option) setValue('cs_option', initialData.cs_option);

      // Expand sections 1 and 8 (rerun module) in edit mode, plus section 2 for dates
      setExpandedSections(new Set([1, 2, 8]));

      console.log('✅ Edit mode: Form pre-filled successfully');
      console.log('📋 All available data keys:', Object.keys(initialData));

      // Show notification that this is edit mode
      setShowSuccessModal(false);
    }
  }, [editMode, initialData, setValue, getUsername]);

  // Show file path input when Type 2 is selected
  useEffect(() => {
    setShowFilePath(requestType === '2');
  }, [requestType]);

  // Show client suppression path when Client Suppression is checked
  useEffect(() => {
    setShowClientSuppressionPath(clientSuppression === true);
  }, [clientSuppression]);

  // Show request ID suppression list when Request ID Suppression is checked
  useEffect(() => {
    setShowRequestIdSuppressionList(requestIdSuppression === true);
  }, [requestIdSuppression]);

  // Show priority percentage when priority file is provided
  useEffect(() => {
    setShowPriorityFields(priorityFile ? priorityFile.trim().length > 0 : false);
  }, [priorityFile]);

  // Show timestamp path when Add TimeStamp is checked
  useEffect(() => {
    setShowTimeStampPath(addTimeStamp === true);
  }, [addTimeStamp]);

  // Real-time residual date validation
  useEffect(() => {
    if (endDate && residualStart) {
      const endDateObj = new Date(endDate);
      const residualDateObj = new Date(residualStart);

      if (residualDateObj < endDateObj) {
        setError('residualStart', {
          type: 'manual',
          message: 'Residual date must be equal to or greater than end date'
        });
      } else {
        clearErrors('residualStart');
      }
    } else if (!residualStart) {
      // Clear error when field is empty
      clearErrors('residualStart');
    }
  }, [endDate, residualStart, setError, clearErrors]);

  const loadFormData = async () => {
    try {
      setLoading(true);

      // Test backend connection first
      console.log('🔗 Testing backend connection at http://localhost:5000...');

      // Load real data from backend
      const clientsData = await ClientService.getClients();
      setClients(clientsData);
      setBackendConnected(true);

      console.log('✅ Backend connection successful');
      console.log('📋 Loaded clients:', clientsData?.length || 0);

    } catch (error) {
      setBackendConnected(false);
      console.error('❌ Backend connection failed:', error);
      console.error('🔍 Error details:', (error as any)?.message || 'Unknown error');
      console.error('🚨 Make sure backend is running at http://localhost:5000');
      setClients([]); // Empty array if backend fails
    } finally {
      setLoading(false);
    }
  };

  // Handle typing in Add Client modal - show autocomplete
  const handleNewClientNameChange = (value: string) => {
    setNewClientName(value);

    if (value.trim()) {
      const matches = clients.filter(client =>
        client.client_name.toLowerCase().includes(value.toLowerCase())
      );
      setFilteredClientsInModal(matches);
    } else {
      setFilteredClientsInModal([]);
    }
  };

  // Validate and show confirmation when clicking Add Client button
  const handleAddClient = async () => {
    const clientName = newClientName.trim();

    if (!clientName) {
      setAlertMessage('Please enter a client name');
      setShowAlertModal(true);
      return;
    }

    // Check if client already exists
    const existingClient = clients.find(
      client => client.client_name.toLowerCase() === clientName.toLowerCase()
    );

    if (existingClient) {
      setAlertMessage(`Client "${clientName}" already exists!`);
      setShowAlertModal(true);
      return;
    }

    // Show confirmation for new client
    setShowAddClient(false);
    setShowConfirmAddClient(true);
  };

  // Confirm and execute add client operation
  const confirmAddNewClient = async () => {
    try {
      setAddingClient(true);
      setShowConfirmAddClient(false);

      const response = await ClientService.addClient(newClientName.trim());

      if (response.success) {
        // Reload client list
        await loadFormData();
        // Set the new client as selected
        setValue('clientName', newClientName.trim());
        setNewClientName('');
        setFilteredClientsInModal([]);

        setAlertMessage(`Client "${newClientName}" added successfully!`);
        setShowAlertModal(true);
      } else {
        setAlertMessage(response.message || 'Failed to add client');
        setShowAlertModal(true);
      }
    } catch (error: any) {
      console.error('Error adding client:', error);
      setAlertMessage(error.message || 'Failed to add client');
      setShowAlertModal(true);
    } finally {
      setAddingClient(false);
    }
  };

  const handleFlushDeliveryData = async () => {
    try {
      setFlushLoading(true);

      const response = await ClientService.flushDeliveryData(clientName);

      if (response.success) {
        console.log('✅ Flush successful:', response);
        // Show custom success modal
        const successMessage = `Successfully flushed ${response.details.records_flushed.toLocaleString()} records from ${response.details.table_name}`;
        setFlushSuccessMessage(successMessage);
        setShowFlushSuccessModal(true);
      } else {
        console.error('❌ Flush failed:', response.error);
        // Show custom error modal
        setFlushErrorMessage(response.error || 'Unknown error occurred');
        setShowFlushErrorModal(true);
      }
    } catch (error: any) {
      console.error('❌ Flush error:', error);
      const errorMessage = error?.response?.data?.error || error?.message || 'Unknown error occurred';
      // Show custom error modal
      setFlushErrorMessage(`Failed to flush delivery data:\n${errorMessage}`);
      setShowFlushErrorModal(true);
    } finally {
      setFlushLoading(false);
      setShowFlushModal(false);
      // Clear timeout when modal is closed
      if (weekTriggerTimeout) {
        clearTimeout(weekTriggerTimeout);
        setWeekTriggerTimeout(null);
      }
      setWeekTriggerPending(false);
    }
  };

  const handleFlushModalClose = () => {
    setShowFlushModal(false);
    // Clear timeout when modal is manually closed
    if (weekTriggerTimeout) {
      clearTimeout(weekTriggerTimeout);
      setWeekTriggerTimeout(null);
    }
    setWeekTriggerPending(false);
  };

  const handleCrossValidation = async () => {
    try {
      resetCrossValidation();

      // Collect file paths from form (respect timestamp checkbox)
      const filePaths = {
        cpm: watch('reportpath') || '',
        decile: watch('qspath') || '',
        timestamp: addTimeStamp ? (watch('timeStampPath') || '') : '' // Only include if checkbox is checked
      };

      // Filter out empty paths
      const validPaths = Object.fromEntries(
        Object.entries(filePaths).filter(([_, path]) => path && path.trim() !== '')
      );

      if (Object.keys(validPaths).length < 2) {
        alert('Please upload at least 2 files to perform cross-validation');
        return;
      }

      await performCrossValidation({}, validPaths);

    } catch (error) {
      console.error('Cross-validation error:', error);
    }
  };

  const shouldRunCrossValidation = () => {
    // Count actually uploaded files (not just paths)
    const uploadCount = [
      uploadedFiles.cpm,
      uploadedFiles.decile,
      addTimeStamp ? uploadedFiles.timestamp : false
    ].filter(Boolean).length;

    return uploadCount >= 2;
  };

  const onSubmit = async (data: AddRequestFormData) => {
    try {
      setSubmitting(true);

      // ========================================================================
      // VALIDATION CHECK: Ensure cross-validation passed before submission
      // ========================================================================

      console.log('📋 Form submission - File states:', {
        cpm: { saved: fileStates.cpm.saved, valid: fileStates.cpm.valid, path: fileStates.cpm.filePath },
        decile: { saved: fileStates.decile.saved, valid: fileStates.decile.valid, path: fileStates.decile.filePath },
        timestamp: { enabled: fileStates.timestamp.enabled, saved: fileStates.timestamp.saved, valid: fileStates.timestamp.valid },
        unique_decile: { enabled: fileStates.unique_decile.enabled, saved: fileStates.unique_decile.saved, valid: fileStates.unique_decile.valid }
      });

      console.log('🔍 Cross-validation state:', crossValidationState);

      // Check if mandatory files are uploaded and valid
      if (!fileStates.cpm.saved || !fileStates.cpm.valid) {
        alert('❌ CPM report must be uploaded and valid before submission.');
        setSubmitting(false);
        return;
      }

      if (!fileStates.decile.saved || !fileStates.decile.valid) {
        alert('❌ Decile report must be uploaded and valid before submission.');
        setSubmitting(false);
        return;
      }

      // Check if optional files are enabled but not uploaded/valid
      if (fileStates.timestamp.enabled && (!fileStates.timestamp.saved || !fileStates.timestamp.valid)) {
        alert('❌ Timestamp report is enabled but not uploaded or invalid. Please upload a valid file or uncheck the option.');
        setSubmitting(false);
        return;
      }

      if (fileStates.unique_decile.enabled && (!fileStates.unique_decile.saved || !fileStates.unique_decile.valid)) {
        alert('❌ Unique Decile report is required for Type-2 requests. Please upload a valid file or change request type.');
        setSubmitting(false);
        return;
      }

      // Check if cross-validation was performed and passed
      if (crossValidationState.performed && crossValidationState.passed === false) {
        const errorList = crossValidationState.errors.join('\n• ');
        if (confirm(`❌ Cannot submit request due to validation issues:\n\n• ${errorList}\n\nPlease resolve these issues and try again.\n\nClick OK to see the validation section.`)) {
          // Scroll to cross-validation section
          const crossValSection = document.querySelector('[class*="Cross-Validation"]');
          crossValSection?.scrollIntoView({ behavior: 'smooth', block: 'center' });
        }
        setSubmitting(false);
        return;
      }

      // If cross-validation hasn't been performed yet but we have mandatory files, trigger it now
      if (!crossValidationState.performed && fileStates.cpm.saved && fileStates.decile.saved) {
        alert('⚠️ Cross-validation has not been performed yet. Please wait for validation to complete.');
        await triggerCrossValidationIfReady(fileStates);
        setSubmitting(false);
        return;
      }

      // ========================================================================
      // END: VALIDATION CHECK
      // ========================================================================

      const requestData = {
        client_name: data.clientName,
        added_by: data.addedBy,
        request_type: parseInt(data.requestType || '1'),
        file_path: data.filePath || '',
        start_date: data.startDate,
        end_date: data.endDate,
        residual_start: data.residualStart,
        week: data.week,
        report_path: data.reportpath,
        decile_report_path: data.qspath,
        options: data.options || 'N',
        offer_option: data.Offer_option || '',
        bounce_option: data.bounce_option || '',
        cs_option: data.cs_option || '',
        query: data.input_query,
        timestamp_append: data.addTimeStamp ? 'Y' : 'N',
        ip_append: data.addIpsLogs ? 'Y' : 'N',
        offerid_unsub_supp: data.offerSuppression ? 'Y' : 'N',
        include_bounce_as_delivered: data.addBounce ? 'Y' : 'N',
        supp_path: data.clientSuppression ? data.clientSuppressionPath : '',
        request_id_supp: data.requestIdSuppression ? data.requestIdSuppressionList : '',
        timestamp_report_path: data.addTimeStamp ? data.timeStampPath : '',
        file_type: data.fileType || 'Delivered',
        priority_file: data.priorityFile || '',
        priority_file_per: data.priorityFilePer || null
      };

      let response;
      let successMessage;

      if (editMode && initialData?.request_id) {
        // Edit mode - Update existing request and rerun
        // FIX: Get value from SELECT dropdown, not radio input
        const rerunModuleElement = document.querySelector('select[name="rerunModule"]') as HTMLSelectElement;
        const rerunModule = rerunModuleElement?.value || 'TRT';

        console.log('🔄 Edit mode: Updating request', initialData.request_id);
        console.log('📦 Rerun module selected:', rerunModule);
        console.log('📋 Full request data being sent:', { ...requestData, rerun_module: rerunModule });

        // Call update endpoint (you may need to create this endpoint)
        response = await api.post(`/update_request/${initialData.request_id}`, {
          ...requestData,
          rerun_module: rerunModule,
          original_request_id: initialData.request_id
        });

        successMessage = `Request ${initialData.request_id} updated and queued for rerun from ${rerunModule} module`;
      } else {
        // New request mode
        console.log('➕ New request mode: Creating new request');
        response = await api.post('/add_request', requestData);
        successMessage = `New request created successfully`;
      }

      if (response.data.success) {
        setLastSubmittedRequestId(response.data.request_id || initialData?.request_id || 'Unknown');
        setShowSuccessModal(true);
        console.log('✅ Request submission successful:', successMessage);
      } else {
        throw new Error(response.data.error || 'Submission failed');
      }
    } catch (error: any) {
      console.error('❌ Error submitting request:', error);
      alert(`Error: ${error.message || 'Failed to submit request'}`);
    } finally {
      setSubmitting(false);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-center">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600 mx-auto mb-2"></div>
          <p className="text-gray-600">Loading form data...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="w-full bg-white min-h-screen py-3">
      {/* Header with Edit Mode Indicator */}
      {editMode && (
        <div className="mb-3 flex justify-end">
          <div className="bg-yellow-50 border border-yellow-200 rounded-lg px-3 py-1">
            <div className="text-right text-sm text-yellow-800 font-medium">
              Edit Mode :: {initialData?.request_id} :: {initialData?.client_name}
            </div>
          </div>
        </div>
      )}

      {/* Toggle All Sections Icon */}
      <div className="mb-4 flex justify-end">
        <button
          type="button"
          onClick={toggleAllSections}
          className="p-1 text-gray-600 hover:text-blue-600 hover:bg-blue-50 rounded-lg transition-colors"
          title={expandedSections.size === (editMode ? 8 : 7) ? "Collapse All Sections" : "Expand All Sections"}
        >
          {expandedSections.size === (editMode ? 8 : 7) ? (
            // Collapse icon - horizontal line
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M20 12H4" />
            </svg>
          ) : (
            // Expand icon - horizontal line with vertical line (plus sign)
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 6v6m0 0v6m0-6h6m-6 0H6" />
            </svg>
          )}
        </button>
      </div>

      <form onSubmit={handleSubmit(onSubmit)} className="space-y-3">

        {/* Section 1: Client Information */}
        <div className="bg-white border border-gray-200 rounded shadow-sm">
          <div
            onClick={() => toggleSection(1)}
            className="flex items-center justify-between px-3 py-2 hover:bg-gray-50 transition-colors cursor-pointer"
          >
            <div className="flex items-center space-x-2">
              <span className="text-blue-600 font-semibold text-sm">1.</span>
              <h3 className="text-sm font-medium text-gray-800">Client Information</h3>
              {watch('clientName') && watch('requestType') && watch('week') && (
                <span className="text-green-600 text-xs">✓</span>
              )}
            </div>
            <button
              type="button"
              className="p-1 text-gray-400 hover:text-gray-600 transition-colors"
            >
              <span className="text-sm">
                {expandedSections.has(1) ? '⋯' : '›'}
              </span>
            </button>
          </div>

          {expandedSections.has(1) && (
            <div className="px-4 pb-4 border-t border-gray-100">
              <div className="flex gap-3 mt-3 items-start">
                <div className="flex-shrink-0 w-64">
                  <label htmlFor="clientName" className="block text-xs font-medium text-gray-700 mb-1">
                    Client Name *
                  </label>
                  <div className="flex gap-2">
                    <select
                      {...register('clientName')}
                      className="w-60 px-2 py-1 border border-gray-300 rounded focus:outline-none focus:ring-2 focus:ring-blue-500 bg-white text-sm"
                    >
                      <option value="">-- Select Client --</option>
                      {clients.map((client, idx) => (
                        <option key={idx} value={client.client_name}>
                          {client.client_name}
                        </option>
                      ))}
                    </select>
                    <button
                      type="button"
                      onClick={() => setShowAddClient(true)}
                      className="px-2 py-1 bg-green-600 hover:bg-green-700 text-white rounded transition-colors text-sm"
                      title="Add New Client"
                    >
                      +
                    </button>
                  </div>
                  {errors.clientName && (
                    <p className="mt-1 text-xs text-red-600">{errors.clientName.message}</p>
                  )}
                </div>

                <div className="flex-shrink-0 w-64">
                  <label className="block text-xs font-medium text-gray-700 mb-1">
                    Request Type *
                  </label>
                  <select
                    {...register('requestType')}
                    className="w-60 px-2 py-1 border border-gray-300 rounded focus:outline-none focus:ring-2 focus:ring-blue-500 bg-white text-sm"
                  >
                    <option value="1">Type 1 - Standard Request</option>
                    <option value="2">Type 2 - With Unique Decile Report Path</option>
                  </select>
                  {errors.requestType && (
                    <p className="mt-1 text-xs text-red-600">{errors.requestType.message}</p>
                  )}
                </div>

                <div className="flex-shrink-0 w-48">
                  <label className="block text-xs font-medium text-gray-700 mb-1">
                    Week *
                    {weekTriggerPending && (
                      <span className="ml-2 text-xs text-blue-600 flex items-center">
                        <div className="animate-spin rounded-full h-3 w-3 border-b-2 border-blue-600 mr-1"></div>
                        Checking cycle...
                      </span>
                    )}
                  </label>
                  <input
                    type="text"
                    {...register('week')}
                    className={`w-44 px-2 py-1 border rounded focus:outline-none focus:ring-2 text-sm ${
                      weekTriggerPending
                        ? 'border-blue-300 focus:ring-blue-500 bg-blue-50'
                        : 'border-gray-300 focus:ring-blue-500'
                    }`}
                    placeholder="e.g., Q4_W8"
                  />
                  {errors.week && (
                    <p className="mt-1 text-xs text-red-600">{errors.week.message}</p>
                  )}
                  {weekTriggerPending && (
                    <div className="mt-1 text-xs text-blue-600 flex items-center">
                      <div className="animate-spin rounded-full h-3 w-3 border-b-2 border-blue-600 mr-1"></div>
                      W1/W2 detected - validating new cycle
                    </div>
                  )}
                </div>

                {/* Type 2 Unique Decile Report Upload - Inline beside Week */}
                {showFilePath && (
                  <div className="flex-shrink-0 w-80">
                    <HybridFileInput
                      label="Unique Decile Report Path *"
                      placeholder="Select Unique Decile Report file"
                      value={watch('filePath') || ''}
                      onChange={(value) => setValue('filePath', value)}
                      onFileValidated={(filePath, isValid, error) => handleFileValidated('unique_decile', filePath, isValid, error || null)}
                      onValidationError={(error) => handleFileValidated('unique_decile', '', false, error)}
                      fileType="unique_decile"
                      clientName={watch('clientName') || ''}
                      weekName={watch('week') || ''}
                      error={errors.filePath?.message}
                      className="w-80"
                    />
                  </div>
                )}
              </div>
            </div>
          )}
        </div>

        {/* Section 2: Date Configuration */}
        <div className="bg-white border border-gray-200 rounded shadow-sm">
          <div
            onClick={() => toggleSection(2)}
            className="flex items-center justify-between px-3 py-2 hover:bg-gray-50 transition-colors cursor-pointer"
          >
            <div className="flex items-center space-x-2">
              <span className="text-green-600 font-semibold text-sm">2.</span>
              <h3 className="text-sm font-medium text-gray-800">Campaign Dates</h3>
              {watch('startDate') && watch('endDate') && watch('residualStart') && (
                <span className="text-green-600 text-xs">✓</span>
              )}
            </div>
            <button
              type="button"
              className="p-1 text-gray-400 hover:text-gray-600 transition-colors"
            >
              <span className="text-sm">
                {expandedSections.has(2) ? '⋯' : '›'}
              </span>
            </button>
          </div>

          {expandedSections.has(2) && (
            <div className="px-4 pb-4 border-t border-gray-100">
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3 mt-3">
                <div>
                  <label className="block text-xs font-medium text-gray-700 mb-1">
                    Start Date *
                  </label>
                  <input
                    type="date"
                    {...register('startDate')}
                    className="w-full px-2 py-1 border border-gray-300 rounded focus:outline-none focus:ring-2 focus:ring-green-500"
                  />
                  {errors.startDate && (
                    <p className="mt-1 text-sm text-red-600">{errors.startDate.message}</p>
                  )}
                </div>

                <div>
                  <label className="block text-xs font-medium text-gray-700 mb-1">
                    End Date *
                  </label>
                  <input
                    type="date"
                    {...register('endDate')}
                    className="w-full px-2 py-1 border border-gray-300 rounded focus:outline-none focus:ring-2 focus:ring-green-500"
                  />
                  {errors.endDate && (
                    <p className="mt-1 text-xs text-red-600">{errors.endDate.message}</p>
                  )}
                </div>

                <div>
                  <label className="block text-xs font-medium text-gray-700 mb-1">
                    Residual Date *
                  </label>
                  <input
                    type="date"
                    {...register('residualStart')}
                    className="w-full px-2 py-1 border border-gray-300 rounded focus:outline-none focus:ring-2 focus:ring-green-500"
                  />
                  {errors.residualStart && (
                    <p className="mt-1 text-xs text-red-600">{errors.residualStart.message}</p>
                  )}
                </div>
              </div>
            </div>
          )}
        </div>

        {/* Section 3: File Settings & Options */}
        <div className="bg-white border border-gray-200 rounded shadow-sm">
          <div
            onClick={() => toggleSection(3)}
            className="flex items-center justify-between px-3 py-2 hover:bg-gray-50 transition-colors cursor-pointer"
          >
            <div className="flex items-center space-x-2">
              <span className="text-yellow-600 font-semibold text-sm">3.</span>
              <h3 className="text-sm font-medium text-gray-800">File Settings</h3>
              {watch('fileType') && (
                <span className="text-green-600 text-xs">✓</span>
              )}
            </div>
            <button
              type="button"
              className="p-1 text-gray-400 hover:text-gray-600 transition-colors"
            >
              <span className="text-sm">
                {expandedSections.has(3) ? '⋯' : '›'}
              </span>
            </button>
          </div>

          {expandedSections.has(3) && (
            <div className="px-6 pb-6 border-t border-gray-100">
              <div className="space-y-4 mt-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2 text-center">File Type *</label>
                  <div className="flex justify-center space-x-8">
                    <label className="flex items-center">
                      <input
                        type="radio"
                        value="Sent"
                        {...register('fileType')}
                        className="w-4 h-4 text-yellow-600 focus:ring-yellow-500 border-gray-300"
                      />
                      <span className="ml-2 text-sm text-gray-700">Sent</span>
                    </label>
                    <label className="flex items-center">
                      <input
                        type="radio"
                        value="Delivered"
                        {...register('fileType')}
                        className="w-4 h-4 text-yellow-600 focus:ring-yellow-500 border-gray-300"
                      />
                      <span className="ml-2 text-sm text-gray-700">Delivered</span>
                    </label>
                  </div>
                  {errors.fileType && (
                    <p className="mt-1 text-sm text-red-600 text-center">{errors.fileType.message}</p>
                  )}
                </div>

                <div className="flex flex-wrap gap-4 justify-center">
                  <label className="flex items-center">
                    <input
                      type="checkbox"
                      {...register('addTimeStamp')}
                      className="w-4 h-4 text-yellow-600 focus:ring-yellow-500 border-gray-300 rounded"
                    />
                    <span className="ml-2 text-sm text-gray-700">Add TimeStamp</span>
                  </label>

                  <label className="flex items-center">
                    <input
                      type="checkbox"
                      {...register('addBounce')}
                      className="w-4 h-4 text-yellow-600 focus:ring-yellow-500 border-gray-300 rounded"
                    />
                    <span className="ml-2 text-sm text-gray-700">Add Bounce</span>
                  </label>

                  <label className="flex items-center">
                    <input
                      type="checkbox"
                      {...register('addIpsLogs')}
                      className="w-4 h-4 text-yellow-600 focus:ring-yellow-500 border-gray-300 rounded"
                    />
                    <span className="ml-2 text-sm text-gray-700">Add IPs to Logs</span>
                  </label>
                </div>

                {/* TimeStamp Path Input */}
                {showTimeStampPath && (
                  <div className="w-96">
                    <HybridFileInput
                      label="TimeStamp File Path *"
                      placeholder="Select Timestamp Report file"
                      value={watch('timeStampPath') || ''}
                      onChange={(value) => setValue('timeStampPath', value)}
                      onFileValidated={(filePath, isValid, error) => handleFileValidated('timestamp', filePath, isValid, error || null)}
                      onValidationError={(error) => handleFileValidated('timestamp', '', false, error)}
                      fileType="timestamp"
                      clientName={watch('clientName') || ''}
                      weekName={watch('week') || ''}
                      error={errors.timeStampPath?.message}
                      className="w-80"
                    />
                  </div>
                )}
              </div>
            </div>
          )}
        </div>

        {/* Section 4: Report Paths */}
        <div className="bg-white border border-gray-200 rounded shadow-sm">
          <div
            onClick={() => toggleSection(4)}
            className="flex items-center justify-between px-3 py-2 hover:bg-gray-50 transition-colors cursor-pointer"
          >
            <div className="flex items-center space-x-2">
              <span className="text-purple-600 font-semibold text-sm">4.</span>
              <h3 className="text-sm font-medium text-gray-800">Report Paths</h3>
              {watch('reportpath') && watch('qspath') && (
                <span className="text-green-600 text-xs">✓</span>
              )}
            </div>
            <button
              type="button"
              className="p-1 text-gray-400 hover:text-gray-600 transition-colors"
            >
              <span className="text-sm">
                {expandedSections.has(4) ? '⋯' : '›'}
              </span>
            </button>
          </div>

          {expandedSections.has(4) && (
            <div className="px-4 pb-4 border-t border-gray-100">
              <div className="flex gap-3 mt-3 items-start">
                <div className="flex-shrink-0 w-80">
                  <HybridFileInput
                    label="CPM Report Path *"
                    placeholder="Select CPM Report file"
                    value={watch('reportpath') || ''}
                    onChange={(value) => setValue('reportpath', value)}
                    onFileValidated={(filePath, isValid, error) => handleFileValidated('cpm', filePath, isValid, error || null)}
                    onValidationError={(error) => handleFileValidated('cpm', '', false, error)}
                    fileType="cpm"
                    clientName={watch('clientName') || ''}
                    weekName={watch('week') || ''}
                    error={errors.reportpath?.message}
                    className="w-80"
                  />
                </div>

                <div className="flex-shrink-0 w-80">
                  <HybridFileInput
                    label="Decile Report Path *"
                    placeholder="Select Decile Report file"
                    value={watch('qspath') || ''}
                    onChange={(value) => setValue('qspath', value)}
                    onFileValidated={(filePath, isValid, error) => handleFileValidated('decile', filePath, isValid, error || null)}
                    onValidationError={(error) => handleFileValidated('decile', '', false, error)}
                    fileType="decile"
                    clientName={watch('clientName') || ''}
                    weekName={watch('week') || ''}
                    error={errors.qspath?.message}
                    className="w-80"
                  />
                </div>
              </div>
            </div>
          )}
        </div>

        {/* Cross-Validation Overlay - Only shows during validation or on failure */}
        {isCrossValidating && (
          <div className="fixed inset-0 bg-black bg-opacity-30 flex items-center justify-center z-50">
            <div className="bg-white rounded-lg shadow-xl p-6 flex items-center space-x-3">
              <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
              <span className="text-gray-700 font-medium">Validating reports...</span>
            </div>
          </div>
        )}

        {/* Cross-Validation Error Display - Only shows if validation failed */}
        {!isCrossValidating && crossValidationState.performed && crossValidationState.passed === false && (
          <div className="bg-white border-2 border-red-300 rounded-lg shadow-sm">
            <div className="bg-red-50 px-4 py-3 border-b border-red-200">
              <div className="flex items-center space-x-2">
                <svg className="h-5 w-5 text-red-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
                </svg>
                <h3 className="text-sm font-semibold text-red-800">Cross-Validation Failed</h3>
              </div>
            </div>
            <div className="px-4 py-3">
              <p className="text-sm text-red-700 mb-2">Please fix the following issues before submitting:</p>
              <ul className="space-y-1">
                {crossValidationState.errors.map((error, index) => (
                  <li key={index} className="text-sm text-red-600 flex items-start space-x-2">
                    <span className="text-red-500 font-bold">•</span>
                    <span>{error}</span>
                  </li>
                ))}
              </ul>
              {crossValidationState.validationsPerformed.length > 0 && (
                <p className="text-xs text-gray-600 mt-3 pt-3 border-t border-red-100">
                  Validations performed: {crossValidationState.validationsPerformed.join(', ')}
                </p>
              )}
            </div>
          </div>
        )}

        {/* Section 5: Suppression List */}
        <div className="bg-white border border-gray-200 rounded shadow-sm">
          <div
            onClick={() => toggleSection(5)}
            className="flex items-center justify-between px-3 py-2 hover:bg-gray-50 transition-colors cursor-pointer"
          >
            <div className="flex items-center space-x-2">
              <span className="text-red-600 font-semibold text-sm">5.</span>
              <h3 className="text-sm font-medium text-gray-800">Suppression List</h3>
            </div>
            <button
              type="button"
              className="p-1 text-gray-400 hover:text-gray-600 transition-colors"
            >
              <span className="text-sm">
                {expandedSections.has(5) ? '⋯' : '›'}
              </span>
            </button>
          </div>

          {expandedSections.has(5) && (
            <div className="px-4 pb-4 border-t border-gray-100">
              <div className="space-y-4 mt-3">
                <div className="grid grid-cols-3 gap-3">
                  <label className="flex items-center">
                    <input
                      type="checkbox"
                      {...register('clientSuppression')}
                      className="w-4 h-4 text-red-600 focus:ring-red-500 border-gray-300 rounded"
                    />
                    <span className="ml-2 text-sm text-gray-700">Client Suppression</span>
                  </label>

                  <label className="flex items-center">
                    <input
                      type="checkbox"
                      {...register('requestIdSuppression')}
                      className="w-4 h-4 text-red-600 focus:ring-red-500 border-gray-300 rounded"
                    />
                    <span className="ml-2 text-sm text-gray-700">Request ID Suppression</span>
                  </label>

                  <label className="flex items-center">
                    <input
                      type="checkbox"
                      {...register('offerSuppression')}
                      className="w-4 h-4 text-red-600 focus:ring-red-500 border-gray-300 rounded"
                    />
                    <span className="ml-2 text-sm text-gray-700">Offer Suppression</span>
                  </label>
                </div>

                {showClientSuppressionPath && (
                  <div className="w-96">
                    <label className="block text-sm font-medium text-gray-700 mb-1">
                      Client Suppression Path *
                    </label>
                    <input
                      type="text"
                      {...register('clientSuppressionPath')}
                      className="w-80 px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-red-500 text-sm"
                      placeholder="Enter client suppression file path"
                    />
                    {errors.clientSuppressionPath && (
                      <p className="mt-1 text-xs text-red-600">{errors.clientSuppressionPath.message}</p>
                    )}
                  </div>
                )}

                {showRequestIdSuppressionList && (
                  <div className="w-96">
                    <label className="block text-sm font-medium text-gray-700 mb-1">
                      Request ID Suppression List *
                    </label>
                    <input
                      type="text"
                      {...register('requestIdSuppressionList')}
                      className="w-80 px-2 py-1 border border-gray-300 rounded focus:outline-none focus:ring-2 focus:ring-red-500 text-sm"
                      placeholder="Enter comma-separated request IDs"
                    />
                    {errors.requestIdSuppressionList && (
                      <p className="mt-1 text-xs text-red-600">{errors.requestIdSuppressionList.message}</p>
                    )}
                  </div>
                )}
              </div>
            </div>
          )}
        </div>

        {/* Section 6: Data Priority */}
        <div className="bg-white border border-gray-200 rounded shadow-sm">
          <div
            onClick={() => toggleSection(6)}
            className="flex items-center justify-between px-3 py-2 hover:bg-gray-50 transition-colors cursor-pointer"
          >
            <div className="flex items-center space-x-2">
              <span className="text-orange-600 font-semibold text-sm">6.</span>
              <h3 className="text-sm font-medium text-gray-800">Data Priority</h3>
            </div>
            <button
              type="button"
              className="p-1 text-gray-400 hover:text-gray-600 transition-colors"
            >
              <span className="text-sm">
                {expandedSections.has(6) ? '⋯' : '›'}
              </span>
            </button>
          </div>

          {expandedSections.has(6) && (
            <div className="px-4 pb-4 border-t border-gray-100">
              <div className="flex gap-3 mt-3 items-start">
                <div className="flex-shrink-0 w-80">
                  <label className="block text-xs font-medium text-gray-700 mb-1">
                    Priority File Path (Optional)
                  </label>
                  <input
                    type="text"
                    {...register('priorityFile')}
                    className="w-80 px-2 py-1 border border-gray-300 rounded focus:outline-none focus:ring-2 focus:ring-orange-500 text-sm"
                    placeholder="Enter priority file path"
                  />
                  {errors.priorityFile && (
                    <p className="mt-1 text-xs text-red-600">{errors.priorityFile.message}</p>
                  )}
                </div>

                {showPriorityFields && (
                  <div className="flex-shrink-0 w-60">
                    <label className="block text-xs font-medium text-gray-700 mb-1">
                      Priority File Percentage *
                    </label>
                    <input
                      type="number"
                      {...register('priorityFilePer', { valueAsNumber: true })}
                      className="w-40 px-2 py-1 border border-gray-300 rounded focus:outline-none focus:ring-2 focus:ring-orange-500 text-sm"
                      placeholder="1-100"
                      min="1"
                      max="100"
                    />
                    {errors.priorityFilePer && (
                      <p className="mt-1 text-xs text-red-600">{errors.priorityFilePer.message}</p>
                    )}
                  </div>
                )}
              </div>
            </div>
          )}
        </div>

        {/* Section 7: SQL Query */}
        <div className="bg-white border border-gray-200 rounded shadow-sm">
          <div
            onClick={() => toggleSection(7)}
            className="flex items-center justify-between px-3 py-2 hover:bg-gray-50 transition-colors cursor-pointer"
          >
            <div className="flex items-center space-x-2">
              <span className="text-indigo-600 font-semibold text-sm">7.</span>
              <h3 className="text-sm font-medium text-gray-800">SQL Query</h3>
              {watch('input_query') && (
                <span className="text-green-600 text-xs">✓</span>
              )}
            </div>
            <button
              type="button"
              className="p-1 text-gray-400 hover:text-gray-600 transition-colors"
            >
              <span className="text-sm">
                {expandedSections.has(7) ? '⋯' : '›'}
              </span>
            </button>
          </div>

          {expandedSections.has(7) && (
            <div className="px-4 pb-4 border-t border-gray-100">
              <div className="mt-3">
                <label className="block text-xs font-medium text-gray-700 mb-1">
                  SQL Query *
                </label>
                <textarea
                  {...register('input_query')}
                  rows={6}
                  className="w-full px-2 py-1 border border-gray-300 rounded focus:outline-none focus:ring-2 focus:ring-indigo-500 font-mono text-sm"
                  placeholder="Enter your SQL query here..."
                />
                {errors.input_query && (
                  <p className="mt-1 text-xs text-red-600">{errors.input_query.message}</p>
                )}
              </div>
            </div>
          )}
        </div>

        {/* Section 8: Rerun Module Selection (Edit Mode Only) */}
        {editMode && (
          <div className="bg-white border border-gray-200 rounded shadow-sm">
            <div
              onClick={() => toggleSection(8)}
              className="flex items-center justify-between px-3 py-2 hover:bg-gray-50 transition-colors cursor-pointer"
            >
              <div className="flex items-center space-x-2">
                <span className="text-purple-600 font-semibold text-sm">8.</span>
                <h3 className="text-sm font-medium text-gray-800">ReRun Module</h3>
              </div>
              <button
                type="button"
                className="p-1 text-gray-400 hover:text-gray-600 transition-colors"
              >
                <span className="text-sm">
                  {expandedSections.has(8) ? '⋯' : '›'}
                </span>
              </button>
            </div>

            {expandedSections.has(8) && (
              <div className="px-4 pb-4 border-t border-gray-100">
                <div className="mt-3">

                  <div className="w-80">
                    <label className="block text-xs font-medium text-gray-700 mb-1">
                      Select Module to Restart From *
                    </label>
                    <select
                      name="rerunModule"
                      defaultValue="TRT"
                      className="w-80 px-2 py-1 border border-gray-300 rounded focus:outline-none focus:ring-2 focus:ring-purple-500 bg-white text-sm"
                    >
                      <option value="TRT">1. TRT</option>
                      <option value="Responders">2. Responders</option>
                      <option value="Suppression">3. Suppression</option>
                      <option value="Source">4. Source</option>
                      <option value="Delivered Report">5. Delivered Report</option>
                      <option value="TimeStamp Appending">6. TimeStamp Appending</option>
                      <option value="IP Appending">7. IP Appending</option>
                    </select>
                  </div>
                </div>
              </div>
            )}
          </div>
        )}

        {/* Submit Section */}
        <div className="bg-white border border-gray-200 rounded shadow-sm p-3">
          <div className="flex justify-center">
            <button
              type="submit"
              disabled={submitting}
              className="px-6 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded transition-colors disabled:opacity-50 disabled:cursor-not-allowed font-medium"
            >
              {submitting ? 'Submitting...' : (editMode ? 'Update & Rerun Request' : 'Submit Request')}
            </button>
          </div>
        </div>
      </form>

      {/* Add Client Modal */}
      {showAddClient && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg shadow-xl p-6 w-96">
            <h3 className="text-lg font-semibold text-gray-900 mb-4">Add New Client</h3>
            <div className="relative mb-4">
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Client Name
              </label>
              <input
                type="text"
                value={newClientName}
                onChange={(e) => handleNewClientNameChange(e.target.value)}
                placeholder="Type client name"
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 text-sm"
                autoFocus
              />
              {/* Autocomplete Dropdown */}
              {filteredClientsInModal.length > 0 && newClientName.trim() && (
                <div className="absolute z-10 w-full mt-1 bg-white border border-gray-300 rounded-lg shadow-lg max-h-48 overflow-y-auto">
                  <div className="p-2 bg-yellow-50 border-b border-yellow-200 text-xs text-yellow-800 font-medium">
                    ⚠️ Matching existing clients:
                  </div>
                  {filteredClientsInModal.map((client, idx) => (
                    <div
                      key={idx}
                      className="px-3 py-2 text-sm text-gray-700 border-b border-gray-100 last:border-b-0 bg-gray-50"
                    >
                      {client.client_name}
                    </div>
                  ))}
                </div>
              )}
            </div>
            <div className="flex justify-end space-x-3">
              <button
                type="button"
                onClick={() => {
                  setShowAddClient(false);
                  setNewClientName('');
                  setFilteredClientsInModal([]);
                }}
                className="px-4 py-2 text-sm font-medium text-gray-700 bg-gray-100 hover:bg-gray-200 rounded-lg transition-colors"
              >
                Cancel
              </button>
              <button
                type="button"
                onClick={handleAddClient}
                disabled={addingClient}
                className="px-4 py-2 text-sm font-medium text-white bg-green-600 hover:bg-green-700 rounded-lg transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {addingClient ? 'Adding...' : 'Add Client'}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Success Modal */}
      {showSuccessModal && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded p-6 max-w-md w-full mx-4">
            <div className="text-center">
              <div className="mx-auto flex items-center justify-center h-10 w-10 rounded-full bg-green-100">
                <svg className="h-5 w-5 text-green-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                </svg>
              </div>
              <h3 className="mt-3 text-base font-medium text-gray-900">Request Submitted Successfully!</h3>
              <p className="mt-2 text-sm text-gray-500">
                Your request has been submitted with ID: {lastSubmittedRequestId}
              </p>
              <div className="mt-4">
                <button
                  type="button"
                  className="w-full inline-flex justify-center rounded border border-transparent shadow-sm px-4 py-2 bg-green-600 text-base font-medium text-white hover:bg-green-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-green-500"
                  onClick={() => {
                    setShowSuccessModal(false);
                    if (onComplete) onComplete();
                  }}
                >
                  Continue
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Flush Delivery Data Modal */}
      <FlushDeliveryDataModal
        isOpen={showFlushModal}
        onClose={handleFlushModalClose}
        onConfirm={handleFlushDeliveryData}
        clientName={clientName || ''}
        weekValue={weekValue || ''}
        loading={flushLoading}
      />

      {/* Flush Success Modal */}
      <SuccessModal
        isOpen={showFlushSuccessModal}
        onClose={() => setShowFlushSuccessModal(false)}
        title="Flush Operation Successful"
        message={flushSuccessMessage}
      />

      {/* Flush Error Modal */}
      <ErrorModal
        isOpen={showFlushErrorModal}
        onClose={() => setShowFlushErrorModal(false)}
        title="Flush Operation Failed"
        message={flushErrorMessage}
      />

      {/* Confirm Add New Client Modal */}
      {showConfirmAddClient && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg shadow-xl p-6 max-w-md w-full mx-4">
            <h3 className="text-lg font-medium text-gray-900 mb-4">Confirm Add New Client</h3>
            <p className="text-sm text-gray-600 mb-6">
              Client "<strong>{newClientName}</strong>" does not exist. Do you want to add it?
              <br /><br />
              <span className="text-xs text-gray-500">This will execute addClient.sh script and create necessary database tables.</span>
            </p>
            <div className="flex justify-end space-x-3">
              <button
                type="button"
                onClick={() => {
                  setShowConfirmAddClient(false);
                  setShowAddClient(true);
                }}
                className="px-4 py-2 text-sm font-medium text-gray-700 bg-gray-100 hover:bg-gray-200 rounded-lg transition-colors"
              >
                No
              </button>
              <button
                type="button"
                onClick={confirmAddNewClient}
                disabled={addingClient}
                className="px-4 py-2 text-sm font-medium text-white bg-green-600 hover:bg-green-700 rounded-lg transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {addingClient ? 'Adding...' : 'Yes, Add Client'}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Alert Modal */}
      <AlertModal
        isOpen={showAlertModal}
        onClose={() => setShowAlertModal(false)}
        title={alertMessage.includes('successfully') ? 'Success' : alertMessage.includes('exists') ? 'Client Exists' : 'Notice'}
        message={alertMessage}
        type={alertMessage.includes('successfully') ? 'success' : alertMessage.includes('exists') ? 'warning' : 'info'}
      />
    </div>
  );
};

export default AddRequestForm;
