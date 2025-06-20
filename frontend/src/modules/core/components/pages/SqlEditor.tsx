import React, { useState, useEffect } from 'react';
import sqlService, { SqlQueryResult, SqlSnippet, SqlHistoryItem } from '../../../../services/sqlService';
import {
  SqlCodeEditor,
  SqlResultsTable,
  SqlSnippetsList,
  SqlHistoryList,
  SaveSnippetDialog
} from '../../sql';

const SqlEditor: React.FC = () => {
  const [sql, setSql] = useState('SELECT * FROM users LIMIT 10;');
  const [results, setResults] = useState<SqlQueryResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<'snippets' | 'history'>('snippets');
  const [snippets, setSnippets] = useState<SqlSnippet[]>([]);
  const [history, setHistory] = useState<SqlHistoryItem[]>([]);
  const [loadingSnippets, setLoadingSnippets] = useState(false);
  const [loadingHistory, setLoadingHistory] = useState(false);
  const [saveDialogOpen, setSaveDialogOpen] = useState(false);

  useEffect(() => {
    fetchSnippets();
    fetchHistory();
  }, []);

  const fetchSnippets = async () => {
    try {
      setLoadingSnippets(true);
      const data = await sqlService.fetchSnippets();
      setSnippets(data);
    } catch (err) {
      console.error('Error fetching snippets:', err);
    } finally {
      setLoadingSnippets(false);
    }
  };

  const fetchHistory = async () => {
    try {
      setLoadingHistory(true);
      const data = await sqlService.fetchHistory();
      setHistory(data);
    } catch (err) {
      console.error('Error fetching history:', err);
    } finally {
      setLoadingHistory(false);
    }
  };

  const executeQuery = async () => {
    try {
      setLoading(true);
      setError(null);
      setResults(null);

      const data = await sqlService.executeQuery(sql);
      setResults(data);

      // Save to history
      if (data.results) {
        // Multiple statements
        await sqlService.saveQueryToHistory(
          sql,
          data.is_read_only || false,
          data.total_execution_time || 0,
          data.total_rows_affected || 0
        );
      } else {
        // Single statement
        await sqlService.saveQueryToHistory(
          sql,
          data.is_read_only || false,
          data.execution_time || 0,
          data.row_count || 0
        );
      }

      // Refresh history
      fetchHistory();
    } catch (err: any) {
      console.error('Error executing query:', err);
      setError(err.message);
      
      // Save failed query to history
      try {
        await sqlService.saveQueryToHistory(sql, true, 0, 0, err.message);
        fetchHistory();
      } catch (historyErr) {
        console.error('Error saving to history:', historyErr);
      }
    } finally {
      setLoading(false);
    }
  };

  const handleSaveSnippet = async (name: string, description: string, isShared: boolean) => {
    try {
      await sqlService.saveSnippet({
        name,
        sql_code: sql,
        description,
        is_shared: isShared
      });
      
      setSaveDialogOpen(false);
      fetchSnippets();
    } catch (err) {
      console.error('Error saving snippet:', err);
    }
  };

  const handleSnippetClick = (snippet: SqlSnippet) => {
    setSql(snippet.sql_code);
  };

  const handleHistoryClick = (historyItem: SqlHistoryItem) => {
    setSql(historyItem.query);
  };

  const handleClearEditor = () => {
    setSql('');
  };

  const handleCopyToClipboard = () => {
    navigator.clipboard.writeText(sql);
  };

  return (
    <div className="p-6">
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2">
          <div className="bg-white dark:bg-secondary-800 p-6 rounded-lg shadow border border-secondary-200 dark:border-secondary-700">
            <div className="flex justify-between mb-4">
              <div className="flex space-x-2">
                <button
                  onClick={executeQuery}
                  disabled={loading || !sql.trim()}
                  className="px-4 py-2 bg-primary-600 hover:bg-primary-700 text-white rounded-md font-medium flex items-center disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5 mr-2" viewBox="0 0 20 20" fill="currentColor">
                    <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM9.555 7.168A1 1 0 008 8v4a1 1 0 001.555.832l3-2a1 1 0 000-1.664l-3-2z" clipRule="evenodd" />
                  </svg>
                  Run Query
                </button>
                <button
                  onClick={() => setSaveDialogOpen(true)}
                  disabled={!sql.trim()}
                  className="px-4 py-2 border border-secondary-300 dark:border-secondary-600 bg-white dark:bg-secondary-800 hover:bg-secondary-50 dark:hover:bg-secondary-700 rounded-md font-medium text-secondary-700 dark:text-secondary-300 flex items-center disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5 mr-2" viewBox="0 0 20 20" fill="currentColor">
                    <path d="M5 4a2 2 0 012-2h6a2 2 0 012 2v14l-5-2.5L5 18V4z" />
                  </svg>
                  Save
                </button>
              </div>
              <div className="flex space-x-2">
                <button
                  onClick={handleCopyToClipboard}
                  disabled={!sql.trim()}
                  className="p-2 text-secondary-500 hover:text-secondary-700 dark:text-secondary-400 dark:hover:text-secondary-200 disabled:opacity-50 disabled:cursor-not-allowed"
                  title="Copy to Clipboard"
                >
                  <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5" viewBox="0 0 20 20" fill="currentColor">
                    <path d="M8 3a1 1 0 011-1h2a1 1 0 110 2H9a1 1 0 01-1-1z" />
                    <path d="M6 3a2 2 0 00-2 2v11a2 2 0 002 2h8a2 2 0 002-2V5a2 2 0 00-2-2 3 3 0 01-3 3H9a3 3 0 01-3-3z" />
                  </svg>
                </button>
                <button
                  onClick={handleClearEditor}
                  disabled={!sql.trim()}
                  className="p-2 text-secondary-500 hover:text-secondary-700 dark:text-secondary-400 dark:hover:text-secondary-200 disabled:opacity-50 disabled:cursor-not-allowed"
                  title="Clear Editor"
                >
                  <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5" viewBox="0 0 20 20" fill="currentColor">
                    <path fillRule="evenodd" d="M9 2a1 1 0 00-.894.553L7.382 4H4a1 1 0 000 2v10a2 2 0 002 2h8a2 2 0 002-2V6a1 1 0 100-2h-3.382l-.724-1.447A1 1 0 0011 2H9zM7 8a1 1 0 012 0v6a1 1 0 11-2 0V8zm5-1a1 1 0 00-1 1v6a1 1 0 102 0V8a1 1 0 00-1-1z" clipRule="evenodd" />
                  </svg>
                </button>
              </div>
            </div>

            <SqlCodeEditor 
              value={sql} 
              onChange={setSql} 
            />

            {loading ? (
              <div className="flex justify-center items-center py-10">
                <div className="animate-spin rounded-full h-10 w-10 border-b-2 border-primary-600"></div>
              </div>
            ) : error ? (
              <div className="mt-4 p-4 bg-error-50 dark:bg-error-900/30 text-error-600 dark:text-error-400 rounded-md">
                <div className="font-medium">Error Executing Query</div>
                <div>{error}</div>
              </div>
            ) : (
              <SqlResultsTable results={results} />
            )}
          </div>
        </div>

        <div className="lg:col-span-1">
          <div className="bg-white dark:bg-secondary-800 rounded-lg shadow border border-secondary-200 dark:border-secondary-700 overflow-hidden">
            <div className="flex border-b border-secondary-200 dark:border-secondary-700">
              <button 
                className={`flex-1 py-3 px-4 text-center font-medium ${
                  activeTab === 'snippets'
                    ? 'text-primary-600 border-b-2 border-primary-600'
                    : 'text-secondary-500 dark:text-secondary-400 hover:text-secondary-700 dark:hover:text-secondary-300'
                }`}
                onClick={() => setActiveTab('snippets')}
              >
                <div className="flex items-center justify-center">
                  <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5 mr-2" viewBox="0 0 20 20" fill="currentColor">
                    <path d="M5 4a2 2 0 012-2h6a2 2 0 012 2v14l-5-2.5L5 18V4z" />
                  </svg>
                  Snippets
                </div>
              </button>
              <button 
                className={`flex-1 py-3 px-4 text-center font-medium ${
                  activeTab === 'history'
                    ? 'text-primary-600 border-b-2 border-primary-600'
                    : 'text-secondary-500 dark:text-secondary-400 hover:text-secondary-700 dark:hover:text-secondary-300'
                }`}
                onClick={() => setActiveTab('history')}
              >
                <div className="flex items-center justify-center">
                  <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5 mr-2" viewBox="0 0 20 20" fill="currentColor">
                    <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm1-12a1 1 0 10-2 0v4a1 1 0 00.293.707l2.828 2.829a1 1 0 101.415-1.415L11 9.586V6z" clipRule="evenodd" />
                  </svg>
                  History
                </div>
              </button>
            </div>

            <div className="p-4 h-[600px] overflow-y-auto">
              {activeTab === 'snippets' ? (
                <SqlSnippetsList 
                  snippets={snippets} 
                  loading={loadingSnippets} 
                  onSnippetClick={handleSnippetClick} 
                />
              ) : (
                <SqlHistoryList 
                  history={history} 
                  loading={loadingHistory} 
                  onHistoryClick={handleHistoryClick} 
                />
              )}
            </div>
          </div>
        </div>
      </div>
      
      <SaveSnippetDialog 
        isOpen={saveDialogOpen}
        onClose={() => setSaveDialogOpen(false)}
        onSave={handleSaveSnippet}
      />
    </div>
  );
};

export default SqlEditor; 