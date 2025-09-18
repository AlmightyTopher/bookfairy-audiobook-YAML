"""
Integration test for performance requirements
Based on quickstart.md Scenario 10
These tests MUST FAIL before implementation - TDD requirement
"""
import pytest
import requests
import time
import threading
import json
import statistics
from testcontainers.compose import DockerCompose


@pytest.fixture(scope="session")
def bookfairy_stack():
    """Fixture that starts the full BookFairy Docker Compose stack"""
    compose = DockerCompose("bookfairy/docker-compose.yml")
    compose.start()
    time.sleep(30)  # Wait for all services to be ready
    yield compose
    compose.stop()


class TestPerformance:
    """Test performance requirements and resource utilization"""

    def test_container_startup_performance(self, bookfairy_stack):
        """Test container startup time meets <30s requirement"""
        # Measure total startup time
        start_time = time.time()

        # Test Discord bot health endpoint responsiveness
        discord_bot_url = "http://localhost:8080"
        max_retries = 10
        retry_count = 0

        while retry_count < max_retries:
            try:
                response = requests.get(f"{discord_bot_url}/health", timeout=5)
                if response.status_code == 200:
                    break
            except:
                pass

            retry_count += 1
            time.sleep(2)  # Wait between retries

        end_time = time.time()
        total_startup_time = end_time - start_time

        # Expected to fail until Discord bot startup is optimized
        assert total_startup_time <= 30, f"Discord bot startup took {total_startup_time:.2f}s, exceeds 30s limit"

        # Should have responded within retry window
        assert retry_count < max_retries, "Discord bot did not become healthy within timeout"

    def test_health_check_performance(self, bookfairy_stack):
        """Test health check endpoints respond within <10s"""
        governance_url = "http://localhost:8080"

        # Test various health endpoints
        health_endpoints = [
            "/health",
            "/health/detailed",
            "/health/ready",
            "/health/cluster",
            "/health/governance"
        ]

        # Measure response times for each endpoint
        response_times = []
        max_response_time = 10  # seconds

        for endpoint in health_endpoints:
            start_time = time.time()

            response = requests.get(f"{governance_url}{endpoint}", timeout=max_response_time + 5)
            assert response.status_code == 200

            end_time = time.time()
            response_time = end_time - start_time
            response_times.append(response_time)

            # Expected to fail until health checks are optimized
            assert response_time <= max_response_time, \
                f"{endpoint} took {response_time:.3f}s, exceeds {max_response_time}s limit"

        # Calculate statistics
        avg_response_time = statistics.mean(response_times)
        max_response_time_actual = max(response_times)

        # Overall health check performance should be strong
        assert avg_response_time <= 5, f"Average health check time {avg_response_time:.3f}s exceeds 5s target"
        assert max_response_time_actual <= max_response_time

    def test_service_scaling_performance(self, bookfairy_stack):
        """Test system performance under concurrent load"""
        discord_bot_url = "http://localhost:8080"

        # Simulate concurrent users
        concurrent_users = 50
        test_duration = 30  # seconds
        successful_requests = 0
        total_requests = 0
        response_times = []

        def user_simulation(user_id):
            nonlocal successful_requests, total_requests
            user_start_time = time.time()

            while time.time() - user_start_time < test_duration:
                request_start = time.time()

                try:
                    # Simulate different types of requests
                    request_types = [
                        ("POST", f"{discord_bot_url}/orchestrate/search", {"query": f"user-{user_id}-search"}),
                        ("POST", f"{discord_bot_url}/orchestrate/recommend", {"user_id": f"user-{user_id}"}),
                        ("GET", f"{discord_bot_url}/workflow/status/test-{user_id}", None),
                    ]

                    request_type, url, data = random.choice(request_types)

                    if request_type == "GET":
                        response = requests.get(url, timeout=10)
                    else:
                        response = requests.post(url, json=data, timeout=10)

                    request_end = time.time()
                    response_time = request_end - request_start

                    if response.status_code in [200, 201, 202]:  # Acceptable success codes
                        successful_requests += 1
                        response_times.append(response_time)

                    total_requests += 1

                except Exception as e:
                    # Count failed requests but continue
                    total_requests += 1
                    continue

                # Random delay to simulate user think time
                time.sleep(random.uniform(0.1, 1.0))

        # Start concurrent user threads
        threads = []
        for user_id in range(concurrent_users):
            thread = threading.Thread(target=user_simulation, args=(user_id,))
            threads.append(thread)

        start_load_test = time.time()
        for thread in threads:
            thread.start()

        # Wait for test duration
        time.sleep(test_duration)

        end_load_test = time.time()
        actual_test_duration = end_load_test - start_load_test

        for thread in threads:
            thread.join()

        # Calculate performance metrics
        success_rate = (successful_requests / total_requests) * 100 if total_requests > 0 else 0
        requests_per_second = total_requests / actual_test_duration if actual_test_duration > 0 else 0

        if response_times:
            avg_response_time = statistics.mean(response_times)
            p95_response_time = statistics.quantiles(response_times, n=20)[18]  # 95th percentile
            max_response_time = max(response_times)
        else:
            avg_response_time = float('inf')
            p95_response_time = float('inf')
            max_response_time = float('inf')

        # Performance requirements (expected to fail until scaling optimizations)
        assert success_rate >= 95, f"Success rate {success_rate:.2f}% below 95% requirement"
        assert avg_response_time <= 2.0, f"Average response time {avg_response_time:.3f}s exceeds 2s limit"
        assert p95_response_time <= 5.0, f"P95 response time {p95_response_time:.3f}s exceeds 5s limit"
        assert requests_per_second >= 10, f"Throughput {requests_per_second:.2f} req/s below 10 req/s minimum"

    def test_resource_utilization_limits(self, bookfairy_stack):
        """Test resource usage stays within reasonable limits"""
        # Check container resource usage
        import docker

        client = docker.from_env()

        # Monitor key containers
        containers_to_monitor = [
            "bookfairy-discord-bot",
            "bookfairy-lazylibrarian",
            "bookfairy-audiobookshelf"
        ]

        for container_name in containers_to_monitor:
            try:
                container = client.containers.get(container_name)

                if container.status == "running":
                    stats = container.stats(stream=False)

                    # Check memory usage (should be reasonable for the workload)
                    memory_usage = stats.get('memory_stats', {}).get('usage', 0)
                    memory_limit = stats.get('memory_stats', {}).get('limit', 0)

                    if memory_limit > 0:
                        memory_percentage = (memory_usage / memory_limit) * 100
                        # Expected to pass, but monitor for reasonable usage
                        assert memory_percentage < 90, \
                            f"{container_name} using {memory_percentage:.1f}% of memory limit"

                    # Check CPU usage
                    cpu_delta = stats.get('cpu_stats', {}).get('cpu_usage', {}).get('total_usage', 0)
                    system_delta = stats.get('cpu_stats', {}).get('system_cpu_usage', 0)
                    prev_cpu_delta = stats.get('precpu_stats', {}).get('cpu_usage', {}).get('total_usage', 0)
                    prev_system_delta = stats.get('precpu_stats', {}).get('system_cpu_usage', 0)

                    if system_delta > prev_system_delta:
                        cpu_percentage = ((cpu_delta - prev_cpu_delta) / (system_delta - prev_system_delta)) * 100
                        # Check for reasonable CPU usage
                        assert cpu_percentage < 95, \
                            f"{container_name} using {cpu_percentage:.1f}% CPU"

            except docker.errors.NotFound:
                continue  # Container might not be running, skip

    def test_caching_performance_impact(self, bookfairy_stack):
        """Test Redis caching improves performance"""
        discord_bot_url = "http://localhost:8080"
        import redis

        redis_client = redis.Redis(host='localhost', port=6379)

        # Test recommendation performance with and without cache
        test_user = "perf-test-user"

        # Warm up cache
        warm_up_request = {
            "user_id": test_user,
            "books": ["Test Book 1", "Test Book 2"],
            "cache": True
        }

        # First request (should cache miss, then populate cache)
        start_time = time.time()
        response1 = requests.post(
            f"{discord_bot_url}/orchestrate/recommend",
            json={**warm_up_request, "cache": False},
            timeout=30
        )
        first_request_time = time.time() - start_time

        # Wait a moment for caching
        time.sleep(1)

        # Second request (should hit cache)
        start_time = time.time()
        response2 = requests.post(
            f"{discord_bot_url}/orchestrate/recommend",
            json=warm_up_request,
            timeout=30
        )
        second_request_time = time.time() - start_time

        # Expected to pass if responses are successful
        assert response1.status_code in [200, 201, 202]
        assert response2.status_code in [200, 201, 202]

        # Cache should provide performance improvement
        if first_request_time > 0 and second_request_time > 0:
            performance_improvement = first_request_time / second_request_time
            # Expected to fail until caching is properly implemented
            assert performance_improvement >= 2.0, \
                ".2f"".2f"".2f"

    def test_database_query_performance(self, bookfairy_stack):
        """Test audiobook metadata query performance"""
        audiobookshelf_url = "http://localhost:13378"

        # Test audiobook search performance
        search_queries = [
            "science fiction",
            "fantasy adventure",
            "mystery thriller"
        ]

        response_times = []

        for query in search_queries:
            start_time = time.time()

            response = requests.get(
                f"{audiobookshelf_url}/api/libraries/main/search",
                params={"q": query, "limit": 20},
                timeout=10
            )

            end_time = time.time()
            response_times.append(end_time - start_time)

            # Should return results in reasonable time
            assert response.status_code == 200

        if response_times:
            avg_search_time = statistics.mean(response_times)
            max_search_time = max(response_times)

            # Expected to fail until Audiobookshelf queries are optimized
            assert avg_search_time <= 3.0, f"Average search time {avg_search_time:.3f}s exceeds 3s limit"
            assert max_search_time <= 5.0, f"Max search time {max_search_time:.3f}s exceeds 5s limit"

    def test_network_latency_requirements(self, bookfairy_stack):
        """Test inter-service network latency meets requirements"""
        discord_bot_url = "http://localhost:8080"

        # Test network round-trip times
        latency_measurements = []
        test_iterations = 10

        for i in range(test_iterations):
            start_time = time.time()

            # Simple health check as latency test
            response = requests.get(f"{discord_bot_url}/health", timeout=5)

            end_time = time.time()
            latency = end_time - start_time
            latency_measurements.append(latency)

            assert response.status_code == 200

        if latency_measurements:
            avg_latency = statistics.mean(latency_measurements)
            p95_latency = statistics.quantiles(latency_measurements, n=20)[18]

            # Network latency should be reasonable
            assert avg_latency <= 0.5, f"Average network latency {avg_latency:.3f}s exceeds 500ms limit"
            assert p95_latency <= 1.0, f"P95 network latency {p95_latency:.3f}s exceeds 1s limit"

    def test_memory_leak_detection(self, bookfairy_stack):
        """Test for memory leaks over sustained operation"""
        import psutil
        import os

        # Get process information for key services
        discord_process = None

        for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
            if 'discord-bot' in str(proc.info.get('cmdline', [])):
                discord_process = proc
                break

        if discord_process:
            # Monitor memory usage over time
            memory_readings = []
            monitoring_duration = 300  # 5 minutes
            monitoring_interval = 30  # 30 seconds

            for i in range(monitoring_duration // monitoring_interval):
                try:
                    memory_mb = discord_process.memory_info().rss / (1024 * 1024)
                    memory_readings.append(memory_mb)
                    time.sleep(monitoring_interval)
                except psutil.NoSuchProcess:
                    break

            if len(memory_readings) >= 3:
                # Check for significant memory growth trend
                first_reading = memory_readings[0]
                last_reading = memory_readings[-1]
                memory_growth = last_reading - first_reading

                # Allow some memory growth but check for excessive leaks
                # Expected to pass normally, fail if significant memory leak
                assert memory_growth <= (first_reading * 0.2), \
                    f"Memory growth {memory_growth:.1f}MB exceeds 20% of initial {first_reading:.1f}MB"

                # Check for steady upward trend that would indicate a leak
                growth_trend = statistics.linear_regression(
                    [i for i in range(len(memory_readings))],
                    memory_readings
                )[0]  # Slope of linear regression

                # Expected to pass, fail if consistent upward memory trend
                assert growth_trend <= 1.0, \
                    f"Memory growth trend {growth_trend:.2f}MB/minute indicates possible leak"

    def test_performance_regression_detection(self, bookfairy_stack):
        """Test performance regression detection and alerting"""
        discord_bot_url = "http://localhost:8080"

        # Establish baseline performance
        baseline_measurements = []
        baseline_iterations = 5

        for i in range(baseline_iterations):
            start_time = time.time()
            response = requests.post(
                f"{discord_bot_url}/orchestrate/search",
                json={"query": f"baseline-test-{i}"},
                timeout=10
            )
            end_time = time.time()

            if response.status_code == 200:
                baseline_measurements.append(end_time - start_time)

            time.sleep(1)

        if baseline_measurements:
            baseline_avg = statistics.mean(baseline_measurements)

            # Test for performance regression
            regression_measurements = []
            regression_threshold = baseline_avg * 2.0  # 100% degradation

            for i in range(3):  # Quick regression check
                start_time = time.time()
                response = requests.post(
                    f"{discord_bot_url}/orchestrate/search",
                    json={"query": f"regression-test-{i}"},
                    timeout=int(regression_threshold + 5)
                )
                end_time = time.time()

                if response.status_code == 200:
                    regression_measurements.append(end_time - start_time)

            if regression_measurements:
                current_avg = statistics.mean(regression_measurements)

                # Expected to pass (no significant regression)
                assert current_avg <= regression_threshold, \
                    f"Performance regression detected: {current_avg:.3f}s vs baseline {baseline_avg:.3f}s"

                # Should issue warning for meaningful but non-critical degradation
                if current_avg > baseline_avg * 1.5:
                    # This would normally trigger monitoring alerts
                    print(".2f")

# Helper imports for multi-threading and randomization
import random
import math

if __name__ == "__main__":
    pytest.main([__file__])
