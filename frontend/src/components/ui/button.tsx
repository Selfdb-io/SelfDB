import React, { forwardRef, ButtonHTMLAttributes } from 'react';
import { cn } from '../../modules/core/utils/cn';

export interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: 'primary' | 'secondary' | 'subtle' | 'outline' | 'ghost' | 'link';
  size?: 'sm' | 'md' | 'lg' | 'icon';
  isLoading?: boolean;
  leftIcon?: React.ReactNode;
  rightIcon?: React.ReactNode;
}

export const Button = forwardRef<HTMLButtonElement, ButtonProps>(
  (
    {
      className,
      variant = 'primary',
      size = 'md',
      isLoading = false,
      leftIcon,
      rightIcon,
      children,
      disabled,
      type = 'button',
      ...props
    },
    ref
  ) => {
    // Define the base styles
    const baseStyles = 'inline-flex items-center justify-center font-medium transition-colors focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-primary-500 disabled:opacity-50 disabled:pointer-events-none';

    // Define variant styles based on design system
    const variantStyles = {
      primary: 'bg-primary-600 text-white hover:bg-primary-700 border border-transparent',
      secondary: 'bg-white dark:bg-secondary-700 border border-secondary-300 dark:border-secondary-600 text-secondary-700 dark:text-secondary-300 hover:bg-secondary-50 dark:hover:bg-secondary-600',
      subtle: 'bg-secondary-100 dark:bg-secondary-700/50 text-secondary-900 dark:text-secondary-200 hover:bg-secondary-200 dark:hover:bg-secondary-700 border border-transparent',
      outline: 'bg-transparent border border-secondary-300 dark:border-secondary-600 text-secondary-900 dark:text-secondary-200 hover:bg-secondary-50 dark:hover:bg-secondary-600',
      ghost: 'bg-transparent text-secondary-900 dark:text-secondary-200 hover:bg-secondary-100 dark:hover:bg-secondary-700 border border-transparent',
      link: 'bg-transparent text-primary-600 hover:underline border-none shadow-none p-0'
    };

    // Define size styles
    const sizeStyles = {
      sm: 'text-xs px-2.5 py-1.5 rounded',
      md: 'text-sm px-3 py-2 rounded-md',
      lg: 'text-base px-4 py-2.5 rounded-md',
      icon: 'p-2 rounded-full h-9 w-9'
    };

    return (
      <button
        ref={ref}
        type={type}
        disabled={disabled || isLoading}
        className={cn(
          baseStyles,
          variantStyles[variant],
          variant !== 'link' && sizeStyles[size],
          className
        )}
        {...props}
      >
        {isLoading && (
          <svg
            className="animate-spin -ml-1 mr-2 h-4 w-4 text-current"
            xmlns="http://www.w3.org/2000/svg"
            fill="none"
            viewBox="0 0 24 24"
          >
            <circle
              className="opacity-25"
              cx="12"
              cy="12"
              r="10"
              stroke="currentColor"
              strokeWidth="4"
            ></circle>
            <path
              className="opacity-75"
              fill="currentColor"
              d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
            ></path>
          </svg>
        )}
        {!isLoading && leftIcon && <span className="mr-2">{leftIcon}</span>}
        {children}
        {!isLoading && rightIcon && <span className="ml-2">{rightIcon}</span>}
      </button>
    );
  }
); 