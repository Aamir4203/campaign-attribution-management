import api from './api';

export interface LoginCredentials {
  username: string;
  password: string;
}

export interface LoginResponse {
  success: boolean;
  message: string;
  token?: string;
  expires_in?: number;
}

export interface SessionInfo {
  success: boolean;
  user_id?: number;
  username?: string;
  expires_at?: string;
  message?: string;
}

class AuthService {
  private tokenKey = 'cam_auth_token';
  private userKey = 'cam_user_info';

  /**
   * Login user with username and password
   */
  async login(credentials: LoginCredentials): Promise<LoginResponse> {
    try {
      const response = await api.post('/api/login', credentials);

      if (response.data.success) {
        // Store token and user info in sessionStorage (48-hour expiry handled by backend)
        sessionStorage.setItem(this.tokenKey, response.data.token);
        sessionStorage.setItem(this.userKey, JSON.stringify({
          username: credentials.username,
          loginTime: new Date().toISOString(),
          token: response.data.token
        }));

        console.log('🔑 Login successful:', credentials.username);
      }

      return response.data;
    } catch (error: any) {
      console.error('❌ Login failed:', error);
      return {
        success: false,
        message: error.response?.data?.message || 'Login failed'
      };
    }
  }

  /**
   * Logout user and clear session
   */
  async logout(): Promise<void> {
    try {
      const token = this.getToken();

      if (token) {
        // Call backend logout to invalidate session
        await api.post('/api/logout', { token });
      }
    } catch (error) {
      console.error('⚠️ Logout API call failed:', error);
    } finally {
      // Always clear local storage regardless of API call success
      this.clearSession();
      console.log('🔑 Logout completed');
    }
  }

  /**
   * Get current authentication token
   */
  getToken(): string | null {
    return sessionStorage.getItem(this.tokenKey);
  }

  /**
   * Get current user information
   */
  getCurrentUser(): { username: string; loginTime: string; token: string } | null {
    try {
      const userInfo = sessionStorage.getItem(this.userKey);
      return userInfo ? JSON.parse(userInfo) : null;
    } catch (error) {
      console.error('❌ Failed to parse user info:', error);
      return null;
    }
  }

  /**
   * Check if user is authenticated
   */
  isAuthenticated(): boolean {
    const token = this.getToken();
    const user = this.getCurrentUser();

    return !!(token && user);
  }

  /**
   * Verify session with backend
   */
  async verifySession(): Promise<boolean> {
    try {
      const token = this.getToken();

      if (!token) {
        return false;
      }

      const response = await api.get('/api/session_info', {
        headers: {
          'Authorization': token
        }
      });

      return response.data.success;
    } catch (error) {
      console.error('⚠️ Session verification failed:', error);
      this.clearSession(); // Clear invalid session
      return false;
    }
  }

  /**
   * Clear session data
   */
  clearSession(): void {
    sessionStorage.removeItem(this.tokenKey);
    sessionStorage.removeItem(this.userKey);
  }

  /**
   * Get username for form auto-population
   */
  getUsername(): string | null {
    const user = this.getCurrentUser();
    return user ? user.username : null;
  }

  /**
   * Initialize auth service - verify existing session on app load
   */
  async initialize(): Promise<boolean> {
    if (!this.isAuthenticated()) {
      return false;
    }

    // Verify session is still valid with backend
    const isValid = await this.verifySession();

    if (!isValid) {
      this.clearSession();
      return false;
    }

    console.log('✅ Session verified, user authenticated');
    return true;
  }
}

export default new AuthService();
