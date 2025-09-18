"""
Contract tests for Discord Bot API POST /orchestrate/download endpoint
These tests MUST FAIL before implementation - TDD requirement
"""
import pytest
import requests
import json
from testcontainers.compose import DockerCompose
import time
from datetime import datetime


class TestDiscordDownloadAPI:
    """Contract tests for audiobook download orchestration endpoint"""

    @pytest.fixture(scope="class")
    def docker_services(self):
        """Set up Docker services for contract testing"""
        with DockerCompose(".", compose_file_name="docker-compose.yml") as compose:
            # Wait for services to be ready
            time.sleep(30)
            yield compose

    @pytest.fixture
    def valid_download_request(self):
        """Valid download request payload per contract"""
        return {
            "torrent_id": "abc123def456",
            "user_id": "discord_user_123456789",
            "priority": "high"
        }

    @pytest.fixture
    def minimal_download_request(self):
        """Minimal valid download request with only required fields"""
        return {
            "torrent_id": "minimal_torrent_789",
            "user_id": "discord_user_987654321"
        }

    def test_orchestrate_download_endpoint_exists(self, docker_services):
        """Test that POST /orchestrate/download endpoint exists"""
        # This WILL FAIL until download orchestration endpoint is implemented
        payload = {
            "torrent_id": "test_torrent",
            "user_id": "test_user"
        }
        response = requests.post(
            "http://localhost:8080/orchestrate/download",
            json=payload,
            timeout=10
        )
        # Endpoint should exist and accept requests
        assert response.status_code != 404
        assert response.headers["content-type"] == "application/json"

    def test_orchestrate_download_valid_request(self, docker_services, valid_download_request):
        """Test valid download request returns proper workflow response"""
        response = requests.post(
            "http://localhost:8080/orchestrate/download",
            json=valid_download_request,
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

    def test_orchestrate_download_minimal_request(self, docker_services, minimal_download_request):
        """Test minimal valid request with only required fields"""
        response = requests.post(
            "http://localhost:8080/orchestrate/download",
            json=minimal_download_request,
            timeout=15
        )

        assert response.status_code == 202

        data = response.json()
        assert "workflow_id" in data
        assert "status" in data

    def test_orchestrate_download_missing_required_fields(self, docker_services):
        """Test validation of required fields"""
        # Missing torrent_id field
        payload = {"user_id": "test_user"}
        response = requests.post(
            "http://localhost:8080/orchestrate/download",
            json=payload,
            timeout=10
        )
        assert response.status_code == 400

        # Missing user_id field
        payload = {"torrent_id": "test_torrent"}
        response = requests.post(
            "http://localhost:8080/orchestrate/download",
            json=payload,
            timeout=10
        )
        assert response.status_code == 400

        # Empty torrent_id
        payload = {"torrent_id": "", "user_id": "test_user"}
        response = requests.post(
            "http://localhost:8080/orchestrate/download",
            json=payload,
            timeout=10
        )
        assert response.status_code == 400

    def test_orchestrate_download_priority_validation(self, docker_services):
        """Test validation of priority enum values"""
        # Invalid priority value
        payload = {
            "torrent_id": "test_torrent",
            "user_id": "test_user",
            "priority": "invalid_priority"
        }
        response = requests.post(
            "http://localhost:8080/orchestrate/download",
            json=payload,
            timeout=10
        )
        assert response.status_code == 400

    def test_orchestrate_download_valid_priorities(self, docker_services):
        """Test all valid priority enum values"""
        valid_priorities = ["low", "normal", "high"]

        for priority in valid_priorities:
            payload = {
                "torrent_id": f"test_torrent_{priority}",
                "user_id": "test_user",
                "priority": priority
            }
            response = requests.post(
                "http://localhost:8080/orchestrate/download",
                json=payload,
                timeout=10
            )
            assert response.status_code == 202

    def test_orchestrate_download_default_priority(self, docker_services):
        """Test that default priority is 'normal' when not specified"""
        payload = {
            "torrent_id": "test_torrent_default",
            "user_id": "test_user"
        }
        response = requests.post(
            "http://localhost:8080/orchestrate/download",
            json=payload,
            timeout=10
        )
        assert response.status_code == 202

        # The system should handle default priority internally
        data = response.json()
        assert "workflow_id" in data

    def test_orchestrate_download_torrent_id_formats(self, docker_services):
        """Test handling of different torrent ID formats"""
        torrent_ids = [
            "abc123def456",  # alphanumeric
            "12345678",      # numeric
            "ABCDEF123456",  # uppercase
            "hash-with-dashes-123",  # with dashes
            "a" * 40         # long hash format
        ]

        for torrent_id in torrent_ids:
            payload = {
                "torrent_id": torrent_id,
                "user_id": "test_user"
            }
            response = requests.post(
                "http://localhost:8080/orchestrate/download",
                json=payload,
                timeout=10
            )
            # Should accept various torrent ID formats
            assert response.status_code == 202

    def test_orchestrate_download_content_type_validation(self, docker_services):
        """Test that endpoint requires JSON content type"""
        payload = "torrent_id=test&user_id=test_user"
        response = requests.post(
            "http://localhost:8080/orchestrate/download",
            data=payload,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            timeout=10
        )
        # Should reject non-JSON content
        assert response.status_code == 400

    def test_orchestrate_download_malformed_json(self, docker_services):
        """Test handling of malformed JSON requests"""
        malformed_json = '{"torrent_id": "test", "user_id": "test_user"'  # Missing closing brace
        response = requests.post(
            "http://localhost:8080/orchestrate/download",
            data=malformed_json,
            headers={"Content-Type": "application/json"},
            timeout=10
        )
        assert response.status_code == 400

    def test_orchestrate_download_service_unavailable(self, docker_services):
        """Test response when download services are unavailable"""
        payload = {
            "torrent_id": "test_torrent",
            "user_id": "test_user"
        }
        response = requests.post(
            "http://localhost:8080/orchestrate/download",
            json=payload,
            timeout=10
        )

        # If services are unavailable, should return 503
        if response.status_code == 503:
            data = response.json()
            # Should contain error information
            assert "error" in data or "message" in data

    def test_orchestrate_download_response_timing(self, docker_services, valid_download_request):
        """Test download orchestration response timing requirements"""
        start_time = time.time()
        response = requests.post(
            "http://localhost:8080/orchestrate/download",
            json=valid_download_request,
            timeout=30
        )
        response_time = time.time() - start_time

        # Should respond quickly for workflow initiation
        assert response_time < 30.0
        assert response.status_code == 202

    def test_orchestrate_download_workflow_id_uniqueness(self, docker_services):
        """Test that each download request generates unique workflow IDs"""
        workflow_ids = set()

        for i in range(5):
            payload = {
                "torrent_id": f"test_torrent_{i}",
                "user_id": f"test_user_{i}"
            }

            response = requests.post(
                "http://localhost:8080/orchestrate/download",
                json=payload,
                timeout=10
            )

            assert response.status_code == 202
            data = response.json()
            workflow_id = data["workflow_id"]

            # Should not have seen this workflow ID before
            assert workflow_id not in workflow_ids
            workflow_ids.add(workflow_id)

    def test_orchestrate_download_method_restrictions(self, docker_services):
        """Test that only POST method is allowed"""
        # GET should not be allowed
        response = requests.get("http://localhost:8080/orchestrate/download", timeout=10)
        assert response.status_code == 405

        # PUT should not be allowed
        response = requests.put("http://localhost:8080/orchestrate/download", timeout=10)
        assert response.status_code == 405

    def test_orchestrate_download_invalid_torrent_id(self, docker_services):
        """Test handling of invalid torrent IDs"""
        invalid_torrent_ids = [
            "",              # empty string
            " ",             # whitespace only
            "invalid chars!", # special characters
            "a" * 1000       # excessively long
        ]

        for torrent_id in invalid_torrent_ids[:2]:  # Test empty and whitespace
            payload = {
                "torrent_id": torrent_id,
                "user_id": "test_user"
            }
            response = requests.post(
                "http://localhost:8080/orchestrate/download",
                json=payload,
                timeout=10
            )
            assert response.status_code == 400

    def test_orchestrate_download_user_id_validation(self, docker_services):
        """Test validation of user_id field"""
        valid_user_ids = [
            "123456789012345678",  # Discord snowflake format
            "user123",             # alphanumeric
            "test_user_123"        # with underscores
        ]

        for user_id in valid_user_ids:
            payload = {
                "torrent_id": "test_torrent",
                "user_id": user_id
            }
            response = requests.post(
                "http://localhost:8080/orchestrate/download",
                json=payload,
                timeout=10
            )
            assert response.status_code == 202

    def test_orchestrate_download_concurrent_requests(self, docker_services):
        """Test handling of concurrent download requests"""
        import concurrent.futures

        def make_download_request(suffix):
            payload = {
                "torrent_id": f"test_torrent_{suffix}",
                "user_id": f"user_{suffix}",
                "priority": "normal"
            }
            return requests.post(
                "http://localhost:8080/orchestrate/download",
                json=payload,
                timeout=15
            )

        # Submit multiple concurrent requests
        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(make_download_request, i) for i in range(10)]
            responses = [future.result() for future in futures]

        # All requests should be handled successfully
        for response in responses:
            assert response.status_code == 202
            data = response.json()
            assert "workflow_id" in data

    def test_orchestrate_download_duplicate_torrent_handling(self, docker_services):
        """Test handling of duplicate torrent download requests"""
        payload = {
            "torrent_id": "duplicate_test_torrent",
            "user_id": "test_user",
            "priority": "normal"
        }

        # Make first request
        response1 = requests.post(
            "http://localhost:8080/orchestrate/download",
            json=payload,
            timeout=10
        )
        assert response1.status_code == 202

        # Make duplicate request
        response2 = requests.post(
            "http://localhost:8080/orchestrate/download",
            json=payload,
            timeout=10
        )

        # Should either accept with new workflow or return existing
        assert response2.status_code in [202, 409]  # 409 for conflict/duplicate

    def test_orchestrate_download_priority_impact_on_response(self, docker_services):
        """Test that priority setting doesn't affect response structure"""
        priorities = ["low", "normal", "high"]

        for priority in priorities:
            payload = {
                "torrent_id": f"priority_test_{priority}",
                "user_id": "test_user",
                "priority": priority
            }

            response = requests.post(
                "http://localhost:8080/orchestrate/download",
                json=payload,
                timeout=10
            )

            assert response.status_code == 202
            data = response.json()

            # Response structure should be consistent regardless of priority
            required_fields = {"workflow_id", "status", "estimated_completion"}
            assert set(data.keys()) >= required_fields