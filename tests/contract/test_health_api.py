"""
Contract tests for Health Check API GET /health endpoint
These tests MUST FAIL before implementation - TDD requirement
"""
import pytest
import requests
from testcontainers.compose import DockerCompose
import time
import json


class TestHealthCheckAPI:
    """Contract tests for basic health check endpoint"""

    @pytest.fixture(scope="class")
    def docker_services(self):
        """Set up Docker services for contract testing"""
        with DockerCompose(".", compose_file_name="docker-compose.yml") as compose:
            # Wait for services to be ready
            time.sleep(30)
            yield compose

    def test_health_endpoint_exists(self, docker_services):
        """Test that GET /health endpoint exists and responds"""
        # This WILL FAIL until Discord bot service is implemented
        response = requests.get("http://localhost:8080/health", timeout=10)
        assert response.status_code == 200
        assert response.headers["content-type"] == "application/json"

    def test_health_response_structure(self, docker_services):
        """Test that health response has required JSON structure"""
        response = requests.get("http://localhost:8080/health", timeout=10)
        assert response.status_code == 200

        data = response.json()

        # Required fields per health-check-api.yaml contract
        assert "status" in data
        assert "timestamp" in data
        assert "service" in data

        # Validate field types and values
        assert data["status"] in ["healthy", "unhealthy"]
        assert isinstance(data["timestamp"], str)
        assert data["service"] == "discord-bot"

    def test_health_response_timing(self, docker_services):
        """Test that health check responds within performance requirements"""
        start_time = time.time()
        response = requests.get("http://localhost:8080/health", timeout=10)
        response_time = time.time() - start_time

        assert response.status_code == 200
        # Performance requirement: <10s health check response
        assert response_time < 10.0

    def test_health_unhealthy_status_code(self, docker_services):
        """Test that unhealthy status returns 503"""
        # This tests the contract when service is unhealthy
        # Will initially fail as endpoint doesn't exist

        # Simulate unhealthy condition (this is a contract test)
        # Implementation should return 503 for unhealthy services
        response = requests.get("http://localhost:8080/health", timeout=10)

        if response.status_code == 503:
            data = response.json()
            assert data["status"] == "unhealthy"
        else:
            # Service is healthy, which is also valid
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "healthy"

    def test_health_endpoint_method_not_allowed(self, docker_services):
        """Test that only GET method is allowed on /health"""
        # Test POST method should return 405
        response = requests.post("http://localhost:8080/health", timeout=10)
        assert response.status_code == 405

    def test_health_json_schema_validation(self, docker_services):
        """Test health response matches OpenAPI schema exactly"""
        response = requests.get("http://localhost:8080/health", timeout=10)
        assert response.status_code == 200

        data = response.json()

        # Strict schema validation per health-check-api.yaml
        required_fields = {"status", "timestamp", "service"}
        assert set(data.keys()) >= required_fields

        # Validate timestamp format (ISO 8601)
        timestamp = data["timestamp"]
        # Should be parseable as ISO format
        from datetime import datetime
        datetime.fromisoformat(timestamp.replace('Z', '+00:00'))

    def test_health_cors_headers(self, docker_services):
        """Test that health endpoint includes proper CORS headers"""
        response = requests.get("http://localhost:8080/health", timeout=10)
        assert response.status_code == 200

        # Check for security headers
        headers = response.headers
        assert "Access-Control-Allow-Origin" in headers
        assert "Content-Security-Policy" in headers or "X-Content-Type-Options" in headers