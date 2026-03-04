import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { requestService } from '../services/requestService';
import { MdCancel, MdVisibility, MdBarChart, MdCloudUpload, MdEdit } from 'react-icons/md';
import RequestStatsModal from '../components/RequestStatsModal';
import MetricsModal from '../components/MetricsModal';
import SnowflakeUploadModal from '../components/SnowflakeUploadModal';

// Custom Alert Modal Component
const AlertModal: React.FC<{
  isOpen: boolean;
  onClose: () => void;
  title: string;
  message: string;
  type?: 'info' | 'success' | 'error' | 'warning';
}> = ({
  isOpen,
  onClose,
  title,
  message,
  type = 'info'
}) => {
  if (!isOpen) return null;

  const getTypeStyles = () => {
    switch (type) {
      case 'success':
        return {
          icon: '✅',
          titleColor: 'text-green-800',
          bgColor: 'bg-green-50',
          borderColor: 'border-green-200'
        };
      case 'error':
        return {
          icon: '❌',
          titleColor: 'text-red-800',
          bgColor: 'bg-red-50',
          borderColor: 'border-red-200'
        };
      case 'warning':
        return {
          icon: '⚠️',
          titleColor: 'text-yellow-800',
          bgColor: 'bg-yellow-50',
          borderColor: 'border-yellow-200'
        };
      default:
        return {
          icon: 'ℹ️',
          titleColor: 'text-blue-800',
          bgColor: 'bg-blue-50',
          borderColor: 'border-blue-200'
        };
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

// Fixed Tooltip Component with proper z-index and positioning
const Tooltip: React.FC<{ children: React.ReactNode; content: string }> = ({
  children,
  content
}) => {
  const [isVisible, setIsVisible] = useState(false);

  if (!content || content === '-' || content.trim() === '') {
    return <div className="w-full text-left truncate">{children}</div>;
  }

  return (
    <div className="relative w-full text-left">
      <div
        className="truncate cursor-pointer"
        onMouseEnter={() => setIsVisible(true)}
        onMouseLeave={() => setIsVisible(false)}
      >
        {children}
      </div>

      {/* Tooltip with very high z-index and fixed positioning */}
      {isVisible && (
        <div
          className="fixed px-3 py-2 text-xs bg-gray-900 text-white rounded shadow-xl whitespace-nowrap pointer-events-none"
          style={{
            zIndex: 99999,
            transform: 'translate(-50%, -100%)',
            top: '50%',
            left: '50%',
            maxWidth: '400px',
            wordWrap: 'break-word',
            whiteSpace: 'normal'
          }}
        >
          {content}
        </div>
      )}
    </div>
  );
};

// Simple cell with tooltip
const TableCell: React.FC<{ content: string; className?: string }> = ({
  content,
  className = ""
}) => {
  return (
    <Tooltip content={content}>
      <div className={`truncate ${className}`}>
        {content}
      </div>
    </Tooltip>
  );
};

// Custom Confirmation Modal Component
const ConfirmationModal: React.FC<{
  isOpen: boolean;
  onClose: () => void;
  onConfirm: () => void;
  title: string;
  message: string;
  confirmText?: string;
  cancelText?: string;
  confirmColor?: string;
}> = ({
  isOpen,
  onClose,
  onConfirm,
  title,
  message,
  confirmText = "Confirm",
  cancelText = "Cancel",
  confirmColor = "bg-blue-600 hover:bg-blue-700"
}) => {
  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div className="bg-white rounded-lg p-6 max-w-md w-full mx-4">
        <h3 className="text-lg font-semibold text-gray-900 mb-2">{title}</h3>
        <p className="text-gray-600 mb-6">{message}</p>
        <div className="flex justify-end space-x-3">
          <button
            onClick={onClose}
            className="px-4 py-2 text-gray-600 border border-gray-300 rounded-lg hover:bg-gray-50 transition-colors"
          >
            {cancelText}
          </button>
          <button
            onClick={() => {
              onConfirm();
              onClose();
            }}
            className={`px-4 py-2 text-white rounded-lg transition-colors ${confirmColor}`}
          >
            {confirmText}
          </button>
        </div>
      </div>
    </div>
  );
};

// Request interface based on database table structure
interface Request {
  request_id: number;
  client_name: string;
  week: string;
  added_by: string;
  trt_count: number;
  request_status: string; // W, R, E, C, RE, N
  request_desc: string;
  execution_time: string;
  request_validation?: string | null; // Y, N, V (Yes, No, Validating)
  sf_upload_status?: string | null; // NULL, 'success', 'failed'
  sf_table_name?: string | null;
  sf_upload_time?: string | null;
}

// Status badge component with clean styling and validation awareness
const StatusBadge: React.FC<{ status: string; validation?: string | null }> = ({ status, validation }) => {
  const getStatusDisplay = (status: string, validation?: string | null) => {
    // If status is 'W' (Waiting) but validation is 'N' (No/Failed), show error
    if (status === 'W' && validation === 'N') {
      return { text: 'Error', className: 'bg-red-100 text-red-800 border-red-300 font-semibold' };
    }

    // If status is 'W' and validation is 'V' (Validating), show validating status
    if (status === 'W' && validation === 'V') {
      return { text: 'Validating', className: 'bg-purple-100 text-purple-800 border-purple-200 animate-pulse' };
    }

    switch (status) {
      case 'W':
        return { text: 'Waiting', className: 'bg-yellow-100 text-yellow-800 border-yellow-200' };
      case 'R':
        return { text: 'Running', className: 'bg-blue-100 text-blue-800 border-blue-200' };
      case 'E':
        return { text: 'Error', className: 'bg-red-100 text-red-800 border-red-200' };
      case 'C':
        return { text: 'Completed', className: 'bg-green-100 text-green-800 border-green-200' };
      case 'RE':
        return { text: 'ReRequested', className: 'bg-orange-100 text-orange-800 border-orange-200' };
      case 'P':
        return { text: 'Pending', className: 'bg-gray-100 text-gray-800 border-gray-200' };
      default:
        return { text: status || 'Unknown', className: 'bg-gray-100 text-gray-800 border-gray-200' };
    }
  };

  const { text, className } = getStatusDisplay(status, validation);

  return (
    <span className={`px-2 py-1 text-xs font-medium rounded-md border ${className}`}>
      {text}
    </span>
  );
};

// Individual button components
const KillButton: React.FC<{ request: Request; onAction: () => void; onAlert: (title: string, message: string, type?: 'info' | 'success' | 'error' | 'warning') => void }> = ({ request, onAction, onAlert }) => {
  const [isProcessing, setIsProcessing] = useState(false);
  const [showConfirm, setShowConfirm] = useState(false);
  const [lastCancelFailed, setLastCancelFailed] = useState(false);

  // Show for Waiting (W), Running (R) status OR if last cancellation attempt failed
  if (!['W', 'R'].includes(request.request_status) && !lastCancelFailed) {
    return <span></span>;
  }

  const handleKill = async () => {
    setIsProcessing(true);
    setShowConfirm(false);
    setLastCancelFailed(false); // Reset failure state

    try {
      const response = await requestService.killRequest(request.request_id);

      if (response.success) {
        // Successful cancellation
        onAlert('Success', `Request ${request.request_id} has been cancelled successfully`, 'success');
        setLastCancelFailed(false);
        onAction(); // This will refresh the data and hide the button
      } else {
        // Cancellation failed but API returned success: false
        console.error('Cancel request failed:', response.error);
        setLastCancelFailed(true); // Keep button available for retry

        const errorMessage = response.error || 'Failed to cancel request. Please try again.';
        onAlert(
          'Cancellation Failed',
          `${errorMessage}\n\nThe cancel button will remain available for retry.`,
          'error'
        );
      }
    } catch (error: any) {
      // Network error or other exception
      console.error('Cancel request failed:', error);
      setLastCancelFailed(true); // Keep button available for retry

      let errorMessage = 'Failed to cancel request. Please try again.';
      if (error.response?.data?.error) {
        errorMessage = error.response.data.error;
      } else if (error.message) {
        errorMessage = error.message;
      }

      onAlert(
        'Cancellation Error',
        `${errorMessage}\n\nThe cancel button will remain available for retry.`,
        'error'
      );
    } finally {
      setIsProcessing(false);
    }
  };

  // Button styling - different appearance if last attempt failed
  const buttonClass = lastCancelFailed
    ? "text-orange-600 hover:text-orange-800 transition-colors disabled:opacity-50 p-1.5 border border-orange-300 rounded hover:bg-orange-50"
    : "text-red-600 hover:text-red-800 transition-colors disabled:opacity-50 p-1.5 rounded hover:bg-red-50";

  const buttonTitle = lastCancelFailed
    ? "Retry Cancel Request (Previous attempt failed)"
    : "Cancel Request";

  return (
    <>
      <button
        onClick={() => setShowConfirm(true)}
        disabled={isProcessing}
        className={buttonClass}
        title={buttonTitle}
      >
        <MdCancel className="w-5 h-5" />
      </button>

      {/* Confirmation Dialog */}
      {showConfirm && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg shadow-xl p-6 max-w-md w-full mx-4">
            <h3 className="text-lg font-semibold text-gray-900 mb-4">
              {lastCancelFailed ? 'Retry Cancellation' : 'Confirm Cancellation'}
            </h3>
            <p className="text-gray-600 mb-6">
              {lastCancelFailed && (
                <span className="text-orange-600 font-medium block mb-2">
                  ⚠️ Previous cancellation attempt failed.
                </span>
              )}
              Are you sure you want to {lastCancelFailed ? 'retry cancelling' : 'cancel'} request{' '}
              <span className="font-semibold text-gray-900">#{request.request_id}</span>?
              {lastCancelFailed && (
                <>
                  <br />
                  <span className="text-sm text-gray-500 mt-2 block">
                    This will attempt to terminate any remaining processes.
                  </span>
                </>
              )}
            </p>
            <div className="flex justify-end space-x-3">
              <button
                onClick={() => setShowConfirm(false)}
                className="px-4 py-2 bg-gray-200 text-gray-700 rounded-lg hover:bg-gray-300 transition-colors font-medium"
              >
                No
              </button>
              <button
                onClick={handleKill}
                disabled={isProcessing}
                className={`px-4 py-2 text-white rounded-lg transition-colors font-medium disabled:opacity-50 ${
                  lastCancelFailed
                    ? 'bg-orange-600 hover:bg-orange-700'
                    : 'bg-red-600 hover:bg-red-700'
                }`}
              >
                {isProcessing ? 'Cancelling...' : (lastCancelFailed ? 'Yes, Retry' : 'Yes, Cancel')}
              </button>
            </div>
          </div>
        </div>
      )}
    </>
  );
};

const EditButton: React.FC<{ request: Request }> = ({ request }) => {
  const navigate = useNavigate();
  const [isLoading, setIsLoading] = useState(false);

  // Show for:
  // - Cancelled/Killed (E) or Completed (C) status
  // - Validation Failed: status is W/RE/RW and validation='N'
  //   (requestPicker picks W, RE, and RW requests for validation, so any can fail)
  const isValidationFailed = ['W', 'RE', 'RW'].includes(request.request_status) && request.request_validation === 'N';
  const canEdit = ['E', 'C'].includes(request.request_status) || isValidationFailed;

  if (!canEdit) {
    return <span></span>;
  }

  const handleEdit = async () => {
    setIsLoading(true);
    try {
      console.log('🔍 Fetching detailed request data for request ID:', request.request_id);

      // Fetch detailed request data from backend
      const detailedData = await requestService.getRequestDetails(request.request_id);
      console.log('📋 Detailed data received:', detailedData);

      // detailedData = { success: true, request: { ... all fields ... } }
      // Spread the nested request object so all fields are at top level
      const requestFromApi = (detailedData.success && detailedData.request) ? detailedData.request : {};

      // Combine basic request data with detailed data (detailed overrides basic)
      const combinedData = {
        // Basic info from current request (fallback if API missing)
        request_id: request.request_id,
        client_name: request.client_name,
        week: request.week,
        added_by: request.added_by,
        trt_count: request.trt_count,
        request_status: request.request_status,
        request_desc: request.request_desc,
        execution_time: request.execution_time,
        // Full detail from API (overrides basic data with proper field names)
        ...requestFromApi
      };

      console.log('🔧 Combined data for edit mode:', combinedData);

      // Navigate to Add Request page with complete detailed data
      navigate('/add-request', {
        state: {
          editMode: true,
          requestData: combinedData
        }
      });

    } catch (error) {
      console.error('❌ Failed to fetch request details:', error);
      console.log('⚠️ Using fallback - navigating with basic request data only');

      // Fallback - navigate with basic data
      navigate('/add-request', {
        state: {
          editMode: true,
          requestData: {
            request_id: request.request_id,
            client_name: request.client_name,
            week: request.week,
            added_by: request.added_by,
            trt_count: request.trt_count,
            request_status: request.request_status,
            request_desc: request.request_desc,
            execution_time: request.execution_time
          }
        }
      });
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <button
      onClick={handleEdit}
      disabled={isLoading}
      className="text-green-600 hover:text-green-800 transition-colors disabled:opacity-50 p-1.5 rounded hover:bg-green-50"
      title={isLoading ? "Loading request details..." : "Edit Request"}
    >
      {isLoading ? (
        <div className="w-5 h-5 border-2 border-green-600 border-t-transparent rounded-full animate-spin"></div>
      ) : (
        <MdEdit className="w-5 h-5" />
      )}
    </button>
  );
};


const ViewButton: React.FC<{ request: Request; onAlert: (title: string, message: string, type?: 'info' | 'success' | 'error' | 'warning') => void }> = ({ request, onAlert }) => {
  const [showStatsModal, setShowStatsModal] = useState(false);

  // Only show for Completed status (matching LogStreamr logic)
  if (request.request_status !== 'C') {
    return <span></span>;
  }

  const handleView = () => {
    setShowStatsModal(true);
  };

  return (
    <>
      <button
        onClick={handleView}
        className="text-gray-600 hover:text-gray-800 transition-colors p-1.5 rounded hover:bg-gray-100"
        title="View Statistics"
      >
        <MdVisibility className="w-5 h-5" />
      </button>

      <RequestStatsModal
        isOpen={showStatsModal}
        onClose={() => setShowStatsModal(false)}
        requestId={request.request_id}
      />
    </>
  );
};

const MetricsButton: React.FC<{ request: Request; onAlert: (title: string, message: string, type?: 'info' | 'success' | 'error' | 'warning') => void }> = ({ request, onAlert }) => {
  const [showModal, setShowModal] = useState(false);
  const [clientName, setClientName] = useState<string>('');
  const [week, setWeek] = useState<string>('');
  const [loading, setLoading] = useState(false);

  // Only show for Completed status
  if (request.request_status !== 'C') {
    return <span></span>;
  }

  const handleMetrics = async () => {
    if (!clientName || !week) {
      setLoading(true);
      try {
        // Fetch client name and week using the same queries as in config.properties
        const clientResponse = await requestService.getClientName(request.request_id);
        const weekResponse = await requestService.getWeek(request.request_id);

        if (clientResponse.success && weekResponse.success) {
          setClientName(clientResponse.clientName || '');
          setWeek(weekResponse.week || '');
        } else {
          onAlert('Error', 'Failed to fetch request details for metrics', 'error');
          return;
        }
      } catch (error) {
        console.error('Failed to fetch request details:', error);
        onAlert('Error', 'Failed to fetch request details for metrics', 'error');
        return;
      } finally {
        setLoading(false);
      }
    }
    setShowModal(true);
  };

  return (
    <>
      <button
        onClick={handleMetrics}
        disabled={loading}
        className="text-green-600 hover:text-green-800 transition-colors disabled:opacity-50 p-1.5 rounded hover:bg-green-50 relative"
        title="Download Metrics"
      >
        {loading ? (
          <div className="animate-spin rounded-full h-5 w-5 border-2 border-green-600 border-t-transparent"></div>
        ) : (
          <MdBarChart className="w-5 h-5" />
        )}
      </button>

      <MetricsModal
        isOpen={showModal}
        onClose={() => setShowModal(false)}
        requestId={request.request_id}
        clientName={clientName}
        week={week}
      />
    </>
  );
};

const UploadButton: React.FC<{ request: Request; onAction: () => void; onAlert: (title: string, message: string, type?: 'info' | 'success' | 'error' | 'warning') => void }> = ({ request, onAction, onAlert }) => {
  const [showUploadModal, setShowUploadModal] = useState(false);

  // Only show for Completed status
  if (request.request_status !== 'C') {
    return <span></span>;
  }

  // Get upload status from request object (already loaded from DB)
  const uploadStatus = request.sf_upload_status === 'success' ? 'success'
    : request.sf_upload_status === 'failed' ? 'error'
    : 'idle';

  const handleUploadClick = () => {
    setShowUploadModal(true);
  };

  const handleModalClose = () => {
    setShowUploadModal(false);
    // Trigger parent refresh to update status
    onAction();
  };

  const getButtonColor = () => {
    switch (uploadStatus) {
      case 'success':
        return 'text-green-600 hover:text-green-800 hover:bg-green-50';
      case 'error':
        return 'text-red-600 hover:text-red-800 hover:bg-red-50';
      default:
        return 'text-blue-600 hover:text-blue-800 hover:bg-blue-50';
    }
  };

  return (
    <>
      <button
        onClick={handleUploadClick}
        className={`${getButtonColor()} transition-colors p-1.5 rounded`}
        title="Upload to Snowflake"
      >
        <MdCloudUpload className="w-5 h-5" />
      </button>

      <SnowflakeUploadModal
        isOpen={showUploadModal}
        onClose={handleModalClose}
        requestId={request.request_id}
        clientName={request.client_name}
        week={request.week}
      />
    </>
  );
};

const RequestLogs: React.FC = () => {
  const navigate = useNavigate();
  // allRequests holds the full dataset fetched from backend (up to monitorMaxRecords)
  const [allRequests, setAllRequests] = useState<Request[]>([]);
  const [loading, setLoading] = useState(true);
  const [searchTerm, setSearchTerm] = useState('');
  const [currentPage, setCurrentPage] = useState(1);
  const [refreshing, setRefreshing] = useState(false);

  // Alert state
  const [alertState, setAlertState] = useState({
    isOpen: false,
    title: '',
    message: '',
    type: 'info' as 'info' | 'success' | 'error' | 'warning'
  });

  const showAlert = (title: string, message: string, type: 'info' | 'success' | 'error' | 'warning' = 'info') => {
    setAlertState({
      isOpen: true,
      title,
      message,
      type
    });
  };

  const closeAlert = () => {
    setAlertState(prev => ({ ...prev, isOpen: false }));
  };

  const requestsPerPage = 50;
  const searchTimeoutRef = React.useRef<ReturnType<typeof setTimeout> | null>(null);
  // Ref so the auto-refresh interval always sees the latest search term
  const searchTermRef = React.useRef(searchTerm);
  React.useEffect(() => { searchTermRef.current = searchTerm; }, [searchTerm]);

  // Pagination over whatever the backend returned (no client-side filtering)
  const totalPages = Math.max(1, Math.ceil(allRequests.length / requestsPerPage));
  const displayRequests = allRequests.slice(
    (currentPage - 1) * requestsPerPage,
    currentPage * requestsPerPage
  );

  // Load requests from API — passes search term to backend when present
  const loadRequests = async (search: string = '') => {
    try {
      setRefreshing(true);
      console.log('🔄 Loading requests from backend API...');

      // When searching, raise the limit so the backend scans the full table
      const params = search.trim()
        ? { limit: 500, search: search.trim() }
        : { limit: 200 };
      const data = await requestService.getRequests(params);

      console.log('✅ Data received from backend:', data);
      setAllRequests(data.requests || []);

    } catch (error) {
      console.error('❌ Failed to load requests from backend:', error);
      console.warn('⚠️ Using fallback sample data for development');

      const fallbackData = [
        {
          request_id: 6589,
          client_name: 'Ikea',
          week: 'Q4_W8',
          added_by: 'RAJASREE',
          trt_count: 0,
          request_status: 'R',
          request_desc: 'Preparing Source.',
          execution_time: '-'
        },
        {
          request_id: 6588,
          client_name: 'TestClient',
          week: 'Q4_W7',
          added_by: 'AKHAN',
          trt_count: 250,
          request_status: 'C',
          request_desc: 'Process completed successfully.',
          execution_time: '01:23:45'
        },
        {
          request_id: 6587,
          client_name: 'Aroma',
          week: 'Q4_W6',
          added_by: 'VNAMMI',
          trt_count: 75,
          request_status: 'E',
          request_desc: 'Error occurred during processing.',
          execution_time: '00:45:30'
        }
      ];

      setAllRequests(fallbackData);
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  // Initial load
  useEffect(() => {
    loadRequests();
  }, []);

  // Auto-refresh every 30 seconds — uses ref to pick up latest search term without re-registering
  useEffect(() => {
    const interval = setInterval(() => {
      loadRequests(searchTermRef.current.trim());
    }, 30000);
    return () => clearInterval(interval);
  }, []);

  // Handle search — debounce the API call so it fires 400 ms after the user stops typing
  const handleSearch = (e: React.ChangeEvent<HTMLInputElement>) => {
    const value = e.target.value;
    setSearchTerm(value);
    setCurrentPage(1);
    if (searchTimeoutRef.current) clearTimeout(searchTimeoutRef.current);
    searchTimeoutRef.current = setTimeout(() => {
      loadRequests(value.trim());
    }, 400);
  };

  // Handle manual refresh — preserve current search term
  const handleRefresh = () => {
    loadRequests(searchTerm.trim());
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-gray-50 to-gray-100 flex items-center justify-center">
        <div className="bg-white rounded-lg shadow-lg p-12 text-center">
          <div className="w-16 h-16 border-4 border-gray-200 border-t-gray-600 rounded-full animate-spin mx-auto mb-6"></div>
          <h2 className="text-2xl font-semibold text-gray-800 mb-3">Loading Requests</h2>
          <p className="text-gray-600">Please wait...</p>
        </div>
      </div>
    );
  }

  return (
    <>
      {/* Search Controls - Fixed at top */}
      <div className="flex-shrink-0 bg-white border-b border-gray-200 py-3">
        <div className="flex justify-end items-center space-x-3 pr-4">
          <input
            type="text"
            placeholder="Search by Request ID, Client, or User..."
            value={searchTerm}
            onChange={handleSearch}
            className="w-80 px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 text-sm"
          />
          <button
            onClick={handleRefresh}
            disabled={refreshing}
            className="p-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors disabled:opacity-50 text-sm"
            title={refreshing ? 'Refreshing...' : 'Refresh'}
          >
            {refreshing ? (
              <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin"></div>
            ) : (
              <span>↻</span>
            )}
          </button>
        </div>
      </div>

      {/* Table Container - Scrollable middle section */}
      <div className="overflow-auto bg-white relative" style={{ height: 'calc(100vh - 220px)' }}>
        <table className="w-full border-collapse table-fixed">
          <thead className="bg-gradient-to-r from-blue-50 to-indigo-100 sticky top-0 z-10">
            <tr>
              <th className="w-20 px-2 py-2 text-left text-xs font-bold text-gray-800 border-b-2 border-blue-200" style={{ whiteSpace: 'nowrap' }}>
                Request ID
              </th>
              <th className="w-32 px-2 py-2 text-left text-xs font-bold text-gray-800 border-b-2 border-blue-200" style={{ whiteSpace: 'nowrap' }}>
                Client Name
              </th>
              <th className="w-16 px-2 py-2 text-left text-xs font-bold text-gray-800 border-b-2 border-blue-200" style={{ whiteSpace: 'nowrap' }}>
                Week
              </th>
              <th className="w-20 px-2 py-2 text-left text-xs font-bold text-gray-800 border-b-2 border-blue-200" style={{ whiteSpace: 'nowrap' }}>
                User
              </th>
              <th className="w-20 px-2 py-2 text-left text-xs font-bold text-gray-800 border-b-2 border-blue-200" style={{ whiteSpace: 'nowrap' }}>
                TRT Count
              </th>
              <th className="w-20 px-2 py-2 text-left text-xs font-bold text-gray-800 border-b-2 border-blue-200" style={{ whiteSpace: 'nowrap' }}>
                Status
              </th>
              <th className="w-40 px-2 py-2 text-left text-xs font-bold text-gray-800 border-b-2 border-blue-200" style={{ whiteSpace: 'nowrap' }}>
                Description
              </th>
              <th className="w-20 px-2 py-2 text-left text-xs font-bold text-gray-800 border-b-2 border-blue-200" style={{ whiteSpace: 'nowrap' }}>
                Exec Time
              </th>
              <th className="w-40 px-2 py-2 text-left text-xs font-bold text-gray-800 border-b-2 border-blue-200" style={{ whiteSpace: 'nowrap' }}>
                Actions
              </th>
            </tr>
          </thead>
          <tbody className="bg-white">
            {displayRequests.map((request) => (
              <tr key={request.request_id} className="hover:bg-blue-25 transition-colors">
                <td className="w-20 px-2 py-2 text-sm font-medium text-gray-900 border-b border-gray-100 align-middle overflow-hidden">
                  <TableCell content={request.request_id.toString()} />
                </td>
                <td className="w-32 px-2 py-2 text-sm text-gray-700 border-b border-gray-100 align-middle overflow-hidden">
                  <TableCell content={request.client_name} />
                </td>
                <td className="w-16 px-2 py-2 text-sm text-gray-700 border-b border-gray-100 align-middle overflow-hidden">
                  <TableCell content={request.week} />
                </td>
                <td className="w-20 px-2 py-2 text-sm text-gray-700 border-b border-gray-100 align-middle overflow-hidden">
                  <TableCell content={request.added_by} />
                </td>
                <td className="w-20 px-2 py-2 text-sm text-gray-700 border-b border-gray-100 align-middle overflow-hidden">
                  <TableCell content={request.trt_count ? request.trt_count.toLocaleString() : '-'} />
                </td>
                <td className="w-20 px-2 py-2 border-b border-gray-100 align-middle overflow-hidden">
                  <div className="text-left">
                    <StatusBadge status={request.request_status} validation={request.request_validation} />
                  </div>
                </td>
                <td className="w-40 px-2 py-2 text-sm text-gray-700 border-b border-gray-100 align-middle overflow-hidden">
                  <TableCell content={request.request_desc} />
                </td>
                <td className="w-20 px-2 py-2 text-sm text-gray-700 border-b border-gray-100 align-middle overflow-hidden">
                  <TableCell content={request.execution_time || '-'} />
                </td>
                <td className="w-40 px-2 py-2 border-b border-gray-100 align-middle overflow-hidden">
                  <div className="flex items-center justify-start space-x-1">
                    <KillButton request={request} onAction={loadRequests} onAlert={showAlert} />
                    <EditButton request={request} />
                    <ViewButton request={request} onAlert={showAlert} />
                    <MetricsButton request={request} onAlert={showAlert} />
                    <UploadButton request={request} onAction={loadRequests} onAlert={showAlert} />
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Pagination - Fixed at bottom */}
      <div className="flex-shrink-0 bg-white px-2 py-3 border-t border-gray-200">
        <div className="flex items-center justify-between">
          <div className="text-sm text-gray-700">
            {`${allRequests.length} requests · page ${currentPage} of ${totalPages}`}
          </div>
          <div className="flex items-center space-x-2">
            <button
              onClick={() => setCurrentPage(Math.max(1, currentPage - 1))}
              disabled={currentPage === 1}
              className="px-3 py-1 border border-gray-300 text-sm rounded hover:bg-gray-50 disabled:opacity-50"
            >
              Previous
            </button>
            <span className="px-3 py-1 text-sm">
              {currentPage} / {totalPages}
            </span>
            <button
              onClick={() => setCurrentPage(Math.min(totalPages, currentPage + 1))}
              disabled={currentPage === totalPages}
              className="px-3 py-1 border border-gray-300 text-sm rounded hover:bg-gray-50 disabled:opacity-50"
            >
              Next
            </button>
          </div>
        </div>
      </div>

      {/* Auto-refresh indicator - Fixed at very bottom */}
      <div className="flex-shrink-0 bg-gray-50 text-center text-sm text-gray-500 py-2">
        Auto-refresh every 30 seconds • Last updated: {new Date().toLocaleTimeString()} • {allRequests.length} requests shown
      </div>

      {/* Custom Alert Modal */}
      <AlertModal
        isOpen={alertState.isOpen}
        onClose={closeAlert}
        title={alertState.title}
        message={alertState.message}
        type={alertState.type}
      />
    </>
  );
};

export default RequestLogs;
