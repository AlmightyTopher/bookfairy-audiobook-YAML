"""
Contract tests for Governance API POST /governance/validation-protocol/{deliverable_type} endpoint
These tests MUST FAIL before implementation - TDD requirement
"""
import pytest
import requests
import json
from testcontainers.compose import DockerCompose
import time
from datetime import datetime


class TestGovernanceValidationAPI:
    """Contract tests for validation protocol execution endpoint"""

    @pytest.fixture(scope="class")
    def docker_services(self):
        """Set up Docker services for contract testing"""
        with DockerCompose(".", compose_file_name="docker-compose.yml") as compose:
            # Wait for services to be ready
            time.sleep(30)
            yield compose

    @pytest.fixture
    def valid_validation_request(self):
        """Valid validation request payload per contract"""
        return {
            "component_id": "discord-bot-service-v1.0",
            "validation_context": {
                "environment": "staging",
                "deployment_target": "kubernetes",
                "dependencies": ["redis", "postgresql", "nginx"],
                "expected_load": "1000 concurrent users"
            },
            "custom_validation_steps": [
                "verify_health_endpoints",
                "test_discord_integration",
                "validate_database_connections"
            ]
        }

    @pytest.fixture
    def minimal_validation_request(self):
        """Minimal valid validation request with only required fields"""
        return {
            "component_id": "test-component-minimal",
            "validation_context": {
                "environment": "test"
            }
        }

    @pytest.fixture
    def valid_deliverable_types(self):
        """Valid deliverable types per contract"""
        return ["container", "service", "integration", "workflow", "system"]

    def test_governance_validation_protocol_endpoint_exists(self, docker_services, valid_deliverable_types, minimal_validation_request):
        """Test that POST /governance/validation-protocol/{type} endpoint exists"""
        # This WILL FAIL until validation protocol endpoint is implemented
        deliverable_type = valid_deliverable_types[0]  # Use first valid type
        response = requests.post(
            f"http://localhost:8080/governance/validation-protocol/{deliverable_type}",
            json=minimal_validation_request,
            timeout=10
        )
        # Endpoint should exist and accept requests
        assert response.status_code != 404
        assert response.headers["content-type"] == "application/json"

    def test_governance_validation_protocol_valid_request(self, docker_services, valid_deliverable_types, valid_validation_request):
        """Test valid validation request returns proper response"""
        deliverable_type = "service"
        response = requests.post(
            f"http://localhost:8080/governance/validation-protocol/{deliverable_type}",
            json=valid_validation_request,
            timeout=60
        )

        # Should return 200 OK for successful validation or 422 for failed validation
        assert response.status_code in [200, 422]

        data = response.json()

        # Required fields per ValidationResult schema
        required_fields = {
            "validation_id", "overall_status", "validation_steps",
            "green_light_status", "timestamp"
        }
        assert set(data.keys()) >= required_fields

        # Validate field types and values
        assert isinstance(data["validation_id"], str)
        assert data["overall_status"] in ["pass", "fail", "partial"]
        assert isinstance(data["validation_steps"], list)
        assert isinstance(data["green_light_status"], bool)

        # Validate timestamp is ISO datetime
        datetime.fromisoformat(data["timestamp"].replace('Z', '+00:00'))

        # Validate validation_steps structure
        for step in data["validation_steps"]:
            step_required_fields = {"step_name", "status", "details", "execution_time"}
            assert set(step.keys()) >= step_required_fields
            assert step["status"] in ["pass", "fail", "skip"]
            assert isinstance(step["execution_time"], (int, float))

    def test_governance_validation_protocol_all_valid_types(self, docker_services, valid_deliverable_types, minimal_validation_request):
        """Test all valid deliverable types work"""
        for deliverable_type in valid_deliverable_types:
            response = requests.post(
                f"http://localhost:8080/governance/validation-protocol/{deliverable_type}",
                json=minimal_validation_request,
                timeout=30
            )

            assert response.status_code in [200, 422]

            data = response.json()
            assert "validation_id" in data
            assert "overall_status" in data

    def test_governance_validation_protocol_invalid_deliverable_type(self, docker_services, minimal_validation_request):
        """Test handling of invalid deliverable types"""
        invalid_types = [
            "invalid-type",
            "application",  # Similar but not exact
            "microservice",  # Close but wrong
            "component"
        ]

        for invalid_type in invalid_types:
            response = requests.post(
                f"http://localhost:8080/governance/validation-protocol/{invalid_type}",
                json=minimal_validation_request,
                timeout=10
            )

            # Should return 400 for invalid deliverable types
            assert response.status_code == 400

    def test_governance_validation_protocol_missing_required_fields(self, docker_services, valid_deliverable_types):
        """Test validation of required fields"""
        deliverable_type = valid_deliverable_types[0]

        # Missing component_id field
        payload = {"validation_context": {"environment": "test"}}
        response = requests.post(
            f"http://localhost:8080/governance/validation-protocol/{deliverable_type}",
            json=payload,
            timeout=10
        )
        assert response.status_code == 400

        # Missing validation_context field
        payload = {"component_id": "test-component"}
        response = requests.post(
            f"http://localhost:8080/governance/validation-protocol/{deliverable_type}",
            json=payload,
            timeout=10
        )
        assert response.status_code == 400

        # Empty required fields
        payload = {"component_id": "", "validation_context": {}}
        response = requests.post(
            f"http://localhost:8080/governance/validation-protocol/{deliverable_type}",
            json=payload,
            timeout=10
        )
        assert response.status_code == 400

    def test_governance_validation_protocol_validation_context_validation(self, docker_services, valid_deliverable_types):
        """Test validation of validation_context object"""
        deliverable_type = "container"

        # Invalid validation_context (not an object)
        payload = {
            "component_id": "test-component",
            "validation_context": "not_an_object"
        }
        response = requests.post(
            f"http://localhost:8080/governance/validation-protocol/{deliverable_type}",
            json=payload,
            timeout=10
        )
        assert response.status_code == 400

        # Valid minimal validation_context
        payload = {
            "component_id": "test-component",
            "validation_context": {"environment": "test"}
        }
        response = requests.post(
            f"http://localhost:8080/governance/validation-protocol/{deliverable_type}",
            json=payload,
            timeout=20
        )
        assert response.status_code in [200, 422]

    def test_governance_validation_protocol_custom_validation_steps(self, docker_services, valid_deliverable_types):
        """Test handling of custom validation steps"""
        deliverable_type = "integration"

        # Invalid custom_validation_steps (not an array)
        payload = {
            "component_id": "test-component",
            "validation_context": {"environment": "test"},
            "custom_validation_steps": "not_an_array"
        }
        response = requests.post(
            f"http://localhost:8080/governance/validation-protocol/{deliverable_type}",
            json=payload,
            timeout=10
        )
        assert response.status_code == 400

        # Valid custom validation steps
        payload = {
            "component_id": "test-component",
            "validation_context": {"environment": "test"},
            "custom_validation_steps": ["step1", "step2", "step3"]
        }
        response = requests.post(
            f"http://localhost:8080/governance/validation-protocol/{deliverable_type}",
            json=payload,
            timeout=25
        )
        assert response.status_code in [200, 422]

        # Empty array should be valid
        payload = {
            "component_id": "test-component",
            "validation_context": {"environment": "test"},
            "custom_validation_steps": []
        }
        response = requests.post(
            f"http://localhost:8080/governance/validation-protocol/{deliverable_type}",
            json=payload,
            timeout=20
        )
        assert response.status_code in [200, 422]

    def test_governance_validation_protocol_validation_steps_execution(self, docker_services, valid_deliverable_types, valid_validation_request):
        """Test that validation steps are properly executed and reported"""
        deliverable_type = "service"
        response = requests.post(
            f"http://localhost:8080/governance/validation-protocol/{deliverable_type}",
            json=valid_validation_request,
            timeout=60
        )

        assert response.status_code in [200, 422]
        data = response.json()

        validation_steps = data["validation_steps"]

        # Should have executed some validation steps
        assert len(validation_steps) > 0

        # Each step should have proper structure and execution info
        for step in validation_steps:
            assert isinstance(step["step_name"], str)
            assert len(step["step_name"].strip()) > 0
            assert step["status"] in ["pass", "fail", "skip"]
            assert isinstance(step["details"], str)
            assert isinstance(step["execution_time"], (int, float))
            assert step["execution_time"] >= 0

    def test_governance_validation_protocol_health_check_results(self, docker_services, valid_deliverable_types, minimal_validation_request):
        """Test that health check results are included when available"""
        deliverable_type = "service"
        response = requests.post(
            f"http://localhost:8080/governance/validation-protocol/{deliverable_type}",
            json=minimal_validation_request,
            timeout=30
        )

        assert response.status_code in [200, 422]
        data = response.json()

        # Health check result is optional but should be object if present
        if "health_check_result" in data:
            assert isinstance(data["health_check_result"], dict)

    def test_governance_validation_protocol_connectivity_test_results(self, docker_services, valid_deliverable_types, minimal_validation_request):
        """Test that connectivity test results are included when available"""
        deliverable_type = "integration"
        response = requests.post(
            f"http://localhost:8080/governance/validation-protocol/{deliverable_type}",
            json=minimal_validation_request,
            timeout=30
        )

        assert response.status_code in [200, 422]
        data = response.json()

        # Connectivity test result is optional but should be object if present
        if "connectivity_test_result" in data:
            assert isinstance(data["connectivity_test_result"], dict)

    def test_governance_validation_protocol_green_light_logic(self, docker_services, valid_deliverable_types, minimal_validation_request):
        """Test green light status logic"""
        deliverable_type = "workflow"
        response = requests.post(
            f"http://localhost:8080/governance/validation-protocol/{deliverable_type}",
            json=minimal_validation_request,
            timeout=30
        )

        assert response.status_code in [200, 422]
        data = response.json()

        overall_status = data["overall_status"]
        green_light_status = data["green_light_status"]

        # Green light should correlate with overall status
        if overall_status == "pass":
            assert green_light_status is True
        elif overall_status == "fail":
            assert green_light_status is False
        # "partial" status could go either way depending on business logic

    def test_governance_validation_protocol_content_type_validation(self, docker_services, valid_deliverable_types):
        """Test that endpoint requires JSON content type"""
        deliverable_type = valid_deliverable_types[0]
        payload = "component_id=test&validation_context=test"
        response = requests.post(
            f"http://localhost:8080/governance/validation-protocol/{deliverable_type}",
            data=payload,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            timeout=10
        )
        # Should reject non-JSON content
        assert response.status_code == 400

    def test_governance_validation_protocol_malformed_json(self, docker_services, valid_deliverable_types):
        """Test handling of malformed JSON requests"""
        deliverable_type = valid_deliverable_types[0]
        malformed_json = '{"component_id": "test", "validation_context": {"env": "test"}'  # Missing closing brace
        response = requests.post(
            f"http://localhost:8080/governance/validation-protocol/{deliverable_type}",
            data=malformed_json,
            headers={"Content-Type": "application/json"},
            timeout=10
        )
        assert response.status_code == 400

    def test_governance_validation_protocol_response_timing(self, docker_services, valid_deliverable_types, minimal_validation_request):
        """Test validation protocol response timing requirements"""
        deliverable_type = "container"

        start_time = time.time()
        response = requests.post(
            f"http://localhost:8080/governance/validation-protocol/{deliverable_type}",
            json=minimal_validation_request,
            timeout=120
        )
        response_time = time.time() - start_time

        # Validation may take time but should be reasonable
        assert response_time < 120.0
        assert response.status_code in [200, 422]

    def test_governance_validation_protocol_method_restrictions(self, docker_services, valid_deliverable_types):
        """Test that only POST method is allowed"""
        deliverable_type = valid_deliverable_types[0]
        endpoint = f"http://localhost:8080/governance/validation-protocol/{deliverable_type}"

        # GET should not be allowed
        response = requests.get(endpoint, timeout=10)
        assert response.status_code == 405

        # PUT should not be allowed
        response = requests.put(endpoint, timeout=10)
        assert response.status_code == 405

    def test_governance_validation_protocol_validation_id_uniqueness(self, docker_services, valid_deliverable_types, minimal_validation_request):
        """Test that each validation generates unique validation IDs"""
        deliverable_type = "system"
        validation_ids = set()

        for i in range(3):
            request_data = minimal_validation_request.copy()
            request_data["component_id"] = f"test-component-{i}"

            response = requests.post(
                f"http://localhost:8080/governance/validation-protocol/{deliverable_type}",
                json=request_data,
                timeout=30
            )

            assert response.status_code in [200, 422]
            data = response.json()
            validation_id = data["validation_id"]

            # Should not have seen this validation ID before
            assert validation_id not in validation_ids
            validation_ids.add(validation_id)

    def test_governance_validation_protocol_different_components(self, docker_services, valid_deliverable_types):
        """Test validation of different component types"""
        component_scenarios = [
            {
                "component_id": "discord-bot-v1",
                "validation_context": {"environment": "production", "type": "discord_bot"}
            },
            {
                "component_id": "redis-cache-cluster",
                "validation_context": {"environment": "staging", "type": "cache_service"}
            },
            {
                "component_id": "postgres-database",
                "validation_context": {"environment": "production", "type": "database"}
            }
        ]

        for scenario in component_scenarios:
            for deliverable_type in valid_deliverable_types[:2]:  # Test first 2 types
                response = requests.post(
                    f"http://localhost:8080/governance/validation-protocol/{deliverable_type}",
                    json=scenario,
                    timeout=35
                )

                assert response.status_code in [200, 422]
                data = response.json()
                assert "validation_id" in data

    def test_governance_validation_protocol_unicode_handling(self, docker_services, valid_deliverable_types):
        """Test handling of unicode characters in validation requests"""
        deliverable_type = "service"
        payload = {
            "component_id": "unicode-test-服务",
            "validation_context": {
                "environment": "test",
                "description": "Testing unicode: 北京, Москва, São Paulo"
            }
        }

        response = requests.post(
            f"http://localhost:8080/governance/validation-protocol/{deliverable_type}",
            json=payload,
            timeout=25
        )

        # Should handle unicode gracefully
        assert response.status_code in [200, 422]

    def test_governance_validation_protocol_concurrent_requests(self, docker_services, valid_deliverable_types, minimal_validation_request):
        """Test handling of concurrent validation requests"""
        import concurrent.futures

        def run_validation(suffix):
            request_data = minimal_validation_request.copy()
            request_data["component_id"] = f"concurrent-test-{suffix}"
            return requests.post(
                f"http://localhost:8080/governance/validation-protocol/service",
                json=request_data,
                timeout=40
            )

        # Submit multiple concurrent requests
        with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
            futures = [executor.submit(run_validation, i) for i in range(5)]
            responses = [future.result() for future in futures]

        # All requests should be handled successfully
        for response in responses:
            assert response.status_code in [200, 422]
            data = response.json()
            assert "validation_id" in data

    def test_governance_validation_protocol_execution_time_tracking(self, docker_services, valid_deliverable_types, valid_validation_request):
        """Test that execution times are properly tracked"""
        deliverable_type = "integration"
        response = requests.post(
            f"http://localhost:8080/governance/validation-protocol/{deliverable_type}",
            json=valid_validation_request,
            timeout=60
        )

        assert response.status_code in [200, 422]
        data = response.json()

        validation_steps = data["validation_steps"]

        # Each step should have reasonable execution time
        for step in validation_steps:
            execution_time = step["execution_time"]
            assert execution_time >= 0
            assert execution_time < 300  # No single step should take more than 5 minutes

        # Total execution time should be sum of individual steps (approximately)
        total_step_time = sum(step["execution_time"] for step in validation_steps)
        assert total_step_time > 0