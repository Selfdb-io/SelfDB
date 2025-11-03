"""
Table model implementation following API Contracts Plan specification.
Based on Table model requirements for database operations.
"""

import uuid
from datetime import datetime, timezone
from typing import Dict, Any, Optional


class Table:
    """
    Table model for database table management.
    
    Attributes:
        name: Table name (e.g., "products", "users")
        schema: JSON schema definition for table structure
        public: Public access flag (public/private)
        owner_id: References User who created the table
        description: Optional description
        metadata: Optional metadata
        row_count: Number of rows in the table
        created_at: Creation timestamp
        updated_at: Last update timestamp
    """
    
    def __init__(
        self,
        name: str,
        schema: Dict[str, Any],
        public: bool,
        owner_id: uuid.UUID,
        description: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        row_count: int = 0,
        created_at: Optional[datetime] = None,
        updated_at: Optional[datetime] = None
    ):
        """
        Initialize a Table instance.
        
        Args:
            name: Table name
            schema: JSON schema definition for table structure
            public: Public access flag
            owner_id: Owner's User ID
            description: Optional description
            metadata: Optional metadata dictionary
            row_count: Number of rows (defaults to 0)
            created_at: Creation timestamp (defaults to now)
            updated_at: Update timestamp (defaults to now)
        """
        self.name = name
        self.schema = schema
        self.public = public
        self.owner_id = owner_id
        self.description = description
        self.metadata = metadata or {}
        self.row_count = row_count
        
        # Set timestamps
        now = datetime.now(timezone.utc)
        self.created_at = created_at or now
        self.updated_at = updated_at or now
    
    def update_row_count(self, count: int) -> None:
        """
        Update the row count for the table.
        
        Args:
            count: New row count
        """
        self.row_count = count
        self.updated_at = datetime.now(timezone.utc)
    
    def update_schema(self, new_schema: Dict[str, Any]) -> None:
        """
        Update the table schema.
        
        Args:
            new_schema: New schema definition
        """
        self.schema = new_schema
        self.updated_at = datetime.now(timezone.utc)
    
    def get_column_names(self) -> list[str]:
        """
        Get list of column names from the schema.
        
        Returns:
            List of column names
        """
        columns = self.schema.get("columns", [])
        return [col.get("name") for col in columns if "name" in col]
    
    def get_primary_key_columns(self) -> list[str]:
        """
        Get list of primary key columns from the schema.
        
        Returns:
            List of primary key column names
        """
        columns = self.schema.get("columns", [])
        return [
            col.get("name") for col in columns 
            if col.get("primary_key") is True and "name" in col
        ]
    
    def has_index(self, column_name: str) -> bool:
        """
        Check if a column has an index defined.
        
        Args:
            column_name: Name of the column
            
        Returns:
            True if column has an index
        """
        indexes = self.schema.get("indexes", [])
        for index in indexes:
            columns = index.get("columns", [])
            if column_name in columns:
                return True
        return False
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert table to dictionary.
        
        Returns:
            Dictionary representation of table
        """
        return {
            "name": self.name,
            "schema": self.schema,
            "public": self.public,
            "owner_id": str(self.owner_id),
            "description": self.description,
            "metadata": self.metadata,
            "row_count": self.row_count,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat()
        }
    
    def __str__(self) -> str:
        """String representation of table."""
        return f"<Table {self.name}>"
    
    def __repr__(self) -> str:
        """Detailed string representation for debugging."""
        return f"<Table(name={self.name}, public={self.public}, owner_id={self.owner_id})>"