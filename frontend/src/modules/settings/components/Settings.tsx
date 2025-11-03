import React, { useState, useEffect } from 'react';
import { useAuth } from '../../auth/context/AuthContext';
import { Avatar } from '../../../components/ui/avatar';
import { Button } from '../../../components/ui/button';
import { Notification, NotificationType } from '../../../components/ui/notification';
import PasswordChangeModal from './PasswordChangeModal';
import CorsOriginModal from './CorsOriginModal';
import { Copy, Check, Plus, Edit2, Trash2, RefreshCw, Globe } from 'lucide-react';
import { IoMdEye, IoMdEyeOff } from "react-icons/io";
import api from '../../../services/api';
import { corsService, CorsOrigin } from '../../../services/corsService';
import { ConfirmationDialog } from '../../../components/ui/confirmation-dialog';

const Profile: React.FC = () => {
  const { currentUser } = useAuth();
  const [isPasswordModalOpen, setIsPasswordModalOpen] = useState(false);
  const [isCorsModalOpen, setIsCorsModalOpen] = useState(false);
  const [editingCorsOrigin, setEditingCorsOrigin] = useState<CorsOrigin | undefined>(undefined);
  const [corsOrigins, setCorsOrigins] = useState<CorsOrigin[]>([]);
  const [isLoadingCors, setIsLoadingCors] = useState(false);
  const [corsError, setCorsError] = useState<string | null>(null);
  const [isDeleteDialogOpen, setIsDeleteDialogOpen] = useState(false);
  const [originToDelete, setOriginToDelete] = useState<CorsOrigin | null>(null);
  const [isDeleting, setIsDeleting] = useState(false);
  const [apiKey, setApiKey] = useState<string | null>(null);
  const [isFetchingKey, setIsFetchingKey] = useState(false);
  const [fetchKeyError, setFetchKeyError] = useState<string | null>(null);
  const [isCopied, setIsCopied] = useState(false);
  const [showApiKey, setShowApiKey] = useState(false);
  const [notification, setNotification] = useState({
    isOpen: false,
    type: 'success' as NotificationType,
    title: '',
    message: ''
  });
  
  // Get the first letter of the user's email for the avatar
  const userInitial = currentUser?.email ? currentUser.email[0].toUpperCase() : '';

  // Get username from email (first part before @ or .)
  const getUsernameFromEmail = (email: string): string => {
    if (!email) return '';
    
    // Get the part before @ or .
    const match = email.match(/^([^@.]+)/);
    return match ? match[1] : email;
  };
  
  const username = currentUser?.email ? getUsernameFromEmail(currentUser.email) : '';

  const handlePasswordChangeSuccess = () => {
    setNotification({
      isOpen: true,
      type: 'success',
      title: 'Password Updated',
      message: 'Your password has been successfully changed.'
    });
  };

  

  const closeNotification = () => {
    setNotification(prev => ({ ...prev, isOpen: false }));
  };

  // Load CORS origins
  const loadCorsOrigins = async () => {
    if (!currentUser?.is_active || currentUser?.role !== 'ADMIN') return;
    
    setIsLoadingCors(true);
    setCorsError(null);
    try {
      const response = await corsService.list(true);
      // Normalize response to an array to avoid runtime errors when response.origins is undefined
      setCorsOrigins(Array.isArray(response.origins) ? response.origins : []);
    } catch (error: any) {
      console.error('Error loading CORS origins:', error);
      setCorsError(error.response?.data?.detail || 'Failed to load CORS origins.');
    } finally {
      setIsLoadingCors(false);
    }
  };

  const handleCorsOriginSuccess = () => {
    setNotification({
      isOpen: true,
      type: 'success',
      title: 'CORS Origin Updated',
      message: 'CORS origin has been successfully saved.'
    });
    loadCorsOrigins(); // Reload the list
  };

  const openDeleteDialog = (origin: CorsOrigin) => {
    setOriginToDelete(origin);
    setIsDeleteDialogOpen(true);
  };

  const handleConfirmDelete = async () => {
    if (!originToDelete) return;
    setIsDeleting(true);
    try {
      await corsService.delete(originToDelete.id);
      setNotification({
        isOpen: true,
        type: 'success',
        title: 'CORS Origin Deleted',
        message: 'CORS origin has been successfully deleted.'
      });
      setIsDeleteDialogOpen(false);
      setOriginToDelete(null);
      await loadCorsOrigins(); // Reload the list
    } catch (error: any) {
      console.error('Error deleting CORS origin:', error);
      setNotification({
        isOpen: true,
        type: 'error',
        title: 'Delete Failed',
        message: error.response?.data?.detail || 'Failed to delete CORS origin.'
      });
    } finally {
      setIsDeleting(false);
    }
  };

  const handleCancelDelete = () => {
    setIsDeleteDialogOpen(false);
    setOriginToDelete(null);
  };

  const handleRefreshCorsCache = async () => {
    try {
      await corsService.refreshCache();
      setNotification({
        isOpen: true,
        type: 'success',
        title: 'Cache Refreshed',
        message: 'CORS origins cache has been refreshed successfully.'
      });
    } catch (error: any) {
      console.error('Error refreshing CORS cache:', error);
      setNotification({
        isOpen: true,
        type: 'error',
        title: 'Refresh Failed',
        message: error.response?.data?.detail || 'Failed to refresh CORS cache.'
      });
    }
  };

  const openCorsModal = (origin?: CorsOrigin) => {
    setEditingCorsOrigin(origin);
    setIsCorsModalOpen(true);
  };

  const closeCorsModal = () => {
    setIsCorsModalOpen(false);
    setEditingCorsOrigin(undefined);
  };

  // Fetch Anon Key
  useEffect(() => {
    const fetchApiKey = async () => {
      setIsFetchingKey(true);
      setFetchKeyError(null);
      try {
  const response = await api.get<{ api_key: string | null }>('/auth/me/api-key');
  // Normalize to null if undefined for consistent rendering logic
  setApiKey(response.data.api_key ?? null);
      } catch (error: any) {
        console.error('Error fetching api key:', error);
        setFetchKeyError(error.response?.data?.detail || 'Failed to fetch API Key.');
      } finally {
        setIsFetchingKey(false);
      }
    };

  fetchApiKey();
    
    // Load CORS origins if user is admin
    if (currentUser?.is_active && currentUser?.role === 'ADMIN') {
      loadCorsOrigins();
    }
  }, [currentUser]);

  // Handle Copy
  const handleCopyKey = () => {
    if (!apiKey) return;
    navigator.clipboard.writeText(apiKey)
      .then(() => {
        setIsCopied(true);
        setTimeout(() => setIsCopied(false), 2000); // Reset after 2 seconds
      })
      .catch(err => {
        console.error('Failed to copy anon key:', err);
        // Optionally show an error notification
      });
  };

  return (
    <div>
      
      <div className="bg-white dark:bg-secondary-800 shadow rounded-lg overflow-hidden">
        <div className="px-4 py-5 sm:px-6">
          <div className="flex items-center space-x-5">
            <Avatar 
              initial={userInitial} 
              size="lg" 
              colorScheme="primary" 
            />
            <div>
              <h3 className="text-lg font-medium text-secondary-900 dark:text-white">
                {currentUser?.email}
              </h3>
              <p className="text-sm text-secondary-500 dark:text-secondary-400">
                {username ? username : 'Administrator'}
              </p>
            </div>
          </div>
        </div>
        
        <div className="border-t border-secondary-200 dark:border-secondary-700 px-4 py-5 sm:p-6">
          <dl className="grid grid-cols-1 gap-x-4 gap-y-6 sm:grid-cols-2">
            <div>
              <dt className="text-sm font-medium text-secondary-500 dark:text-secondary-400">Email address</dt>
              <dd className="mt-1 text-sm text-secondary-900 dark:text-white">{currentUser?.email}</dd>
            </div>
            <div>
              <dt className="text-sm font-medium text-secondary-500 dark:text-secondary-400">Status</dt>
              <dd className="mt-1 text-sm text-secondary-900 dark:text-white">
                {currentUser?.is_active ? (
                  <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-success-100 text-success-800 dark:bg-success-900/30 dark:text-success-400">
                    Active
                  </span>
                ) : (
                  <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-error-100 text-error-800 dark:bg-error-900/30 dark:text-error-400">
                    Inactive
                  </span>
                )}
              </dd>
            </div>
            <div>
              <dt className="text-sm font-medium text-secondary-500 dark:text-secondary-400">Role</dt>
              <dd className="mt-1 text-sm text-secondary-900 dark:text-white">
                {currentUser?.is_active && currentUser?.role === 'ADMIN' ? (
                  <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-primary-100 text-primary-800 dark:bg-primary-900/30 dark:text-primary-400">
                    Administrator
                  </span>
                ) : (
                  <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-secondary-100 text-secondary-800 dark:bg-secondary-700 dark:text-secondary-300">
                    User
                  </span>
                )}
              </dd>
            </div>
            <div>
              <dt className="text-sm font-medium text-secondary-500 dark:text-secondary-400">Created on</dt>
              <dd className="mt-1 text-sm text-secondary-900 dark:text-white">
                {currentUser?.created_at ? new Date(currentUser.created_at).toLocaleDateString() : '-'}
              </dd>
            </div>
          </dl>
        </div>
        
        {/* Password Change Section */}
        <div className="border-t border-secondary-200 dark:border-secondary-700 px-4 py-5 sm:p-6">
          <div className="flex justify-between items-center mb-4">
            <h3 className="text-lg font-medium text-secondary-900 dark:text-white">Security Settings</h3>
            <Button 
              onClick={() => setIsPasswordModalOpen(true)}
              size="sm"
            >
              Change Password
            </Button>
            
          </div>
          <p className="text-sm text-secondary-500 dark:text-secondary-400">
            Update your password regularly to keep your account secure.
          </p>
        </div>

        {/* API Key Section - Renders only if key is fetched */}
  {(apiKey !== null || isFetchingKey || fetchKeyError) && (
          <div className="border-t border-secondary-200 dark:border-secondary-700 px-4 py-5 sm:p-6">
      <h3 className="text-lg font-medium text-secondary-900 dark:text-white mb-4">API Key</h3>

            {isFetchingKey && (
              <p className="text-sm text-secondary-500 dark:text-secondary-400">Loading key...</p>
            )}

            {fetchKeyError && (
              <p className="text-sm text-error-600 dark:text-error-400">Error: {fetchKeyError}</p>
            )}

            {apiKey && (
              <div className="space-y-3">
                 <p className="text-sm text-secondary-500 dark:text-secondary-400">
                  This is the global API key used for programmatic or anonymous access to public resources.
                  Keep it secure. <span className="font-semibold">Use with caution.</span>
                </p>
                <div className="flex items-center space-x-2 bg-secondary-100 dark:bg-secondary-700 p-3 rounded-md">
                  <span className="flex-grow text-sm font-mono text-secondary-700 dark:text-secondary-200 break-all">
                    {showApiKey ? apiKey : '••••••••••••••••••••••••••••••••'}
                  </span>
                  <Button
                    variant="ghost"
                    size="icon"
                    onClick={() => setShowApiKey(!showApiKey)}
                    className="text-secondary-500 hover:text-secondary-700 dark:text-secondary-400 dark:hover:text-secondary-200"
                    aria-label={showApiKey ? 'Hide key' : 'Show key'}
                  >
                    {showApiKey ? <IoMdEyeOff className="h-5 w-5" /> : <IoMdEye className="h-5 w-5" />}
                  </Button>
                  <Button
                    variant="ghost"
                    size="icon"
                    onClick={handleCopyKey}
                    className="text-secondary-500 hover:text-secondary-700 dark:text-secondary-400 dark:hover:text-secondary-200"
                    aria-label={isCopied ? 'Copied' : 'Copy key'}
                  >
                    {isCopied ? (
                      <Check className="h-5 w-5 text-success-500" />
                    ) : (
                      <Copy className="h-5 w-5" />
                    )}
                  </Button>
                </div>
              </div>
            )}
            {!apiKey && !isFetchingKey && !fetchKeyError && (
                 <p className="text-sm text-secondary-500 dark:text-secondary-400">
                   API Key is not configured or available.
                </p>
            )}
          </div>
        )}

        {/* CORS Management Section - Only visible to admins */}
        {currentUser?.is_active && currentUser?.role === 'ADMIN' && (
          <div className="border-t border-secondary-200 dark:border-secondary-700 px-4 py-5 sm:p-6">
            <div className="flex justify-between items-center mb-4">
              <div className="flex items-center space-x-2">
                <Globe className="h-5 w-5 text-secondary-500 dark:text-secondary-400" />
                <h3 className="text-lg font-medium text-secondary-900 dark:text-white">CORS Management</h3>
              </div>
              <div className="flex space-x-2">
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={handleRefreshCorsCache}
                  title="Refresh CORS cache"
                >
                  <RefreshCw className="h-4 w-4" />
                </Button>
                <Button 
                  onClick={() => openCorsModal()}
                  size="sm"
                >
                  <Plus className="h-4 w-4 mr-2" />
                  Add Origin
                </Button>
              </div>
            </div>

            <p className="text-sm text-secondary-500 dark:text-secondary-400 mb-4">
              Manage allowed CORS origins for cross-domain requests. Changes take effect immediately.
            </p>

            {isLoadingCors && (
              <p className="text-sm text-secondary-500 dark:text-secondary-400">Loading CORS origins...</p>
            )}

            {corsError && (
              <p className="text-sm text-error-600 dark:text-error-400 mb-4">Error: {corsError}</p>
            )}

            {!isLoadingCors && !corsError && (corsOrigins?.length ?? 0) === 0 && (
              <div className="text-center py-8 bg-secondary-50 dark:bg-secondary-700 rounded-lg">
                <Globe className="h-12 w-12 text-secondary-400 mx-auto mb-4" />
                <p className="text-sm text-secondary-500 dark:text-secondary-400">
                  No CORS origins configured. Add your first origin to allow cross-domain requests.
                </p>
              </div>
            )}

            {!isLoadingCors && (corsOrigins?.length ?? 0) > 0 && (
              <div className="space-y-3">
                {corsOrigins.map((origin) => (
                  <div
                    key={origin.id}
                    className="flex items-center justify-between p-3 bg-secondary-50 dark:bg-secondary-700 rounded-lg"
                  >
                    <div className="flex-grow">
                      <div className="font-mono text-sm text-secondary-900 dark:text-white">
                        {origin.origin}
                      </div>
                      {origin.description && (
                        <div className="text-xs text-secondary-500 dark:text-secondary-400 mt-1">
                          {origin.description}
                        </div>
                      )}
                      <div className="text-xs text-secondary-400 dark:text-secondary-500 mt-1">
                        Created: {new Date(origin.created_at).toLocaleDateString()}
                      </div>
                    </div>
                    <div className="flex items-center space-x-2 ml-4">
                      <span
                        className={`inline-flex items-center px-2 py-1 rounded-full text-xs font-medium ${
                          origin.is_active
                            ? 'bg-success-100 text-success-800 dark:bg-success-900/30 dark:text-success-400'
                            : 'bg-secondary-100 text-secondary-800 dark:bg-secondary-600 dark:text-secondary-300'
                        }`}
                      >
                        {origin.is_active ? 'Active' : 'Inactive'}
                      </span>
                      <Button
                        variant="ghost"
                        size="icon"
                        onClick={() => openCorsModal(origin)}
                        className="text-secondary-500 hover:text-secondary-700 dark:text-secondary-400 dark:hover:text-secondary-200"
                        title="Edit origin"
                      >
                        <Edit2 className="h-4 w-4" />
                      </Button>
                      <Button
                        variant="ghost"
                        size="icon"
                        onClick={() => openDeleteDialog(origin)}
                        className="text-error-500 hover:text-error-700 dark:text-error-400 dark:hover:text-error-200"
                        title="Delete origin"
                      >
                        <Trash2 className="h-4 w-4" />
                      </Button>
                    </div>
                  </div>
                ))}
              </div>
            )}
              </div>
        )}
      </div>

      {/* Password Change Modal */}
      <PasswordChangeModal
        isOpen={isPasswordModalOpen}
        onClose={() => setIsPasswordModalOpen(false)}
        onSuccess={handlePasswordChangeSuccess}
      />

      {/* CORS Origin Modal */}
      <CorsOriginModal
        isOpen={isCorsModalOpen}
        onClose={closeCorsModal}
        onSuccess={handleCorsOriginSuccess}
        origin={editingCorsOrigin}
      />

      {/* Notification */}
      <Notification
        isOpen={notification.isOpen}
        onClose={closeNotification}
        type={notification.type}
        title={notification.title}
        message={notification.message}
      />

      {/* Confirmation dialog for deletion */}
      <ConfirmationDialog
        isOpen={isDeleteDialogOpen}
        onClose={handleCancelDelete}
        onConfirm={handleConfirmDelete}
        title="Delete CORS Origin"
        description={originToDelete ? `Are you sure you want to permanently delete the CORS origin "${originToDelete.origin}"? This action cannot be undone.` : 'Are you sure you want to delete this CORS origin?'}
        confirmButtonText="Delete"
        cancelButtonText="Cancel"
        confirmButtonVariant="primary"
        confirmButtonClassName=""
        isConfirmLoading={isDeleting}
        isDestructive={true}
      />
    </div>
  );
};

export default Profile; 