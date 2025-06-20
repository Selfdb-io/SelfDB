import React, { useEffect, useState } from 'react';
import { getRegularUsersPaginated, createUser, deleteUser, UserCreate } from '../../../../services/userService';
import { Button } from '../../../../components/ui/button';
import { Input } from '../../../../components/ui/input';
import { Modal } from '../../../../components/ui/modal';
import { ConfirmationDialog } from '../../../../components/ui/confirmation-dialog';
import { useTheme } from '../../context/ThemeContext';
import realtimeService from '../../../../services/realtimeService';
import { Table, TableHeader } from '../../../../components/ui/table';
import { Pagination } from '../../../../components/ui/pagination';
import { Trash2, PlusCircle } from 'lucide-react';

interface User {
  id: string;
  email: string;
  is_active: boolean;
  is_superuser: boolean;
  created_at: string;
  isDeleting?: boolean;
}

const Auth: React.FC = () => {
  const { theme } = useTheme();
  const [users, setUsers] = useState<User[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [addModalOpen, setAddModalOpen] = useState(false);
  const [addForm, setAddForm] = useState<UserCreate>({ email: '', password: '', is_active: true, is_superuser: false });
  const [addLoading, setAddLoading] = useState(false);
  const [addError, setAddError] = useState<string | null>(null);
  const [deleteError, setDeleteError] = useState<string | null>(null);
  const [deleteConfirmation, setDeleteConfirmation] = useState<{ isOpen: boolean; user: User | null }>({
    isOpen: false,
    user: null
  });

  // Add pagination state
  const [currentPage, setCurrentPage] = useState(1);
  const [pageSize] = useState(100);
  const [totalUsers, setTotalUsers] = useState(0);
  const [totalPages, setTotalPages] = useState(0);

  useEffect(() => {
    const fetchUsers = async () => {
      setLoading(true);
      setError(null);
      try {
        const result = await getRegularUsersPaginated(currentPage, pageSize);
        setUsers(result.data);
        setTotalUsers(result.total);
        setTotalPages(result.totalPages);
      } catch (err: any) {
        setError(err?.message || 'Failed to load users');
      } finally {
        setLoading(false);
      }
    };

    fetchUsers();

    // Real-time updates
    const handleUserUpdate = (data: any) => {
      console.log('Received user update via WebSocket:', data);
      // When users change, refresh the current page
      fetchUsers();
    };

    const subscriptionId = 'users';
    realtimeService.subscribe(subscriptionId);
    const removeListener = realtimeService.addListener(subscriptionId, handleUserUpdate);

    // Cleanup on component unmount
    return () => {
      removeListener();
      realtimeService.unsubscribe(subscriptionId);
    };

  }, [currentPage, pageSize]); // Add pagination dependencies

  const handleAddUser = async (e: React.FormEvent) => {
    e.preventDefault();
    setAddLoading(true);
    setAddError(null);
    try {
      if (!addForm.email || !addForm.password) {
        setAddError('Email and password are required');
        setAddLoading(false);
        return;
      }
      await createUser(addForm);
      // Reset to first page to see the new user
      setCurrentPage(1);
      setAddModalOpen(false);
      setAddForm({ email: '', password: '', is_active: true, is_superuser: false });
    } catch (err: any) {
      setAddError(err?.response?.data?.detail || err?.message || 'Failed to add user');
    } finally {
      setAddLoading(false);
    }
  };

  const handleDeleteConfirm = async () => {
    if (!deleteConfirmation.user) return;
    
    const userId = deleteConfirmation.user.id;
    
    // Mark the user as deleting instead of using a separate deleteLoadingId
    setUsers(users.map(user => 
      user.id === userId ? { ...user, isDeleting: true } : user
    ));
    
    setDeleteError(null);
    setDeleteConfirmation({ isOpen: false, user: null });
    
    try {
      await deleteUser(userId);
      // Refresh current page after successful deletion
      const fetchUsers = async () => {
        try {
          const result = await getRegularUsersPaginated(currentPage, pageSize);
          setUsers(result.data);
          setTotalUsers(result.total);
          setTotalPages(result.totalPages);
        } catch (err: any) {
          setError(err?.message || 'Failed to load users');
        }
      };
      setTimeout(fetchUsers, 300);
    } catch (err: any) {
      setDeleteError(err?.response?.data?.detail || err?.message || 'Failed to delete user');
      // Reset the deleting state if there was an error
      setUsers(users.map(user => 
        user.id === userId ? { ...user, isDeleting: false } : user
      ));
    }
  };



  // Define table headers for the Table component with row numbering
  const tableHeaders: TableHeader[] = [
    { key: 'rowNumber', label: '#', isNumeric: true },
    { key: 'email', label: 'Email' },
    { key: 'status', label: 'Status' },
    { key: 'created', label: 'Created' }
  ];

  // Prepare data for the Table component with formatting and row numbers
  const tableData = users.map((user, index) => {
    // Calculate row number accounting for pagination
    const rowNumber = (currentPage - 1) * pageSize + index + 1;
    
    return {
      id: user.id,
      rowNumber: (
        <span className="font-mono text-secondary-600 dark:text-secondary-400">
          {rowNumber}
        </span>
      ),
      email: user.email,
      status: user.is_active ? (
        <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-success-100 dark:bg-success-900 text-success-800 dark:text-success-100">Active</span>
      ) : (
        <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-error-100 dark:bg-error-900 text-error-800 dark:text-error-100">Inactive</span>
      ),
      created: new Date(user.created_at).toLocaleDateString(),
      isDeleting: user.isDeleting
    };
  });

  // Render delete button for actions column
  const renderActions = (item: any) => (
    <Button
      variant="outline"
      size="sm"
      className="text-error-600 dark:text-error-400 border-error-300 dark:border-error-500 hover:bg-error-50 dark:hover:bg-error-900/30 flex items-center"
      onClick={() => setDeleteConfirmation({ isOpen: true, user: users.find(u => u.id === item.id) || null })}
      disabled={item.isDeleting}
    >
      {item.isDeleting ? (
        <span className="px-1">...</span>
      ) : (
        <Trash2 className="w-4 h-4" />
      )}
    </Button>
  );

  return (
    <div className="p-2">
      <div className="flex justify-end mb-4">
        <Button onClick={() => setAddModalOpen(true)} className="bg-primary-600 text-white hover:bg-primary-700">Add User
          <PlusCircle className="ml-2 h-5 w-5" />
        </Button>
      </div>
      
      <Table
        headers={tableHeaders}
        data={tableData}
        isLoading={loading}
        errorMessage={error}
        renderActions={renderActions}
      />

      {/* Pagination Controls */}
      <Pagination
        currentPage={currentPage}
        totalPages={totalPages}
        totalItems={totalUsers}
        pageSize={pageSize}
        onPageChange={setCurrentPage}
        itemName="users"
      />

      {deleteError && (
        <div className="text-error-600 dark:text-error-400 bg-error-50 dark:bg-error-900/30 p-2 rounded mt-2 text-sm">{deleteError}</div>
      )}
      
      {/* Add User Modal */}
      <Modal isOpen={addModalOpen} onClose={() => setAddModalOpen(false)} title="Add User">
        <form onSubmit={handleAddUser} className="space-y-4">
          {addError && <div className="text-error-600 dark:text-error-400 bg-error-50 dark:bg-error-900/30 p-2 rounded text-sm">{addError}</div>}
          <div>
            <label htmlFor="email" className="block text-sm font-medium text-secondary-700 dark:text-secondary-300 mb-1">Email</label>
            <Input
              id="email"
              type="email"
              value={addForm.email}
              onChange={e => setAddForm({ ...addForm, email: e.target.value })}
              required
              className="w-full"
              disabled={addLoading}
            />
          </div>
          <div>
            <label htmlFor="password" className="block text-sm font-medium text-secondary-700 dark:text-secondary-300 mb-1">Password</label>
            <Input
              id="password"
              type="password"
              value={addForm.password}
              onChange={e => setAddForm({ ...addForm, password: e.target.value })}
              required
              className="w-full"
              disabled={addLoading}
            />
          </div>
          <div className="flex items-center space-x-2">
            <input
              id="is_active"
              type="checkbox"
              checked={addForm.is_active}
              onChange={e => setAddForm({ ...addForm, is_active: e.target.checked })}
              disabled={addLoading}
              className="form-checkbox h-4 w-4 text-primary-600 dark:text-primary-500 border-secondary-300 dark:border-secondary-600 rounded"
            />
            <label htmlFor="is_active" className="text-sm text-secondary-700 dark:text-secondary-300">Active</label>
          </div>
          <div className="flex justify-end space-x-2 pt-2">
            <Button type="button" variant="outline" onClick={() => setAddModalOpen(false)} disabled={addLoading}>Cancel</Button>
            <Button type="submit" className="bg-primary-600 text-white hover:bg-primary-700" isLoading={addLoading}>Add User</Button>
          </div>
        </form>
      </Modal>

      {/* Replace Delete Confirmation Modal with ConfirmationDialog component */}
      <ConfirmationDialog
        isOpen={deleteConfirmation.isOpen}
        onClose={() => setDeleteConfirmation({ isOpen: false, user: null })}
        onConfirm={handleDeleteConfirm}
        title="Confirm Delete User"
        description={
          <p>
            Are you sure you want to delete the user <span className={`font-medium ${theme === 'dark' ? 'text-white' : 'text-secondary-900'}`}>{deleteConfirmation.user?.email}</span>?
            This action cannot be undone.
          </p>
        }
        confirmButtonText="Delete User"
        cancelButtonText="Cancel"
        isDestructive={true}
      />
    </div>
  );
};

export default Auth; 