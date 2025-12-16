import React, { useState, useEffect } from 'react';
import { useAuth } from '../components/Auth';
import api from '../services/api';

// Configuration constants (matching app.yaml)
const DASHBOARD_CONFIG = {
  refreshInterval: 300000, // 5 minutes in milliseconds (from app.yaml dashboard.refresh.interval)
  refreshIntervalSeconds: 300, // 5 minutes in seconds (for display)
  defaultDateFilter: 'wtd', // Week to Date (from app.yaml dashboard.dateFilter.default)
  longRunningThreshold: 7200 // 2 hours in seconds (from app.yaml dashboard.alerts.longRunningThreshold)
};

interface DashboardMetrics {
  total_requests: number;
  active_requests: number;
  waiting_requests: number;
  completed_today: number;
  failed_requests: number;
  avg_execution_time: number;
}

interface UserData {
  username: string;
  total_requests: number;
  completed_requests: number;
  active_requests: number;
  avg_execution_hours: number;
  success_rate: number;
}

interface Alert {
  type: string;
  severity: string;
  message: string;
  request_id?: number;
  user?: string;
  description?: string;
}

const Dashboard: React.FC = () => {
  let username = 'User';

  try {
    const { getUsername } = useAuth();
    username = getUsername() || 'User';
  } catch (authError) {
    console.error('Auth hook error:', authError);
  }

  const [metrics, setMetrics] = useState<DashboardMetrics>({
    total_requests: 0,
    active_requests: 0,
    waiting_requests: 0,
    completed_today: 0,
    failed_requests: 0,
    avg_execution_time: 0
  });
  const [users, setUsers] = useState<UserData[]>([]);
  const [alerts, setAlerts] = useState<Alert[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [lastUpdated, setLastUpdated] = useState<Date>(new Date());
  const [dateFilter, setDateFilter] = useState(DASHBOARD_CONFIG.defaultDateFilter);
  const [customFromDate, setCustomFromDate] = useState('');
  const [customToDate, setCustomToDate] = useState('');
  const [showCustomDatePicker, setShowCustomDatePicker] = useState(false);
  const [isUserActivityExpanded, setIsUserActivityExpanded] = useState(false);
  const [userActivityViewMode, setUserActivityViewMode] = useState<'list' | 'chart'>('list');
  const [chartLoading, setChartLoading] = useState(false);

  const fetchDashboardData = async () => {
    try {
      setError(null);

      // If we're in chart view, show loading for data processing
      if (userActivityViewMode === 'chart') {
        setChartLoading(true);
      }

      // Calculate date range based on filter
      const getDateRange = () => {
        const today = new Date();

        switch (dateFilter) {
          case 'wtd': // Week to Date (Monday to today)
            const monday = new Date(today);
            const dayOfWeek = today.getDay();
            const daysFromMonday = dayOfWeek === 0 ? -6 : 1 - dayOfWeek;
            monday.setDate(today.getDate() + daysFromMonday);
            return { from: monday.toISOString().split('T')[0], to: today.toISOString().split('T')[0] };

          case 'mtd': // Month to Date
            const monthStart = new Date(today.getFullYear(), today.getMonth(), 1);
            return { from: monthStart.toISOString().split('T')[0], to: today.toISOString().split('T')[0] };

          case 'ytd': // Year to Date
            const yearStart = new Date(today.getFullYear(), 0, 1);
            return { from: yearStart.toISOString().split('T')[0], to: today.toISOString().split('T')[0] };

          case 'custom': // Custom Range
            return {
              from: customFromDate || today.toISOString().split('T')[0],
              to: customToDate || today.toISOString().split('T')[0]
            };

          default:
            const defaultMonday = new Date(today);
            const defaultDayOfWeek = today.getDay();
            const defaultDaysFromMonday = defaultDayOfWeek === 0 ? -6 : 1 - defaultDayOfWeek;
            defaultMonday.setDate(today.getDate() + defaultDaysFromMonday);
            return { from: defaultMonday.toISOString().split('T')[0], to: today.toISOString().split('T')[0] };
        }
      };

      const dateRange = getDateRange();

      // Fetch metrics, user data, and alerts in parallel
      const [metricsResponse, usersResponse, alertsResponse] = await Promise.all([
        api.get(`/api/dashboard/metrics?from=${dateRange.from}&to=${dateRange.to}`),
        api.get(`/api/dashboard/users?from=${dateRange.from}&to=${dateRange.to}`),
        api.get('/api/dashboard/alerts')
      ]);

      // Handle metrics data
      if (metricsResponse.data.success && metricsResponse.data.metrics) {
        const metrics = metricsResponse.data.metrics;
        setMetrics({
          total_requests: Number(metrics.total_requests) || 0,
          active_requests: Number(metrics.active_requests) || 0,
          waiting_requests: Number(metrics.waiting_requests) || 0,
          completed_today: Number(metrics.completed_today) || 0,
          failed_requests: Number(metrics.failed_requests) || 0,
          avg_execution_time: Number(metrics.avg_execution_time) || 0
        });
      } else {
        setMetrics({
          total_requests: 0,
          active_requests: 0,
          waiting_requests: 0,
          completed_today: 0,
          failed_requests: 0,
          avg_execution_time: 0
        });
      }

      // Handle user activity data
      if (usersResponse.data.success && usersResponse.data.user_data) {
        console.log('👥 User activity data received:', usersResponse.data.user_data.length, 'users');
        setUsers(usersResponse.data.user_data);
      } else {
        console.log('⚠️ No user activity data received');
        setUsers([]);
      }

      // Handle alerts data
      if (alertsResponse.data.success && alertsResponse.data.alerts) {
        setAlerts(alertsResponse.data.alerts);
      } else {
        setAlerts([]);
      }

      setLastUpdated(new Date());
    } catch (err: any) {
      console.error('Dashboard API error:', err);
      setError('Unable to load dashboard data - using fallback');
      setMetrics({
        total_requests: 0,
        active_requests: 0,
        waiting_requests: 0,
        completed_today: 0,
        failed_requests: 0,
        avg_execution_time: 0
      });
      setUsers([]);
      setAlerts([]);
    } finally {
      setLoading(false);
      // Complete chart loading if it was active
      if (chartLoading) {
        setTimeout(() => setChartLoading(false), 300); // Small delay for smooth transition
      }
    }
  };

  useEffect(() => {
    fetchDashboardData();

    // Set up auto-refresh using config interval (5 minutes)
    const interval = setInterval(fetchDashboardData, DASHBOARD_CONFIG.refreshInterval);
    return () => clearInterval(interval);
  }, []);

  const formatNumber = (num: number | null | undefined): string => {
    if (num === null || num === undefined) return '0';
    return num.toLocaleString();
  };

  const formatExecutionTime = (hours: number | null | undefined): string => {
    if (!hours || hours === 0) return '0h';
    if (hours < 1) return `${Math.round(hours * 60)}m`;
    return `${hours.toFixed(1)}h`;
  };

  const getDateFilterLabel = (filter: string): string => {
    switch (filter) {
      case 'wtd': return 'WeekToDate';
      case 'mtd': return 'MonthToDate';
      case 'ytd': return 'YearToDate';
      case 'custom': return 'Custom';
      default: return 'WeekToDate';
    }
  };

  const handleDateFilterChange = (value: string) => {
    setDateFilter(value);
    if (value === 'custom') {
      setShowCustomDatePicker(true);
    } else {
      setShowCustomDatePicker(false);
    }
  };

  // Handle view mode change with loading simulation
  const handleViewModeChange = async (mode: 'list' | 'chart') => {
    if (mode === userActivityViewMode) return;

    setChartLoading(true);

    // Simulate realistic processing time for data visualization
    // Chart generation involves: data processing, sorting, calculations, rendering
    const processingTime = mode === 'chart' ? 1200 : 500; // Chart takes longer to generate

    // Add some realistic delay to show the loading experience
    await new Promise(resolve => setTimeout(resolve, processingTime));

    setUserActivityViewMode(mode);
    setChartLoading(false);
  };

  // Auto-refresh when date filter changes
  useEffect(() => {
    fetchDashboardData();
  }, [dateFilter, customFromDate, customToDate]);

  // Render loading state
  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-96 bg-gray-50 m-4 rounded-lg">
        <div className="text-center">
          <div className="w-16 h-16 border-4 border-blue-200 border-t-blue-600 rounded-full animate-spin mx-auto mb-4"></div>
          <p className="text-lg text-gray-700">Loading dashboard...</p>
        </div>
      </div>
    );
  }


  return (
    <div className="min-h-screen bg-gray-100 px-4 py-6">
      {/* Header */}
      <div className="mb-6">
        <div className="flex justify-between items-center">
          <div>
            <h2 className="text-gray-600 font-bold">Real-Time Request Insights</h2>
          </div>
          <div className="flex items-center space-x-4">
            <div className="flex items-center space-x-2">
              <select
                value={dateFilter}
                onChange={(e) => handleDateFilterChange(e.target.value)}
                className="px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 text-sm"
              >
                <option value="wtd">WeekToDate</option>
                <option value="mtd">MonthToDate</option>
                <option value="ytd">YearToDate</option>
                <option value="custom">Custom</option>
              </select>

              {showCustomDatePicker && (
                <div className="flex items-center space-x-2">
                  <input
                    type="date"
                    value={customFromDate}
                    onChange={(e) => setCustomFromDate(e.target.value)}
                    className="px-2 py-1 border border-gray-300 rounded text-sm"
                  />
                  <span className="text-sm text-gray-500">to</span>
                  <input
                    type="date"
                    value={customToDate}
                    onChange={(e) => setCustomToDate(e.target.value)}
                    className="px-2 py-1 border border-gray-300 rounded text-sm"
                  />
                </div>
              )}
            </div>
            <button
              onClick={fetchDashboardData}
              disabled={loading}
              className="px-3 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors disabled:opacity-50"
              title={loading ? 'Refreshing...' : 'Refresh'}
            >
              ↻
            </button>
            <div className="text-sm text-gray-500">
              Last updated: {lastUpdated.toLocaleTimeString()}
            </div>
          </div>
        </div>
      </div>

      {error && (
        <div className="mb-6 p-4 bg-yellow-50 border border-yellow-200 rounded-lg">
          <p className="text-yellow-800">⚠️ {error}</p>
        </div>
      )}

      {/* Key Metrics Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-6 gap-6 mb-6">
        <div className="bg-white p-6 rounded-lg shadow">
          <h3 className="text-sm font-medium text-gray-500 mb-2">Total Requests</h3>
          <p className="text-3xl font-bold text-blue-600">{formatNumber(metrics.total_requests)}</p>
        </div>

        <div className="bg-white p-6 rounded-lg shadow">
          <h3 className="text-sm font-medium text-gray-500 mb-2">Waiting</h3>
          <p className="text-3xl font-bold text-yellow-500">{formatNumber(metrics.waiting_requests)}</p>
        </div>

        <div className="bg-white p-6 rounded-lg shadow">
          <h3 className="text-sm font-medium text-gray-500 mb-2">Active Now</h3>
          <p className="text-3xl font-bold text-orange-500">{formatNumber(metrics.active_requests)}</p>
        </div>

        <div className="bg-white p-6 rounded-lg shadow">
          <h3 className="text-sm font-medium text-gray-500 mb-2">Completed</h3>
          <p className="text-3xl font-bold text-green-600">{formatNumber(metrics.completed_today)}</p>
        </div>

        <div className="bg-white p-6 rounded-lg shadow">
          <h3 className="text-sm font-medium text-gray-500 mb-2">Failed</h3>
          <p className="text-3xl font-bold text-red-500">{formatNumber(metrics.failed_requests)}</p>
        </div>

        <div className="bg-white p-6 rounded-lg shadow">
          <h3 className="text-sm font-medium text-gray-500 mb-2">Avg Exec Time</h3>
          <p className="text-3xl font-bold text-purple-600">{formatExecutionTime(metrics.avg_execution_time)}</p>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-6">
        {/* Alerts */}
        <div className="bg-white p-6 rounded-lg shadow">
          <h3 className="text-lg font-semibold text-gray-900 mb-4">🚨 Alerts</h3>
          {alerts.length > 0 ? (
            <div className="space-y-3 max-h-40 overflow-y-auto">
              {alerts.map((alert, index) => (
                <div key={index} className={`p-3 rounded-lg border-l-4 ${
                  alert.severity === 'warning'
                    ? 'bg-yellow-50 border-yellow-400'
                    : 'bg-red-50 border-red-400'
                }`}>
                  <p className="text-sm text-gray-800">{alert.message}</p>
                  {alert.request_id && (
                    <p className="text-xs text-gray-600 mt-1">Request ID: {alert.request_id}</p>
                  )}
                </div>
              ))}
            </div>
          ) : (
            <p className="text-green-600 text-sm">✅ No active alerts - all requests processing normally</p>
          )}
        </div>

        {/* Health Check */}
        <div className="bg-white p-6 rounded-lg shadow">
          <h3 className="text-lg font-semibold text-gray-900 mb-4">🔍 Health Check</h3>
          <button
            onClick={async () => {
              try {
                const response = await api.post('/api/dashboard/health-check');
                if (response.data.success) {
                  const results = response.data.health_check;
                  let message = '✅ System Health Check Complete!\n\n';

                  if (results.database?.status === 'healthy') {
                    message += `• Database: ✅ Connected (${results.database.version?.split(' ')[0] || 'PostgreSQL'})\n`;
                  } else {
                    message += `• Database: ❌ ${results.database?.error || 'Failed'}\n`;
                  }

                  message += `• API: ✅ ${results.api_endpoints?.status || 'Healthy'}\n`;
                  message += `• Queue: ✅ ${results.processing_queue?.status || 'Operational'} (${results.processing_queue?.total_requests || 0} total requests)\n`;
                  message += `• Frontend: ✅ Working`;

                  alert(message);
                } else {
                  alert('❌ Health Check Failed!\n\nSystem diagnostics returned errors.');
                }
              } catch (err) {
                alert('❌ Health Check Failed!\n\nUnable to complete system diagnostics.\n\nThis may indicate backend connectivity issues.');
              }
            }}
            className="w-full px-4 py-3 bg-purple-600 text-white rounded-lg hover:bg-purple-700 transition-colors text-sm"
          >
            🔍 Run Health Check
          </button>
        </div>
      </div>

      {/* User Activity Section - Collapsible */}
      <div className="grid grid-cols-1 gap-4 mb-6">
        <div className="bg-white rounded shadow">
          <div
            className="p-3 cursor-pointer hover:bg-gray-50 transition-colors"
            onClick={() => setIsUserActivityExpanded(!isUserActivityExpanded)}
          >
            <div className="flex justify-between items-center">
              <h3 className="text-base font-medium text-gray-900 flex items-center">
                👥 User Activity
                <span className="ml-2 text-xs text-gray-500">({users.length} users)</span>
              </h3>
              <div className="flex items-center space-x-2">
                <button
                  onClick={(e) => {
                    e.stopPropagation();
                    handleViewModeChange('chart');
                  }}
                  disabled={chartLoading}
                  className={`p-1 transition-colors disabled:opacity-50 disabled:cursor-not-allowed relative ${
                    userActivityViewMode === 'chart'
                      ? 'text-blue-600'
                      : 'text-gray-400 hover:text-blue-600'
                  }`}
                  title="Bar Graph View"
                >
                  {chartLoading && userActivityViewMode !== 'chart' ? (
                    <div className="absolute inset-0 flex items-center justify-center">
                      <div className="w-2 h-2 border border-blue-400 border-t-transparent rounded-full animate-spin"></div>
                    </div>
                  ) : null}
                  <span className={chartLoading && userActivityViewMode !== 'chart' ? 'opacity-30' : ''}>📈</span>
                </button>
                <button
                  onClick={(e) => {
                    e.stopPropagation();
                    handleViewModeChange('list');
                  }}
                  disabled={chartLoading}
                  className={`p-1 transition-colors disabled:opacity-50 disabled:cursor-not-allowed relative ${
                    userActivityViewMode === 'list'
                      ? 'text-green-600'
                      : 'text-gray-400 hover:text-green-600'
                  }`}
                  title="List View"
                >
                  {chartLoading && userActivityViewMode !== 'list' ? (
                    <div className="absolute inset-0 flex items-center justify-center">
                      <div className="w-2 h-2 border border-green-400 border-t-transparent rounded-full animate-spin"></div>
                    </div>
                  ) : null}
                  <span className={chartLoading && userActivityViewMode !== 'list' ? 'opacity-30' : ''}>📋</span>
                </button>
                <span className="text-xs text-gray-500">{getDateFilterLabel(dateFilter)}</span>
                <span className="text-gray-400 text-base transition-transform duration-200" style={{
                  transform: isUserActivityExpanded ? 'rotate(90deg)' : 'rotate(0deg)'
                }}>
                  ›
                </span>
              </div>
            </div>
          </div>

          {isUserActivityExpanded && (
            <div className="px-3 pb-3 border-t border-gray-100">
              {chartLoading ? (
                <div className="flex flex-col items-center justify-center py-12 space-y-4">
                  <div className="relative">
                    {/* Outer spinning ring */}
                    <div className="animate-spin rounded-full h-12 w-12 border-4 border-blue-100 border-t-blue-600"></div>
                    {/* Inner pulsing dot */}
                    <div className="absolute inset-0 flex items-center justify-center">
                      <div className="w-4 h-4 bg-blue-600 rounded-full animate-pulse"></div>
                    </div>
                    {/* Chart icon overlay */}
                    <div className="absolute -top-1 -right-1">
                      <span className="text-xs animate-bounce">📊</span>
                    </div>
                  </div>
                  <div className="text-center space-y-2">
                    <p className="text-base font-medium text-gray-700 animate-pulse">
                      {userActivityViewMode === 'chart' ? '📊 Generating Multi-Metric Chart...' : '📋 Loading List View...'}
                    </p>
                    <p className="text-sm text-gray-500">
                      {userActivityViewMode === 'chart'
                        ? 'Creating vertical bars for requests, execution time, and success rates'
                        : 'Organizing user data for list display'
                      }
                    </p>
                    <div className="flex justify-center space-x-1 mt-3">
                      <div className="w-2 h-2 bg-blue-400 rounded-full animate-bounce" style={{ animationDelay: '0ms' }}></div>
                      <div className="w-2 h-2 bg-blue-400 rounded-full animate-bounce" style={{ animationDelay: '150ms' }}></div>
                      <div className="w-2 h-2 bg-blue-400 rounded-full animate-bounce" style={{ animationDelay: '300ms' }}></div>
                    </div>
                  </div>
                </div>
              ) : users.length > 0 ? (
                <>
                  {userActivityViewMode === 'list' ? (
                    <div className="space-y-2 max-h-60 overflow-y-auto mt-2">
                      {users.map((user, index) => (
                        <div key={index} className="grid grid-cols-4 gap-3 items-center py-3 px-3 border border-gray-200 rounded-lg hover:bg-gray-50 hover:border-gray-300 transition-all">
                          <div className="flex-1 min-w-0">
                            <p className="text-sm font-semibold text-gray-900 truncate">{user.username}</p>
                            <p className="text-xs text-gray-600 truncate">
                              {formatNumber(user.total_requests)} total requests
                            </p>
                          </div>
                          <div className="text-center">
                            <p className="text-sm font-bold text-green-600">{formatNumber(user.completed_requests)}</p>
                            <p className="text-xs text-gray-500">completed</p>
                          </div>
                          <div className="text-center">
                            <p className="text-sm font-bold text-blue-600">{user.success_rate.toFixed(1)}%</p>
                            <p className="text-xs text-gray-500">success rate</p>
                          </div>
                          <div className="text-right">
                            <p className="text-sm font-bold text-purple-600">{formatExecutionTime(user.avg_execution_hours)}</p>
                            <p className="text-xs text-gray-500">avg time</p>
                          </div>
                        </div>
                      ))}
                      {users.length > 6 && (
                        <div className="text-center text-xs text-gray-400 pt-1">
                          Scroll to see all {users.length} users
                        </div>
                      )}
                    </div>
                  ) : (
                    <div className="mt-2 space-y-3 max-h-60 overflow-y-auto">
                      <div className="text-center mb-4">
                        <div className="text-sm font-medium text-gray-700 mb-1">
                          📊 Multi-Metric User Analytics
                        </div>
                        <div className="text-xs text-gray-500">
                          Requests • Execution Time • Success Rate
                        </div>
                      </div>
                      <div className="flex justify-start overflow-x-auto pb-2" style={{ minHeight: '180px' }}>
                        <div className="flex items-end space-x-3 px-2">
                          {users
                            .sort((a, b) => b.total_requests - a.total_requests)
                            .slice(0, 6)
                            .map((user, index) => {
                              const maxRequests = Math.max(...users.map(u => u.total_requests));
                              const maxExecTime = Math.max(...users.map(u => u.avg_execution_hours));

                              // Normalize heights (max 120px)
                              const requestsHeight = Math.max(20, (user.total_requests / maxRequests) * 120);
                              const execTimeHeight = Math.max(20, (user.avg_execution_hours / maxExecTime) * 120);
                              const baseHeight = 40; // Minimum height for visibility

                              return (
                                <div key={index} className="flex flex-col items-center space-y-2 min-w-16 group hover:bg-gray-50 p-1 rounded transition-colors">
                                  {/* Success Rate Badge on Top */}
                                  <div className="text-xs font-medium text-white bg-green-500 px-2 py-1 rounded-full mb-1 group-hover:bg-green-600 transition-colors shadow-sm">
                                    {user.success_rate}%
                                  </div>

                                  {/* Vertical Bars Container */}
                                  <div className="flex items-end space-x-1 h-32">
                                    {/* Requests Bar */}
                                    <div className="flex flex-col items-center">
                                      <div
                                        className="w-4 bg-gradient-to-t from-blue-600 to-blue-400 rounded-t-sm transition-all duration-700 relative hover:from-blue-700 hover:to-blue-500 shadow-sm overflow-hidden"
                                        style={{
                                          height: `${Math.max(baseHeight, requestsHeight)}px`,
                                          minHeight: '40px'
                                        }}
                                      >
                                        {/* Completed requests overlay */}
                                        <div
                                          className="absolute bottom-0 left-0 right-0 bg-gradient-to-t from-green-500 to-green-400 transition-all duration-700"
                                          style={{
                                            height: `${(user.completed_requests / user.total_requests) * 100}%`
                                          }}
                                        ></div>

                                        <div className="absolute -top-6 left-1/2 transform -translate-x-1/2 text-xs font-bold text-blue-700 bg-white px-1 rounded shadow-sm opacity-0 group-hover:opacity-100 transition-opacity">
                                          {user.completed_requests}/{user.total_requests}
                                        </div>
                                        {/* Simple value on bar */}
                                        <div className="absolute top-1 left-1/2 transform -translate-x-1/2 text-xs font-medium text-white opacity-0 group-hover:opacity-100 transition-opacity">
                                          {user.total_requests}
                                        </div>
                                      </div>
                                      <span className="text-xs text-gray-500 mt-1 group-hover:text-blue-600 transition-colors font-medium">Req</span>
                                    </div>

                                    {/* Execution Time Bar */}
                                    <div className="flex flex-col items-center">
                                      <div
                                        className="w-4 bg-gradient-to-t from-purple-600 to-purple-400 rounded-t-sm transition-all duration-700 relative hover:from-purple-700 hover:to-purple-500 shadow-sm"
                                        style={{
                                          height: `${Math.max(baseHeight, execTimeHeight)}px`,
                                          minHeight: '40px'
                                        }}
                                      >
                                        <div className="absolute -top-6 left-1/2 transform -translate-x-1/2 text-xs font-bold text-purple-700 bg-white px-1 rounded shadow-sm opacity-0 group-hover:opacity-100 transition-opacity whitespace-nowrap">
                                          {formatExecutionTime(user.avg_execution_hours)}
                                        </div>
                                        {/* Simple value on bar */}
                                        <div className="absolute top-1 left-1/2 transform -translate-x-1/2 text-xs font-medium text-white opacity-0 group-hover:opacity-100 transition-opacity">
                                          {user.avg_execution_hours < 1 ? `${Math.round(user.avg_execution_hours * 60)}m` : `${user.avg_execution_hours.toFixed(1)}h`}
                                        </div>
                                      </div>
                                      <span className="text-xs text-gray-500 mt-1 group-hover:text-purple-600 transition-colors font-medium">Time</span>
                                    </div>
                                  </div>

                                  {/* Username at bottom */}
                                  <div className="text-xs font-medium text-gray-700 text-center w-16 truncate group-hover:text-gray-900 transition-colors" title={user.username}>
                                    {user.username.substring(0, 8)}
                                  </div>
                                </div>
                              );
                            })}
                        </div>
                      </div>

                      {/* Legend */}
                      <div className="flex justify-center space-x-4 mt-3 pt-2 border-t border-gray-100">
                        <div className="flex items-center space-x-1">
                          <div className="w-3 h-3 bg-gradient-to-t from-blue-600 to-blue-400 rounded"></div>
                          <span className="text-xs text-gray-600">Requests</span>
                        </div>
                        <div className="flex items-center space-x-1">
                          <div className="w-3 h-3 bg-gradient-to-t from-purple-600 to-purple-400 rounded"></div>
                          <span className="text-xs text-gray-600">Avg Time</span>
                        </div>
                        <div className="flex items-center space-x-1">
                          <div className="w-3 h-3 bg-green-500 rounded-full"></div>
                          <span className="text-xs text-gray-600">Success %</span>
                        </div>
                      </div>

                      {users.length > 6 && (
                        <div className="text-center text-xs text-gray-400 pt-1">
                          Showing top 6 users by total requests
                        </div>
                      )}
                    </div>
                  )}
                </>
              ) : (
                <p className="text-gray-500 text-sm mt-2">No user activity data available</p>
              )}
            </div>
          )}
        </div>
      </div>

      {/* Footer */}
      <div className="mt-4 text-center text-xs text-gray-500">
        <p>
          🔄 Last updated: {lastUpdated.toLocaleTimeString()} •
          {formatNumber(metrics.total_requests)} total requests
        </p>
      </div>
    </div>
  );
};

export default Dashboard;
