import React, { useState, useEffect } from 'react';
import { Modal } from '../../../components/ui/modal';
import { Button } from '../../../components/ui/button';
import { Input } from '../../../components/ui/input';
import { Label } from '../../../components/ui/label';
import { Textarea } from '../../../components/ui/textarea';
import { corsService, CorsOrigin, CorsOriginCreate, CorsOriginUpdate } from '../../../services/corsService';

interface CorsOriginModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSuccess: () => void;
  origin?: CorsOrigin; // If provided, edit mode; otherwise, create mode
}

const CorsOriginModal: React.FC<CorsOriginModalProps> = ({
  isOpen,
  onClose,
  onSuccess,
  origin
}) => {
  const [formData, setFormData] = useState({
    origin: '',
    description: ''
  });
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [validationError, setValidationError] = useState<string | null>(null);

  const isEditMode = !!origin;

  // Reset form when modal opens/closes or origin changes
  useEffect(() => {
    if (isOpen) {
      setFormData({
        origin: origin?.origin || '',
        description: origin?.description || ''
      });
      setError(null);
      setValidationError(null);
    }
  }, [isOpen, origin]);

  const validateOrigin = async (originUrl: string) => {
    if (!originUrl.trim()) {
      setValidationError('Origin URL is required');
      return false;
    }

    try {
      const validation = await corsService.validate(originUrl.trim());
      if (!validation.is_valid) {
        setValidationError(validation.error_message || 'Invalid origin URL');
        return false;
      }
      setValidationError(null);
      return true;
    } catch (error) {
      setValidationError('Failed to validate origin URL');
      return false;
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setIsLoading(true);

    try {
      // Validate origin first
      const isValid = await validateOrigin(formData.origin);
      if (!isValid) {
        setIsLoading(false);
        return;
      }

      if (isEditMode && origin) {
        // Update existing origin
        const updateData: CorsOriginUpdate = {
          origin: formData.origin.trim(),
          description: formData.description.trim() || undefined
        };
        await corsService.update(origin.id, updateData);
      } else {
        // Create new origin
        const createData: CorsOriginCreate = {
          origin: formData.origin.trim(),
          description: formData.description.trim() || undefined
        };
        await corsService.create(createData);
      }

      onSuccess();
      onClose();
    } catch (error: any) {
      console.error('Error saving CORS origin:', error);
      setError(error.response?.data?.detail || 'Failed to save CORS origin');
    } finally {
      setIsLoading(false);
    }
  };

  const handleOriginChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setFormData(prev => ({ ...prev, origin: e.target.value }));
    setValidationError(null);
  };

  const handleDescriptionChange = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    setFormData(prev => ({ ...prev, description: e.target.value }));
  };

  return (
    <Modal 
      isOpen={isOpen} 
      onClose={onClose}
      title={isEditMode ? 'Edit CORS Origin' : 'Add CORS Origin'}
      size="md"
    >
      <div className="space-y-4">

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <Label htmlFor="origin">Origin URL *</Label>
            <Input
              id="origin"
              type="url"
              value={formData.origin}
              onChange={handleOriginChange}
              placeholder="https://app.example.com"
              className={validationError ? 'border-error-500 focus:border-error-500' : ''}
              required
            />
            {validationError && (
              <p className="text-sm text-error-600 dark:text-error-400 mt-1">
                {validationError}
              </p>
            )}
            <p className="text-xs text-secondary-500 dark:text-secondary-400 mt-1">
              Enter the full origin URL including protocol (https://)
            </p>
          </div>

          <div>
            <Label htmlFor="description">Description</Label>
            <Textarea
              id="description"
              value={formData.description}
              onChange={handleDescriptionChange}
              placeholder="Optional description for this origin"
              rows={3}
            />
          </div>

          {error && (
            <div className="text-sm text-error-600 dark:text-error-400 bg-error-50 dark:bg-error-900/20 p-3 rounded-md">
              {error}
            </div>
          )}

          <div className="flex justify-end space-x-3 pt-4">
            <Button
              type="button"
              variant="ghost"
              onClick={onClose}
              disabled={isLoading}
            >
              Cancel
            </Button>
            <Button
              type="submit"
              disabled={isLoading || !!validationError}
            >
              {isLoading ? 'Saving...' : isEditMode ? 'Update' : 'Add'}
            </Button>
          </div>
        </form>
      </div>
    </Modal>
  );
};

export default CorsOriginModal;