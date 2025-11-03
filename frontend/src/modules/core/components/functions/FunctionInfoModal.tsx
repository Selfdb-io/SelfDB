import React, { useState, useEffect } from 'react';
import { AlertTriangle } from 'lucide-react';
import { Input } from '../../../../components/ui/input';
import { Textarea } from '../../../../components/ui/textarea';
import { Button } from '../../../../components/ui/button';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription } from '../../../../components/ui/dialog';
import { updateFunction, setEnvVars } from '../../../../services/functionService';

// Status toggle removed (no backend support)

interface FunctionInfoModalProps {
  isOpen: boolean;
  onClose: () => void;
  functionId: string;
  functionName: string;
  functionDescription?: string;
  functionStatus?: string;
  envVars?: Record<string, string>;
  onUpdate?: () => void;
}

const FunctionInfoModal: React.FC<FunctionInfoModalProps> = ({
  isOpen,
  onClose,
  functionId,
  functionName,
  functionDescription = '',
  functionStatus,
  envVars = {},
  onUpdate,
}) => {
  const [functionData, setFunctionData] = useState({
    name: functionName,
    description: functionDescription,
  });
  const [envVarsState, setEnvVarsState] = useState<Record<string, string>>({});
  const [envVarsChanged, setEnvVarsChanged] = useState(false);
  
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [initialLoading, setInitialLoading] = useState(false);

  // No status handling needed
  useEffect(() => {
    setInitialLoading(false);
  }, [isOpen]);

  // Update state when props change
  useEffect(() => {
    setFunctionData({
      name: functionName,
      description: functionDescription || '',
    });
    // Initialize env vars state with values from the envVars object
    const initialEnvVars: Record<string, string> = {};
    if (envVars && typeof envVars === 'object' && !Array.isArray(envVars)) {
      Object.keys(envVars).forEach(envVarName => {
        initialEnvVars[envVarName] = envVars[envVarName] || '';
      });
    }
    setEnvVarsState(initialEnvVars);
    setEnvVarsChanged(false);
  }, [functionName, functionDescription, functionStatus, envVars, isOpen]);

  const handleChange = (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) => {
    const { name, value } = e.target;
    
    setFunctionData({
      ...functionData,
      [name]: value
    });
  };

  // Removed status toggle

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
      // Update function info
      const updatePayload: Partial<{ name: string; description: string }> = {
        name: functionData.name,
        description: functionData.description,
      };
      
      await updateFunction(functionId, updatePayload);
      
      // Update env vars if they changed
      if (envVarsChanged) {
        await setEnvVars(functionId, envVarsState);
      }
      
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
      <DialogContent className="sm:max-w-md max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle className="text-xl font-semibold">Edit Function Information</DialogTitle>
          <DialogDescription>
            Update the function's name and description.
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
            
            <div>
              <label className="block text-sm font-medium mb-2">Environment Variables</label>
              <div className="space-y-2">
                {Object.entries(envVarsState).map(([key, value], index) => (
                  <div key={index} className="flex gap-2 items-center">
                    <Input
                      placeholder="Name"
                      value={key}
                      onChange={(e) => {
                        const newKey = e.target.value;
                        const newEnvVars = { ...envVarsState };
                        delete newEnvVars[key];
                        if (newKey) {
                          newEnvVars[newKey] = value;
                        }
                        setEnvVarsState(newEnvVars);
                        setEnvVarsChanged(true);
                      }}
                      className="flex-1"
                    />
                    <Input
                      type="password"
                      placeholder="Variable value"
                      value={value}
                      onChange={(e) => {
                        const newValue = e.target.value;
                        setEnvVarsState({ ...envVarsState, [key]: newValue });
                        setEnvVarsChanged(true);
                      }}
                      className="flex-1"
                    />
                    <Button
                      type="button"
                      variant="outline"
                      size="sm"
                      onClick={() => {
                        const newEnvVars = { ...envVarsState };
                        delete newEnvVars[key];
                        setEnvVarsState(newEnvVars);
                        setEnvVarsChanged(true);
                      }}
                    >
                      Remove
                    </Button>
                  </div>
                ))}
                <Button
                  type="button"
                  variant="outline"
                  size="sm"
                  onClick={() => {
                    const newEnvVars = { ...envVarsState };
                    const newKey = '';
                    newEnvVars[newKey] = '';
                    setEnvVarsState(newEnvVars);
                    setEnvVarsChanged(true);
                  }}
                >
                  Add Environment Variable
                </Button>
              </div>
              <p className="text-xs text-secondary-500 dark:text-secondary-400 mt-1">
                Environment variables are securely stored. Existing values are hidden for security.
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