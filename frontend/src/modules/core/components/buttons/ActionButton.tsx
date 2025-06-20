import React from 'react';

interface ActionButtonProps {
  title: string;
  description: string;
  icon: React.ReactNode;
  onClick: () => void;
}

export const ActionButton: React.FC<ActionButtonProps> = ({
  title,
  description,
  icon,
  onClick
}) => {
  return (
    <button 
      onClick={onClick} 
      className="flex items-center p-4 border border-secondary-200 dark:border-secondary-600 rounded-lg hover:bg-secondary-50 dark:hover:bg-secondary-700 hover:border-primary-300 dark:hover:border-primary-700 transition-colors"
    >
      <div className="mr-3 bg-secondary-100 dark:bg-secondary-700 p-2 rounded-full text-primary-600 dark:text-primary-400 shrink-0">
        {icon}
      </div>
      <div className="flex-1 text-left">
        <h3 className="text-lg font-medium text-secondary-800 dark:text-white">{title}</h3>
        <p className="text-sm text-secondary-500 dark:text-secondary-400">{description}</p>
      </div>
    </button>
  );
}; 