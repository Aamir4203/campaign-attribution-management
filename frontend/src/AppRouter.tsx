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

        {/* Root route */}
        <Route path="/" element={<Navigate to="/dashboard" replace />} />

        {/* Protected routes */}
        <Route path="/dashboard" element={
          <ProtectedRoute>
            <Layout>
              <Dashboard />
            </Layout>
          </ProtectedRoute>
        } />

        <Route path="/add-request" element={
          <ProtectedRoute>
            <Layout>
              <AddRequest />
            </Layout>
          </ProtectedRoute>
        } />

        <Route path="/requests" element={
          <ProtectedRoute>
            <Layout>
              <RequestLogs />
            </Layout>
          </ProtectedRoute>
        } />
      </Routes>
    </Router>
  );
};

export default AppRouter;
