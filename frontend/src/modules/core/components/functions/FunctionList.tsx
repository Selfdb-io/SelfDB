import React, { useState } from 'react';
import { MoreVertical, DatabaseZap } from 'lucide-react';
import { Function, deleteFunction } from '../../../../services/functionService';
import { ConfirmationDialog } from '../../../../components/ui/confirmation-dialog';
import { formatDistanceToNow } from 'date-fns';
import { Table, TableHeader } from '../../../../components/ui/table';

interface FunctionListProps {
  functions: Function[];
  onFunctionClick: (functionId: string) => void;
  onEditFunction: (func: Function) => void;
  onFunctionDeleted: (functionId: string) => void;
  loading: boolean;
  error: string | null;
}

interface FormattedFunction extends Function {
  lastUpdated: string;
  statusLabel: React.ReactNode;
}

const FunctionList: React.FC<FunctionListProps> = ({
  functions,
  onFunctionClick,
  onEditFunction,
  onFunctionDeleted,
  loading,
  error
}) => {
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
  const [functionToDelete, setFunctionToDelete] = useState<string | null>(null);
  const [isDeleting, setIsDeleting] = useState(false);
  const [deleteError, setDeleteError] = useState<string | null>(null);

  // Convert is_active to status for each function if needed
  const processedFunctions = functions.map(func => {
    const processedFunc = { ...func };
    // If status is undefined but is_active is defined, derive status from is_active
    if (processedFunc.status === undefined && processedFunc.is_active !== undefined) {
      processedFunc.status = processedFunc.is_active ? 'active' : 'draft';
    }
    return processedFunc;
  });

  if (loading) {
    return (
      <div className="flex justify-center items-center p-12">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary-600"></div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="p-6 bg-error-50 dark:bg-error-900/20 border border-error-200 dark:border-error-800 rounded-lg text-error-700 dark:text-error-300">
        <h3 className="text-lg font-heading font-semibold mb-2">Error Loading Functions</h3>
        <p>{error}</p>
      </div>
    );
  }

  if (processedFunctions.length === 0 && !loading) {
    return (
      <div className="text-secondary-500 dark:text-secondary-400 py-8 text-center text-base">
        No functions found. Create your first function to get started.
      </div>
    );
  }

  const handleDeleteConfirm = async () => {
    if (!functionToDelete) return;
    
    try {
      setIsDeleting(true);
      setDeleteError(null);
      await deleteFunction(functionToDelete);
      onFunctionDeleted(functionToDelete);
      setDeleteDialogOpen(false);
    } catch (err: any) {
      console.error('Error deleting function:', err);
      setDeleteError(err.response?.data?.detail || err.message || 'Failed to delete function');
    } finally {
      setIsDeleting(false);
      setFunctionToDelete(null);
    }
  };

  const handleDeleteCancel = () => {
    setDeleteDialogOpen(false);
    setFunctionToDelete(null);
    setDeleteError(null);
  };

  const tableHeaders: TableHeader[] = [
    { key: 'name', label: 'Name' },
    { key: 'statusLabel', label: 'Status' },
    { key: 'lastUpdated', label: 'Last Updated' },
  ];

  const formattedData: FormattedFunction[] = processedFunctions.map(func => ({
    ...func,
    lastUpdated: formatDistanceToNow(new Date(func.updated_at), { addSuffix: true }),
    statusLabel: (
      <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium
        ${func.status === 'active' 
          ? 'bg-success-100 dark:bg-success-900/20 text-success-800 dark:text-success-300' 
          : 'bg-warning-100 dark:bg-warning-900/20 text-warning-800 dark:text-warning-300'}`}
      >
        {func.status === 'active' ? 'On' : 'Off'}
      </span>
    ),
  }));

  const renderRowIcon = () => <DatabaseZap className="h-5 w-5 text-primary-600" />;

  const renderActions = (item: FormattedFunction) => (
    <button
      onClick={(e) => {
        e.stopPropagation();
        onEditFunction(item);
      }}
      className="text-secondary-600 hover:text-secondary-700 dark:text-secondary-400 dark:hover:text-secondary-300 p-1 rounded hover:bg-secondary-100 dark:hover:bg-secondary-700"
      aria-label="Edit function"
    >
      <MoreVertical className="h-5 w-5" />
    </button>
  );

  const handleRowClick = (item: FormattedFunction) => {
    onFunctionClick(item.id);
  };

  return (
    <>
      <Table<FormattedFunction>
        headers={tableHeaders}
        data={formattedData}
        renderActions={renderActions}
        onRowClick={handleRowClick}
        renderRowIcon={renderRowIcon}
      />

      <ConfirmationDialog
        isOpen={deleteDialogOpen}
        onClose={handleDeleteCancel}
        onConfirm={handleDeleteConfirm}
        title="Delete Function"
        description={
          <>
            Are you sure you want to delete this function? This action cannot be undone.
            {deleteError && (
              <div className="mt-2 text-error-600 dark:text-error-400 text-sm">
                {deleteError}
              </div>
            )}
          </>
        }
        confirmButtonText="Delete"
        isConfirmLoading={isDeleting}
        isDestructive={true}
      />
    </>
  );
};

export default FunctionList; 