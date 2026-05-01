from fastapi import FastAPI
from sqlalchemy import text
from dotenv import load_dotenv
from app.core.logging import configure_logging

load_dotenv()
configure_logging()

from app.core.database import Base, engine
from app.models import account, loan_operation_metric
from app.controllers import user_controller
from app.controllers import book_controller
from app.controllers import loan_controller
from app.controllers import author_controller
from app.controllers import auth_controller
from app.controllers import account_controller
from app.controllers import loan_request_controller
from app.controllers import health_controller
from app.controllers import metrics_controller

app = FastAPI(title="Library API")

Base.metadata.create_all(bind=engine)
if engine.dialect.name == "postgresql":
    with engine.begin() as connection:
        connection.execute(text("ALTER TABLE loans DROP CONSTRAINT IF EXISTS uq_user_book_active_loan"))
        connection.execute(
            text(
                "CREATE UNIQUE INDEX IF NOT EXISTS ix_loans_active_user_book "
                "ON loans (user_id, book_id) WHERE status = 'active'"
            )
        )
        connection.execute(text("ALTER TABLE users DROP CONSTRAINT IF EXISTS uq_user_email"))
        connection.execute(text("ALTER TABLE users DROP CONSTRAINT IF EXISTS users_email_key"))
        connection.execute(
            text(
                "CREATE UNIQUE INDEX IF NOT EXISTS ix_users_active_email "
                "ON users (email) WHERE deleted_at IS NULL"
            )
        )
        connection.execute(text("ALTER TABLE accounts ADD COLUMN IF NOT EXISTS user_id INTEGER"))
        connection.execute(
            text(
                """
                DO $$
                BEGIN
                    IF NOT EXISTS (
                        SELECT 1
                        FROM pg_constraint
                        WHERE conname = 'fk_accounts_user_id'
                    ) THEN
                        ALTER TABLE accounts
                        ADD CONSTRAINT fk_accounts_user_id
                        FOREIGN KEY (user_id) REFERENCES users(id);
                    END IF;
                END
                $$;
                """
            )
        )
        connection.execute(text("ALTER TABLE loans ADD COLUMN IF NOT EXISTS renewal_count INTEGER NOT NULL DEFAULT 0"))
        connection.execute(
            text(
                "CREATE INDEX IF NOT EXISTS ix_loan_requests_pending_loan "
                "ON loan_requests (user_id, book_id) "
                "WHERE request_type = 'loan' AND status = 'pending'"
            )
        )
        connection.execute(
            text(
                "CREATE INDEX IF NOT EXISTS ix_loan_requests_pending_action "
                "ON loan_requests (request_type, loan_id) "
                "WHERE status = 'pending' AND loan_id IS NOT NULL"
            )
        )

app.include_router(auth_controller.router)
app.include_router(health_controller.router)
app.include_router(account_controller.router)
app.include_router(user_controller.router)
app.include_router(book_controller.router)
app.include_router(loan_controller.router)
app.include_router(loan_request_controller.router)
app.include_router(author_controller.router)
app.include_router(metrics_controller.router)
