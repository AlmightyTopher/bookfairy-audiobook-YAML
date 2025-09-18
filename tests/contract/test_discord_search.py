"""
Contract tests for Discord Bot API POST /orchestrate/search endpoint
These tests MUST FAIL before implementation - TDD requirement
"""
import pytest
import requests
import json
from testcontainers.compose import DockerCompose
import time
from datetime import datetime


class TestDiscordSearchAPI:
    """Contract tests for audiobook search orchestration endpoint"""

    @pytest.fixture(scope="class")
    def docker_services(self):
        """Set up Docker services for contract testing"""
        with DockerCompose(".", compose_file_name="docker-compose.yml") as compose:
            # Wait for services to be ready
            time.sleep(30)
            yield compose

    @pytest.fixture
    def valid_search_request(self):
        """Valid search request payload per contract"""
        return {
            "query": "The Hobbit",
            "user_id": "discord_user_123456789",
            "search_type": "title",
            "filters": {
                "language": "en",
                "format": "mp3"
            }
        }

    @pytest.fixture
    def minimal_search_request(self):
        """Minimal valid search request with only required fields"""
        return {
            "query": "Dune Frank Herbert",
            "user_id": "discord_user_987654321"
        }

    def test_orchestrate_search_endpoint_exists(self, docker_services):
        """Test that POST /orchestrate/search endpoint exists"""
        # This WILL FAIL until search orchestration endpoint is implemented
        payload = {
            "query": "test",
            "user_id": "test_user"
        }
        response = requests.post(
            "http://localhost:8080/orchestrate/search",
            json=payload,
            timeout=10
        )
        # Endpoint should exist and accept requests
        assert response.status_code != 404
        assert response.headers["content-type"] == "application/json"

    def test_orchestrate_search_valid_request(self, docker_services, valid_search_request):
        """Test valid search request returns proper workflow response"""
        response = requests.post(
            "http://localhost:8080/orchestrate/search",
            json=valid_search_request,
            timeout=15
        )

        # Should return 202 Accepted per contract
        assert response.status_code == 202

        data = response.json()

        # Required fields per WorkflowResponse schema
        required_fields = {"workflow_id", "status", "estimated_completion"}
        assert set(data.keys()) >= required_fields

        # Validate field types and values
        assert isinstance(data["workflow_id"], str)
        assert len(data["workflow_id"]) > 0
        assert data["status"] in ["initiated", "queued", "processing"]

        # Validate estimated_completion is ISO datetime
        datetime.fromisoformat(data["estimated_completion"].replace('Z', '+00:00'))

    def test_orchestrate_search_minimal_request(self, docker_services, minimal_search_request):
        """Test minimal valid request with only required fields"""
        response = requests.post(
            "http://localhost:8080/orchestrate/search",
            json=minimal_search_request,
            timeout=15
        )

        assert response.status_code == 202

        data = response.json()
        assert "workflow_id" in data
        assert "status" in data

    def test_orchestrate_search_missing_required_fields(self, docker_services):
        """Test validation of required fields"""
        # Missing query field
        payload = {"user_id": "test_user"}
        response = requests.post(
            "http://localhost:8080/orchestrate/search",
            json=payload,
            timeout=10
        )
        assert response.status_code == 400

        # Missing user_id field
        payload = {"query": "test query"}
        response = requests.post(
            "http://localhost:8080/orchestrate/search",
            json=payload,
            timeout=10
        )
        assert response.status_code == 400

        # Empty query
        payload = {"query": "", "user_id": "test_user"}
        response = requests.post(
            "http://localhost:8080/orchestrate/search",
            json=payload,
            timeout=10
        )
        assert response.status_code == 400

    def test_orchestrate_search_invalid_search_type(self, docker_services):
        """Test validation of search_type enum values"""
        payload = {
            "query": "Test Book",
            "user_id": "test_user",
            "search_type": "invalid_type"
        }
        response = requests.post(
            "http://localhost:8080/orchestrate/search",
            json=payload,
            timeout=10
        )
        assert response.status_code == 400

    def test_orchestrate_search_valid_search_types(self, docker_services):
        """Test all valid search_type enum values"""
        valid_types = ["title", "author", "series", "isbn"]

        for search_type in valid_types:
            payload = {
                "query": f"Test {search_type}",
                "user_id": "test_user",
                "search_type": search_type
            }
            response = requests.post(
                "http://localhost:8080/orchestrate/search",
                json=payload,
                timeout=10
            )
            assert response.status_code == 202

    def test_orchestrate_search_filters_validation(self, docker_services):
        """Test validation of optional filters"""
        # Invalid format enum
        payload = {
            "query": "Test Book",
            "user_id": "test_user",
            "filters": {
                "format": "invalid_format"
            }
        }
        response = requests.post(
            "http://localhost:8080/orchestrate/search",
            json=payload,
            timeout=10
        )
        assert response.status_code == 400

        # Valid format enums
        valid_formats = ["any", "mp3", "m4a", "flac"]
        for format_type in valid_formats:
            payload = {
                "query": "Test Book",
                "user_id": "test_user",
                "filters": {
                    "format": format_type
                }
            }
            response = requests.post(
                "http://localhost:8080/orchestrate/search",
                json=payload,
                timeout=10
            )
            assert response.status_code == 202

    def test_orchestrate_search_content_type_validation(self, docker_services):
        """Test that endpoint requires JSON content type"""
        payload = "query=test&user_id=test_user"
        response = requests.post(
            "http://localhost:8080/orchestrate/search",
            data=payload,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            timeout=10
        )
        # Should reject non-JSON content
        assert response.status_code == 400

    def test_orchestrate_search_malformed_json(self, docker_services):
        """Test handling of malformed JSON requests"""
        malformed_json = '{"query": "test", "user_id": "test_user"'  # Missing closing brace
        response = requests.post(
            "http://localhost:8080/orchestrate/search",
            data=malformed_json,
            headers={"Content-Type": "application/json"},
            timeout=10
        )
        assert response.status_code == 400

    def test_orchestrate_search_service_unavailable(self, docker_services):
        """Test response when search services are unavailable"""
        payload = {
            "query": "Test Book",
            "user_id": "test_user"
        }
        response = requests.post(
            "http://localhost:8080/orchestrate/search",
            json=payload,
            timeout=10
        )

        # If services are unavailable, should return 503
        if response.status_code == 503:
            data = response.json()
            # Should contain error information
            assert "error" in data or "message" in data

    def test_orchestrate_search_response_timing(self, docker_services, valid_search_request):
        """Test search orchestration response timing requirements"""
        start_time = time.time()
        response = requests.post(
            "http://localhost:8080/orchestrate/search",
            json=valid_search_request,
            timeout=30
        )
        response_time = time.time() - start_time

        # Should respond quickly for workflow initiation
        assert response_time < 30.0
        assert response.status_code == 202

    def test_orchestrate_search_workflow_id_uniqueness(self, docker_services, valid_search_request):
        """Test that each search request generates unique workflow IDs"""
        workflow_ids = set()

        for i in range(5):
            # Modify request slightly for each iteration
            request = valid_search_request.copy()
            request["query"] = f"Test Book {i}"

            response = requests.post(
                "http://localhost:8080/orchestrate/search",
                json=request,
                timeout=10
            )

            assert response.status_code == 202
            data = response.json()
            workflow_id = data["workflow_id"]

            # Should not have seen this workflow ID before
            assert workflow_id not in workflow_ids
            workflow_ids.add(workflow_id)

    def test_orchestrate_search_method_restrictions(self, docker_services):
        """Test that only POST method is allowed"""
        # GET should not be allowed
        response = requests.get("http://localhost:8080/orchestrate/search", timeout=10)
        assert response.status_code == 405

        # PUT should not be allowed
        response = requests.put("http://localhost:8080/orchestrate/search", timeout=10)
        assert response.status_code == 405

    def test_orchestrate_search_large_query_handling(self, docker_services):
        """Test handling of very large search queries"""
        # Very long query string
        long_query = "A" * 1000
        payload = {
            "query": long_query,
            "user_id": "test_user"
        }

        response = requests.post(
            "http://localhost:8080/orchestrate/search",
            json=payload,
            timeout=15
        )

        # Should either accept (202) or reject with validation error (400)
        assert response.status_code in [202, 400]

    def test_orchestrate_search_unicode_handling(self, docker_services):
        """Test handling of unicode characters in search queries"""
        unicode_queries = [
            "Les Misérables",
            "北京大学",
            "Война и мир",
            "🎧 Audiobook Test"
        ]

        for query in unicode_queries:
            payload = {
                "query": query,
                "user_id": "test_user"
            }

            response = requests.post(
                "http://localhost:8080/orchestrate/search",
                json=payload,
                timeout=10
            )

            # Should handle unicode gracefully
            assert response.status_code == 202

    def test_orchestrate_search_concurrent_requests(self, docker_services):
        """Test handling of concurrent search requests"""
        import concurrent.futures

        def make_search_request(query_suffix):
            payload = {
                "query": f"Test Book {query_suffix}",
                "user_id": f"user_{query_suffix}"
            }
            return requests.post(
                "http://localhost:8080/orchestrate/search",
                json=payload,
                timeout=15
            )

        # Submit multiple concurrent requests
        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(make_search_request, i) for i in range(10)]
            responses = [future.result() for future in futures]

        # All requests should be handled successfully
        for response in responses:
            assert response.status_code == 202
            data = response.json()
            assert "workflow_id" in data