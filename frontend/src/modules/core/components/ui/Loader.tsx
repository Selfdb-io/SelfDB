import React from 'react';

interface LoaderProps {
  size?: 'small' | 'medium' | 'large';
  className?: string;
}

export const Loader: React.FC<LoaderProps> = ({ 
  size = 'medium', 
  className = ''
}) => {
  const sizeClass = {
    small: 'h-4 w-4 border-2',
    medium: 'h-8 w-8 border-2',
    large: 'h-12 w-12 border-b-2'
  };

  return (
    <div className={`animate-spin rounded-full border-primary-600 ${sizeClass[size]} ${className}`}></div>
  );
};

export default Loader; 