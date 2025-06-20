import React, { useState, useRef, useEffect } from 'react';
import { cn } from '../../modules/core/utils/cn';

interface DropdownMenuProps {
  trigger: React.ReactNode;
  children: React.ReactNode;
  align?: 'left' | 'right';
  width?: 'auto' | 'sm' | 'md' | 'lg';
  className?: string;
}

export const DropdownMenu: React.FC<DropdownMenuProps> = ({
  trigger,
  children,
  align = 'right',
  width = 'md',
  className,
}) => {
  const [isOpen, setIsOpen] = useState(false);
  const dropdownRef = useRef<HTMLDivElement>(null);

  // Handle clicks outside to close dropdown
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
        setIsOpen(false);
      }
    };

    if (isOpen) {
      document.addEventListener('mousedown', handleClickOutside);
    }

    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
    };
  }, [isOpen]);

  // Define width classes
  const widthClasses = {
    auto: 'w-auto',
    sm: 'w-48',
    md: 'w-56',
    lg: 'w-64',
  };

  // Define alignment classes
  const alignClasses = {
    left: 'left-0',
    right: 'right-0',
  };

  return (
    <div className="relative" ref={dropdownRef}>
      <div
        onClick={() => setIsOpen(!isOpen)}
        className="cursor-pointer"
      >
        {trigger}
      </div>

      {isOpen && (
        <div
          className={cn(
            'absolute z-10 mt-2 origin-top-right rounded-md bg-white py-1 shadow-lg ring-1 ring-secondary-200 focus:outline-none',
            alignClasses[align],
            widthClasses[width],
            className
          )}
        >
          {children}
        </div>
      )}
    </div>
  );
};

interface DropdownItemProps {
  children: React.ReactNode;
  onClick?: () => void;
  className?: string;
  icon?: React.ReactNode;
  disabled?: boolean;
  variant?: 'default' | 'primary' | 'destructive';
}

export const DropdownItem: React.FC<DropdownItemProps> = ({
  children,
  onClick,
  className,
  icon,
  disabled = false,
  variant = 'default',
}) => {
  // Define variant styles
  const variantStyles = {
    default: 'text-secondary-700 hover:bg-secondary-50',
    primary: 'text-primary-600 hover:bg-primary-50 font-medium',
    destructive: 'text-error-600 hover:bg-error-50',
  };

  return (
    <button
      className={cn(
        'flex w-full items-center px-4 py-2 text-sm',
        variantStyles[variant],
        disabled && 'opacity-50 cursor-not-allowed hover:bg-transparent',
        className
      )}
      onClick={disabled ? undefined : onClick}
      disabled={disabled}
    >
      {icon && <span className="mr-2 text-secondary-500">{icon}</span>}
      {children}
    </button>
  );
}; 