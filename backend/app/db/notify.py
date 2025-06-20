from typing import Any, Dict, Optional, List, Union, Literal
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
import json
import logging
import uuid
from datetime import datetime, date, time

logger = logging.getLogger(__name__)


class CustomJSONEncoder(json.JSONEncoder):
    """
    Custom JSON encoder that properly handles UUID objects, datetime objects and other
    non-serializable types.
    """
    def default(self, obj):
        if isinstance(obj, uuid.UUID):
            # Convert UUID objects to strings
            return str(obj)
        elif isinstance(obj, (datetime, date, time)):
            # Convert datetime objects to ISO format strings
            return obj.isoformat()
        # Let the base class handle other types or raise TypeError
        return super().default(obj)

async def emit_table_notification(
    db: AsyncSession,
    table_name: str,
    operation: Literal["INSERT", "UPDATE", "DELETE"],
    data: Optional[Dict[str, Any]] = None,
    old_data: Optional[Dict[str, Any]] = None
) -> None:
    """
    Emit a notification for a table operation.
    
    Args:
        db: Database session
        table_name: Name of the table
        operation: One of "INSERT", "UPDATE", "DELETE"
        data: New data for INSERT/UPDATE operations
        old_data: Old data for UPDATE/DELETE operations
    """
    try:
        payload: Dict[str, Any] = {
            "operation": operation,
            "table": table_name,
        }
        
        if data is not None:
            payload["data"] = data
            
        if old_data is not None:
            payload["old_data"] = old_data
            
        channel = f"{table_name}_changes"
        
        # Use custom encoder to handle UUID objects
        payload_json = json.dumps(payload, cls=CustomJSONEncoder)
        
        await db.execute(
            text(f"SELECT pg_notify(:channel, :payload)"),
            {"channel": channel, "payload": payload_json}
        )
        
        logger.debug(f"Emitted notification on channel {channel}: {payload_json}")
    except Exception as e:
        logger.error(f"Error emitting notification: {e}")

async def ensure_table_trigger_exists(
    db: AsyncSession,
    table_name: str,
    operations: List[Literal["INSERT", "UPDATE", "DELETE"]] = ["INSERT", "UPDATE", "DELETE"]
) -> bool:
    """
    Ensure that a notification trigger exists for the specified table.
    Creates the trigger if it doesn't exist.
    
    Args:
        db: Database session
        table_name: Name of the table
        operations: List of operations to trigger on (INSERT, UPDATE, DELETE)
    
    Returns:
        bool: True if the trigger was created or already exists, False otherwise
    """
    async with db.begin():
        try:
            table_exists_query = """
            SELECT EXISTS (
                SELECT FROM information_schema.tables
                WHERE table_schema = 'public'
                AND table_name = :table_name
            );
            """
            result = await db.execute(text(table_exists_query), {"table_name": table_name})
            table_exists = result.scalar()
            
            if not table_exists:
                logger.warning(f"Table {table_name} does not exist, cannot create trigger")
                return False
                
            function_name = f"notify_{table_name}_changes"
            create_function_query = f"""
            CREATE OR REPLACE FUNCTION {function_name}()
            RETURNS TRIGGER AS $$
            DECLARE
                payload JSON;
            BEGIN
                IF (TG_OP = 'DELETE') THEN
                    payload = json_build_object(
                        'operation', TG_OP,
                        'table', TG_TABLE_NAME,
                        'old_data', row_to_json(OLD)
                    );
                ELSE
                    payload = json_build_object(
                        'operation', TG_OP,
                        'table', TG_TABLE_NAME,
                        'data', row_to_json(NEW),
                        'old_data', CASE WHEN TG_OP = 'UPDATE' THEN row_to_json(OLD) ELSE NULL END
                    );
                END IF;

                PERFORM pg_notify('{table_name}_changes', payload::text);
                RETURN NEW;
            END;
            $$ LANGUAGE plpgsql;
            """
            await db.execute(text(create_function_query))
            logger.info(f"Created trigger function {function_name}")
            
            trigger_name = f"{table_name}_notify_trigger"
            drop_trigger_if_exists_query = f"""
            DROP TRIGGER IF EXISTS {trigger_name} ON "{table_name}";
            """
            
            try:
                await db.execute(text(drop_trigger_if_exists_query))
                
                operations_str = " OR ".join(operations)
                create_trigger_query = f"""
                CREATE TRIGGER {trigger_name}
                AFTER {operations_str} ON "{table_name}"
                FOR EACH ROW
                EXECUTE FUNCTION {function_name}();
                """
                await db.execute(text(create_trigger_query))
                logger.info(f"Created database trigger for table {table_name} on operations: {', '.join(operations)}")
            except Exception as e:
                logger.error(f"Error creating trigger for table {table_name}: {e}")
                return False
                
            return True
        except Exception as e:
            logger.error(f"Error creating table trigger: {e}")
            return False

async def create_trigger_for_all_tables(db: AsyncSession) -> None:
    """
    Create notification triggers for all tables in the database.
    Each table trigger creation is handled in its own transaction to prevent
    one failure from affecting others.
    """
    try:
        # First get the list of tables in a separate transaction that we explicitly commit
        tables = []
        async with db.begin() as transaction:
            query = """
            SELECT table_name
            FROM information_schema.tables
            WHERE table_schema = 'public'
            AND table_type = 'BASE TABLE';
            """
            result = await db.execute(text(query))
            tables = [row.table_name for row in result.fetchall()]
            # Transaction will be committed here when the block exits
        
        # Now process each table with its own transaction
        for table_name in tables:
            try:
                success = await ensure_table_trigger_exists(db, table_name)
                if success:
                    logger.info(f"Successfully created trigger for table {table_name}")
                else:
                    logger.warning(f"Failed to create trigger for table {table_name}")
            except Exception as e:
                logger.error(f"Error creating trigger for table {table_name}: {e}")
                continue
            
    except Exception as e:
        logger.error(f"Error creating triggers for all tables: {e}")
        # Make sure we rollback any active transaction in case of error
        try:
            await db.rollback()
        except Exception:
            pass
