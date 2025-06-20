import React from 'react';
import { SqlSnippet } from '../../../../services/sqlService';
import { formatSql } from '../../utils/sqlFormatter';

interface SqlSnippetsListProps {
  snippets: SqlSnippet[];
  loading: boolean;
  onSnippetClick: (snippet: SqlSnippet) => void;
}

const SqlSnippetsList: React.FC<SqlSnippetsListProps> = ({
  snippets,
  loading,
  onSnippetClick,
}) => {
  if (loading) {
    return (
      <div className="flex justify-center items-center py-10">
        <div className="animate-spin rounded-full h-10 w-10 border-b-2 border-primary-600"></div>
      </div>
    );
  }

  if (!snippets || snippets.length === 0) {
    return (
      <div className="bg-white dark:bg-secondary-800 p-8 text-center rounded-lg border border-secondary-200 dark:border-secondary-700">
        <div className="text-secondary-400 dark:text-secondary-500 mb-3">
          <svg xmlns="http://www.w3.org/2000/svg" className="h-12 w-12 mx-auto" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 5a2 2 0 012-2h10a2 2 0 012 2v16l-7-3.5L5 21V5z" />
          </svg>
        </div>
        <h3 className="text-lg font-heading font-semibold text-secondary-800 dark:text-secondary-300">No saved snippets</h3>
        <p className="mt-1 text-xs text-secondary-500 dark:text-secondary-400">
          Save your SQL queries for quick access
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-3">
      {snippets.map((snippet) => (
        <div
          key={snippet.id}
          onClick={() => onSnippetClick(snippet)}
          className="bg-white dark:bg-secondary-800 p-4 rounded-lg border border-secondary-200 dark:border-secondary-700 hover:border-primary-300 dark:hover:border-primary-700 cursor-pointer transition-colors"
        >
          <div className="flex items-center mb-2">
            <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5 text-primary-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 5a2 2 0 012-2h10a2 2 0 012 2v16l-7-3.5L5 21V5z" />
            </svg>
            <h3 className="ml-2 font-medium text-xs text-secondary-800 dark:text-secondary-300">
              {snippet.name}
            </h3>
            {snippet.is_shared && (
              <span className="ml-2 inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-accent-100 dark:bg-accent-900 text-accent-800 dark:text-accent-300">
                Shared
              </span>
            )}
          </div>
          
          {snippet.description && (
            <p className="text-xs text-secondary-500 dark:text-secondary-400 mb-2">
              {snippet.description}
            </p>
          )}
          
          <div className="bg-secondary-50 dark:bg-secondary-900 p-2 rounded font-mono text-xs text-secondary-800 dark:text-secondary-300 overflow-hidden">
            <div className="line-clamp-3">{formatSql(snippet.sql_code)}</div>
          </div>
        </div>
      ))}
    </div>
  );
};

export default SqlSnippetsList; 