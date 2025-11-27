import React from 'react';

const Dashboard: React.FC = () => {
  return (
    <div className="w-full h-screen"> {/* Full width and height, no centering */}
      <div className="bg-white w-full h-full pl-0 pr-12 py-12 flex items-center justify-center"> {/* Remove left padding, keep others */}
        <div className="text-center">
          <div className="w-16 h-16 border-4 border-blue-200 border-t-blue-600 rounded-full animate-spin mx-auto mb-6"></div>
          <h2 className="text-2xl font-semibold text-gray-800 mb-3">Dashboard</h2>
          <p className="text-gray-600">Coming soon in Phase 3</p>
        </div>
      </div>
    </div>
  );
};

export default Dashboard;
