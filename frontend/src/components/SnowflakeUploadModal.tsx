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
      restorePreviousUploadState();
    } else {
      // Clean up when modal closes
      if (pollIntervalRef.current) {
        clearInterval(pollIntervalRef.current);
      }
    }
  }, [isOpen]);

  const restorePreviousUploadState = async () => {
    try {
      const response = await fetch(`/api/snowflake/upload-status/${requestId}`);
      const data = await response.json();

      if (!data.success || !data.upload_status) return;

      const { status, table_name, audit_status } = data.upload_status;

      // Only restore if at least one upload has been attempted
      if (!status && !audit_status) return;

      const restoredProgress: DualUploadProgress = {
        production: status ? {
          task_id: `restored_prod_${requestId}`,
          status: status === 'success' ? 'completed' : 'failed',
          percentage: 100,
          result: status === 'success' ? { table_name: table_name || undefined } : undefined,
          error: status === 'failed' ? 'Previous upload failed' : undefined
        } : null,
        audit: audit_status ? {
          task_id: `restored_audit_${requestId}`,
          status: audit_status === 'success' ? 'completed' : 'failed',
          percentage: 100,
          result: audit_status === 'success' ? { tables: 'Previously uploaded to LPT' } : undefined,
          error: audit_status === 'failed' ? 'Previous audit upload failed' : undefined
        } : null
      };

      setDualProgress(restoredProgress);
      setCanReupload(true);
    } catch (err) {
      console.error('Error restoring upload state:', err);
    }
  };

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

  const startUpload = async (uploadType: 'production' | 'audit' | 'both' = 'both', isReupload: boolean = false) => {
    setUploading(true);
    setError(null);
    setCanReupload(false);

    // If dual upload toggle is OFF, force production only — but only for initial uploads from the form.
    // Re-upload actions must always respect the explicitly specified type.
    const effectiveUploadType = (!dualUploadToggle && !isReupload) ? 'production' : uploadType;

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

        // Poll production progress (skip restored placeholder IDs — they don't exist on the backend)
        if (dualProgress.production?.task_id && !dualProgress.production.task_id.startsWith('restored_')) {
          const prodResponse = await fetch(`/api/snowflake/progress/${dualProgress.production.task_id}`);
          const prodData = await prodResponse.json();
          if (prodData.success) {
            updates.production = prodData.task;
          }
        }

        // Poll audit progress (skip restored placeholder IDs)
        if (dualProgress.audit?.task_id && !dualProgress.audit.task_id.startsWith('restored_')) {
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
    startUpload(reuploadType, true);
  };

  const handleReuploadCancel = () => {
    setShowReuploadConfirm(false);
  };

  const getStatusIcon = () => {
    if (!uploadProgress) return null;

    switch (uploadProgress.status) {
      case 'completed':
        return <MdCheck className="w-5 h-5 text-green-600" />;
      case 'failed':
        return <MdError className="w-5 h-5 text-red-500" />;
      case 'running':
      case 'pending':
        return (
          <div className="w-5 h-5 border-2 border-blue-600 border-t-transparent rounded-full animate-spin" />
        );
      default:
        return null;
    }
  };

  const getStatusColor = () => {
    if (!uploadProgress) return 'bg-gray-200';

    switch (uploadProgress.status) {
      case 'completed':
        return 'bg-green-500';
      case 'failed':
        return 'bg-red-500';
      case 'running':
      case 'pending':
        return 'bg-blue-500';
      default:
        return 'bg-gray-200';
    }
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded shadow-xl w-full max-w-[538px] flex flex-col relative">

        {/* Header */}
        <div className="flex items-center justify-between px-4 py-3 border-b border-gray-200">
          <div className="flex items-center space-x-2">
            <FaRegSnowflake className="h-4 w-4 text-slate-600" />
            <h2 className="text-sm font-semibold text-gray-800">
              Upload to Snowflake — #{requestId}
            </h2>
          </div>
          <div className="flex items-center space-x-3">
            {/* Dual Upload Toggle */}
            {!uploading && !dualProgress.production && !dualProgress.audit && (
              <div className="flex items-center space-x-2">
                <span className="text-xs text-gray-500">Dual Upload</span>
                <button
                  onClick={() => setDualUploadToggle(!dualUploadToggle)}
                  className={`relative inline-flex h-4 w-8 items-center rounded-full transition-colors focus:outline-none ${
                    dualUploadToggle ? 'bg-slate-600' : 'bg-gray-300'
                  }`}
                  disabled={uploading}
                >
                  <span
                    className={`inline-block h-3 w-3 transform rounded-full bg-white transition-transform shadow ${
                      dualUploadToggle ? 'translate-x-4' : 'translate-x-0.5'
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
        <div className="px-4 py-3">
          <div className="space-y-3">

          {error && (
            <div className="bg-red-50 border border-red-200 rounded p-2 flex items-start space-x-2">
              <MdError className="h-4 w-4 text-red-500 mt-0.5 flex-shrink-0" />
              <p className="text-xs text-red-700">{error}</p>
            </div>
          )}

          {loading ? (
            <div className="flex items-center justify-center py-8">
              <div className="animate-spin rounded-full h-7 w-7 border-b-2 border-slate-600"></div>
              <span className="ml-3 text-sm text-gray-500">Loading table columns...</span>
            </div>
          ) : (dualProgress.production || dualProgress.audit) ? (

            /* Progress View */
            <div className="space-y-3">

              {/* Production Delivery */}
              {dualProgress.production && (
                <div className="space-y-1.5">
                  <div className="flex items-center justify-between">
                    <span className="text-xs font-semibold text-gray-600 uppercase tracking-wide">Production</span>
                    <span className="text-xs font-bold text-gray-700">{dualProgress.production.percentage}%</span>
                  </div>
                  <div className="w-full bg-gray-100 rounded-full h-1.5 overflow-hidden">
                    <div
                      className={`h-full transition-all duration-300 ease-out rounded-full ${
                        dualProgress.production.status === 'completed' ? 'bg-emerald-500' :
                        dualProgress.production.status === 'failed'    ? 'bg-red-500'     : 'bg-slate-500'
                      }`}
                      style={{ width: `${dualProgress.production.percentage}%` }}
                    />
                  </div>
                  <div className="flex items-center space-x-2">
                    {dualProgress.production.status === 'completed' && <MdCheck className="w-4 h-4 text-emerald-500" />}
                    {dualProgress.production.status === 'failed'    && <MdError className="w-4 h-4 text-red-500" />}
                    {(dualProgress.production.status === 'running' || dualProgress.production.status === 'pending') &&
                      <div className="w-4 h-4 border-2 border-slate-500 border-t-transparent rounded-full animate-spin" />}
                    <p className="text-xs text-gray-600">
                      {dualProgress.production.status === 'completed' ? 'Completed' :
                       dualProgress.production.status === 'failed'    ? 'Failed'    : 'Uploading...'}
                      {dualProgress.production.substep && dualProgress.production.status !== 'completed' &&
                        <span className="text-gray-400 ml-1">— {dualProgress.production.substep}</span>}
                    </p>
                  </div>
                  {dualProgress.production.status === 'completed' && dualProgress.production.result && (
                    <div className="bg-gray-50 border border-gray-200 rounded px-2 py-1.5 text-xs text-gray-500 flex gap-4">
                      <span>Table: <strong className="text-gray-700">{dualProgress.production.result.table_name}</strong></span>
                      {dualProgress.production.result.rows_verified &&
                        <span>Rows: <strong className="text-gray-700">{dualProgress.production.result.rows_verified.toLocaleString()}</strong></span>}
                    </div>
                  )}
                </div>
              )}

              {/* Separator */}
              {dualProgress.production && dualProgress.audit && (
                <div className="border-t border-gray-200" />
              )}

              {/* Audit Delivery */}
              {dualProgress.audit && (
                <div className="space-y-1.5">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center space-x-1">
                      <span className="text-xs font-semibold text-gray-600 uppercase tracking-wide">Audit (LPT)</span>
                      <div className="relative group">
                        <MdInfo className="w-3.5 h-3.5 text-gray-400 cursor-help" />
                        <div className="absolute left-full top-1/2 -translate-y-1/2 ml-2 hidden group-hover:block w-72 p-2.5 bg-white border border-gray-300 text-gray-700 text-xs rounded shadow-lg z-[9999] pointer-events-none">
                          <div className="absolute right-full top-1/2 -translate-y-1/2 border-4 border-transparent border-r-white mr-[-1px]"></div>
                          <span className="font-semibold text-gray-800">Fixed Header:</span>
                          <span className="ml-1 text-gray-500">Md5hash|Subject|Creative|del_date|open_date|click_date|unsub_date|delivered|Segment|D_B_Segment|FILE_NAME</span>
                        </div>
                      </div>
                    </div>
                    <span className="text-xs font-bold text-gray-700">{dualProgress.audit.percentage}%</span>
                  </div>
                  <div className="w-full bg-gray-100 rounded-full h-1.5 overflow-hidden">
                    <div
                      className={`h-full transition-all duration-300 ease-out rounded-full ${
                        dualProgress.audit.status === 'completed' ? 'bg-emerald-500' :
                        dualProgress.audit.status === 'failed'    ? 'bg-red-500'     : 'bg-indigo-500'
                      }`}
                      style={{ width: `${dualProgress.audit.percentage}%` }}
                    />
                  </div>
                  <div className="flex items-center space-x-2">
                    {dualProgress.audit.status === 'completed' && <MdCheck className="w-4 h-4 text-emerald-500" />}
                    {dualProgress.audit.status === 'failed'    && <MdError className="w-4 h-4 text-red-500" />}
                    {(dualProgress.audit.status === 'running' || dualProgress.audit.status === 'pending') &&
                      <div className="w-4 h-4 border-2 border-indigo-500 border-t-transparent rounded-full animate-spin" />}
                    <p className="text-xs text-gray-600">
                      {dualProgress.audit.status === 'completed' ? 'Completed' :
                       dualProgress.audit.status === 'failed'    ? 'Failed'    : 'Uploading...'}
                      {dualProgress.audit.substep && dualProgress.audit.status !== 'completed' &&
                        <span className="text-gray-400 ml-1">— {dualProgress.audit.substep}</span>}
                    </p>
                  </div>
                  {dualProgress.audit.status === 'completed' && dualProgress.audit.result && (
                    <div className="bg-gray-50 border border-gray-200 rounded px-2 py-1.5 text-xs text-gray-500 flex gap-4 flex-wrap">
                      {dualProgress.audit.result.files_uploaded !== undefined &&
                        <span>Files: <strong className="text-gray-700">{dualProgress.audit.result.files_uploaded}</strong></span>}
                      {dualProgress.audit.result.total_rows !== undefined &&
                        <span>Rows: <strong className="text-gray-700">{dualProgress.audit.result.total_rows.toLocaleString()}</strong></span>}
                      {dualProgress.audit.result.tables &&
                        <span>Tables: <strong className="text-gray-700">{dualProgress.audit.result.tables}</strong></span>}
                    </div>
                  )}
                </div>
              )}
            </div>

          ) : (

            /* Column Selection View */
            <div className="space-y-3">
              <div>
                <p className="text-xs font-semibold text-gray-600 uppercase tracking-wide mb-2">Header Type</p>
                <div className="flex flex-col space-y-2">
                  <label className="flex items-center cursor-pointer">
                    <input
                      type="radio"
                      value="standard"
                      checked={headerType === 'standard'}
                      onChange={() => setHeaderType('standard')}
                      className="mr-2 h-3.5 w-3.5 text-slate-600 focus:ring-slate-500 border-gray-300"
                      disabled={uploading}
                    />
                    <span className="text-sm text-gray-700">Standard Header</span>
                    <div className="relative group ml-2">
                      <MdInfo className="w-4 h-4 text-gray-400 cursor-help" />
                      <div className="absolute left-full top-1/2 -translate-y-1/2 ml-2 hidden group-hover:block w-80 p-3 bg-white border border-gray-300 text-gray-700 text-xs rounded-lg shadow-lg z-[9999] pointer-events-none">
                        <div className="absolute right-full top-1/2 -translate-y-1/2 border-6 border-transparent border-r-white mr-[-1px]"></div>
                        <span className="font-semibold text-gray-800">Columns: </span>
                        <span className="text-gray-600">Md5hash, Segment, SubSeg, Decile, DeliveredFlag, DeliveredDate, Subject, Creative, OpenDate, ClickDate, UnsubDate</span>
                      </div>
                    </div>
                  </label>
                  <label className="flex items-center cursor-pointer">
                    <input
                      type="radio"
                      value="custom"
                      checked={headerType === 'custom'}
                      onChange={() => setHeaderType('custom')}
                      className="mr-2 h-3.5 w-3.5 text-slate-600 focus:ring-slate-500 border-gray-300"
                      disabled={uploading}
                    />
                    <span className="text-sm text-gray-700">Custom Header <span className="text-gray-400 text-xs">(Standard + extra columns)</span></span>
                  </label>
                </div>
              </div>

              {/* Custom Column Selection */}
              {headerType === 'custom' && columns && (
                <div>
                  <p className="text-xs font-semibold text-gray-600 uppercase tracking-wide mb-1.5">
                    Additional Columns
                    <span className="ml-1.5 text-gray-400 font-normal normal-case">({selectedCustomColumns.length} selected)</span>
                  </p>
                  <div className="border border-gray-200 rounded p-3 bg-gray-50">
                    <div className="grid grid-cols-4 gap-2">
                      {columns.custom.map(column => (
                        <label key={column} className="flex items-center space-x-1.5 cursor-pointer">
                          <input
                            type="checkbox"
                            checked={selectedCustomColumns.includes(column)}
                            onChange={() => handleCustomColumnToggle(column)}
                            className="h-3.5 w-3.5 text-slate-600 focus:ring-slate-500 border-gray-300 rounded"
                            disabled={uploading}
                          />
                          <span className="text-xs text-gray-700">{column}</span>
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
        <div className="flex items-center justify-end space-x-2 px-4 py-3 border-t border-gray-200">
          {canReupload && (
            <>
              {/* Re-upload Production */}
              {dualProgress.production && (
                <button
                  onClick={() => handleReuploadClick('production')}
                  className={`px-3 py-1.5 text-xs font-medium rounded transition-colors flex items-center space-x-1.5 ${
                    dualProgress.production.status === 'failed'
                      ? 'bg-red-500 hover:bg-red-600 text-white'
                      : 'bg-slate-600 hover:bg-slate-700 text-white'
                  }`}
                  title={dualProgress.production.status === 'failed' ? 'Re-upload Production (failed)' : 'Re-upload Production'}
                >
                  <MdRefresh className="h-3.5 w-3.5" />
                  <span>Re-upload Prod</span>
                </button>
              )}

              {/* Re-upload Audit */}
              {dualProgress.audit && (
                <button
                  onClick={() => handleReuploadClick('audit')}
                  className={`px-3 py-1.5 text-xs font-medium rounded transition-colors flex items-center space-x-1.5 ${
                    dualProgress.audit.status === 'failed'
                      ? 'bg-red-500 hover:bg-red-600 text-white'
                      : 'bg-indigo-600 hover:bg-indigo-700 text-white'
                  }`}
                  title={dualProgress.audit.status === 'failed' ? 'Re-upload Audit (failed)' : 'Re-upload Audit'}
                >
                  <MdRefresh className="h-3.5 w-3.5" />
                  <span>Re-upload Audit</span>
                </button>
              )}

              {/* Re-upload Both */}
              {dualProgress.production && dualProgress.audit && (
                <button
                  onClick={() => handleReuploadClick('both')}
                  className="px-3 py-1.5 text-xs font-medium rounded transition-colors flex items-center space-x-1.5 bg-gray-600 hover:bg-gray-700 text-white"
                  title="Re-upload to Both"
                >
                  <MdRefresh className="h-3.5 w-3.5" />
                  <span>Re-upload Both</span>
                </button>
              )}
            </>
          )}

          {!dualProgress.production && !dualProgress.audit && (
            <button
              onClick={() => startUpload('both')}
              disabled={uploading || loading || (headerType === 'custom' && selectedCustomColumns.length === 0)}
              className={`px-4 py-1.5 text-sm font-medium text-white rounded flex items-center space-x-2 transition-all duration-200 ${
                uploading || loading || (headerType === 'custom' && selectedCustomColumns.length === 0)
                  ? 'bg-gray-300 cursor-not-allowed'
                  : 'bg-slate-700 hover:bg-slate-800 hover:shadow-sm'
              }`}
              title={dualUploadToggle ? 'Upload to Both Snowflake Accounts' : 'Upload to Production Snowflake'}
            >
              <MdCloudUpload className="h-4 w-4" />
              <span>{dualUploadToggle ? 'Start Dual Upload' : 'Start Upload'}</span>
            </button>
          )}
        </div>

        {/* Re-upload Confirmation Dialog */}
        {showReuploadConfirm && (
          <div className="absolute inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 rounded">
            <div className="bg-white rounded shadow-xl p-4 max-w-sm mx-4">
              <div className="flex items-start space-x-3">
                <MdInfo className="h-5 w-5 text-amber-500 flex-shrink-0 mt-0.5" />
                <div className="flex-1">
                  <p className="text-sm font-semibold text-gray-800 mb-1">Confirm Re-upload</p>
                  <p className="text-xs text-gray-500 mb-3">
                    This will replace existing data in the Snowflake table.
                  </p>
                  <div className="flex space-x-2 justify-end">
                    <button
                      onClick={handleReuploadCancel}
                      className="px-3 py-1.5 text-xs font-medium text-gray-600 bg-gray-100 hover:bg-gray-200 rounded transition-colors"
                    >
                      Cancel
                    </button>
                    <button
                      onClick={handleReuploadConfirm}
                      className="px-3 py-1.5 text-xs font-medium text-white bg-red-500 hover:bg-red-600 rounded transition-colors"
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
