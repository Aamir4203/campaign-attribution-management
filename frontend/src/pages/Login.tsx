import React from 'react';
import { Navigate, useLocation, useNavigate } from 'react-router-dom';
import { useAuth } from '../components/Auth/AuthProvider';
import LoginForm from '../components/Auth/LoginForm';

const Login: React.FC = () => {
  const { login, isAuthenticated, isLoading } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();

  // Redirect if already authenticated
  if (isAuthenticated) {
    const from = location.state?.from?.pathname || '/add-request';
    return <Navigate to={from} replace />;
  }

  const handleLogin = async (username: string, password: string) => {
    const result = await login(username, password);

    if (result.success) {
      // Redirect to the page they were trying to access, or default to add-request
      const from = location.state?.from?.pathname || '/add-request';
      navigate(from, { replace: true });
    }

    return result;
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100 flex items-center justify-center p-6">
      <div className="w-full max-w-md">
        {/* Header */}
        <div className="text-center mb-8">
          {/* Logo/Icon */}
          <div className="w-16 h-16 bg-gradient-to-r from-blue-600 to-indigo-600 rounded-full flex items-center justify-center mx-auto mb-4 shadow-lg">
            <svg className="w-8 h-8 text-white" fill="currentColor" viewBox="0 0 20 20">
              <path d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"/>
            </svg>
          </div>

         {/* <h1 className="text-3xl font-bold text-gray-900 mb-2">
            CAM Login
          </h1>*/}
          <p className="text-lg font-bold text-black-600">
            Campaign Attribution Management
          </p>
        </div>

        {/* Login Form Card */}
        <div className="bg-white rounded-lg shadow-lg p-8 border border-gray-200">
          <h2 className="text-xl font-semibold text-gray-900 mb-6 text-center">
            Sign In
          </h2>

          <LoginForm onSubmit={handleLogin} isLoading={isLoading} />
        </div>

        {/* Help Text */}
        <div className="mt-6 text-center">
          <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
            <p className="text-sm text-blue-700">
              <strong>Need access?</strong> Contact your administrator.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
};

export default Login;
