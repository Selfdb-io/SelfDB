import React, { useState, useEffect } from 'react';
import { Button } from '../../../../components/ui/button';
import { Input } from '../../../../components/ui/input';
import { Label } from '../../../../components/ui/label';
import { Modal } from '../../../../components/ui/modal';
import { Bucket, CreateBucketData, createBucket, updateBucket } from '../../../../services/bucketService';

// Toggle component for public/private setting
const Toggle: React.FC<{
  isChecked: boolean;
  onChange: (checked: boolean) => void;
  label: string;
  id: string;
}> = ({ isChecked, onChange, label, id }) => {
  return (
    <div className="flex items-center space-x-3">
      <button
        type="button"
        role="switch"
        aria-checked={isChecked}
        id={id}
        onClick={() => onChange(!isChecked)}
        className={`
          relative inline-flex h-6 w-11 flex-shrink-0 cursor-pointer rounded-full border-2 border-transparent 
          transition-colors duration-200 ease-in-out focus:outline-none focus:ring-2 focus:ring-primary-500 focus:ring-offset-2
          ${isChecked ? 'bg-green-600' : 'bg-secondary-200 dark:bg-secondary-700'}
        `}
      >
        <span className="sr-only">{label}</span>
        <span
          aria-hidden="true"
          className={`
            pointer-events-none inline-block h-5 w-5 transform rounded-full bg-white shadow 
            ring-0 transition duration-200 ease-in-out
            ${isChecked ? 'translate-x-5' : 'translate-x-0'}
          `}
        />
      </button>
      <Label htmlFor={id} className="text-sm text-secondary-700 dark:text-secondary-300 cursor-pointer">
        {label}
      </Label>
    </div>
  );
};

interface BucketFormProps {
  isOpen: boolean;
  onClose: () => void;
  onSuccess: (bucket: Bucket) => void;
  editBucket?: Bucket | null;
}

const BucketForm: React.FC<BucketFormProps> = ({ 
  isOpen,
  onClose,
  onSuccess, 
  editBucket = null
}) => {
  const [name, setName] = useState('');
  const [description, setDescription] = useState('');
  const [isPublic, setIsPublic] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Reset form when modal opens/closes or editBucket changes
  useEffect(() => {
    if (isOpen) {
      if (editBucket) {
        setName(editBucket.name);
        setDescription(editBucket.description || '');
        setIsPublic(editBucket.is_public);
      } else {
        // Reset form for create mode
        setName('');
        setDescription('');
        setIsPublic(false);
      }
      setError(null);
    }
  }, [isOpen, editBucket]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError(null);
    
    try {
      const bucketData: CreateBucketData = {
        name,
        description: description || undefined,
        is_public: isPublic
      };
      
      let result;
      
      if (editBucket) {
        result = await updateBucket(editBucket.id, bucketData);
      } else {
        result = await createBucket(bucketData);
      }
      
      onSuccess(result);
      onClose();
      
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to save bucket');
    } finally {
      setLoading(false);
    }
  };

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      title={editBucket ? 'Edit Bucket' : 'Create New Bucket'}
    >
      {error && (
        <div className="text-error-600 dark:text-error-400 bg-error-50 dark:bg-error-900/30 p-4 rounded mb-4 text-sm">
          {error}
        </div>
      )}
      
      <form onSubmit={handleSubmit} className="space-y-4">
        <div>
          <Label htmlFor="name">Bucket Name</Label>
          <Input
            id="name"
            type="text"
            value={name}
            onChange={(e) => setName(e.target.value)}
            required
            placeholder="e.g., profile-images, documents, backups"
            className="mt-1"
          />
        </div>
        
        <div>
          <Label htmlFor="description">Description (optional)</Label>
          <Input
            id="description"
            type="text"
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            placeholder="A short description of what this bucket is for"
            className="mt-1"
          />
        </div>
        
        <div className="mt-4">
          <Toggle
            id="is-public"
            isChecked={isPublic}
            onChange={setIsPublic}
            label="Make this bucket public (files will be accessible without authentication)"
          />
        </div>
        
        <div className="flex justify-end space-x-2 pt-4">
          <Button
            type="button"
            variant="outline"
            onClick={onClose}
            disabled={loading}
          >
            Cancel
          </Button>
          <Button
            type="submit"
            disabled={loading}
            className={loading ? 'opacity-70' : ''}
          >
            {loading ? (
              <>
                <span className="mr-2 animate-spin rounded-full h-4 w-4 border-b-2 border-white"></span>
                {editBucket ? 'Saving...' : 'Creating...'}
              </>
            ) : (
              editBucket ? 'Save Changes' : 'Create Bucket'
            )}
          </Button>
        </div>
      </form>
    </Modal>
  );
};

export default BucketForm; 