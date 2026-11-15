import os

import pytest
from fastapi.testclient import TestClient

os.environ["CORS_ORIGINS"] = (
    "http://localhost:5173,http://127.0.0.1:5173"
)
os.environ["NASA_REQUEST_TIMEOUT_SECONDS"] = "20"

from app.main import app  # noqa: E402


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)
