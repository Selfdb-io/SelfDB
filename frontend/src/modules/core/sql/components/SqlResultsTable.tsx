import React from 'react';
import { SqlQueryResult } from '../../../../services/sqlService';
import { formatCellValue } from '../../utils/sqlFormatter';
import { FiDownload } from 'react-icons/fi';

interface SqlResultsTableProps {
  results: SqlQueryResult | null;
  onDownloadRequest?: (payload: { columns: string[]; data: any[] }) => void;
}

const SqlResultsTable: React.FC<SqlResultsTableProps> = ({ results, onDownloadRequest }) => {
  if (!results) return null;

  // Single query result (old format)
  if (!results.results) {
    // Check if we have enhanced DDL results (columns + data even for non-read-only)
    if (!results.is_read_only && results.columns && results.data && results.data.length > 0) {
      // Render enhanced DDL operations table
      return (
        <div className="mt-4">
          <div className="bg-success-50 dark:bg-success-900/30 p-3 rounded-lg border border-success-200 dark:border-success-700 mb-3">
            <div className="text-success-700 dark:text-success-300 font-medium text-sm">{results.message}</div>
            <div className="text-xs text-success-600 dark:text-success-400 mt-1">
              Execution time: {results.execution_time?.toFixed(3)} seconds
            </div>
          </div>
          <div className="flex justify-end items-center mb-2">
            <button
              type="button"
              className="p-2 text-secondary-500 hover:text-secondary-700 dark:text-secondary-400 dark:hover:text-secondary-200"
              title="Download (CSV or Text)"
              onClick={() => onDownloadRequest && onDownloadRequest({ columns: results.columns!, data: results.data! })}
            >
              <FiDownload className="h-5 w-5" />
            </button>
          </div>
          
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-secondary-200 dark:divide-secondary-700">
              <thead className="bg-secondary-50 dark:bg-secondary-800">
                <tr>
                  {results.columns.map((column, index) => (
                    <th 
                      key={index} 
                      className="px-4 py-2 text-left text-xs font-medium text-secondary-500 dark:text-secondary-400 uppercase tracking-wider"
                    >
                      {column}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody className="bg-white dark:bg-secondary-800 divide-y divide-secondary-200 dark:divide-secondary-700">
                {results.data.map((row, rowIndex) => (
                  <tr key={rowIndex}>
                    {results.columns && results.columns.map((column, colIndex) => (
                      <td 
                        key={colIndex}
                        className="px-4 py-2 text-xs text-secondary-800 dark:text-secondary-300"
                      >
                        {formatCellValue(row[column])}
                      </td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      );
    }
    
    if (!results.is_read_only) {
      return (
        <div className="bg-white dark:bg-secondary-800 p-4 rounded-lg border border-secondary-200 dark:border-secondary-700 mt-4">
          <div className="text-success-600 dark:text-success-400 font-medium mb-2">Query executed successfully</div>
          <div className="text-xs text-secondary-800 dark:text-secondary-300">{results.message}</div>
          <div className="text-xs text-secondary-500 dark:text-secondary-400 mt-2">
            Execution time: {results.execution_time?.toFixed(3)} seconds
          </div>
        </div>
      );
    }

    if (!results.columns || !results.data || results.data.length === 0) {
      return (
        <div className="bg-white dark:bg-secondary-800 p-4 rounded-lg border border-secondary-200 dark:border-secondary-700 mt-4">
          <div className="font-medium text-xs text-secondary-800 dark:text-secondary-300 mb-2">Query executed successfully</div>
          <div className="text-xs text-secondary-600 dark:text-secondary-400">No results returned</div>
          <div className="text-xs text-secondary-500 dark:text-secondary-400 mt-2">
            Execution time: {results.execution_time?.toFixed(3)} seconds
          </div>
        </div>
      );
    }

    return (
      <div className="mt-4">
        <div className="flex justify-between items-center mb-2">
          <div className="text-xs font-medium text-secondary-800 dark:text-secondary-300">
            Results: {results.row_count} rows
          </div>
          <div className="flex items-center space-x-2">
            <div className="text-xs text-secondary-500 dark:text-secondary-400">
              Execution time: {results.execution_time?.toFixed(3)} seconds
            </div>
            {results.columns && results.data && results.data.length > 0 && (
              <button
                type="button"
                className="p-2 text-secondary-500 hover:text-secondary-700 dark:text-secondary-400 dark:hover:text-secondary-200"
                title="Download (CSV or Text)"
                onClick={() => onDownloadRequest && onDownloadRequest({ columns: results.columns!, data: results.data! })}
              >
                <FiDownload className="h-5 w-5" />
              </button>
            )}
          </div>
        </div>
        
        <div className="overflow-x-auto">
          <table className="min-w-full divide-y divide-secondary-200 dark:divide-secondary-700">
            <thead className="bg-secondary-50 dark:bg-secondary-800">
              <tr>
                {results.columns && results.columns.map((column, index) => (
                  <th 
                    key={index} 
                    className="px-4 py-2 text-left text-xs font-medium text-secondary-500 dark:text-secondary-400 uppercase tracking-wider"
                  >
                    {column}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody className="bg-white dark:bg-secondary-800 divide-y divide-secondary-200 dark:divide-secondary-700">
              {results.data.map((row, rowIndex) => (
                <tr key={rowIndex}>
                  {results.columns && results.columns.map((column, colIndex) => (
                    <td 
                      key={colIndex}
                      className="px-4 py-2 text-xs text-secondary-800 dark:text-secondary-300"
                    >
                      {formatCellValue(row[column])}
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    );
  }

  // Multiple query results (new format)
  return (
    <div className="mt-4">
      <div className="flex justify-between items-center mb-2">
        <div className="text-xs font-medium text-secondary-800 dark:text-secondary-300">
          {results.results.length} {results.results.length === 1 ? 'Statement' : 'Statements'} Executed
        </div>
        <div className="text-xs text-secondary-500 dark:text-secondary-400">
          Total execution time: {results.total_execution_time?.toFixed(3)} seconds
        </div>
      </div>

      <div className="space-y-4">
        {results.results.map((result, resultIndex) => (
          <div 
            key={resultIndex}
            className="bg-white dark:bg-secondary-800 p-4 rounded-lg border border-secondary-200 dark:border-secondary-700"
          >
            <div className="mb-3">
              <div className="bg-secondary-50 dark:bg-secondary-900 p-2 rounded-md font-mono text-xs text-secondary-800 dark:text-secondary-300 mb-2 whitespace-pre-wrap">
                {result.statement}
              </div>
              
              <div className="flex justify-between items-center">
                <div className="text-xs text-secondary-500 dark:text-secondary-400">
                  Execution time: {result.execution_time.toFixed(3)} seconds
                </div>
                {!result.is_read_only && (
                  <div className="text-xs text-success-600 dark:text-success-400">
                    {result.message}
                  </div>
                )}
              </div>
            </div>

            {result.is_read_only && (
              <>
                {(!result.columns || !result.data || result.data.length === 0) ? (
                  <div className="text-xs text-secondary-600 dark:text-secondary-400 mt-2">
                    No results returned
                  </div>
                ) : (
                  <>
                    <div className="flex justify-between items-center mb-2">
                      <div className="text-xs text-secondary-800 dark:text-secondary-300">
                        Results: {result.row_count} rows
                      </div>
                      {result.columns && result.data && result.data.length > 0 && (
                        <button
                          type="button"
                          className="p-2 text-secondary-500 hover:text-secondary-700 dark:text-secondary-400 dark:hover:text-secondary-200"
                          title="Download (CSV or Text)"
                          onClick={() => onDownloadRequest && onDownloadRequest({ columns: result.columns!, data: result.data! })}
                        >
                          <FiDownload className="h-5 w-5" />
                        </button>
                      )}
                    </div>
                    <div className="overflow-x-auto">
                      <table className="min-w-full divide-y divide-secondary-200 dark:divide-secondary-700">
                        <thead className="bg-secondary-50 dark:bg-secondary-900">
                          <tr>
                            {result.columns && result.columns.map((column, index) => (
                              <th 
                                key={index} 
                                className="px-4 py-2 text-left text-xs font-medium text-secondary-500 dark:text-secondary-400 uppercase tracking-wider"
                              >
                                {column}
                              </th>
                            ))}
                          </tr>
                        </thead>
                        <tbody className="bg-white dark:bg-secondary-800 divide-y divide-secondary-200 dark:divide-secondary-700">
                          {result.data && result.columns && result.data.map((row, rowIndex) => (
                            <tr key={rowIndex}>
                              {result.columns && result.columns.map((column, colIndex) => (
                                <td 
                                  key={colIndex}
                                  className="px-4 py-2 text-xs text-secondary-800 dark:text-secondary-300"
                                >
                                  {formatCellValue(row[column])}
                                </td>
                              ))}
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  </>
                )}
              </>
            )}
          </div>
        ))}
      </div>
    </div>
  );
};

export default SqlResultsTable; 