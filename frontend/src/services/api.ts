import axios, { AxiosInstance, AxiosResponse } from 'axios';
import configService from './configService';

// Get API configuration
const apiConfig = configService.getApiConfig();

// Create axios instance with base configuration from config service
const api: AxiosInstance = axios.create({
  baseURL: apiConfig.baseUrl,
  timeout: apiConfig.timeout,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Request interceptor
api.interceptors.request.use(
  (config) => {
    // Log API calls in debug mode
    if (configService.isDebug()) {
      console.log(`🔗 API Request: ${config.method?.toUpperCase()} ${config.url}`, config.data);
    }
    return config;
  },
  (error) => {
    if (configService.isDebug()) {
      console.error('❌ API Request Error:', error);
    }
    return Promise.reject(error);
  }
);

// Response interceptor for error handling
api.interceptors.response.use(
  (response: AxiosResponse) => {
    if (configService.isDebug()) {
      console.log(`✅ API Response: ${response.config.method?.toUpperCase()} ${response.config.url}`, response.data);
    }
    return response;
  },
  (error) => {
    if (configService.isDebug()) {
      console.error('❌ API Response Error:', error.response?.data || error.message);
    }

    // Handle common error cases
    if (error.response?.status === 404) {
      throw new Error('Resource not found');
    } else if (error.response?.status === 500) {
      throw new Error('Server error occurred');
    } else if (error.code === 'ECONNREFUSED') {
      throw new Error('Unable to connect to server. Please ensure the backend is running.');
    }

    return Promise.reject(error);
  }
);

export default api;
