"""loan due notifications

Revision ID: 0002_loan_due_notifications
Revises: 0001_initial_schema
Create Date: 2026-05-01 00:00:00.000000
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "0002_loan_due_notifications"
down_revision: str | None = "0001_initial_schema"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "loan_due_notifications",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("loan_id", sa.Integer(), nullable=False),
        sa.Column("channel", sa.String(), nullable=False),
        sa.Column("notification_date", sa.Date(), nullable=False),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("error_message", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["loan_id"], ["loans.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "loan_id",
            "channel",
            "notification_date",
            name="uq_loan_due_notifications_loan_channel_date",
        ),
    )
    op.create_index(
        "ix_loan_due_notifications_channel",
        "loan_due_notifications",
        ["channel"],
        unique=False,
    )
    op.create_index(
        "ix_loan_due_notifications_channel_date",
        "loan_due_notifications",
        ["channel", "notification_date"],
        unique=False,
    )
    op.create_index("ix_loan_due_notifications_id", "loan_due_notifications", ["id"], unique=False)
    op.create_index("ix_loan_due_notifications_loan_id", "loan_due_notifications", ["loan_id"], unique=False)
    op.create_index(
        "ix_loan_due_notifications_notification_date",
        "loan_due_notifications",
        ["notification_date"],
        unique=False,
    )
    op.create_index(
        "ix_loan_due_notifications_status",
        "loan_due_notifications",
        ["status"],
        unique=False,
    )
    op.create_index(
        "ix_loan_due_notifications_status_created_at",
        "loan_due_notifications",
        ["status", "created_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_loan_due_notifications_status_created_at", table_name="loan_due_notifications")
    op.drop_index("ix_loan_due_notifications_status", table_name="loan_due_notifications")
    op.drop_index("ix_loan_due_notifications_notification_date", table_name="loan_due_notifications")
    op.drop_index("ix_loan_due_notifications_loan_id", table_name="loan_due_notifications")
    op.drop_index("ix_loan_due_notifications_id", table_name="loan_due_notifications")
    op.drop_index("ix_loan_due_notifications_channel_date", table_name="loan_due_notifications")
    op.drop_index("ix_loan_due_notifications_channel", table_name="loan_due_notifications")
    op.drop_table("loan_due_notifications")
