import React, { useEffect, useRef } from 'react';
import { createPortal } from 'react-dom';
import { cn } from '../../modules/core/utils/cn';
import { useTheme } from '../../modules/core/context/ThemeContext';

export interface ModalProps {
  isOpen: boolean;
  onClose: () => void;
  title: string;
  size?: 'sm' | 'md' | 'lg' | 'xl';
  children: React.ReactNode;
  className?: string;
}

export const Modal: React.FC<ModalProps> = ({
  isOpen,
  onClose,
  title,
  size = 'md',
  children,
  className,
}) => {
  const { theme } = useTheme();
  const modalRef = useRef<HTMLDivElement>(null);

  // Close modal when clicking outside
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (modalRef.current && !modalRef.current.contains(event.target as Node)) {
        onClose();
      }
    };

    // Close modal on escape key press
    const handleEscKey = (event: KeyboardEvent) => {
      if (event.key === 'Escape') {
        onClose();
      }
    };

    if (isOpen) {
      document.addEventListener('mousedown', handleClickOutside);
      document.addEventListener('keydown', handleEscKey);
      // Prevent body scrolling when modal is open
      document.body.style.overflow = 'hidden';
    }

    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
      document.removeEventListener('keydown', handleEscKey);
      document.body.style.overflow = '';
    };
  }, [isOpen, onClose]);

  // Size classes based on design system
  const sizeClasses = {
    sm: 'max-w-sm',
    md: 'max-w-md',
    lg: 'max-w-lg',
    xl: 'max-w-xl',
  };

  if (!isOpen) return null;

  return createPortal(
    <div className={cn(
      "fixed inset-0 z-50 flex items-center justify-center p-4",
      theme === 'dark' ? 'bg-secondary-950/80' : 'bg-secondary-950/50'
    )}>
      <div 
        ref={modalRef}
        className={cn(
          'relative rounded-lg shadow-lg w-full',
          theme === 'dark' ? 'bg-secondary-800 border border-secondary-700' : 'bg-white',
          sizeClasses[size],
          className
        )}
      >
        {/* Modal header */}
        <div className={cn(
          "flex items-center justify-between p-4 border-b",
          theme === 'dark' ? 'border-secondary-700' : 'border-secondary-200'
        )}>
          <h3 className={cn(
            "font-heading text-lg font-medium",
            theme === 'dark' ? 'text-white' : 'text-secondary-800'
          )}>
            {title}
          </h3>
          <button
            type="button"
            onClick={onClose}
            className={cn(
              "focus:outline-none focus:ring-2 focus:ring-primary-500 rounded-md",
              theme === 'dark' ? 'text-secondary-400 hover:text-secondary-200' : 'text-secondary-500 hover:text-secondary-700'
            )}
          >
            <svg 
              xmlns="http://www.w3.org/2000/svg" 
              className="h-5 w-5" 
              viewBox="0 0 20 20" 
              fill="currentColor"
            >
              <path 
                fillRule="evenodd" 
                d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z" 
                clipRule="evenodd" 
              />
            </svg>
          </button>
        </div>

        {/* Modal content */}
        <div className="p-4">
          {children}
        </div>
      </div>
    </div>,
    document.body
  );
}; 