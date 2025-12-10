import React from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { AddRequestForm } from '../components/Forms/AddRequestForm';

const AddRequest: React.FC = () => {
  const navigate = useNavigate();
  const location = useLocation();

  // Check if we're in edit mode with request data
  const editMode = location.state?.editMode || false;
  const requestData = location.state?.requestData || null;

  const handleFormComplete = () => {
    // Navigate to request logs after successful submission
    navigate('/requests');
  };

  return (
    <div className="w-full h-full"> {/* Simple direct layout */}
      <AddRequestForm
        onComplete={handleFormComplete}
        editMode={editMode}
        initialData={requestData}
      />
    </div>
  );
};

export default AddRequest;
