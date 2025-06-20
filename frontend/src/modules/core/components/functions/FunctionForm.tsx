import React, { useState, useEffect } from 'react';
import { Function, createFunction, updateFunction, getFunctionTemplate } from '../../../../services/functionService';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter, DialogDescription } from '../../../../components/ui/dialog';
import { Label } from '../../../../components/ui/label';
import { Input } from '../../../../components/ui/input';
import { Textarea } from '../../../../components/ui/textarea';
import { Button } from '../../../../components/ui/button';

interface FunctionFormProps {
  isOpen: boolean;
  onClose: () => void;
  onSuccess: (func: Function) => void;
  editFunction: Function | null;
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
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (isOpen && !editFunction) {
      resetForm();
      loadTemplate();
    }
  }, [isOpen]);

  useEffect(() => {
    if (editFunction) {
      setName(editFunction.name);
      setDescription(editFunction.description || '');
      setCode(editFunction.code);
    }
  }, [editFunction]);

  const resetForm = () => {
    setName('');
    setDescription('');
    setCode('');
    setError(null);
  };

  const loadTemplate = async () => {
    try {
      const template = await getFunctionTemplate('http');
      setCode(template);
    } catch (err) {
      console.error('Error loading template:', err);
      setCode('// Add your function code here\n\nexport default async function(event, context) {\n  // Your function logic\n  return {\n    statusCode: 200,\n    body: JSON.stringify({ message: "Hello from SelfDB!" })\n  };\n}');
    }
  };

  const handleSubmit = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    setLoading(true);
    setError(null);
    
    try {
      const payload = {
        name,
        description,
        code,
        trigger_type: 'http',
        status: 'draft'
      };
      
      let result;
      
      if (editFunction) {
        result = await updateFunction(editFunction.id, payload);
      } else {
        result = await createFunction(payload);
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
      <DialogContent className="sm:max-w-2xl">
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
          
          <div className="space-y-2">
            <Label htmlFor="name">Function Name</Label>
            <Input
              id="name"
              value={name}
              onChange={(e: React.ChangeEvent<HTMLInputElement>) => setName(e.target.value)}
              placeholder="my-function"
              required
            />
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
              Write your function code using JavaScript/TypeScript
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