import api from './api';

// Types based on actual backend API responses
export interface Client {
  client_name: string; // Backend only returns client_name for the dropdown
}

export interface CheckClientResponse {
  exists: boolean;
  client_id?: number;
}

export interface AddClientResponse {
  success: boolean;
  client_id?: number;
  message?: string;
}

export interface User {
  username: string;
}

export class ClientService {
  // Get all clients for dropdown (from addRequest.html route)
  static async getClients(): Promise<Client[]> {
    try {
      console.log('🔗 Fetching clients from http://localhost:5000/api/clients');
      const response = await api.get('/api/clients');

      console.log('📡 Raw response:', response);
      console.log('📋 Response data:', response.data);

      // Validate response structure
      if (!response.data) {
        throw new Error('No data in response');
      }

      if (response.data.success !== true) {
        throw new Error(response.data.error || 'Backend returned unsuccessful response');
      }

      if (!Array.isArray(response.data.clients)) {
        throw new Error('Clients data is not an array');
      }

      const clients = response.data.clients;
      console.log(`✅ Successfully loaded ${clients.length} clients:`, clients.slice(0, 3));

      return clients;
    } catch (error: any) {
      console.error('❌ Client loading error:', error);
      console.error('🔍 Error message:', error.message);
      console.error('🔍 Error response:', error.response?.data);
      console.error('🔍 Error status:', error.response?.status);

      // Re-throw the actual error for proper handling upstream
      throw new Error(`Failed to load clients: ${error.message}`);
    }
  }

  // Get all users for "Added By" dropdown
  static async getUsers(): Promise<User[]> {
    try {
      const response = await api.get('/api/users');

      if (!response.data.success) {
        throw new Error(response.data.error || 'Backend returned unsuccessful response');
      }

      const users = response.data.users || [];

      return users;
    } catch (error) {
      throw new Error('Failed to load users. Please try again.');
    }
  }

  // Check if client exists (from /check_client route)
  static async checkClient(clientName: string): Promise<CheckClientResponse> {
    try {
      const response = await api.post('/check_client', {
        client_name: clientName
      });
      return response.data;
    } catch (error) {
      console.error('Failed to check client:', error);
      throw new Error('Failed to verify client. Please try again.');
    }
  }

  // Add new client (from /add_client route)
  static async addClient(clientName: string): Promise<AddClientResponse> {
    try {
      const response = await api.post('/add_client', {
        client_name: clientName
      });
      return response.data;
    } catch (error) {
      console.error('Failed to add client:', error);
      throw new Error('Failed to add new client. Please try again.');
    }
  }

  // Flush total delivery data for a client (W1/W2 week logic)
  static async flushDeliveryData(clientName: string): Promise<any> {
    try {
      console.log('🗑️ Flushing delivery data for client:', clientName);
      const response = await api.post(`/api/clients/${encodeURIComponent(clientName)}/flush-delivery-data`);

      console.log('✅ Flush response:', response.data);
      return response.data;
    } catch (error: any) {
      console.error('❌ Flush delivery data error:', error);
      throw error;
    }
  }
}

export default ClientService;
