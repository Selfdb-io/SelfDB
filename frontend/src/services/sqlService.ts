import api from './api';

// Interfaces
export interface SqlQueryResult {
  success: boolean;
  is_read_only?: boolean;
  execution_time?: number;
  row_count?: number;
  columns?: string[];
  data?: any[];
  message?: string;
  error?: string;
  results?: SqlStatementResult[];
  total_execution_time?: number;
  total_rows_affected?: number;
}

export interface SqlStatementResult {
  statement: string;
  is_read_only: boolean;
  execution_time: number;
  row_count?: number;
  columns?: string[];
  data?: any[];
  message?: string;
}

export interface SqlSnippet {
  id: string | number;
  name: string;
  sql_code: string;
  description?: string;
  is_shared: boolean;
  created_at?: string;
  created_by?: string;
}

export interface SqlHistoryItem {
  id: string | number;
  query: string;
  is_read_only: boolean;
  execution_time: number;
  row_count: number;
  error?: string;
  executed_at: string;
}

const sqlService = {
  // Execute SQL query
  executeQuery: async (query: string): Promise<SqlQueryResult> => {
    try {
      const response = await api.post('/sql/query', { query });
      return response.data;
    } catch (error: any) {
      if (error.response?.data?.detail) {
        throw new Error(error.response.data.detail);
      }
      if (error.response?.data?.error) {
        throw new Error(error.response.data.error);
      }
      throw new Error(error.message || 'Error executing query');
    }
  },

  // Save query to history
  saveQueryToHistory: async (
    query: string, 
    result: SqlQueryResult
  ): Promise<void> => {
    await api.post('/sql/history', {
      query,
      result
    });
  },

  // Fetch query history
  fetchHistory: async (): Promise<SqlHistoryItem[]> => {
    const response = await api.get('/sql/history');
    return response.data.history || [];
  },

  // Fetch saved snippets
  fetchSnippets: async (): Promise<SqlSnippet[]> => {
    const response = await api.get('/sql/snippets');
    return response.data;
  },

  // Save a snippet
  saveSnippet: async (snippet: {
    name: string;
    sql_code: string;
    description?: string;
    is_shared: boolean;
  }): Promise<SqlSnippet> => {
    const response = await api.post('/sql/snippets', snippet);
    return response.data;
  },

  // Delete a snippet
  deleteSnippet: async (id: string | number): Promise<void> => {
    await api.delete(`/sql/snippets/${id}`);
  },
};

export default sqlService; 