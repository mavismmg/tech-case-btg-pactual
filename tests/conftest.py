import os
import pytest
from dotenv import load_dotenv

load_dotenv()

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import app.core.rate_limit as rate_limit_module
from app.core.database import Base
from app.dependencies import get_db
from app.models import account
from app.server import app

DATABASE_URL = os.getenv("TEST_DATABASE_URL")
if DATABASE_URL is None:
    raise RuntimeError("TEST_DATABASE_URL must be set for tests")

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


@pytest.fixture(scope="function")
def client(db):
    def override_get_db():
        try:
            yield db
        finally:
            pass

    previous_rate_limit_enabled = rate_limit_module.RATE_LIMIT_ENABLED
    rate_limit_module.RATE_LIMIT_ENABLED = False
    app.dependency_overrides[get_db] = override_get_db

    try:
        with TestClient(app) as test_client:
            yield test_client
    finally:
        app.dependency_overrides.clear()
        rate_limit_module.RATE_LIMIT_ENABLED = previous_rate_limit_enabled
