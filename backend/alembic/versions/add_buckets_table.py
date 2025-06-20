"""Add buckets table and update files table

Revision ID: add_buckets_table
Revises: 1a1a1a1a1a1a
Create Date: 2023-07-01 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'add_buckets_table'
down_revision = '1a1a1a1a1a1a'
branch_labels = None
depends_on = None


def upgrade():
    # Create buckets table
    op.create_table(
        'buckets',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('description', sa.String(), nullable=True),
        sa.Column('minio_bucket_name', sa.String(), nullable=False),
        sa.Column('is_public', sa.Boolean(), default=False),
        sa.Column('owner_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['owner_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('minio_bucket_name')
    )

    # Add bucket_id column to files table
    op.add_column('files', sa.Column('bucket_id', postgresql.UUID(as_uuid=True), nullable=True))
    op.create_foreign_key(None, 'files', 'buckets', ['bucket_id'], ['id'])


def downgrade():
    # Drop foreign key constraint and bucket_id column from files table
    op.drop_constraint(None, 'files', type_='foreignkey')
    op.drop_column('files', 'bucket_id')

    # Drop buckets table
    op.drop_table('buckets')
