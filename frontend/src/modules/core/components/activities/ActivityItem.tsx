import React from 'react';

interface ActivityItemProps {
  title: string;
  description: string;
  timestamp: string;
  icon?: React.ReactNode;
}

export const ActivityItem: React.FC<ActivityItemProps> = ({
  title,
  description,
  timestamp,
  icon = (
    <svg className="w-5 h-5 text-secondary-600 dark:text-secondary-300" fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
    </svg>
  )
}) => {
  return (
    <div className="flex items-start border-b border-secondary-100 dark:border-secondary-700 pb-4 last:border-0">
      <div className="bg-secondary-100 dark:bg-secondary-700 p-2 rounded-full mr-3">
        {icon}
      </div>
      <div>
        <h3 className="text-lg font-medium text-secondary-800 dark:text-white">{title}</h3>
        <p className="text-sm text-secondary-500 dark:text-secondary-400">{description}</p>
        <p className="text-xs text-secondary-400 dark:text-secondary-500 mt-1">{timestamp}</p>
      </div>
    </div>
  );
}; 