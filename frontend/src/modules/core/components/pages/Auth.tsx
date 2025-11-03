import React, { useEffect, useState } from 'react';
import { getRegularUsersPaginated, createUser, deleteUser, UserCreate, User, updateUser } from '../../../../services/userService';
import { Button } from '../../../../components/ui/button';
import { Input } from '../../../../components/ui/input';
import { Modal } from '../../../../components/ui/modal';
import { ConfirmationDialog } from '../../../../components/ui/confirmation-dialog';
import { useTheme } from '../../context/ThemeContext';
import realtimeService from '../../../../services/realtimeService';
import { Table, TableHeader } from '../../../../components/ui/table';
import { Pagination } from '../../../../components/ui/pagination';
import { Trash2, PlusCircle, Edit2 } from 'lucide-react';
import { adminSetUserPassword } from '../../../../services/userService';

const Auth: React.FC = () => {
  const { theme } = useTheme();
  const [users, setUsers] = useState<User[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [addModalOpen, setAddModalOpen] = useState(false);
  const [addForm, setAddForm] = useState<UserCreate>({ email: '', password: '', first_name: '', last_name: '' });
  const [addLoading, setAddLoading] = useState(false);
  const [addError, setAddError] = useState<string | null>(null);
  const [deleteError, setDeleteError] = useState<string | null>(null);
  const [deleteConfirmation, setDeleteConfirmation] = useState<{ isOpen: boolean; user: User | null }>({
    isOpen: false,
    user: null
  });
  // Note: we no longer use a separate password modal. Password editing is incorporated
  // into the single Edit User modal (see editUserForm.password + editConfirmPassword).

  // Edit user modal (PUT /users/:id)
  // Single editable model for admin edits (includes optional password)
  type EditableUser = {
    email: string;
    first_name: string;
    last_name: string;
    role?: string | undefined;
    is_active?: boolean | undefined;
    password?: string | undefined; // optional - if provided we'll call adminSetUserPassword
  };

  const [editUserModal, setEditUserModal] = useState<{ isOpen: boolean; user: User | null }>({ isOpen: false, user: null });
  const [editUserForm, setEditUserForm] = useState<EditableUser>({ email: '', first_name: '', last_name: '', role: undefined, is_active: true, password: undefined });
  const [editConfirmPassword, setEditConfirmPassword] = useState<string>('');
  const [editChangePassword, setEditChangePassword] = useState<boolean>(false);
  const [editUserLoading, setEditUserLoading] = useState(false);
  const [editUserError, setEditUserError] = useState<string | null>(null);

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
      if (!addForm.email || !addForm.password || !addForm.first_name || !addForm.last_name) {
        setAddError('Email, password, first name, and last name are required');
        setAddLoading(false);
        return;
      }
      await createUser(addForm);
      // Immediately fetch updated data for page 1
      setCurrentPage(1);
      const result = await getRegularUsersPaginated(1, pageSize);
      setUsers(result.data);
      setTotalUsers(result.total);
      setTotalPages(result.totalPages);
      setAddModalOpen(false);
      setAddForm({ email: '', password: '', first_name: '', last_name: '' });
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
      // Immediately fetch updated data for current page
      const result = await getRegularUsersPaginated(currentPage, pageSize);
      setUsers(result.data);
      setTotalUsers(result.total);
      setTotalPages(result.totalPages);
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
    { key: 'first_name', label: 'First Name' },
    { key: 'last_name', label: 'Last Name' },
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
      first_name: user.first_name || '-',
      last_name: user.last_name || '-',
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

  

  const renderRowActions = (item: any) => (
    <div className="flex space-x-2">
      <Button
        variant="ghost"
        size="sm"
        onClick={() => {
          const user = users.find(u => u.id === item.id) || null;
          setEditUserModal({ isOpen: true, user });
          setEditUserForm({ email: user?.email || '', first_name: user?.first_name || '', last_name: user?.last_name || '', role: user?.role, is_active: user?.is_active, password: undefined });
          setEditConfirmPassword('');
          setEditChangePassword(false);
          setEditUserError(null);
        }}
      >
        <Edit2 className="w-4 h-4" />
      </Button>
      {/* (reset password removed) */}
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
    </div>
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
        renderActions={renderRowActions}
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
            <div className="mt-2 text-xs text-secondary-600 dark:text-secondary-400 space-y-1">
              <p className="font-medium">Password must contain:</p>
              <ul className="list-disc list-inside space-y-0.5 pl-2">
                <li className={addForm.password.length >= 8 ? 'text-success-600 dark:text-success-400' : ''}>
                  At least 8 characters
                </li>
                <li className={/[A-Z]/.test(addForm.password) ? 'text-success-600 dark:text-success-400' : ''}>
                  At least one uppercase letter (A-Z)
                </li>
                <li className={/[a-z]/.test(addForm.password) ? 'text-success-600 dark:text-success-400' : ''}>
                  At least one lowercase letter (a-z)
                </li>
                <li className={/[0-9]/.test(addForm.password) ? 'text-success-600 dark:text-success-400' : ''}>
                  At least one number (0-9)
                </li>
                <li className={/[!@#$%^&*()_+\-=\[\]{};':"\\|,.<>\/?]/.test(addForm.password) ? 'text-success-600 dark:text-success-400' : ''}>
                  At least one special character (!@#$%^&*, etc.)
                </li>
              </ul>
            </div>
          </div>
          <div>
            <label htmlFor="first_name" className="block text-sm font-medium text-secondary-700 dark:text-secondary-300 mb-1">First Name</label>
            <Input
              id="first_name"
              type="text"
              value={addForm.first_name}
              onChange={e => {
                const value = e.target.value;
                // Auto-capitalize first letter
                const capitalized = value.charAt(0).toUpperCase() + value.slice(1);
                setAddForm({ ...addForm, first_name: capitalized });
              }}
              className="w-full"
              disabled={addLoading}
            />
          </div>
          <div>
            <label htmlFor="last_name" className="block text-sm font-medium text-secondary-700 dark:text-secondary-300 mb-1">Last Name</label>
            <Input
              id="last_name"
              type="text"
              value={addForm.last_name}
              onChange={e => {
                const value = e.target.value;
                // Auto-capitalize first letter
                const capitalized = value.charAt(0).toUpperCase() + value.slice(1);
                setAddForm({ ...addForm, last_name: capitalized });
              }}
              className="w-full"
              disabled={addLoading}
            />
          </div>
          <div className="flex justify-end space-x-2 pt-2">
            <Button type="button" variant="outline" onClick={() => setAddModalOpen(false)} disabled={addLoading}>Cancel</Button>
            <Button type="submit" className="bg-primary-600 text-white hover:bg-primary-700" isLoading={addLoading}>Add User</Button>
          </div>
        </form>
      </Modal>

      {/* Edit User Modal */}
  <Modal isOpen={editUserModal.isOpen} onClose={() => { setEditUserModal({ isOpen: false, user: null }); setEditUserForm({ email: '', first_name: '', last_name: '', role: undefined, is_active: true, password: undefined }); setEditConfirmPassword(''); setEditChangePassword(false); setEditUserError(null); }} title={editUserModal.user ? `Edit user ${editUserModal.user.email}` : 'Edit user'}>
    <form className="flex flex-col h-[70vh]" onSubmit={async (e) => {
            e.preventDefault();
            if (!editUserModal.user) return;
            setEditUserError(null);
            setEditUserLoading(true);

            try {
              // If admin opted to change the password, validate it client-side before sending
              const pwd = editChangePassword ? (editUserForm.password ?? '') : '';
              if (editChangePassword && pwd && pwd.length > 0) {
                // Confirm match
                if (pwd !== editConfirmPassword) {
                  setEditUserError('New passwords do not match');
                  setEditUserLoading(false);
                  return;
                }
                // Strength checks
                if (pwd.length < 8) { setEditUserError('Password must be at least 8 characters'); setEditUserLoading(false); return; }
                if (!/[A-Z]/.test(pwd)) { setEditUserError('Password must contain at least one uppercase letter'); setEditUserLoading(false); return; }
                if (!/[a-z]/.test(pwd)) { setEditUserError('Password must contain at least one lowercase letter'); setEditUserLoading(false); return; }
                if (!/[0-9]/.test(pwd)) { setEditUserError('Password must contain at least one number'); setEditUserLoading(false); return; }
                if (!/[!@#$%^&*(),.?":{}|<>]/.test(pwd)) { setEditUserError('Password must contain at least one special character'); setEditUserLoading(false); return; }
              }

              const payload: any = { email: editUserForm.email, first_name: editUserForm.first_name, last_name: editUserForm.last_name, is_active: editUserForm.is_active };
              if (editUserForm.role) payload.role = editUserForm.role;

              // Update non-password fields first
              await updateUser(editUserModal.user.id, payload);

              // If password provided (and change toggled), call adminSetUserPassword separately
              if (editChangePassword && pwd && pwd.length > 0) {
                await adminSetUserPassword(editUserModal.user.id, pwd);
              }

              const result = await getRegularUsersPaginated(currentPage, pageSize);
              setUsers(result.data);
              setTotalUsers(result.total);
              setTotalPages(result.totalPages);
              setEditUserModal({ isOpen: false, user: null });
              setEditUserForm({ email: '', first_name: '', last_name: '', role: undefined, is_active: true, password: undefined });
              setEditConfirmPassword('');
            } catch (err: any) {
              setEditUserError(err?.response?.data?.detail || err?.message || 'Failed to update user');
            } finally {
              setEditUserLoading(false);
            }
          }}>
          <div className="overflow-y-auto pr-2 space-y-4">
            {editUserError && <div className="text-error-600 dark:text-error-400 bg-error-50 dark:bg-error-900/30 p-2 rounded text-sm">{editUserError}</div>}
            <div>
              <label htmlFor="edit_email" className="block text-sm font-medium text-secondary-700 dark:text-secondary-300 mb-1">Email</label>
              <Input id="edit_email" type="email" value={editUserForm.email} onChange={e => setEditUserForm({ ...editUserForm, email: e.target.value })} />
            </div>
            <div>
              <label htmlFor="edit_first_name" className="block text-sm font-medium text-secondary-700 dark:text-secondary-300 mb-1">First Name</label>
              <Input id="edit_first_name" type="text" value={editUserForm.first_name} onChange={e => setEditUserForm({ ...editUserForm, first_name: e.target.value })} />
            </div>
            <div>
              <label htmlFor="edit_last_name" className="block text-sm font-medium text-secondary-700 dark:text-secondary-300 mb-1">Last Name</label>
              <Input id="edit_last_name" type="text" value={editUserForm.last_name} onChange={e => setEditUserForm({ ...editUserForm, last_name: e.target.value })} />
            </div>
            <div>
              <label htmlFor="edit_role" className="block text-sm font-medium text-secondary-700 dark:text-secondary-300 mb-1">Role</label>
              <Input id="edit_role" type="text" value={editUserForm.role || ''} onChange={e => setEditUserForm({ ...editUserForm, role: e.target.value })} />
              <p className="text-xs text-secondary-600 dark:text-secondary-400 mt-1">Use role names like <span className="font-mono">ADMIN</span> or <span className="font-mono">USER</span></p>
            </div>
            <div className="flex items-center space-x-2">
              <input id="edit_is_active" type="checkbox" checked={!!editUserForm.is_active} onChange={e => setEditUserForm({ ...editUserForm, is_active: e.target.checked })} />
              <label htmlFor="edit_is_active" className="text-sm text-secondary-700 dark:text-secondary-300">Active</label>
            </div>
            <div>
              <label className="flex items-center space-x-2 text-sm font-medium text-secondary-700 dark:text-secondary-300 mb-1">
                <input id="edit_change_password" type="checkbox" checked={editChangePassword} onChange={e => {
                  const checked = e.target.checked;
                  setEditChangePassword(checked);
                  if (!checked) {
                    // clear password fields when toggled off
                    setEditUserForm({ ...editUserForm, password: undefined });
                    setEditConfirmPassword('');
                  } else {
                    // initialize empty strings to show inputs
                    setEditUserForm({ ...editUserForm, password: '' });
                    setEditConfirmPassword('');
                  }
                }} />
                <span>Change user password</span>
              </label>
              <p className="text-xs text-secondary-500 dark:text-secondary-400 mb-3">As an admin, you can set a new password for this user. The user can change it later if needed.</p>

              {editChangePassword && (
                <div className="border border-secondary-200 dark:border-secondary-700 rounded-lg p-4 bg-secondary-50 dark:bg-secondary-800/50">
                  <div className="space-y-4">
                    <div>
                      <label htmlFor="edit_password" className="block text-sm font-medium text-secondary-700 dark:text-secondary-300 mb-2">
                        New Password
                      </label>
                      <Input
                        id="edit_password"
                        type="password"
                        value={editUserForm.password || ''}
                        onChange={e => setEditUserForm({ ...editUserForm, password: e.target.value })}
                        placeholder="Enter new password"
                        className="w-full"
                      />
                    </div>

                    <div>
                      <label htmlFor="edit_confirm_password" className="block text-sm font-medium text-secondary-700 dark:text-secondary-300 mb-2">
                        Confirm New Password
                        {editConfirmPassword && (
                          <span className={`ml-2 text-xs ${editUserForm.password === editConfirmPassword ? 'text-success-600 dark:text-success-400' : 'text-error-600 dark:text-error-400'}`}>
                            {editUserForm.password === editConfirmPassword ? '✓ Passwords match' : '✗ Passwords do not match'}
                          </span>
                        )}
                      </label>
                      <Input
                        id="edit_confirm_password"
                        type="password"
                        value={editConfirmPassword}
                        onChange={e => setEditConfirmPassword(e.target.value)}
                        placeholder="Confirm new password"
                        className={`w-full ${editConfirmPassword && editUserForm.password !== editConfirmPassword ? 'border-error-300 dark:border-error-600 focus:border-error-500' : ''}`}
                      />
                    </div>

                    {/* Password Requirements */}
                    {editUserForm.password !== undefined && editUserForm.password !== '' && (
                      <div className="bg-white dark:bg-secondary-900 border border-secondary-200 dark:border-secondary-600 rounded-md p-3">
                        <p className="text-sm font-medium text-secondary-700 dark:text-secondary-300 mb-2">Password Requirements:</p>
                        <div className="grid grid-cols-1 gap-1 text-xs">
                          <div className={`flex items-center space-x-2 ${editUserForm.password.length >= 8 ? 'text-success-600 dark:text-success-400' : 'text-secondary-500 dark:text-secondary-400'}`}>
                            <span>{editUserForm.password.length >= 8 ? '✓' : '○'}</span>
                            <span>At least 8 characters</span>
                          </div>
                          <div className={`flex items-center space-x-2 ${/[A-Z]/.test(editUserForm.password) ? 'text-success-600 dark:text-success-400' : 'text-secondary-500 dark:text-secondary-400'}`}>
                            <span>{/[A-Z]/.test(editUserForm.password) ? '✓' : '○'}</span>
                            <span>One uppercase letter (A-Z)</span>
                          </div>
                          <div className={`flex items-center space-x-2 ${/[a-z]/.test(editUserForm.password) ? 'text-success-600 dark:text-success-400' : 'text-secondary-500 dark:text-secondary-400'}`}>
                            <span>{/[a-z]/.test(editUserForm.password) ? '✓' : '○'}</span>
                            <span>One lowercase letter (a-z)</span>
                          </div>
                          <div className={`flex items-center space-x-2 ${/[0-9]/.test(editUserForm.password) ? 'text-success-600 dark:text-success-400' : 'text-secondary-500 dark:text-secondary-400'}`}>
                            <span>{/[0-9]/.test(editUserForm.password) ? '✓' : '○'}</span>
                            <span>One number (0-9)</span>
                          </div>
                          <div className={`flex items-center space-x-2 ${/[!@#$%^&*(),.?\":{}|<>]/.test(editUserForm.password) ? 'text-success-600 dark:text-success-400' : 'text-secondary-500 dark:text-secondary-400'}`}>
                            <span>{/[!@#$%^&*(),.?\":{}|<>]/.test(editUserForm.password) ? '✓' : '○'}</span>
                            <span>One special character (!@#$%^&*, etc.)</span>
                          </div>
                        </div>
                      </div>
                    )}

                    <div className="text-xs text-secondary-600 dark:text-secondary-400 bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-md p-2">
                      <strong>Admin Action:</strong> This will immediately set the user's password. The user will be required to change their password on next login if your security policy requires it.
                    </div>
                  </div>
                </div>
              )}
            </div>
          </div>
          <div className="mt-2 sticky bottom-0 bg-transparent pt-2 bg-gradient-to-t from-transparent to-transparent">
            <div className="flex justify-end space-x-2 py-2 bg-panel/0">
              <Button type="button" variant="outline" onClick={() => { setEditUserModal({ isOpen: false, user: null }); setEditUserForm({ email: '', first_name: '', last_name: '', role: undefined, is_active: true, password: undefined }); setEditConfirmPassword(''); setEditUserError(null); }} disabled={editUserLoading}>Cancel</Button>
              <Button type="submit" className="bg-primary-600 text-white hover:bg-primary-700" isLoading={editUserLoading} disabled={editChangePassword && editUserForm.password !== undefined && editUserForm.password !== '' && editUserForm.password !== editConfirmPassword}>Save</Button>
            </div>
          </div>
        </form>
      </Modal>

      {/* Password editing has been integrated into the Edit User modal above. */}

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