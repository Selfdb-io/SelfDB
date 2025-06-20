import React from 'react';
import { cn } from '../../modules/core/utils/cn';

interface AvatarProps {
  initial: string;
  size?: 'sm' | 'md' | 'lg';
  colorScheme?: 'primary' | 'secondary' | 'accent';
  className?: string;
}

export const Avatar: React.FC<AvatarProps> = ({
  initial,
  size = 'md',
  colorScheme = 'primary',
  className,
}) => {
  // Define size classes
  const sizeClasses = {
    sm: 'h-6 w-6 text-xs',
    md: 'h-8 w-8 text-sm',
    lg: 'h-10 w-10 text-base',
  };

  // Define color classes based on our design system
  const colorClasses = {
    primary: 'bg-primary-600 text-white',
    secondary: 'bg-secondary-200 text-secondary-800',
    accent: 'bg-accent-500 text-white',
  };

  return (
    <div
      className={cn(
        'rounded-full flex items-center justify-center font-medium',
        sizeClasses[size],
        colorClasses[colorScheme],
        className
      )}
    >
      {initial.charAt(0).toUpperCase()}
    </div>
  );
}; 