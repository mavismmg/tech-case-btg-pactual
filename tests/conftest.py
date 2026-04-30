import os
import pytest
from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.core.database import Base

load_dotenv()

DATABASE_URL = os.getenv("TEST_DATABASE_URL")
if DATABASE_URL is None:
    raise RuntimeError("TEST_DATABASE_URL or DATABASE_URL must be set for tests")

engine = create_engine(DATABASE_URL)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

@pytest.fixture(scope="function")
def db():
    Base.metadata.create_all(bind=engine)
    
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()

        Base.metadata.drop_all(bind=engine)