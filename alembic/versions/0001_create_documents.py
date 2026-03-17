"""create documents table

Revision ID: 0001
Revises:
Create Date: 2026-03-17
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID

revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        sa.text(
            """
        CREATE TABLE IF NOT EXISTS documents (
            id UUID NOT NULL,
            filename VARCHAR(255) NOT NULL,
            s3_key VARCHAR(1024) NOT NULL,
            document_type VARCHAR(50) NOT NULL,
            status VARCHAR(20) NOT NULL DEFAULT 'pending',
            owner_id UUID NOT NULL,
            created_at TIMESTAMP WITH TIME ZONE NOT NULL,
            updated_at TIMESTAMP WITH TIME ZONE NOT NULL,
            chunk_count INTEGER NOT NULL DEFAULT 0,
            error_message VARCHAR(2048),
            PRIMARY KEY (id),
            UNIQUE (s3_key)
        )
    """
        )
    )
    op.execute(sa.text("CREATE INDEX IF NOT EXISTS ix_documents_owner_id ON documents (owner_id)"))
    op.execute(
        sa.text("CREATE INDEX IF NOT EXISTS ix_documents_created_at ON documents (created_at)")
    )


def downgrade() -> None:
    op.execute(sa.text("DROP INDEX IF EXISTS ix_documents_created_at"))
    op.execute(sa.text("DROP INDEX IF EXISTS ix_documents_owner_id"))
    op.execute(sa.text("DROP TABLE IF EXISTS documents"))
