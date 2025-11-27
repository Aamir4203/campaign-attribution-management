import React, { useState, useEffect } from 'react';
import { useForm } from 'react-hook-form';
import { yupResolver } from '@hookform/resolvers/yup';
import { addRequestSchema, AddRequestFormData } from '../../../utils/validation';
import ClientService from '../../../services/clientService';
import api from '../../../services/api';
import { useAuth } from '../../Auth';

interface AddRequestFormProps {
  onComplete?: () => void;
}

const AddRequestForm: React.FC<AddRequestFormProps> = ({ onComplete }) => {
  const { getUsername } = useAuth();
  const [clients, setClients] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [showAddClient, setShowAddClient] = useState(false);
  const [newClientName, setNewClientName] = useState('');
  const [showFilePath, setShowFilePath] = useState(false);
  const [showClientSuppressionPath, setShowClientSuppressionPath] = useState(false);
  const [showRequestIdSuppressionList, setShowRequestIdSuppressionList] = useState(false);
  const [showPriorityFields, setShowPriorityFields] = useState(false);
  const [showTimeStampPath, setShowTimeStampPath] = useState(false);
  const [backendConnected, setBackendConnected] = useState(false);
  const [showSuccessModal, setShowSuccessModal] = useState(false);
  const [lastSubmittedRequestId, setLastSubmittedRequestId] = useState<string | number | null>(null);

  const form = useForm<AddRequestFormData>({
    resolver: yupResolver(addRequestSchema),
    mode: 'onChange',
    defaultValues: {
      clientName: '',
      addedBy: getUsername() || 'Unknown', // Use logged-in username
      requestType: '1',
      filePath: '',
      startDate: '',
      endDate: '',
      residualStart: '',
      week: '',
      reportpath: '',
      qspath: '',
      options: 'N',
      Offer_option: '',
      bounce_option: '',
      cs_option: '',
      input_query: '',
      addTimeStamp: false,
      addIpsLogs: false,
      offerSuppression: false,
      addBounce: false,
      clientSuppression: false,
      requestIdSuppression: false,
      clientSuppressionPath: '',
      requestIdSuppressionList: '',
      timeStampPath: '',
      fileType: 'Delivered',
      priorityFile: '',
      priorityFilePer: undefined
    },
  });

  const { register, handleSubmit, formState: { errors }, watch, setValue, setError, clearErrors } = form;
  const requestType = watch('requestType');
  const clientSuppression = watch('clientSuppression');
  const requestIdSuppression = watch('requestIdSuppression');
  const priorityFile = watch('priorityFile');
  const addTimeStamp = watch('addTimeStamp');
  const endDate = watch('endDate');
  const residualStart = watch('residualStart');

  // Load data on mount
  useEffect(() => {
    loadFormData();
  }, []);

  // Show file path input when Type 2 is selected
  useEffect(() => {
    setShowFilePath(requestType === '2');
  }, [requestType]);

  // Show client suppression path when Client Suppression is checked
  useEffect(() => {
    setShowClientSuppressionPath(clientSuppression === true);
  }, [clientSuppression]);

  // Show request ID suppression list when Request ID Suppression is checked
  useEffect(() => {
    setShowRequestIdSuppressionList(requestIdSuppression === true);
  }, [requestIdSuppression]);

  // Show priority percentage when priority file is provided
  useEffect(() => {
    setShowPriorityFields(priorityFile && priorityFile.trim().length > 0);
  }, [priorityFile]);

  // Show timestamp path when Add TimeStamp is checked
  useEffect(() => {
    setShowTimeStampPath(addTimeStamp === true);
  }, [addTimeStamp]);

  // Real-time residual date validation
  useEffect(() => {
    if (endDate && residualStart) {
      const endDateObj = new Date(endDate);
      const residualDateObj = new Date(residualStart);

      if (residualDateObj < endDateObj) {
        setError('residualStart', {
          type: 'manual',
          message: 'Residual date must be equal to or greater than end date'
        });
      } else {
        clearErrors('residualStart');
      }
    } else if (!residualStart) {
      // Clear error when field is empty
      clearErrors('residualStart');
    }
  }, [endDate, residualStart, setError, clearErrors]);

  const loadFormData = async () => {
    try {
      setLoading(true);

      // Test backend connection first
      console.log('🔗 Testing backend connection at http://localhost:5000...');

      // Load real data from backend
      const clientsData = await ClientService.getClients();
      setClients(clientsData);
      setBackendConnected(true);

      console.log('✅ Backend connection successful');
      console.log('📋 Loaded clients:', clientsData?.length || 0);

    } catch (error) {
      setBackendConnected(false);
      console.error('❌ Backend connection failed:', error);
      console.error('🔍 Error details:', error?.message || 'Unknown error');
      console.error('🚨 Make sure backend is running at http://localhost:5000');
      setClients([]); // Empty array if backend fails
    } finally {
      setLoading(false);
    }
  };

  const handleAddClient = async () => {
    if (!newClientName.trim()) {
      return;
    }

    try {
      const result = await ClientService.addClient(newClientName);
      if (result.success) {
        await loadFormData(); // Refresh client list
        setValue('clientName', newClientName);
        setShowAddClient(false);
        setNewClientName('');
      }
    } catch (error) {
      // Silent error handling
    }
  };

  const onSubmit = async (data: AddRequestFormData) => {
    try {
      setSubmitting(true);

      // Ensure addedBy is set to the logged-in username
      const formDataWithUser = {
        ...data,
        addedBy: getUsername() || 'Unknown'
      };

      const result = await api.post('/submit_form', formDataWithUser);

      if (result.data.success) {
        // Show success popup with request ID instead of redirecting
        setLastSubmittedRequestId(result.data.request_id);
        setShowSuccessModal(true);
        form.reset(); // Reset form after successful submission

        // Reset addedBy to current user after reset
        form.setValue('addedBy', getUsername() || 'Unknown');
      }
    } catch (error) {
      // Silent error handling
    } finally {
      setSubmitting(false);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center py-12">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
        <span className="ml-3 text-gray-600">Loading form data...</span>
      </div>
    );
  }

  return (
    <div className="w-full space-y-10">{/* Simple direct layout without any card styling */}

      <form onSubmit={handleSubmit(onSubmit)} className="space-y-8">

        {/* Section 1: Client Information */}
        <div className="bg-gradient-to-r from-slate-50 to-gray-100 rounded-xl p-6 border border-slate-300 shadow-lg hover:shadow-xl transition-shadow duration-200">
          <h3 className="text-lg font-semibold text-slate-800 mb-4 flex items-center">
            <svg className="w-5 h-5 mr-2 text-slate-600" fill="currentColor" viewBox="0 0 20 20">
              <path d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"/>
            </svg>
            Client Information
          </h3>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div>
              <label htmlFor="clientName" className="block text-sm font-medium text-gray-700 mb-2">
                Client Name *
              </label>
              <div className="flex gap-2">
                <select
                  {...register('clientName')}
                  className="flex-1 px-3 py-2 border-2 border-blue-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 bg-white shadow-sm hover:border-blue-300 transition-colors"
                >
                  <option value="">-- Select Client --</option>
                  {clients.map((client, idx) => (
                    <option key={idx} value={client.client_name}>
                      {client.client_name}
                    </option>
                  ))}
                </select>
                <button
                  type="button"
                  onClick={() => setShowAddClient(true)}
                  className="px-4 py-2 bg-green-600 hover:bg-green-700 text-white rounded-lg transition-colors shadow-sm flex items-center"
                  title="Add New Client"
                >
                  <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
                    <path fillRule="evenodd" d="M10 3a1 1 0 011 1v5h5a1 1 0 110 2h-5v5a1 1 0 11-2 0v-5H4a1 1 0 110-2h5V4a1 1 0 011-1z" clipRule="evenodd"/>
                  </svg>
                </button>
              </div>
              {errors.clientName && (
                <p className="mt-1 text-sm text-red-600">{errors.clientName.message}</p>
              )}
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Request Type *
              </label>
              <select
                {...register('requestType')}
                className="w-full px-3 py-2 border-2 border-blue-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 bg-white shadow-sm hover:border-blue-300 transition-colors"
              >
                <option value="1">Type1 - Unique/Non_Unique</option>
                <option value="2">Type2 - Unique Decile Report Path Required</option>
                <option value="3">Type3 - Advanced Processing</option>
              </select>
            </div>
          </div>

          {/* Type 2 File Path */}
          {showFilePath && (
            <div className="mt-6">
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Unique Decile Report Path *
              </label>
              <input
                type="text"
                {...register('filePath')}
                className="w-full px-3 py-2 border-2 border-blue-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 shadow-sm hover:border-blue-300 transition-colors"
                placeholder="Enter unique decile report file path"
              />
              {errors.filePath && (
                <p className="mt-1 text-sm text-red-600">{errors.filePath.message}</p>
              )}
            </div>
          )}
        </div>

        {/* Section 3: Date Configuration */}
        <div className="bg-gradient-to-r from-amber-50 to-orange-50 rounded-xl p-6 border border-amber-300 shadow-lg hover:shadow-xl transition-shadow duration-200">
          <h3 className="text-lg font-semibold text-amber-800 mb-4 flex items-center">
            <svg className="w-5 h-5 mr-2 text-amber-700" fill="currentColor" viewBox="0 0 20 20">
              <path fillRule="evenodd" d="M6 2a1 1 0 00-1 1v1H4a2 2 0 00-2 2v10a2 2 0 002 2h12a2 2 0 002-2V6a2 2 0 00-2-2h-1V3a1 1 0 10-2 0v1H7V3a1 1 0 00-1-1zm0 5a1 1 0 000 2h8a1 1 0 100-2H6z" clipRule="evenodd"/>
            </svg>
            Campaign Dates
          </h3>
          <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Start Date *
              </label>
              <input
                type="date"
                {...register('startDate')}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-orange-500 focus:border-transparent shadow-sm"
              />
              {errors.startDate && (
                <p className="mt-1 text-sm text-red-600">{errors.startDate.message}</p>
              )}
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                End Date *
              </label>
              <input
                type="date"
                {...register('endDate')}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-orange-500 focus:border-transparent shadow-sm"
              />
              {errors.endDate && (
                <p className="mt-1 text-sm text-red-600">{errors.endDate.message}</p>
              )}
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Residual Date
              </label>
              <input
                type="date"
                {...register('residualStart')}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-orange-500 focus:border-transparent shadow-sm"
              />
              {errors.residualStart && (
                <p className="mt-1 text-sm text-red-600">{errors.residualStart.message}</p>
              )}
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Week
              </label>
              <input
                type="text"
                {...register('week')}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-orange-500 focus:border-transparent shadow-sm"
                placeholder="e.g., 2025-W01"
              />
            </div>
          </div>
        </div>

        {/* Section 4: File Settings & Options */}
        <div className="bg-gradient-to-r from-green-50 to-emerald-50 rounded-xl p-6 border border-green-300 shadow-lg hover:shadow-xl transition-shadow duration-200">
          <h3 className="text-lg font-semibold text-green-800 mb-4 flex items-center">
            <svg className="w-5 h-5 mr-2 text-green-700" fill="currentColor" viewBox="0 0 20 20">
              <path fillRule="evenodd" d="M4 4a2 2 0 00-2 2v8a2 2 0 002 2h12a2 2 0 002-2V6a2 2 0 00-2-2H4zm2 6a2 2 0 114 0 2 2 0 01-4 0zm8-2a2 2 0 100 4 2 2 0 000-4z" clipRule="evenodd"/>
            </svg>
            File Options
          </h3>

          {/* File Type Radio Buttons - Centered */}
          <div className="mb-6">
            <div className="text-center">
              <label className="block text-sm font-medium text-gray-700 mb-3">File Type</label>
              <div className="flex justify-center space-x-8">
                <label className="flex items-center">
                  <input
                    type="radio"
                    value="Sent"
                    {...register('fileType')}
                    className="w-4 h-4 text-indigo-600 focus:ring-indigo-500 border-gray-300"
                  />
                  <span className="ml-2 text-sm text-gray-700">Sent</span>
                </label>
                <label className="flex items-center">
                  <input
                    type="radio"
                    value="Delivered"
                    {...register('fileType')}
                    className="w-4 h-4 text-indigo-600 focus:ring-indigo-500 border-gray-300"
                  />
                  <span className="ml-2 text-sm text-gray-700">Delivered</span>
                </label>
              </div>
            </div>
          </div>

          {/* Checkboxes in single horizontal line */}
          <div className="flex justify-center space-x-12 mb-6">
            <label className="flex items-center">
              <input
                type="checkbox"
                {...register('addTimeStamp')}
                className="w-4 h-4 text-indigo-600 focus:ring-indigo-500 border-gray-300 rounded"
              />
              <span className="ml-2 text-sm text-gray-700">Add TimeStamp</span>
            </label>

            <label className="flex items-center">
              <input
                type="checkbox"
                {...register('addBounce')}
                className="w-4 h-4 text-indigo-600 focus:ring-indigo-500 border-gray-300 rounded"
              />
              <span className="ml-2 text-sm text-gray-700">Add Bounce</span>
            </label>

            <label className="flex items-center">
              <input
                type="checkbox"
                {...register('addIpsLogs')}
                className="w-4 h-4 text-indigo-600 focus:ring-indigo-500 border-gray-300 rounded"
              />
              <span className="ml-2 text-sm text-gray-700">Add IPs to Logs</span>
            </label>
          </div>

          {/* TimeStamp Path Input - appears when Add TimeStamp is checked */}
          {showTimeStampPath && (
            <div className="mt-4">
              <label className="block text-sm font-medium text-gray-700 mb-2">
                TimeStamp File Path *
              </label>
              <input
                type="text"
                {...register('timeStampPath')}
                className="w-full px-3 py-2 border-2 border-emerald-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-emerald-500 focus:border-emerald-500 shadow-sm hover:border-emerald-300 transition-colors"
                placeholder="Enter timestamp file path"
              />
              {errors.timeStampPath && (
                <p className="mt-1 text-sm text-red-600">{errors.timeStampPath.message}</p>
              )}
            </div>
          )}
        </div>

        {/* Section 5: Report Paths */}
        <div className="bg-gradient-to-r from-yellow-50 to-amber-50 rounded-xl p-6 border border-yellow-300 shadow-lg hover:shadow-xl transition-shadow duration-200">
          <h3 className="text-lg font-semibold text-yellow-800 mb-4 flex items-center">
            <svg className="w-5 h-5 mr-2 text-yellow-700" fill="currentColor" viewBox="0 0 20 20">
              <path fillRule="evenodd" d="M2 6a2 2 0 012-2h5l2 2h5a2 2 0 012 2v6a2 2 0 01-2 2H4a2 2 0 01-2-2V6z" clipRule="evenodd"/>
            </svg>
            Report Paths
          </h3>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Report Path
              </label>
              <input
                type="text"
                {...register('reportpath')}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-green-500 focus:border-transparent shadow-sm"
                placeholder="Enter report path"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Quality Score Report Path
              </label>
              <input
                type="text"
                {...register('qspath')}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-green-500 focus:border-transparent shadow-sm"
                placeholder="Enter QS report path"
              />
            </div>
          </div>
        </div>

        {/* Section 5: Suppression List */}
        <div className="bg-gradient-to-r from-violet-50 to-purple-50 rounded-xl p-6 border border-violet-300 shadow-lg hover:shadow-xl transition-shadow duration-200">
          <h3 className="text-lg font-semibold text-violet-800 mb-4 flex items-center">
            <svg className="w-5 h-5 mr-2 text-violet-700" fill="currentColor" viewBox="0 0 20 20">
              <path fillRule="evenodd" d="M9 2a1 1 0 000 2h2a1 1 0 100-2H9z" clipRule="evenodd"/>
              <path fillRule="evenodd" d="M4 5a2 2 0 012-2h8a2 2 0 012 2v6a2 2 0 01-2 2H6a2 2 0 01-2-2V5zm2.5 3a1.5 1.5 0 100-3 1.5 1.5 0 000 3zm2.45 4a2.5 2.5 0 10-4.9 0h4.9zM12 9a1 1 0 100-2 1 1 0 000 2zm-1 4h2v2h-2v-2z" clipRule="evenodd"/>
            </svg>
            Suppression List
          </h3>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            <div className="space-y-3">
              <label className="flex items-center">
                <input
                  type="checkbox"
                  {...register('offerSuppression')}
                  className="w-4 h-4 text-purple-600 focus:ring-purple-500 border-gray-300 rounded"
                />
                <span className="ml-2 text-sm text-gray-700">Offer Suppression</span>
              </label>
            </div>

            <div className="space-y-3">
              <label className="flex items-center">
                <input
                  type="checkbox"
                  {...register('clientSuppression')}
                  className="w-4 h-4 text-purple-600 focus:ring-purple-500 border-gray-300 rounded"
                />
                <span className="ml-2 text-sm text-gray-700">Client Suppression</span>
              </label>

              {/* Client Suppression Path Input - appears when checkbox is checked */}
              {showClientSuppressionPath && (
                <div className="mt-2">
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Client Suppression File Path
                  </label>
                  <input
                    type="text"
                    {...register('clientSuppressionPath')}
                    className="w-full px-3 py-2 border-2 border-purple-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-purple-500 focus:border-purple-500 shadow-sm hover:border-purple-300 transition-colors"
                    placeholder="Enter client suppression file path"
                  />
                  {errors.clientSuppressionPath && (
                    <p className="mt-1 text-sm text-red-600">{errors.clientSuppressionPath.message}</p>
                  )}
                </div>
              )}
            </div>

            <div className="space-y-3">
              <label className="flex items-center">
                <input
                  type="checkbox"
                  {...register('requestIdSuppression')}
                  className="w-4 h-4 text-purple-600 focus:ring-purple-500 border-gray-300 rounded"
                />
                <span className="ml-2 text-sm text-gray-700">Request ID Suppression</span>
              </label>

              {/* Request ID Suppression List - appears when checkbox is checked */}
              {showRequestIdSuppressionList && (
                <div className="mt-2">
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Request IDs (comma-separated)
                  </label>
                  <input
                    type="text"
                    {...register('requestIdSuppressionList')}
                    className="w-full px-3 py-2 border-2 border-purple-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-purple-500 focus:border-purple-500 shadow-sm hover:border-purple-300 transition-colors"
                    placeholder="e.g., 1234,5678,9012"
                  />
                  {errors.requestIdSuppressionList && (
                    <p className="mt-1 text-sm text-red-600">{errors.requestIdSuppressionList.message}</p>
                  )}
                  <p className="mt-1 text-xs text-gray-500">Enter request IDs separated by commas</p>
                </div>
              )}
            </div>
          </div>
        </div>

        {/* Section 6: Data Priority */}
        <div className="bg-gradient-to-r from-blue-50 to-cyan-50 rounded-xl p-6 border border-blue-300 shadow-lg hover:shadow-xl transition-shadow duration-200">
          <h3 className="text-lg font-semibold text-blue-800 mb-4 flex items-center">
            <svg className="w-5 h-5 mr-2 text-blue-700" fill="currentColor" viewBox="0 0 20 20">
              <path fillRule="evenodd" d="M3 4a1 1 0 011-1h12a1 1 0 011 1v2a1 1 0 01-1 1H4a1 1 0 01-1-1V4zm0 4a1 1 0 011-1h12a1 1 0 011 1v2a1 1 0 01-1 1H4a1 1 0 01-1-1V8zm0 4a1 1 0 011-1h12a1 1 0 011 1v2a1 1 0 01-1 1H4a1 1 0 01-1-1v-2z" clipRule="evenodd"/>
            </svg>
            Data Priority Settings
          </h3>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Priority File Path
              </label>
              <input
                type="text"
                {...register('priorityFile')}
                className="w-full px-3 py-2 border-2 border-cyan-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-cyan-500 focus:border-cyan-500 shadow-sm hover:border-cyan-300 transition-colors"
                placeholder="Enter priority file path"
              />
              {errors.priorityFile && (
                <p className="mt-1 text-sm text-red-600">{errors.priorityFile.message}</p>
              )}
            </div>

            {showPriorityFields && (
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Priority Percentage (1-100) *
                </label>
                <input
                  type="number"
                  min="1"
                  max="100"
                  step="1"
                  {...register('priorityFilePer')}
                  className="w-full px-3 py-2 border-2 border-cyan-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-cyan-500 focus:border-cyan-500 shadow-sm hover:border-cyan-300 transition-colors"
                  placeholder="Enter percentage (1-100)"
                />
                {errors.priorityFilePer && (
                  <p className="mt-1 text-sm text-red-600">{errors.priorityFilePer.message}</p>
                )}
              </div>
            )}
          </div>
        </div>

        {/* Section 7: SQL Query */}
        <div className="bg-gradient-to-r from-rose-50 to-pink-50 rounded-xl p-6 border border-rose-300 shadow-lg hover:shadow-xl transition-shadow duration-200">
          <h3 className="text-lg font-semibold text-rose-800 mb-4 flex items-center">
            <svg className="w-5 h-5 mr-2 text-rose-700" fill="currentColor" viewBox="0 0 20 20">
              <path fillRule="evenodd" d="M3 4a1 1 0 011-1h12a1 1 0 011 1v2a1 1 0 01-1 1H4a1 1 0 01-1-1V4zm0 4a1 1 0 011-1h12a1 1 0 011 1v2a1 1 0 01-1 1H4a1 1 0 01-1-1V8zm0 4a1 1 0 011-1h12a1 1 0 011 1v2a1 1 0 01-1 1H4a1 1 0 01-1-1v-2z" clipRule="evenodd"/>
            </svg>
            SQL Query
          </h3>
          <div>
            <textarea
              {...register('input_query')}
              rows={6}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-gray-500 focus:border-transparent shadow-sm font-mono text-sm"
              placeholder="-- SELECT * FROM table WHERE condition"
            />
          </div>
        </div>

        {/* Submit Section */}
        <div className="bg-gradient-to-r from-slate-600 to-gray-700 rounded-xl p-6 text-center shadow-lg hover:shadow-xl transition-shadow duration-200">
          <button
            type="submit"
            disabled={submitting || !backendConnected}
            className={`px-8 py-3 rounded-lg font-semibold text-white transition-all transform hover:scale-105 shadow-lg ${
              submitting || !backendConnected
                ? 'bg-gray-400 cursor-not-allowed'
                : 'bg-gradient-to-r from-orange-500 to-red-500 hover:from-orange-600 hover:to-red-600'
            }`}
          >
            {submitting ? (
              <span className="flex items-center justify-center">
                <svg className="animate-spin -ml-1 mr-3 h-5 w-5 text-white" fill="none" viewBox="0 0 24 24">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"/>
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"/>
                </svg>
                Processing Request...
              </span>
            ) : (
              'Submit Request'
            )}
          </button>

          {!backendConnected && (
            <div className="mt-3 p-3 bg-red-50 border border-red-200 rounded-lg">
              <div className="flex items-start">
                <div className="flex-shrink-0">
                  <svg className="h-5 w-5 text-red-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.732-.833-2.5 0L3.732 16.5c-.77.833.192 2.5 1.732 2.5z" />
                  </svg>
                </div>
                <div className="ml-3">
                  <h3 className="text-sm font-medium text-red-800">Backend Connection Required</h3>
                  <div className="mt-2 text-sm text-red-700">
                    <p>The backend server is not running or not accessible.</p>
                    <p className="mt-1 font-medium">To fix this:</p>
                    <ul className="list-disc list-inside mt-1 space-y-1">
                      <li>Make sure the backend terminal is running</li>
                      <li>Check for "Running on http://localhost:5000" message</li>
                      <li>Refresh this page</li>
                    </ul>
                  </div>
                </div>
              </div>
            </div>
          )}
        </div>
      </form>

      {/* Add Client Modal */}
      {showAddClient && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg p-6 w-96">
            <h3 className="text-lg font-semibold mb-4">Add New Client</h3>
            <input
              type="text"
              value={newClientName}
              onChange={(e) => setNewClientName(e.target.value)}
              placeholder="Enter client name"
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 mb-4"
            />
            <div className="flex gap-2">
              <button
                onClick={handleAddClient}
                className="flex-1 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700"
              >
                Add Client
              </button>
              <button
                onClick={() => {
                  setShowAddClient(false);
                  setNewClientName('');
                }}
                className="flex-1 px-4 py-2 bg-gray-300 text-gray-700 rounded-lg hover:bg-gray-400"
              >
                Cancel
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Success Modal */}
      {showSuccessModal && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg p-6 w-96 max-w-md mx-4">
            <div className="text-center">
              {/* Success Icon */}
              <div className="w-16 h-16 mx-auto mb-4 bg-green-100 rounded-full flex items-center justify-center">
                <svg className="w-8 h-8 text-green-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M5 13l4 4L19 7"></path>
                </svg>
              </div>

              {/* Success Message */}
              <h3 className="text-xl font-semibold text-gray-900 mb-2">Request Submitted Successfully!</h3>

              {/* Request ID */}
              <p className="text-gray-600 mb-4">Your request has been submitted to the system.</p>
              <div className="bg-blue-50 border border-blue-200 rounded-lg p-3 mb-6">
                <p className="text-sm text-gray-600 mb-1">Request ID:</p>
                <p className="text-lg font-mono font-semibold text-blue-800">{lastSubmittedRequestId}</p>
              </div>

              {/* Action Buttons */}
              <div className="flex gap-3">
                <button
                  onClick={() => {
                    setShowSuccessModal(false);
                    setLastSubmittedRequestId(null);
                  }}
                  className="flex-1 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
                >
                  Submit Another Request
                </button>
                <button
                  onClick={() => {
                    setShowSuccessModal(false);
                    setLastSubmittedRequestId(null);
                    // Note: Request Logs page is not implemented yet
                    alert('Request Logs page is coming soon! Your request is being processed.');
                  }}
                  className="flex-1 px-4 py-2 bg-gray-200 text-gray-700 rounded-lg hover:bg-gray-300 transition-colors"
                >
                  View Status
                </button>
              </div>

              {/* Info Note */}
              <p className="text-xs text-gray-500 mt-3">
                You can track the progress of your request using the Request ID above.
              </p>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default AddRequestForm;
