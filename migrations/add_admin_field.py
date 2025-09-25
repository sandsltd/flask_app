"""Add is_admin field to User model

This migration adds an is_admin boolean field to the User table
to support administrative access across all events.

Revision ID: add_admin_field_001
Create Date: 2025-09-25
"""

from alembic import op
import sqlalchemy as sa

def upgrade():
    """Add is_admin column to user table if it doesn't exist."""
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    
    # Check if column already exists
    columns = [col['name'] for col in inspector.get_columns('user')]
    
    if 'is_admin' not in columns:
        op.add_column('user', 
            sa.Column('is_admin', sa.Boolean(), nullable=True, default=False)
        )
        
        # Set default value for existing records
        op.execute("UPDATE user SET is_admin = false WHERE is_admin IS NULL")
        
        # Make column not nullable after setting defaults
        op.alter_column('user', 'is_admin', nullable=False)
        
        print("Added is_admin column to user table")
    else:
        print("is_admin column already exists in user table")

def downgrade():
    """Remove is_admin column from user table."""
    op.drop_column('user', 'is_admin')