import React from 'react';

interface SummaryCardProps {
  title: string;
  value: string | number;
  subtitle: string;
}

export const SummaryCard: React.FC<SummaryCardProps> = ({ title, value, subtitle }) => {
  return (
    <div className="bg-white dark:bg-secondary-800 rounded-lg shadow border border-secondary-100 dark:border-secondary-700 p-6">
      <h3 className="text-lg font-medium text-secondary-800 dark:text-white mb-2">{title}</h3>
      <p className="text-3xl font-bold text-primary-600 dark:text-primary-400">{value}</p>
      <p className="text-sm text-secondary-500 dark:text-secondary-400 mt-2">{subtitle}</p>
    </div>
  );
}; 