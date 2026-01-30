import React, { useState, useEffect, useRef } from 'react';
import { MdClose, MdCloudUpload, MdCheck, MdError, MdInfo, MdRefresh } from 'react-icons/md';
import { FaRegSnowflake } from 'react-icons/fa';

interface SnowflakeUploadModalProps {
  isOpen: boolean;
  onClose: () => void;
  requestId: number;
  clientName: string;
  week: string;
}

interface ColumnData {
  standard: string[];
  custom: string[];
  excluded: string[];
}

interface UploadProgress {
  task_id: string;
  status: 'pending' | 'running' | 'completed' | 'failed';
  percentage: number;
  substep?: string;
  error?: string;
  result?: {
    table_name: string;
    rows_uploaded: number;
    rows_verified: number;
  };
}

const SnowflakeUploadModal: React.FC<SnowflakeUploadModalProps> = ({
  isOpen,
  onClose,
  requestId,
  clientName,
  week
}) => {
  const [headerType, setHeaderType] = useState<'standard' | 'custom'>('standard');
  const [columns, setColumns] = useState<ColumnData | null>(null);
  const [selectedCustomColumns, setSelectedCustomColumns] = useState<string[]>([]);
  const [loading, setLoading] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState<UploadProgress | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [canReupload, setCanReupload] = useState(false);
  const [showReuploadConfirm, setShowReuploadConfirm] = useState(false);

  const pollIntervalRef = useRef<NodeJS.Timeout | null>(null);

  // Fetch columns when modal opens
  useEffect(() => {
    if (isOpen) {
      fetchColumns();
    } else {
      // Clean up when modal closes
      if (pollIntervalRef.current) {
        clearInterval(pollIntervalRef.current);
      }
    }
  }, [isOpen]);

  // Poll progress when uploading
  useEffect(() => {
    if (uploading && uploadProgress?.task_id) {
      startProgressPolling(uploadProgress.task_id);
    }

    return () => {
      if (pollIntervalRef.current) {
        clearInterval(pollIntervalRef.current);
      }
    };
  }, [uploading, uploadProgress?.task_id]);

  const fetchColumns = async () => {
    setLoading(true);
    setError(null);

    try {
      console.log('🔍 SnowflakeUploadModal Props:', { requestId, clientName, week });

      // Use the same table naming as MetricsModal - no lowercase conversion
      const tableName = `apt_custom_${requestId}_${clientName}_${week}_postback_table`;
      console.log('🔍 Generated table name:', tableName);

      const apiUrl = `/api/tables/${tableName}/columns`;
      console.log('🔍 API URL:', apiUrl);

      // Use the same API endpoint as MetricsModal
      const response = await fetch(apiUrl);
      console.log('🔍 Response status:', response.status);
      console.log('🔍 Response ok:', response.ok);

      const data = await response.json();
      console.log('🔍 Response data:', data);

      if (data.success) {
        // Get standard columns from config
        const standardColumns = [
          'Md5hash', 'Segment', 'SubSeg', 'Decile', 'DeliveredFlag',
          'DeliveredDate', 'Subject', 'Creative', 'OpenDate', 'ClickDate', 'UnsubDate'
        ];

        // Excluded columns from config
        const excludedColumns = ['priority', 'status', 'unsub', 'freq', 'id', 'touch', 'diff'];

        // Source columns used in standard header (these should also be excluded from custom selection)
        const sourceColumnsInStandardHeader = [
          'flag',        // used in DeliveredFlag
          'del_date',    // used in DeliveredDate
          'open_date',   // used in OpenDate
          'click_date',  // used in ClickDate
          'unsub_date'   // used in UnsubDate
        ];

        // Combine all columns to exclude
        const allExcludedColumns = [
          ...standardColumns.map(s => s.toLowerCase()),
          ...excludedColumns,
          ...sourceColumnsInStandardHeader
        ];

        // Filter available custom columns
        const availableCustomColumns = data.columns.filter(
          (col: string) => !allExcludedColumns.includes(col.toLowerCase())
        );

        console.log('✅ Filtered custom columns:', availableCustomColumns);

        setColumns({
          standard: standardColumns,
          custom: availableCustomColumns,
          excluded: excludedColumns
        });
      } else {
        console.error('❌ API returned error:', data.error);
        setError(data.error || 'Failed to fetch columns');
      }
    } catch (err) {
      console.error('❌ Exception in fetchColumns:', err);
      setError('Failed to fetch columns from server');
    } finally {
      setLoading(false);
    }
  };

  const handleCustomColumnToggle = (column: string) => {
    setSelectedCustomColumns(prev => {
      if (prev.includes(column)) {
        return prev.filter(c => c !== column);
      } else {
        return [...prev, column];
      }
    });
  };

  const startUpload = async () => {
    setUploading(true);
    setError(null);
    setCanReupload(false);

    try {
      const response = await fetch(`/api/snowflake/upload/${requestId}`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          client_name: clientName,
          week: week,
          header_type: headerType,
          custom_columns: headerType === 'custom' ? selectedCustomColumns : []
        })
      });

      const data = await response.json();

      if (data.success) {
        setUploadProgress({
          task_id: data.task_id,
          status: 'pending',
          percentage: 0
        });
      } else {
        setError(data.error || 'Failed to start upload');
        setUploading(false);
        setCanReupload(true);
      }
    } catch (err) {
      setError('Failed to start upload');
      console.error('Error starting upload:', err);
      setUploading(false);
      setCanReupload(true);
    }
  };

  const startProgressPolling = (taskId: string) => {
    // Clear any existing interval
    if (pollIntervalRef.current) {
      clearInterval(pollIntervalRef.current);
    }

    // Poll every 2 seconds
    pollIntervalRef.current = setInterval(async () => {
      try {
        const response = await fetch(`/api/snowflake/progress/${taskId}`);
        const data = await response.json();

        if (data.success) {
          setUploadProgress(data.task);

          // Stop polling if task is completed or failed
          if (data.task.status === 'completed' || data.task.status === 'failed') {
            if (pollIntervalRef.current) {
              clearInterval(pollIntervalRef.current);
            }

            setUploading(false);
            setCanReupload(true);

            if (data.task.status === 'failed') {
              setError(data.task.error || 'Upload failed');
            }
          }
        }
      } catch (err) {
        console.error('Error polling progress:', err);
      }
    }, 2000);
  };

  const handleReuploadClick = () => {
    setShowReuploadConfirm(true);
  };

  const handleReuploadConfirm = () => {
    setShowReuploadConfirm(false);
    setUploadProgress(null);
    setError(null);
    setCanReupload(false);
    startUpload();
  };

  const handleReuploadCancel = () => {
    setShowReuploadConfirm(false);
  };

  const getStatusIcon = () => {
    if (!uploadProgress) return null;

    switch (uploadProgress.status) {
      case 'completed':
        return <MdCheck className="w-6 h-6 text-green-600" />;
      case 'failed':
        return <MdError className="w-6 h-6 text-red-600" />;
      case 'running':
      case 'pending':
        return (
          <div className="w-6 h-6 border-4 border-blue-600 border-t-transparent rounded-full animate-spin" />
        );
      default:
        return null;
    }
  };

  const getStatusColor = () => {
    if (!uploadProgress) return 'bg-gray-200';

    switch (uploadProgress.status) {
      case 'completed':
        return 'bg-green-600';
      case 'failed':
        return 'bg-red-600';
      case 'running':
      case 'pending':
        return 'bg-blue-600';
      default:
        return 'bg-gray-200';
    }
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded shadow-xl w-full max-w-2xl flex flex-col relative">
        {/* Header */}
        <div className="flex items-center justify-between p-4 border-b border-gray-200">
          <div className="flex items-center space-x-2">
            <FaRegSnowflake className="h-5 w-5 text-blue-600" />
            <h2 className="text-base font-medium text-gray-900">
              Upload to Snowflake - #{requestId}
            </h2>
          </div>
          <button
            onClick={onClose}
            className="text-gray-400 hover:text-gray-600 transition-colors"
            disabled={uploading}
          >
            <MdClose className="h-4 w-4" />
          </button>
        </div>

        {/* Content */}
        <div className="p-4">
          <div className="space-y-4">
          {error && (
            <div className="bg-red-50 border border-red-200 rounded p-3">
              <div className="flex">
                <div className="ml-2">
                  <h3 className="text-sm font-medium text-red-800">Error</h3>
                  <p className="mt-1 text-sm text-red-700">{error}</p>
                </div>
              </div>
            </div>
          )}

          {loading ? (
            <div className="flex items-center justify-center py-12">
              <div className="animate-spin rounded-full h-10 w-10 border-b-2 border-blue-600"></div>
              <span className="ml-3 text-gray-600">Loading table columns...</span>
            </div>
          ) : uploadProgress ? (
            /* Upload Progress View */
            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <div className="flex items-center space-x-3">
                  {getStatusIcon()}
                  <div>
                    <h3 className="text-base font-medium text-gray-900">
                      {uploadProgress.status === 'completed'
                        ? 'Upload Completed'
                        : uploadProgress.status === 'failed'
                        ? 'Upload Failed'
                        : 'Uploading...'}
                    </h3>
                    {/* Hide substep if completed or if it's "Verifying upload..." */}
                    {uploadProgress.substep &&
                     uploadProgress.status !== 'completed' &&
                     !uploadProgress.substep.toLowerCase().includes('verifying') && (
                      <p className="text-xs text-gray-600">{uploadProgress.substep}</p>
                    )}
                  </div>
                </div>
                <span className="text-xl font-bold text-gray-900">
                  {uploadProgress.percentage}%
                </span>
              </div>

              {/* Progress Bar */}
              <div className="w-full bg-gray-200 rounded-full h-3 overflow-hidden">
                <div
                  className={`h-full ${getStatusColor()} transition-all duration-300 ease-out`}
                  style={{ width: `${uploadProgress.percentage}%` }}
                />
              </div>

              {/* Results */}
              {uploadProgress.status === 'completed' && uploadProgress.result && (
                <div className="bg-green-50 border border-green-200 rounded-lg p-4 space-y-2">
                  <div className="flex items-center space-x-2">
                    <MdCheck className="w-6 h-6 text-green-600" />
                    <h4 className="text-base font-medium text-green-900">Upload Successful!</h4>
                  </div>
                  <div className="text-sm text-green-800 space-y-1.5 pl-8">
                    <p>Table: <strong>{uploadProgress.result.table_name}</strong></p>
                    <div className="flex items-center space-x-1.5">
                      <MdCheck className="w-5 h-5 text-green-600" />
                      <p>Rows Verified: <strong>{uploadProgress.result.rows_verified.toLocaleString()}</strong></p>
                    </div>
                  </div>
                </div>
              )}
            </div>
          ) : (
            /* Column Selection View */
            <div className="space-y-4">
              {/* Header Type Selection */}
              <div>
                <h3 className="text-base font-medium text-gray-900 mb-3 text-left">Select Header Type</h3>
                <div className="flex flex-col space-y-3">
                  <label className="flex items-center">
                    <input
                      type="radio"
                      value="standard"
                      checked={headerType === 'standard'}
                      onChange={() => setHeaderType('standard')}
                      className="mr-3 h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300"
                      disabled={uploading}
                    />
                    <span className="text-gray-700 text-base font-medium">Standard Header</span>
                    <div className="relative group ml-3">
                      <MdInfo className="w-5 h-5 text-gray-400 cursor-help" />
                      <div className="absolute left-full top-1/2 -translate-y-1/2 ml-3 hidden group-hover:block w-96 p-4 bg-white border border-gray-300 text-gray-700 text-sm rounded-lg shadow-lg z-[9999] pointer-events-none">
                        {/* Arrow pointing left */}
                        <div className="absolute right-full top-1/2 -translate-y-1/2 border-8 border-transparent border-r-white mr-[-1px]"></div>
                        <div className="absolute right-full top-1/2 -translate-y-1/2 border-8 border-transparent border-r-gray-300"></div>
                        <div className="font-semibold text-gray-900 mb-2">Standard columns:</div>
                        <div className="text-gray-600 leading-relaxed">
                          Md5hash, Segment, SubSeg, Decile, DeliveredFlag, DeliveredDate, Subject, Creative, OpenDate, ClickDate, UnsubDate
                        </div>
                      </div>
                    </div>
                  </label>
                  <label className="flex items-center">
                    <input
                      type="radio"
                      value="custom"
                      checked={headerType === 'custom'}
                      onChange={() => setHeaderType('custom')}
                      className="mr-3 h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300"
                      disabled={uploading}
                    />
                    <span className="text-gray-700 text-base font-medium">Custom Header (Standard + Custom Columns)</span>
                  </label>
                </div>
              </div>

              {/* Custom Column Selection */}
              {headerType === 'custom' && columns && (
                <div>
                  <h3 className="text-base font-medium text-gray-900 mb-3">
                    Select Additional Columns
                    <span className="ml-2 text-sm font-normal text-gray-500">
                      ({selectedCustomColumns.length} selected)
                    </span>
                  </h3>
                  <div className="border rounded-lg p-4 bg-gray-50">
                    <div className="grid grid-cols-4 gap-3">
                      {columns.custom.map(column => (
                        <label
                          key={column}
                          className="flex items-center space-x-2 cursor-pointer"
                        >
                          <input
                            type="checkbox"
                            checked={selectedCustomColumns.includes(column)}
                            onChange={() => handleCustomColumnToggle(column)}
                            className="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded"
                            disabled={uploading}
                          />
                          <span className="text-sm text-gray-700">{column}</span>
                        </label>
                      ))}
                    </div>
                  </div>
                </div>
              )}
            </div>
          )}
          </div>
        </div>

        {/* Footer */}
        <div className="flex items-center justify-end space-x-2 p-4 border-t border-gray-200">
          {canReupload && (
            <button
              onClick={handleReuploadClick}
              className="px-3 py-2 text-sm font-medium bg-gray-500 hover:bg-gray-600 text-white rounded transition-colors flex items-center space-x-2"
              title="Re-upload to Snowflake (existing data will be replaced)"
            >
              <MdRefresh className="h-4 w-4" />
              <span>Re-upload</span>
            </button>
          )}

          {!uploadProgress && (
            <button
              onClick={startUpload}
              disabled={uploading || loading || (headerType === 'custom' && selectedCustomColumns.length === 0)}
              className={`px-4 py-2 text-sm font-medium text-white border border-transparent rounded flex items-center space-x-2 transition-all duration-200 ${
                uploading || loading || (headerType === 'custom' && selectedCustomColumns.length === 0)
                  ? 'bg-gray-400 cursor-not-allowed'
                  : 'bg-blue-600 hover:bg-blue-700 hover:shadow-md'
              }`}
            >
              <MdCloudUpload className="h-5 w-5" />
              <span>Start Upload</span>
            </button>
          )}
        </div>

        {/* Re-upload Confirmation Dialog */}
        {showReuploadConfirm && (
          <div className="absolute inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 rounded">
            <div className="bg-white rounded-lg shadow-xl p-5 max-w-md mx-4">
              <div className="flex items-start space-x-3">
                <div className="flex-shrink-0">
                  <MdInfo className="h-7 w-7 text-yellow-500" />
                </div>
                <div className="flex-1">
                  <h3 className="text-base font-medium text-gray-900 mb-2">
                    Confirm Re-upload
                  </h3>
                  <p className="text-sm text-gray-600 mb-4">
                    Are you sure you want to re-upload? This will replace all existing data in the Snowflake table.
                  </p>
                  <div className="flex space-x-2 justify-end">
                    <button
                      onClick={handleReuploadCancel}
                      className="px-4 py-2 text-sm font-medium text-gray-700 bg-gray-100 hover:bg-gray-200 rounded transition-colors"
                    >
                      No
                    </button>
                    <button
                      onClick={handleReuploadConfirm}
                      className="px-4 py-2 text-sm font-medium text-white bg-yellow-500 hover:bg-yellow-600 rounded transition-colors"
                    >
                      Yes, Re-upload
                    </button>
                  </div>
                </div>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default SnowflakeUploadModal;
