import React from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { Layout } from './components';
import { ProtectedRoute } from './components/Auth';
import Dashboard from './pages/Dashboard';
import AddRequest from './pages/AddRequest';
import RequestLogs from './pages/RequestLogs';
import Login from './pages/Login';

const AppRouter: React.FC = () => {
  return (
    <Router>
      <Routes>
        {/* Public route - Login */}
        <Route path="/login" element={<Login />} />

        {/* Protected routes - wrapped in Layout */}
        <Route path="/*" element={
          <ProtectedRoute>
            <Layout>
              <Routes>
                <Route path="/" element={<Navigate to="/add-request" replace />} />
                <Route path="/dashboard" element={<Dashboard />} />
                <Route path="/add-request" element={<AddRequest />} />
                <Route path="/requests" element={<RequestLogs />} />
              </Routes>
            </Layout>
          </ProtectedRoute>
        } />
      </Routes>
    </Router>
  );
};

export default AppRouter;
