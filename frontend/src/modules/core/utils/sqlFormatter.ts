/**
 * Simple SQL formatting utility that adds basic highlighting
 * In a production app, you might want to use a proper SQL formatter library
 */
export const formatSql = (sql: string): string => {
  if (!sql) return '';
  
  // Very simple formatting - a robust solution would use a proper SQL parser
  return sql.trim();
};

/**
 * Format cell values for display in tables
 */
export const formatCellValue = (value: any): string => {
  if (value === null || value === undefined) {
    return 'null';
  }

  if (typeof value === 'object') {
    return JSON.stringify(value);
  }

  if (typeof value === 'boolean') {
    return value ? 'true' : 'false';
  }

  return value.toString();
}; 