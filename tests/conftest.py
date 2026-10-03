import os
# Set APP_ENV=testing before imports
os.environ["APP_ENV"] = "testing"
os.environ["DATABASE_URL"] = "sqlite:///:memory:"

import pytest
from fastapi.testclient import TestClient

import app.database as app_db
from app.database import Base, get_db
from app.main import app

# Bind in-memory SQLite to database engine
Base.metadata.create_all(bind=app_db.engine)


@pytest.fixture(scope="function")
def db_session():
    """Create a clean database session for a test function."""
    Base.metadata.create_all(bind=app_db.engine)
    db = app_db.SessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture(scope="function")
def client(db_session):
    """FastAPI TestClient with overridden database dependency."""
    def _override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = _override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()
