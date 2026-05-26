"""
Pytest Configuration and Fixtures
Shared fixtures for all tests
"""
import pytest
import asyncio
from typing import AsyncGenerator, Generator
from motor.motor_asyncio import AsyncIOMotorClient
from fastapi.testclient import TestClient

from app.main import app
from app.config import settings


# ==================== Event Loop ====================

@pytest.fixture(scope="session")
def event_loop() -> Generator:
    """
    Create event loop for async tests
    """
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


# ==================== Test Client ====================

@pytest.fixture
def client() -> TestClient:
    """
    Create FastAPI test client

    Returns:
        TestClient for making API requests
    """
    return TestClient(app)


# ==================== Database Fixtures ====================

@pytest.fixture
async def test_db() -> AsyncGenerator:
    """
    Create test database connection

    Yields:
        Test MongoDB database
    """
    # Create test database connection
    client = AsyncIOMotorClient(settings.mongodb_url)
    db = client[f"{settings.mongodb_db_name}_test"]

    yield db

    # Cleanup - drop test database after tests
    await client.drop_database(f"{settings.mongodb_db_name}_test")
    client.close()


# ==================== Mock Data ====================

@pytest.fixture
def mock_user_data():
    """
    Mock user data for testing

    Returns:
        Dict with user data
    """
    return {
        "email": "test@example.com",
        "password": "SecurePassword123!",
        "name": "Test User"
    }


@pytest.fixture
def mock_company_data():
    """
    Mock company data for testing

    Returns:
        Dict with company data
    """
    return {
        "name": "Test Company",
        "phone_number": "+1234567890",
        "description": "Test company description",
        "industry": "Technology"
    }


@pytest.fixture
def mock_knowledge_data():
    """
    Mock knowledge data for testing

    Returns:
        Dict with knowledge data
    """
    return {
        "title": "Test Document",
        "description": "Test document description",
        "tags": ["test", "documentation"]
    }


# ==================== Authentication Helpers ====================

@pytest.fixture
async def superadmin_token(client: TestClient, mock_user_data: dict) -> str:
    """
    Create superadmin user and return JWT token

    Args:
        client: Test client
        mock_user_data: Mock user data

    Returns:
        JWT access token
    """
    # Register superadmin (no company_id)
    register_data = {
        "email": "superadmin@example.com",
        "password": mock_user_data["password"],
        "name": "Super Admin"
    }

    response = client.post("/api/auth/register", json=register_data)
    assert response.status_code == 201

    return response.json()["access_token"]


@pytest.fixture
async def admin_token(client: TestClient, mock_user_data: dict, mock_company_data: dict) -> str:
    """
    Create admin user and return JWT token

    Args:
        client: Test client
        mock_user_data: Mock user data
        mock_company_data: Mock company data

    Returns:
        JWT access token
    """
    # First create superadmin to create company
    superadmin_data = {
        "email": "superadmin2@example.com",
        "password": mock_user_data["password"],
        "name": "Super Admin 2"
    }
    superadmin_response = client.post("/api/auth/register", json=superadmin_data)
    superadmin_token = superadmin_response.json()["access_token"]

    # Create company
    company_response = client.post(
        "/api/superadmin/companies",
        json=mock_company_data,
        headers={"Authorization": f"Bearer {superadmin_token}"}
    )
    company_id = company_response.json()["id"]

    # Create admin for that company
    admin_data = {
        "email": "admin@example.com",
        "password": mock_user_data["password"],
        "name": "Admin User",
        "company_id": company_id
    }

    response = client.post("/api/auth/register", json=admin_data)
    return response.json()["access_token"]


# ==================== Audio Test Data ====================

@pytest.fixture
def sample_audio_mulaw() -> bytes:
    """
    Sample mulaw audio data for testing

    Returns:
        Bytes of mulaw audio (silence)
    """
    # 160 bytes of mulaw silence (~20ms at 8kHz)
    return bytes([0xFF] * 160)


@pytest.fixture
def sample_audio_pcm() -> bytes:
    """
    Sample PCM audio data for testing

    Returns:
        Bytes of PCM audio (silence)
    """
    # 320 bytes of 16-bit PCM silence (~20ms at 8kHz)
    return bytes([0x00] * 320)


# ==================== AI Provider Mocks ====================

class MockSTTProvider:
    """Mock STT provider for testing"""

    async def transcribe(self, audio_data: bytes):
        """Mock transcribe method"""
        return type('obj', (object,), {'text': 'Hello, how can I help you?'})


class MockLLMProvider:
    """Mock LLM provider for testing"""

    async def generate(self, messages, **kwargs):
        """Mock generate method"""
        return type('obj', (object,), {
            'content': 'I am a test assistant. How can I help you today?',
            'usage': {'prompt_tokens': 10, 'completion_tokens': 15, 'total_tokens': 25}
        })


class MockTTSProvider:
    """Mock TTS provider for testing"""

    async def synthesize(self, text: str):
        """Mock synthesize method"""
        # Return fake WAV audio
        fake_wav = b'RIFF' + b'\x00' * 100
        return type('obj', (object,), {'audio_data': fake_wav, 'format': 'wav'})


class MockEmbeddingsProvider:
    """Mock embeddings provider for testing"""

    async def embed(self, texts: list):
        """Mock embed method"""
        # Return fake embeddings
        embeddings = [[0.1] * 1536 for _ in texts]
        return type('obj', (object,), {'embeddings': embeddings})


@pytest.fixture
def mock_stt_provider():
    """Mock STT provider fixture"""
    return MockSTTProvider()


@pytest.fixture
def mock_llm_provider():
    """Mock LLM provider fixture"""
    return MockLLMProvider()


@pytest.fixture
def mock_tts_provider():
    """Mock TTS provider fixture"""
    return MockTTSProvider()


@pytest.fixture
def mock_embeddings_provider():
    """Mock embeddings provider fixture"""
    return MockEmbeddingsProvider()
