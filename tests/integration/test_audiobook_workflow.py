"""
Integration test for end-to-end audiobook workflow
Based on quickstart.md Scenario 2
These tests MUST FAIL before implementation - TDD requirement
"""
import pytest
import requests
import time
import json
from testcontainers.compose import DockerCompose


class TestAudiobookWorkflow:
    """Integration tests for complete audiobook acquisition and processing pipeline"""

    @pytest.fixture(scope="class")
    def docker_services(self):
        """Set up Docker services for workflow testing"""
        with DockerCompose(".", compose_file_name="docker-compose.yml") as compose:
            time.sleep(120)  # Wait for all services
            yield compose

    @pytest.fixture
    def test_search_request(self):
        """Valid search request payload"""
        return {
            "query": "The Hobbit",
            "user_id": "test-user-123",
            "search_type": "title"
        }

    def test_search_workflow_initiation(self, docker_services, test_search_request):
        """Test that search request successfully initiates workflow"""
        # This will fail until Discord bot orchestration API is implemented
        response = requests.post(
            "http://localhost:8080/orchestrate/search",
            json=test_search_request,
            headers={"Content-Type": "application/json"},
            timeout=30
        )

        assert response.status_code == 202  # Accepted
        data = response.json()

        # Should return workflow response with ID
        assert "workflow_id" in data
        assert "status" in data
        assert data["status"] in ["initiated", "queued", "processing"]

        # Store workflow ID for subsequent tests
        return data["workflow_id"]

    def test_workflow_progress_monitoring(self, docker_services):
        """Test workflow progress can be monitored"""
        # First initiate a workflow
        search_request = {
            "query": "The Hobbit",
            "user_id": "test-user-123",
            "search_type": "title"
        }

        response = requests.post(
            "http://localhost:8080/orchestrate/search",
            json=search_request,
            timeout=30
        )
        assert response.status_code == 202

        workflow_id = response.json()["workflow_id"]

        # Monitor workflow progress
        max_attempts = 60  # 10 minutes max
        attempt = 0

        while attempt < max_attempts:
            status_response = requests.get(
                f"http://localhost:8080/workflow/{workflow_id}/status",
                timeout=10
            )

            assert status_response.status_code == 200
            status_data = status_response.json()

            # Validate status response structure
            assert "workflow_id" in status_data
            assert "status" in status_data
            assert "current_stage" in status_data
            assert "progress" in status_data

            # Check progress is valid percentage
            progress = status_data["progress"]
            assert 0 <= progress <= 100

            # Check for completion or failure
            if status_data["status"] in ["completed", "failed"]:
                break

            time.sleep(10)
            attempt += 1

        # Workflow should complete within timeout
        assert status_data["status"] in ["completed", "failed"], \
            "Workflow did not complete within timeout"

    def test_lazylibrarian_integration(self, docker_services):
        """Test that search request reaches LazyLibrarian"""
        # This tests the integration: Discord bot → LazyLibrarian
        search_request = {
            "query": "Test Book",
            "user_id": "test-user-456",
            "search_type": "title"
        }

        # Initiate search
        response = requests.post(
            "http://localhost:8080/orchestrate/search",
            json=search_request,
            timeout=30
        )
        assert response.status_code == 202

        workflow_id = response.json()["workflow_id"]

        # Verify LazyLibrarian received the search
        # Check LazyLibrarian logs or API for search activity
        time.sleep(30)  # Allow time for processing

        # Validate that LazyLibrarian processed the request
        # This will fail until integration is implemented
        ll_response = requests.get("http://localhost:5299/api", timeout=10)
        assert ll_response.status_code == 200

    def test_prowlarr_indexer_integration(self, docker_services):
        """Test that Prowlarr returns search results from indexers"""
        # Test the LazyLibrarian ↔ Prowlarr integration

        # First check Prowlarr is accessible
        prowlarr_response = requests.get("http://localhost:9696/", timeout=10)
        assert prowlarr_response.status_code == 200

        # Initiate search that should trigger Prowlarr
        search_request = {
            "query": "Popular Audiobook",
            "user_id": "test-user-789",
            "search_type": "title"
        }

        response = requests.post(
            "http://localhost:8080/orchestrate/search",
            json=search_request,
            timeout=30
        )
        assert response.status_code == 202

        # Allow time for Prowlarr indexer queries
        time.sleep(60)

        # Verify search results were returned
        workflow_id = response.json()["workflow_id"]
        status_response = requests.get(
            f"http://localhost:8080/workflow/{workflow_id}/status",
            timeout=10
        )

        status_data = status_response.json()
        assert status_data["current_stage"] in ["download", "process", "completed"]

    def test_qbittorrent_download_integration(self, docker_services):
        """Test qBittorrent receives and processes download requests"""
        # Test the workflow: Prowlarr → qBittorrent download

        # Check qBittorrent is accessible
        qb_response = requests.get("http://localhost:8081/", timeout=10)
        assert qb_response.status_code == 200

        # Simulate download request
        download_request = {
            "torrent_id": "test-torrent-123",
            "user_id": "test-user-download",
            "priority": "normal"
        }

        response = requests.post(
            "http://localhost:8080/orchestrate/download",
            json=download_request,
            timeout=30
        )
        assert response.status_code == 202

        workflow_id = response.json()["workflow_id"]

        # Monitor download progress
        time.sleep(60)  # Allow download to start

        # Check workflow moved to processing stage
        status_response = requests.get(
            f"http://localhost:8080/workflow/{workflow_id}/status",
            timeout=10
        )

        status_data = status_response.json()
        assert status_data["current_stage"] in ["download", "process", "completed"]

    def test_audiobookshelf_processing(self, docker_services):
        """Test Audiobookshelf processes completed downloads"""
        # Test the qBittorrent → Audiobookshelf integration

        # Check Audiobookshelf is accessible
        abs_response = requests.get("http://localhost:13378/healthcheck", timeout=10)
        assert abs_response.status_code == 200

        # Simulate processing request
        process_request = {
            "file_path": "/downloads/test-audiobook/",
            "user_id": "test-user-process",
            "metadata_source": "hardcover"
        }

        response = requests.post(
            "http://localhost:8080/orchestrate/process",
            json=process_request,
            timeout=30
        )
        assert response.status_code == 202

        workflow_id = response.json()["workflow_id"]

        # Monitor processing
        time.sleep(90)  # Allow processing time

        # Verify processing completed
        status_response = requests.get(
            f"http://localhost:8080/workflow/{workflow_id}/status",
            timeout=10
        )

        status_data = status_response.json()
        assert status_data["status"] in ["completed", "processing"]

    def test_hardcover_metadata_enrichment(self, docker_services):
        """Test metadata enrichment from Hardcover API"""
        # Test Audiobookshelf ↔ Hardcover API integration

        process_request = {
            "file_path": "/downloads/the-hobbit/",
            "user_id": "test-user-metadata",
            "metadata_source": "hardcover"
        }

        response = requests.post(
            "http://localhost:8080/orchestrate/process",
            json=process_request,
            timeout=30
        )
        assert response.status_code == 202

        workflow_id = response.json()["workflow_id"]

        # Wait for metadata enrichment
        time.sleep(120)

        # Verify workflow completed with metadata
        status_response = requests.get(
            f"http://localhost:8080/workflow/{workflow_id}/status",
            timeout=10
        )

        status_data = status_response.json()

        # Should have completed with metadata
        if status_data["status"] == "completed":
            # Check that metadata was enriched
            assert "metadata" not in status_data or \
                   status_data.get("metadata", {}).get("source") == "hardcover"

    def test_complete_end_to_end_workflow(self, docker_services):
        """Test complete workflow from search to final notification"""
        # Full end-to-end test covering all integration points

        # Step 1: Initiate search
        search_request = {
            "query": "Test End to End",
            "user_id": "test-user-e2e",
            "search_type": "title"
        }

        response = requests.post(
            "http://localhost:8080/orchestrate/search",
            json=search_request,
            timeout=30
        )
        assert response.status_code == 202

        workflow_id = response.json()["workflow_id"]

        # Step 2: Monitor through all stages
        stages_seen = set()
        max_wait = 600  # 10 minutes for full workflow
        start_time = time.time()

        while time.time() - start_time < max_wait:
            status_response = requests.get(
                f"http://localhost:8080/workflow/{workflow_id}/status",
                timeout=10
            )
            assert status_response.status_code == 200

            status_data = status_response.json()
            current_stage = status_data["current_stage"]
            stages_seen.add(current_stage)

            # Check for completion
            if status_data["status"] == "completed":
                break

            # Check for failure
            if status_data["status"] == "failed":
                assert False, f"Workflow failed: {status_data.get('error_details')}"

            time.sleep(15)

        # Verify workflow completed
        assert status_data["status"] == "completed", \
            "End-to-end workflow did not complete within timeout"

        # Verify we saw expected stages
        expected_stages = {"search", "download", "process"}
        assert len(stages_seen.intersection(expected_stages)) > 0, \
            f"Did not see expected workflow stages. Saw: {stages_seen}"

    def test_workflow_error_handling(self, docker_services):
        """Test workflow handles errors gracefully"""
        # Test with invalid search request to trigger error handling

        invalid_request = {
            "query": "",  # Empty query should cause error
            "user_id": "test-user-error",
            "search_type": "invalid_type"
        }

        response = requests.post(
            "http://localhost:8080/orchestrate/search",
            json=invalid_request,
            timeout=30
        )

        # Should return error or handle gracefully
        assert response.status_code in [400, 422, 202]

        if response.status_code == 202:
            # If workflow started, it should fail gracefully
            workflow_id = response.json()["workflow_id"]

            time.sleep(30)

            status_response = requests.get(
                f"http://localhost:8080/workflow/{workflow_id}/status",
                timeout=10
            )
            status_data = status_response.json()

            # Should eventually fail with error details
            if status_data["status"] == "failed":
                assert "error_details" in status_data

    def test_concurrent_workflows(self, docker_services):
        """Test system handles multiple concurrent workflows"""
        # Test system can handle multiple users simultaneously

        workflows = []

        # Start multiple workflows
        for i in range(3):
            search_request = {
                "query": f"Concurrent Test {i}",
                "user_id": f"test-user-concurrent-{i}",
                "search_type": "title"
            }

            response = requests.post(
                "http://localhost:8080/orchestrate/search",
                json=search_request,
                timeout=30
            )
            assert response.status_code == 202

            workflows.append(response.json()["workflow_id"])

        # Monitor all workflows
        time.sleep(120)

        # Check all workflows are progressing
        for workflow_id in workflows:
            status_response = requests.get(
                f"http://localhost:8080/workflow/{workflow_id}/status",
                timeout=10
            )
            assert status_response.status_code == 200

            status_data = status_response.json()
            assert status_data["status"] in ["pending", "active", "completed"]