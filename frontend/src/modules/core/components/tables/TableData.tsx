import React, { useState, useEffect, useMemo } from 'react';
import { getTableData, getTable, deleteTableData, updateTableData } from '../../../../services/tableService';
import { Loader } from '../ui/Loader';
import { Trash2, Edit } from 'lucide-react';
import { Button } from '../../../../components/ui/button';
import { ConfirmationDialog } from '../../../../components/ui/confirmation-dialog';
import { Table, TableHeader } from '../../../../components/ui/table';
import { Pagination } from '../../../../components/ui/pagination';
import { Input } from '../../../../components/ui/input';

interface TableDataProps {
  tableName: string;
}

// Use forwardRef to allow parent components to get a reference to this component
const TableData = React.forwardRef<{ refreshData: () => Promise<void> }, TableDataProps>((props, ref) => {
  const { tableName } = props;
  const [tableData, setTableData] = useState<any[]>([]);
  const [columns, setColumns] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [currentPage, setCurrentPage] = useState(1);
  const [pageSize] = useState(100);
  const [totalRows, setTotalRows] = useState(0);
  const [totalPages, setTotalPages] = useState(0);

  const [orderBy, setOrderBy] = useState<string | null>(null);
  
  // New state for delete confirmation
  const [deleteConfirmation, setDeleteConfirmation] = useState<{ isOpen: boolean; row: any | null }>({
    isOpen: false,
    row: null
  });
  const [deleting, setDeleting] = useState(false);
  const [deleteError, setDeleteError] = useState<string | null>(null);

  // New state for edit functionality
  const [editModal, setEditModal] = useState<{ isOpen: boolean; row: any | null }>({
    isOpen: false,
    row: null
  });
  const [editData, setEditData] = useState<Record<string, any>>({});
  const [updating, setUpdating] = useState(false);
  const [updateError, setUpdateError] = useState<string | null>(null);

  // Function to fetch table data
  const fetchData = async () => {
    try {
      setLoading(true);
      
      // First, fetch the table structure to ensure we always have column info
      const tableStructure = await getTable(tableName);
      
      // Then fetch table data with pagination, filtering, etc.
      const result = await getTableData(
        tableName, 
        currentPage, 
        pageSize, 
        orderBy,
     
      );
      
      // Use data from the data endpoint
      const newData = Array.isArray(result.data) ? result.data : [];
      setTableData(newData);

      // Handle both direct total and metadata total
      const totalCount = result.total || result.metadata?.total_count || result.metadata?.total || 0;
      setTotalRows(totalCount);
      setTotalPages(Math.ceil(totalCount / pageSize));
      
      // Debug logging
      console.log('TableData fetch result:', {
        tableName,
        currentPage,
        pageSize,
        dataLength: newData.length,
        totalRows: totalCount,
        totalPages: Math.ceil(totalCount / pageSize),
        resultTotal: result.total,
        metadata: result.metadata,
        result: result
      });
      
      // Process table structure to match the expected column format
      if (tableStructure && tableStructure.columns && tableStructure.columns.length > 0) {
        const formattedColumns = tableStructure.columns.map((col: any) => ({
          name: col.column_name,
          type: col.data_type,
        }));
        
        // Override columns with the structure columns even if the data endpoint returned some
        setColumns(formattedColumns);
      } else if (Array.isArray(result.columns)) {
        // Fallback to data endpoint columns if structure doesn't have any
        setColumns(result.columns);
      } else {
        setColumns([]);
      }
      
      setError(null);
    } catch (err: any) {
      console.error('Error fetching table data:', err);
      setError(String(err.response?.data?.detail || err.message || 'Failed to load table data'));
      setTableData([]);
      setColumns([]);
      setTotalRows(0);
      setTotalPages(0);
    } finally {
      setLoading(false);
    }
  };

  // Expose the refreshData method via ref
  React.useImperativeHandle(ref, () => ({
    refreshData: async () => {
      await fetchData();
    }
  }));

  useEffect(() => {
    fetchData();
  }, [tableName, currentPage, pageSize, orderBy]);

  // Format cell value based on its content
  const formatCellValue = (value: any) => {
    if (value === null || value === undefined) {
      return <em className="text-secondary-400 dark:text-secondary-500">NULL</em>;
    }
    
    if (typeof value === 'object') {
      try {
        return <span className="font-mono text-xs">{JSON.stringify(value)}</span>;
      } catch {
        return <em className="text-secondary-400 dark:text-secondary-500">[Object]</em>;
      }
    }
    
    if (typeof value === 'boolean') {
      return value ? 'true' : 'false';
    }
    
    return String(value);
  };



  const handleOrderChange = (column: string) => {
    // Toggle between ascending, descending, and no sort
    if (orderBy === `${column}:asc`) {
      setOrderBy(`${column}:desc`);
    } else if (orderBy === `${column}:desc`) {
      setOrderBy(null);
    } else {
      setOrderBy(`${column}:asc`);
    }
    setCurrentPage(1); // Reset to first page when sorting
  };

  // Prepare headers for the reusable Table component
  const tableHeaders = useMemo<TableHeader[]>(() => {
    // Add row number as the first column
    const headers: TableHeader[] = [
      { key: 'rowNumber', label: '#', isNumeric: true }
    ];
    
    // Add the actual table columns
    columns.forEach(col => {
      headers.push({
        key: col.name,
        label: col.name,
        isSortable: true,
      });
    });
    
    return headers;
  }, [columns]);

  // Prepare data with formatted cells and row numbers for the reusable Table component
  const formattedTableData = useMemo(() => {
    if (!columns.length) return [];
    return tableData.map((row, index) => {
      const formattedRow: Record<string, React.ReactNode> = {};
      
      // Add row number (accounting for pagination)
      const rowNumber = (currentPage - 1) * pageSize + index + 1;
      formattedRow['rowNumber'] = (
        <span className="font-mono text-secondary-600 dark:text-secondary-400">
          {rowNumber}
        </span>
      );
      
      // Add actual column data
      columns.forEach(col => {
        formattedRow[col.name] = formatCellValue(row[col.name]);
      });
      
      // Store the original row index to access raw data later
      formattedRow['__originalIndex'] = index;
      
      return formattedRow;
    });
  }, [tableData, columns, currentPage, pageSize]);

  // Extract sort key and direction
  const [sortKey, sortDirection] = useMemo(() => {
    if (!orderBy) return [null, null];
    const parts = orderBy.split(':');
    return [parts[0], parts[1] as 'asc' | 'desc'];
  }, [orderBy]);

  // New function to handle delete button click
  const handleDeleteClick = (row: any) => {
    setDeleteConfirmation({ isOpen: true, row });
    setDeleteError(null);
  };

  // New function to handle delete confirmation
  const handleDeleteConfirm = async () => {
    if (!deleteConfirmation.row) return;
    
    setDeleting(true);
    setDeleteError(null);
    
    try {
      // Determine the primary key column
      const primaryKey = columns.find(col => 
        // This is a simple heuristic - you might need to adjust based on your data
        col.name === 'id' || col.name.endsWith('_id')
      )?.name || 'id';
      
      // Get the primary key value
      const id = deleteConfirmation.row[primaryKey];
      
      // Use the actual deleteTableData function from tableService
      await deleteTableData(tableName, id, primaryKey);
      
      // Update UI by removing the deleted row
      setTableData(prev => prev.filter(row => row[primaryKey] !== id));
      
      // Close the dialog
      setDeleteConfirmation({ isOpen: false, row: null });
    } catch (err: any) {
      console.error('Error deleting row:', err);
      setDeleteError(err?.response?.data?.detail || err?.message || 'Failed to delete row');
    } finally {
      setDeleting(false);
    }
  };

  // New function to handle delete cancellation
  const handleDeleteCancel = () => {
    setDeleteConfirmation({ isOpen: false, row: null });
    setDeleteError(null);
  };

  // New function to handle edit button click
  const handleEditClick = (row: any) => {
    setEditModal({ isOpen: true, row });
    setEditData({ ...row }); // Copy the row data for editing
    setUpdateError(null);
  };

  // New function to handle edit confirmation
  const handleEditConfirm = async () => {
    if (!editModal.row) return;
    
    setUpdating(true);
    setUpdateError(null);
    
    try {
      // Determine the primary key column
      const primaryKey = columns.find(col => 
        col.name === 'id' || col.name.endsWith('_id')
      )?.name || 'id';
      
      // Get the primary key value
      const id = editModal.row[primaryKey];
      
      // Define system fields that shouldn't be updated
      const systemFields = [
        primaryKey,
        'created_at',
        'updated_at',
        'date_created',
        'date_updated',
        'timestamp',
        'modified_at',
        'inserted_at'
      ];
      
      // Filter out system fields from the update data
      const updateData = Object.keys(editData).reduce((acc, key) => {
        if (!systemFields.includes(key)) {
          acc[key] = editData[key];
        }
        return acc;
      }, {} as Record<string, any>);
      
      // Use the updateTableData function
      await updateTableData(tableName, id, primaryKey, updateData);
      
      // Update UI by replacing the updated row
      setTableData(prev => prev.map(row => 
        row[primaryKey] === id ? { ...row, ...updateData } : row
      ));
      
      // Close the dialog
      setEditModal({ isOpen: false, row: null });
      setEditData({});
    } catch (err: any) {
      console.error('Error updating row:', err);
      setUpdateError(err?.response?.data?.detail || err?.message || 'Failed to update row');
    } finally {
      setUpdating(false);
    }
  };

  // New function to handle edit cancellation
  const handleEditCancel = () => {
    setEditModal({ isOpen: false, row: null });
    setEditData({});
    setUpdateError(null);
  };

  // Handle input changes in edit modal
  const handleEditInputChange = (columnName: string, value: any) => {
    setEditData(prev => ({
      ...prev,
      [columnName]: value
    }));
  };

  // Add renderActions function for the Table component
  const renderActions = (row: any) => {
    const originalIndex = row['__originalIndex'] as number;
    const rawRow = tableData[originalIndex];
    
    return (
      <div className="flex items-center gap-2">
        <Button
          variant="outline"
          size="sm"
          className="text-primary-600 dark:text-primary-400 border-primary-300 dark:border-primary-500 hover:bg-primary-50 dark:hover:bg-primary-900/30 flex items-center"
          onClick={() => handleEditClick(rawRow)} // Use raw data instead of formatted data
          title="Edit row"
        >
          <Edit className="w-4 h-4" />
        </Button>
        <Button
          variant="outline"
          size="sm"
          className="text-error-600 dark:text-error-400 border-error-300 dark:border-error-500 hover:bg-error-50 dark:hover:bg-error-900/30 flex items-center"
          onClick={() => handleDeleteClick(rawRow)} // Use raw data instead of formatted data
          title="Delete row"
        >
          <Trash2 className="w-4 h-4" />
        </Button>
      </div>
    );
  };

  if (loading) {
    return (
      <div className="flex justify-center items-center p-12">
        <Loader size="large" />
      </div>
    );
  } else if (error) {
    // Use the Table component's error state rendering (optional, could keep custom one)
    return (
      <div className="p-6">
        <Table
          headers={[]}
          data={[]}
          errorMessage={error}
        />
      </div>
    );
  }

  return (
    <div>
      {/* Use the reusable Table component */} 
      <Table<Record<string, React.ReactNode>>
        headers={tableHeaders}
        data={formattedTableData}
        isLoading={loading} 
        errorMessage={error}
        isEmpty={tableData.length === 0 && !loading && !error}
        onSort={handleOrderChange}
        sortKey={sortKey}
        sortDirection={sortDirection}
        renderActions={renderActions} // Add the actions renderer
        maxCellWidth={94} // Limit cell width to prevent horizontal scrolling
      />

      {/* Pagination Controls */}
      {columns.length > 0 && (
        <Pagination
          currentPage={currentPage}
          totalPages={totalPages}
          totalItems={totalRows}
          pageSize={pageSize}
          onPageChange={setCurrentPage}
          itemName="rows"
        />
      )}

      {/* Add Delete Confirmation Dialog */}
      <ConfirmationDialog
        isOpen={deleteConfirmation.isOpen}
        onClose={handleDeleteCancel}
        onConfirm={handleDeleteConfirm}
        title="Confirm Delete"
        description={
          <>
            <p className="text-secondary-600 dark:text-secondary-300">
              Are you sure you want to delete this row? This action cannot be undone.
            </p>
            
            {deleteError && (
              <div className="text-error-600 dark:text-error-400 bg-error-50 dark:bg-error-900/30 p-4 rounded mt-4 text-sm">
                {deleteError}
              </div>
            )}
          </>
        }
        confirmButtonText={deleting ? "Deleting..." : "Delete"}
        isDestructive={true}
        isConfirmLoading={deleting}
      />

      {/* Edit Row Modal */}
      {editModal.isOpen && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white dark:bg-secondary-800 rounded-lg shadow-xl max-w-2xl w-full mx-4 max-h-[80vh] overflow-y-auto">
            <div className="p-6">
              <h3 className="text-lg font-semibold text-secondary-800 dark:text-white mb-4">
                Edit Row
              </h3>
              
              {updateError && (
                <div className="text-error-600 dark:text-error-400 bg-error-50 dark:bg-error-900/30 p-4 rounded mb-4 text-sm">
                  {updateError}
                </div>
              )}
              
              <div className="space-y-4">
                {columns.map(column => {
                  // Define system fields that shouldn't be editable
                  const systemFields = [
                    'id',
                    'created_at',
                    'updated_at',
                    'date_created',
                    'date_updated',
                    'timestamp',
                    'modified_at',
                    'inserted_at'
                  ];
                  
                  // Skip system fields and primary key fields
                  const isSystemField = systemFields.includes(column.name) || column.name.endsWith('_id');
                  if (isSystemField) return null;
                  
                  return (
                    <div key={column.name}>
                      <label className="block text-sm font-medium text-secondary-700 dark:text-secondary-300 mb-1">
                        {column.name}
                        <span className="ml-1 text-xs text-secondary-500">({column.type})</span>
                      </label>
                      <Input
                        type="text"
                        value={editData[column.name] || ''}
                        onChange={(e) => handleEditInputChange(column.name, e.target.value)}
                        placeholder={`Enter ${column.name}`}
                        className="w-full"
                      />
                    </div>
                  );
                })}
              </div>
              
              <div className="flex justify-end space-x-3 mt-6">
                <Button
                  variant="outline"
                  onClick={handleEditCancel}
                  disabled={updating}
                >
                  Cancel
                </Button>
                <Button
                  onClick={handleEditConfirm}
                  disabled={updating}
                  className="bg-primary-600 hover:bg-primary-700"
                >
                  {updating ? "Updating..." : "Update"}
                </Button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
});

export default TableData; 