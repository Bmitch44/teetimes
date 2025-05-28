# tests/conftest.py
import pytest
from sqlmodel import SQLModel, create_engine, Session
from fastapi.testclient import TestClient

from src.db import get_session # Original get_session
from src.main import app # Your FastAPI app
from src.models import Course, TeeTime # Import your models

# Use an in-memory SQLite database for testing
DATABASE_URL_TEST = "sqlite:///./test_teetimes.db" # Or "sqlite:///:memory:" but file DB is easier to inspect
engine_test = create_engine(DATABASE_URL_TEST, echo=False) # echo=False for cleaner test output

@pytest.fixture(scope="session", autouse=True)
def create_test_db():
    # Create the test database and tables
    SQLModel.metadata.create_all(engine_test)
    yield
    # Teardown: drop all tables or remove the DB file if needed
    # For simplicity, we can let it recreate if it exists or manage file deletion outside
    # For in-memory, it's automatically cleared. If file-based, it persists.
    # Let's try recreating each time for a clean state if file-based.
    # SQLModel.metadata.drop_all(engine_test) # This might be too aggressive if other sessions use it.
    # A better approach for file-based is to remove the file after tests run, or ensure clean tables.
    # For now, create_all is fine. We'll manage test.db manually or clear tables per test.

@pytest.fixture(scope="function") # Use "function" scope for per-test isolation
def db_session_test():
    # This fixture provides a test database session.
    # It creates tables, yields a session, and then clears tables.
    SQLModel.metadata.create_all(engine_test) # Ensure tables are created for each test
    connection = engine_test.connect()
    transaction = connection.begin()
    session = Session(bind=connection)
    yield session
    session.close()
    transaction.rollback() # Rollback any changes made during the test
    connection.close()
    SQLModel.metadata.drop_all(engine_test) # Clean up: drop tables after each test for isolation

@pytest.fixture(scope="function")
def client_test(db_session_test):
    # This fixture provides a TestClient for API testing.
    # It overrides the app's get_session dependency with the test session.
    def override_get_session():
        yield db_session_test
    
    app.dependency_overrides[get_session] = override_get_session
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear() # Clean up overrides
