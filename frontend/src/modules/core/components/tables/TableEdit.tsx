import React, { useState, useEffect } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { getTable } from '../../../../services/tableService';
import { Loader } from '../ui/Loader';

const TableEdit: React.FC = () => {
  const { tableName } = useParams<{ tableName: string }>();
  const navigate = useNavigate();
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [tableInfo, setTableInfo] = useState<any>(null);

  useEffect(() => {
    const fetchTableDetails = async () => {
      if (!tableName) return;
      
      try {
        setLoading(true);
        // Fetch table metadata
        const tableData = await getTable(tableName);
        setTableInfo(tableData);
        setError(null);
      } catch (err: any) {
        console.error('Error fetching table details:', err);
        setError(err.response?.data?.detail || err.message || 'Failed to load table structure');
      } finally {
        setLoading(false);
      }
    };

    fetchTableDetails();
  }, [tableName]);

  if (loading) {
    return (
      <div className="p-6">
        <div className="flex items-center mb-6">
          <button
            onClick={() => navigate(`/tables/${tableName}`)}
            className="mr-4 text-primary-600 hover:text-primary-700 dark:text-primary-400 dark:hover:text-primary-300"
          >
            ← Back to Table
          </button>
          <h2 className="text-2xl font-heading font-semibold text-secondary-800 dark:text-white tracking-tight">
            Edit {tableName}
          </h2>
        </div>
        <div className="bg-white dark:bg-secondary-800 p-12 rounded-lg shadow border border-secondary-200 dark:border-secondary-700 flex justify-center">
          <Loader size="large" />
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="p-6">
        <div className="flex items-center mb-6">
          <button
            onClick={() => navigate(`/tables/${tableName}`)}
            className="mr-4 text-primary-600 hover:text-primary-700 dark:text-primary-400 dark:hover:text-primary-300"
          >
            ← Back to Table
          </button>
          <h2 className="text-2xl font-heading font-semibold text-secondary-800 dark:text-white tracking-tight">
            Error Loading Table Structure
          </h2>
        </div>
        <div className="bg-error-50 dark:bg-error-900/20 p-6 rounded-lg border border-error-200 dark:border-error-800 text-error-700 dark:text-error-300">
          <h3 className="text-lg font-heading font-semibold mb-2">Error</h3>
          <p>{error}</p>
        </div>
      </div>
    );
  }

  return (
    <div className="p-6">
      <div className="flex items-center mb-6">
        <button
          onClick={() => navigate(`/tables/${tableName}`)}
          className="mr-4 text-primary-600 hover:text-primary-700 dark:text-primary-400 dark:hover:text-primary-300"
        >
          ← Back to Table
        </button>
        <h2 className="text-2xl font-heading font-semibold text-secondary-800 dark:text-white tracking-tight">
          Edit Table: {tableName}
        </h2>
      </div>

      <div className="bg-white dark:bg-secondary-800 rounded-lg shadow border border-secondary-200 dark:border-secondary-700 p-6">
        <div className="grid grid-cols-1 gap-6">
          <div className="p-4 bg-warning-50 dark:bg-warning-900/20 border border-warning-200 dark:border-warning-800 rounded-md text-warning-700 dark:text-warning-300">
            <p>Table structure editing will be implemented soon. This is a placeholder component.</p>
          </div>
          
          {tableInfo && (
            <div>
              <h3 className="text-lg font-heading font-semibold mb-4 text-secondary-800 dark:text-white">Current Table Structure</h3>
              
              <div className="mb-4">
                <label className="block text-sm font-medium text-secondary-700 dark:text-secondary-300">Table Name</label>
                <div className="mt-1 p-2 bg-secondary-50 dark:bg-secondary-900 rounded-md">
                  {tableInfo.name}
                </div>
              </div>
              
              {tableInfo.description && (
                <div className="mb-4">
                  <label className="block text-sm font-medium text-secondary-700 dark:text-secondary-300">Description</label>
                  <div className="mt-1 p-2 bg-secondary-50 dark:bg-secondary-900 rounded-md">
                    {tableInfo.description}
                  </div>
                </div>
              )}
              
              {tableInfo.columns && (
                <div>
                  <label className="block text-sm font-medium text-secondary-700 dark:text-secondary-300 mb-2">Columns</label>
                  <div className="overflow-x-auto">
                    <table className="min-w-full divide-y divide-secondary-200 dark:divide-secondary-700">
                      <thead className="bg-secondary-50 dark:bg-secondary-800">
                        <tr>
                          <th className="px-4 py-2 text-left text-xs font-medium text-secondary-500 dark:text-secondary-400 uppercase tracking-wider">
                            Name
                          </th>
                          <th className="px-4 py-2 text-left text-xs font-medium text-secondary-500 dark:text-secondary-400 uppercase tracking-wider">
                            Type
                          </th>
                          <th className="px-4 py-2 text-center text-xs font-medium text-secondary-500 dark:text-secondary-400 uppercase tracking-wider">
                            Nullable
                          </th>
                          <th className="px-4 py-2 text-center text-xs font-medium text-secondary-500 dark:text-secondary-400 uppercase tracking-wider">
                            Primary Key
                          </th>
                        </tr>
                      </thead>
                      <tbody className="bg-white dark:bg-secondary-800 divide-y divide-secondary-200 dark:divide-secondary-700">
                        {tableInfo.columns.map((column: any, index: number) => (
                          <tr key={index}>
                            <td className="px-4 py-2 whitespace-nowrap text-secondary-700 dark:text-secondary-300">
                              {column.name}
                            </td>
                            <td className="px-4 py-2 whitespace-nowrap text-secondary-700 dark:text-secondary-300">
                              {column.type}
                            </td>
                            <td className="px-4 py-2 text-center text-secondary-700 dark:text-secondary-300">
                              {column.nullable ? 'Yes' : 'No'}
                            </td>
                            <td className="px-4 py-2 text-center text-secondary-700 dark:text-secondary-300">
                              {column.primary_key ? 'Yes' : 'No'}
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
              )}
            </div>
          )}
          
          <div className="flex justify-end mt-8">
            <button
              onClick={() => navigate(`/tables/${tableName}`)}
              className="px-4 py-2 bg-primary-600 text-white rounded-md hover:bg-primary-700 transition-colors"
            >
              Back to Table
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};

export default TableEdit; 