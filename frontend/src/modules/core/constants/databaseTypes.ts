// PostgreSQL and SQLite compatible data types
export const DATA_TYPES = [
  'bigint',
  'boolean',
  'character varying',
  'date',
  'double precision',
  'integer',
  'json',
  'jsonb',
  'numeric',
  'real',
  'smallint',
  'text',
  'time',
  'timestamp',
  'timestamp with time zone',
  'uuid',
  // SQLite compatible types
  'INTEGER',
  'TEXT',
  'REAL',
  'NUMERIC',
  'BOOLEAN',
  'DATE',
  'TIMESTAMP',
  'JSON'
];

// Group data types for type-specific operations
export const CHARACTER_TYPES = [
  'character varying',
  'varchar',
  'char',
  'VARCHAR',
  'CHAR',
  'text',
  'TEXT'
];

export const NUMERIC_TYPES = [
  'numeric',
  'decimal',
  'NUMERIC',
  'DECIMAL',
  'double precision',
  'real'
];

// System tables that should be hidden from regular users
export const SYSTEM_TABLES = [
  'alembic_version',
  'buckets',
  'files',
  'roles',
  'sql_history',
  'sql_snippets',
  'users',
  'functions',
  'function_versions',
  'function_env_vars',
  'refresh_tokens'
]; 