import { SYSTEM_TABLES } from '../modules/core/constants/databaseTypes';
import { getAllTables, Table } from './tableService';
import sqlService from './sqlService';

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
  const allTables: Table[] = await getAllTables();
  const dynamicNames = allTables.map((t) => t.name);
  const includeNames = Array.from(new Set<string>([...dynamicNames, 'users', 'buckets', 'files']));

  // Helper to safely quote identifiers for IN list
  const quoteList = (names: string[]) => names.map((n) => `'${n.replace(/'/g, "''")}'`);
  const inList = quoteList(includeNames).join(', ');

  // Queries to introspect columns and foreign keys
  const columnsQuery = `
    SELECT 
      c.table_name,
      c.column_name,
      c.data_type,
      c.column_default,
      EXISTS (
        SELECT 1
        FROM information_schema.table_constraints tc
        JOIN information_schema.key_column_usage kcu
          ON tc.constraint_name = kcu.constraint_name
         AND tc.table_schema = kcu.table_schema
        WHERE tc.constraint_type = 'PRIMARY KEY'
          AND tc.table_name = c.table_name
          AND kcu.column_name = c.column_name
      ) AS is_primary_key
    FROM information_schema.columns c
    WHERE c.table_schema = 'public'
      AND c.table_name IN (${inList})
    ORDER BY c.table_name, c.ordinal_position
  `;

  const fksQuery = `
    SELECT 
      tc.table_name      AS source_table,
      kcu.column_name    AS source_column,
      ccu.table_name     AS target_table,
      ccu.column_name    AS target_column
    FROM information_schema.table_constraints tc
    JOIN information_schema.key_column_usage kcu
      ON tc.constraint_name = kcu.constraint_name
     AND tc.table_schema = kcu.table_schema
    JOIN information_schema.constraint_column_usage ccu
      ON ccu.constraint_name = tc.constraint_name
     AND ccu.table_schema = tc.table_schema
    WHERE tc.constraint_type = 'FOREIGN KEY'
      AND tc.table_schema = 'public'
      AND tc.table_name IN (${inList})
      AND ccu.table_name IN (${inList})
  `;

  try {
    const [colsRes, fksRes] = await Promise.all([
      sqlService.executeQuery(columnsQuery),
      sqlService.executeQuery(fksQuery),
    ]);

    const cols = (colsRes.data || []) as Array<{
      table_name: string;
      column_name: string;
      data_type: string;
      column_default?: string | null;
      is_primary_key: boolean;
    }>;

    const fkRows = (fksRes.data || []) as Array<{
      source_table: string;
      source_column: string;
      target_table: string;
      target_column: string;
    }>;

    // Group columns by table
    const byTable = new Map<string, SchemaColumn[]>();
    const pkByTable = new Map<string, string[]>();
    cols.forEach((r) => {
      const list = byTable.get(r.table_name) || [];
      list.push({
        column_name: r.column_name,
        data_type: r.data_type,
        column_default: r.column_default || undefined,
        is_primary_key: !!r.is_primary_key,
      });
      byTable.set(r.table_name, list);
      if (r.is_primary_key) {
        const pkList = pkByTable.get(r.table_name) || [];
        pkList.push(r.column_name);
        pkByTable.set(r.table_name, pkList);
      }
    });

    // Build nodes (only for tables we included and have columns for)
    const nodes: SchemaNode[] = includeNames
      .filter((t) => byTable.has(t))
      .map((t) => ({
        id: t,
        label: t,
        columns: byTable.get(t) || [],
        primary_keys: pkByTable.get(t) || [],
        foreignKeys: [],
      }));

    // Build edges from foreign key rows
    const edges: SchemaEdge[] = fkRows.map((fk, idx) => ({
      id: `${fk.source_table}.${fk.source_column}->${fk.target_table}.${fk.target_column}-${idx}`,
      source: fk.source_table,
      target: fk.target_table,
      source_column: fk.source_column,
      target_column: fk.target_column,
    }));

    // Mark node foreign key columns for UI
    const nodeMap = new Map(nodes.map((n) => [n.id, n] as const));
    edges.forEach((e) => {
      const src = nodeMap.get(e.source);
      if (src) {
        src.foreignKeys = src.foreignKeys || [];
        if (!src.foreignKeys.includes(e.source_column)) src.foreignKeys.push(e.source_column);
      }
    });

    return { nodes, edges };
  } catch (e) {
    throw e;
  }
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