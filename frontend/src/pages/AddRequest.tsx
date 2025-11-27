import React from 'react';
import { useNavigate } from 'react-router-dom';
import { AddRequestForm } from '../components/Forms/AddRequestForm';

const AddRequest: React.FC = () => {
  const navigate = useNavigate();

  const handleFormComplete = () => {
    // Navigate to request logs after successful submission
    navigate('/requests');
  };

  return (
    <div className="w-full h-full"> {/* Simple direct layout */}
      <AddRequestForm onComplete={handleFormComplete} />
    </div>
  );
};

export default AddRequest;
