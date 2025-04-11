"""Change external_id to string

Revision ID: 20250408_change_external_id_to_string
Create Date: 2025-04-08 14:31:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '20250408_change_external_id_to_string'
down_revision = None  # Can be replaced with previous migration ID
branch_labels = None
depends_on = None

def upgrade():
    # This migration documents a manual change that was already applied
    # ALTER TABLE conversations ALTER COLUMN external_id TYPE VARCHAR;
    op.execute("SELECT 1")  # No-op since the change was done manually
    
def downgrade():
    # If needed, this would change the column back to INTEGER
    # op.execute("ALTER TABLE conversations ALTER COLUMN external_id TYPE INTEGER USING external_id::integer;")
    pass 