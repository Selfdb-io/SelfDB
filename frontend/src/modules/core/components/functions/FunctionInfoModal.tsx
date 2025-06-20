import React, { useState, useEffect } from 'react';
import { AlertTriangle } from 'lucide-react';
import { Input } from '../../../../components/ui/input';
import { Textarea } from '../../../../components/ui/textarea';
import { Button } from '../../../../components/ui/button';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription } from '../../../../components/ui/dialog';
import { Label } from '../../../../components/ui/label';
import { updateFunction, Function, getFunction } from '../../../../services/functionService';

// Toggle component for On/Off setting
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

interface FunctionInfoModalProps {
  isOpen: boolean;
  onClose: () => void;
  functionId: string;
  functionName: string;
  functionDescription?: string;
  functionStatus?: string;
  onUpdate?: () => void;
}

const FunctionInfoModal: React.FC<FunctionInfoModalProps> = ({
  isOpen,
  onClose,
  functionId,
  functionName,
  functionDescription = '',
  functionStatus,
  onUpdate,
}) => {
  const [functionData, setFunctionData] = useState({
    name: functionName,
    description: functionDescription,
    status: functionStatus || 'draft',
    isActive: functionStatus === 'active'
  });
  
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [initialLoading, setInitialLoading] = useState(false);

  // If functionStatus is undefined, fetch the function to get is_active
  useEffect(() => {
    if (isOpen && functionId && functionStatus === undefined) {
      setInitialLoading(true);
      
      getFunction(functionId)
        .then(data => {
          // Convert is_active to status
          const derivedStatus = data.is_active ? 'active' : 'draft';
          
          setFunctionData(prev => ({
            ...prev,
            status: derivedStatus,
            isActive: Boolean(data.is_active)
          }));
          
          setInitialLoading(false);
        })
        .catch(err => {
          console.error('Error fetching function in modal:', err);
          setInitialLoading(false);
        });
    }
  }, [functionId, functionStatus, isOpen]);

  // Update state when props change
  useEffect(() => {
    if (functionStatus !== undefined) {
      setFunctionData({
        name: functionName,
        description: functionDescription || '',
        status: functionStatus || 'draft',
        isActive: functionStatus === 'active'
      });
    } else {
      // Don't update status if it's undefined - keep the derived one
      setFunctionData(prev => ({
        name: functionName,
        description: functionDescription || '',
        status: prev.status,
        isActive: prev.isActive
      }));
    }
  }, [functionName, functionDescription, functionStatus, isOpen]);

  const handleChange = (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) => {
    const { name, value } = e.target;
    
    setFunctionData({
      ...functionData,
      [name]: value
    });
  };

  const handleStatusChange = (isActive: boolean) => {
    setFunctionData({
      ...functionData,
      isActive,
      status: isActive ? 'active' : 'draft'
    });
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    
    // Basic validation
    if (!functionData.name.trim()) {
      setError('Function name is required');
      return;
    }
    
    setLoading(true);
    setError(null);
    
    try {
      // The backend expects is_active as a boolean, but our frontend API uses status as a string
      // Create a properly typed payload to satisfy TypeScript
      const updatePayload: Partial<Function> = {
        name: functionData.name,
        description: functionData.description,
        status: functionData.status,
        is_active: functionData.isActive 
      };
      
      await updateFunction(functionId, updatePayload);
      
      onClose();
      if (onUpdate) {
        onUpdate();
      }
    } catch (err: any) {
      console.error('Error updating function:', err);
      setError(err.response?.data?.detail || err.message || 'Failed to update function information');
    } finally {
      setLoading(false);
    }
  };

  return (
    <Dialog open={isOpen} onOpenChange={(open) => !open && onClose()}>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle className="text-xl font-semibold">Edit Function Information</DialogTitle>
          <DialogDescription>
            Update the function's name, description, and status.
          </DialogDescription>
        </DialogHeader>
        
        {error && (
          <div className="mb-4 p-3 bg-error-50 dark:bg-error-900/20 border border-error-200 dark:border-error-800 rounded-md text-error-700 dark:text-error-300 flex items-center">
            <AlertTriangle className="h-5 w-5 mr-2" />
            <span>{error}</span>
          </div>
        )}
        
        {initialLoading ? (
          <div className="py-8 flex justify-center">
            <div className="animate-spin rounded-full h-6 w-6 border-b-2 border-primary-600"></div>
          </div>
        ) : (
          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label className="block text-sm font-medium mb-1">Function Name</label>
              <Input
                name="name"
                value={functionData.name}
                onChange={handleChange}
                placeholder="e.g. getUser"
                className="w-full"
              />
            </div>
            
            <div>
              <label className="block text-sm font-medium mb-1">Description</label>
              <Textarea
                name="description"
                value={functionData.description}
                onChange={handleChange}
                rows={3}
                placeholder="Function description..."
                className="resize-none"
              />
            </div>
            
            <div className="mt-4">
              <Toggle
                id="function-status"
                isChecked={functionData.isActive}
                onChange={handleStatusChange}
                label="Function Status (On/Off)"
              />
              <p className="text-xs text-secondary-500 dark:text-secondary-400 mt-1">
                Turn functions On to make them available for use, or Off to disable them.
              </p>
            </div>
            
            <div className="flex justify-end space-x-3 pt-2">
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
              >
                {loading ? 'Updating...' : 'Update Function'}
              </Button>
            </div>
          </form>
        )}
      </DialogContent>
    </Dialog>
  );
};

export default FunctionInfoModal; 