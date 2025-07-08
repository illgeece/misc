"""Tests for the main FastAPI application."""

import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_root_endpoint():
    """Test the root endpoint."""
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["message"] == "DM Helper API"
    assert "version" in data
    assert data["status"] == "running"


def test_health_check():
    """Test the health check endpoint."""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"


def test_chat_endpoint():
    """Test the chat endpoint."""
    response = client.post(
        "/api/v1/chat/",
        json={
            "message": "Hello, DM Helper!",
            "session_id": "test_session"
        }
    )
    assert response.status_code == 200
    data = response.json()
    assert "message" in data
    assert data["session_id"] == "test_session"
    assert "sources" in data
    assert "suggested_actions" in data


def test_characters_endpoint():
    """Test the characters endpoint."""
    response = client.get("/api/v1/characters/")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)


def test_knowledge_sources_endpoint():
    """Test the knowledge sources endpoint."""
    response = client.get("/api/v1/knowledge/sources")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)