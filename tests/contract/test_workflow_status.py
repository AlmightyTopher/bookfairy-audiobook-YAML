"""
Contract tests for Discord Bot API GET /workflow/{workflow_id}/status endpoint
These tests MUST FAIL before implementation - TDD requirement
"""
import pytest
import requests
import json
from testcontainers.compose import DockerCompose
import time
from datetime import datetime
import uuid


class TestWorkflowStatusAPI:
    """Contract tests for workflow status tracking endpoint"""

    @pytest.fixture(scope="class")
    def docker_services(self):
        """Set up Docker services for contract testing"""
        with DockerCompose(".", compose_file_name="docker-compose.yml") as compose:
            # Wait for services to be ready
            time.sleep(30)
            yield compose

    @pytest.fixture
    def sample_workflow_id(self):
        """Generate a sample workflow ID for testing"""
        return str(uuid.uuid4())

    @pytest.fixture
    def known_workflow_ids(self):
        """List of known workflow IDs that might exist"""
        return [
            "test_workflow_123",
            "search_workflow_456",
            "download_workflow_789",
            "process_workflow_abc"
        ]

    def test_workflow_status_endpoint_exists(self, docker_services, sample_workflow_id):
        """Test that GET /workflow/{id}/status endpoint exists"""
        # This WILL FAIL until workflow status endpoint is implemented
        response = requests.get(
            f"http://localhost:8080/workflow/{sample_workflow_id}/status",
            timeout=10
        )
        # Endpoint should exist (either 200 for valid workflow or 404 for invalid)
        assert response.status_code in [200, 404]
        assert response.headers["content-type"] == "application/json"

    def test_workflow_status_valid_workflow_response(self, docker_services, known_workflow_ids):
        """Test valid workflow status response structure"""
        # Try with multiple potential workflow IDs
        for workflow_id in known_workflow_ids:
            response = requests.get(
                f"http://localhost:8080/workflow/{workflow_id}/status",
                timeout=10
            )

            if response.status_code == 200:
                # Found a valid workflow, test response structure
                data = response.json()

                # Required fields per WorkflowStatus schema
                required_fields = {
                    "workflow_id", "status", "current_stage", "progress",
                    "started_at"
                }
                assert set(data.keys()) >= required_fields

                # Validate field types and values
                assert isinstance(data["workflow_id"], str)
                assert data["status"] in ["pending", "active", "completed", "failed"]
                assert isinstance(data["current_stage"], str)
                assert isinstance(data["progress"], (int, float))
                assert 0.0 <= data["progress"] <= 100.0

                # Validate timestamps
                assert isinstance(data["started_at"], str)
                datetime.fromisoformat(data["started_at"].replace('Z', '+00:00'))

                # Optional completed_at field
                if "completed_at" in data:
                    assert isinstance(data["completed_at"], str)
                    datetime.fromisoformat(data["completed_at"].replace('Z', '+00:00'))

                # Optional error_details field
                if "error_details" in data:
                    assert isinstance(data["error_details"], dict)

                break

    def test_workflow_status_nonexistent_workflow(self, docker_services):
        """Test response for non-existent workflow ID"""
        nonexistent_id = "nonexistent_workflow_" + str(uuid.uuid4())
        response = requests.get(
            f"http://localhost:8080/workflow/{nonexistent_id}/status",
            timeout=10
        )

        # Should return 404 for non-existent workflow
        assert response.status_code == 404

        # Should still return JSON with error information
        data = response.json()
        assert "error" in data or "message" in data

    def test_workflow_status_invalid_workflow_id_format(self, docker_services):
        """Test handling of invalid workflow ID formats"""
        invalid_ids = [
            "",                    # empty string
            " ",                   # whitespace
            "invalid-chars!@#",    # special characters
            "a" * 1000            # extremely long ID
        ]

        for invalid_id in invalid_ids[:2]:  # Test first two cases
            response = requests.get(
                f"http://localhost:8080/workflow/{invalid_id}/status",
                timeout=10
            )

            # Should return 400 for invalid format or 404 for not found
            assert response.status_code in [400, 404]

    def test_workflow_status_progress_validation(self, docker_services, known_workflow_ids):
        """Test that progress values are within valid range"""
        for workflow_id in known_workflow_ids:
            response = requests.get(
                f"http://localhost:8080/workflow/{workflow_id}/status",
                timeout=10
            )

            if response.status_code == 200:
                data = response.json()
                progress = data["progress"]

                # Progress should be between 0 and 100
                assert 0.0 <= progress <= 100.0

                # Progress should make sense for status
                status = data["status"]
                if status == "pending":
                    assert progress == 0.0
                elif status == "completed":
                    assert progress == 100.0
                elif status == "failed":
                    # Failed workflows may have partial progress
                    assert 0.0 <= progress <= 100.0

    def test_workflow_status_consistency(self, docker_services, sample_workflow_id):
        """Test that repeated requests for same workflow return consistent data"""
        responses = []

        # Make multiple requests for the same workflow
        for _ in range(3):
            response = requests.get(
                f"http://localhost:8080/workflow/{sample_workflow_id}/status",
                timeout=10
            )
            responses.append(response)
            time.sleep(1)  # Small delay between requests

        # All responses should have same status code
        status_codes = [r.status_code for r in responses]
        assert len(set(status_codes)) == 1  # All should be the same

        if responses[0].status_code == 200:
            # If workflow exists, certain fields should remain consistent
            data_list = [r.json() for r in responses]

            # workflow_id should be consistent
            workflow_ids = [d["workflow_id"] for d in data_list]
            assert len(set(workflow_ids)) == 1

            # started_at should be consistent
            started_ats = [d["started_at"] for d in data_list]
            assert len(set(started_ats)) == 1

    def test_workflow_status_completed_workflow_fields(self, docker_services, known_workflow_ids):
        """Test that completed workflows have proper fields"""
        for workflow_id in known_workflow_ids:
            response = requests.get(
                f"http://localhost:8080/workflow/{workflow_id}/status",
                timeout=10
            )

            if response.status_code == 200:
                data = response.json()

                if data["status"] == "completed":
                    # Completed workflows should have completed_at timestamp
                    assert "completed_at" in data
                    assert isinstance(data["completed_at"], str)

                    # Progress should be 100%
                    assert data["progress"] == 100.0

                    # Should not have error_details
                    assert "error_details" not in data or data["error_details"] is None

    def test_workflow_status_failed_workflow_fields(self, docker_services, known_workflow_ids):
        """Test that failed workflows have proper fields"""
        for workflow_id in known_workflow_ids:
            response = requests.get(
                f"http://localhost:8080/workflow/{workflow_id}/status",
                timeout=10
            )

            if response.status_code == 200:
                data = response.json()

                if data["status"] == "failed":
                    # Failed workflows should have error_details
                    assert "error_details" in data
                    assert isinstance(data["error_details"], dict)
                    assert len(data["error_details"]) > 0

                    # May or may not have completed_at (depends on when it failed)
                    if "completed_at" in data:
                        assert isinstance(data["completed_at"], str)

    def test_workflow_status_method_restrictions(self, docker_services, sample_workflow_id):
        """Test that only GET method is allowed"""
        endpoint = f"http://localhost:8080/workflow/{sample_workflow_id}/status"

        # POST should not be allowed
        response = requests.post(endpoint, timeout=10)
        assert response.status_code == 405

        # PUT should not be allowed
        response = requests.put(endpoint, timeout=10)
        assert response.status_code == 405

        # DELETE should not be allowed
        response = requests.delete(endpoint, timeout=10)
        assert response.status_code == 405

    def test_workflow_status_response_timing(self, docker_services, known_workflow_ids):
        """Test workflow status response timing requirements"""
        for workflow_id in known_workflow_ids[:3]:  # Test first 3 IDs
            start_time = time.time()
            response = requests.get(
                f"http://localhost:8080/workflow/{workflow_id}/status",
                timeout=10
            )
            response_time = time.time() - start_time

            # Status check should be fast
            assert response_time < 10.0
            assert response.status_code in [200, 404]

    def test_workflow_status_caching_headers(self, docker_services, sample_workflow_id):
        """Test that status endpoint has appropriate caching headers"""
        response = requests.get(
            f"http://localhost:8080/workflow/{sample_workflow_id}/status",
            timeout=10
        )

        headers = response.headers

        # Status should not be cached for long periods as it changes
        cache_control = headers.get("Cache-Control", "")
        if "max-age" in cache_control:
            # If caching is allowed, it should be short-lived
            import re
            max_age_match = re.search(r'max-age=(\d+)', cache_control)
            if max_age_match:
                max_age = int(max_age_match.group(1))
                assert max_age <= 60  # Max 60 seconds caching

    def test_workflow_status_concurrent_requests(self, docker_services, known_workflow_ids):
        """Test handling of concurrent status requests"""
        import concurrent.futures

        def get_workflow_status(workflow_id):
            return requests.get(
                f"http://localhost:8080/workflow/{workflow_id}/status",
                timeout=10
            )

        # Submit concurrent requests for different workflows
        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            futures = [
                executor.submit(get_workflow_status, wf_id)
                for wf_id in known_workflow_ids
            ]
            responses = [future.result() for future in futures]

        # All requests should complete successfully
        for response in responses:
            assert response.status_code in [200, 404]

    def test_workflow_status_url_encoding(self, docker_services):
        """Test handling of URL-encoded workflow IDs"""
        # Test with URL-encoded characters
        encoded_ids = [
            "workflow%20with%20spaces",
            "workflow-with-dashes",
            "workflow_with_underscores"
        ]

        for workflow_id in encoded_ids:
            response = requests.get(
                f"http://localhost:8080/workflow/{workflow_id}/status",
                timeout=10
            )

            # Should handle encoded IDs gracefully
            assert response.status_code in [200, 404, 400]

    def test_workflow_status_different_workflow_types(self, docker_services):
        """Test status endpoint with different workflow types"""
        workflow_types = [
            "search_workflow_test",
            "download_workflow_test",
            "process_workflow_test",
            "recommend_workflow_test"
        ]

        for workflow_id in workflow_types:
            response = requests.get(
                f"http://localhost:8080/workflow/{workflow_id}/status",
                timeout=10
            )

            # All workflow types should use same status endpoint
            assert response.status_code in [200, 404]

            if response.status_code == 200:
                data = response.json()
                # Response structure should be consistent across workflow types
                assert "status" in data
                assert "progress" in data

    def test_workflow_status_current_stage_validation(self, docker_services, known_workflow_ids):
        """Test that current_stage field contains meaningful values"""
        stage_patterns = [
            "initializing", "searching", "downloading", "processing",
            "validating", "completing", "completed", "failed", "pending"
        ]

        for workflow_id in known_workflow_ids:
            response = requests.get(
                f"http://localhost:8080/workflow/{workflow_id}/status",
                timeout=10
            )

            if response.status_code == 200:
                data = response.json()
                current_stage = data["current_stage"]

                # Stage should be a non-empty string
                assert isinstance(current_stage, str)
                assert len(current_stage.strip()) > 0

                # Stage should be reasonable length
                assert len(current_stage) <= 100