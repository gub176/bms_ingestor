"""Tests for monitoring endpoints"""
import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_health_endpoint():
    """Test health check endpoint"""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"


def test_metrics_html():
    """Test metrics HTML page"""
    response = client.get("/metrics")
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
    assert "BMS Cloud Platform" in response.text


def test_metrics_data():
    """Test metrics JSON data"""
    response = client.get("/metrics/data")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, dict)


def test_metrics_text():
    """Test metrics Prometheus format"""
    response = client.get("/metrics/text")
    assert response.status_code == 200
    assert "text/plain" in response.headers["content-type"]
