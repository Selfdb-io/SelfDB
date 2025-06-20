import React, { useState, useEffect } from 'react';
import { HiClipboardDocumentList, HiCheckCircle } from "react-icons/hi2";
import { getTableSql } from '../../../../services/tableService';
import { Loader } from '../ui/Loader';

interface TableSqlProps {
  tableName: string;
}

const TableSql: React.FC<TableSqlProps> = ({ tableName }) => {
  const [sql, setSql] = useState<string>('');
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [copied, setCopied] = useState<boolean>(false);

  useEffect(() => {
    const fetchTableSql = async () => {
      try {
        setLoading(true);
        const data = await getTableSql(tableName);
        setSql(data.sql);
        setError(null);
      } catch (err: any) {
        console.error('Error fetching table SQL:', err);
        setError(err.response?.data?.detail || err.message || 'Failed to load SQL script');
      } finally {
        setLoading(false);
      }
    };

    fetchTableSql();
  }, [tableName]);

  const handleCopyToClipboard = () => {
    navigator.clipboard.writeText(sql);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  if (loading) {
    return (
      <div className="flex justify-center p-8">
        <Loader size="large" />
      </div>
    );
  }

  if (error) {
    return (
      <div className="p-6 bg-error-50 dark:bg-error-900/20 text-error-700 dark:text-error-300 rounded-md">
        <p className="font-medium mb-2">Error Loading SQL</p>
        <p>{error}</p>
      </div>
    );
  }

  return (
    <div>
      <div className="flex justify-between items-center mb-4">
        <h3 className="text-lg font-heading font-semibold text-secondary-800 dark:text-white">
          SQL Creation Script
        </h3>
        <button
          onClick={handleCopyToClipboard}
          disabled={!sql}
          className={`flex items-center space-x-1.5 px-3 py-1.5 text-sm rounded-md transition-colors duration-150 disabled:opacity-50 ${
            copied
              ? 'bg-success-100 text-success-700 dark:bg-success-900/30 dark:text-success-300 border border-success-200 dark:border-success-700'
              : 'bg-white dark:bg-secondary-700 border border-secondary-300 dark:border-secondary-600 text-secondary-700 dark:text-secondary-300 hover:bg-secondary-50 dark:hover:bg-secondary-600'
          }`}
        >
          {copied ? (
            <>
              <HiCheckCircle className="w-4 h-4" />
              <span>Copied!</span>
            </>
          ) : (
            <>
              <HiClipboardDocumentList className="w-4 h-4" />
              <span>Copy</span>
            </>
          )}
        </button>
      </div>
      
      <div className="bg-secondary-800 dark:bg-secondary-900 text-white rounded-md p-4 font-mono text-sm overflow-auto max-h-[500px] whitespace-pre-wrap">
        {sql || <span className="text-secondary-400 dark:text-secondary-500 italic">No SQL script available</span>}
      </div>
    </div>
  );
};

export default TableSql; 