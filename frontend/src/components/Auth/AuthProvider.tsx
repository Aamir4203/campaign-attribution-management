import React, { createContext, useContext, useEffect, useState } from 'react';
import authService from '../../services/authService';

interface User {
  username: string;
  loginTime: string;
  token: string;
}

interface AuthContextType {
  user: User | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  login: (username: string, password: string) => Promise<{ success: boolean; message: string }>;
  logout: () => Promise<void>;
  getUsername: () => string | null;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};

interface AuthProviderProps {
  children: React.ReactNode;
}

export const AuthProvider: React.FC<AuthProviderProps> = ({ children }) => {
  const [user, setUser] = useState<User | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  // Initialize auth state on component mount
  useEffect(() => {
    initializeAuth();
  }, []);

  const initializeAuth = async () => {
    try {
      setIsLoading(true);

      // Check if user has valid session
      const isValid = await authService.initialize();

      if (isValid) {
        const currentUser = authService.getCurrentUser();
        setUser(currentUser);
        console.log('✅ User session restored:', currentUser?.username);
      } else {
        setUser(null);
        console.log('ℹ️ No valid session found');
      }
    } catch (error) {
      console.error('❌ Auth initialization failed:', error);
      setUser(null);
    } finally {
      setIsLoading(false);
    }
  };

  const login = async (username: string, password: string) => {
    try {
      setIsLoading(true);

      const response = await authService.login({ username, password });

      if (response.success) {
        const currentUser = authService.getCurrentUser();
        setUser(currentUser);
        console.log('✅ Login successful:', username);
      }

      return response;
    } catch (error) {
      console.error('❌ Login error in context:', error);
      return {
        success: false,
        message: 'Login failed due to unexpected error'
      };
    } finally {
      setIsLoading(false);
    }
  };

  const logout = async () => {
    try {
      setIsLoading(true);
      await authService.logout();
      setUser(null);
      console.log('✅ Logout successful');
    } catch (error) {
      console.error('❌ Logout error:', error);
    } finally {
      setIsLoading(false);
    }
  };

  const getUsername = (): string | null => {
    return authService.getUsername();
  };

  const value: AuthContextType = {
    user,
    isAuthenticated: !!user,
    isLoading,
    login,
    logout,
    getUsername
  };

  return (
    <AuthContext.Provider value={value}>
      {children}
    </AuthContext.Provider>
  );
};
