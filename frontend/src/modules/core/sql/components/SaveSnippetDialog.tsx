import React, { useState } from 'react';

interface SaveSnippetDialogProps {
  isOpen: boolean;
  onClose: () => void;
  onSave: (name: string, description: string, isShared: boolean) => void;
}

const SaveSnippetDialog: React.FC<SaveSnippetDialogProps> = ({
  isOpen,
  onClose,
  onSave,
}) => {
  const [name, setName] = useState('');
  const [description, setDescription] = useState('');
  const [isShared, setIsShared] = useState(false);

  if (!isOpen) return null;

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    onSave(name, description, isShared);
    setName('');
    setDescription('');
    setIsShared(false);
  };

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div className="bg-white dark:bg-secondary-800 rounded-lg shadow-xl max-w-md w-full">
        <div className="p-6">
          <h3 className="text-lg font-heading font-semibold text-secondary-800 dark:text-secondary-300 mb-4">
            Save SQL Snippet
          </h3>
          
          <form onSubmit={handleSubmit}>
            <div className="mb-4">
              <label htmlFor="snippet-name" className="block text-xs font-medium text-secondary-700 dark:text-secondary-300 mb-1">
                Name
              </label>
              <input
                id="snippet-name"
                type="text"
                value={name}
                onChange={(e) => setName(e.target.value)}
                className="w-full px-3 py-2 border border-secondary-300 dark:border-secondary-700 rounded-md bg-white dark:bg-secondary-900 text-secondary-800 dark:text-white focus:outline-none focus:ring-2 focus:ring-primary-500"
                required
              />
            </div>
            
            <div className="mb-4">
              <label htmlFor="snippet-description" className="block text-xs font-medium text-secondary-700 dark:text-secondary-300 mb-1">
                Description (optional)
              </label>
              <textarea
                id="snippet-description"
                value={description}
                onChange={(e) => setDescription(e.target.value)}
                className="w-full px-3 py-2 border border-secondary-300 dark:border-secondary-700 rounded-md bg-white dark:bg-secondary-900 text-secondary-800 dark:text-white focus:outline-none focus:ring-2 focus:ring-primary-500"
                rows={3}
              />
            </div>
            
            <div className="mb-4 flex items-center">
              <input
                id="share-snippet"
                type="checkbox"
                checked={isShared}
                onChange={(e) => setIsShared(e.target.checked)}
                className="h-4 w-4 text-primary-600 focus:ring-primary-500 border-secondary-300 dark:border-secondary-700 rounded"
              />
              <label htmlFor="share-snippet" className="ml-2 block text-xs text-secondary-700 dark:text-secondary-300">
                Share with other users
              </label>
            </div>
            
            <div className="flex justify-end space-x-2 mt-6">
              <button
                type="button"
                onClick={onClose}
                className="px-4 py-2 border border-secondary-300 dark:border-secondary-700 rounded-md shadow-sm text-xs font-medium text-secondary-700 dark:text-secondary-300 bg-white dark:bg-secondary-900 hover:bg-secondary-50 dark:hover:bg-secondary-800 focus:outline-none focus:ring-2 focus:ring-primary-500"
              >
                Cancel
              </button>
              <button
                type="submit"
                disabled={!name.trim()}
                className="px-4 py-2 border border-transparent rounded-md shadow-sm text-xs font-medium text-white bg-primary-600 hover:bg-primary-700 focus:outline-none focus:ring-2 focus:ring-primary-500 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                Save
              </button>
            </div>
          </form>
        </div>
      </div>
    </div>
  );
};

export default SaveSnippetDialog; 