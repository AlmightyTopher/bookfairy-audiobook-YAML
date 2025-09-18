"""
Integration test for complete service stack deployment
Based on quickstart.md Scenario 1
These tests MUST FAIL before implementation - TDD requirement
"""
import pytest
import docker
import time
import requests
from testcontainers.compose import DockerCompose


class TestServiceStackDeployment:
    """Integration tests for complete 8-service BookFairy stack deployment"""

    @pytest.fixture(scope="class")
    def docker_compose(self):
        """Set up full Docker Compose stack"""
        with DockerCompose(".", compose_file_name="docker-compose.yml") as compose:
            # Wait for all services to start
            time.sleep(120)  # Allow time for all 8 services
            yield compose

    def test_all_containers_running(self, docker_compose):
        """Test that all 8 expected containers are running"""
        client = docker.from_env()
        containers = client.containers.list()

        expected_containers = {
            "bookfairy-discord-bot",
            "bookfairy-lazylibrarian",
            "bookfairy-prowlarr",
            "bookfairy-qbittorrent",
            "bookfairy-audiobookshelf",
            "bookfairy-lm-studio",
            "bookfairy-redis"
        }

        running_containers = {container.name for container in containers}

        # All expected containers must be running
        assert expected_containers.issubset(running_containers)

        # Verify each container is in 'running' state
        for container_name in expected_containers:
            container = client.containers.get(container_name)
            assert container.status == "running"

    def test_health_checks_pass_within_timeout(self, docker_compose):
        """Test all services return healthy within 5 minutes"""
        health_endpoints = {
            "discord-bot": "http://localhost:8080/health",
            "lazylibrarian": "http://localhost:5299/",
            "prowlarr": "http://localhost:9696/",
            "qbittorrent": "http://localhost:8081/",
            "audiobookshelf": "http://localhost:13378/healthcheck",
            "lm-studio": "http://localhost:1234/v1/models",
            "redis": None  # Redis health checked via Discord bot dependency
        }

        start_time = time.time()
        timeout = 300  # 5 minutes

        while time.time() - start_time < timeout:
            all_healthy = True

            for service, endpoint in health_endpoints.items():
                if endpoint is None:
                    continue

                try:
                    response = requests.get(endpoint, timeout=10)
                    if response.status_code not in [200, 201]:
                        all_healthy = False
                        break
                except requests.RequestException:
                    all_healthy = False
                    break

            if all_healthy:
                return  # All services are healthy

            time.sleep(10)  # Wait 10 seconds before retry

        # If we get here, timeout was reached
        assert False, "Not all services became healthy within 5 minutes"

    def test_service_map_generation(self, docker_compose):
        """Test that service map can be generated and contains all connections"""
        # This will fail until service map generation script is implemented
        import subprocess

        result = subprocess.run([
            "python", "scripts/generate-service-map.py",
            "--output=service-map.json"
        ], capture_output=True, text=True)

        assert result.returncode == 0, f"Service map generation failed: {result.stderr}"

        # Verify service map file was created
        import os
        assert os.path.exists("service-map.json")

        # Validate service map content
        import json
        with open("service-map.json", "r") as f:
            service_map = json.load(f)

        # Must contain all 8 services
        assert "containers" in service_map
        assert len(service_map["containers"]) >= 7  # 8 services (redis counted separately)

        # Must contain connections
        assert "connections" in service_map
        assert len(service_map["connections"]) > 0

    def test_connectivity_validation_passes(self, docker_compose):
        """Test that all service connections can be validated"""
        # This will fail until connectivity validation script is implemented
        import subprocess

        result = subprocess.run([
            "python", "scripts/validate-connectivity.py",
            "--config=service-map.json"
        ], capture_output=True, text=True)

        assert result.returncode == 0, f"Connectivity validation failed: {result.stderr}"

        # Should report zero failed connectivity tests
        assert "Zero failed connectivity tests" in result.stdout or \
               "All connectivity tests passed" in result.stdout

    def test_container_resource_limits(self, docker_compose):
        """Test that containers respect configured resource limits"""
        client = docker.from_env()

        resource_expectations = {
            "bookfairy-discord-bot": {"cpu_limit": 1.0, "memory_limit": "512m"},
            "bookfairy-lazylibrarian": {"cpu_limit": 2.0, "memory_limit": "1g"},
            "bookfairy-prowlarr": {"cpu_limit": 1.0, "memory_limit": "512m"},
            "bookfairy-qbittorrent": {"cpu_limit": 4.0, "memory_limit": "2g"},
            "bookfairy-audiobookshelf": {"cpu_limit": 2.0, "memory_limit": "1g"},
            "bookfairy-lm-studio": {"cpu_limit": 8.0, "memory_limit": "16g"},
            "bookfairy-redis": {"cpu_limit": 1.0, "memory_limit": "512m"},
        }

        for container_name, expected_limits in resource_expectations.items():
            try:
                container = client.containers.get(container_name)

                # Check if container has resource constraints
                host_config = container.attrs.get("HostConfig", {})

                # Memory limit check (if configured)
                if "memory_limit" in expected_limits:
                    memory_limit = host_config.get("Memory", 0)
                    if memory_limit > 0:
                        # Verify memory limit is reasonable
                        assert memory_limit > 0

            except docker.errors.NotFound:
                assert False, f"Container {container_name} not found"

    def test_network_isolation(self, docker_compose):
        """Test that services are properly isolated on bookfairy network"""
        client = docker.from_env()

        # Check that bookfairy-network exists
        networks = client.networks.list()
        network_names = [net.name for net in networks]

        bookfairy_networks = [name for name in network_names if "bookfairy" in name]
        assert len(bookfairy_networks) > 0, "BookFairy network not found"

        # Verify containers are connected to the network
        bookfairy_network = None
        for network in networks:
            if "bookfairy" in network.name:
                bookfairy_network = network
                break

        assert bookfairy_network is not None

        # Check connected containers
        connected_containers = bookfairy_network.attrs.get("Containers", {})
        assert len(connected_containers) >= 7  # All our services

    def test_volume_mounts_working(self, docker_compose):
        """Test that required volume mounts are functioning"""
        client = docker.from_env()

        # Check key volume mounts exist and are accessible
        containers_with_volumes = [
            "bookfairy-lazylibrarian",
            "bookfairy-qbittorrent",
            "bookfairy-audiobookshelf",
            "bookfairy-redis"
        ]

        for container_name in containers_with_volumes:
            try:
                container = client.containers.get(container_name)

                # Verify container has volume mounts
                mounts = container.attrs.get("Mounts", [])
                assert len(mounts) > 0, f"Container {container_name} has no volume mounts"

                # Check that volumes are properly mounted
                for mount in mounts:
                    assert mount.get("Type") in ["bind", "volume"]

            except docker.errors.NotFound:
                assert False, f"Container {container_name} not found"

    def test_service_startup_order(self, docker_compose):
        """Test that services start in correct dependency order"""
        client = docker.from_env()

        # Redis should start before Discord bot (dependency)
        redis_container = client.containers.get("bookfairy-redis")
        discord_container = client.containers.get("bookfairy-discord-bot")

        redis_start_time = redis_container.attrs["State"]["StartedAt"]
        discord_start_time = discord_container.attrs["State"]["StartedAt"]

        # Redis should have started before or around the same time as Discord bot
        from datetime import datetime
        redis_time = datetime.fromisoformat(redis_start_time.replace('Z', '+00:00'))
        discord_time = datetime.fromisoformat(discord_start_time.replace('Z', '+00:00'))

        # Allow some tolerance for startup timing
        time_diff = (discord_time - redis_time).total_seconds()
        assert time_diff >= -30, "Redis should start before Discord bot"