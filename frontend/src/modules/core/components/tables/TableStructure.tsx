import React, { useEffect, useState } from 'react';
import { Column, ColumnDefinition, addColumn, updateColumn, deleteColumn } from '../../../../services/tableService';
import { Table, TableHeader } from '../../../../components/ui/table';
import { Edit, Trash, AlertTriangle, KeyRound, PlusCircle } from 'lucide-react';
import { Input } from '../../../../components/ui/input';
import { Button } from '../../../../components/ui/button';
import { DATA_TYPES, CHARACTER_TYPES, NUMERIC_TYPES } from '../../constants/databaseTypes';

interface TableStructureProps {
  columns: Column[];
  primaryKeys?: string[];
  tableName: string;
  tableDescription?: string;
  onStructureChange?: () => void;
}

// Modal component for adding or editing columns
interface ColumnModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSave: (columnData: Partial<Column>) => void;
  column?: Column;
  isEdit?: boolean;
}

const ColumnModal: React.FC<ColumnModalProps> = ({ 
  isOpen, 
  onClose, 
  onSave, 
  column, 
  isEdit = false 
}) => {
  const [columnData, setColumnData] = useState<Partial<Column>>(
    column || {
      name: '',
      type: 'text',
      nullable: true,
      default: null,
    }
  );
  
  const [error, setError] = useState<string | null>(null);

  // Reset form values each time the modal opens or when switching between add/edit
  useEffect(() => {
    if (isOpen) {
      setColumnData(
        column || {
          name: '',
          type: 'text',
          nullable: true,
          default: null,
        }
      );
      setError(null);
    }
  }, [isOpen, column]);

  const handleChange = (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement | HTMLTextAreaElement>) => {
    const { name, value } = e.target;
    setColumnData({
      ...columnData,
      [name]: value
    });
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    
    // Basic validation
    if (!columnData.name) {
      setError('Column name is required');
      return;
    }
    
    if (!columnData.type) {
      setError('Column type is required');
      return;
    }
    
    // Create a copy for formatting
    const formattedColumnData = { ...columnData };
    
    // Clean up type-specific fields that don't apply to the current type
    if (!NUMERIC_TYPES.includes(formattedColumnData.type || '')) {
      // Remove numeric-specific fields if not a numeric type
    }
    
    if (!CHARACTER_TYPES.includes(formattedColumnData.type || '')) {
      // Remove character-specific fields if not a character type
    }
    
    onSave(formattedColumnData);
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div className="bg-white dark:bg-secondary-800 rounded-lg shadow-lg max-w-2xl w-full p-6">
        <h2 className="text-xl font-semibold mb-4">
          {isEdit ? 'Edit Column' : 'Add New Column'}
        </h2>
        
        {error && (
          <div className="mb-4 p-3 bg-error-50 border border-error-200 rounded-md text-error-700 flex items-center">
            <AlertTriangle className="h-5 w-5 mr-2" />
            <span>{error}</span>
          </div>
        )}
        
        <form onSubmit={handleSubmit}>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-4">
            <div>
              <label className="block text-sm font-medium mb-1">Column Name</label>
              <Input
                name="name"
                value={columnData.name || ''}
                onChange={handleChange}
                disabled={isEdit}
                placeholder="e.g. first_name"
                className="w-full"
              />
            </div>
            
            <div>
              <label className="block text-sm font-medium mb-1">Data Type</label>
              <select
                name="type"
                value={columnData.type || ''}
                onChange={handleChange}
                className="w-full p-1 border border-secondary-300 dark:border-secondary-600 rounded-md bg-white dark:bg-secondary-900 text-secondary-800 dark:text-white h-8"
              >
                {DATA_TYPES.map(type => (
                  <option key={type} value={type}>{type}</option>
                ))}
              </select>
            </div>
            
          </div>
          
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-4">  
            <div>
              <label className="block text-sm font-medium mb-1">Nullable</label>
              <input
                type="checkbox"
                name="nullable"
                checked={columnData.nullable || false}
                onChange={(e) => handleChange({ target: { name: 'nullable', value: e.target.checked } } as any)}
                className="w-4 h-4 text-primary-600 border-secondary-300 dark:border-secondary-600 rounded focus:ring-primary-500"
              />
            </div>
            
            <div>
              <label className="block text-sm font-medium mb-1">Default Value</label>
              <Input
                name="default"
                value={columnData.default || ''}
                onChange={handleChange}
                placeholder="Default value"
              />
            </div>
          </div>
          
          <div className="flex justify-end space-x-3">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 border border-secondary-300 rounded-md hover:bg-secondary-50"
            >
              Cancel
            </button>
            <button
              type="submit"
              className="px-4 py-2 bg-primary-500 text-white rounded-md hover:bg-primary-600"
            >
              {isEdit ? 'Update Column' : 'Add Column'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};

// Confirmation modal for delete operations
interface ConfirmModalProps {
  isOpen: boolean;
  onClose: () => void;
  onConfirm: () => void;
  title: string;
  message: string;
}

const ConfirmModal: React.FC<ConfirmModalProps> = ({ 
  isOpen, 
  onClose, 
  onConfirm, 
  title, 
  message 
}) => {
  if (!isOpen) return null;
  
  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div className="bg-white dark:bg-secondary-800 rounded-lg shadow-lg max-w-md w-full p-6">
        <h2 className="text-xl font-semibold mb-2">{title}</h2>
        <p className="mb-6 text-secondary-600 dark:text-secondary-400">{message}</p>
        <div className="flex justify-end space-x-3">
          <button
            onClick={onClose}
            className="px-4 py-2 border border-secondary-300 rounded-md hover:bg-secondary-50"
          >
            Cancel
          </button>
          <button
            onClick={onConfirm}
            className="px-4 py-2 bg-error-500 text-white rounded-md hover:bg-error-600"
          >
            Delete
          </button>
        </div>
      </div>
    </div>
  );
};

const TableStructure: React.FC<TableStructureProps> = ({ 
  columns, 
  primaryKeys = [],
  tableName,
  onStructureChange 
}) => {
  const [isAddModalOpen, setIsAddModalOpen] = useState(false);
  const [isEditModalOpen, setIsEditModalOpen] = useState(false);
  const [isDeleteModalOpen, setIsDeleteModalOpen] = useState(false);
  const [selectedColumn, setSelectedColumn] = useState<Column | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  if (!columns || columns.length === 0) {
    return (
      <div className="p-8 text-center">
        <p className="text-secondary-600 dark:text-secondary-400">No columns found for this table.</p>
      </div>
    );
  }

  // Define headers for the table
  const headers: TableHeader[] = [
    { key: 'primaryKey', label: '', isSortable: false },
    { key: 'columnName', label: 'Column Name', isSortable: true },
    { key: 'dataType', label: 'Data Type', isSortable: true },
    { key: 'nullable', label: 'Nullable', isSortable: true },
    { key: 'defaultValue', label: 'Default Value', isSortable: true },
    { key: 'description', label: 'Description', isSortable: true },
  ];

  // Transform columns data to match the format expected by the Table component
  const tableData = columns.map(column => ({
    primaryKey: '',  // We'll use renderRowIcon to display the primary key indicator
    columnName: column.name,
    dataType: formatDataType(column),
    nullable: column.nullable ? 'NULL' : 'NOT NULL',
    defaultValue: column.default !== null ? column.default : 'null',
    description: 'No description', // New API doesn't support column descriptions
    // Store the original column for use in renderActions
    originalColumn: column,
  }));

  const handleAddColumn = async (columnData: Partial<Column>) => {
    setLoading(true);
    setError(null);
    try {
      await addColumn(tableName, columnData as ColumnDefinition);
      setIsAddModalOpen(false);
      if (onStructureChange) onStructureChange();
    } catch (err: any) {
      setError(err.message || 'Failed to add column');
    } finally {
      setLoading(false);
    }
  };

  const handleEditColumn = async (columnData: Partial<Column>) => {
    if (!selectedColumn) return;
    
    setLoading(true);
    setError(null);
    try {
      const updateData = {
        new_name: columnData.name,
        type: columnData.type,
        nullable: columnData.nullable,
      };
      await updateColumn(tableName, selectedColumn.name, updateData);
      setIsEditModalOpen(false);
      if (onStructureChange) onStructureChange();
    } catch (err: any) {
      setError(err.message || 'Failed to update column');
    } finally {
      setLoading(false);
    }
  };

  const handleDeleteColumn = async () => {
    if (!selectedColumn) return;
    
    setLoading(true);
    setError(null);
    try {
      await deleteColumn(tableName, selectedColumn.name);
      setIsDeleteModalOpen(false);
      if (onStructureChange) onStructureChange();
    } catch (err: any) {
      setError(err.message || 'Failed to delete column');
    } finally {
      setLoading(false);
    }
  };

  // Render row icon (primary key indicator)
  const renderRowIcon = (item: any) => {
    if (primaryKeys.includes(item.originalColumn.column_name)) {
      return (
        <span 
          title="Primary Key"
          className="inline-block w-5 h-5 text-primary-500 dark:text-primary-400"
        >
          <KeyRound className="h-5 w-5" />
        </span>
      );
    }
    return null;
  };

  // Render custom data type cell with styling
  const renderDataType = (dataType: string) => (
    <span className="px-2 py-1 text-xs rounded-full bg-secondary-100 dark:bg-secondary-700 text-secondary-800 dark:text-secondary-200 font-mono">
      {dataType}
    </span>
  );

  // Render nullable status with appropriate styling
  const renderNullable = (nullable: string) => (
    nullable === 'NULL' ? (
      <span className="px-2 py-1 text-xs rounded-full bg-secondary-100 dark:bg-secondary-700 text-secondary-600 dark:text-secondary-300">
        NULL
      </span>
    ) : (
      <span className="px-2 py-1 text-xs rounded-full bg-primary-100 dark:bg-primary-900/30 text-primary-700 dark:text-primary-300 font-medium">
        NOT NULL
      </span>
    )
  );

  // Custom render for default value with styling
  const renderDefaultValue = (value: string) => (
    value === 'null' ? (
      <span className="text-secondary-400 dark:text-secondary-500 italic font-mono text-sm">null</span>
    ) : (
      <span className="font-mono text-sm">{value}</span>
    )
  );

  // Custom render for description with styling
  const renderDescription = (description: string) => (
    description === 'No description' ? (
      <span className="text-secondary-400 dark:text-secondary-500 italic">No description</span>
    ) : (
      description
    )
  );

  // Render action buttons for each row
  const renderActions = (item: any) => (
    <div className="flex justify-center space-x-2">
      <button
        className="p-1 text-primary-500 hover:text-primary-600 dark:text-primary-400 dark:hover:text-primary-300"
        title="Edit Column"
        onClick={() => {
          setSelectedColumn(item.originalColumn);
          setIsEditModalOpen(true);
        }}
      >
        <Edit className="h-5 w-5" />
      </button>
      <button
        className="p-1 text-error-500 hover:text-error-600 dark:text-error-400 dark:hover:text-error-300"
        title="Delete Column"
        onClick={() => {
          setSelectedColumn(item.originalColumn);
          setIsDeleteModalOpen(true);
        }}
      >
        <Trash className="h-5 w-5" />
      </button>
    </div>
  );

  // Custom render function for each cell
  const customData = tableData.map(item => ({
    ...item,
    dataType: renderDataType(item.dataType),
    nullable: renderNullable(item.nullable),
    defaultValue: renderDefaultValue(item.defaultValue),
    description: renderDescription(item.description)
  }));

  return (
    <div className="space-y-4">
      {error && (
        <div className="mb-4 p-3 bg-error-50 border border-error-200 rounded-md text-error-700 flex items-center">
          <AlertTriangle className="h-5 w-5 mr-2" />
          <span>{error}</span>
        </div>
      )}
      
      <div className="mb-4 flex justify-end">
        <Button
          onClick={() => setIsAddModalOpen(true)}
          size="sm"
          className="flex items-center gap-2"
          disabled={loading}
        >
          <PlusCircle className="w-4 h-4" />
          Add Column
        </Button>
      </div>
      
      <Table
        headers={headers}
        data={customData}
        renderRowIcon={renderRowIcon}
        renderActions={renderActions}
        tableClassName="min-w-full"
      />
      
      {/* Add Column Modal */}
      <ColumnModal
        isOpen={isAddModalOpen}
        onClose={() => setIsAddModalOpen(false)}
        onSave={handleAddColumn}
      />
      
      {/* Edit Column Modal */}
      {selectedColumn && (
        <ColumnModal
          isOpen={isEditModalOpen}
          onClose={() => setIsEditModalOpen(false)}
          onSave={handleEditColumn}
          column={selectedColumn}
          isEdit={true}
        />
      )}
      
      {/* Delete Confirmation Modal */}
      {selectedColumn && (
        <ConfirmModal
          isOpen={isDeleteModalOpen}
          onClose={() => setIsDeleteModalOpen(false)}
          onConfirm={handleDeleteColumn}
          title="Delete Column"
          message={`Are you sure you want to delete the column "${selectedColumn.name}"? This action cannot be undone.`}
        />
      )}
    </div>
  );
};

// Helper function to format data type display
const formatDataType = (column: Column): string => {
  return column.type.toUpperCase();
};

export default TableStructure; 