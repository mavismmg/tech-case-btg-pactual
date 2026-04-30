from fastapi import FastAPI
from app.core.database import Base, engine
from app.controllers import user_controller
from app.controllers import book_controller
from app.controllers import loan_controller
from app.controllers import author_controller

app = FastAPI(title="Library API")

Base.metadata.create_all(bind=engine)

app.include_router(user_controller.router)
app.include_router(book_controller.router)
app.include_router(loan_controller.router)
app.include_router(author_controller.router)