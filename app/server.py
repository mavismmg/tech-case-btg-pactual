from contextlib import asynccontextmanager
import os

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.logging import configure_logging

load_dotenv()
configure_logging()

from app.services.notification_scheduler import DueLoanNotificationScheduler
from app.controllers import user_controller
from app.controllers import book_controller
from app.controllers import loan_controller
from app.controllers import author_controller
from app.controllers import auth_controller
from app.controllers import account_controller
from app.controllers import loan_request_controller
from app.controllers import health_controller
from app.controllers import metrics_controller
from app.controllers import notification_controller


notification_scheduler = DueLoanNotificationScheduler()


@asynccontextmanager
async def lifespan(app: FastAPI):
    notification_scheduler.start()
    try:
        yield
    finally:
        notification_scheduler.stop()


app = FastAPI(title="Library API", lifespan=lifespan)

cors_origins = [
    origin.strip()
    for origin in os.getenv("CORS_ORIGINS", "http://localhost:5173").split(",")
    if origin.strip()
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
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
app.include_router(notification_controller.router)
