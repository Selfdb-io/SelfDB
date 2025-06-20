import React from 'react';
import { SqlHistoryItem } from '../../../../services/sqlService';
import { formatSql } from '../../utils/sqlFormatter';

interface SqlHistoryListProps {
  history: SqlHistoryItem[];
  loading: boolean;
  onHistoryClick: (historyItem: SqlHistoryItem) => void;
}

const SqlHistoryList: React.FC<SqlHistoryListProps> = ({
  history,
  loading,
  onHistoryClick,
}) => {
  if (loading) {
    return (
      <div className="flex justify-center items-center py-10">
        <div className="animate-spin rounded-full h-10 w-10 border-b-2 border-primary-600"></div>
      </div>
    );
  }

  if (!history || history.length === 0) {
    return (
      <div className="bg-white dark:bg-secondary-800 p-8 text-center rounded-lg border border-secondary-200 dark:border-secondary-700">
        <div className="text-secondary-400 dark:text-secondary-500 mb-3">
          <svg xmlns="http://www.w3.org/2000/svg" className="h-12 w-12 mx-auto" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
        </div>
        <h3 className="text-lg font-heading font-semibold text-secondary-800 dark:text-secondary-300">No query history</h3>
        <p className="mt-1 text-xs text-secondary-500 dark:text-secondary-400">
          Execute queries to see your history
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-3">
      {history.map((item) => (
        <div
          key={item.id}
          onClick={() => onHistoryClick(item)}
          className={`bg-white dark:bg-secondary-800 p-4 rounded-lg border border-secondary-200 dark:border-secondary-700 hover:border-primary-300 dark:hover:border-primary-700 cursor-pointer transition-colors ${
            item.error ? 'border-l-4 border-l-error-500' : 'border-l-4 border-l-success-500'
          }`}
        >
          <div className="flex justify-between items-center mb-2">
            <span className="text-xs font-medium text-secondary-800 dark:text-secondary-300">
              {new Date(item.executed_at).toLocaleString()}
            </span>
            <div className="text-xs text-secondary-500 dark:text-secondary-400">
              {item.execution_time ? `${item.execution_time.toFixed(3)}s` : 'N/A'}
              {item.row_count !== null && ` • ${item.row_count} rows`}
            </div>
          </div>
          
          <div className="bg-secondary-50 dark:bg-secondary-900 p-2 rounded font-mono text-xs text-secondary-800 dark:text-secondary-300 overflow-hidden">
            <div className="line-clamp-3">{formatSql(item.query)}</div>
          </div>
          
          {item.error && (
            <div className="mt-2 text-xs text-error-600 dark:text-error-400">
              Error: {item.error}
            </div>
          )}
        </div>
      ))}
    </div>
  );
};

export default SqlHistoryList; 