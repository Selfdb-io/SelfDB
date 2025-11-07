import React, { useState, useEffect } from 'react';
import { Eye, EyeOff } from 'lucide-react';
import { SelfFunction, createFunction, updateFunction, setEnvVars as setFunctionEnvVars, CreateFunctionRequest, UpdateFunctionRequest } from '../../../../services/functionService';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter, DialogDescription } from '../../../../components/ui/dialog';
import { Label } from '../../../../components/ui/label';
import { Input } from '../../../../components/ui/input';
import { Textarea } from '../../../../components/ui/textarea';
import { Button } from '../../../../components/ui/button';

interface FunctionFormProps {
  isOpen: boolean;
  onClose: () => void;
  onSuccess: (func: SelfFunction) => void;
  editFunction: SelfFunction | null;
}

const FunctionForm: React.FC<FunctionFormProps> = ({
  isOpen,
  onClose,
  onSuccess,
  editFunction
}) => {
  const [name, setName] = useState('');
  const [description, setDescription] = useState('');
  const [code, setCode] = useState('');
  const [timeoutSeconds, setTimeoutSeconds] = useState(30);
  const [memoryLimitMb, setMemoryLimitMb] = useState(512);
  const [maxConcurrent, setMaxConcurrent] = useState(10);
  const [envVars, setEnvVars] = useState<Record<string, string>>({});
  const [envVarVisibility, setEnvVarVisibility] = useState<Record<string, boolean>>({});
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (isOpen && !editFunction) {
      resetForm();
      // Seed with local default snippet for Deno/TypeScript
      setCode(`// Add your function code here
// Runtime: Deno (TypeScript/JavaScript)

export default async function(request, context) {
  const { env } = context;
  
  // Your function logic here
  return { 
    message: "Hello from SelfDB!",
    timestamp: new Date().toISOString()
  };
}`);
    }
  }, [isOpen]);

  useEffect(() => {
    if (editFunction) {
      setName(editFunction.name);
      setDescription(editFunction.description || '');
      setCode(editFunction.code || '');
      setTimeoutSeconds(editFunction.timeout_seconds || 30);
      setMemoryLimitMb(editFunction.memory_limit_mb || 512);
      setMaxConcurrent(editFunction.max_concurrent || 10);
      // Populate env vars with actual values from the function
      const envVarsFromFunction: Record<string, string> = {};
      const visibilityFromFunction: Record<string, boolean> = {};
      if (editFunction.env_vars) {
        Object.keys(editFunction.env_vars).forEach(envVarName => {
          envVarsFromFunction[envVarName] = editFunction.env_vars[envVarName] || '';
          visibilityFromFunction[envVarName] = false; // Start hidden
        });
      }
      setEnvVars(envVarsFromFunction);
      setEnvVarVisibility(visibilityFromFunction);
    }
  }, [editFunction]);

  const resetForm = () => {
    setName('');
    setDescription('');
    setCode('');
    setTimeoutSeconds(30);
    setMemoryLimitMb(512);
    setMaxConcurrent(10);
    setEnvVars({});
    setEnvVarVisibility({});
    setError(null);
  };

  // Removed remote template fetch (not supported by backend)

  const handleSubmit = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    setLoading(true);
    setError(null);

    try {
      let result;

      if (editFunction) {
        // For updates, update function settings and env vars separately
        const updatePayload: UpdateFunctionRequest = {
          description: description || undefined,
          code: code || undefined,
          timeout_seconds: timeoutSeconds,
          memory_limit_mb: memoryLimitMb,
          max_concurrent: maxConcurrent,
        };
        result = await updateFunction(editFunction.id, updatePayload);
        
        // Update env vars if any are set
        if (Object.keys(envVars).length > 0) {
          await setFunctionEnvVars(editFunction.id, envVars);
        }
      } else {
        // For creation, include all fields (always use Deno runtime)
        const createPayload: CreateFunctionRequest = {
          name,
          description: description || undefined,
          code,
          runtime: 'deno',
          timeout_seconds: timeoutSeconds,
          memory_limit_mb: memoryLimitMb,
          max_concurrent: maxConcurrent,
          env_vars: Object.keys(envVars).length > 0 ? envVars : undefined,
        };
        result = await createFunction(createPayload);
      }
      
      onSuccess(result);
      onClose();
      resetForm();
    } catch (err: any) {
      console.error('Error saving function:', err);
      setError(err.response?.data?.detail || err.message || 'An error occurred while saving the function');
    } finally {
      setLoading(false);
    }
  };

  return (
    <Dialog open={isOpen} onOpenChange={(open: boolean) => !open && onClose()}>
      <DialogContent className="sm:max-w-2xl max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle>
            {editFunction ? 'Edit Function' : 'Create New Function'}
          </DialogTitle>
          <DialogDescription>
            {editFunction ? 'Modify your function code and settings below.' : 'Create a new function by providing the details below.'}
          </DialogDescription>
        </DialogHeader>
        
        <form onSubmit={handleSubmit} className="space-y-4">
          {error && (
            <div className="p-4 bg-error-50 dark:bg-error-900/30 border border-error-200 dark:border-error-800 rounded-md text-error-700 dark:text-error-300 text-sm">
              {error}
            </div>
          )}

          {editFunction && (
            <div className="bg-secondary-50 dark:bg-secondary-900/20 p-4 rounded-lg border border-secondary-200 dark:border-secondary-700">
              <h3 className="text-lg font-semibold mb-4 text-secondary-800 dark:text-white">Function Overview</h3>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                <div className="space-y-4">
                  <div>
                    <p className="text-sm font-medium text-secondary-500 dark:text-secondary-400">HTTP Endpoint</p>
                    <p className="mt-1 font-mono bg-secondary-100 dark:bg-secondary-800 p-2 rounded text-secondary-800 dark:text-white">
                      /{editFunction.name.toLowerCase()}
                    </p>
                  </div>
                  <div>
                    <p className="text-sm font-medium text-secondary-500 dark:text-secondary-400">Runtime</p>
                    <p className="mt-1">{editFunction.runtime || 'deno_typescript'}</p>
                  </div>
                  <div>
                    <p className="text-sm font-medium text-secondary-500 dark:text-secondary-400">Environment Variables</p>
                    <div className="mt-1">
                      {editFunction.env_vars && Object.keys(editFunction.env_vars).length > 0 ? (
                        <div className="flex flex-wrap gap-1">
                          {Object.keys(editFunction.env_vars).map((envVarName, index) => (
                            <span
                              key={index}
                              className="inline-flex items-center px-2 py-1 rounded-md text-xs font-medium bg-secondary-200 dark:bg-secondary-700 text-secondary-800 dark:text-secondary-200"
                            >
                              {envVarName}
                            </span>
                          ))}
                        </div>
                      ) : (
                        <p className="text-secondary-400 dark:text-secondary-500 text-sm">No environment variables configured</p>
                      )}
                    </div>
                  </div>
                </div>
                <div className="space-y-4">
                  <div>
                    <p className="text-sm font-medium text-secondary-500 dark:text-secondary-400">Status</p>
                    <div className="mt-1">
                      <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium
                        ${editFunction.is_active
                          ? 'bg-success-100 dark:bg-success-900/20 text-success-800 dark:text-success-300'
                          : 'bg-warning-100 dark:bg-warning-900/20 text-warning-800 dark:text-warning-300'}`}
                      >
                        {editFunction.is_active ? 'Active' : 'Inactive'}
                      </span>
                    </div>
                  </div>
                  <div>
                    <p className="text-sm font-medium text-secondary-500 dark:text-secondary-400">Deployment Status</p>
                    <div className="mt-1">
                      <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium
                        ${editFunction.deployment_status === 'deployed'
                          ? 'bg-success-100 dark:bg-success-900/20 text-success-800 dark:text-success-300'
                          : editFunction.deployment_status === 'failed'
                          ? 'bg-error-100 dark:bg-error-900/20 text-error-800 dark:text-error-300'
                          : 'bg-warning-100 dark:bg-warning-900/20 text-warning-800 dark:text-warning-300'}`}
                      >
                        {editFunction.deployment_status === 'deployed' ? 'Deployed' :
                         editFunction.deployment_status === 'failed' ? 'Failed' :
                         editFunction.deployment_status === 'pending' ? 'Pending' : 'Draft'}
                      </span>
                    </div>
                  </div>
                  <div>
                    <p className="text-sm font-medium text-secondary-500 dark:text-secondary-400">Executions</p>
                    <p className="mt-1">{editFunction.execution_success_count}/{editFunction.execution_count} successful</p>
                  </div>
                  {editFunction.avg_execution_time_ms && (
                    <div>
                      <p className="text-sm font-medium text-secondary-500 dark:text-secondary-400">Avg Execution Time</p>
                      <p className="mt-1">{editFunction.avg_execution_time_ms}ms</p>
                    </div>
                  )}
                  <div>
                    <p className="text-sm font-medium text-secondary-500 dark:text-secondary-400">Created</p>
                    <p className="mt-1">{new Date(editFunction.created_at).toLocaleString()}</p>
                  </div>
                  <div>
                    <p className="text-sm font-medium text-secondary-500 dark:text-secondary-400">Last Updated</p>
                    <p className="mt-1">{new Date(editFunction.updated_at).toLocaleString()}</p>
                  </div>
                </div>
              </div>
            </div>
          )}

          <div className="space-y-2">
            <Label htmlFor="name">Function Name</Label>
            <Input
              id="name"
              value={name}
              onChange={(e: React.ChangeEvent<HTMLInputElement>) => setName(e.target.value)}
              placeholder="my-function"
              required
              disabled={!!editFunction}
            />
            {editFunction && (
              <p className="text-xs text-secondary-500 dark:text-secondary-400">
                Function name cannot be changed after creation.
              </p>
            )}
          </div>
          
          <div className="space-y-2">
            <Label htmlFor="description">Description (Optional)</Label>
            <Textarea
              id="description"
              value={description}
              onChange={(e: React.ChangeEvent<HTMLTextAreaElement>) => setDescription(e.target.value)}
              placeholder="Describe what this function does"
              rows={2}
            />
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label htmlFor="timeout">Timeout (seconds)</Label>
              <Input
                id="timeout"
                type="number"
                min="5"
                max="300"
                value={timeoutSeconds}
                onChange={(e: React.ChangeEvent<HTMLInputElement>) => setTimeoutSeconds(Number(e.target.value))}
              />
            </div>

            <div className="space-y-2">
              <Label htmlFor="memory">Memory Limit (MB)</Label>
              <Input
                id="memory"
                type="number"
                min="128"
                max="4096"
                value={memoryLimitMb}
                onChange={(e: React.ChangeEvent<HTMLInputElement>) => setMemoryLimitMb(Number(e.target.value))}
              />
            </div>
          </div>

          <div className="space-y-2">
            <Label htmlFor="concurrency">Max Concurrent Executions</Label>
            <Input
              id="concurrency"
              type="number"
              min="1"
              max="100"
              value={maxConcurrent}
              onChange={(e: React.ChangeEvent<HTMLInputElement>) => setMaxConcurrent(Number(e.target.value))}
            />
          </div>

          {!editFunction && (
            <>
            </>
          )}

          <div className="space-y-2">
            <Label>Environment Variables</Label>
            <div className="space-y-2">
              {Object.entries(envVars).map(([key, value], index) => (
                <div key={index} className="flex gap-2 items-center">
                  <Input
                    placeholder="Name"
                    value={key}
                    onChange={(e) => {
                      const newKey = e.target.value;
                      const newEnvVars = { ...envVars };
                      const newVisibility = { ...envVarVisibility };
                      delete newEnvVars[key];
                      delete newVisibility[key];
                      if (newKey) {
                        newEnvVars[newKey] = value;
                        newVisibility[newKey] = envVarVisibility[key] || false;
                      }
                      setEnvVars(newEnvVars);
                      setEnvVarVisibility(newVisibility);
                    }}
                    className="flex-1"
                  />
                  <div className="relative flex-1">
                    <Input
                      type={envVarVisibility[key] ? "text" : "password"}
                      placeholder="Variable value"
                      value={value}
                      onChange={(e) => {
                        const newValue = e.target.value;
                        setEnvVars({ ...envVars, [key]: newValue });
                      }}
                      className="pr-10"
                    />
                    <button
                      type="button"
                      onClick={() => {
                        setEnvVarVisibility({
                          ...envVarVisibility,
                          [key]: !envVarVisibility[key]
                        });
                      }}
                      className="absolute right-2 top-1/2 transform -translate-y-1/2 text-secondary-400 hover:text-secondary-600 dark:text-secondary-500 dark:hover:text-secondary-300"
                    >
                      {envVarVisibility[key] ? (
                        <EyeOff className="h-4 w-4" />
                      ) : (
                        <Eye className="h-4 w-4" />
                      )}
                    </button>
                  </div>
                  <Button
                    type="button"
                    variant="outline"
                    size="sm"
                    onClick={() => {
                      const newEnvVars = { ...envVars };
                      const newVisibility = { ...envVarVisibility };
                      delete newEnvVars[key];
                      delete newVisibility[key];
                      setEnvVars(newEnvVars);
                      setEnvVarVisibility(newVisibility);
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
                  const newEnvVars = { ...envVars };
                  const newKey = '';
                  newEnvVars[newKey] = '';
                  setEnvVars(newEnvVars);
                  setEnvVarVisibility({
                    ...envVarVisibility,
                    [newKey]: false
                  });
                }}
              >
                Add Environment Variable
              </Button>
            </div>
            <p className="text-xs text-secondary-500 dark:text-secondary-400">
              Environment variables are securely stored and available to your function at runtime.
              {editFunction && " Existing values are hidden for security."} Click the eye icon to show/hide values.
            </p>
          </div>

          <div className="space-y-2">
            <Label htmlFor="code">Function Code</Label>
            <Textarea
              id="code"
              value={code}
              onChange={(e: React.ChangeEvent<HTMLTextAreaElement>) => setCode(e.target.value)}
              placeholder="// Your function code"
              rows={10}
              className="font-mono text-sm"
              required
            />
            <p className="text-xs text-secondary-500 dark:text-secondary-400">
              Write your function code using JavaScript/TypeScript. Use 'request' and 'context' parameters.
            </p>
          </div>
          
          <DialogFooter>
            <Button
              type="button"
              variant="outline"
              onClick={onClose}
              disabled={loading}
            >
              Cancel
            </Button>
            <Button type="submit" disabled={loading}>
              {loading ? (
                <div className="flex items-center">
                  <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white mr-2"></div>
                  {editFunction ? 'Updating...' : 'Creating...'}
                </div>
              ) : (
                editFunction ? 'Update Function' : 'Create Function'
              )}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
};

export default FunctionForm;