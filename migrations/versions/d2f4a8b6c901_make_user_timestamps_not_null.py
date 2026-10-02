"""Make user timestamps NOT NULL after backfilling legacy rows."""

from collections.abc import Sequence

from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "d2f4a8b6c901"
down_revision: str | None = "c4d3a1f6b2e0"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(
        'UPDATE "user" SET '
        'created_at = COALESCE(created_at, updated_at, CURRENT_TIMESTAMP), '
        'updated_at = COALESCE(updated_at, created_at, CURRENT_TIMESTAMP) '
        'WHERE created_at IS NULL OR updated_at IS NULL'
    )
    for column in ("created_at", "updated_at"):
        op.alter_column("user", column, existing_type=postgresql.TIMESTAMP(timezone=True, precision=0), nullable=False)


def downgrade() -> None:
    for column in ("created_at", "updated_at"):
        op.alter_column("user", column, existing_type=postgresql.TIMESTAMP(timezone=True, precision=0), nullable=True)
