"""Add cloud function tables

Revision ID: add_functions_tables
Revises: add_buckets_table
Create Date: 2024-06-12 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'add_functions_tables'
down_revision = 'add_buckets_table'
branch_labels = None
depends_on = None


def upgrade():
    # ------------------------------------------------------------------
    # 1. functions table (without version_id to avoid circular FK)
    # ------------------------------------------------------------------
    op.create_table(
        'functions',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('name', sa.String(length=255), nullable=False, unique=True),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('code', sa.Text(), nullable=False),
        # Enums
        sa.Column('runtime', sa.Enum('deno', name='function_runtime'), nullable=False, server_default='deno'),
        sa.Column(
            'trigger_type',
            sa.Enum('http', 'schedule', 'database', name='function_trigger_type'),
            nullable=False,
            server_default='http',
        ),
        # HTTP specifics
        sa.Column('method', sa.String(length=10), nullable=True),
        sa.Column('path', sa.String(length=255), nullable=True, unique=True),
        # Schedule specifics
        sa.Column('schedule', sa.String(length=255), nullable=True),
        # Database specifics
        sa.Column('table_name', sa.String(length=255), nullable=True),
        sa.Column('operations', sa.String(length=255), nullable=True),
        sa.Column('filter_conditions', sa.Text(), nullable=True),
        sa.Column(
            'transaction_handling',
            sa.Enum('allow', 'abort', 'modify', name='function_tx_handling'),
            nullable=True,
            server_default='allow',
        ),
        # Versioning stub (added later)
        sa.Column('version_number', sa.Integer(), nullable=False, server_default='1'),
        # State & ownership
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.text('true')),
        sa.Column('owner_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['owner_id'], ['users.id'], name='fk_functions_owner_id_users'),
    )

    # Index for fast look‑ups by owner
    op.create_index('idx_functions_owner_id', 'functions', ['owner_id'])
    op.create_index('idx_functions_is_active', 'functions', ['is_active'])

    # ------------------------------------------------------------------
    # 2. function_versions table
    # ------------------------------------------------------------------
    op.create_table(
        'function_versions',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('function_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('version_number', sa.Integer(), nullable=False),
        sa.Column('code', sa.Text(), nullable=False),
        sa.Column('metadata', sa.Text(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('created_by', postgresql.UUID(as_uuid=True), nullable=True),
        sa.ForeignKeyConstraint(['function_id'], ['functions.id'], name='fk_function_versions_function_id_functions', ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['created_by'], ['users.id'], name='fk_function_versions_created_by_users'),
    )

    op.create_index('idx_function_versions_function_id', 'function_versions', ['function_id'])
    op.create_unique_constraint(
        'uq_function_versions_function_id_version_number',
        'function_versions',
        ['function_id', 'version_number'],
    )

    # ------------------------------------------------------------------
    # 3. Add version_id FK to functions now that versions table exists
    # ------------------------------------------------------------------
    op.add_column('functions', sa.Column('version_id', postgresql.UUID(as_uuid=True), nullable=True))
    op.create_foreign_key(
        'fk_functions_version_id_function_versions',
        'functions',
        'function_versions',
        ['version_id'],
        ['id'],
        ondelete='SET NULL',
    )

    # ------------------------------------------------------------------
    # 4. function_env_vars table
    # ------------------------------------------------------------------
    op.create_table(
        'function_env_vars',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('function_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('key', sa.String(length=255), nullable=False),
        sa.Column('value', sa.Text(), nullable=False),
        sa.Column('is_secret', sa.Boolean(), nullable=False, server_default=sa.text('true')),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['function_id'], ['functions.id'], name='fk_function_env_vars_function_id_functions', ondelete='CASCADE'),
        sa.UniqueConstraint('function_id', 'key', name='uq_function_env_vars_function_id_key'),
    )


def downgrade():
    # Drop tables in reverse order to satisfy FK constraints
    op.drop_table('function_env_vars')
    op.drop_constraint('fk_functions_version_id_function_versions', 'functions', type_='foreignkey')
    op.drop_column('functions', 'version_id')
    op.drop_table('function_versions')
    op.drop_index('idx_functions_is_active', table_name='functions')
    op.drop_index('idx_functions_owner_id', table_name='functions')
    op.drop_table('functions')

    # Finally drop the Enum types explicitly to avoid clutter
    op.execute('DROP TYPE IF EXISTS function_runtime')
    op.execute('DROP TYPE IF EXISTS function_trigger_type')
    op.execute('DROP TYPE IF EXISTS function_tx_handling') 