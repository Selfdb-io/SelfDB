import React from 'react';
import { SqlQueryResult } from '../../../../services/sqlService';
import { formatCellValue } from '../../utils/sqlFormatter';

interface SqlResultsTableProps {
  results: SqlQueryResult | null;
}

const SqlResultsTable: React.FC<SqlResultsTableProps> = ({ results }) => {
  if (!results) return null;

  // Single query result (old format)
  if (!results.results) {
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
          <div className="text-xs text-secondary-500 dark:text-secondary-400">
            Execution time: {results.execution_time?.toFixed(3)} seconds
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
                    <div className="text-xs text-secondary-800 dark:text-secondary-300 mb-2">
                      Results: {result.row_count} rows
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