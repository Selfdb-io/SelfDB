import api from './api';
import { SYSTEM_TABLES } from '../modules/core/constants/databaseTypes';

// Column definition
export interface Column {
  column_name: string;
  data_type: string;
  is_nullable: string;
  column_default: string | null;
  character_maximum_length?: number;
  numeric_precision?: number;
  numeric_scale?: number;
  column_description?: string;
}

// Foreign key definition
export interface ForeignKey {
  column_name: string;
  foreign_table_name: string;
  foreign_column_name: string;
}

// Index definition
export interface Index {
  index_name: string;
  column_name: string;
  is_unique: boolean;
  is_primary: boolean;
}

// Table type definition
export interface Table {
  name: string;
  description?: string;
  column_count: number;
  size: number;
  columns?: Column[];
  primary_keys?: string[];
  foreign_keys?: ForeignKey[];
  indexes?: Index[];
  row_count?: number;
}

// Table data response
export interface TableDataResponse {
  data: any[];
  total?: number; // Direct total (for backwards compatibility)
  page?: number;
  page_size?: number;
  columns?: {
    name: string;
    type: string;
  }[];
  metadata?: {
    total_count?: number;
    total?: number;
    page?: number;
    page_size?: number;
    total_pages?: number;
    columns?: any[];
  };
}

// Check if a table is a system table
export const isSystemTable = (tableName: string): boolean => {
  return SYSTEM_TABLES.includes(tableName);
};

// Get all tables
export const getUserTables = async (): Promise<Table[]> => {
  const response = await api.get('/tables');
  // Filter out all system tables including 'users' table
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
  if (filterColumn && filterValue) {
    params.filter_column = filterColumn;
    params.filter_value = filterValue;
  }

  const response = await api.get(`/tables/${tableName}/data`, { params });
  return response.data;
};

// Create a new table
export const createTable = async (tableData: any) => {
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
export const addColumn = async (tableName: string, columnData: Partial<Column>) => {
  const response = await api.post(`/tables/${tableName}/columns`, columnData);
  return response.data;
};

// Update a column in a table
export const updateColumn = async (tableName: string, columnName: string, columnData: Partial<Column>) => {
  const response = await api.put(`/tables/${tableName}/columns/${columnName}`, columnData);
  return response.data;
};

// Delete a column from a table
export const deleteColumn = async (tableName: string, columnName: string) => {
  const response = await api.delete(`/tables/${tableName}/columns/${columnName}`);
  return response.data;
};

// Update table properties (name and description)
export const updateTable = async (tableName: string, data: { new_name?: string; description?: string }) => {
  const response = await api.put(`/tables/${tableName}`, data);
  return response.data;
};   

// Check if a table has foreign key references
export const hasTableForeignKeyReferences = async (tableName: string): Promise<boolean> => {
  try {
    // Get all tables
    const tables = await getAllTables();
    
    for (const table of tables) {
      if (table.name === tableName) continue;
      
      const tableDetails = table.foreign_keys 
        ? table 
        : await getTable(table.name);
      
      // Check if any foreign key references the target table
      if (tableDetails.foreign_keys && tableDetails.foreign_keys.some(fk => fk.foreign_table_name === tableName)) {
        return true;
      }
    }
    
    return false;
  } catch (error) {
    console.error("Error checking for foreign key references:", error);
    return false;
  }
}; 