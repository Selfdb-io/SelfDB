import React from 'react';

interface CardProps {
  title: string;
  children: React.ReactNode;
  className?: string;
}

export const Card: React.FC<CardProps> = ({ title, children, className = '' }) => {
  return (
    <div className={`bg-white dark:bg-secondary-800 rounded-lg shadow border border-secondary-100 dark:border-secondary-700 p-6 ${className}`}>
      <h2 className="text-xl font-semibold text-secondary-800 dark:text-white mb-4">{title}</h2>
      <div>
        {children}
      </div>
    </div>
  );
}; 