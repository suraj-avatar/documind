"""
conftest.py — Shared pytest fixtures for the DocuMind test suite.
"""

import sys
import os
import pytest

# Add the app directory to sys.path so imports resolve without installation
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'app'))

from fastapi.testclient import TestClient
from main import app


@pytest.fixture(scope="module")
def client():
    """A FastAPI TestClient that persists across the module's tests."""
    with TestClient(app) as c:
        yield c
