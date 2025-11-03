import api from './api';
import { SYSTEM_TABLES } from '../modules/core/constants/databaseTypes';

// Column definition matching backend API
export interface Column {
  name: string;
  type: string;
  nullable?: boolean;
  unique?: boolean;
  default?: any;
  primary_key?: boolean;
}

// Table schema definition
export interface TableSchema {
  columns: Column[];
  indexes?: Array<{
    name: string;
    columns: string[];
    unique?: boolean;
  }>;
}

// Table definition matching backend API
export interface Table {
  name: string;
  description?: string;
  public?: boolean;
  owner_id?: string;
  schema?: TableSchema;
  row_count?: number;
  created_at?: string;
  updated_at?: string;
  metadata?: any;
}

// Table data response matching backend API
export interface TableDataResponse {
  data: any[];
  metadata: {
    total_count: number;
    page: number;
    page_size: number;
    total_pages: number;
  };
}

// Create table request matching backend API
export interface CreateTableRequest {
  name: string;
  description?: string;
  public?: boolean;
  schema: TableSchema;
  metadata?: any;
}

// Update table request matching backend API
export interface UpdateTableRequest {
  new_name?: string;
  description?: string;
  public?: boolean;
}

// Column definition for add/update operations
export interface ColumnDefinition {
  name: string;
  type: string;
  nullable?: boolean;
  unique?: boolean;
  default?: any;
  primary_key?: boolean;
}

// Update column request
export interface UpdateColumnRequest {
  new_name?: string;
  type?: string;
  nullable?: boolean;
  default?: any;
}

// Check if a table is a system table
export const isSystemTable = (tableName: string): boolean => {
  return SYSTEM_TABLES.includes(tableName);
};

// Get all tables
export const getUserTables = async (): Promise<Table[]> => {
  const response = await api.get('/tables');
  // Filter out system tables
  return response.data.filter((table: Table) => !isSystemTable(table.name));
};

// Get all tables including system tables (for admin purposes)
export const getAllTables = async (): Promise<Table[]> => {
  const response = await api.get('/tables');
  return response.data;
};

// Alias for getUserTables for consistency with other services
export const getTables = getUserTables;

// Get a specific table by name
export const getTable = async (tableName: string): Promise<Table> => {
  const response = await api.get(`/tables/${tableName}`);
  return response.data;
};

// Get table data with pagination and filtering
export const getTableData = async (
  tableName: string,
  page = 1,
  pageSize = 100,
  orderBy: string | null = null,
  filterColumn: string | null = null,
  filterValue: string | null = null
): Promise<TableDataResponse> => {
  const params: Record<string, any> = {
    page,
    page_size: pageSize,
  };

  if (orderBy) params.order_by = orderBy;
  if (filterColumn && filterValue !== null && filterValue !== undefined) {
    params.filter_column = filterColumn;
    params.filter_value = filterValue;
  }

  const response = await api.get(`/tables/${tableName}/data`, { params });
  return response.data;
};

// Create a new table
export const createTable = async (tableData: CreateTableRequest) => {
  const response = await api.post('/tables', tableData);
  return response.data;
};

// Insert data into a table
export const insertTableData = async (tableName: string, data: any) => {
  const response = await api.post(`/tables/${tableName}/data`, data);
  return response.data;
};

// Update a row in a table
export const updateTableData = async (tableName: string, id: string | number, idColumn: string, data: any) => {
  const response = await api.put(`/tables/${tableName}/data/${id}?id_column=${idColumn}`, data);
  return response.data;
};

// Delete a row from a table
export const deleteTableData = async (tableName: string, id: string | number, idColumn: string) => {
  const response = await api.delete(`/tables/${tableName}/data/${id}?id_column=${idColumn}`);
  return response.data;
};

// Get SQL creation script for a table
export const getTableSql = async (tableName: string) => {
  const response = await api.get(`/tables/${tableName}/sql`);
  return response.data;
};

// Delete an entire table
export const deleteTable = async (tableName: string) => {
  const response = await api.delete(`/tables/${tableName}`);
  return response.data;
};

// Add a column to a table
export const addColumn = async (tableName: string, columnData: ColumnDefinition) => {
  const response = await api.post(`/tables/${tableName}/columns`, columnData);
  return response.data;
};

// Update a column in a table
export const updateColumn = async (tableName: string, columnName: string, columnData: UpdateColumnRequest) => {
  const response = await api.put(`/tables/${tableName}/columns/${columnName}`, columnData);
  return response.data;
};

// Delete a column from a table
export const deleteColumn = async (tableName: string, columnName: string) => {
  const response = await api.delete(`/tables/${tableName}/columns/${columnName}`);
  return response.data;
};

// Update table properties (name and description)
export const updateTable = async (tableName: string, data: UpdateTableRequest) => {
  const response = await api.put(`/tables/${tableName}`, data);
  return response.data;
};   

// Check if a table has foreign key references
export const hasTableForeignKeyReferences = async (_tableName: string): Promise<boolean> => {
  // Note: This function may need to be updated based on the new backend API
  // For now, return false as foreign key checking is not implemented in the current API
  console.warn('hasTableForeignKeyReferences not implemented for new API');
  return false;
}; 