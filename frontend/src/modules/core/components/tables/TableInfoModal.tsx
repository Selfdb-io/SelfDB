import React, { useState } from 'react';
import { AlertTriangle } from 'lucide-react';
import { Input } from '../../../../components/ui/input';
import { updateTable } from '../../../../services/tableService';

interface TableInfoModalProps {
  isOpen: boolean;
  onClose: () => void;
  tableName: string;
  tableDescription?: string;
  onStructureChange?: () => void;
}

const TableInfoModal: React.FC<TableInfoModalProps> = ({
  isOpen,
  onClose,
  tableName,
  tableDescription = '',
  onStructureChange,
}) => {
  const [tableData, setTableData] = useState<{ new_name: string; description: string }>({
    new_name: tableName,
    description: tableDescription,
  });
  
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const handleChange = (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) => {
    const { name, value } = e.target;
    setTableData({
      ...tableData,
      [name]: value
    });
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    
    // Basic validation
    if (!tableData.new_name.trim()) {
      setError('Table name is required');
      return;
    }
    
    // Check if table name has changed
    const data: { new_name?: string; description?: string } = {
      description: tableData.description
    };
    
    if (tableData.new_name !== tableName) {
      data.new_name = tableData.new_name;
    }
    
    setLoading(true);
    setError(null);
    
    try {
      await updateTable(tableName, data);
      onClose();
      if (onStructureChange) onStructureChange();
    } catch (err: any) {
      setError(err.message || 'Failed to update table information');
    } finally {
      setLoading(false);
    }
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div className="bg-white dark:bg-secondary-800 rounded-lg shadow-lg max-w-2xl w-full p-6">
        <h2 className="text-xl font-semibold mb-4">
          Edit Table Information
        </h2>
        
        {error && (
          <div className="mb-4 p-3 bg-error-50 border border-error-200 rounded-md text-error-700 flex items-center">
            <AlertTriangle className="h-5 w-5 mr-2" />
            <span>{error}</span>
          </div>
        )}
        
        <form onSubmit={handleSubmit}>
          <div className="mb-4">
            <label className="block text-sm font-medium mb-1">Table Name</label>
            <Input
              name="new_name"
              value={tableData.new_name}
              onChange={handleChange}
              placeholder="e.g. users"
              className="w-full"
            />
          </div>
          
          <div className="mb-4">
            <label className="block text-sm font-medium mb-1">Description</label>
            <textarea
              name="description"
              value={tableData.description}
              onChange={handleChange}
              rows={3}
              className="w-full rounded-md border border-secondary-200 bg-white px-3 py-2 text-sm"
              placeholder="Table description..."
            />
          </div>
          
          <div className="flex justify-end space-x-3">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 border border-secondary-300 rounded-md hover:bg-secondary-50"
              disabled={loading}
            >
              Cancel
            </button>
            <button
              type="submit"
              className="px-4 py-2 bg-primary-500 text-white rounded-md hover:bg-primary-600"
              disabled={loading}
            >
              {loading ? 'Updating...' : 'Update Table'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};

export default TableInfoModal; 