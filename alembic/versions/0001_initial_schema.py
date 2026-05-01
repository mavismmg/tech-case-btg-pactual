"""initial schema

Revision ID: 0001_initial_schema
Revises:
Create Date: 2026-05-01 00:00:00.000000
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "0001_initial_schema"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "authors",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name", name="uq_author_name"),
    )
    op.create_index("ix_authors_id", "authors", ["id"], unique=False)
    op.create_index("ix_authors_name", "authors", ["name"], unique=False)

    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("email", sa.String(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_users_id", "users", ["id"], unique=False)
    op.create_index("ix_users_name", "users", ["name"], unique=False)
    op.create_index("ix_users_email", "users", ["email"], unique=False)
    op.create_index(
        "ix_users_active_email",
        "users",
        ["email"],
        unique=True,
        postgresql_where=sa.text("deleted_at IS NULL"),
    )

    op.create_table(
        "accounts",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("email", sa.String(), nullable=False),
        sa.Column("password_hash", sa.String(), nullable=False),
        sa.Column("role", sa.String(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("email", name="uq_account_email"),
    )
    op.create_index("ix_accounts_id", "accounts", ["id"], unique=False)
    op.create_index("ix_accounts_name", "accounts", ["name"], unique=False)
    op.create_index("ix_accounts_email", "accounts", ["email"], unique=True)

    op.create_table(
        "books",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("isbn", sa.String(), nullable=False),
        sa.Column("author_id", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(), nullable=False),
        sa.Column("published_date", sa.Date(), nullable=False),
        sa.Column("is_available", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["author_id"], ["authors.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_books_id", "books", ["id"], unique=False)
    op.create_index("ix_books_isbn", "books", ["isbn"], unique=False)
    op.create_index("ix_books_title", "books", ["title"], unique=False)

    op.create_table(
        "loans",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("book_id", sa.Integer(), nullable=False),
        sa.Column("loan_date", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("expected_return_date", sa.DateTime(timezone=True), nullable=False),
        sa.Column("actual_return_date", sa.DateTime(timezone=True), nullable=True),
        sa.Column("fine_value", sa.Float(), nullable=False),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("renewal_count", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["book_id"], ["books.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_loans_id", "loans", ["id"], unique=False)
    op.create_index(
        "ix_loans_active_user_book",
        "loans",
        ["user_id", "book_id"],
        unique=True,
        postgresql_where=sa.text("status = 'active'"),
    )

    op.create_table(
        "loan_requests",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("request_type", sa.String(), nullable=False),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("requester_account_id", sa.Integer(), nullable=False),
        sa.Column("reviewer_account_id", sa.Integer(), nullable=True),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("book_id", sa.Integer(), nullable=True),
        sa.Column("loan_id", sa.Integer(), nullable=True),
        sa.Column("rejection_reason", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["book_id"], ["books.id"]),
        sa.ForeignKeyConstraint(["loan_id"], ["loans.id"]),
        sa.ForeignKeyConstraint(["requester_account_id"], ["accounts.id"]),
        sa.ForeignKeyConstraint(["reviewer_account_id"], ["accounts.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_loan_requests_id", "loan_requests", ["id"], unique=False)
    op.create_index("ix_loan_requests_request_type", "loan_requests", ["request_type"], unique=False)
    op.create_index("ix_loan_requests_status", "loan_requests", ["status"], unique=False)
    op.create_index(
        "ix_loan_requests_pending_loan",
        "loan_requests",
        ["user_id", "book_id"],
        unique=False,
        postgresql_where=sa.text("request_type = 'loan' AND status = 'pending'"),
    )
    op.create_index(
        "ix_loan_requests_pending_action",
        "loan_requests",
        ["request_type", "loan_id"],
        unique=False,
        postgresql_where=sa.text("status = 'pending' AND loan_id IS NOT NULL"),
    )

    op.create_table(
        "loan_operation_metrics",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("operation", sa.String(), nullable=False),
        sa.Column("loan_id", sa.Integer(), nullable=True),
        sa.Column("loan_request_id", sa.Integer(), nullable=True),
        sa.Column("user_id", sa.Integer(), nullable=True),
        sa.Column("book_id", sa.Integer(), nullable=True),
        sa.Column("account_id", sa.Integer(), nullable=True),
        sa.Column("reviewer_account_id", sa.Integer(), nullable=True),
        sa.Column("fine_value", sa.Float(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["account_id"], ["accounts.id"]),
        sa.ForeignKeyConstraint(["book_id"], ["books.id"]),
        sa.ForeignKeyConstraint(["loan_id"], ["loans.id"]),
        sa.ForeignKeyConstraint(["loan_request_id"], ["loan_requests.id"]),
        sa.ForeignKeyConstraint(["reviewer_account_id"], ["accounts.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_loan_operation_metrics_account_id", "loan_operation_metrics", ["account_id"], unique=False)
    op.create_index("ix_loan_operation_metrics_book_id", "loan_operation_metrics", ["book_id"], unique=False)
    op.create_index("ix_loan_operation_metrics_id", "loan_operation_metrics", ["id"], unique=False)
    op.create_index("ix_loan_operation_metrics_loan_id", "loan_operation_metrics", ["loan_id"], unique=False)
    op.create_index(
        "ix_loan_operation_metrics_loan_request_id",
        "loan_operation_metrics",
        ["loan_request_id"],
        unique=False,
    )
    op.create_index("ix_loan_operation_metrics_operation", "loan_operation_metrics", ["operation"], unique=False)
    op.create_index(
        "ix_loan_operation_metrics_operation_created_at",
        "loan_operation_metrics",
        ["operation", "created_at"],
        unique=False,
    )
    op.create_index(
        "ix_loan_operation_metrics_reviewer_account_id",
        "loan_operation_metrics",
        ["reviewer_account_id"],
        unique=False,
    )
    op.create_index("ix_loan_operation_metrics_user_id", "loan_operation_metrics", ["user_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_loan_operation_metrics_user_id", table_name="loan_operation_metrics")
    op.drop_index("ix_loan_operation_metrics_reviewer_account_id", table_name="loan_operation_metrics")
    op.drop_index("ix_loan_operation_metrics_operation_created_at", table_name="loan_operation_metrics")
    op.drop_index("ix_loan_operation_metrics_operation", table_name="loan_operation_metrics")
    op.drop_index("ix_loan_operation_metrics_loan_request_id", table_name="loan_operation_metrics")
    op.drop_index("ix_loan_operation_metrics_loan_id", table_name="loan_operation_metrics")
    op.drop_index("ix_loan_operation_metrics_id", table_name="loan_operation_metrics")
    op.drop_index("ix_loan_operation_metrics_book_id", table_name="loan_operation_metrics")
    op.drop_index("ix_loan_operation_metrics_account_id", table_name="loan_operation_metrics")
    op.drop_table("loan_operation_metrics")

    op.drop_index("ix_loan_requests_pending_action", table_name="loan_requests")
    op.drop_index("ix_loan_requests_pending_loan", table_name="loan_requests")
    op.drop_index("ix_loan_requests_status", table_name="loan_requests")
    op.drop_index("ix_loan_requests_request_type", table_name="loan_requests")
    op.drop_index("ix_loan_requests_id", table_name="loan_requests")
    op.drop_table("loan_requests")

    op.drop_index("ix_loans_active_user_book", table_name="loans")
    op.drop_index("ix_loans_id", table_name="loans")
    op.drop_table("loans")

    op.drop_index("ix_books_title", table_name="books")
    op.drop_index("ix_books_isbn", table_name="books")
    op.drop_index("ix_books_id", table_name="books")
    op.drop_table("books")

    op.drop_index("ix_accounts_email", table_name="accounts")
    op.drop_index("ix_accounts_name", table_name="accounts")
    op.drop_index("ix_accounts_id", table_name="accounts")
    op.drop_table("accounts")

    op.drop_index("ix_users_active_email", table_name="users")
    op.drop_index("ix_users_email", table_name="users")
    op.drop_index("ix_users_name", table_name="users")
    op.drop_index("ix_users_id", table_name="users")
    op.drop_table("users")

    op.drop_index("ix_authors_name", table_name="authors")
    op.drop_index("ix_authors_id", table_name="authors")
    op.drop_table("authors")
