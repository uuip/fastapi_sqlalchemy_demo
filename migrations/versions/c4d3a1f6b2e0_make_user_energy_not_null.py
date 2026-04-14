"""make user.energy NOT NULL with default 0

Revision ID: c4d3a1f6b2e0
Revises: 7b8d0b89d2e1
Create Date: 2026-05-09 18:05:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "c4d3a1f6b2e0"
down_revision: str | None = "7b8d0b89d2e1"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute('UPDATE "user" SET energy = 0 WHERE energy IS NULL')
    op.alter_column(
        "user",
        "energy",
        existing_type=sa.BigInteger(),
        nullable=False,
        server_default=sa.text("0"),
    )


def downgrade() -> None:
    op.alter_column(
        "user",
        "energy",
        existing_type=sa.BigInteger(),
        nullable=True,
        server_default=None,
    )
