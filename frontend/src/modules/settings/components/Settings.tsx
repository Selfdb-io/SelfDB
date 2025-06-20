import React, { useState, useEffect } from 'react';
import { useAuth } from '../../auth/context/AuthContext';
import { Avatar } from '../../../components/ui/avatar';
import { Button } from '../../../components/ui/button';
import { Notification } from '../../../components/ui/notification';
import PasswordChangeModal from './PasswordChangeModal';
import { Copy, Check } from 'lucide-react';
import { IoMdEye, IoMdEyeOff } from "react-icons/io";
import api from '../../../services/api';

const Profile: React.FC = () => {
  const { currentUser } = useAuth();
  const [isPasswordModalOpen, setIsPasswordModalOpen] = useState(false);
  const [anonKey, setAnonKey] = useState<string | null>(null);
  const [isFetchingKey, setIsFetchingKey] = useState(false);
  const [fetchKeyError, setFetchKeyError] = useState<string | null>(null);
  const [isCopied, setIsCopied] = useState(false);
  const [showAnonKey, setShowAnonKey] = useState(false);
  const [notification, setNotification] = useState({
    isOpen: false,
    type: 'success' as const,
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

  // Fetch Anon Key
  useEffect(() => {
    const fetchAnonKey = async () => {
      setIsFetchingKey(true);
      setFetchKeyError(null);
      try {
        const response = await api.get<{ anon_key: string | null }>('/users/me/anon-key');
        setAnonKey(response.data.anon_key);
      } catch (error: any) {
        console.error('Error fetching anon key:', error);
        setFetchKeyError(error.response?.data?.detail || 'Failed to fetch Anonymous Key.');
      } finally {
        setIsFetchingKey(false);
      }
    };

    fetchAnonKey();
  }, []);

  // Handle Copy
  const handleCopyKey = () => {
    if (!anonKey) return;
    navigator.clipboard.writeText(anonKey)
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
                {currentUser?.is_superuser ? (
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
        {(anonKey !== null || isFetchingKey || fetchKeyError) && (
          <div className="border-t border-secondary-200 dark:border-secondary-700 px-4 py-5 sm:p-6">
            <h3 className="text-lg font-medium text-secondary-900 dark:text-white mb-4">Anonymous Access Key</h3>

            {isFetchingKey && (
              <p className="text-sm text-secondary-500 dark:text-secondary-400">Loading key...</p>
            )}

            {fetchKeyError && (
              <p className="text-sm text-error-600 dark:text-error-400">Error: {fetchKeyError}</p>
            )}

            {anonKey && (
              <div className="space-y-3">
                 <p className="text-sm text-secondary-500 dark:text-secondary-400">
                  This is the global key used for anonymous access to public resources.
                  Keep it secure. <span className="font-semibold">Use with caution.</span>
                </p>
                <div className="flex items-center space-x-2 bg-secondary-100 dark:bg-secondary-700 p-3 rounded-md">
                  <span className="flex-grow text-sm font-mono text-secondary-700 dark:text-secondary-200 break-all">
                    {showAnonKey ? anonKey : '••••••••••••••••••••••••••••••••'}
                  </span>
                  <Button
                    variant="ghost"
                    size="icon"
                    onClick={() => setShowAnonKey(!showAnonKey)}
                    className="text-secondary-500 hover:text-secondary-700 dark:text-secondary-400 dark:hover:text-secondary-200"
                    aria-label={showAnonKey ? 'Hide key' : 'Show key'}
                  >
                    {showAnonKey ? <IoMdEyeOff className="h-5 w-5" /> : <IoMdEye className="h-5 w-5" />}
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
            {!anonKey && !isFetchingKey && !fetchKeyError && (
                 <p className="text-sm text-secondary-500 dark:text-secondary-400">
                    Anonymous Access Key is not configured or available.
                </p>
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

      {/* Notification */}
      <Notification
        isOpen={notification.isOpen}
        onClose={closeNotification}
        type={notification.type}
        title={notification.title}
        message={notification.message}
      />
    </div>
  );
};

export default Profile; 