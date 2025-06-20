import api from './api';
import { SYSTEM_TABLES } from '../modules/core/constants/databaseTypes';

export interface SchemaNode {
  id: string;
  label: string;
  columns: SchemaColumn[];
  primary_keys?: string[];
  foreignKeys?: string[];
}

export interface SchemaColumn {
  column_name: string;
  data_type: string;
  column_default?: string;
  is_primary_key?: boolean;
}

export interface SchemaEdge {
  id: string;
  source: string;
  target: string;
  source_column: string;
  target_column: string;
}

export interface SchemaData {
  nodes: SchemaNode[];
  edges: SchemaEdge[];
}

/**
 * Fetch schema visualization data
 * @returns Promise with schema visualization data
 */
export const fetchSchemaVisualization = async (): Promise<SchemaData> => {
  const response = await api.get('/schema/visualization');
  return response.data;
};

/**
 * Check if a table is a system table (except for allowed ones)
 * @param tableName Table name to check
 * @returns boolean indicating if it's a system table
 */
export const isSystemTable = (tableName: string, allowedTables: string[] = ['users', 'files', 'buckets']): boolean => {
  const systemPrefixes = ['pg_', 'information_schema'];
  
  // It's a system table if:
  // 1. It's in our SYSTEM_TABLES list AND not in our allowed list
  // 2. It has a system prefix (like pg_ or information_schema)
  return (
    (SYSTEM_TABLES.includes(tableName) && !allowedTables.includes(tableName)) ||
    systemPrefixes.some(prefix => tableName.startsWith(prefix))
  );
};

/**
 * Save schema layout to local storage
 * @param positions Node positions to save
 */
export const saveSchemaLayout = (positions: Record<string, { x: number, y: number }>): void => {
  try {
    localStorage.setItem('schemaNodePositions', JSON.stringify(positions));
  } catch (error) {
    console.error('Error saving schema layout:', error);
  }
};

/**
 * Load schema layout from local storage
 * @returns Saved positions or null if not available
 */
export const loadSchemaLayout = (): Record<string, { x: number, y: number }> | null => {
  try {
    const savedPositions = localStorage.getItem('schemaNodePositions');
    if (savedPositions) {
      return JSON.parse(savedPositions);
    }
  } catch (error) {
    console.error('Error loading saved layout:', error);
  }
  return null;
}; 