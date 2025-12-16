import React, { useState, useEffect } from 'react';
import { requestService } from '../services/requestService';
import { MdClose, MdDownload } from 'react-icons/md';

interface StatItem {
  header: string;
  value: string;
}

interface RequestStats {
  request_details: StatItem[];
  logs_details: StatItem[];
}

interface RequestStatsModalProps {
  isOpen: boolean;
  onClose: () => void;
  requestId: number;
}

const RequestStatsModal: React.FC<RequestStatsModalProps> = ({
  isOpen,
  onClose,
  requestId
}) => {
  const [stats, setStats] = useState<RequestStats | null>(null);
  const [loading, setLoading] = useState(false);
  const [downloadLoading, setDownloadLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (isOpen && requestId) {
      fetchStats();
    }
  }, [isOpen, requestId]);

  const fetchStats = async () => {
    setLoading(true);
    setError(null);

    try {
      const response = await requestService.getRequestStats(requestId);

      if (response.success) {
        setStats(response.stats);
      } else {
        setError(response.error || 'Failed to fetch statistics');
      }
    } catch (err) {
      setError('Failed to fetch statistics');
      console.error('Error fetching stats:', err);
    } finally {
      setLoading(false);
    }
  };

  const formatHeader = (header: string): string => {
    // Remove HTML tags first
    let formatted = header.replace(/<\/?b>/g, '');

    // Handle specific patterns and add proper spacing
    formatted = formatted
      // First handle specific known patterns
      .replace(/ActuaLogsCount/g, 'Actual Logs Count')
      .replace(/ActualLogsTRTmatchCount/g, 'Actual Logs TRT Match Count')
      .replace(/ActualLogsPBreportedCount/g, 'Actual Logs PB Reported Count')
      .replace(/ActualOpensCount/g, 'Actual Opens Count')
      .replace(/OpensTRTmatchCount/g, 'Opens TRT Match Count')
      .replace(/OpensPBreportedCount/g, 'Opens PB Reported Count')
      .replace(/ActualClicksCount/g, 'Actual Clicks Count')
      .replace(/ClicksTRTmatchCount/g, 'Clicks TRT Match Count')
      .replace(/ClicksPBreportedCount/g, 'Clicks PB Reported Count')
      .replace(/OpensToOpensPBreportedGenCount/g, 'Opens To Opens PB Reported Gen Count')
      .replace(/ClicksToClicksPBreportedGenCount/g, 'Clicks To Clicks PB Reported Gen Count')
      .replace(/RequestID/g, 'Request ID')
      .replace(/ClientName/g, 'Client Name')
      .replace(/TRTFileCount/g, 'TRT File Count')
      .replace(/RequestStatus/g, 'Request Status')
      .replace(/RequestDescription/g, 'Request Description')
      .replace(/StartTime/g, 'Start Time')
      .replace(/TotalExecutionTime/g, 'Total Execution Time')
      .replace(/UnsubHardsSuppressionCount/g, 'Unsub Hards Suppression Count')
      .replace(/OfferIDSuppressionCount/g, 'Offer ID Suppression Count')
      .replace(/ClientSuppressionCount/g, 'Client Suppression Count')
      .replace(/MaxTouchCount/g, 'Max Touch Count')
      .replace(/LastWeekDeliveredInsertedCount/g, 'Last Week Delivered Inserted Count')
      .replace(/UnsubInsertedCount/g, 'Unsub Inserted Count')
      .replace(/UniqueDeliveredCount/g, 'Unique Delivered Count')
      .replace(/TotalDeliveredCount/g, 'Total Delivered Count')
      .replace(/NewlyAddedRecordsCount/g, 'Newly Added Records Count')
      .replace(/NewlyAddedIPCount/g, 'Newly Added IP Count')
      .replace(/TotalRunningUniqueCount/g, 'Total Running Unique Count')
      .replace(/DeliveredTable/g, 'Delivered Table')
      .replace(/AddedBy/g, 'Added By')
      // General patterns for any remaining cases
      .replace(/([a-z])([A-Z])/g, '$1 $2')
      // Clean up any double spaces
      .replace(/\s+/g, ' ')
      .trim();

    return formatted;
  };

  const handleDownload = async () => {
    setDownloadLoading(true);
    try {
      const response = await requestService.downloadRequestStats(requestId);

      // Create blob and download
      const blob = new Blob([response], {
        type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
      });

      const url = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = `RequestDetails-${requestId}.xlsx`;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      window.URL.revokeObjectURL(url);
    } catch (error) {
      console.error('Error downloading stats:', error);
      setError('Failed to download statistics');
    } finally {
      setDownloadLoading(false);
    }
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div className="bg-white rounded shadow-xl w-full max-w-lg mx-4 max-h-[70vh] flex flex-col">
        {/* Header */}
        <div className="flex items-center justify-between p-3 border-b border-gray-200">
          <div className="flex items-center space-x-2">
            <span className="text-blue-600">📊</span>
            <h2 className="text-base font-medium text-gray-900">
              Request Statistics - #{requestId}
            </h2>
          </div>
          <div className="flex items-center space-x-2">
            {stats && (
              <button
                onClick={handleDownload}
                disabled={downloadLoading}
                className={`px-2 py-1 text-xs font-medium text-white border border-transparent rounded flex items-center space-x-1 ${
                  downloadLoading
                    ? 'bg-green-400 cursor-not-allowed'
                    : 'bg-green-600 hover:bg-green-700'
                }`}
              >
                {downloadLoading ? (
                  <div className="animate-spin rounded-full h-3 w-3 border-2 border-white border-t-transparent"></div>
                ) : (
                  <MdDownload className="h-3 w-3" />
                )}
                <span>{downloadLoading ? 'Downloading...' : 'Download Excel'}</span>
              </button>
            )}
            <button
              onClick={onClose}
              className="text-gray-400 hover:text-gray-600 transition-colors"
            >
              <MdClose className="h-4 w-4" />
            </button>
          </div>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-hidden p-3">
          {loading && (
            <div className="flex items-center justify-center h-32">
              <div className="animate-spin rounded-full h-6 w-6 border-b-2 border-blue-600"></div>
              <span className="ml-2 text-sm text-gray-600">Loading...</span>
            </div>
          )}

          {error && (
            <div className="bg-red-50 border border-red-200 rounded p-2">
              <div className="flex">
                <div className="ml-2">
                  <h3 className="text-xs font-medium text-red-800">Error</h3>
                  <p className="mt-1 text-xs text-red-700">{error}</p>
                </div>
              </div>
            </div>
          )}

          {stats && (
            <div className="space-y-4 overflow-y-auto max-h-[50vh]">
              {/* Request Details Section */}
              <div>
                <h3 className="text-sm font-medium text-gray-900 mb-2 flex items-center">
                  <span className="h-1 w-1 bg-blue-600 rounded-full mr-2"></span>
                  Request Details
                </h3>
                <div className="bg-gray-50 rounded p-2">
                  <div className="overflow-x-auto">
                    <table style={{
                      width: '100%',
                      tableLayout: 'fixed',
                      borderCollapse: 'collapse',
                      '--name-width': '50%',
                      '--value-width': '50%'
                    } as any} className="bg-white rounded border border-gray-200">
                      <colgroup>
                        <col style={{ width: '50% !important' }} />
                        <col style={{ width: '50% !important' }} />
                      </colgroup>
                      <thead className="bg-gradient-to-r from-blue-600 to-indigo-700">
                        <tr>
                          <th style={{
                            width: '50% !important',
                            minWidth: '50%',
                            maxWidth: '50%'
                          }} className="px-3 py-2 text-left text-xs font-bold text-white border-b border-white border-r border-white">
                            Name
                          </th>
                          <th style={{
                            width: '50% !important',
                            minWidth: '50%',
                            maxWidth: '50%'
                          }} className="px-3 py-2 text-left text-xs font-bold text-white border-b border-white">
                            Value
                          </th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-gray-200">
                        {stats.request_details.map((item, index) => (
                          <tr key={index} className={index % 2 === 0 ? 'bg-white hover:bg-gray-50' : 'bg-gray-50 hover:bg-gray-100'}>
                            <td style={{
                              width: '50% !important',
                              minWidth: '50%',
                              maxWidth: '50%'
                            }} className="px-3 py-2 text-xs font-medium text-gray-700 border-r border-gray-200">
                              {formatHeader(item.header)}
                            </td>
                            <td style={{
                              width: '50% !important',
                              minWidth: '50%',
                              maxWidth: '50%'
                            }} className="px-3 py-2 text-xs text-gray-900">
                              {item.value || 'N/A'}
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
              </div>

              {/* Logs Details Section */}
              <div>
                <h3 className="text-sm font-medium text-gray-900 mb-2 flex items-center">
                  <span className="h-1 w-1 bg-blue-600 rounded-full mr-2"></span>
                  Logs Details
                </h3>
                <div className="bg-gray-50 rounded p-2">
                  <div className="overflow-x-auto">
                    <table style={{
                      width: '100%',
                      tableLayout: 'fixed',
                      borderCollapse: 'collapse',
                      '--name-width': '50%',
                      '--value-width': '50%'
                    } as any} className="bg-white rounded border border-gray-200">
                      <colgroup>
                        <col style={{ width: '50% !important' }} />
                        <col style={{ width: '50% !important' }} />
                      </colgroup>
                      <thead className="bg-gradient-to-r from-blue-600 to-indigo-700">
                        <tr>
                          <th style={{
                            width: '50% !important',
                            minWidth: '50%',
                            maxWidth: '50%'
                          }} className="px-3 py-2 text-left text-xs font-bold text-white border-b border-white border-r border-white">
                            Name
                          </th>
                          <th style={{
                            width: '50% !important',
                            minWidth: '50%',
                            maxWidth: '50%'
                          }} className="px-3 py-2 text-left text-xs font-bold text-white border-b border-white">
                            Value
                          </th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-gray-200">
                        {stats.logs_details.map((item, index) => (
                          <tr key={index} className={index % 2 === 0 ? 'bg-white hover:bg-gray-50' : 'bg-gray-50 hover:bg-gray-100'}>
                            <td style={{
                              width: '50% !important',
                              minWidth: '50%',
                              maxWidth: '50%'
                            }} className="px-3 py-2 text-xs font-medium text-gray-700 border-r border-gray-200">
                              {formatHeader(item.header)}
                            </td>
                            <td style={{
                              width: '50% !important',
                              minWidth: '50%',
                              maxWidth: '50%'
                            }} className="px-3 py-2 text-xs text-gray-900">
                              {item.value || 'N/A'}
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default RequestStatsModal;
