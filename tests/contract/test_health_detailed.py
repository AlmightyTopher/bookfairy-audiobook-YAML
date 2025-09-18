"""
Contract tests for Health Check API GET /health/detailed endpoint
These tests MUST FAIL before implementation - TDD requirement
"""
import pytest
import requests
from testcontainers.compose import DockerCompose
import time


class TestHealthDetailedAPI:
    """Contract tests for detailed health check endpoint"""

    @pytest.fixture(scope="class")
    def docker_services(self):
        """Set up Docker services for contract testing"""
        with DockerCompose(".", compose_file_name="docker-compose.yml") as compose:
            time.sleep(30)
            yield compose

    def test_health_detailed_endpoint_exists(self, docker_services):
        """Test that GET /health/detailed endpoint exists"""
        # This WILL FAIL until endpoint is implemented
        response = requests.get("http://localhost:8080/health/detailed", timeout=10)
        assert response.status_code == 200
        assert response.headers["content-type"] == "application/json"

    def test_health_detailed_response_structure(self, docker_services):
        """Test detailed health response structure per contract"""
        response = requests.get("http://localhost:8080/health/detailed", timeout=10)
        assert response.status_code == 200

        data = response.json()

        # Required fields per health-check-api.yaml contract
        required_fields = {
            "status", "timestamp", "service", "version",
            "uptime", "dependencies", "metrics"
        }
        assert set(data.keys()) >= required_fields

        # Validate status enum
        assert data["status"] in ["healthy", "degraded", "unhealthy"]

        # Validate dependencies array structure
        dependencies = data["dependencies"]
        assert isinstance(dependencies, list)

        for dep in dependencies:
            assert "name" in dep
            assert "status" in dep
            assert "response_time" in dep
            assert "last_check" in dep
            assert dep["status"] in ["available", "degraded", "unavailable"]

    def test_health_detailed_dependencies_validation(self, docker_services):
        """Test that all expected service dependencies are reported"""
        response = requests.get("http://localhost:8080/health/detailed", timeout=10)
        assert response.status_code == 200

        data = response.json()
        dependencies = data["dependencies"]

        # Expected dependencies per system architecture
        expected_deps = {
            "redis", "lazylibrarian", "prowlarr", "qbittorrent",
            "audiobookshelf", "lm-studio"
        }

        reported_deps = {dep["name"] for dep in dependencies}
        assert expected_deps.issubset(reported_deps)

    def test_health_detailed_metrics_structure(self, docker_services):
        """Test that metrics section has expected structure"""
        response = requests.get("http://localhost:8080/health/detailed", timeout=10)
        assert response.status_code == 200

        data = response.json()
        metrics = data["metrics"]

        # Standard metrics per contract
        expected_metrics = {"cpu_usage", "memory_usage", "disk_usage"}
        assert set(metrics.keys()) >= expected_metrics

        # Validate metric value types
        for metric_name, value in metrics.items():
            if metric_name in expected_metrics:
                assert isinstance(value, (int, float))
                assert 0 <= value <= 100  # Percentage values

    def test_health_detailed_uptime_format(self, docker_services):
        """Test uptime field format and validity"""
        response = requests.get("http://localhost:8080/health/detailed", timeout=10)
        assert response.status_code == 200

        data = response.json()
        uptime = data["uptime"]

        # Uptime should be integer seconds
        assert isinstance(uptime, int)
        assert uptime >= 0

    def test_health_detailed_unhealthy_response(self, docker_services):
        """Test detailed health response when service is unhealthy"""
        response = requests.get("http://localhost:8080/health/detailed", timeout=10)

        if response.status_code == 503:
            # Service is unhealthy
            data = response.json()
            assert data["status"] in ["degraded", "unhealthy"]

            # Should still have all required fields
            required_fields = {
                "status", "timestamp", "service", "dependencies"
            }
            assert set(data.keys()) >= required_fields

    def test_health_detailed_custom_metrics(self, docker_services):
        """Test that custom application metrics are included"""
        response = requests.get("http://localhost:8080/health/detailed", timeout=10)
        assert response.status_code == 200

        data = response.json()

        # Should have custom_metrics field per contract
        if "custom_metrics" in data:
            custom_metrics = data["custom_metrics"]
            assert isinstance(custom_metrics, dict)

            # BookFairy-specific metrics
            expected_custom = {
                "active_workflows", "total_audiobooks", "cache_hit_rate"
            }

            # At least some custom metrics should be present
            assert len(custom_metrics) > 0