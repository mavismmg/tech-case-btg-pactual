from fastapi import FastAPI
from dotenv import load_dotenv
from app.core.logging import configure_logging

load_dotenv()
configure_logging()

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

app.include_router(auth_controller.router)
app.include_router(health_controller.router)
app.include_router(account_controller.router)
app.include_router(user_controller.router)
app.include_router(book_controller.router)
app.include_router(loan_controller.router)
app.include_router(loan_request_controller.router)
app.include_router(author_controller.router)
app.include_router(metrics_controller.router)
