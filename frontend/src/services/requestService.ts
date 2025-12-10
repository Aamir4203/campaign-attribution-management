// Request Management Service
import api from './api';

export interface RequestsParams {
  page?: number;
  limit?: number;
  search?: string;
}

export interface RequestsResponse {
  requests: any[];
  total: number;
  page: number;
  totalPages: number;
}

export const requestService = {
  // Get requests with pagination and search
  async getRequests(params: RequestsParams = {}): Promise<RequestsResponse> {
    const { page = 1, limit = 50, search = '' } = params;

    const queryParams = new URLSearchParams({
      page: page.toString(),
      limit: limit.toString(),
      ...(search && { search })
    });

    console.log(`🔄 Fetching requests from API: /api/requests?${queryParams}`);

    try {
      const response = await api.get(`/api/requests?${queryParams}`);
      console.log('✅ Request API response:', response.data);

      if (response.data.success) {
        return {
          requests: response.data.requests || [],
          total: response.data.total || 0,
          page: response.data.page || 1,
          totalPages: response.data.totalPages || 1
        };
      } else {
        throw new Error(response.data.error || 'Failed to fetch requests');
      }
    } catch (error) {
      console.error('❌ Request service error:', error);

      // Return empty data structure for consistent error handling
      return {
        requests: [],
        total: 0,
        page: 1,
        totalPages: 1
      };
    }
  },

  // Get specific request details
  async getRequestDetails(requestId: number) {
    const response = await api.get(`/api/requests/${requestId}/details`);
    return response.data;
  },

  // Get request statistics
  async getRequestStats(requestId: number) {
    const response = await api.get(`/api/requests/${requestId}/stats`);
    return response.data;
  },

  // Download request statistics as Excel
  async downloadRequestStats(requestId: number) {
    const response = await api.get(`/api/requests/${requestId}/stats/download`, {
      responseType: 'blob'
    });
    return response.data;
  },


  // Rerun request with specific type
  async rerunRequest(requestId: number, rerunType: string) {
    const response = await api.post(`/api/requests/${requestId}/rerun`, {
      rerun_type: rerunType
    });
    return response.data;
  },

  // Kill/Cancel request
  async killRequest(requestId: number) {
    const response = await api.post(`/api/requests/${requestId}/kill`);
    return response.data;
  },

  // Download request files
  async downloadRequest(requestId: number) {
    const response = await api.get(`/api/requests/${requestId}/download`, {
      responseType: 'blob'
    });
    return response.data;
  },

  // Upload request files
  async uploadRequest(requestId: number, file: File) {
    const formData = new FormData();
    formData.append('file', file);

    const response = await api.post(`/api/requests/${requestId}/upload`, formData, {
      headers: {
        'Content-Type': 'multipart/form-data'
      }
    });
    return response.data;
  },

  // Get status counts for dashboard
  async getStatusCounts() {
    const response = await api.get('/api/requests/status-counts');
    return response.data;
  },

  // Get table columns for metrics
  async getTableColumns(tableName: string) {
    const response = await api.get(`/api/tables/${tableName}/columns`);
    return response.data;
  },

  // Get client name for a request
  async getClientName(requestId: number) {
    const response = await api.get(`/api/requests/${requestId}/client-name`);
    return response.data;
  },

  // Get week for a request
  async getWeek(requestId: number) {
    const response = await api.get(`/api/requests/${requestId}/week`);
    return response.data;
  },

  // Download metrics with custom queries
  async downloadMetrics(requestId: number, metricsConfig: any) {
    const response = await api.post(`/api/requests/${requestId}/metrics/download`, metricsConfig, {
      responseType: 'blob'
    });
    return response.data;
  }
};
