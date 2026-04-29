from fastapi import FastAPI
from app.core.database import Base, engine
from app.controllers import user_controller

app = FastAPI(title="Library API")

Base.metadata.create_all(bind=engine)

app.include_router(user_controller.router)