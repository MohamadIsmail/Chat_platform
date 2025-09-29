import pytest
import asyncio
import httpx
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
import tempfile
import os
from unittest.mock import AsyncMock, MagicMock

from app.main import app
from app.core.database import Base, get_db
from app.core.cache import cache_manager
from app.models.user import User
from app.models.message import DirectMessage
from app.core.security import get_password_hash
from faker import Faker

fake = Faker()

# Test database URL (SQLite for testing)
SQLALCHEMY_DATABASE_URL = "sqlite:///./test_chat.db"

# Create test engine
engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)

TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="function")
def db_session():
    """Create a fresh database session for each test."""
    # Create tables
    Base.metadata.create_all(bind=engine)
    
    # Create session
    session = TestingSessionLocal()
    
    try:
        yield session
    finally:
        session.close()
        # Clean up tables
        Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="function")
def client(db_session):
    """Create a test client with database dependency override."""
    
    def override_get_db():
        try:
            yield db_session
        finally:
            pass
    
    # Override database dependency
    app.dependency_overrides[get_db] = override_get_db
    
    # Mock Redis cache manager
    cache_manager.redis = AsyncMock()
    cache_manager.is_available = AsyncMock(return_value=False)
    
    with TestClient(app) as test_client:
        yield test_client
    
    # Clean up
    app.dependency_overrides.clear()


@pytest.fixture(scope="function")
def async_client():
    """Create an async test client for async operations."""
    return httpx.AsyncClient(app=app, base_url="http://testserver")


@pytest.fixture(scope="function")
def test_user_data():
    """Generate test user data."""
    return {
        "username": fake.user_name(),
        "email": fake.email(),
        "password": fake.password(length=12)
    }


@pytest.fixture(scope="function")
def test_user(db_session, test_user_data):
    """Create a test user in the database."""
    user = User(
        username=test_user_data["username"],
        email=test_user_data["email"],
        hashed_password=get_password_hash(test_user_data["password"])
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture(scope="function")
def test_users(db_session, test_user_data):
    """Create multiple test users."""
    users = []
    for i in range(3):
        user_data = {
            "username": f"{test_user_data['username']}_{i}",
            "email": f"user{i}@test.com",
            "password": test_user_data["password"]
        }
        user = User(
            username=user_data["username"],
            email=user_data["email"],
            hashed_password=get_password_hash(user_data["password"])
        )
        db_session.add(user)
        users.append(user)
    
    db_session.commit()
    for user in users:
        db_session.refresh(user)
    
    return users


@pytest.fixture(scope="function")
def auth_headers(client, test_user, test_user_data):
    """Get authentication headers for a test user."""
    # Login to get token
    response = client.post(
        "/login",
        data={
            "username": test_user_data["username"],
            "password": test_user_data["password"]
        }
    )
    
    assert response.status_code == 200
    token = response.json()["access_token"]
    
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture(scope="function")
def test_message_data():
    """Generate test message data."""
    return {
        "content": fake.text(max_nb_chars=200),
        "recipient_id": 1
    }


@pytest.fixture(scope="function")
def test_messages(db_session, test_user, test_users):
    """Create test messages in the database."""
    messages = []
    for i, recipient in enumerate(test_users[:2]):
        message = DirectMessage(
            content=fake.text(max_nb_chars=100),
            sender_id=test_user.id,
            recipient_id=recipient.id
        )
        db_session.add(message)
        messages.append(message)
    
    db_session.commit()
    for message in messages:
        db_session.refresh(message)
    
    return messages


@pytest.fixture(scope="function")
def mock_redis():
    """Mock Redis cache for testing."""
    mock_redis = AsyncMock()
    mock_redis.get = AsyncMock(return_value=None)
    mock_redis.set = AsyncMock(return_value=True)
    mock_redis.delete = AsyncMock(return_value=True)
    mock_redis.exists = AsyncMock(return_value=False)
    mock_redis.keys = AsyncMock(return_value=[])
    mock_redis.ping = AsyncMock(return_value=True)
    
    return mock_redis


@pytest.fixture(scope="function")
def mock_cache_service(mock_redis):
    """Mock cache service for testing."""
    from app.core.cache import cache_service
    cache_service.cache_manager.redis = mock_redis
    cache_service.cache_manager.is_available = AsyncMock(return_value=True)
    cache_service.get = AsyncMock(return_value=None)
    cache_service.set = AsyncMock(return_value=True)
    cache_service.delete = AsyncMock(return_value=True)
    cache_service.exists = AsyncMock(return_value=False)
    
    return cache_service


class TestDataFactory:
    """Factory class for creating test data."""
    
    @staticmethod
    def create_user_data(username=None, email=None, password=None):
        """Create user data for testing."""
        return {
            "username": username or fake.user_name(),
            "email": email or fake.email(),
            "password": password or fake.password(length=12)
        }
    
    @staticmethod
    def create_message_data(content=None, recipient_id=None):
        """Create message data for testing."""
        return {
            "content": content or fake.text(max_nb_chars=200),
            "recipient_id": recipient_id or 1
        }
    
    @staticmethod
    def create_multiple_users(count=5):
        """Create multiple user data entries."""
        return [
            TestDataFactory.create_user_data() for _ in range(count)
        ]


@pytest.fixture(scope="function")
def data_factory():
    """Provide test data factory."""
    return TestDataFactory()


# Pytest configuration
def pytest_configure(config):
    """Configure pytest."""
    config.addinivalue_line(
        "markers", "slow: marks tests as slow (deselect with '-m \"not slow\"')"
    )
    config.addinivalue_line(
        "markers", "integration: marks tests as integration tests"
    )
    config.addinivalue_line(
        "markers", "e2e: marks tests as end-to-end tests"
    )


# Test utilities
class TestHelpers:
    """Helper functions for tests."""
    
    @staticmethod
    def assert_user_response(response_data, expected_user):
        """Assert user response data matches expected user."""
        assert response_data["id"] == expected_user.id
        assert response_data["username"] == expected_user.username
        assert response_data["email"] == expected_user.email
        assert "password" not in response_data
    
    @staticmethod
    def assert_message_response(response_data, expected_message):
        """Assert message response data matches expected message."""
        assert response_data["id"] == expected_message.id
        assert response_data["content"] == expected_message.content
        assert response_data["sender_id"] == expected_message.sender_id
        assert response_data["recipient_id"] == expected_message.recipient_id
        assert "created_at" in response_data
    
    @staticmethod
    def assert_error_response(response, status_code, detail=None):
        """Assert error response format."""
        assert response.status_code == status_code
        if detail:
            assert response.json()["detail"] == detail
    
    @staticmethod
    def create_auth_headers(token):
        """Create authorization headers."""
        return {"Authorization": f"Bearer {token}"}


@pytest.fixture(scope="function")
def helpers():
    """Provide test helpers."""
    return TestHelpers()
