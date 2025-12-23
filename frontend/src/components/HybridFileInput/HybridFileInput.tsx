/**
 * Hybrid File Input Component
 * Toggles between text input and file upload modes
 */

import React, { useState } from 'react';
import { featureFlagService } from '../../services/FeatureFlagService';
import FileUploadWithValidation from '../FileUpload/FileUploadWithValidation';

interface HybridFileInputProps {
  label: string;
  placeholder: string;
  value: string;
  onChange: (value: string) => void;
  fileType?: 'timestamp' | 'cpm' | 'decile';
  clientName?: string;
  weekName?: string;
  error?: string;
  disabled?: boolean;
  className?: string;
}

type InputMode = 'text' | 'upload';

const HybridFileInput: React.FC<HybridFileInputProps> = ({
  label,
  placeholder,
  value,
  onChange,
  fileType,
  clientName = '',
  weekName = '',
  error,
  disabled = false,
  className = ''
}) => {
  const [mode, setMode] = useState<InputMode>('upload');
  const [uploadError, setUploadError] = useState<string>('');

  // Check if upload feature is available
  const isUploadEnabled = featureFlagService.isFileUploadEnabled();
  const isHybridModeEnabled = featureFlagService.isHybridModeEnabled();

  // If upload is not enabled or no file type specified, show only text input
  if (!isUploadEnabled || !fileType || !isHybridModeEnabled) {
    return (
      <div className={className}>
        <label className="block text-xs font-medium text-gray-700 mb-1">
          {label} {!isUploadEnabled && '(Text Mode Only)'}
        </label>
        <input
          type="text"
          value={value}
          onChange={(e) => onChange(e.target.value)}
          placeholder={placeholder}
          disabled={disabled}
          className={`w-full px-3 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 text-sm ${
            error ? 'border-red-300' : 'border-gray-300'
          } ${disabled ? 'bg-gray-100 cursor-not-allowed' : ''}`}
        />
        {error && (
          <p className="mt-1 text-xs text-red-600">{error}</p>
        )}
      </div>
    );
  }

  // Hybrid mode with toggle
  return (
    <div className={className}>
      {/* Label with Mode Toggle */}
      <div className="flex items-center justify-between mb-2">
        <label className="block text-xs font-medium text-gray-700">
          {label}
        </label>
        <div className="flex items-center space-x-2">
          <span className="text-xs text-gray-500">Mode:</span>
          <div className="relative">
            <select
              value={mode}
              onChange={(e) => setMode(e.target.value as InputMode)}
              disabled={disabled}
              className="text-xs border border-gray-300 rounded px-2 py-1 focus:outline-none focus:ring-1 focus:ring-blue-500"
            >
              <option value="text">File Path</option>
              <option value="upload">File Upload</option>
            </select>
          </div>
        </div>
      </div>

      {/* Input Area */}
      {mode === 'text' ? (
        // Text Input Mode
        <div>
          <input
            type="text"
            value={value}
            onChange={(e) => onChange(e.target.value)}
            placeholder={placeholder}
            disabled={disabled}
            className={`w-full px-3 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 text-sm ${
              error ? 'border-red-300' : 'border-gray-300'
            } ${disabled ? 'bg-gray-100 cursor-not-allowed' : ''}`}
          />
          <p className="mt-1 text-xs text-gray-500">
            Enter the complete file path on the server
          </p>
        </div>
      ) : (
        // Upload Mode
        <div>
          <FileUploadWithValidation
            fileType={fileType}
            clientName={clientName}
            weekName={weekName}
            onFileValidated={(filePath) => {
              onChange(filePath);
              setUploadError('');
            }}
            onValidationError={(error) => {
              setUploadError(error);
            }}
            disabled={disabled}
            className="w-full"
          />
        </div>
      )}

      {/* Error Display */}
      {mode === 'text' && error && (
        <p className="mt-1 text-xs text-red-600">{error}</p>
      )}
      {mode === 'upload' && uploadError && (
        <p className="mt-1 text-xs text-red-600">{uploadError}</p>
      )}

      {/* Mode-specific Help Text */}
      {mode === 'upload' && (!clientName || !weekName) && (
        <div className="mt-2 p-2 bg-yellow-50 border border-yellow-200 rounded">
          <p className="text-xs text-yellow-700">
            ⚠️ Please select client name and week name first to enable file upload validation
          </p>
        </div>
      )}
    </div>
  );
};

export default HybridFileInput;
