"""
Contract tests for Health Check API GET /health/ready endpoint
These tests MUST FAIL before implementation - TDD requirement
"""
import pytest
import requests
from testcontainers.compose import DockerCompose
import time
from datetime import datetime


class TestHealthReadyAPI:
    """Contract tests for readiness check endpoint"""

    @pytest.fixture(scope="class")
    def docker_services(self):
        """Set up Docker services for contract testing"""
        with DockerCompose(".", compose_file_name="docker-compose.yml") as compose:
            # Wait for services to be ready
            time.sleep(30)
            yield compose

    def test_health_ready_endpoint_exists(self, docker_services):
        """Test that GET /health/ready endpoint exists and responds"""
        # This WILL FAIL until readiness endpoint is implemented
        response = requests.get("http://localhost:8080/health/ready", timeout=10)
        assert response.status_code in [200, 503]  # Either ready or not ready
        assert response.headers["content-type"] == "application/json"

    def test_health_ready_response_structure(self, docker_services):
        """Test that readiness response has required JSON structure"""
        response = requests.get("http://localhost:8080/health/ready", timeout=10)
        assert response.status_code in [200, 503]

        data = response.json()

        # Required fields per health-check-api.yaml contract
        assert "ready" in data
        assert "dependencies" in data

        # Validate field types
        assert isinstance(data["ready"], bool)
        assert isinstance(data["dependencies"], list)

    def test_health_ready_dependencies_structure(self, docker_services):
        """Test that dependencies array has proper structure"""
        response = requests.get("http://localhost:8080/health/ready", timeout=10)
        assert response.status_code in [200, 503]

        data = response.json()
        dependencies = data["dependencies"]

        for dep in dependencies:
            # Each dependency must have required fields
            required_fields = {"name", "status", "response_time", "last_check"}
            assert set(dep.keys()) >= required_fields

            # Validate enum values and types
            assert dep["status"] in ["available", "degraded", "unavailable"]
            assert isinstance(dep["response_time"], (int, float))
            assert isinstance(dep["last_check"], str)

            # Validate timestamp format
            datetime.fromisoformat(dep["last_check"].replace('Z', '+00:00'))

    def test_health_ready_expected_dependencies(self, docker_services):
        """Test that all critical dependencies are checked for readiness"""
        response = requests.get("http://localhost:8080/health/ready", timeout=10)
        assert response.status_code in [200, 503]

        data = response.json()
        dependencies = data["dependencies"]

        # Critical dependencies for BookFairy Discord bot
        critical_deps = {
            "redis",
            "lazylibrarian",
            "prowlarr",
            "qbittorrent",
            "audiobookshelf",
            "lm-studio"
        }

        reported_deps = {dep["name"] for dep in dependencies}
        assert critical_deps.issubset(reported_deps)

    def test_health_ready_status_correlation(self, docker_services):
        """Test that ready status correlates with dependency availability"""
        response = requests.get("http://localhost:8080/health/ready", timeout=10)
        assert response.status_code in [200, 503]

        data = response.json()
        ready = data["ready"]
        dependencies = data["dependencies"]

        if response.status_code == 200:
            # Service reports as ready
            assert ready is True

            # All critical dependencies should be available or degraded (not unavailable)
            critical_deps = ["redis", "lazylibrarian", "prowlarr"]
            for dep in dependencies:
                if dep["name"] in critical_deps:
                    assert dep["status"] in ["available", "degraded"]

        elif response.status_code == 503:
            # Service not ready
            assert ready is False

            # At least one critical dependency should be unavailable
            critical_unavailable = any(
                dep["status"] == "unavailable"
                for dep in dependencies
                if dep["name"] in ["redis", "lazylibrarian", "prowlarr"]
            )
            assert critical_unavailable

    def test_health_ready_response_time_performance(self, docker_services):
        """Test readiness check performance requirements"""
        start_time = time.time()
        response = requests.get("http://localhost:8080/health/ready", timeout=15)
        response_time = time.time() - start_time

        assert response.status_code in [200, 503]
        # Readiness check should be fast but may take longer than basic health
        assert response_time < 15.0

        # Check individual dependency response times
        data = response.json()
        for dep in data["dependencies"]:
            # Each dependency check should be reasonable
            assert dep["response_time"] < 10.0

    def test_health_ready_error_response_structure(self, docker_services):
        """Test error response structure when service not ready"""
        response = requests.get("http://localhost:8080/health/ready", timeout=10)

        if response.status_code == 503:
            data = response.json()

            # Should follow HealthError schema from contract
            expected_fields = {"status", "timestamp", "service", "error"}

            # Might be in error format or ready format with ready=false
            if "error" in data:
                # Error format
                assert set(data.keys()) >= expected_fields
                assert data["status"] in ["unhealthy", "error"]
            else:
                # Ready format with ready=false
                assert data["ready"] is False

    def test_health_ready_method_restrictions(self, docker_services):
        """Test that only GET method is allowed on /health/ready"""
        # Test POST method should return 405
        response = requests.post("http://localhost:8080/health/ready", timeout=10)
        assert response.status_code == 405

        # Test PUT method should return 405
        response = requests.put("http://localhost:8080/health/ready", timeout=10)
        assert response.status_code == 405

    def test_health_ready_caching_headers(self, docker_services):
        """Test that readiness endpoint has appropriate caching headers"""
        response = requests.get("http://localhost:8080/health/ready", timeout=10)
        assert response.status_code in [200, 503]

        headers = response.headers

        # Readiness should not be cached for long periods
        cache_control = headers.get("Cache-Control", "")
        assert "no-cache" in cache_control or "max-age" not in cache_control or "max-age=0" in cache_control

    def test_health_ready_concurrent_requests(self, docker_services):
        """Test readiness endpoint handles concurrent requests properly"""
        import concurrent.futures
        import threading

        def make_request():
            return requests.get("http://localhost:8080/health/ready", timeout=10)

        # Make multiple concurrent requests
        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(make_request) for _ in range(10)]
            responses = [future.result() for future in futures]

        # All requests should complete successfully
        for response in responses:
            assert response.status_code in [200, 503]
            data = response.json()
            assert "ready" in data
            assert "dependencies" in data

    def test_health_ready_dependency_timeout_handling(self, docker_services):
        """Test that dependency timeouts are handled gracefully"""
        response = requests.get("http://localhost:8080/health/ready", timeout=20)
        assert response.status_code in [200, 503]

        data = response.json()
        dependencies = data["dependencies"]

        # Dependencies with high response times should be marked appropriately
        for dep in dependencies:
            if dep["response_time"] > 5.0:
                # Slow dependencies should be marked as degraded or unavailable
                assert dep["status"] in ["degraded", "unavailable"]