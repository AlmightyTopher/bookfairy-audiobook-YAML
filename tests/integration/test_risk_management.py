"""
Integration test for risk management and severity evaluation
Based on quickstart.md Scenario 7
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


class TestRiskManagement:
    """Test risk assessment system using Severity/Ease rubric"""

    def test_severity_ease_rubric_application(self, bookfairy_stack):
        """Test severity and ease classifications are applied consistently"""
        governance_url = "http://localhost:8080"

        # Test different types of risks and issues
        test_cases = [
            {
                "type": "redis_connection_failure",
                "description": "Redis service becomes unavailable",
                "scope": "affects_caching_and_recommendations",
                "expected_severity": "High"  # Affects critical functionality
            },
            {
                "type": "missing_error_logging",
                "description": "Error messages not being logged",
                "scope": "debugging_and_monitoring",
                "expected_severity": "Medium"  # Diagnostic but not critical
            },
            {
                "type": "slow_response_times",
                "description": "API responses taking >10 seconds",
                "scope": "user_experience",
                "expected_severity": "Medium"  # Degrades but remains functional
            },
            {
                "type": "documentation_update",
                "description": "API documentation not updated",
                "scope": "developer_experience",
                "expected_severity": "Low"  # Future/polish issue
            }
        ]

        for test_case in test_cases:
            risk_request = {
                "risk_identifier": test_case["type"],
                "description": test_case["description"],
                "scope": test_case["scope"],
                "potential_impact": f"Impact on {test_case['scope'].replace('_', ' ')}"
            }

            response = requests.post(
                f"{governance_url}/governance/risk-assessment/severe",
                json=risk_request,
                timeout=15
            )

            # Expected to fail until severity rubric is implemented
            assert response.status_code == 200
            assessment = response.json()

            assert "severity" in assessment
            assert "ease" in assessment
            assert "justification" in assessment

            # Verify severity classifications meet expectations
            assessed_severity = assessment["severity"]
            assert assessed_severity in ["Blocker", "High", "Medium", "Low"]

            # Critical test: if we expect High severity, it should be classified as High
            if test_case["expected_severity"] == "High":
                assert assessed_severity == "High" or assessed_severity == "Blocker"

    def test_ease_classification_accuracy(self, bookfairy_stack):
        """Test ease classification for various types of work"""
        governance_url = "http://localhost:8080"

        # Test cases with clear ease expectations
        ease_test_cases = [
            {
                "task": "update_dependency_version",
                "description": "Update Python package version in requirements.txt",
                "complexity_factors": ["single_file_change", "no_logic_changes"],
                "expected_ease": "Easy"  # <30 minutes, straightforward
            },
            {
                "task": "add_circuit_breaker",
                "description": "Implement circuit breaker pattern across multiple services",
                "complexity_factors": [
                    "distributed_implementation",
                    "state_management",
                    "error_handling",
                    "configuration",
                    "testing"
                ],
                "expected_ease": "Hard"  # days+, external dependencies
            },
            {
                "task": "add_health_checks",
                "description": "Add health check endpoints to individual services",
                "complexity_factors": [
                    "multiple_services",
                    "consistent_interface",
                    "error_conditions",
                    "testing"
                ],
                "expected_ease": "Moderate"  # hours, moderate complexity
            },
            {
                "task": "config_logging_format",
                "description": "Standardize logging format across all services",
                "complexity_factors": [
                    "configuration_changes",
                    "multiple_services",
                    "consistent_format"
                ],
                "expected_ease": "Moderate"  # hours, moderate complexity
            }
        ]

        for test_case in ease_test_cases:
            ease_request = {
                "task_identifier": test_case["task"],
                "description": test_case["description"],
                "complexity_factors": test_case["complexity_factors"],
                "estimated_effort": f"Expected {test_case['expected_ease']}"
            }

            response = requests.post(
                f"{governance_url}/governance/risk-assessment/ease",
                json=ease_request,
                timeout=15
            )

            # Expected to fail until ease rubric is implemented
            assert response.status_code == 200
            assessment = response.json()

            assert "ease" in assessment
            assert "justification" in assessment
            assert "estimated_hours" in assessment

            assessed_ease = assessment["ease"]
            assert assessed_ease in ["Easy", "Moderate", "Hard"]

            # Critical test: if we expect a specific ease, it should be close
            # (allowing some flexibility in classification)
            if test_case["expected_ease"] == "Easy":
                assert assessed_ease == "Easy"
            elif test_case["expected_ease"] == "Hard":
                assert assessed_ease == "Hard"

    def test_blocker_detection_and_prevention(self, bookfairy_stack):
        """Test Blocker severity issues are detected and prevent progression"""
        governance_url = "http://localhost:8080"
        discord_bot_url = "http://localhost:8080"

        # Test case 1: Security vulnerability
        blocker_issue_1 = {
            "issue_type": "security_vulnerability",
            "details": {
                "vulnerability": "hardcoded_api_keys",
                "scope": "discord_bot_service",
                "impact": "complete_system_compromise_possible",
                "fix_required": "immediate_deployment_block"
            }
        }

        response1 = requests.post(
            f"{governance_url}/governance/risk-assessment/blocker-check",
            json=blocker_issue_1,
            timeout=15
        )

        assert response1.status_code == 200
        blocker_check_1 = response1.json()

        assert blocker_check_1["is_blocker"] == True
        assert "blocker_reason" in blocker_check_1
        assert "must_fix_before_proceeding" in blocker_check_1
        assert blocker_check_1["must_fix_before_proceeding"] == True

        # Test case 2: Non-blocker issue
        non_blocker_issue = {
            "issue_type": "documentation_missing",
            "details": {
                "documentation_type": "api_endpoint_docs",
                "scope": "single_endpoint",
                "impact": "developer_experience",
                "fix_required": "not_urgent"
            }
        }

        response2 = requests.post(
            f"{governance_url}/governance/risk-assessment/blocker-check",
            json=non_blocker_issue,
            timeout=15
        )

        assert response2.status_code == 200
        non_blocker_check = response2.json()

        assert non_blocker_check["is_blocker"] == False
        assert "can_proceed_with_fix_later" in non_blocker_check

    def test_risk_register_and_tracking(self, bookfairy_stack):
        """Test risks are registered and tracked with proper prioritization"""
        governance_url = "http://localhost:8080"

        # Create a set of risks to track
        risks_to_register = [
            {
                "id": "RISK-001",
                "title": "Redis Dependency Risk",
                "severity": "High",
                "ease": "Moderate",
                "description": "System heavily depends on Redis for recommendations and caching"
            },
            {
                "id": "RISK-002",
                "title": "Private Key Storage",
                "severity": "Blocker",
                "ease": "Easy",
                "description": "Discord bot token stored in environment but not properly secured"
            },
            {
                "id": "RISK-003",
                "title": "Documentation Gaps",
                "severity": "Low",
                "ease": "Easy",
                "description": "API documentation incomplete for new endpoints"
            }
        ]

        # Register risks
        response = requests.post(
            f"{governance_url}/governance/risk-register/add-multiple",
            json={"risks": risks_to_register},
            timeout=20
        )

        # Expected to fail until risk register is implemented
        assert response.status_code == 201
        register_result = response.json()

        assert "registered_risks" in register_result
        assert len(register_result["registered_risks"]) == 3

        # Query risk register
        query_response = requests.get(f"{governance_url}/governance/risk-register")
        assert query_response.status_code == 200

        risk_register = query_response.json()
        assert "risks" in risk_register
        assert len(risk_register["risks"]) >= 3

        # Find registered risks
        registered_risks = {risk["id"]: risk for risk in risk_register["risks"]}

        for original_risk in risks_to_register:
            risk_id = original_risk["id"]
            assert risk_id in registered_risks
            registered = registered_risks[risk_id]

            assert registered["severity"] == original_risk["severity"]
            assert registered["ease"] == original_risk["ease"]
            assert "registered_date" in registered
            assert "priority_score" in registered  # Computed prioritization

    def test_prioritization_matrix_application(self, bookfairy_stack):
        """Test Severity x Ease prioritization matrix works correctly"""
        governance_url = "http://localhost:8080"

        # Test various combinations of severity and ease
        prioritization_tests = [
            {
                "title": "Blocker-Easy",
                "severity": "Blocker",
                "ease": "Easy",
                "expected_priority": "CRITICAL_FIX_NOW"
            },
            {
                "title": "Blocker-Hard",
                "severity": "Blocker",
                "ease": "Hard",
                "expected_priority": "PLAN_DEDICATED_EFFORT"
            },
            {
                "title": "High-Easy",
                "severity": "High",
                "ease": "Easy",
                "expected_priority": "HIGH_PRIORITY_BACKLOG"
            },
            {
                "title": "Low-Hard",
                "severity": "Low",
                "ease": "Hard",
                "expected_priority": "CONSIDERATION_IN_ROADMAP"
            }
        ]

        for test_case in prioritization_tests:
            priority_request = {
                "title": test_case["title"],
                "severity": test_case["severity"],
                "ease": test_case["ease"],
                "test_prioritization": True
            }

            response = requests.post(
                f"{governance_url}/governance/prioritization-matrix/evaluate",
                json=priority_request,
                timeout=15
            )

            # Expected to fail until prioritization matrix is implemented
            assert response.status_code == 200
            priority_result = response.json()

            assert "calculated_priority" in priority_result
            assert "recommendation" in priority_result
            assert "rationale" in priority_result
            assert "action_plan" in priority_result

            # Test for specific expected priority (flexible matching)
            expected = test_case["expected_priority"]
            if expected == "CRITICAL_FIX_NOW":
                assert "IMMEDIATE" in priority_result["recommendation"].upper() or \
                       "CRITICAL" in priority_result["recommendation"].upper()
            elif expected == "PLAN_DEDICATED_EFFORT":
                assert "DEDICATED" in priority_result["recommendation"].upper()
            elif expected == "HIGH_PRIORITY_BACKLOG":
                assert "HIGH" in priority_result["recommendation"].upper()

    def test_termination_criteria_enforcement(self, bookfairy_stack):
        """Test that project termination criteria work correctly"""
        governance_url = "http://localhost:8080"

        # Create scenarios with different risk profiles
        scenarios = [
            {
                "name": "no_blockers_low_meds",
                "blocker_count": 0,
                "high_count": 0,
                "medium_count": 2,
                "expected_termination_allowed": True
            },
            {
                "name": "has_blocker",
                "blocker_count": 1,
                "high_count": 0,
                "medium_count": 0,
                "expected_termination_allowed": False
            },
            {
                "name": "has_high_no_mitigation",
                "blocker_count": 0,
                "high_count": 1,
                "medium_count": 0,
                "expected_termination_allowed": False
            },
            {
                "name": "mediums_with_mitigation",
                "blocker_count": 0,
                "high_count": 0,
                "medium_count": 3,
                "with_mitigations": True,
                "expected_termination_allowed": True
            }
        ]

        for scenario in scenarios:
            termination_request = {
                "project_phase": "implementation",
                "assessment_date": "2025-09-18",
                "blocker_count": scenario["blocker_count"],
                "high_count": scenario["high_count"],
                "medium_count": scenario["medium_count"],
                "with_mitigations": scenario.get("with_mitigations", False),
                "unresolved_critical_issues": [
                    "Fake critical issue" for _ in range(scenario["blocker_count"] + scenario["high_count"])
                ]
            }

            response = requests.post(
                f"{governance_url}/governance/termination-check",
                json=termination_request,
                timeout=20
            )

            # Expected to fail until termination criteria are implemented
            assert response.status_code == 200
            termination_result = response.json()

            assert "termination_allowed" in termination_result
            assert "justification" in termination_result
            assert "blocking_issues" in termination_result

            actual_allowed = termination_result["termination_allowed"]
            expected_allowed = scenario["expected_termination_allowed"]

            assert actual_allowed == expected_allowed, \
                f"Scenario {scenario['name']}: expected termination_allowed={expected_allowed}, got {actual_allowed}"

    def test_risk_assessment_workflow_integration(self, bookfairy_stack):
        """Test complete risk assessment workflow from discovery to mitigation"""
        governance_url = "http://localhost:8080"
        discord_bot_url = "http://localhost:8080"

        # Discover risk through system analysis
        discovery_request = {
            "analysis_type": "code_review",
            "component": "discord_bot",
            "scan_scope": "error_handling_patterns"
        }

        discovery_response = requests.post(
            f"{governance_url}/governance/risk-discovery/scan",
            json=discovery_request,
            timeout=25
        )

        # Expected to fail until full workflow is implemented
        assert discovery_response.status_code == 200
        discovered_risks = discovery_response.json()

        assert "discovered_risks" in discovered_risks
        assert len(discovered_risks["discovered_risks"]) > 0

        # Process discovered risk through assessment workflow
        for risk in discovered_risks["discovered_risks"][:1]:  # Process first risk
            assessment_workflow = {
                "risk_id": risk["id"],
                "workflow_steps": [
                    "severity_assessment",
                    "ease_assessment",
                    "prioritization_matrix",
                    "mitigation_planning"
                ]
            }

            workflow_response = requests.post(
                f"{governance_url}/governance/risk-workflow/process",
                json=assessment_workflow,
                timeout=30
            )

            assert workflow_response.status_code == 200
            workflow_result = workflow_response.json()

            assert "workflow_completed" in workflow_result
            assert "final_risk_status" in workflow_result
            assert "recommended_actions" in workflow_result

            # Should have gone through all workflow steps
            for step in assessment_workflow["workflow_steps"]:
                assert step in workflow_result
                step_result = workflow_result[step]
                assert "completed" in step_result
                assert step_result["completed"] == True


if __name__ == "__main__":
    pytest.main([__file__])
