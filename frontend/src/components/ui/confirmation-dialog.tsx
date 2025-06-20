import React, { ReactNode } from 'react';
import { Modal } from './modal';
import { Button } from './button';

export interface ConfirmationDialogProps {
  isOpen: boolean;
  onClose: () => void;
  onConfirm: () => void;
  title?: string;
  description?: ReactNode;
  confirmButtonText?: string;
  cancelButtonText?: string;
  confirmButtonVariant?: 'primary' | 'secondary' | 'subtle' | 'outline' | 'ghost' | 'link';
  confirmButtonClassName?: string;
  cancelButtonClassName?: string;
  isConfirmLoading?: boolean;
  isDestructive?: boolean;
}

export const ConfirmationDialog: React.FC<ConfirmationDialogProps> = ({
  isOpen,
  onClose,
  onConfirm,
  title = 'Confirm Action',
  description = 'Are you sure you want to perform this action?',
  confirmButtonText = 'Confirm',
  cancelButtonText = 'Cancel',
  confirmButtonVariant = 'primary',
  confirmButtonClassName = '',
  cancelButtonClassName = '',
  isConfirmLoading = false,
  isDestructive = false,
}) => {
  const getConfirmButtonClasses = () => {
    if (isDestructive) {
      return `text-white bg-error-600 hover:bg-error-700 dark:bg-error-700 dark:hover:bg-error-800 ${confirmButtonClassName}`;
    }
    if (confirmButtonClassName.includes('bg-error')) {
      return confirmButtonClassName;
    }
    return confirmButtonClassName;
  };

  return (
    <Modal 
      isOpen={isOpen} 
      onClose={onClose}
      title={title}
    >
      <div className="space-y-4">
        <div className="text-secondary-700 dark:text-secondary-300">
          {description}
        </div>
        <div className="flex justify-end space-x-2 pt-2">
          <Button 
            type="button" 
            variant="outline" 
            onClick={onClose}
            className={cancelButtonClassName}
          >
            {cancelButtonText}
          </Button>
          <Button 
            type="button"
            variant={confirmButtonVariant}
            className={getConfirmButtonClasses()}
            onClick={onConfirm}
            isLoading={isConfirmLoading}
          >
            {confirmButtonText}
          </Button>
        </div>
      </div>
    </Modal>
  );
}; 