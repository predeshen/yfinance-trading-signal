"""Property-based tests for API endpoints"""
import pytest
from fastapi.testclient import TestClient


# Property 43 & 44: Health endpoint
def test_health_endpoint_properties():
    """
    Feature: trading-scanner-python, Property 43 & 44
    
    Property 43: Health endpoint response
    Property 44: Health status codes
    
    Validates: Requirements 12.2, 12.3
    """
    from app.main import app
    client = TestClient(app)
    
    # Test health endpoint
    response = client.get("/health")
    
    # Should return JSON
    assert response.headers["content-type"] == "application/json"
    
    # Should have status field
    data = response.json()
    assert "status" in data
    assert "database" in data
    
    # Status code should be 200 or 503
    assert response.status_code in [200, 503]
