import React from 'react';
import { Bucket } from '../../../../services/bucketService';
import BucketForm from './BucketForm';

interface BucketFormModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSubmit: (updatedBucket: Partial<Bucket>) => void;
  bucket: Bucket;
  title: string;
  submitButtonText: string;
}

const BucketFormModal: React.FC<BucketFormModalProps> = ({
  isOpen,
  onClose,
  onSubmit,
  bucket
}) => {
  // Handle successful form submission
  const handleSuccess = (updatedBucket: Bucket) => {
    onSubmit(updatedBucket);
  };

  return (
    <BucketForm
      isOpen={isOpen}
      onClose={onClose}
      onSuccess={handleSuccess}
      editBucket={bucket}
    />
  );
};

export default BucketFormModal; 