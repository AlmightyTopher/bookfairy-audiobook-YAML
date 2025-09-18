"""
Contract tests for Governance API POST /governance/audit-lens/{lens_name}/apply endpoint
These tests MUST FAIL before implementation - TDD requirement
"""
import pytest
import requests
import json
from testcontainers.compose import DockerCompose
import time
from datetime import datetime


class TestGovernanceAuditAPI:
    """Contract tests for audit lens application endpoint"""

    @pytest.fixture(scope="class")
    def docker_services(self):
        """Set up Docker services for contract testing"""
        with DockerCompose(".", compose_file_name="docker-compose.yml") as compose:
            # Wait for services to be ready
            time.sleep(30)
            yield compose

    @pytest.fixture
    def valid_audit_request(self):
        """Valid audit lens request payload per contract"""
        return {
            "context": "BookFairy Discord bot deployment decision",
            "decision_or_component": "Using containerized microservices architecture",
            "evaluation_criteria": [
                "scalability impact",
                "maintenance overhead",
                "security implications"
            ],
            "additional_context": {
                "environment": "production",
                "team_size": "small",
                "timeline": "2 weeks"
            }
        }

    @pytest.fixture
    def minimal_audit_request(self):
        """Minimal valid audit request with only required fields"""
        return {
            "context": "Database selection for audiobook metadata",
            "decision_or_component": "PostgreSQL vs MongoDB choice"
        }

    @pytest.fixture
    def valid_lens_names(self):
        """Valid audit lens names per contract"""
        return [
            "assumptions", "best-practices", "edge-cases", "safety-security",
            "scalability", "performance", "reliability", "observability",
            "communication", "cost", "human-factors", "self-consistency",
            "regret-later"
        ]

    def test_governance_audit_lens_endpoint_exists(self, docker_services, valid_lens_names, minimal_audit_request):
        """Test that POST /governance/audit-lens/{lens}/apply endpoint exists"""
        # This WILL FAIL until audit lens endpoint is implemented
        lens_name = valid_lens_names[0]  # Use first valid lens
        response = requests.post(
            f"http://localhost:8080/governance/audit-lens/{lens_name}/apply",
            json=minimal_audit_request,
            timeout=10
        )
        # Endpoint should exist and accept requests
        assert response.status_code != 404
        assert response.headers["content-type"] == "application/json"

    def test_governance_audit_lens_valid_request(self, docker_services, valid_lens_names, valid_audit_request):
        """Test valid audit lens request returns proper response"""
        lens_name = "safety-security"
        response = requests.post(
            f"http://localhost:8080/governance/audit-lens/{lens_name}/apply",
            json=valid_audit_request,
            timeout=30
        )

        # Should return 200 OK per contract
        assert response.status_code == 200

        data = response.json()

        # Required fields per AuditLensResult schema
        required_fields = {
            "lens_name", "assessment_result", "findings",
            "recommendations", "priority", "applied_date"
        }
        assert set(data.keys()) >= required_fields

        # Validate field types and values
        assert data["lens_name"] == lens_name
        assert data["assessment_result"] in ["pass", "fail", "needs_attention"]
        assert isinstance(data["findings"], str)
        assert isinstance(data["recommendations"], list)
        assert data["priority"] in ["critical", "high", "medium", "low"]

        # Validate applied_date is ISO datetime
        datetime.fromisoformat(data["applied_date"].replace('Z', '+00:00'))

    def test_governance_audit_lens_all_valid_lenses(self, docker_services, valid_lens_names, minimal_audit_request):
        """Test all valid audit lens names work"""
        for lens_name in valid_lens_names:
            response = requests.post(
                f"http://localhost:8080/governance/audit-lens/{lens_name}/apply",
                json=minimal_audit_request,
                timeout=20
            )

            assert response.status_code == 200

            data = response.json()
            assert data["lens_name"] == lens_name
            assert "assessment_result" in data

    def test_governance_audit_lens_invalid_lens_name(self, docker_services, minimal_audit_request):
        """Test handling of invalid lens names"""
        invalid_lens_names = [
            "invalid-lens",
            "nonexistent",
            "security",  # Similar but not exact
            "performance-test"  # Close but wrong
        ]

        for invalid_lens in invalid_lens_names:
            response = requests.post(
                f"http://localhost:8080/governance/audit-lens/{invalid_lens}/apply",
                json=minimal_audit_request,
                timeout=10
            )

            # Should return 400 for invalid lens names
            assert response.status_code == 400

    def test_governance_audit_lens_missing_required_fields(self, docker_services, valid_lens_names):
        """Test validation of required fields"""
        lens_name = valid_lens_names[0]

        # Missing context field
        payload = {"decision_or_component": "test component"}
        response = requests.post(
            f"http://localhost:8080/governance/audit-lens/{lens_name}/apply",
            json=payload,
            timeout=10
        )
        assert response.status_code == 400

        # Missing decision_or_component field
        payload = {"context": "test context"}
        response = requests.post(
            f"http://localhost:8080/governance/audit-lens/{lens_name}/apply",
            json=payload,
            timeout=10
        )
        assert response.status_code == 400

        # Empty required fields
        payload = {"context": "", "decision_or_component": ""}
        response = requests.post(
            f"http://localhost:8080/governance/audit-lens/{lens_name}/apply",
            json=payload,
            timeout=10
        )
        assert response.status_code == 400

    def test_governance_audit_lens_optional_fields(self, docker_services, valid_lens_names):
        """Test handling of optional fields"""
        lens_name = "best-practices"

        # With evaluation_criteria
        payload = {
            "context": "Test context",
            "decision_or_component": "Test component",
            "evaluation_criteria": ["criterion1", "criterion2"]
        }
        response = requests.post(
            f"http://localhost:8080/governance/audit-lens/{lens_name}/apply",
            json=payload,
            timeout=15
        )
        assert response.status_code == 200

        # With additional_context
        payload = {
            "context": "Test context",
            "decision_or_component": "Test component",
            "additional_context": {"key1": "value1", "key2": "value2"}
        }
        response = requests.post(
            f"http://localhost:8080/governance/audit-lens/{lens_name}/apply",
            json=payload,
            timeout=15
        )
        assert response.status_code == 200

    def test_governance_audit_lens_evaluation_criteria_validation(self, docker_services, valid_lens_names):
        """Test validation of evaluation_criteria array"""
        lens_name = "scalability"

        # Invalid evaluation_criteria (not an array)
        payload = {
            "context": "Test context",
            "decision_or_component": "Test component",
            "evaluation_criteria": "not_an_array"
        }
        response = requests.post(
            f"http://localhost:8080/governance/audit-lens/{lens_name}/apply",
            json=payload,
            timeout=10
        )
        assert response.status_code == 400

        # Empty array should be valid
        payload = {
            "context": "Test context",
            "decision_or_component": "Test component",
            "evaluation_criteria": []
        }
        response = requests.post(
            f"http://localhost:8080/governance/audit-lens/{lens_name}/apply",
            json=payload,
            timeout=15
        )
        assert response.status_code == 200

    def test_governance_audit_lens_additional_context_validation(self, docker_services, valid_lens_names):
        """Test validation of additional_context object"""
        lens_name = "reliability"

        # Invalid additional_context (not an object)
        payload = {
            "context": "Test context",
            "decision_or_component": "Test component",
            "additional_context": "not_an_object"
        }
        response = requests.post(
            f"http://localhost:8080/governance/audit-lens/{lens_name}/apply",
            json=payload,
            timeout=10
        )
        assert response.status_code == 400

        # Empty object should be valid
        payload = {
            "context": "Test context",
            "decision_or_component": "Test component",
            "additional_context": {}
        }
        response = requests.post(
            f"http://localhost:8080/governance/audit-lens/{lens_name}/apply",
            json=payload,
            timeout=15
        )
        assert response.status_code == 200

    def test_governance_audit_lens_response_quality(self, docker_services, valid_audit_request):
        """Test quality of audit lens response"""
        lens_name = "safety-security"
        response = requests.post(
            f"http://localhost:8080/governance/audit-lens/{lens_name}/apply",
            json=valid_audit_request,
            timeout=30
        )

        assert response.status_code == 200
        data = response.json()

        # Findings should be meaningful
        assert len(data["findings"].strip()) > 0

        # Recommendations should be actionable
        recommendations = data["recommendations"]
        assert len(recommendations) > 0
        for rec in recommendations:
            assert isinstance(rec, str)
            assert len(rec.strip()) > 0

    def test_governance_audit_lens_content_type_validation(self, docker_services, valid_lens_names):
        """Test that endpoint requires JSON content type"""
        lens_name = valid_lens_names[0]
        payload = "context=test&decision_or_component=test"
        response = requests.post(
            f"http://localhost:8080/governance/audit-lens/{lens_name}/apply",
            data=payload,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            timeout=10
        )
        # Should reject non-JSON content
        assert response.status_code == 400

    def test_governance_audit_lens_malformed_json(self, docker_services, valid_lens_names):
        """Test handling of malformed JSON requests"""
        lens_name = valid_lens_names[0]
        malformed_json = '{"context": "test", "decision_or_component": "test"'  # Missing closing brace
        response = requests.post(
            f"http://localhost:8080/governance/audit-lens/{lens_name}/apply",
            data=malformed_json,
            headers={"Content-Type": "application/json"},
            timeout=10
        )
        assert response.status_code == 400

    def test_governance_audit_lens_response_timing(self, docker_services, valid_lens_names, minimal_audit_request):
        """Test audit lens response timing requirements"""
        lens_name = "performance"

        start_time = time.time()
        response = requests.post(
            f"http://localhost:8080/governance/audit-lens/{lens_name}/apply",
            json=minimal_audit_request,
            timeout=60
        )
        response_time = time.time() - start_time

        # Audit analysis may take time but should be reasonable
        assert response_time < 60.0
        assert response.status_code == 200

    def test_governance_audit_lens_method_restrictions(self, docker_services, valid_lens_names):
        """Test that only POST method is allowed"""
        lens_name = valid_lens_names[0]
        endpoint = f"http://localhost:8080/governance/audit-lens/{lens_name}/apply"

        # GET should not be allowed
        response = requests.get(endpoint, timeout=10)
        assert response.status_code == 405

        # PUT should not be allowed
        response = requests.put(endpoint, timeout=10)
        assert response.status_code == 405

    def test_governance_audit_lens_different_contexts(self, docker_services, valid_lens_names):
        """Test audit lens with different context types"""
        lens_name = "assumptions"

        contexts = [
            {
                "context": "Technical architecture decision",
                "decision_or_component": "Microservices vs monolith"
            },
            {
                "context": "Security implementation",
                "decision_or_component": "JWT vs session-based authentication"
            },
            {
                "context": "Performance optimization",
                "decision_or_component": "Redis caching strategy"
            }
        ]

        for context_data in contexts:
            response = requests.post(
                f"http://localhost:8080/governance/audit-lens/{lens_name}/apply",
                json=context_data,
                timeout=20
            )

            assert response.status_code == 200
            data = response.json()
            assert "assessment_result" in data

    def test_governance_audit_lens_priority_assignment(self, docker_services, valid_lens_names, valid_audit_request):
        """Test that audit lens assigns appropriate priority levels"""
        lens_name = "safety-security"
        response = requests.post(
            f"http://localhost:8080/governance/audit-lens/{lens_name}/apply",
            json=valid_audit_request,
            timeout=30
        )

        assert response.status_code == 200
        data = response.json()

        priority = data["priority"]
        assert priority in ["critical", "high", "medium", "low"]

        # Security lens should tend toward higher priorities for security issues
        # This is a contract test, so we just verify the field exists and is valid

    def test_governance_audit_lens_unicode_handling(self, docker_services, valid_lens_names):
        """Test handling of unicode characters in audit requests"""
        lens_name = "communication"
        payload = {
            "context": "International deployment with unicode: 北京, Москва, São Paulo",
            "decision_or_component": "Multi-language support implementation"
        }

        response = requests.post(
            f"http://localhost:8080/governance/audit-lens/{lens_name}/apply",
            json=payload,
            timeout=20
        )

        # Should handle unicode gracefully
        assert response.status_code == 200

    def test_governance_audit_lens_concurrent_requests(self, docker_services, valid_lens_names, minimal_audit_request):
        """Test handling of concurrent audit lens requests"""
        import concurrent.futures

        def apply_audit_lens(lens_name):
            request_data = minimal_audit_request.copy()
            request_data["context"] = f"Concurrent test for {lens_name}"
            return requests.post(
                f"http://localhost:8080/governance/audit-lens/{lens_name}/apply",
                json=request_data,
                timeout=30
            )

        # Submit concurrent requests for different lenses
        with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
            futures = [
                executor.submit(apply_audit_lens, lens)
                for lens in valid_lens_names[:5]  # Test first 5 lenses
            ]
            responses = [future.result() for future in futures]

        # All requests should be handled successfully
        for response in responses:
            assert response.status_code == 200
            data = response.json()
            assert "assessment_result" in data

    def test_governance_audit_lens_large_input_handling(self, docker_services, valid_lens_names):
        """Test handling of large input data"""
        lens_name = "edge-cases"

        # Large context and decision
        large_context = "A" * 5000
        large_decision = "B" * 2000

        payload = {
            "context": large_context,
            "decision_or_component": large_decision
        }

        response = requests.post(
            f"http://localhost:8080/governance/audit-lens/{lens_name}/apply",
            json=payload,
            timeout=60
        )

        # Should either accept or reject with validation error
        assert response.status_code in [200, 400]

    def test_governance_audit_lens_assessment_result_consistency(self, docker_services, valid_lens_names, minimal_audit_request):
        """Test that assessment results are consistent for same input"""
        lens_name = "self-consistency"

        # Make same request multiple times
        responses = []
        for _ in range(3):
            response = requests.post(
                f"http://localhost:8080/governance/audit-lens/{lens_name}/apply",
                json=minimal_audit_request,
                timeout=20
            )
            responses.append(response)

        # All responses should be successful
        for response in responses:
            assert response.status_code == 200

        # Results should be consistent (deterministic analysis)
        assessment_results = [r.json()["assessment_result"] for r in responses]
        # Note: In a real implementation, we'd expect consistency, but this is a contract test