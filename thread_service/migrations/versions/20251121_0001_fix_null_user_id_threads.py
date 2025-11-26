"""Fix threads with NULL user_id.

Revision ID: 20251121_0001
Revises: 20251120_232056
Create Date: 2025-11-21 00:01:00.000000

This migration assigns threads with NULL user_id to the first user in the system,
or deletes them if no users exist. This fixes the issue where historical threads
are not visible after the user authentication migration.

"""
from __future__ import annotations

from typing import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy import text

# revision identifiers, used by Alembic.
revision: str = "20251121_0001"
down_revision: str | None = "20251120_232056"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    """Assign threads with NULL user_id to the first user, or delete if no users exist."""
    connection = op.get_bind()
    
    # Check if there are threads with NULL user_id
    result = connection.execute(text("SELECT COUNT(*) FROM threads WHERE user_id IS NULL"))
    null_thread_count = result.scalar() or 0
    
    if null_thread_count == 0:
        print("No threads with NULL user_id found. Migration complete.")
        return
    
    print(f"Found {null_thread_count} threads with NULL user_id. Attempting to fix...")
    
    # Get the first user in the system (by creation date)
    user_result = connection.execute(
        text("SELECT id FROM users ORDER BY created_at ASC LIMIT 1")
    )
    first_user_id = user_result.scalar()
    
    if first_user_id:
        # Assign NULL user_id threads to the first user
        update_result = connection.execute(
            text("UPDATE threads SET user_id = :user_id WHERE user_id IS NULL"),
            {"user_id": str(first_user_id)},
        )
        connection.commit()
        updated_count = update_result.rowcount if hasattr(update_result, 'rowcount') else null_thread_count
        print(f"Assigned {updated_count} threads to user {first_user_id}")
    else:
        # No users exist - delete orphaned threads
        # This is safer than leaving them orphaned
        connection.execute(text("DELETE FROM threads WHERE user_id IS NULL"))
        connection.commit()
        print(f"Deleted {null_thread_count} orphaned threads (no users exist)")
    
    # Now make user_id non-nullable (if it wasn't already)
    # Check if constraint already exists
    try:
        op.alter_column("threads", "user_id", nullable=False)
        print("Made user_id column non-nullable")
    except Exception as e:
        # Constraint might already exist or column might already be non-nullable
        print(f"Note: Could not alter user_id column (may already be non-nullable): {e}")


def downgrade() -> None:
    """This migration cannot be safely reversed."""
    # We cannot restore the NULL values without knowing which threads had them
    # This is a one-way migration
    pass

