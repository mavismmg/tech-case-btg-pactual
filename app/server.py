from fastapi import FastAPI
from sqlalchemy import text
from dotenv import load_dotenv
from app.core.logging import configure_logging

load_dotenv()
configure_logging()

from app.core.database import Base, engine
from app.models import account
from app.controllers import user_controller
from app.controllers import book_controller
from app.controllers import loan_controller
from app.controllers import author_controller
from app.controllers import auth_controller
from app.controllers import account_controller

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

app.include_router(auth_controller.router)
app.include_router(account_controller.router)
app.include_router(user_controller.router)
app.include_router(book_controller.router)
app.include_router(loan_controller.router)
app.include_router(author_controller.router)
