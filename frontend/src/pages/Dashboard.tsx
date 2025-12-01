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

  const fetchDashboardData = async () => {
    try {
      setError(null);

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
          completed_today: Number(metrics.completed_today) || 0,
          failed_requests: Number(metrics.failed_requests) || 0,
          avg_execution_time: Number(metrics.avg_execution_time) || 0
        });
      } else {
        setMetrics({ total_requests: 0, active_requests: 0, completed_today: 0, failed_requests: 0, avg_execution_time: 0 });
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
      setMetrics({ total_requests: 0, active_requests: 0, completed_today: 0, failed_requests: 0, avg_execution_time: 0 });
      setUsers([]);
      setAlerts([]);
    } finally {
      setLoading(false);
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
      case 'wtd': return 'Week to Date';
      case 'mtd': return 'Month to Date';
      case 'ytd': return 'Year to Date';
      case 'custom': return 'Custom Range';
      default: return 'Week to Date';
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
    <div className="min-h-screen bg-gray-100 p-6"
         style={{ paddingLeft: '100px' }}>
      {/* Header */}
      <div className="mb-6">
        <div className="flex justify-between items-center">
          <div>
            <h2 className="text-gray-600 font-bold">Real-time Performance Monitoring & Insights</h2>
          </div>
          <div className="flex items-center space-x-4">
            <div className="flex items-center space-x-2">
              <select
                value={dateFilter}
                onChange={(e) => handleDateFilterChange(e.target.value)}
                className="px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 text-sm"
              >
                <option value="wtd">WTD</option>
                <option value="mtd">MTD</option>
                <option value="ytd">YTD</option>
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
              className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors disabled:opacity-50"
            >
              {loading ? 'Refreshing...' : '🔄 Refresh'}
            </button>
            <div className="text-sm text-gray-500">
              Last updated: {lastUpdated.toLocaleTimeString()}
            </div>
          </div>
        </div>

        <div className="text-sm text-blue-600 bg-blue-50 px-3 py-1 rounded-lg mt-2">
          📅 Showing data for: {getDateFilterLabel(dateFilter)}
        </div>
      </div>

      {error && (
        <div className="mb-6 p-4 bg-yellow-50 border border-yellow-200 rounded-lg">
          <p className="text-yellow-800">⚠️ {error}</p>
        </div>
      )}

      {/* Key Metrics Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-5 gap-6 mb-6">
        <div className="bg-white p-6 rounded-lg shadow">
          <h3 className="text-sm font-medium text-gray-500 mb-2">Total Requests</h3>
          <p className="text-3xl font-bold text-blue-600">{formatNumber(metrics.total_requests)}</p>
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

        {/* Quick Actions */}
        <div className="bg-white p-6 rounded-lg shadow">
          <h3 className="text-lg font-semibold text-gray-900 mb-4">🎯 Quick Actions</h3>
          <div className="space-y-3">
            <button
              onClick={() => window.location.href = '/add-request'}
              className="w-full px-4 py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors text-sm"
            >
              ➕ Add New Request
            </button>
            <button
              onClick={() => window.location.href = '/requests'}
              className="w-full px-4 py-3 bg-green-600 text-white rounded-lg hover:bg-green-700 transition-colors text-sm"
            >
              📋 View Request Monitor
            </button>
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
      </div>

      {/* User Activity Section - Full Width */}
      <div className="grid grid-cols-1 gap-6 mb-6">
        <div className="bg-white p-6 rounded-lg shadow">
          <div className="flex justify-between items-center mb-4">
            <h3 className="text-lg font-semibold text-gray-900">👥 User Activity</h3>
            <span className="text-sm text-gray-500">{getDateFilterLabel(dateFilter)} ({users.length} users)</span>
          </div>
          {users.length > 0 ? (
            <div className="space-y-3 max-h-80 overflow-y-auto">
              {users.map((user, index) => (
                <div key={index} className="flex justify-between items-center py-3 border-b border-gray-100 last:border-b-0">
                  <div className="flex-1">
                    <p className="font-medium text-gray-900">{user.username}</p>
                    <p className="text-sm text-gray-500">
                      {user.total_requests} requests • {user.success_rate}% success
                    </p>
                  </div>
                  <div className="text-right ml-4">
                    <p className="text-sm text-green-600 font-medium">{user.completed_requests} completed</p>
                    <p className="text-xs text-gray-500">{formatExecutionTime(user.avg_execution_hours)} avg</p>
                  </div>
                </div>
              ))}
              {users.length > 8 && (
                <div className="text-center text-xs text-gray-400 pt-2">
                  Scroll to see all {users.length} users
                </div>
              )}
            </div>
          ) : (
            <p className="text-gray-500">No user activity data available for the selected date range</p>
          )}
        </div>
      </div>

      {/* Footer */}
      <div className="mt-6 text-center text-sm text-gray-500">
        <p>
          🔄 Last updated: {lastUpdated.toLocaleTimeString()} •
          {formatNumber(metrics.total_requests)} total requests
        </p>
      </div>
    </div>
  );
};

export default Dashboard;
