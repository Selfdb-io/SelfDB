"""remove_function_trigger_fields

Revision ID: remove_function_trigger_fields
Revises: add_functions_tables
Create Date: 2023-10-10

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'remove_function_trigger_fields'
down_revision = 'add_functions_tables'
branch_labels = None
depends_on = None


def upgrade():
    # Remove trigger-specific columns from functions table
    op.drop_column('functions', 'trigger_type')
    op.drop_column('functions', 'method')
    op.drop_column('functions', 'path')
    op.drop_column('functions', 'schedule')
    op.drop_column('functions', 'table_name')
    op.drop_column('functions', 'operations')
    op.drop_column('functions', 'filter_conditions')
    op.drop_column('functions', 'transaction_handling')
    
    # Drop the unused enums
    op.execute('DROP TYPE IF EXISTS function_trigger_type')
    op.execute('DROP TYPE IF EXISTS function_tx_handling')


def downgrade():
    # Re-create the enums
    op.execute("CREATE TYPE function_trigger_type AS ENUM ('http', 'schedule', 'database')")
    op.execute("CREATE TYPE function_tx_handling AS ENUM ('allow', 'abort', 'modify')")
    
    # Re-add the columns
    op.add_column('functions', sa.Column('trigger_type', sa.Enum('http', 'schedule', 'database', name='function_trigger_type'), nullable=False, server_default='http'))
    op.add_column('functions', sa.Column('method', sa.String(length=10), nullable=True))
    op.add_column('functions', sa.Column('path', sa.String(length=255), nullable=True, unique=True))
    op.add_column('functions', sa.Column('schedule', sa.String(length=255), nullable=True))
    op.add_column('functions', sa.Column('table_name', sa.String(length=255), nullable=True))
    op.add_column('functions', sa.Column('operations', sa.String(length=255), nullable=True))
    op.add_column('functions', sa.Column('filter_conditions', sa.Text(), nullable=True))
    op.add_column('functions', sa.Column('transaction_handling', sa.Enum('allow', 'abort', 'modify', name='function_tx_handling'), nullable=True, server_default='allow'))
