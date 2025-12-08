import React, { useState, useEffect } from 'react';
import { useForm } from 'react-hook-form';
import { yupResolver } from '@hookform/resolvers/yup';
import { addRequestSchema, AddRequestFormData } from '../../../utils/validation';
import ClientService from '../../../services/clientService';
import api from '../../../services/api';
import { useAuth } from '../../Auth';
import SectionNavigator, { SectionInfo } from './SectionNavigator';

interface AddRequestFormWithSidebarProps {
  onComplete?: () => void;
}

const AddRequestFormWithSidebar: React.FC<AddRequestFormWithSidebarProps> = ({ onComplete }) => {
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

  // Current active section
  const [activeSectionId, setActiveSectionId] = useState(1);

  const form = useForm<AddRequestFormData>({
    resolver: yupResolver(addRequestSchema),
    mode: 'onChange',
    defaultValues: {
      clientName: '',
      addedBy: getUsername() || 'Unknown',
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

  // Section definitions
  const sections: SectionInfo[] = [
    {
      id: 1,
      title: 'Client Information',
      shortTitle: 'Client Info',
      icon: '👤',
      isComplete: !!watch('clientName'),
      hasError: !!errors.clientName || !!errors.requestType,
      isActive: activeSectionId === 1,
    },
    {
      id: 2,
      title: 'Campaign Dates',
      shortTitle: 'Dates',
      icon: '📅',
      isComplete: !!watch('startDate') && !!watch('endDate'),
      hasError: !!errors.startDate || !!errors.endDate || !!errors.residualStart,
      isActive: activeSectionId === 2,
    },
    {
      id: 3,
      title: 'File Options',
      shortTitle: 'File Options',
      icon: '📁',
      isComplete: !!watch('fileType'),
      hasError: !!errors.fileType || !!errors.timeStampPath,
      isActive: activeSectionId === 3,
    },
    {
      id: 4,
      title: 'Report Paths',
      shortTitle: 'Reports',
      icon: '📊',
      isComplete: !!watch('reportpath'),
      hasError: !!errors.reportpath || !!errors.qspath,
      isActive: activeSectionId === 4,
    },
    {
      id: 5,
      title: 'Suppression List',
      shortTitle: 'Suppression',
      icon: '🚫',
      isComplete: clientSuppression && !!watch('clientSuppressionPath'),
      hasError: !!errors.clientSuppressionPath || !!errors.requestIdSuppressionList,
      isActive: activeSectionId === 5,
    },
    {
      id: 6,
      title: 'Data Priority Settings',
      shortTitle: 'Priority',
      icon: '⚡',
      isComplete: !priorityFile || (priorityFile && !!watch('priorityFilePer')),
      hasError: !!errors.priorityFile || !!errors.priorityFilePer,
      isActive: activeSectionId === 6,
    },
    {
      id: 7,
      title: 'SQL Query',
      shortTitle: 'Query',
      icon: '💻',
      isComplete: !!watch('input_query'),
      hasError: !!errors.input_query,
      isActive: activeSectionId === 7,
    },
  ];

  const progress = {
    completed: sections.filter((s) => s.isComplete).length,
    total: sections.length,
  };

  // Load data on mount
  useEffect(() => {
    loadFormData();
  }, []);

  const loadFormData = async () => {
    try {
      setLoading(true);

      // Test backend connectivity
      try {
        await api.get('/status');
        setBackendConnected(true);
      } catch {
        setBackendConnected(false);
      }

      // Load clients
      const clientsData = await ClientService.getClients();
      setClients(clientsData);

    } catch (error) {
      console.error('Error loading form data:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleSectionClick = (sectionId: number) => {
    setActiveSectionId(sectionId);
    // Scroll to section smoothly
    const element = document.getElementById(`section-${sectionId}`);
    if (element) {
      element.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }
  };

  const handleAddClient = async () => {
    if (!newClientName.trim()) return;

    try {
      await ClientService.addClient(newClientName.trim());
      await loadFormData(); // Reload client list
      setValue('clientName', newClientName.trim());
      setShowAddClient(false);
      setNewClientName('');
    } catch (error) {
      console.error('Error adding client:', error);
    }
  };

  const onSubmit = async (data: AddRequestFormData) => {
    // ...existing submit logic...
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-center">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600 mx-auto mb-2"></div>
          <p className="text-gray-600">Loading form data...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="flex h-full w-full">
      {/* Left Sidebar Navigation */}
      <SectionNavigator
        sections={sections}
        onSectionClick={handleSectionClick}
        progress={progress}
      />

      {/* Main Form Content Area */}
      <div className="flex-1 overflow-y-auto bg-gray-50" style={{ paddingLeft: '0px' }}>
        <div className="max-w-4xl mx-auto p-6">
          <form onSubmit={handleSubmit(onSubmit)} className="space-y-6">

            {/* Page Header */}
            <div className="bg-white rounded-lg shadow-sm p-6">
              <div className="flex items-center justify-between">
                <div>
                  <h1 className="text-2xl font-bold text-gray-800">📋 Add New Request</h1>
                  <p className="text-sm text-gray-600 mt-1">
                    Progress: {progress.completed}/{progress.total} sections completed
                  </p>
                </div>
                <div className="flex items-center space-x-3">
                  {!backendConnected && (
                    <div className="px-3 py-1 bg-yellow-100 text-yellow-800 rounded-md text-xs">
                      Backend Disconnected
                    </div>
                  )}
                  <button
                    type="submit"
                    disabled={submitting}
                    className="px-6 py-2 bg-green-600 hover:bg-green-700 text-white rounded-lg transition-colors disabled:opacity-50"
                  >
                    {submitting ? 'Submitting...' : 'Submit Request'}
                  </button>
                </div>
              </div>
            </div>

            {/* Section 1: Client Information */}
            <div id="section-1" className="bg-white rounded-lg shadow-sm">
              <div className="border-l-4 border-blue-500 p-6">
                <div className="flex items-center space-x-3 mb-4">
                  <span className="text-2xl">👤</span>
                  <div>
                    <h2 className="text-xl font-semibold text-gray-800">1. Client Information</h2>
                    <p className="text-sm text-gray-600">Select client and request type</p>
                  </div>
                  {sections[0].isComplete && (
                    <span className="text-green-600 text-lg">✓</span>
                  )}
                </div>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">
                      Client Name *
                    </label>
                    <div className="flex gap-2">
                      <select
                        {...register('clientName')}
                        className="flex-1 px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 bg-white"
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
                        className="px-4 py-2 bg-green-600 hover:bg-green-700 text-white rounded-lg transition-colors"
                        title="Add New Client"
                      >
                        +
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
                      className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 bg-white"
                    >
                      <option value="1">Type 1</option>
                      <option value="2">Type 2</option>
                    </select>
                    {errors.requestType && (
                      <p className="mt-1 text-sm text-red-600">{errors.requestType.message}</p>
                    )}
                  </div>
                </div>
              </div>
            </div>

            {/* Section 2: Campaign Dates */}
            <div id="section-2" className="bg-white rounded-lg shadow-sm">
              <div className="border-l-4 border-green-500 p-6">
                <div className="flex items-center space-x-3 mb-4">
                  <span className="text-2xl">📅</span>
                  <div>
                    <h2 className="text-xl font-semibold text-gray-800">2. Campaign Dates</h2>
                    <p className="text-sm text-gray-600">Set campaign and residual dates</p>
                  </div>
                  {sections[1].isComplete && (
                    <span className="text-green-600 text-lg">✓</span>
                  )}
                </div>

                <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">
                      Start Date *
                    </label>
                    <input
                      type="date"
                      {...register('startDate')}
                      className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-green-500"
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
                      className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-green-500"
                    />
                    {errors.endDate && (
                      <p className="mt-1 text-sm text-red-600">{errors.endDate.message}</p>
                    )}
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">
                      Residual Start *
                    </label>
                    <input
                      type="date"
                      {...register('residualStart')}
                      className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-green-500"
                    />
                    {errors.residualStart && (
                      <p className="mt-1 text-sm text-red-600">{errors.residualStart.message}</p>
                    )}
                  </div>
                </div>

                <div className="mt-4">
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Week *
                  </label>
                  <input
                    type="text"
                    {...register('week')}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-green-500"
                    placeholder="e.g., Q4_W8"
                  />
                  {errors.week && (
                    <p className="mt-1 text-sm text-red-600">{errors.week.message}</p>
                  )}
                </div>
              </div>
            </div>

            {/* Continue with other sections... */}
            {/* For now, showing placeholder for remaining sections */}
            {activeSectionId > 2 && (
              <div className="bg-white rounded-lg shadow-sm p-6 text-center">
                <div className="text-gray-500">
                  <span className="text-2xl mb-2 block">🚧</span>
                  <h3 className="text-lg font-medium mb-2">Section {activeSectionId} Coming Soon</h3>
                  <p className="text-sm">This section is under development</p>
                </div>
              </div>
            )}
          </form>
        </div>
      </div>

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
            <div className="flex justify-end space-x-3">
              <button
                type="button"
                onClick={() => setShowAddClient(false)}
                className="px-4 py-2 text-gray-600 hover:text-gray-800 transition-colors"
              >
                Cancel
              </button>
              <button
                type="button"
                onClick={handleAddClient}
                className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg transition-colors"
              >
                Add Client
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default AddRequestFormWithSidebar;
