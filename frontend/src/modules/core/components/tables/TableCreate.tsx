import React, { useState } from 'react';
import { createTable } from '../../../../services/tableService';
import { Modal } from '../../../../components/ui/modal';
import { Button } from '../../../../components/ui/button';
import { Input } from '../../../../components/ui/input';
import { PlusCircle } from 'lucide-react';
import { DATA_TYPES } from '../../constants/databaseTypes';

interface ColumnDefinition {
  name: string;
  type: string;
  nullable: boolean;
  primaryKey: boolean;
}

interface TableCreateProps {
  isOpen: boolean;
  onClose: () => void;
  onTableCreated?: () => void;
}

const TableCreate: React.FC<TableCreateProps> = ({ isOpen, onClose, onTableCreated }) => {
  const [tableName, setTableName] = useState('');
  const [description, setDescription] = useState('');
  const [columns, setColumns] = useState<ColumnDefinition[]>([
    { name: 'id', type: 'INTEGER', nullable: false, primaryKey: true },
  ]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const resetForm = () => {
    setTableName('');
    setDescription('');
    setColumns([
      { name: 'id', type: 'INTEGER', nullable: false, primaryKey: true },
    ]);
    setError(null);
  };

  const handleClose = () => {
    resetForm();
    onClose();
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    
    if (!tableName.trim()) {
      setError('Table name is required');
      return;
    }
    
    if (columns.length === 0) {
      setError('At least one column is required');
      return;
    }
    
    try {
      setLoading(true);
      setError(null);
      
      await createTable({
        name: tableName,
        description,
        columns: columns.map(col => ({
          name: col.name,
          type: col.type,
          nullable: col.nullable,
          primary_key: col.primaryKey
        }))
      });
      
      handleClose();
      if (onTableCreated) {
        onTableCreated();
      }
    } catch (err: any) {
      console.error('Error creating table:', err);
      setError(err.response?.data?.detail || err.message || 'Failed to create table');
    } finally {
      setLoading(false);
    }
  };

  const addColumn = () => {
    setColumns([
      ...columns,
      { name: '', type: 'TEXT', nullable: true, primaryKey: false }
    ]);
  };

  const updateColumn = (index: number, field: keyof ColumnDefinition, value: string | boolean) => {
    const updatedColumns = [...columns];
    updatedColumns[index] = {
      ...updatedColumns[index],
      [field]: value
    };
    setColumns(updatedColumns);
  };

  const removeColumn = (index: number) => {
    setColumns(columns.filter((_, i) => i !== index));
  };

  return (
    <Modal 
      isOpen={isOpen} 
      onClose={handleClose} 
      title="Create New Table"
      size="xl"
    >
      <form onSubmit={handleSubmit} className="space-y-6">
        {error && (
          <div className="p-4 bg-error-50 dark:bg-error-900/20 border border-error-200 dark:border-error-800 rounded-md text-error-700 dark:text-error-300">
            {error}
          </div>
        )}

        <div>
          <label className="block text-sm font-medium text-secondary-700 dark:text-secondary-300 mb-1" htmlFor="tableName">
            Table Name
          </label>
          <Input
            id="tableName"
            type="text"
            value={tableName}
            onChange={(e) => setTableName(e.target.value)}
            className="w-full"
            placeholder="Enter table name"
            disabled={loading}
            required
          />
        </div>

        <div>
          <label className="block text-sm font-medium text-secondary-700 dark:text-secondary-300 mb-1" htmlFor="description">
            Description (Optional)
          </label>
          <textarea
            id="description"
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            className="w-full p-2 border border-secondary-300 dark:border-secondary-600 rounded-md bg-white dark:bg-secondary-900 text-secondary-800 dark:text-white h-20 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary-600 focus-visible:ring-offset-2"
            placeholder="Enter table description"
            disabled={loading}
          />
        </div>

        <div>
          <h3 className="text-sm font-medium text-secondary-700 dark:text-secondary-300 mb-2">Columns</h3>
          <div className="overflow-x-auto border border-secondary-200 dark:border-secondary-700 rounded-md">
            <table className="min-w-full divide-y divide-secondary-200 dark:divide-secondary-700">
              <thead className="bg-secondary-50 dark:bg-secondary-800">
                <tr>
                  <th className="px-4 py-2 text-left text-xs font-medium text-secondary-500 dark:text-secondary-400 uppercase tracking-wider">
                    Name
                  </th>
                  <th className="px-4 py-2 text-left text-xs font-medium text-secondary-500 dark:text-secondary-400 uppercase tracking-wider">
                    Type
                  </th>
                  <th className="px-4 py-2 text-center text-xs font-medium text-secondary-500 dark:text-secondary-400 uppercase tracking-wider">
                    Nullable
                  </th>
                  <th className="px-4 py-2 text-center text-xs font-medium text-secondary-500 dark:text-secondary-400 uppercase tracking-wider">
                    Primary Key
                  </th>
                  <th className="px-4 py-2 text-center text-xs font-medium text-secondary-500 dark:text-secondary-400 uppercase tracking-wider">
                    Actions
                  </th>
                </tr>
              </thead>
              <tbody className="bg-white dark:bg-secondary-800 divide-y divide-secondary-200 dark:divide-secondary-700">
                {columns.map((column, index) => (
                  <tr key={index}>
                    <td className="px-4 py-2">
                      <Input
                        type="text"
                        value={column.name}
                        onChange={(e) => updateColumn(index, 'name', e.target.value)}
                        className="w-full p-1 h-8"
                        placeholder="Column name"
                        disabled={loading}
                        required
                      />
                    </td>
                    <td className="px-4 py-2">
                      <select
                        value={column.type}
                        onChange={(e) => updateColumn(index, 'type', e.target.value)}
                        className="w-full p-1 border border-secondary-300 dark:border-secondary-600 rounded-md bg-white dark:bg-secondary-900 text-secondary-800 dark:text-white h-8"
                        disabled={loading}
                      >
                        {DATA_TYPES.map((type) => (
                          <option key={type} value={type}>
                            {type}
                          </option>
                        ))}
                      </select>
                    </td>
                    <td className="px-4 py-2 text-center">
                      <input
                        type="checkbox"
                        checked={column.nullable}
                        onChange={(e) => updateColumn(index, 'nullable', e.target.checked)}
                        className="w-4 h-4 text-primary-600 border-secondary-300 dark:border-secondary-600 rounded focus:ring-primary-500"
                        disabled={loading}
                      />
                    </td>
                    <td className="px-4 py-2 text-center">
                      <input
                        type="checkbox"
                        checked={column.primaryKey}
                        onChange={(e) => updateColumn(index, 'primaryKey', e.target.checked)}
                        className="w-4 h-4 text-primary-600 border-secondary-300 dark:border-secondary-600 rounded focus:ring-primary-500"
                        disabled={loading}
                      />
                    </td>
                    <td className="px-4 py-2 text-center">
                      <Button
                        type="button"
                        onClick={() => removeColumn(index)}
                        variant="ghost"
                        size="sm"
                        className="text-error-600 hover:text-error-700 hover:bg-error-50 dark:text-error-400 dark:hover:text-error-300 dark:hover:bg-error-900/20 h-7 px-2"
                        disabled={columns.length === 1 || loading}
                      >
                        Remove
                      </Button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <div className="mt-2">
            <Button
              type="button"
              onClick={addColumn}
              size="sm"
              variant="outline"
              disabled={loading}
              leftIcon={<PlusCircle className="h-4 w-4" />}
            >
              Add Column
            </Button>
          </div>
        </div>

        <div className="flex justify-end space-x-2 pt-2">
          <Button 
            type="button" 
            variant="outline" 
            onClick={handleClose} 
            disabled={loading}
          >
            Cancel
          </Button>
          <Button 
            type="submit" 
            isLoading={loading} 
          >
            {loading ? 'Creating...' : 'Create Table'}
          </Button>
        </div>
      </form>
    </Modal>
  );
};

export default TableCreate; 