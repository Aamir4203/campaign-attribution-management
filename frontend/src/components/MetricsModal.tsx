import React, { useState, useEffect } from 'react';
import { requestService } from '../services/requestService';
import { MdClose, MdBarChart, MdDownload, MdAdd } from 'react-icons/md';

interface MetricsModalProps {
  isOpen: boolean;
  onClose: () => void;
  requestId: number;
  clientName: string;
  week: string;
}

interface ColumnConfig {
  name: string;
  alias?: string;
  aggregation?: string;
  groupBy?: boolean;
}

interface QueryConfig {
  columns: ColumnConfig[];
  groupByColumns: ColumnConfig[];
}

const MetricsModal: React.FC<MetricsModalProps> = ({
  isOpen,
  onClose,
  requestId,
  clientName,
  week
}) => {
  const [metricType, setMetricType] = useState<'standard' | 'custom'>('standard');
  const [includeStandardHeaders, setIncludeStandardHeaders] = useState(false);
  const [customQueries, setCustomQueries] = useState<QueryConfig[]>([]);
  const [availableColumns, setAvailableColumns] = useState<string[]>([]);
  const [loading, setLoading] = useState(false);
  const [downloadLoading, setDownloadLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Define excluded columns
  const excludedColumns = ['status', 'unsub', 'id', 'diff', 'offerid', 'ip', 'timestamp', 'file_status', 'md5hash'];

  // Define special column mappings for metric fields (should not be in GROUP BY)
  const specialColumns: Record<string, { alias: string; aggregation: string; groupBy: boolean }> = {
    email: { alias: 'Sent', aggregation: 'count(email)', groupBy: false },
    open_date: { alias: 'UniqueOpens', aggregation: 'count(open_date)', groupBy: false },
    click_date: { alias: 'UniqueClicks', aggregation: 'count(click_date)', groupBy: false },
    unsub_date: { alias: 'UniqueUnsubs', aggregation: 'count(unsub_date)', groupBy: false }
  };

  // Special flag columns (handled separately) - also metric fields
  const flagColumns = [
    { name: 'flag_soft', alias: 'SoftBounces', aggregation: "sum(case when flag='S' then 1 else 0 end)", groupBy: false },
    { name: 'flag_hard', alias: 'HardBounces', aggregation: "sum(case when flag='B' then 1 else 0 end)", groupBy: false }
  ];

  // Standard queries
  const standardQueries = [
    {
      name: 'Detailed Metrics by Creative and Segment',
      query: `select count(email) Sent,sum(case when flag is null then 1 else 0 end) Delivered,count(open_date) UniqueOpens,count(click_date) UniqueClicks,count(unsub_date) UniqueUnsubs,sum(case when flag='S' then 1 else 0 end ) SoftBounces,sum(case when flag='B' then 1 else 0 end) HardBounces,del_date DeliveredDate,subject SubjectLine,Creative,OfferId,Segment,subseg SubSegment from apt_custom_${requestId}_${clientName}_${week}_postback_table group by 8,9,10,11,12,13;`
    },
    {
      name: 'Metrics by Segment and Decile',
      query: `select count(email) Sent,sum(case when flag is null then 1 else 0 end) Delivered,count(open_date) UniqueOpens,count(click_date) UniqueClicks,count(unsub_date) UniqueUnsubs,Segment,subseg SubSegment,Decile from apt_custom_${requestId}_${clientName}_${week}_postback_table group by 6,7,8 order by 6,7,8;`
    }
  ];

  useEffect(() => {
    if (isOpen && metricType === 'custom') {
      fetchTableColumns();
    }
  }, [isOpen, metricType]);

  const fetchTableColumns = async () => {
    setLoading(true);
    try {
      // Fetch columns from the postback table
      const tableName = `apt_custom_${requestId}_${clientName}_${week}_postback_table`;
      const response = await requestService.getTableColumns(tableName);

      if (response.success) {
        // Filter out excluded columns
        const filteredColumns = response.columns.filter(
          (col: string) => !excludedColumns.includes(col.toLowerCase())
        );
        setAvailableColumns(filteredColumns);
      } else {
        setError('Failed to fetch table columns');
      }
    } catch (err) {
      setError('Failed to fetch table columns');
      console.error('Error fetching columns:', err);
    } finally {
      setLoading(false);
    }
  };

  const addCustomQuery = () => {
    setCustomQueries([...customQueries, { columns: [], groupByColumns: [] }]);
  };

  const updateQueryColumn = (queryIndex: number, columnName: string, selected: boolean) => {
    const updatedQueries = [...customQueries];
    const query = updatedQueries[queryIndex];

    if (selected) {
      const columnConfig: ColumnConfig = {
        name: columnName,
        groupBy: true // Default all columns to GROUP BY
      };

      // Add special handling for metric columns (aggregations) - these should NOT be grouped
      if (specialColumns[columnName]) {
        columnConfig.alias = specialColumns[columnName].alias;
        columnConfig.aggregation = specialColumns[columnName].aggregation;
        columnConfig.groupBy = false; // Metric fields should not be in GROUP BY
      }

      // Handle flag columns - these are also metrics
      const flagColumn = flagColumns.find(f => f.name === columnName);
      if (flagColumn) {
        columnConfig.alias = flagColumn.alias;
        columnConfig.aggregation = flagColumn.aggregation;
        columnConfig.groupBy = false; // Flag metric fields should not be in GROUP BY
      }

      query.columns.push(columnConfig);
    } else {
      query.columns = query.columns.filter(col => col.name !== columnName);
    }

    setCustomQueries(updatedQueries);
  };

  const generateCustomQuery = (queryConfig: QueryConfig): string => {
    const selectColumns = queryConfig.columns.map(col => {
      if (col.aggregation) {
        return col.alias ? `${col.aggregation} ${col.alias}` : col.aggregation;
      } else {
        return col.alias ? `${col.name} ${col.alias}` : col.name;
      }
    });

    // Calculate GROUP BY positions based on which columns are marked for groupBy
    const groupByPositions: number[] = [];
    queryConfig.columns.forEach((col, index) => {
      if (col.groupBy) {
        groupByPositions.push(index + 1); // 1-based indexing for GROUP BY
      }
    });

    const tableName = `apt_custom_${requestId}_${clientName}_${week}_postback_table`;

    let query = `SELECT ${selectColumns.join(', ')} FROM ${tableName}`;

    if (groupByPositions.length > 0) {
      query += ` GROUP BY ${groupByPositions.join(', ')}`;
    }

    return query + ';';
  };

  const handleDownload = async () => {
    setDownloadLoading(true);
    try {
      const queries = metricType === 'standard'
        ? standardQueries.map(q => ({ name: q.name, query: q.query }))
        : customQueries.map((config, index) => ({
            name: `Custom Query ${index + 1}`,
            query: generateCustomQuery(config)
          }));

      if (includeStandardHeaders && metricType === 'custom') {
        queries.unshift(...standardQueries.map(q => ({ name: q.name, query: q.query })));
      }

      const response = await requestService.downloadMetrics(requestId, {
        queries,
        metricType,
        includeStandardHeaders
      });

      // Create blob and download
      const blob = new Blob([response], {
        type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
      });

      const url = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = `Metrics-${requestId}.xlsx`;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      window.URL.revokeObjectURL(url);
    } catch (error) {
      console.error('Error downloading metrics:', error);
      setError('Failed to download metrics');
    } finally {
      setDownloadLoading(false);
    }
  };

  const removeCustomQuery = (index: number) => {
    const updatedQueries = customQueries.filter((_, i) => i !== index);
    setCustomQueries(updatedQueries);
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div className="bg-white rounded-lg shadow-xl w-full max-w-2xl mx-4 max-h-[60vh] flex flex-col">
        {/* Download Loading Overlay */}
        {downloadLoading && (
          <div className="absolute inset-0 bg-black bg-opacity-30 flex items-center justify-center z-10 rounded-lg">
            <div className="bg-white rounded-lg p-6 flex flex-col items-center space-y-3">
              <div className="animate-spin rounded-full h-8 w-8 border-4 border-green-600 border-t-transparent"></div>
              <span className="text-gray-700 font-medium">Downloading Metrics...</span>
            </div>
          </div>
        )}
        {/* Header */}
        <div className="flex items-center justify-between p-6 border-b border-gray-200">
          <div className="flex items-center space-x-3">
            <MdBarChart className="h-6 w-6 text-blue-600" />
            <h2 className="text-xl font-semibold text-gray-900">
              Download Metrics - #{requestId}
            </h2>
          </div>
          <div className="flex items-center space-x-3">
            <button
              onClick={handleDownload}
              disabled={downloadLoading || (metricType === 'custom' && customQueries.length === 0 && !includeStandardHeaders)}
              className={`px-4 py-2 text-sm font-medium text-white border border-transparent rounded-md focus:outline-none focus:ring-2 focus:ring-green-500 flex items-center space-x-2 ${
                downloadLoading || (metricType === 'custom' && customQueries.length === 0 && !includeStandardHeaders)
                  ? 'bg-gray-400 cursor-not-allowed'
                  : 'bg-green-600 hover:bg-green-700'
              }`}
            >
              {downloadLoading ? (
                <div className="animate-spin rounded-full h-4 w-4 border-2 border-white border-t-transparent"></div>
              ) : (
                <MdDownload className="h-4 w-4" />
              )}
              <span>{downloadLoading ? 'Downloading...' : 'Download'}</span>
            </button>
            <button
              onClick={onClose}
              className="text-gray-400 hover:text-gray-600 transition-colors"
            >
              <MdClose className="h-6 w-6" />
            </button>
          </div>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-hidden p-6">
          {error && (
            <div className="bg-red-50 border border-red-200 rounded-md p-4 mb-4">
              <div className="flex">
                <div className="ml-3">
                  <h3 className="text-sm font-medium text-red-800">Error</h3>
                  <p className="mt-1 text-sm text-red-700">{error}</p>
                </div>
              </div>
            </div>
          )}

          <div className="space-y-6 overflow-y-auto max-h-[40vh]">
            {/* Metric Type Selection */}
            <div>
              <h3 className="text-lg font-semibold text-gray-900 mb-4 text-left">Select Metric Type</h3>
              <div className="flex flex-col space-y-3">
                <label className="flex items-center">
                  <input
                    type="radio"
                    name="metricType"
                    value="standard"
                    checked={metricType === 'standard'}
                    onChange={(e) => setMetricType(e.target.value as 'standard' | 'custom')}
                    className="mr-2 h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300"
                  />
                  <span className="text-gray-700 font-medium">Standard Metrics</span>
                </label>
                <label className="flex items-center">
                  <input
                    type="radio"
                    name="metricType"
                    value="custom"
                    checked={metricType === 'custom'}
                    onChange={(e) => setMetricType(e.target.value as 'standard' | 'custom')}
                    className="mr-2 h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300"
                  />
                  <span className="text-gray-700 font-medium">Custom Metrics</span>
                </label>
              </div>
            </div>

            {/* Custom Metrics Configuration */}
            {metricType === 'custom' && (
              <div>
                <div className="flex items-center justify-between mb-4">
                  <h4 className="text-md font-semibold text-gray-800">Custom Queries</h4>
                  <div className="flex items-center space-x-4">
                    <label className="flex items-center">
                      <input
                        type="checkbox"
                        checked={includeStandardHeaders}
                        onChange={(e) => setIncludeStandardHeaders(e.target.checked)}
                        className="mr-2 h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded"
                      />
                      <span className="text-sm text-gray-700">Include Standard Headers</span>
                    </label>
                    <button
                      onClick={addCustomQuery}
                      className="flex items-center space-x-1 px-3 py-1 bg-blue-600 text-white rounded-md hover:bg-blue-700 text-sm"
                    >
                      <MdAdd className="h-4 w-4" />
                      <span>Add Query</span>
                    </button>
                  </div>
                </div>

                {loading && (
                  <div className="flex items-center justify-center py-8">
                    <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
                    <span className="ml-3 text-gray-600">Loading table columns...</span>
                  </div>
                )}

                {customQueries.map((query, queryIndex) => (
                  <div key={queryIndex} className="bg-gray-50 p-4 rounded-lg mb-4">
                    <div className="flex items-center justify-between mb-3">
                      <h5 className="font-medium text-gray-700">Custom Query {queryIndex + 1}</h5>
                      <button
                        onClick={() => removeCustomQuery(queryIndex)}
                        className="text-red-500 hover:text-red-700 text-sm"
                      >
                        Remove
                      </button>
                    </div>

                    <div className="grid grid-cols-3 gap-4">
                      {/* Regular available columns */}
                      {availableColumns.map((column) => {
                        const isSelected = query.columns.some(col => col.name === column);
                        const specialCol = specialColumns[column];

                        return (
                          <label key={column} className="flex items-center space-x-2">
                            <input
                              type="checkbox"
                              checked={isSelected}
                              onChange={(e) => updateQueryColumn(queryIndex, column, e.target.checked)}
                              className="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded"
                            />
                            <span className="text-sm text-gray-700">
                              {column}
                              {specialCol && (
                                <span className="text-blue-600 text-xs ml-1">
                                  → {specialCol.alias}
                                </span>
                              )}
                            </span>
                          </label>
                        );
                      })}

                      {/* Special flag columns */}
                      {flagColumns.map((flagCol) => {
                        const isSelected = query.columns.some(col => col.name === flagCol.name);

                        return (
                          <label key={flagCol.name} className="flex items-center space-x-2">
                            <input
                              type="checkbox"
                              checked={isSelected}
                              onChange={(e) => updateQueryColumn(queryIndex, flagCol.name, e.target.checked)}
                              className="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded"
                            />
                            <span className="text-sm text-gray-700">
                              {flagCol.alias}
                              <span className="text-blue-600 text-xs ml-1">
                                (flag)
                              </span>
                            </span>
                          </label>
                        );
                      })}
                    </div>

                    {query.columns.length > 0 && (
                      <div className="mt-3">
                        <h6 className="text-sm font-medium text-gray-600 mb-2">Generated Query:</h6>
                        <code className="text-xs text-gray-600 bg-white p-2 rounded border block overflow-x-auto">
                          {generateCustomQuery(query)}
                        </code>
                      </div>
                    )}
                  </div>
                ))}

                {customQueries.length === 0 && !loading && (
                  <div className="text-center py-8 text-gray-500">
                    Click "Add Query" to create custom metrics queries
                  </div>
                )}
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};

export default MetricsModal;
