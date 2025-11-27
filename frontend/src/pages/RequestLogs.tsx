import React, { useState, useEffect } from 'react';
import { requestService } from '../services/requestService';

// Request interface based on database table structure
interface Request {
  request_id: number;
  client_name: string;
  week: string;
  added_by: string;
  trt_count: number;
  request_status: string; // W, R, E, C, RE
  request_desc: string;
  execution_time: string;
}

// Status badge component with clean styling
const StatusBadge: React.FC<{ status: string }> = ({ status }) => {
  const getStatusDisplay = (status: string) => {
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

  const { text, className } = getStatusDisplay(status);

  return (
    <span className={`px-2 py-1 text-xs font-medium rounded-md border ${className}`}>
      {text}
    </span>
  );
};

// Individual button components
const KillButton: React.FC<{ request: Request; onAction: () => void }> = ({ request, onAction }) => {
  const [isProcessing, setIsProcessing] = useState(false);

  // Only show for Running status (matching LogStreamr logic)
  if (request.request_status !== 'R') {
    return <span></span>;
  }

  const handleKill = async () => {
    if (window.confirm(`Are you sure you want to kill request ${request.request_id}?`)) {
      setIsProcessing(true);
      try {
        await requestService.killRequest(request.request_id);
        alert(`Request ${request.request_id} has been cancelled`);
        onAction();
      } catch (error) {
        console.error('Kill request failed:', error);
        alert('Failed to cancel request. Please try again.');
      } finally {
        setIsProcessing(false);
      }
    }
  };

  return (
    <button
      onClick={handleKill}
      disabled={isProcessing}
      className="px-2 py-1 bg-red-600 text-white text-xs rounded hover:bg-red-700 transition-colors disabled:opacity-50"
      title="Kill/Cancel"
    >
      {isProcessing ? 'Killing...' : 'Kill'}
    </button>
  );
};

const RerunButton: React.FC<{ request: Request; onAction: () => void }> = ({ request, onAction }) => {
  const [showDropdown, setShowDropdown] = useState(false);
  const [isProcessing, setIsProcessing] = useState(false);

  // Only show for Completed and Error status (matching LogStreamr logic)
  if (!['C', 'E'].includes(request.request_status)) {
    return <span></span>;
  }

  const handleRerun = async (rerunType: string) => {
    setIsProcessing(true);
    try {
      await requestService.rerunRequest(request.request_id, rerunType);
      alert(`Request ${request.request_id} marked for rerun (${rerunType})`);
      onAction();
    } catch (error) {
      console.error('Rerun failed:', error);
      alert('Failed to rerun request. Please try again.');
    } finally {
      setShowDropdown(false);
      setIsProcessing(false);
    }
  };

  return (
    <div className="relative">
      <button
        onClick={() => setShowDropdown(!showDropdown)}
        disabled={isProcessing}
        className="px-2 py-1 bg-blue-600 text-white text-xs rounded hover:bg-blue-700 transition-colors disabled:opacity-50"
        title="ReRun"
      >
        {isProcessing ? 'Processing...' : 'ReRun ▼'}
      </button>
      {showDropdown && (
        <div className="absolute top-full left-0 mt-1 bg-white border border-gray-200 rounded shadow-lg z-20 min-w-24">
          <button
            onClick={() => handleRerun('Type1')}
            className="block w-full px-3 py-2 text-left text-xs hover:bg-gray-100"
          >
            Type 1
          </button>
          <button
            onClick={() => handleRerun('Type2')}
            className="block w-full px-3 py-2 text-left text-xs hover:bg-gray-100"
          >
            Type 2
          </button>
          <button
            onClick={() => handleRerun('Type3')}
            className="block w-full px-3 py-2 text-left text-xs hover:bg-gray-100"
          >
            Type 3
          </button>
        </div>
      )}
    </div>
  );
};

const ViewButton: React.FC<{ request: Request }> = ({ request }) => {
  // Only show for Completed status (matching LogStreamr logic)
  if (request.request_status !== 'C') {
    return <span></span>;
  }

  const handleView = () => {
    alert(`View details for request ${request.request_id} - Feature coming soon`);
  };

  return (
    <button
      onClick={handleView}
      className="px-2 py-1 bg-gray-600 text-white text-xs rounded hover:bg-gray-700 transition-colors"
      title="View Details"
    >
      View
    </button>
  );
};

const DownloadButton: React.FC<{ request: Request }> = ({ request }) => {
  const [isProcessing, setIsProcessing] = useState(false);

  // Only show for Completed status (matching LogStreamr logic)
  if (request.request_status !== 'C') {
    return <span></span>;
  }

  const handleDownload = async () => {
    setIsProcessing(true);
    try {
      const blob = await requestService.downloadRequest(request.request_id);
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `request_${request.request_id}_files.zip`;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);
    } catch (error) {
      console.error('Download failed:', error);
      alert('Download functionality not available yet.');
    } finally {
      setIsProcessing(false);
    }
  };

  return (
    <button
      onClick={handleDownload}
      disabled={isProcessing}
      className="px-2 py-1 bg-green-600 text-white text-xs rounded hover:bg-green-700 transition-colors disabled:opacity-50"
      title="Download"
    >
      {isProcessing ? 'Downloading...' : 'Download'}
    </button>
  );
};

const UploadButton: React.FC<{ request: Request; onAction: () => void }> = ({ request, onAction }) => {
  const [isProcessing, setIsProcessing] = useState(false);

  // Only show for Completed status (matching LogStreamr logic)
  if (request.request_status !== 'C') {
    return <span></span>;
  }

  const handleUpload = () => {
    const input = document.createElement('input');
    input.type = 'file';
    input.accept = '.zip,.csv,.txt';
    input.onchange = async (e) => {
      const file = (e.target as HTMLInputElement).files?.[0];
      if (file) {
        setIsProcessing(true);
        try {
          await requestService.uploadRequest(request.request_id, file);
          alert(`File uploaded successfully for request ${request.request_id}`);
          onAction();
        } catch (error) {
          console.error('Upload failed:', error);
          alert('Upload functionality not available yet.');
        } finally {
          setIsProcessing(false);
        }
      }
    };
    input.click();
  };

  return (
    <button
      onClick={handleUpload}
      disabled={isProcessing}
      className="px-2 py-1 bg-purple-600 text-white text-xs rounded hover:bg-purple-700 transition-colors disabled:opacity-50"
      title="Upload"
    >
      {isProcessing ? 'Uploading...' : 'Upload'}
    </button>
  );
};

const RequestLogs: React.FC = () => {
  const [requests, setRequests] = useState<Request[]>([]);
  const [loading, setLoading] = useState(true);
  const [searchTerm, setSearchTerm] = useState('');
  const [currentPage, setCurrentPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const [refreshing, setRefreshing] = useState(false);

  const requestsPerPage = 50;

  // Load requests from API
  const loadRequests = async () => {
    try {
      setRefreshing(true);
      console.log('🔄 Loading requests from backend API...');

      const data = await requestService.getRequests({
        page: currentPage,
        limit: requestsPerPage,
        search: searchTerm
      });

      console.log('✅ Data received from backend:', data);
      setRequests(data.requests || []);
      setTotalPages(Math.ceil((data.total || 0) / requestsPerPage));

    } catch (error) {
      console.error('❌ Failed to load requests from backend:', error);
      console.warn('⚠️ Using fallback sample data for development');

      // Fallback sample data only for development when backend is not available
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

      setRequests(fallbackData);
      setTotalPages(1);
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  // Initial load
  useEffect(() => {
    loadRequests();
  }, [currentPage, searchTerm]);

  // Auto-refresh every 30 seconds (hybrid approach)
  useEffect(() => {
    const interval = setInterval(() => {
      loadRequests();
    }, 30000); // 30 seconds

    return () => clearInterval(interval);
  }, [currentPage, searchTerm]);

  // Handle search
  const handleSearch = (e: React.ChangeEvent<HTMLInputElement>) => {
    setSearchTerm(e.target.value);
    setCurrentPage(1); // Reset to first page on search
  };

  // Handle manual refresh
  const handleRefresh = () => {
    loadRequests();
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
            className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors disabled:opacity-50 text-sm"
          >
            {refreshing ? 'Refreshing...' : 'Refresh'}
          </button>
        </div>
      </div>

      {/* Table Container - Scrollable middle section */}
      <div className="overflow-auto bg-white" style={{ height: 'calc(100vh - 220px)' }}>
        <table className="w-full border-collapse border border-gray-300">
          <thead className="bg-gray-100 sticky top-0 z-10">
            <tr>
              <th className="w-20 px-3 py-3 text-left text-sm font-bold text-black uppercase tracking-wider border border-gray-300">
                RequestId
              </th>
              <th className="w-32 px-3 py-3 text-left text-sm font-bold text-black uppercase tracking-wider border border-gray-300">
                Client Name
              </th>
              <th className="w-20 px-3 py-3 text-left text-sm font-bold text-black uppercase tracking-wider border border-gray-300">
                Week
              </th>
              <th className="w-28 px-3 py-3 text-left text-sm font-bold text-black uppercase tracking-wider border border-gray-300">
                AddedBy
              </th>
              <th className="w-24 px-3 py-3 text-left text-sm font-bold text-black uppercase tracking-wider border border-gray-300">
                TRTCount
              </th>
              <th className="w-24 px-3 py-3 text-left text-sm font-bold text-black uppercase tracking-wider border border-gray-300">
                Status
              </th>
              <th className="w-48 px-3 py-3 text-left text-sm font-bold text-black uppercase tracking-wider border border-gray-300">
                Description
              </th>
              <th className="w-24 px-3 py-3 text-left text-sm font-bold text-black uppercase tracking-wider border border-gray-300">
                ExecTime
              </th>
              <th className="w-60 px-3 py-3 text-center text-sm font-bold text-black uppercase tracking-wider border border-gray-300">
                Actions
              </th>
            </tr>
          </thead>
          <tbody className="bg-white">
            {requests.map((request) => (
              <tr key={request.request_id} className="hover:bg-gray-50">
                <td className="w-20 px-3 py-4 whitespace-nowrap text-sm font-medium text-gray-900 border border-gray-200">
                  {request.request_id}
                </td>
                <td className="w-32 px-3 py-4 whitespace-nowrap text-sm text-gray-900 border border-gray-200">
                  {request.client_name}
                </td>
                <td className="w-20 px-3 py-4 whitespace-nowrap text-sm text-gray-900 border border-gray-200">
                  {request.week}
                </td>
                <td className="w-28 px-3 py-4 whitespace-nowrap text-sm text-gray-900 border border-gray-200">
                  {request.added_by}
                </td>
                <td className="w-24 px-3 py-4 whitespace-nowrap text-sm text-gray-900 border border-gray-200">
                  {request.trt_count ? request.trt_count.toLocaleString() : '-'}
                </td>
                <td className="w-24 px-3 py-4 whitespace-nowrap border border-gray-200">
                  <StatusBadge status={request.request_status} />
                </td>
                <td className="w-48 px-3 py-4 text-sm text-gray-900 border border-gray-200 truncate" title={request.request_desc}>
                  {request.request_desc}
                </td>
                <td className="w-24 px-3 py-4 whitespace-nowrap text-sm text-gray-900 border border-gray-200">
                  {request.execution_time || '-'}
                </td>
                <td className="w-60 px-3 py-4 whitespace-nowrap border border-gray-200">
                  <div className="flex items-center justify-center space-x-1">
                    <KillButton request={request} onAction={loadRequests} />
                    <RerunButton request={request} onAction={loadRequests} />
                    <ViewButton request={request} />
                    <DownloadButton request={request} />
                    <UploadButton request={request} onAction={loadRequests} />
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
            Showing page {currentPage} of {totalPages} ({requestsPerPage} per page)
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
        Auto-refresh every 30 seconds • Last updated: {new Date().toLocaleTimeString()} • {requests.length} requests shown
      </div>
    </>
  );
};

export default RequestLogs;
