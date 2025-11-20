"""Initial thread schema."""

from __future__ import annotations

from typing import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "20241120_0001"
down_revision: str | None = None
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    thread_status = sa.Enum(
        "open",
        "paused",
        "closed",
        name="thread_status_enum",
    )
    participant_role = sa.Enum(
        "user",
        "agent",
        "tool",
        name="participant_role_enum",
    )
    message_kind = sa.Enum(
        "text",
        "rich",
        "tool_call",
        name="message_kind_enum",
    )
    attachment_kind = sa.Enum(
        "file",
        "image",
        "link",
        name="attachment_kind_enum",
    )

    # thread_status.create(op.get_bind(), checkfirst=True)
    # participant_role.create(op.get_bind(), checkfirst=True)
    # message_kind.create(op.get_bind(), checkfirst=True)
    # attachment_kind.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "threads",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            nullable=False,
        ),
        sa.Column("title", sa.String(length=255), nullable=True),
        sa.Column("status", thread_status, nullable=False, server_default="open"),
        sa.Column("summary", sa.Text(), nullable=True),
        sa.Column(
            "metadata",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )

    op.create_table(
        "participants",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            nullable=False,
        ),
        sa.Column(
            "thread_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("threads.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("role", participant_role, nullable=False, server_default="user"),
        sa.Column("display_name", sa.String(length=255), nullable=True),
        sa.Column(
            "metadata",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )
    op.create_index(
        op.f("ix_participants_thread_id"),
        "participants",
        ["thread_id"],
    )

    op.create_table(
        "messages",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            nullable=False,
        ),
        sa.Column(
            "thread_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("threads.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "participant_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("participants.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("kind", message_kind, nullable=False, server_default="text"),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column(
            "metadata",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )
    op.create_index(op.f("ix_messages_thread_id"), "messages", ["thread_id"])
    op.create_index(op.f("ix_messages_participant_id"), "messages", ["participant_id"])

    op.create_table(
        "message_attachments",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            nullable=False,
        ),
        sa.Column(
            "message_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("messages.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("kind", attachment_kind, nullable=False, server_default="file"),
        sa.Column("uri", sa.Text(), nullable=False),
        sa.Column("content_type", sa.String(length=255), nullable=True),
        sa.Column(
            "metadata",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )
    op.create_index(
        op.f("ix_message_attachments_message_id"),
        "message_attachments",
        ["message_id"],
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_message_attachments_message_id"), table_name="message_attachments")
    op.drop_table("message_attachments")
    op.drop_index(op.f("ix_messages_participant_id"), table_name="messages")
    op.drop_index(op.f("ix_messages_thread_id"), table_name="messages")
    op.drop_table("messages")
    op.drop_index(op.f("ix_participants_thread_id"), table_name="participants")
    op.drop_table("participants")
    op.drop_table("threads")

    sa.Enum(name="attachment_kind_enum").drop(op.get_bind(), checkfirst=True)
    sa.Enum(name="message_kind_enum").drop(op.get_bind(), checkfirst=True)
    sa.Enum(name="participant_role_enum").drop(op.get_bind(), checkfirst=True)
    sa.Enum(name="thread_status_enum").drop(op.get_bind(), checkfirst=True)
