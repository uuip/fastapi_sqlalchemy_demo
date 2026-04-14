"""rename user balance to energy

Revision ID: 7b8d0b89d2e1
Revises: 065d9696fad1
Create Date: 2026-05-09 01:55:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "7b8d0b89d2e1"
down_revision: str | None = "065d9696fad1"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.alter_column(
        "user",
        "balance",
        new_column_name="energy",
        existing_type=sa.BigInteger(),
        existing_nullable=True,
    )


def downgrade() -> None:
    op.alter_column(
        "user",
        "energy",
        new_column_name="balance",
        existing_type=sa.BigInteger(),
        existing_nullable=True,
    )
