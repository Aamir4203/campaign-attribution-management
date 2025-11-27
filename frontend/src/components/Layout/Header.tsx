import React, { useState } from 'react';
import { useAuth } from '../Auth';

interface HeaderProps {
  sidebarOpen?: boolean;
  onToggleSidebar?: () => void;
}

export const Header: React.FC<HeaderProps> = ({ sidebarOpen = true, onToggleSidebar }) => {
  const { user, logout, getUsername } = useAuth();
  const [showLogoutModal, setShowLogoutModal] = useState(false);

  const handleLogoutClick = () => {
    setShowLogoutModal(true);
  };

  const handleLogoutConfirm = async () => {
    setShowLogoutModal(false);
    await logout();
  };

  const handleLogoutCancel = () => {
    setShowLogoutModal(false);
  };

  return (
    <header className="fixed top-0 left-0 right-0 bg-white border-b border-gray-200 shadow-sm h-20 flex items-center justify-between px-6 z-50">{/* Made header fixed */}
      {/* Left Section - Logo and Toggle */}
      <div className="flex items-center space-x-4">
        {/* Sidebar Toggle Button */}
        <button
          onClick={onToggleSidebar}
          className="p-2 rounded-lg hover:bg-gray-100 transition-colors lg:hidden"
        >
          <svg className="w-6 h-6 text-gray-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M4 6h16M4 12h16M4 18h16"/>
          </svg>
        </button>

        {/* Logo and Title */}
        <div className="flex items-center">
          <div className="w-10 h-10 bg-gradient-to-r from-blue-600 to-indigo-600 rounded-lg flex items-center justify-center mr-3 shadow-lg">
            <span className="text-white font-bold text-lg">C</span>
          </div>
          <div>
            <h1 className="text-xl font-bold text-gray-900">CAM</h1>
            <p className="text-sm text-gray-500">Campaign Attribution Management</p>
          </div>
        </div>
      </div>

      {/* Right Section - User Info and Logout */}
      <div className="flex items-center space-x-4">
        {/* User Welcome */}
        <div className="hidden md:block text-right">
          <p className="text-sm font-medium text-gray-900">
            Welcome, {getUsername() || 'User'}
          </p>
          <p className="text-xs text-gray-500">
            {user?.loginTime ? new Date(user.loginTime).toLocaleDateString() : 'Today'}
          </p>
        </div>

        {/* User Avatar */}
        <div className="w-8 h-8 bg-gradient-to-r from-purple-500 to-pink-500 rounded-full flex items-center justify-center">
          <span className="text-white text-sm font-semibold">
            {(getUsername() || 'U').charAt(0).toUpperCase()}
          </span>
        </div>

        {/* Logout Button */}
        <button
          onClick={handleLogoutClick}
          className="flex items-center space-x-2 px-3 py-2 rounded-lg bg-red-50 hover:bg-red-100 text-red-700 transition-colors group"
          title="Logout"
        >
          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M17 16l4-4m0 0l-4-4m4 4H7m6 4v1a3 3 0 01-3 3H6a3 3 0 01-3-3V7a3 3 0 013-3h4a3 3 0 013 3v1"/>
          </svg>
          <span className="hidden sm:block text-sm font-medium">Logout</span>
        </button>
      </div>

      {/* Custom Logout Confirmation Modal */}
      {showLogoutModal && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg shadow-xl p-6 w-96 max-w-md mx-4">
            <div className="flex items-center justify-center w-12 h-12 mx-auto mb-4 bg-red-100 rounded-full">
              <svg className="w-6 h-6 text-red-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M17 16l4-4m0 0l-4-4m4 4H7m6 4v1a3 3 0 01-3 3H6a3 3 0 01-3-3V7a3 3 0 013-3h4a3 3 0 013 3v1"/>
              </svg>
            </div>

            <h3 className="text-lg font-semibold text-gray-900 text-center mb-2">
              Confirm Logout
            </h3>

            <p className="text-gray-600 text-center mb-6">
              Do you still want to logout?
            </p>

            <div className="flex space-x-3">
              <button
                onClick={handleLogoutCancel}
                className="flex-1 px-4 py-2 border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-50 transition-colors"
              >
                Cancel
              </button>
              <button
                onClick={handleLogoutConfirm}
                className="flex-1 px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 transition-colors"
              >
                Logout
              </button>
            </div>
          </div>
        </div>
      )}
    </header>
  );
};

export default Header;
