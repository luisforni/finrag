"""create users and query_logs tables

Revision ID: 0002
Revises: 0001
Create Date: 2026-03-17
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0002"
down_revision: Union[str, None] = "0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        sa.text(
            """
        CREATE TABLE IF NOT EXISTS users (
            id UUID NOT NULL,
            email VARCHAR(255) NOT NULL,
            full_name VARCHAR(100) NOT NULL,
            hashed_password VARCHAR(255) NOT NULL,
            role VARCHAR(20) NOT NULL DEFAULT 'analyst',
            is_active BOOLEAN NOT NULL DEFAULT true,
            created_at TIMESTAMP WITH TIME ZONE NOT NULL,
            PRIMARY KEY (id),
            UNIQUE (email)
        )
    """
        )
    )
    op.execute(sa.text("CREATE UNIQUE INDEX IF NOT EXISTS ix_users_email ON users (email)"))

    op.execute(
        sa.text(
            """
        CREATE TABLE IF NOT EXISTS query_logs (
            id UUID NOT NULL,
            user_id UUID NOT NULL,
            question TEXT NOT NULL,
            answer TEXT NOT NULL,
            document_ids_json TEXT NOT NULL DEFAULT '[]',
            sources_count INTEGER NOT NULL DEFAULT 0,
            tokens_used INTEGER NOT NULL DEFAULT 0,
            latency_ms INTEGER NOT NULL DEFAULT 0,
            created_at TIMESTAMP WITH TIME ZONE NOT NULL,
            PRIMARY KEY (id)
        )
    """
        )
    )
    op.execute(sa.text("CREATE INDEX IF NOT EXISTS ix_query_logs_user_id ON query_logs (user_id)"))
    op.execute(
        sa.text("CREATE INDEX IF NOT EXISTS ix_query_logs_created_at ON query_logs (created_at)")
    )


def downgrade() -> None:
    op.execute(sa.text("DROP INDEX IF EXISTS ix_query_logs_created_at"))
    op.execute(sa.text("DROP INDEX IF EXISTS ix_query_logs_user_id"))
    op.execute(sa.text("DROP TABLE IF EXISTS query_logs"))
    op.execute(sa.text("DROP INDEX IF EXISTS ix_users_email"))
    op.execute(sa.text("DROP TABLE IF EXISTS users"))
