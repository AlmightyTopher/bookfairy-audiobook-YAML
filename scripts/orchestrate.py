#!/usr/bin/env python3
"""
BookFairy Orchestration Service
Implements service coordination, workflow execution, and inter-service communication
Based on data-model.md specification and integration tests
"""
import asyncio
import json
import time
import uuid
import sys
import os
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Callable
from concurrent.futures import ThreadPoolExecutor

# Add project root to path
sys.path.append(os.path.join(os.path.dirname(__file__), "..", ".."))

from services.shared.models.workflow import (
    WorkflowExecution, WorkflowType, WorkflowStatus, WorkflowRegistry,
    WorkflowExecutionRW, WorkflowRegistryRW
)
from services.shared.models.service_map import ServiceMap, BookFairyService
from services.shared.models.container import DockerContainerRegistry
from services.shared.models.health import HealthMonitorRegistry
from services.shared.models.governance import AuditLensFramework, AuditLens
from services.shared.models.user_request import UserRequest
from services.shared.models.validation import ValidationProtocolRegistry


class ServiceOrchestrator:
    """Core orchestration engine for BookFairy services"""

    def __init__(self):
        self.service_map = ServiceMap()
        self.container_registry = DockerContainerRegistry()
        self.health_registry = HealthMonitorRegistry()
        self.workflow_registry = WorkflowRegistry()
        self.audit_framework = AuditLensFramework()

        # Service call queue
        self.execution_executor = ThreadPoolExecutor(max_workers=10)

        # Active orchestrations tracking
        self.active_orchestrations: Dict[str, asyncio.Task] = {}
        self.orchestration_events: List[Dict[str, Any]] = []

        print("BookFairy Service Orchestrator initialized")

    def initialize_services(self):
        """Initialize all BookFairy services in dependency order"""
        services_config = [
            {
                "name": "redis",
                "type": "redis",
                "api_port": 6379,
                "health_endpoint": "/health",
                "dependencies": []
            },
            {
                "name": "discord-bot",
                "type": "discord-bot",
                "api_port": 8080,
                "health_endpoint": "/health",
                "dependencies": ["redis"]
            },
            {
                "name": "lazylibrarian",
                "type": "lazylibrarian",
                "api_port": 5299,
                "health_endpoint": "/health",
                "dependencies": []
            },
            {
                "name": "prowlarr",
                "type": "prowlarr",
                "api_port": 9696,
                "health_endpoint": "/api/v1/health",
                "dependencies": []
            },
            {
                "name": "qbittorrent",
                "type": "qbittorrent",
                "api_port": 8080,
                "health_endpoint": "/api/v2/app/version",
                "dependencies": []
            },
            {
                "name": "audiobookshelf",
                "type": "audiobookshelf",
                "api_port": 13378,
                "health_endpoint": "/healthcheck",
                "dependencies": ["redis"]
            },
            {
                "name": "lm-studio",
                "type": "lm-studio",
                "api_port": 1234,
                "health_endpoint": "/v1/models",
                "dependencies": []
            }
        ]

        # Initialize service map
        for config in services_config:
            service = BookFairyService(
                service_name=config["name"],
                service_type=config["type"],
                display_name=config["name"].title(),
                description=f"BookFairy {config['type']} service",
                api_port=config["api_port"],
                health_endpoint=config["health_endpoint"]
            )

            self.service_map.add_service(service)
            self.health_registry.register_service(config["name"])
            print(f"Initialized service: {config['name']}")

    async def orchestrate_workflow(self, workflow: WorkflowExecution) -> WorkflowExecution:
        """Main orchestration method for workflow execution"""
        print(f"🪄 Starting orchestration for workflow: {workflow.workflow_id}")

        workflow.start_workflow()
        self.workflow_registry.register_workflow(workflow)

        # Apply governance audit to workflow execution
        self._apply_governance_audit(workflow, "orchestration_start")

        try:
            # Validate workflow dependencies
            dependency_validation = await self._validate_workflow_dependencies(workflow)
            if not dependency_validation["valid"]:
                workflow.fail_workflow(f"Dependency validation failed: {dependency_validation['error']}")
                return workflow

            # Execute workflow steps in dependency order
            await self._execute_workflow_steps(workflow)

        except Exception as e:
            workflow.fail_workflow(f"Orchestration error: {str(e)}")
            print(f"❌ Workflow orchestration failed: {e}")

        finally:
            # Apply final audit
            self._apply_governance_audit(workflow, "orchestration_complete")
            workflow.update_progress()

        return workflow

    async def _validate_workflow_dependencies(self, workflow: WorkflowExecution) -> Dict[str, Any]:
        """Validate that all required services are healthy"""
        required_services = set()

        # Extract all service names from workflow steps
        for step in workflow.steps:
            required_services.add(step.service_name)

        # Check service health
        unhealthy_services = []
        dependency_issues = []

        for service_name in required_services:
            service = self.service_map.get_service(service_name)
            if not service:
                dependency_issues.append(f"Service {service_name} not registered")
                continue

            # Check health status
            health_data = self.health_registry.get_service_health(service_name)
            if not health_data or health_data.overall_status not in ["healthy", "degraded"]:
                unhealthy_services.append(service_name)

        if dependency_issues or unhealthy_services:
            return {
                "valid": False,
                "error": f"Unhealthy services: {unhealthy_services}, Issues: {dependency_issues}"
            }

        return {"valid": True}

    async def _execute_workflow_steps(self, workflow: WorkflowExecution):
        """Execute workflow steps respecting dependencies"""
        completed_steps = set()
        pending_steps = [step for step in workflow.steps]

        while pending_steps:
            # Find steps that can be executed
            executable_steps = []
            for step in pending_steps:
                if all(dep_id in completed_steps for dep_id in step.depends_on):
                    executable_steps.append(step)

            if not executable_steps:
                # No steps can be executed, potential circular dependency or stuck workflow
                remaining_deps = set()
                for step in pending_steps:
                    remaining_deps.update(dep_id for dep_id in step.depends_on if dep_id not in completed_steps)
                workflow.fail_workflow(f"Workflow stuck - cannot execute remaining steps. Missing dependencies: {remaining_deps}")
                return

            # Execute all executable steps concurrently
            execution_tasks = []
            for step in executable_steps:
                task = asyncio.create_task(self._execute_step(step, workflow))
                execution_tasks.append((step, task))

            # Wait for all steps to complete
            for step, task in execution_tasks:
                try:
                    await task
                    completed_steps.add(step.step_id)
                    pending_steps.remove(step)
                    workflow.update_progress()
                except Exception as e:
                    workflow.fail_workflow(f"Step {step.step_id} failed: {str(e)}")
                    return

    async def _execute_step(self, step, workflow: WorkflowExecution):
        """Execute individual workflow step"""
        print(f"🚀 Executing step: {step.name} on {step.service_name}")

        step.start_execution()

        try:
            # Get service configuration
            service = self.service_map.get_service(step.service_name)
            if not service or not service.api_port:
                raise ValueError(f"Service {step.service_name} not properly configured")

            # Prepare API call
            service_url = f"http://localhost:{service.api_port}"
            call_url = f"{service_url}{step.endpoint}"

            # Prepare request data
            call_params = self._prepare_step_parameters(step, workflow)

            # Execute service call in thread pool
            await asyncio.to_thread(self._call_service_endpoint, call_url, step, call_params, workflow)

            # Success - captures response in step.result_data
            step.complete_execution(step.result_data)
            print(f"✅ Step completed: {step.name}")

        except Exception as e:
            error_msg = f"Step execution failed: {str(e)}"
            step.fail_execution(error_msg)
            print(f"❌ Step failed: {step.name} - {error_msg}")
            raise

    def _prepare_step_parameters(self, step, workflow: WorkflowExecution) -> Dict[str, Any]:
        """Prepare parameters for service call"""
        params = {}

        # Map workflow inputs to step inputs
        for input_key, workflow_key in step.input_mapping.items():
            if workflow_key in workflow.input_parameters:
                params[input_key] = workflow.input_parameters[workflow_key]
            elif workflow_key in workflow.context_data:
                params[input_key] = workflow.context_data[workflow_key]

        # Add step-specific parameters
        if step.validation_parameters:
            params.update(step.validation_parameters)

        return params

    def _call_service_endpoint(self, url: str, step, params: Dict[str, Any],
                              workflow: WorkflowExecution):
        """Execute actual service call (runs in thread pool)"""
        import requests

        try:
            # Make HTTP request based on method
            if step.method == "POST":
                response = requests.post(url, json=params, timeout=step.timeout_seconds)
            elif step.method == "GET":
                response = requests.get(url, params=params, timeout=step.timeout_seconds)
            elif step.method == "PUT":
                response = requests.put(url, json=params, timeout=step.timeout_seconds)
            elif step.method == "DELETE":
                response = requests.delete(url, params=params, timeout=step.timeout_seconds)
            else:
                response = requests.get(url, params=params, timeout=step.timeout_seconds)

            # Store response data
            if response.status_code < 400:
                try:
                    step.result_data = response.json()
                except:
                    step.result_data = {
                        "status_code": response.status_code,
                        "text_response": response.text[:1000]
                    }

                # Update workflow context with output mapping
                for workflow_key, step_key in step.output_mapping.items():
                    if isinstance(step.result_data, dict) and step_key in step.result_data:
                        workflow.context_data[workflow_key] = step.result_data[step_key]

            else:
                raise ValueError(f"Service call failed with status {response.status_code}: {response.text}")

        except requests.exceptions.Timeout:
            raise ValueError(f"Service call to {url} timed out")
        except requests.exceptions.ConnectionError:
            raise ValueError(f"Cannot connect to service at {url}")
        except Exception as e:
            raise ValueError(f"Service call error: {str(e)}")

    def _apply_governance_audit(self, workflow: WorkflowExecution, context: str):
        """Apply governance audit lenses to orchestration activities"""
        audit_target = {
            "workflow_type": workflow.workflow_type.value,
            "orchestration_context": context,
            "progress_percentage": workflow.progress_percentage,
            "step_count": len(workflow.steps) if workflow.steps else 0,
            "failed_steps": len(workflow.failed_steps)
        }

        # Apply scalability lens for service orchestration patterns
        scalability_findings = self.audit_framework.apply_lens(
            AuditLens.SCALABILITY_GROWTH,
            audit_target,
            {"context": "service_orchestration"}
        )

        # Apply reliability lens for orchestration error handling
        reliability_findings = self.audit_framework.apply_lens(
            AuditLens.RELIABILITY_CONTINUITY,
            audit_target,
            {"context": "workflow_execution"}
        )

        # Log significant audit findings
        all_findings = scalability_findings + reliability_findings
        for finding in all_findings:
            if finding.severity == "high" or finding.severity == "blocker":
                print(f"🔍 Audit Finding: {finding.title} - {finding.description}")

    async def process_user_request(self, request: UserRequest) -> WorkflowExecution:
        """Process a user request by creating and orchestrating appropriate workflow"""

        print(f"📋 Processing user request type: {request.request_type.value}")

        if request.request_type == "search":
            workflow = self._create_search_workflow(request)
        elif request.request_type == "download":
            workflow = self._create_download_workflow(request)
        elif request.request_type == "recommend":
            workflow = self._create_recommendation_workflow(request)
        else:
            # Generic workflow
            workflow = WorkflowExecution(
                workflow_id="",
                workflow_type=WorkflowType.SEARCH,  # Default
                user_id=request.user_id,
                name=f"Request: {request.request_type.value}",
                description=request.content
            )

        # Orchestrate the workflow
        orchestrated_workflow = await self.orchestrate_workflow(workflow)

        # Update request with workflow information
        request.workflow_id = orchestrated_workflow.workflow_id

        return orchestrated_workflow

    def _create_search_workflow(self, request: UserRequest) -> WorkflowExecution:
        """Create search workflow from user request"""

        from services.shared.models.workflow import WorkflowStep

        workflow = WorkflowExecution(
            workflow_id="",
            workflow_type=WorkflowType.SEARCH,
            user_id=request.user_id,
            name=f"Search: {request.content[:30]}",
            description=f"Search audiobook collection for '{request.content}'"
        )

        steps = [
            WorkflowStep(
                step_id="search_validate",
                name="Validate Search Request",
                description="Validate and sanitize search query",
                service_name="bookfairy-orchestration",  # Internal validation
                endpoint="/validate/search",
                method="POST",
                validation_parameters={"query": request.content}
            ),
            WorkflowStep(
                step_id="search_execute",
                name="Execute Library Search",
                description="Search Audiobookshelf library",
                service_name="audiobookshelf",
                endpoint="/api/libraries/main/search",
                method="GET",
                depends_on=["search_validate"]
            ),
            WorkflowStep(
                step_id="search_format",
                name="Format Search Results",
                description="Format results for Discord response",
                service_name="bookfairy-orchestration",  # Internal processing
                endpoint="/format/results",
                method="POST",
                depends_on=["search_execute"]
            )
        ]

        workflow.steps = steps
        return workflow

    def _create_download_workflow(self, request: UserRequest) -> WorkflowExecution:
        """Create download workflow (placeholder - would need more complexity)"""
        from services.shared.models.workflow import WorkflowStep

        workflow = WorkflowExecution(
            workflow_id="",
            workflow_type=WorkflowType.DOWNLOAD,
            user_id=request.user_id,
            name="Download Request",
            description=f"Initiate download for: {request.content}"
        )

        # Simplified download workflow
        workflow.steps = [
            WorkflowStep(
                step_id="download_init",
                name="Initialize Download",
                description="Create download request",
                service_name="lazylibrarian",
                endpoint="/api/download",
                method="POST"
            )
        ]

        return workflow

    def _create_recommendation_workflow(self, request: UserRequest) -> WorkflowExecution:
        """Create AI recommendation workflow"""
        from services.shared.models.workflow import WorkflowStep

        workflow = WorkflowExecution(
            workflow_id="",
            workflow_type=WorkflowType.RECOMMEND,
            user_id=request.user_id,
            name="AI Recommendations",
            description=f"Get AI recommendations based on: {request.content}"
        )

        workflow.steps = [
            WorkflowStep(
                step_id="analyze_profile",
                name="Analyze User Profile",
                description="Get user reading history from Audiobookshelf",
                service_name="audiobookshelf",
                endpoint="/api/users/profile",
                method="GET"
            ),
            WorkflowStep(
                step_id="generate_ai",
                name="Generate AI Recommendations",
                description="Use LM Studio for AI-powered recommendations",
                service_name="lm-studio",
                endpoint="/v1/completions",
                method="POST",
                depends_on=["analyze_profile"]
            ),
            WorkflowStep(
                step_id="format_response",
                name="Format AI Response",
                description="Format recommendations for human-readable output",
                service_name="bookfairy-orchestration",
                endpoint="/format/recommendations",
                method="POST",
                depends_on=["generate_ai"]
            )
        ]

        return workflow

    def get_service_status(self, service_name: str) -> Dict[str, Any]:
        """Get detailed status of a specific service"""
        service = self.service_map.get_service(service_name)
        if not service:
            return {"error": "Service not found"}

        health_data = self.health_registry.get_service_health(service_name)
        if health_data:
            return {
                "service_name": service_name,
                "registered": True,
                "health_status": health_data.overall_status.value,
                "last_health_check": health_data.last_updated.isoformat() if health_data.last_updated else None
            }
        else:
            return {
                "service_name": service_name,
                "registered": True,
                "health_status": "unknown",
                "last_health_check": None
            }

    def get_system_overview(self) -> Dict[str, Any]:
        """Get comprehensive system orchestration overview"""
        total_services = len(self.service_map.services)
        healthy_services = 0
        for service_name in self.service_map.services.keys():
            health_data = self.health_registry.get_service_health(service_name)
            if health_data and health_data.overall_status == "healthy":
                healthy_services += 1

        active_workflows = len([w for w in self.workflow_registry.workflows.values()
                              if w.status == WorkflowStatus.RUNNING])

        return {
            "total_services": total_services,
            "healthy_services": healthy_services,
            "service_health_percentage": (healthy_services / total_services * 100) if total_services > 0 else 0,
            "active_workflows": active_workflows,
            "total_workflows_executed": len(self.workflow_registry.workflows),
            "timestamp": datetime.utcnow().isoformat()
        }

    def export_audit_trail(self) -> List[Dict[str, Any]]:
        """Export orchestration audit trail for compliance reporting"""
        audit_data = []

        for workflow in self.workflow_registry.workflows.values():
            audit_data.append({
                "workflow_id": workflow.workflow_id,
                "workflow_type": workflow.workflow_type.value,
                "user_id": workflow.user_id,
                "status": workflow.status.value,
                "total_execution_time_ms": workflow.total_execution_time_ms,
                "step_count": len(workflow.steps),
                "failed_steps": len(workflow.failed_steps),
                "governace_audits_applied": len(workflow.audit_lens_applied),
                "created_at": workflow.created_at.isoformat(),
                "completed_at": workflow.completed_at.isoformat() if workflow.completed_at else None
            })

        return audit_data


async def main():
    """Main orchestration service entry point"""

    orchestrator = ServiceOrchestrator()
    orchestrator.initialize_services()

    print("BookFairy Orchestration Service started")
    print(f"Available services: {list(orchestrator.service_map.services.keys())}")
    print("\n" + "="*60)

    # Get system overview
    overview = orchestrator.get_system_overview()
    print("📊 SYSTEM OVERVIEW:")
    print(".1f")
    print(f"   Active workflows: {overview['active_workflows']}")
    print(f"   Total workflows: {overview['total_workflows_executed']}")

    # Test orchestration with a mock workflow
    print("\n🧪 Testing orchestration with mock user request...")

    test_request = UserRequest(
        request_id="",
        user_id="test_user_123",
        request_type="search",
        content="science fiction audiobooks",
        parameters={"max_results": 5}
    )

    try:
        orchestrated_workflow = await orchestrator.process_user_request(test_request)
        print(f"✅ Mock orchestration completed: {orchestrated_workflow.workflow_id}")
        print(f"   Status: {orchestrated_workflow.status.value}")
        print(f"   Steps executed: {len(orchestrated_workflow.steps)}")

    except Exception as e:
        print(f"❌ Mock orchestration failed: {e}")

    print("\n🔄 Orchestration service ready for workflow requests")
    print("Waiting for Discord bot or other services to submit workflows...")

    # Keep service running
    try:
        while True:
            await asyncio.sleep(60)
            # Could periodically check for stuck workflows here

    except KeyboardInterrupt:
        print("\n🛑 Orchestration service stopped by user")
    except Exception as e:
        print(f"\n❌ Orchestration service error: {e}")
    finally:
        orchestrator.execution_executor.shutdown(wait=True)
        print("🏁 Orchestration service shutdown complete")


if __name__ == "__main__":
    asyncio.run(main())
