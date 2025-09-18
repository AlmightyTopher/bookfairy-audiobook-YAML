"""
Integration test for validation protocol enforcement
Based on quickstart.md Scenario 8
These tests MUST FAIL before implementation - TDD requirement
"""
import pytest
import requests
import time
import json
from testcontainers.compose import DockerCompose


@pytest.fixture(scope="session")
def bookfairy_stack():
    """Fixture that starts the full BookFairy Docker Compose stack"""
    compose = DockerCompose("bookfairy/docker-compose.yml")
    compose.start()
    time.sleep(30)  # Wait for all services to be ready
    yield compose
    compose.stop()


class TestValidationProtocol:
    """Test validation protocol enforcement throughout the system"""

    def test_validation_protocol_structure(self, bookfairy_stack):
        """Test validation protocol has required components"""
        governance_url = "http://localhost:8080"

        # Request validation protocol definition
        response = requests.get(f"{governance_url}/governance/validation-protocol")
        assert response.status_code == 200

        validation_protocol = response.json()

        # Check protocol structure
        assert "health_check_method" in validation_protocol
        assert "connectivity_test" in validation_protocol
        assert "green_light_confirmation" in validation_protocol
        assert "required_steps" in validation_protocol

        # Verify all three steps are defined
        steps = validation_protocol["required_steps"]
        step_names = [step["name"] for step in steps]

        assert "health_check" in step_names
        assert "connectivity_test" in step_names
        assert "green_light_confirmation" in step_names

        # Each step should have success criteria
        for step in steps:
            assert "success_criteria" in step
            assert "timeout_seconds" in step
            assert "retry_logic" in step

    def test_health_check_validation_step(self, bookfairy_stack):
        """Test health check validation step implementation"""
        governance_url = "http://localhost:8080"

        # Test health check against individual services
        services_to_test = [
            {"name": "discord-bot", "port": 8080, "endpoint": "/health"},
            {"name": "redis", "port": 6379, "endpoint": "/health"},
            {"name": "audiobookshelf", "port": 13378, "endpoint": "/health"}
        ]

        for service in services_to_test:
            health_validation = {
                "service_name": service["name"],
                "health_endpoint": service["endpoint"],
                "expected_status_code": 200,
                "timeout_seconds": 10
            }

            response = requests.post(
                f"{governance_url}/governance/validation-protocol/health-check",
                json=health_validation,
                timeout=15
            )

            # Should return validation result
            validation_result = response.json()
            assert "validation_result" in validation_result
            assert "service_name" in validation_result
            assert "passed" in validation_result

    def test_connectivity_test_validation_step(self, bookfairy_stack):
        """Test connectivity validation between services"""
        governance_url = "http://localhost:8080"

        # Test connectivity patterns from the BookFairy system
        connectivity_tests = [
            {
                "source": "discord-bot",
                "target": "redis",
                "connection_type": "caching",
                "test_method": "ping_set_get"
            },
            {
                "source": "discord-bot",
                "target": "lm-studio",
                "connection_type": "ai_service",
                "test_method": "model_query"
            },
            {
                "source": "lazylibrarian",
                "target": "prowlarr",
                "connection_type": "indexer_integration",
                "test_method": "indexer_sync"
            }
        ]

        for test_config in connectivity_tests:
            connectivity_request = {
                "source_service": test_config["source"],
                "target_service": test_config["target"],
                "connection_type": test_config["connection_type"],
                "test_method": test_config["test_method"],
                "timeout_seconds": 20
            }

            response = requests.post(
                f"{governance_url}/governance/validation-protocol/connectivity-test",
                json=connectivity_request,
                timeout=25
            )

            # Expected to fail until connectivity tests are implemented
            assert response.status_code == 200
            connectivity_result = response.json()

            assert "connectivity_test_result" in connectivity_result
            assert "source_service" in connectivity_result
            assert "target_service" in connectivity_result
            assert "connection_status" in connectivity_result
            assert "latency_ms" in connectivity_result or "error_message" in connectivity_result

            # Connection should be successful or explain failure
            connection_status = connectivity_result["connection_status"]
            assert connection_status in ["successful", "failed", "degraded", "timeout"]

    def test_green_light_confirmation_step(self, bookfairy_stack):
        """Test final green light confirmation for deliverables"""
        governance_url = "http://localhost:8080"

        # Test green light for various deliverables
        deliverables = [
            {
                "deliverable_name": "container_startup",
                "requirements": ["all_containers_running", "no_critical_errors_in_logs"],
                "stakeholders": ["infrastructure_team", "developers"]
            },
            {
                "deliverable_name": "service_integration",
                "requirements": ["all_service_connections_working", "basic_workflow_test_passed"],
                "stakeholders": ["developers", "qa_team"]
            },
            {
                "deliverable_name": "production_readiness",
                "requirements": ["performance_baseline_met", "security_scan_passed", "documentation_complete"],
                "stakeholders": ["product_manager", "security_team", "devops"]
            }
        ]

        for deliverable in deliverables:
            green_light_request = {
                "deliverable_name": deliverable["deliverable_name"],
                "validation_criteria": deliverable["requirements"],
                "stakeholders": deliverable["stakeholders"],
                "require_all_approvals": True
            }

            response = requests.post(
                f"{governance_url}/governance/validation-protocol/green-light",
                json=green_light_request,
                timeout=30
            )

            # Expected to fail until green light confirmation is implemented
            assert response.status_code == 200
            green_light_result = response.json()

            assert "green_light_result" in green_light_result
            assert "deliverable_name" in green_light_result
            assert "approval_status" in green_light_result
            assert "validated_requirements" in green_light_result
            assert "stakeholder_approvals" in green_light_result

            # Green light result should be definitive
            approval_status = green_light_result["approval_status"]
            assert approval_status in ["approved", "blocked", "pending", "conditional_approval"]

            if approval_status == "approved":
                assert "approved_timestamp" in green_light_result
            elif approval_status == "blocked":
                assert "blocking_reasons" in green_light_result

    def test_validation_protocol_enforcement(self, bookfairy_stack):
        """Test that validation protocol is enforced before progression"""
        governance_url = "http://localhost:8080"
        discord_bot_url = "http://localhost:8080"

        # Simulate a feature delivery attempt without full validation
        delivery_request = {
            "feature_name": "ai_recommendations",
            "deliverables": ["code_implementation", "unit_tests", "integration_tests"],
            "validation_attempted": {
                "health_check": True,
                "connectivity_test": False,  # Intentionally skipped
                "green_light_confirmation": False  # Intentionally skipped
            }
        }

        response = requests.post(
            f"{governance_url}/governance/validation-protocol/deliver",
            json=delivery_request,
            timeout=20
        )

        # Should block delivery due to incomplete validation
        delivery_result = response.json()
        assert "delivery_blocked" in delivery_result
        assert delivery_result["delivery_blocked"] == True
        assert "missing_validation_steps" in delivery_result

        missing_steps = delivery_result["missing_validation_steps"]
        assert "connectivity_test" in missing_steps
        assert "green_light_confirmation" in missing_steps

    def test_validation_retry_logic(self, bookfairy_stack):
        """Test retry logic for validation failures"""
        governance_url = "http://localhost:8080"

        # Configure a flaky service for testing retries
        test_service = {
            "service_name": "flaky_service",
            "endpoint": "/health",
            "expected_failure_rate": 0.3,  # 30% of requests fail
            "max_retries": 3,
            "retry_delay_seconds": 2
        }

        response = requests.post(
            f"{governance_url}/governance/validation-protocol/retry-test",
            json=test_service,
            timeout=60  # Allow time for retries
        )

        # Expected to fail until retry logic is implemented
        assert response.status_code == 200
        retry_result = response.json()

        assert "retry_attempts_made" in retry_result
        assert "final_result" in retry_result
        assert "retry_history" in retry_result

        retry_history = retry_result["retry_history"]
        assert len(retry_history) <= test_service["max_retries"] + 1  # Initial + retries

        # Should eventually succeed or provide detailed failure analysis
        assert retry_result["final_result"] in ["success", "persistent_failure"]

    def test_validation_timeout_handling(self, bookfairy_stack):
        """Test timeout handling in validation protocol"""
        governance_url = "http://localhost:8080"

        # Test with very short timeout
        slow_validation = {
            "service_name": "slow_service",
            "endpoint": "/health",
            "timeout_seconds": 1,  # Very short timeout
            "simulated_delay": 5   # Service that takes 5 seconds
        }

        start_time = time.time()
        response = requests.post(
            f"{governance_url}/governance/validation-protocol/timeout-test",
            json=slow_validation,
            timeout=10
        )
        end_time = time.time()

        validation_result = response.json()
        assert "validation_result" in validation_result
        assert "timeout_handling" in validation_result

        timeout_handling = validation_result["timeout_handling"]
        assert "timed_out" in timeout_handling
        assert "timeout_duration_seconds" in timeout_handling
        assert "graceful_degradation" in timeout_handling

        # Timeout should be detected
        assert timeout_handling["timed_out"] == True
        assert timeout_handling["timeout_duration_seconds"] <= slow_validation["timeout_seconds"] + 1

    def test_validation_reporting_and_audit_trail(self, bookfairy_stack):
        """Test comprehensive validation reporting and audit trail"""
        governance_url = "http://localhost:8080"

        # Request validation audit trail
        response = requests.get(f"{governance_url}/governance/validation-protocol/audit-trail")
        assert response.status_code == 200

        audit_trail = response.json()

        assert "validation_events" in audit_trail
        assert "latest_validation_status" in audit_trail
        assert "audit_trail_metadata" in audit_trail

        # Check audit trail structure
        events = audit_trail["validation_events"]
        if len(events) > 0:
            for event in events:
                assert "timestamp" in event
                assert "validation_type" in event
                assert "status" in event
                assert "details" in event

                validation_type = event["validation_type"]
                assert validation_type in ["health_check", "connectivity_test", "green_light_confirmation"]

    def test_validation_protocol_compliance_check(self, bookfairy_stack):
        """Test automated compliance checking against validation protocol"""
        governance_url = "http://localhost:8080"

        # Check compliance across multiple recent deliverables
        compliance_request = {
            "time_window_days": 7,
            "check_required_validations": True,
            "validate_protocol_enforcement": True
        }

        response = requests.post(
            f"{governance_url}/governance/validation-protocol/compliance-check",
            json=compliance_request,
            timeout=30
        )

        # Expected to fail until compliance checking is implemented
        assert response.status_code == 200
        compliance_result = response.json()

        assert "compliance_status" in compliance_result
        assert "protocol_coverage_percent" in compliance_result
        assert "non_compliant_deliverables" in compliance_result
        assert "validation_gaps" in compliance_result
        assert "recommended_improvements" in compliance_result

        # Compliance status should be definitive
        compliance_status = compliance_result["compliance_status"]
        assert compliance_status in ["compliant", "non_compliant", "partial_compliance", "no_data"]

        if compliance_status == "compliant":
            assert compliance_result["protocol_coverage_percent"] == 100

    def test_end_to_end_validation_workflow(self, bookfairy_stack):
        """Test complete validation workflow for a new service deployment"""
        governance_url = "http://localhost:8080"

        # Initiate full validation workflow for a new service
        workflow_request = {
            "workflow_type": "service_deployment_validation",
            "service_name": "new_audiobook_processor",
            "validation_scope": {
                "health_checks": True,
                "connectivity_tests": True,
                "green_light_confirmation": True,
                "performance_validation": True,
                "security_validation": True
            },
            "stakeholders": ["developers", "qa", "security"],
            "required_approvals": ["qa_signoff", "security_clearance"]
        }

        response = requests.post(
            f"{governance_url}/governance/validation-protocol/workflow/start",
            json=workflow_request,
            timeout=45
        )

        # Expected to fail until full workflow is implemented
        assert response.status_code == 200
        workflow_result = response.json()

        assert "workflow_id" in workflow_result
        assert "workflow_status" in workflow_result
        assert "current_step" in workflow_result
        assert "completed_steps" in workflow_result
        assert "pending_steps" in workflow_result

        workflow_status = workflow_result["workflow_status"]
        assert workflow_status in ["in_progress", "completed", "failed", "blocked"]

        # If in progress, should have current step
        if workflow_status == "in_progress":
            assert "current_step" in workflow_result
            assert workflow_result["current_step"] is not None

        # Track completion status
        completed_steps = workflow_result["completed_steps"]
        pending_steps = workflow_result["pending_steps"]

        expected_steps = ["health_check", "connectivity_test", "green_light_confirmation"]
        all_steps = completed_steps + pending_steps + [workflow_result.get("current_step")]

        for expected_step in expected_steps:
            assert expected_step in all_steps


if __name__ == "__main__":
    pytest.main([__file__])
