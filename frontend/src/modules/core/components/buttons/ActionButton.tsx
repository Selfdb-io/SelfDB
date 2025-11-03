import React from 'react';
import { FiCheck, FiClock } from 'react-icons/fi';

interface ActionButtonProps {
  title: string;
  description: string;
  icon: React.ReactNode;
  onClick: () => void;
  badgeLabel?: string;
  badgeStatus?: 'ready' | 'pending';
}

export const ActionButton: React.FC<ActionButtonProps> = ({
  title,
  description,
  icon,
  onClick,
  badgeLabel,
  badgeStatus
}) => {
  const badgeStyles = (() => {
    switch (badgeStatus) {
      case 'ready':
        return {
          text: 'text-green-600 dark:text-green-300',
          icon: <FiCheck className="h-3 w-3 text-green-700" />,
          iconBg: 'bg-green-100 dark:bg-green-900/40'
        };
      case 'pending':
        return {
          text: 'text-amber-600 dark:text-amber-300',
          icon: <FiClock className="h-3 w-3 text-amber-700" />,
          iconBg: 'bg-amber-100 dark:bg-amber-900/40'
        };
      default:
        return {
          text: 'text-primary-600 dark:text-primary-300',
          icon: null as React.ReactNode,
          iconBg: 'bg-primary-100 dark:bg-primary-900/40'
        };
    }
  })();

  return (
    <button 
      onClick={onClick} 
      className="flex items-center p-4 border border-secondary-200 dark:border-secondary-600 rounded-lg hover:bg-secondary-50 dark:hover:bg-secondary-700 hover:border-primary-300 dark:hover:border-primary-700 transition-colors"
    >
      <div className="mr-3 bg-secondary-100 dark:bg-secondary-700 p-2 rounded-full text-primary-600 dark:text-primary-400 shrink-0">
        {icon}
      </div>
      <div className="flex-1 text-left">
        <div className="flex items-center gap-2 flex-wrap">
          <h3 className="text-lg font-medium text-secondary-800 dark:text-white">{title}</h3>
          {badgeLabel && (
            <span className={`inline-flex items-center gap-1 text-sm font-medium ${badgeStyles.text}`}>
              {badgeStyles.icon && (
                <span className={`inline-flex h-5 w-5 items-center justify-center rounded-full ${badgeStyles.iconBg}`}>
                  {badgeStyles.icon}
                </span>
              )}
              {badgeLabel}
            </span>
          )}
        </div>
        <p className="text-sm text-secondary-500 dark:text-secondary-400">{description}</p>
      </div>
    </button>
  );
}; 