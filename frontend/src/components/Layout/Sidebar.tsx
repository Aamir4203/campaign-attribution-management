import React from 'react';
import { Link, useLocation } from 'react-router-dom';

interface SidebarProps {
  className?: string;
  isOpen?: boolean;
  onToggle?: () => void;
}

export const Sidebar: React.FC<SidebarProps> = ({
  className = '',
  isOpen = true,
  onToggle
}) => {
  const location = useLocation();

  const menuItems = [
    {
      id: 'dashboard',
      label: 'Dashboard',
      icon: '📊',
      path: '/dashboard'
    },
    {
      id: 'add-request',
      label: 'Add Request',
      icon: '➕',
      path: '/add-request'
    },
    {
      id: 'request-logs',
      label: 'Request Monitor',
      icon: '📋',
      path: '/requests'
    }
  ];

  const isActive = (path: string) => location.pathname === path || (path === '/dashboard' && location.pathname === '/');

  if (!isOpen) {
    return (
      <aside className={`fixed left-0 top-20 h-full w-16 bg-white border-r border-gray-200 shadow-sm z-40 ${className}`} style={{ top: '5rem' }}>
        <div className="flex flex-col h-full">
          {/* Collapsed Header with Expand Button */}
          <div className="px-2 py-4 border-b border-gray-200">
            <div className="flex justify-center">
              {onToggle && (
                <button
                  onClick={onToggle}
                  className="p-2 rounded-md hover:bg-gray-100 transition-colors text-gray-600 hover:text-gray-900"
                  title="Expand sidebar"
                >
                  <span className="sr-only">Expand sidebar</span>
                  <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
                  </svg>
                </button>
              )}
            </div>
          </div>

          {/* Collapsed Menu Items */}
          <div className="flex flex-col items-center py-4 space-y-4">
            {menuItems.map((item) => (
              <Link
                key={item.id}
                to={item.path}
                className={`w-10 h-10 flex items-center justify-center rounded-lg transition-colors ${
                  isActive(item.path)
                    ? 'bg-blue-50 text-blue-600'
                    : 'text-gray-600 hover:bg-gray-100 hover:text-gray-900'
                }`}
                title={item.label}
              >
                <span className="text-xl">{item.icon}</span>
              </Link>
            ))}
          </div>
        </div>
      </aside>
    );
  }

  return (
    <aside className={`fixed left-0 top-20 h-full w-60 bg-white border-r border-gray-200 shadow-sm z-40 ${className}`} style={{ top: '5rem' }}>
      <div className="flex flex-col h-full">
        {/* Sidebar Header */}
        <div className="px-6 py-4 border-b border-gray-200">
          <div className="flex items-center justify-between">
            <h2 className="text-lg font-semibold text-gray-900">Navigation</h2>
            {onToggle && (
              <button
                onClick={onToggle}
                className="p-1 rounded-md hover:bg-gray-100 transition-colors text-gray-600 hover:text-gray-900"
                title="Collapse sidebar"
              >
                <span className="sr-only">Toggle sidebar</span>
                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
                </svg>
              </button>
            )}
          </div>
        </div>

        {/* Navigation Menu */}
        <nav className="flex-1 px-4 py-4 space-y-2">
          {menuItems.map((item) => (
            <Link
              key={item.id}
              to={item.path}
              className={`flex items-center px-3 py-2 rounded-lg text-sm font-medium transition-colors ${
                isActive(item.path)
                  ? 'bg-blue-50 text-blue-600 border-l-4 border-blue-600'
                  : 'text-gray-600 hover:text-gray-900 hover:bg-gray-50'
              }`}
            >
              <span className="mr-3 text-lg">{item.icon}</span>
              {item.label}
            </Link>
          ))}
        </nav>

        {/* Sidebar Footer */}
        <div className="px-4 py-4 border-t border-gray-200">
          <div className="text-xs text-gray-500">
            <p className="font-medium">Campaign Attribution Management</p>
            <p>Version 2.0.0</p>
          </div>
        </div>
      </div>
    </aside>
  );
};

export default Sidebar;
