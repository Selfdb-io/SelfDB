"""SQL Service for executing PostgreSQL queries with security and history tracking."""

import re
import time
import uuid
import json
import logging
from typing import List, Optional, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field

from shared.database.connection_manager import DatabaseConnectionManager

logger = logging.getLogger(__name__)


class SqlExecutionResult(BaseModel):
    """Result of a SQL query execution."""
    success: bool
    is_read_only: bool
    execution_time: float
    row_count: Optional[int] = None
    columns: Optional[List[str]] = None
    data: Optional[List[Dict[str, Any]]] = None
    message: Optional[str] = None
    error: Optional[str] = None
    operations_summary: Optional[Dict[str, Any]] = None  # Summary of DDL operations


class QueryHistory(BaseModel):
    """Query execution history entry."""
    id: str
    query: str
    is_read_only: bool
    execution_time: float
    row_count: int
    error: Optional[str] = None
    executed_at: datetime
    user_id: str


class SqlSnippet(BaseModel):
    """Saved SQL snippet."""
    id: str
    name: str
    sql_code: str
    description: Optional[str] = None
    is_shared: bool = False
    created_at: datetime
    created_by: str


class SqlSnippetCreate(BaseModel):
    """Request model for creating a SQL snippet."""
    name: str = Field(..., min_length=1, max_length=100)
    sql_code: str = Field(..., min_length=1, max_length=100000)
    description: Optional[str] = None
    is_shared: bool = False


class SecurityError(Exception):
    """Exception raised for security violations."""
    pass


class SqlService:
    """Service for executing SQL queries with security and history tracking."""
    
    def __init__(self, database_manager: DatabaseConnectionManager):
        self.database_manager = database_manager
        # In-memory storage for testing (in production, this would be database-backed)
        self._query_history: List[QueryHistory] = []
        self._snippets: List[SqlSnippet] = []
        
        # Dangerous operation patterns
        self._dangerous_patterns = [
            r'\bdrop\s+database\b',
            r'\balter\s+system\b',
            r'\bcreate\s+role\b',
            r'\bdrop\s+role\b',
            r'\bcreate\s+user\b',
            r'\bdrop\s+user\b',
            r'\bset\s+role\b',
            r'\bpg_terminate_backend\b',
            r'\bcopy\s+.*\b(from|to)\b.*(program|stdin)',
        ]

    async def execute_query(
        self,
        query: str,
        user_id: str,
        params: Optional[Dict[str, Any]] = None
    ) -> SqlExecutionResult:
        """Execute a single SQL query."""
        start_time = time.time()
        
        try:
            # Validate query security first
            await self._validate_query_security(query)
            
            # Determine if read-only
            is_read_only = await self._is_read_only_query(query)
            
            # Execute the query
            operations_summary = None
            async with self.database_manager.acquire() as conn:
                if is_read_only:
                    # For SELECT queries, fetch data
                    result = await conn.fetch(query)
                    if result:
                        data = [dict(record) for record in result]
                    else:
                        data = []
                else:
                    # For DDL/DML queries, execute and get status
                    status = await conn.execute(query)
                    
                    # Auto-register tables created via CREATE TABLE
                    # Check query text for CREATE TABLE (handles multi-statement scripts)
                    registered_tables = []
                    if re.search(r'\bCREATE\s+TABLE\b', query, re.IGNORECASE):
                        registered_tables = await self._register_tables_from_query(query, user_id, conn)
                    
                    # Auto-cleanup metadata for dropped tables
                    if re.search(r'\bDROP\s+TABLE\b', query, re.IGNORECASE):
                        await self._cleanup_dropped_tables_metadata(query, conn)
                    
                    # Analyze DDL operations and return detailed information
                    data, operations_summary = await self._analyze_ddl_operations(
                        query, status, conn, registered_tables
                    )

            execution_time = time.time() - start_time
            
            # Calculate result metadata
            row_count = len(data) if data else 0
            columns = list(data[0].keys()) if data and len(data) > 0 else None
            
            # Generate informative message
            if operations_summary:
                message = self._generate_ddl_message(operations_summary, execution_time)
            else:
                message = f"Query executed successfully in {execution_time:.2f}s"
            
            return SqlExecutionResult(
                success=True,
                is_read_only=is_read_only,
                execution_time=execution_time,
                row_count=row_count,
                data=data,
                columns=columns,
                message=message,
                operations_summary=operations_summary
            )
        except SecurityError as e:
            # Re-raise security errors
            raise
        except Exception as e:
            execution_time = time.time() - start_time
            return SqlExecutionResult(
                success=False,
                is_read_only=await self._is_read_only_query(query),
                execution_time=execution_time,
                error=str(e),
                message="Query execution failed"
            )

    async def execute_script(self, script: str, user_id: str) -> List[SqlExecutionResult]:
        """Execute a multi-statement SQL script."""
        statements = await self._parse_multi_statement_script(script)
        results = []
        
        for statement in statements:
            if statement.strip():
                result = await self.execute_query(statement, user_id)
                results.append(result)
        
        return results

    async def save_query_history(
        self,
        query: str,
        result: SqlExecutionResult,
        user_id: str
    ):
        """Save query execution to history."""
        history_entry = QueryHistory(
            id=str(uuid.uuid4()),
            query=query,
            is_read_only=result.is_read_only,
            execution_time=result.execution_time,
            row_count=result.row_count or 0,
            error=result.error,
            executed_at=datetime.now(),
            user_id=user_id
        )
        self._query_history.append(history_entry)

    async def get_query_history(self, user_id: str, limit: int = 100) -> List[QueryHistory]:
        """Get query execution history for a user."""
        user_history = [h for h in self._query_history if h.user_id == user_id]
        # Sort by most recent first
        user_history.sort(key=lambda x: x.executed_at, reverse=True)
        return user_history[:limit]

    async def save_snippet(self, snippet: SqlSnippetCreate, user_id: str) -> SqlSnippet:
        """Save a new SQL snippet."""
        snippet_obj = SqlSnippet(
            id=str(uuid.uuid4()),
            name=snippet.name,
            sql_code=snippet.sql_code,
            description=snippet.description,
            is_shared=snippet.is_shared,
            created_at=datetime.now(),
            created_by=user_id
        )
        self._snippets.append(snippet_obj)
        return snippet_obj

    async def get_snippets(self, user_id: str) -> List[SqlSnippet]:
        """Get all snippets for a user."""
        user_snippets = [s for s in self._snippets if s.created_by == user_id]
        return user_snippets

    async def delete_snippet(self, snippet_id: str, user_id: str):
        """Delete a SQL snippet."""
        for i, snippet in enumerate(self._snippets):
            if snippet.id == snippet_id and snippet.created_by == user_id:
                del self._snippets[i]
                return
        raise Exception(f"Snippet {snippet_id} not found or access denied")

    async def _is_read_only_query(self, query: str) -> bool:
        """Determine if a query is read-only."""
        query_lower = query.strip().lower()
        
        # Read-only operations
        read_only_keywords = ['select', 'show', 'explain', 'describe']
        
        # Check first keyword
        first_keyword = query_lower.split()[0] if query_lower else ''
        
        if first_keyword in read_only_keywords:
            return True
        
        # WITH statements can be read-only if they contain SELECT
        if first_keyword == 'with' and 'select' in query_lower:
            return True
        
        return False

    async def _validate_query_security(self, query: str) -> None:
        """Validate query security rules."""
        query_lower = query.lower()
        
        # Check for dangerous patterns
        for pattern in self._dangerous_patterns:
            if re.search(pattern, query_lower, re.IGNORECASE):
                raise SecurityError(f"Dangerous SQL operation detected: {pattern}")

    async def _parse_multi_statement_script(self, script: str) -> List[str]:
        """Parse a multi-statement script into individual statements."""
        statements = []
        current_statement = ""
        in_string = False
        string_char = None
        
        lines = script.split('\n')
        
        for line in lines:
            # Remove single-line comments
            if '--' in line and not in_string:
                comment_pos = line.find('--')
                line = line[:comment_pos]
            
            # Simple string literal tracking
            i = 0
            while i < len(line):
                char = line[i]
                
                if char in ("'", '"') and (i == 0 or line[i-1] != '\\'):
                    if not in_string:
                        in_string = True
                        string_char = char
                    elif char == string_char:
                        in_string = False
                        string_char = None
                
                i += 1
            
            current_statement += line + '\n'
            
            # If line ends with semicolon and we're not in a string
            if line.strip().endswith(';') and not in_string:
                stmt = current_statement.strip()
                if stmt:
                    # Remove trailing semicolon
                    if stmt.endswith(';'):
                        stmt = stmt[:-1].strip()
                    if stmt:
                        statements.append(stmt)
                current_statement = ""
        
        # Add any remaining statement
        if current_statement.strip():
            stmt = current_statement.strip()
            if stmt.endswith(';'):
                stmt = stmt[:-1].strip()
            if stmt:
                statements.append(stmt)
        
        # Remove block comments
        cleaned_statements = []
        for stmt in statements:
            # Remove /* */ comments
            stmt = re.sub(r'/\*.*?\*/', '', stmt, flags=re.DOTALL)
            stmt = stmt.strip()
            if stmt:
                cleaned_statements.append(stmt)
        
        return cleaned_statements

    async def _introspect_table_schema(self, table_name: str, conn) -> Dict[str, Any]:
        """Introspect table schema from information_schema."""
        # Get column definitions
        columns_query = """
            SELECT 
                column_name,
                data_type,
                character_maximum_length,
                is_nullable,
                column_default
            FROM information_schema.columns
            WHERE table_name = $1 AND table_schema = 'public'
            ORDER BY ordinal_position
        """
        columns_rows = await conn.fetch(columns_query, table_name)
        
        # Get primary key columns
        pk_query = """
            SELECT a.attname
            FROM pg_index i
            JOIN pg_attribute a ON a.attrelid = i.indrelid AND a.attnum = ANY(i.indkey)
            WHERE i.indrelid = $1::regclass AND i.indisprimary
        """
        try:
            pk_rows = await conn.fetch(pk_query, table_name)
            pk_columns = {row['attname'] for row in pk_rows}
        except:
            pk_columns = set()
        
        # Build schema definition
        columns = []
        for col in columns_rows:
            column_def = {
                'name': col['column_name'],
                'type': col['data_type'],
                'nullable': col['is_nullable'] == 'YES',
                'primary_key': col['column_name'] in pk_columns
            }
            
            if col['column_default']:
                column_def['default'] = col['column_default']
            
            if col['character_maximum_length']:
                column_def['max_length'] = col['character_maximum_length']
            
            columns.append(column_def)
        
        return {'columns': columns, 'indexes': []}

    async def _register_tables_from_query(self, query: str, user_id: str, conn) -> List[str]:
        """Register all tables created in a query (handles multi-statement scripts).
        
        Returns:
            List of successfully registered table names
        """
        registered = []
        try:
            # Extract all table names from CREATE TABLE statements
            # Pattern matches: CREATE TABLE [IF NOT EXISTS] table_name
            pattern = r'\bCREATE\s+TABLE\s+(?:IF\s+NOT\s+EXISTS\s+)?["]?([a-zA-Z_][a-zA-Z0-9_]*)["]?'
            matches = re.findall(pattern, query, re.IGNORECASE)
            
            if not matches:
                logger.debug("No CREATE TABLE statements found in query")
                return registered
            
            logger.info(f"Found {len(matches)} CREATE TABLE statement(s): {matches}")
            
            # Register each table
            for table_name in matches:
                success = await self._register_table_metadata(table_name, user_id, conn, query)
                if success:
                    registered.append(table_name)
                
        except Exception as e:
            # Log but don't fail the query execution
            logger.error(f"Failed to register tables from query: {e}")
            # Don't raise - metadata registration failure shouldn't fail the query
        
        return registered

    async def _cleanup_dropped_tables_metadata(self, query: str, conn):
        """Remove metadata for tables that were dropped via DROP TABLE.
        
        This ensures the tables metadata stays in sync with actual PostgreSQL tables.
        """
        try:
            # Extract all table names from DROP TABLE statements
            # Pattern matches: DROP TABLE [IF EXISTS] table_name
            pattern = r'\bDROP\s+TABLE\s+(?:IF\s+EXISTS\s+)?["]?([a-zA-Z_][a-zA-Z0-9_]*)["]?'
            matches = re.findall(pattern, query, re.IGNORECASE)
            
            if not matches:
                logger.debug("No DROP TABLE statements found in query")
                return
            
            logger.info(f"Found {len(matches)} DROP TABLE statement(s): {matches}")
            
            # Remove metadata for each dropped table
            for table_name in matches:
                deleted_count = await conn.fetchval(
                    "DELETE FROM tables WHERE name = $1 RETURNING 1",
                    table_name
                )
                
                if deleted_count:
                    logger.info(f"Removed metadata for dropped table '{table_name}'")
                else:
                    logger.debug(f"No metadata found for table '{table_name}' (may not have been registered)")
                
        except Exception as e:
            # Log but don't fail the query execution
            logger.error(f"Failed to cleanup dropped tables metadata: {e}")
            # Don't raise - metadata cleanup failure shouldn't fail the query

    async def _register_table_metadata(self, table_name: str, user_id: str, conn, creation_sql: str) -> bool:
        """Register a single table in the tables metadata.
        
        Returns:
            True if successfully registered, False otherwise
        """
        try:
            # Check if table metadata already exists
            existing = await conn.fetchval(
                "SELECT name FROM tables WHERE name = $1",
                table_name
            )
            if existing:
                logger.debug(f"Table '{table_name}' already registered in metadata")
                return False
            
            # Verify table exists in database
            table_exists = await conn.fetchval(
                """
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_schema = 'public' 
                    AND table_name = $1
                )
                """,
                table_name
            )
            
            if not table_exists:
                logger.warning(f"Table '{table_name}' not found in database, skipping registration")
                return False
            
            # Introspect the table schema
            schema = await self._introspect_table_schema(table_name, conn)
            
            # Insert into tables metadata
            await conn.execute(
                """
                INSERT INTO tables (name, schema, public, owner_id, description, metadata, row_count)
                VALUES ($1, $2::jsonb, $3, $4, $5, $6::jsonb, 0)
                ON CONFLICT (name) DO NOTHING
                """,
                table_name,
                json.dumps(schema),
                False,  # Default to private
                user_id,
                f"Table created via SQL Editor",
                json.dumps({'created_via': 'sql_editor', 'creation_sql': creation_sql})
            )
            
            logger.info(f"Successfully registered table '{table_name}' in metadata for user {user_id}")
            return True
            
        except Exception as e:
            # Log but don't fail the query execution
            logger.error(f"Failed to register table '{table_name}' metadata: {e}")
            # Don't raise - metadata registration failure shouldn't fail the query
            return False

    async def _analyze_ddl_operations(
        self, 
        query: str, 
        status: str, 
        conn, 
        registered_tables: List[str]
    ) -> tuple[List[Dict[str, Any]], Optional[Dict[str, Any]]]:
        """Analyze DDL/DML operations and return detailed information in table format.
        
        Returns:
            Tuple of (data rows, operations summary)
        """
        try:
            operations = []
            summary_counts = {}
            
            # Detect CREATE TABLE operations
            create_table_pattern = r'\bCREATE\s+TABLE\s+(?:IF\s+NOT\s+EXISTS\s+)?["]?([a-zA-Z_][a-zA-Z0-9_]*)["]?'
            table_matches = re.findall(create_table_pattern, query, re.IGNORECASE)
            
            for table_name in table_matches:
                table_info = await self._get_table_details(table_name, conn)
                if table_info:
                    operations.append({
                        'Operation': 'CREATE',
                        'Object Type': 'TABLE',
                        'Object Name': table_name,
                        'Details': table_info['details'],
                        'Status': '✅ Registered in metadata' if table_name in registered_tables else '⚠️ Created (not registered)'
                    })
            if table_matches:
                summary_counts['tables_created'] = len(table_matches)
                summary_counts['tables_registered'] = len(registered_tables)
            
            # Detect CREATE INDEX operations
            create_index_pattern = r'\bCREATE\s+(?:UNIQUE\s+)?INDEX\s+(?:IF\s+NOT\s+EXISTS\s+)?["]?([a-zA-Z_][a-zA-Z0-9_]*)["]?\s+ON\s+["]?([a-zA-Z_][a-zA-Z0-9_]*)["]?'
            index_matches = re.findall(create_index_pattern, query, re.IGNORECASE)
            
            for index_name, table_name in index_matches:
                index_info = await self._get_index_details(index_name, table_name, conn)
                if index_info:
                    operations.append({
                        'Operation': 'CREATE',
                        'Object Type': 'INDEX',
                        'Object Name': index_name,
                        'Details': index_info['details'],
                        'Status': '✅ Created'
                    })
            if index_matches:
                summary_counts['indexes_created'] = len(index_matches)
            
            # Detect INSERT operations
            insert_pattern = r'\bINSERT\s+INTO\s+["]?([a-zA-Z_][a-zA-Z0-9_]*)["]?'
            insert_matches = re.findall(insert_pattern, query, re.IGNORECASE)
            if insert_matches and status:
                # Extract row count from status (e.g., "INSERT 0 5" means 5 rows)
                row_count = self._extract_row_count_from_status(status)
                for table_name in set(insert_matches):  # Use set to avoid duplicates
                    operations.append({
                        'Operation': 'INSERT',
                        'Object Type': 'TABLE',
                        'Object Name': table_name,
                        'Details': f"{row_count} row{'s' if row_count != 1 else ''} inserted",
                        'Status': '✅ Inserted'
                    })
                summary_counts['rows_inserted'] = row_count
            
            # Detect UPDATE operations
            update_pattern = r'\bUPDATE\s+["]?([a-zA-Z_][a-zA-Z0-9_]*)["]?'
            update_matches = re.findall(update_pattern, query, re.IGNORECASE)
            if update_matches and status:
                row_count = self._extract_row_count_from_status(status)
                for table_name in set(update_matches):
                    operations.append({
                        'Operation': 'UPDATE',
                        'Object Type': 'TABLE',
                        'Object Name': table_name,
                        'Details': f"{row_count} row{'s' if row_count != 1 else ''} updated",
                        'Status': '✅ Updated'
                    })
                summary_counts['rows_updated'] = row_count
            
            # Detect DELETE operations
            delete_pattern = r'\bDELETE\s+FROM\s+["]?([a-zA-Z_][a-zA-Z0-9_]*)["]?'
            delete_matches = re.findall(delete_pattern, query, re.IGNORECASE)
            if delete_matches and status:
                row_count = self._extract_row_count_from_status(status)
                for table_name in set(delete_matches):
                    operations.append({
                        'Operation': 'DELETE',
                        'Object Type': 'TABLE',
                        'Object Name': table_name,
                        'Details': f"{row_count} row{'s' if row_count != 1 else ''} deleted",
                        'Status': '✅ Deleted'
                    })
                summary_counts['rows_deleted'] = row_count
            
            # Detect ALTER TABLE operations
            alter_table_pattern = r'\bALTER\s+TABLE\s+["]?([a-zA-Z_][a-zA-Z0-9_]*)["]?'
            alter_matches = re.findall(alter_table_pattern, query, re.IGNORECASE)
            if alter_matches:
                for table_name in set(alter_matches):
                    alter_details = self._extract_alter_details(query)
                    operations.append({
                        'Operation': 'ALTER',
                        'Object Type': 'TABLE',
                        'Object Name': table_name,
                        'Details': alter_details,
                        'Status': '✅ Altered'
                    })
                summary_counts['tables_altered'] = len(set(alter_matches))
            
            # Detect DROP TABLE operations
            drop_table_pattern = r'\bDROP\s+TABLE\s+(?:IF\s+EXISTS\s+)?["]?([a-zA-Z_][a-zA-Z0-9_]*)["]?'
            drop_table_matches = re.findall(drop_table_pattern, query, re.IGNORECASE)
            if drop_table_matches:
                cascade = 'CASCADE' in query.upper()
                for table_name in drop_table_matches:
                    operations.append({
                        'Operation': 'DROP',
                        'Object Type': 'TABLE',
                        'Object Name': table_name,
                        'Details': f"Table dropped{' (CASCADE)' if cascade else ''}",
                        'Status': '✅ Dropped'
                    })
                summary_counts['tables_dropped'] = len(drop_table_matches)
            
            # Detect DROP INDEX operations
            drop_index_pattern = r'\bDROP\s+INDEX\s+(?:IF\s+EXISTS\s+)?["]?([a-zA-Z_][a-zA-Z0-9_]*)["]?'
            drop_index_matches = re.findall(drop_index_pattern, query, re.IGNORECASE)
            if drop_index_matches:
                for index_name in drop_index_matches:
                    operations.append({
                        'Operation': 'DROP',
                        'Object Type': 'INDEX',
                        'Object Name': index_name,
                        'Details': 'Index dropped',
                        'Status': '✅ Dropped'
                    })
                summary_counts['indexes_dropped'] = len(drop_index_matches)
            
            # Detect TRUNCATE operations
            truncate_pattern = r'\bTRUNCATE\s+(?:TABLE\s+)?["]?([a-zA-Z_][a-zA-Z0-9_]*)["]?'
            truncate_matches = re.findall(truncate_pattern, query, re.IGNORECASE)
            if truncate_matches:
                for table_name in truncate_matches:
                    operations.append({
                        'Operation': 'TRUNCATE',
                        'Object Type': 'TABLE',
                        'Object Name': table_name,
                        'Details': 'All rows removed',
                        'Status': '✅ Truncated'
                    })
                summary_counts['tables_truncated'] = len(truncate_matches)
            
            # If we found any operations, return structured data
            if operations:
                summary_counts['total_operations'] = len(operations)
                return operations, summary_counts
            
            # Otherwise, return simple status response
            data = [{"status": status}] if status else []
            return data, None
            
        except Exception as e:
            logger.error(f"Failed to analyze operations: {e}")
            # Fallback to simple response
            data = [{"status": status}] if status else []
            return data, None

    async def _get_table_details(self, table_name: str, conn) -> Optional[Dict[str, Any]]:
        """Get detailed information about a table."""
        try:
            # Get column count
            col_count = await conn.fetchval(
                """
                SELECT COUNT(*) 
                FROM information_schema.columns 
                WHERE table_name = $1 AND table_schema = 'public'
                """,
                table_name
            )
            
            # Get primary key columns
            pk_cols = await conn.fetch(
                """
                SELECT a.attname
                FROM pg_index i
                JOIN pg_attribute a ON a.attrelid = i.indrelid AND a.attnum = ANY(i.indkey)
                WHERE i.indrelid = $1::regclass AND i.indisprimary
                """,
                table_name
            )
            pk_count = len(pk_cols)
            
            # Get foreign key count
            fk_count = await conn.fetchval(
                """
                SELECT COUNT(*)
                FROM information_schema.table_constraints
                WHERE table_name = $1 
                  AND table_schema = 'public'
                  AND constraint_type = 'FOREIGN KEY'
                """,
                table_name
            )
            
            # Get check constraint count
            check_count = await conn.fetchval(
                """
                SELECT COUNT(*)
                FROM information_schema.table_constraints
                WHERE table_name = $1 
                  AND table_schema = 'public'
                  AND constraint_type = 'CHECK'
                """,
                table_name
            )
            
            # Build details string
            details_parts = [f"{col_count} columns"]
            if pk_count > 0:
                details_parts.append(f"{pk_count} PK")
            if fk_count > 0:
                details_parts.append(f"{fk_count} FK")
            if check_count > 0:
                details_parts.append(f"{check_count} CHECK")
            
            return {
                'details': ', '.join(details_parts),
                'column_count': col_count,
                'pk_count': pk_count,
                'fk_count': fk_count,
                'check_count': check_count
            }
            
        except Exception as e:
            logger.error(f"Failed to get table details for '{table_name}': {e}")
            return None

    async def _get_index_details(self, index_name: str, table_name: str, conn) -> Optional[Dict[str, Any]]:
        """Get detailed information about an index."""
        try:
            # Get index details
            index_info = await conn.fetchrow(
                """
                SELECT 
                    i.indisunique as is_unique,
                    am.amname as index_type,
                    array_agg(a.attname ORDER BY array_position(i.indkey, a.attnum)) as columns
                FROM pg_index i
                JOIN pg_class c ON c.oid = i.indexrelid
                JOIN pg_am am ON am.oid = c.relam
                JOIN pg_attribute a ON a.attrelid = i.indrelid AND a.attnum = ANY(i.indkey)
                WHERE c.relname = $1
                GROUP BY i.indisunique, am.amname
                """,
                index_name
            )
            
            if index_info:
                unique_str = "UNIQUE " if index_info['is_unique'] else ""
                cols_str = ', '.join(index_info['columns'])
                details = f"{unique_str}on {table_name}({cols_str}) using {index_info['index_type']}"
                
                return {
                    'details': details,
                    'is_unique': index_info['is_unique'],
                    'index_type': index_info['index_type'],
                    'columns': index_info['columns']
                }
            
            return None
            
        except Exception as e:
            logger.error(f"Failed to get index details for '{index_name}': {e}")
            return None

    def _extract_row_count_from_status(self, status: str) -> int:
        """Extract row count from PostgreSQL status message.
        
        Examples:
            "INSERT 0 5" -> 5 rows inserted
            "UPDATE 3" -> 3 rows updated
            "DELETE 10" -> 10 rows deleted
        """
        try:
            parts = status.split()
            if len(parts) >= 3:
                # INSERT format: "INSERT 0 5"
                return int(parts[2])
            elif len(parts) >= 2:
                # UPDATE/DELETE format: "UPDATE 3"
                return int(parts[1])
            return 0
        except (ValueError, IndexError):
            return 0

    def _extract_alter_details(self, query: str) -> str:
        """Extract ALTER TABLE operation details."""
        query_upper = query.upper()
        
        if 'ADD COLUMN' in query_upper or 'ADD ' in query_upper:
            return 'Column added'
        elif 'DROP COLUMN' in query_upper:
            return 'Column dropped'
        elif 'ALTER COLUMN' in query_upper or 'MODIFY COLUMN' in query_upper:
            return 'Column altered'
        elif 'RENAME TO' in query_upper:
            return 'Table renamed'
        elif 'ADD CONSTRAINT' in query_upper:
            return 'Constraint added'
        elif 'DROP CONSTRAINT' in query_upper:
            return 'Constraint dropped'
        else:
            return 'Table structure modified'

    def _generate_ddl_message(self, operations_summary: Dict[str, Any], execution_time: float) -> str:
        """Generate an informative message for DDL/DML operations."""
        parts = []
        
        # DDL operations
        tables_created = operations_summary.get('tables_created', 0)
        indexes_created = operations_summary.get('indexes_created', 0)
        tables_dropped = operations_summary.get('tables_dropped', 0)
        indexes_dropped = operations_summary.get('indexes_dropped', 0)
        tables_altered = operations_summary.get('tables_altered', 0)
        tables_truncated = operations_summary.get('tables_truncated', 0)
        
        # DML operations
        rows_inserted = operations_summary.get('rows_inserted', 0)
        rows_updated = operations_summary.get('rows_updated', 0)
        rows_deleted = operations_summary.get('rows_deleted', 0)
        
        # Build message parts
        if tables_created > 0:
            parts.append(f"{tables_created} table{'s' if tables_created > 1 else ''}")
        if indexes_created > 0:
            parts.append(f"{indexes_created} index{'es' if indexes_created > 1 else ''}")
        
        if parts:
            operation_str = ' and '.join(parts)
            message = f"✅ Created {operation_str} in {execution_time:.2f}s"
            
            registered = operations_summary.get('tables_registered', 0)
            if registered > 0:
                message += f". {registered} table{'s' if registered > 1 else ''} registered in SelfDB."
            
            return message
        
        # DROP operations
        if tables_dropped > 0 or indexes_dropped > 0:
            drop_parts = []
            if tables_dropped > 0:
                drop_parts.append(f"{tables_dropped} table{'s' if tables_dropped > 1 else ''}")
            if indexes_dropped > 0:
                drop_parts.append(f"{indexes_dropped} index{'es' if indexes_dropped > 1 else ''}")
            return f"✅ Dropped {' and '.join(drop_parts)} in {execution_time:.2f}s"
        
        # ALTER operations
        if tables_altered > 0:
            return f"✅ Altered {tables_altered} table{'s' if tables_altered > 1 else ''} in {execution_time:.2f}s"
        
        # TRUNCATE operations
        if tables_truncated > 0:
            return f"✅ Truncated {tables_truncated} table{'s' if tables_truncated > 1 else ''} in {execution_time:.2f}s"
        
        # DML operations
        if rows_inserted > 0:
            return f"✅ Inserted {rows_inserted} row{'s' if rows_inserted != 1 else ''} in {execution_time:.2f}s"
        if rows_updated > 0:
            return f"✅ Updated {rows_updated} row{'s' if rows_updated != 1 else ''} in {execution_time:.2f}s"
        if rows_deleted > 0:
            return f"✅ Deleted {rows_deleted} row{'s' if rows_deleted != 1 else ''} in {execution_time:.2f}s"
        
        # Fallback
        return f"Query executed successfully in {execution_time:.2f}s"
