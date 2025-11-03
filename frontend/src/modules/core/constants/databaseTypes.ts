// PostgreSQL data types supported by SelfDB
// UUID is the default and recommended type for primary keys
export const DATA_TYPES = [
  // Basic types
  'uuid',
  'text',
  'integer',
  'bigint',
  'boolean',
  'character varying',
  'varchar',
  'character',
  'char',
  'name',

  // Numeric types
  'smallint',
  'int2',
  'int',
  'int4',
  'int8',
  'real',
  'float4',
  'double precision',
  'float8',
  'numeric',
  'decimal',

  // Serial types
  'serial',
  'serial2',
  'serial4',
  'bigserial',
  'serial8',
  'smallserial',

  // Date/Time types
  'date',
  'time',
  'time without time zone',
  'timetz',
  'time with time zone',
  'timestamp',
  'timestamp without time zone',
  'timestamptz',
  'timestamp with time zone',

  // JSON types
  'json',
  'jsonb',

  // Special types
  'interval',
  'money',
  'bytea',

  // Network types
  'inet',
  'cidr',

  // MAC address types
  'macaddr',
  'macaddr8',

  // Bit string types
  'bit',
  'bit varying',
  'varbit',

  // Geometric types
  'point',
  'circle',
  'box',
  'lseg',
  'line',
  'path',
  'polygon',

  // Array types (base types with [] suffix will be handled dynamically)
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
  'refresh_tokens',
  'cors_origins'
]; 