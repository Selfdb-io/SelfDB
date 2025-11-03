"""
Test suite for Table model implementation following TDD principles.
Based on API Contracts Plan specification for Table model.
"""

import pytest
import uuid
from datetime import datetime, timezone

from shared.models.table import Table
from shared.models.user import User, UserRole


class TestTableModel:
    """Test cases for Table model implementation."""
    
    def test_table_creation_with_required_fields(self):
        """Test creating a table with all required fields."""
        owner_id = uuid.uuid4()
        schema = {
            "columns": [
                {"name": "id", "type": "uuid", "primary_key": True},
                {"name": "name", "type": "varchar", "max_length": 255},
                {"name": "created_at", "type": "timestamp"}
            ]
        }
        
        table = Table(
            name="products",
            schema=schema,
            public=False,
            owner_id=owner_id,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        )
        
        assert table.name == "products"
        assert table.schema == schema
        assert table.public is False
        assert table.owner_id == owner_id
        assert isinstance(table.created_at, datetime)
        assert isinstance(table.updated_at, datetime)
    
    def test_table_public_access_flag(self):
        """Test table public/private access flag."""
        owner_id = uuid.uuid4()
        schema = {"columns": []}
        
        public_table = Table(
            name="public_data",
            schema=schema,
            public=True,
            owner_id=owner_id,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        )
        
        private_table = Table(
            name="private_data",
            schema=schema,
            public=False,
            owner_id=owner_id,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        )
        
        assert public_table.public is True
        assert private_table.public is False
    
    def test_table_schema_definition(self):
        """Test table schema definition for table structure."""
        schema = {
            "columns": [
                {"name": "id", "type": "uuid", "primary_key": True, "nullable": False},
                {"name": "email", "type": "varchar", "max_length": 255, "unique": True},
                {"name": "age", "type": "integer", "min": 0, "max": 150},
                {"name": "is_active", "type": "boolean", "default": True},
                {"name": "metadata", "type": "jsonb", "nullable": True},
                {"name": "created_at", "type": "timestamp", "default": "now()"}
            ],
            "indexes": [
                {"columns": ["email"], "unique": True},
                {"columns": ["created_at"], "type": "btree"}
            ]
        }
        
        owner_id = uuid.uuid4()
        
        table = Table(
            name="users",
            schema=schema,
            public=False,
            owner_id=owner_id,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        )
        
        assert table.schema == schema
        assert len(table.schema["columns"]) == 6
        assert table.schema["columns"][0]["name"] == "id"
        assert table.schema["columns"][0]["type"] == "uuid"
        assert table.schema["columns"][0]["primary_key"] is True
    
    def test_table_ownership_relationship(self):
        """Test table ownership relationship to User."""
        owner = User(
            id=uuid.uuid4(),
            email="table-owner@example.com",
            password="ownerPassword123!",
            role=UserRole.USER,
            is_active=True,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        )
        
        schema = {"columns": [{"name": "id", "type": "uuid"}]}
        
        table = Table(
            name="owner-table",
            schema=schema,
            public=False,
            owner_id=owner.id,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        )
        
        assert table.owner_id == owner.id
    
    def test_table_name_validation(self):
        """Test table name validation."""
        schema = {"columns": []}
        owner_id = uuid.uuid4()
        
        # Valid table names
        valid_names = [
            "users",
            "products",
            "order_items",
            "user_profiles",
            "a"  # Single character
        ]
        
        for name in valid_names:
            table = Table(
                name=name,
                schema=schema,
                public=False,
                owner_id=owner_id,
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc)
            )
            assert table.name == name
    
    def test_table_unique_naming_per_owner(self):
        """Test that table names are unique per owner."""
        owner_id = uuid.uuid4()
        table_name = "my-table"
        schema = {"columns": []}
        
        table1 = Table(
            name=table_name,
            schema=schema,
            public=False,
            owner_id=owner_id,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        )
        
        # Same owner, same name - should be prevented at database level
        table2 = Table(
            name=table_name,
            schema=schema,
            public=True,  # Different public flag
            owner_id=owner_id,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        )
        
        assert table1.name == table2.name
        assert table1.owner_id == table2.owner_id
    
    def test_table_timestamps(self):
        """Test that created_at and updated_at are datetime objects."""
        now = datetime.now(timezone.utc)
        schema = {"columns": []}
        
        table = Table(
            name="timestamp-table",
            schema=schema,
            public=False,
            owner_id=uuid.uuid4(),
            created_at=now,
            updated_at=now
        )
        
        assert table.created_at == now
        assert table.updated_at == now
        assert isinstance(table.created_at, datetime)
        assert isinstance(table.updated_at, datetime)
    
    def test_table_to_dict_conversion(self):
        """Test table serialization to dictionary."""
        owner_id = uuid.uuid4()
        schema = {
            "columns": [
                {"name": "id", "type": "uuid", "primary_key": True},
                {"name": "data", "type": "jsonb"}
            ]
        }
        
        table = Table(
            name="dict-table",
            schema=schema,
            public=True,
            owner_id=owner_id,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        )
        
        table_dict = table.to_dict()
        
        assert table_dict["name"] == table.name
        assert table_dict["schema"] == table.schema
        assert table_dict["public"] == table.public
        assert table_dict["owner_id"] == str(table.owner_id)
        assert "created_at" in table_dict
        assert "updated_at" in table_dict
    
    def test_table_string_representation(self):
        """Test table string representation."""
        schema = {"columns": []}
        
        table = Table(
            name="repr-table",
            schema=schema,
            public=False,
            owner_id=uuid.uuid4(),
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        )
        
        assert str(table) == f"<Table {table.name}>"
    
    def test_table_description_field(self):
        """Test optional description field."""
        schema = {"columns": []}
        owner_id = uuid.uuid4()
        
        # Without description
        table1 = Table(
            name="no-desc-table",
            schema=schema,
            public=False,
            owner_id=owner_id,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        )
        assert table1.description is None
        
        # With description
        table2 = Table(
            name="with-desc-table",
            schema=schema,
            public=False,
            owner_id=owner_id,
            description="This table stores user activity logs",
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        )
        assert table2.description == "This table stores user activity logs"
    
    def test_table_metadata_field(self):
        """Test optional metadata field."""
        metadata = {"category": "analytics", "retention_days": 90}
        schema = {"columns": []}
        
        table = Table(
            name="metadata-table",
            schema=schema,
            public=False,
            owner_id=uuid.uuid4(),
            metadata=metadata,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        )
        
        assert table.metadata == metadata
    
    def test_table_row_count_tracking(self):
        """Test row count tracking."""
        schema = {"columns": []}
        
        table = Table(
            name="counted-table",
            schema=schema,
            public=False,
            owner_id=uuid.uuid4(),
            row_count=1000,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        )
        
        assert table.row_count == 1000
    
    def test_table_indexes_and_constraints(self):
        """Test table indexes and constraints definition."""
        schema = {
            "columns": [
                {"name": "id", "type": "uuid", "primary_key": True},
                {"name": "email", "type": "varchar", "unique": True},
                {"name": "created_at", "type": "timestamp"}
            ],
            "indexes": [
                {"name": "idx_email", "columns": ["email"], "unique": True},
                {"name": "idx_created_at", "columns": ["created_at"], "type": "btree"}
            ],
            "constraints": [
                {"type": "check", "name": "chk_positive_age", "condition": "age > 0"}
            ]
        }
        
        table = Table(
            name="constrained-table",
            schema=schema,
            public=False,
            owner_id=uuid.uuid4(),
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        )
        
        assert "indexes" in table.schema
        assert "constraints" in table.schema
        assert len(table.schema["indexes"]) == 2
        assert table.schema["indexes"][0]["name"] == "idx_email"
    
    def test_table_update_row_count(self):
        """Test updating table row count."""
        schema = {"columns": []}
        
        table = Table(
            name="counted-table",
            schema=schema,
            public=False,
            owner_id=uuid.uuid4(),
            row_count=100,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        )
        
        # Update row count
        table.update_row_count(250)
        
        assert table.row_count == 250
        assert table.updated_at > table.created_at
    
    def test_table_update_schema(self):
        """Test updating table schema."""
        old_schema = {"columns": [{"name": "id", "type": "uuid"}]}
        new_schema = {
            "columns": [
                {"name": "id", "type": "uuid"},
                {"name": "name", "type": "varchar"}
            ]
        }
        
        table = Table(
            name="schema-table",
            schema=old_schema,
            public=False,
            owner_id=uuid.uuid4(),
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        )
        
        # Update schema
        table.update_schema(new_schema)
        
        assert table.schema == new_schema
        assert len(table.schema["columns"]) == 2
        assert table.updated_at > table.created_at
    
    def test_table_get_column_names(self):
        """Test getting column names from schema."""
        schema = {
            "columns": [
                {"name": "id", "type": "uuid"},
                {"name": "email", "type": "varchar"},
                {"name": "created_at", "type": "timestamp"}
            ]
        }
        
        table = Table(
            name="column-table",
            schema=schema,
            public=False,
            owner_id=uuid.uuid4(),
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        )
        
        column_names = table.get_column_names()
        assert column_names == ["id", "email", "created_at"]
    
    def test_table_get_primary_key_columns(self):
        """Test getting primary key columns from schema."""
        schema = {
            "columns": [
                {"name": "id", "type": "uuid", "primary_key": True},
                {"name": "email", "type": "varchar"},
                {"name": "user_id", "type": "uuid", "primary_key": True}
            ]
        }
        
        table = Table(
            name="pk-table",
            schema=schema,
            public=False,
            owner_id=uuid.uuid4(),
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        )
        
        pk_columns = table.get_primary_key_columns()
        assert pk_columns == ["id", "user_id"]
    
    def test_table_has_index(self):
        """Test checking if column has index."""
        schema = {
            "columns": [
                {"name": "id", "type": "uuid"},
                {"name": "email", "type": "varchar"},
                {"name": "created_at", "type": "timestamp"}
            ],
            "indexes": [
                {"name": "idx_email", "columns": ["email"], "unique": True},
                {"name": "idx_created", "columns": ["created_at"]}
            ]
        }
        
        table = Table(
            name="indexed-table",
            schema=schema,
            public=False,
            owner_id=uuid.uuid4(),
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        )
        
        assert table.has_index("email") is True
        assert table.has_index("created_at") is True
        assert table.has_index("id") is False