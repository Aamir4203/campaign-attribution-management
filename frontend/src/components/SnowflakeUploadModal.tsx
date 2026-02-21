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
    table_name?: string;
    rows_uploaded?: number;
    rows_verified?: number;
    files_uploaded?: number;
    total_rows?: number;
    tables?: string;
  };
}

interface DualUploadProgress {
  production: UploadProgress | null;
  audit: UploadProgress | null;
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
  const [dualProgress, setDualProgress] = useState<DualUploadProgress>({ production: null, audit: null });
  const [error, setError] = useState<string | null>(null);
  const [canReupload, setCanReupload] = useState(false);
  const [showReuploadConfirm, setShowReuploadConfirm] = useState(false);
  const [reuploadType, setReuploadType] = useState<'production' | 'audit' | 'both'>('both');

  // Dual upload feature flag
  const [dualUploadEnabled, setDualUploadEnabled] = useState(false);
  const [dualUploadToggle, setDualUploadToggle] = useState(false);

  const pollIntervalRef = useRef<NodeJS.Timeout | null>(null);

  // Legacy single progress for backward compatibility
  const uploadProgress = dualProgress.production;

  // Fetch feature flags on mount
  useEffect(() => {
    const fetchFeatures = async () => {
      try {
        const response = await fetch('/api/features');
        const data = await response.json();
        if (data.success) {
          setDualUploadEnabled(data.features.dual_sf_upload || false);
          setDualUploadToggle(data.features.dual_sf_upload || false);
        }
      } catch (err) {
        console.error('Error fetching features:', err);
      }
    };
    fetchFeatures();
  }, []);

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

  // Poll progress when uploading (dual polling)
  useEffect(() => {
    if (uploading && (dualProgress.production?.task_id || dualProgress.audit?.task_id)) {
      startDualProgressPolling();
    }

    return () => {
      if (pollIntervalRef.current) {
        clearInterval(pollIntervalRef.current);
      }
    };
  }, [uploading, dualProgress.production?.task_id, dualProgress.audit?.task_id]);

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

  const startUpload = async (uploadType: 'production' | 'audit' | 'both' = 'both') => {
    setUploading(true);
    setError(null);
    setCanReupload(false);

    // If dual upload toggle is OFF, force production only
    const effectiveUploadType = !dualUploadToggle ? 'production' : uploadType;

    try {
      // Use dual upload endpoint
      const response = await fetch(`/api/snowflake/upload-dual/${requestId}`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          client_name: clientName,
          week: week,
          header_type: headerType,
          custom_columns: headerType === 'custom' ? selectedCustomColumns : [],
          enable_production: effectiveUploadType === 'production' || effectiveUploadType === 'both',
          enable_audit: effectiveUploadType === 'audit' || effectiveUploadType === 'both'
        })
      });

      const data = await response.json();

      if (data.success) {
        // Set dual progress
        const newProgress: DualUploadProgress = {
          production: (uploadType === 'production' || uploadType === 'both') && data.production_task_id ? {
            task_id: data.production_task_id,
            status: 'pending',
            percentage: 0
          } : dualProgress.production,
          audit: (uploadType === 'audit' || uploadType === 'both') && data.audit_task_id ? {
            task_id: data.audit_task_id,
            status: 'pending',
            percentage: 0
          } : dualProgress.audit
        };
        setDualProgress(newProgress);
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

  const startDualProgressPolling = () => {
    // Clear any existing interval
    if (pollIntervalRef.current) {
      clearInterval(pollIntervalRef.current);
    }

    // Poll every 2 seconds
    pollIntervalRef.current = setInterval(async () => {
      try {
        const updates: DualUploadProgress = {
          production: dualProgress.production,
          audit: dualProgress.audit
        };

        // Poll production progress
        if (dualProgress.production?.task_id) {
          const prodResponse = await fetch(`/api/snowflake/progress/${dualProgress.production.task_id}`);
          const prodData = await prodResponse.json();
          if (prodData.success) {
            updates.production = prodData.task;
          }
        }

        // Poll audit progress
        if (dualProgress.audit?.task_id) {
          const auditResponse = await fetch(`/api/snowflake/progress/${dualProgress.audit.task_id}`);
          const auditData = await auditResponse.json();
          if (auditData.success) {
            updates.audit = auditData.task;
          }
        }

        setDualProgress(updates);

        // Check if both completed or failed
        const prodDone = !updates.production || ['completed', 'failed'].includes(updates.production.status);
        const auditDone = !updates.audit || ['completed', 'failed'].includes(updates.audit.status);

        if (prodDone && auditDone) {
          if (pollIntervalRef.current) {
            clearInterval(pollIntervalRef.current);
          }
          setUploading(false);
          setCanReupload(true);

          // Set error if any failed
          if (updates.production?.status === 'failed') {
            setError(`Production: ${updates.production.error || 'Upload failed'}`);
          }
          if (updates.audit?.status === 'failed') {
            setError(prev => prev ? `${prev} | Audit: ${updates.audit?.error || 'Upload failed'}` : `Audit: ${updates.audit?.error || 'Upload failed'}`);
          }
        }
      } catch (err) {
        console.error('Error polling dual progress:', err);
      }
    }, 2000);
  };

  const handleReuploadClick = (type: 'production' | 'audit' | 'both') => {
    setReuploadType(type);
    setShowReuploadConfirm(true);
  };

  const handleReuploadConfirm = () => {
    setShowReuploadConfirm(false);
    setDualProgress({ production: null, audit: null });
    setError(null);
    setCanReupload(false);
    startUpload(reuploadType);
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
          <div className="flex items-center space-x-4">
            {/* Dual Upload Toggle - Always visible */}
            {!uploading && !dualProgress.production && !dualProgress.audit && (
              <div className="flex items-center space-x-2">
                <span className="text-xs text-gray-600">Dual Upload</span>
                <button
                  onClick={() => setDualUploadToggle(!dualUploadToggle)}
                  className={`relative inline-flex h-5 w-9 items-center rounded-full transition-colors focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 ${
                    dualUploadToggle ? 'bg-blue-600' : 'bg-gray-300'
                  }`}
                  disabled={uploading}
                >
                  <span
                    className={`inline-block h-3 w-3 transform rounded-full bg-white transition-transform ${
                      dualUploadToggle ? 'translate-x-5' : 'translate-x-1'
                    }`}
                  />
                </button>
              </div>
            )}
            <button
              onClick={onClose}
              className="text-gray-400 hover:text-gray-600 transition-colors"
              disabled={uploading}
            >
              <MdClose className="h-4 w-4" />
            </button>
          </div>
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
          ) : (dualProgress.production || dualProgress.audit) ? (
            /* Dual Upload Progress View */
            <div className="space-y-4">
              {/* Production Delivery Progress */}
              {dualProgress.production && (
                <div className="space-y-3">
                  <div className="flex items-center space-x-2">
                    <h3 className="text-sm font-semibold text-gray-700">Production Delivery</h3>
                  </div>
                  <div className="flex items-center justify-between">
                    <div className="flex items-center space-x-3">
                      {dualProgress.production.status !== 'completed' && (
                        dualProgress.production.status === 'failed' ? <MdError className="w-6 h-6 text-red-600" /> :
                        dualProgress.production.status === 'running' || dualProgress.production.status === 'pending' ?
                        <div className="w-6 h-6 border-4 border-blue-600 border-t-transparent rounded-full animate-spin" /> : null
                      )}
                      <div>
                        <p className="text-sm text-gray-900">
                          {dualProgress.production.status === 'completed' ? 'Completed' :
                           dualProgress.production.status === 'failed' ? 'Failed' : 'Uploading...'}
                        </p>
                        {dualProgress.production.substep && dualProgress.production.status !== 'completed' && (
                          <p className="text-xs text-gray-600">{dualProgress.production.substep}</p>
                        )}
                      </div>
                    </div>
                    <span className="text-base font-bold text-gray-900">{dualProgress.production.percentage}%</span>
                  </div>
                  <div className="w-full bg-gray-200 rounded-full h-2 overflow-hidden">
                    <div
                      className={`h-full transition-all duration-300 ease-out ${
                        dualProgress.production.status === 'completed' ? 'bg-green-600' :
                        dualProgress.production.status === 'failed' ? 'bg-red-600' : 'bg-blue-600'
                      }`}
                      style={{ width: `${dualProgress.production.percentage}%` }}
                    />
                  </div>
                  {dualProgress.production.status === 'completed' && dualProgress.production.result && (
                    <div className="bg-white border border-gray-200 rounded p-3 text-xs text-gray-600">
                      <p>Table: <strong>{dualProgress.production.result.table_name}</strong></p>
                      <p>Rows: <strong>{dualProgress.production.result.rows_verified?.toLocaleString()}</strong></p>
                    </div>
                  )}
                </div>
              )}

              {/* Grey Separator Line */}
              {dualProgress.production && dualProgress.audit && (
                <div className="border-t border-gray-300 my-4"></div>
              )}

              {/* Audit Delivery Progress */}
              {dualProgress.audit && (
                <div className="space-y-3">
                  <div className="flex items-center space-x-2">
                    <h3 className="text-sm font-semibold text-gray-700">Audit Delivery (LPT Account)</h3>
                    <div className="relative group">
                      <MdInfo className="w-4 h-4 text-gray-400 cursor-help" />
                      <div className="absolute left-full top-1/2 -translate-y-1/2 ml-2 hidden group-hover:block w-80 p-3 bg-white border border-gray-300 text-gray-700 text-xs rounded-lg shadow-lg z-[9999] pointer-events-none">
                        <div className="absolute right-full top-1/2 -translate-y-1/2 border-8 border-transparent border-r-white mr-[-1px]"></div>
                        <div className="font-semibold text-gray-900 mb-1">Fixed Header Format:</div>
                        <div className="text-gray-600">Md5hash|Subject|Creative|del_date|open_date|click_date|unsub_date|delivered|Segment|D_B_Segment|FILE_NAME</div>
                      </div>
                    </div>
                  </div>
                  <div className="flex items-center justify-between">
                    <div className="flex items-center space-x-3">
                      {dualProgress.audit.status !== 'completed' && (
                        dualProgress.audit.status === 'failed' ? <MdError className="w-6 h-6 text-red-600" /> :
                        dualProgress.audit.status === 'running' || dualProgress.audit.status === 'pending' ?
                        <div className="w-6 h-6 border-4 border-purple-600 border-t-transparent rounded-full animate-spin" /> : null
                      )}
                      <div>
                        <p className="text-sm text-gray-900">
                          {dualProgress.audit.status === 'completed' ? 'Completed' :
                           dualProgress.audit.status === 'failed' ? 'Failed' : 'Uploading...'}
                        </p>
                        {dualProgress.audit.substep && dualProgress.audit.status !== 'completed' && (
                          <p className="text-xs text-gray-600">{dualProgress.audit.substep}</p>
                        )}
                      </div>
                    </div>
                    <span className="text-base font-bold text-gray-900">{dualProgress.audit.percentage}%</span>
                  </div>
                  <div className="w-full bg-gray-200 rounded-full h-2 overflow-hidden">
                    <div
                      className={`h-full transition-all duration-300 ease-out ${
                        dualProgress.audit.status === 'completed' ? 'bg-green-600' :
                        dualProgress.audit.status === 'failed' ? 'bg-red-600' : 'bg-purple-600'
                      }`}
                      style={{ width: `${dualProgress.audit.percentage}%` }}
                    />
                  </div>
                  {dualProgress.audit.status === 'completed' && dualProgress.audit.result && (
                    <div className="bg-white border border-gray-200 rounded p-3 text-xs text-gray-600">
                      <p>Files: <strong>{dualProgress.audit.result.files_uploaded}</strong></p>
                      <p>Total Rows: <strong>{dualProgress.audit.result.total_rows?.toLocaleString()}</strong></p>
                      <p>Tables: <strong>{dualProgress.audit.result.tables}</strong></p>
                    </div>
                  )}
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
            <>
              {/* Production Re-upload Button - Always show after completion */}
              {dualProgress.production && (
                <button
                  onClick={() => handleReuploadClick('production')}
                  className={`px-3 py-2 text-sm font-medium rounded transition-colors flex items-center space-x-2 ${
                    dualProgress.production.status === 'failed'
                      ? 'bg-red-500 hover:bg-red-600 text-white'
                      : 'bg-blue-500 hover:bg-blue-600 text-white'
                  }`}
                  title={
                    dualProgress.production.status === 'failed'
                      ? 'Re-upload to Production Snowflake (Failed)'
                      : 'Re-upload to Production Snowflake'
                  }
                >
                  <MdRefresh className="h-4 w-4" />
                  <span>Re-upload Production</span>
                </button>
              )}

              {/* Audit Re-upload Button */}
              {dualProgress.audit && (
                <button
                  onClick={() => handleReuploadClick('audit')}
                  className={`px-3 py-2 text-sm font-medium rounded transition-colors flex items-center space-x-2 ${
                    dualProgress.audit.status === 'failed'
                      ? 'bg-red-500 hover:bg-red-600 text-white'
                      : 'bg-purple-500 hover:bg-purple-600 text-white'
                  }`}
                  title={
                    dualProgress.audit.status === 'failed'
                      ? 'Re-upload to Audit LPT Snowflake (Failed)'
                      : 'Re-upload to Audit LPT Snowflake'
                  }
                >
                  <MdRefresh className="h-4 w-4" />
                  <span>Re-upload Audit</span>
                </button>
              )}

              {/* Both Re-upload Button - Show when both deliveries exist */}
              {dualProgress.production && dualProgress.audit && (
                <button
                  onClick={() => handleReuploadClick('both')}
                  className={`px-3 py-2 text-sm font-medium rounded transition-colors flex items-center space-x-2 ${
                    dualProgress.production.status === 'failed' && dualProgress.audit.status === 'failed'
                      ? 'bg-orange-500 hover:bg-orange-600 text-white'
                      : 'bg-gray-500 hover:bg-gray-600 text-white'
                  }`}
                  title="Re-upload to Both Snowflake Accounts"
                >
                  <MdRefresh className="h-4 w-4" />
                  <span>Re-upload Both</span>
                </button>
              )}
            </>
          )}

          {!dualProgress.production && !dualProgress.audit && (
            <button
              onClick={() => startUpload('both')}
              disabled={uploading || loading || (headerType === 'custom' && selectedCustomColumns.length === 0)}
              className={`px-4 py-2 text-sm font-medium text-white border border-transparent rounded flex items-center space-x-2 transition-all duration-200 ${
                uploading || loading || (headerType === 'custom' && selectedCustomColumns.length === 0)
                  ? 'bg-gray-400 cursor-not-allowed'
                  : 'bg-blue-600 hover:bg-blue-700 hover:shadow-md'
              }`}
              title={dualUploadToggle ? "Upload data to Both Snowflake Accounts" : "Upload data to Production Snowflake"}
            >
              <MdCloudUpload className="h-5 w-5" />
              <span>{dualUploadToggle ? 'Start Dual Upload' : 'Start Upload'}</span>
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
