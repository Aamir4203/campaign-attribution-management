import React, { useState } from 'react';

interface FlushDeliveryDataModalProps {
  isOpen: boolean;
  onClose: () => void;
  onConfirm: () => void;
  clientName: string;
  weekValue: string;
  loading?: boolean;
}

const FlushDeliveryDataModal: React.FC<FlushDeliveryDataModalProps> = ({
  isOpen,
  onClose,
  onConfirm,
  clientName,
  weekValue,
  loading = false
}) => {
  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div className="bg-white rounded-lg shadow-xl p-6 max-w-md w-full mx-4">
        <div className="text-center">
          <h3 className="text-lg font-medium text-gray-900 mb-4">
            This is new week cycle. Please confirm.
          </h3>
          <div className="bg-gray-50 rounded-lg p-3 mb-6">
            <p className="text-sm text-gray-700">
              <span className="font-medium">Week:</span> {weekValue}
            </p>
            <p className="text-sm text-gray-700">
              <span className="font-medium">Client:</span> {clientName}
            </p>
          </div>
          <div className="flex justify-center space-x-3">
            <button
              onClick={onClose}
              disabled={loading}
              className="px-6 py-2 bg-gray-200 text-gray-700 rounded-lg hover:bg-gray-300 transition-colors font-medium disabled:opacity-50 disabled:cursor-not-allowed"
            >
              No
            </button>
            <button
              onClick={onConfirm}
              disabled={loading}
              className="px-6 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 transition-colors font-medium flex items-center space-x-2 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {loading ? (
                <>
                  <div className="animate-spin rounded-full h-4 w-4 border-2 border-white border-t-transparent"></div>
                  <span>Processing...</span>
                </>
              ) : (
                <span>Yes</span>
              )}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};

export default FlushDeliveryDataModal;
