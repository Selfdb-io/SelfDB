import React, { useState } from 'react';
import { Modal } from '../../../components/ui/modal';
import { Button } from '../../../components/ui/button';
import { Input } from '../../../components/ui/input';
import { changePassword } from '../../../services/userService';

interface PasswordChangeModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSuccess: () => void;
}

const PasswordChangeModal: React.FC<PasswordChangeModalProps> = ({
  isOpen,
  onClose,
  onSuccess
}) => {
  const [currentPassword, setCurrentPassword] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [error, setError] = useState('');
  const [isLoading, setIsLoading] = useState(false);

  // Live validation flags
  const lengthOk = newPassword.length >= 8;
  const upperOk = /[A-Z]/.test(newPassword);
  const lowerOk = /[a-z]/.test(newPassword);
  const digitOk = /\d/.test(newPassword);
  const specialOk = /[!@#$%^&*(),.?":{}|<>]/.test(newPassword);
  const matchOk = newPassword === confirmPassword && newPassword.length > 0;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    
    // Validation
    if (!currentPassword || !newPassword || !confirmPassword) {
      setError('All fields are required');
      return;
    }
    
    if (newPassword !== confirmPassword) {
      setError('New passwords do not match');
      return;
    }
    
    if (newPassword.length < 8) {
      setError('Password must be at least 8 characters');
      return;
    }
    // Match backend strength requirements: uppercase, lowercase, digit, special char
    if (!/[A-Z]/.test(newPassword)) {
      setError('Password must contain at least one uppercase letter');
      return;
    }
    if (!/[a-z]/.test(newPassword)) {
      setError('Password must contain at least one lowercase letter');
      return;
    }
    if (!/\d/.test(newPassword)) {
      setError('Password must contain at least one digit');
      return;
    }
    if (!/[!@#$%^&*(),.?":{}|<>]/.test(newPassword)) {
      setError('Password must contain at least one special character');
      return;
    }
    
    try {
      setIsLoading(true);
      await changePassword({
        current_password: currentPassword,
        new_password: newPassword
      });
      
      // Reset form
      setCurrentPassword('');
      setNewPassword('');
      setConfirmPassword('');
      
      // Close modal and notify success
      onClose();
      onSuccess();
    } catch (err: any) {
      // Try to surface backend validation errors (FastAPI Pydantic errors are in response.data.detail)
      const resp = err?.response?.data;
      if (resp) {
        // detail can be an array of errors or a string
        if (Array.isArray(resp.detail)) {
          // Map to readable message
          const first = resp.detail[0];
          if (first && first.msg) {
            setError(first.msg);
          } else {
            setError(JSON.stringify(resp.detail));
          }
        } else if (typeof resp.detail === 'string') {
          setError(resp.detail);
        } else if (resp.message) {
          setError(resp.message);
        } else {
          setError('Failed to change password. Please check your current password and try again.');
        }
      } else {
        setError('Failed to change password. Please check your current password and try again.');
      }
    } finally {
      setIsLoading(false);
    }
  };

  const handleClose = () => {
    // Reset form when closing
    setCurrentPassword('');
    setNewPassword('');
    setConfirmPassword('');
    setError('');
    onClose();
  };

  return (
    <Modal isOpen={isOpen} onClose={handleClose} title="Change Password">
      {error && (
        <div className="mb-4 p-3 bg-error-50 text-error-800 rounded-md">
          {error}
        </div>
      )}
      
      <form onSubmit={handleSubmit}>
        <div className="mb-4">
          <label htmlFor="currentPassword" className="block text-sm font-medium text-secondary-700 mb-1">
            Current Password
          </label>
          <Input
            id="currentPassword"
            type="password"
            value={currentPassword}
            onChange={(e) => setCurrentPassword(e.target.value)}
          />
        </div>
        
        <div className="mb-4">
          <label htmlFor="newPassword" className="block text-sm font-medium text-secondary-700 mb-1">
            New Password
          </label>
          <Input
            id="newPassword"
            type="password"
            value={newPassword}
            onChange={(e) => setNewPassword(e.target.value)}
          />
        </div>
        {/* Live password requirements checklist */}
        <div className="mb-4 text-sm text-secondary-600 dark:text-secondary-400">
          <p className="font-medium mb-2">Password must contain:</p>
          <ul className="list-none space-y-1 pl-0">
            <li className={`${lengthOk ? 'text-success-600 dark:text-success-400' : 'text-secondary-500 dark:text-secondary-400'}`}>
              {lengthOk ? '✓' : '○'} At least 8 characters
            </li>
            <li className={`${upperOk ? 'text-success-600 dark:text-success-400' : 'text-secondary-500 dark:text-secondary-400'}`}>
              {upperOk ? '✓' : '○'} At least one uppercase letter (A-Z)
            </li>
            <li className={`${lowerOk ? 'text-success-600 dark:text-success-400' : 'text-secondary-500 dark:text-secondary-400'}`}>
              {lowerOk ? '✓' : '○'} At least one lowercase letter (a-z)
            </li>
            <li className={`${digitOk ? 'text-success-600 dark:text-success-400' : 'text-secondary-500 dark:text-secondary-400'}`}>
              {digitOk ? '✓' : '○'} At least one number (0-9)
            </li>
            <li className={`${specialOk ? 'text-success-600 dark:text-success-400' : 'text-secondary-500 dark:text-secondary-400'}`}>
              {specialOk ? '✓' : '○'} At least one special character (!@#$%^&*, etc.)
            </li>
            <li className={`${matchOk ? 'text-success-600 dark:text-success-400' : 'text-secondary-500 dark:text-secondary-400'}`}>
              {matchOk ? '✓' : '○'} New password matches confirmation
            </li>
          </ul>
        </div>
        
        <div className="mb-4">
          <label htmlFor="confirmPassword" className="block text-sm font-medium text-secondary-700 mb-1">
            Confirm New Password
          </label>
          <Input
            id="confirmPassword"
            type="password"
            value={confirmPassword}
            onChange={(e) => setConfirmPassword(e.target.value)}
          />
        </div>
        
        <div className="mt-6 flex justify-end space-x-3">
          <Button 
            variant="outline" 
            onClick={handleClose}
          >
            Cancel
          </Button>
          <Button 
            type="submit" 
            isLoading={isLoading}
          >
            Change Password
          </Button>
        </div>
      </form>
    </Modal>
  );
};

export default PasswordChangeModal; 