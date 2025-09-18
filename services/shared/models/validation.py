"""
Validation Protocol Model
Comprehensive validation procedures and compliance checking
Based on data-model.md specification and integration tests
"""
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Callable
from datetime import datetime
from enum import Enum


class ValidationStepType(Enum):
    """Types of validation steps"""
    HEALTH_CHECK = "health_check"              # Service health verification
    CONNECTIVITY_TEST = "connectivity_test"    # Service-to-service communication
    GREEN_LIGHT_CONFIRMATION = "green_light_confirmation"  # Stakeholder approval
    PERFORMANCE_VALIDATION = "performance_validation"      # Performance benchmarks
    SECURITY_VALIDATION = "security_validation"           # Security compliance
    FUNCTIONAL_TEST = "functional_test"                   # Core functionality test
    INTEGRATION_TEST = "integration_test"                # Multi-service integration


class ValidationStatus(Enum):
    """Status of validation steps"""
    PENDING = "pending"            # Not started yet
    RUNNING = "running"           # Currently executing
    PASSED = "passed"             # Validation successful
    FAILED = "failed"             # Validation failed
    BLOCKED = "blocked"           # Blocked by dependencies
    SKIPPED = "skipped"           # Validation skipped
    TIMEOUT = "timeout"           # Validation timed out


@dataclass
class ValidationStep:
    """Individual validation step in protocol"""

    step_id: str
    name: str
    step_type: ValidationStepType

    # Step configuration
    service_name: Optional[str] = None
    endpoint: Optional[str] = None
    expected_status_code: int = 200

    # Execution parameters
    timeout_seconds: int = 300
    retry_count: int = 0
    max_retries: int = 3
    required_for_completion: bool = True

    # Dependencies (other step IDs that must complete first)
    depends_on: List[str] = field(default_factory=list)

    # Validation logic
    validation_function: Optional[Callable] = None
    validation_parameters: Dict[str, Any] = field(default_factory=dict)

    # Results
    status: ValidationStatus = ValidationStatus.PENDING
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    execution_time_ms: Optional[int] = None

    # Success criteria
    success_criteria: Dict[str, Any] = field(default_factory=dict)
    actual_results: Dict[str, Any] = field(default_factory=dict)

    # Error handling
    error_message: Optional[str] = None
    logs: List[str] = field(default_factory=list)

    def __post_init__(self):
        """Initialize validation step"""
        if self.success_criteria.get("response_time_max_ms"):
            self.success_criteria.setdefault("timeout_seconds", 30)
        if not self.step_id:
            self.step_id = f"vstep_{self.step_type.value}_{self.service_name or 'system'}_{int(datetime.utcnow().timestamp())}"

    def start_execution(self):
        """Mark step as started"""
        self.status = ValidationStatus.RUNNING
        self.started_at = datetime.utcnow()

    def complete_successfully(self, results: Optional[Dict[str, Any]] = None,
                            execution_time: Optional[int] = None):
        """Mark step as completed successfully"""
        self.status = ValidationStatus.PASSED
        self.completed_at = datetime.utcnow()
        self.actual_results = results or {}
        if execution_time:
            self.execution_time_ms = execution_time

    def complete_with_failure(self, error_message: str, details: Optional[Dict[str, Any]] = None):
        """Mark step as failed"""
        self.status = ValidationStatus.FAILED
        self.completed_at = datetime.utcnow()
        self.error_message = error_message
        if details:
            self.actual_results.update(details)

        # Calculate execution time
        if self.started_at:
            delta = self.completed_at - self.started_at
            self.execution_time_ms = int(delta.total_seconds() * 1000)

    def is_ready(self) -> bool:
        """Check if step is ready to execute (dependencies met)"""
        if not self.depends_on:
            return True
        # Note: Dependency checking would need access to validation registry
        # For now, assume ready if no dependencies or status is PENDING
        return self.status == ValidationStatus.PENDING

    def check_success_criteria(self) -> bool:
        """Check if step results meet success criteria"""
        if not self.success_criteria:
            return True  # No criteria means always successful if completed

        # Check response time (if specified)
        max_time = self.success_criteria.get("response_time_max_ms")
        if max_time and self.execution_time_ms:
            if self.execution_time_ms > max_time:
                return False

        # Check HTTP status (if specified)
        expected_status = self.success_criteria.get("status_code", self.expected_status_code)
        actual_status = self.actual_results.get("status_code")
        if expected_status and actual_status:
            if actual_status != expected_status:
                return False

        # Check custom validation function results
        if self.actual_results.get("validation_passed") is False:
            return False

        return True

    def get_execution_time_str(self) -> str:
        """Get human-readable execution time"""
        if not self.execution_time_ms:
            return "Not executed"

        ms = self.execution_time_ms
        if ms < 1000:
            return f"{ms}ms"
        elif ms < 60000:
            return ".1f"
        else:
            return ".1f"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "step_id": self.step_id,
            "name": self.name,
            "step_type": self.step_type.value,
            "service_name": self.service_name,
            "endpoint": self.endpoint,
            "expected_status_code": self.expected_status_code,
            "timeout_seconds": self.timeout_seconds,
            "retry_count": self.retry_count,
            "max_retries": self.max_retries,
            "required_for_completion": self.required_for_completion,
            "depends_on": self.depends_on,
            "validation_parameters": self.validation_parameters,
            "status": self.status.value,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "execution_time_ms": self.execution_time_ms,
            "success_criteria": self.success_criteria,
            "actual_results": self.actual_results,
            "error_message": self.error_message,
            "logs": self.logs[:10]  # Limit logs to last 10 entries
        }


@dataclass
class ValidationProtocol:
    """Complete validation protocol for a deliverable or workflow"""

    protocol_id: str
    name: str
    description: str

    # Protocol scope
    deliverable_name: str = ""    # What is being validated
    environment: str = "development"  # dev, staging, production

    # Validation steps
    validation_steps: List[ValidationStep] = field(default_factory=list)

    # Execution tracking
    created_at: datetime = field(default_factory=datetime.utcnow)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    total_execution_time_ms: Optional[int] = None

    # Results summary
    total_steps: int = 0
    passed_steps: int = 0
    failed_steps: int = 0
    skipped_steps: int = 0
    overall_status: str = "not_started"

    # Compliance and governance
    stakeholder_approvals: Dict[str, bool] = field(default_factory=dict)
    compliance_flags: List[str] = field(default_factory=list)

    def __post_init__(self):
        """Initialize validation protocol"""
        if not self.protocol_id:
            self.protocol_id = f"prot_{int(datetime.utcnow().timestamp())}"
        self.keyword = self.deliverable_name.replace(" ", "_").lower()

    def add_step(self, step: ValidationStep):
        """Add a validation step to the protocol"""
        self.validation_steps.append(step)
        self.total_steps = len(self.validation_steps)

    def start_validation(self):
        """Start protocol execution"""
        self.started_at = datetime.utcnow()
        self.overall_status = "running"

    def complete_validation(self):
        """Complete protocol execution with results summary"""
        self.completed_at = datetime.utcnow()
        self._calculate_results()

        if self.started_at:
            delta = self.completed_at - self.started_at
            self.total_execution_time_ms = int(delta.total_seconds() * 1000)

    def _calculate_results(self):
        """Calculate overall results from step outcomes"""
        self.passed_steps = sum(1 for step in self.validation_steps
                              if step.status == ValidationStatus.PASSED)
        self.failed_steps = sum(1 for step in self.validation_steps
                              if step.status == ValidationStatus.FAILED)
        self.skipped_steps = sum(1 for step in self.validation_steps
                               if step.status == ValidationStatus.SKIPPED)

        # Determine overall status
        required_steps_passed = True
        for step in self.validation_steps:
            if step.required_for_completion and step.status != ValidationStatus.PASSED:
                required_steps_passed = False
                break

        if required_steps_passed and self.failed_steps == 0:
            self.overall_status = "completed"
        elif self.failed_steps > 0:
            self.overall_status = "failed"
        elif self.passed_steps > 0:
            self.overall_status = "partial"
        else:
            self.overall_status = "not_started"

    def get_next_executable_steps(self) -> List[ValidationStep]:
        """Get steps that can be executed (dependencies resolved)"""
        executable = []

        for step in self.validation_steps:
            if step.status != ValidationStatus.PENDING:
                continue

            # Check dependencies
            dependencies_met = True
            for dep_step_id in step.depends_on:
                dep_step = self.get_step(dep_step_id)
                if not dep_step or dep_step.status != ValidationStatus.PASSED:
                    dependencies_met = False
                    step.status = ValidationStatus.BLOCKED
                    break

            if dependencies_met:
                executable.append(step)

        return executable

    def get_step(self, step_id: str) -> Optional[ValidationStep]:
        """Get validation step by ID"""
        return next((step for step in self.validation_steps if step.step_id == step_id), None)

    def is_complete(self) -> bool:
        """Check if validation protocol is complete"""
        return self.overall_status in ["completed", "failed"]

    def can_proceed_to_green_light(self) -> bool:
        """Check if protocol allows proceeding to final green light"""
        # Must have completed all required steps
        for step in self.validation_steps:
            if step.required_for_completion and step.status != ValidationStatus.PASSED:
                return False

        # Must have all critical stakeholder approvals
        critical_stakeholders = ["infrastructure", "security", "business_owner"]
        for stakeholder in critical_stakeholders:
            if stakeholder in self.stakeholder_approvals and not self.stakeholder_approvals[stakeholder]:
                return False

        # No blocking compliance flags
        blocking_flags = ["security_violation", "data_breach", "stop_production"]
        if any(flag in self.compliance_flags for flag in blocking_flags):
            return False

        return True

    def get_detailed_report(self) -> Dict[str, Any]:
        """Generate detailed validation report"""
        step_reports = []
        for step in self.validation_steps:
            step_reports.append({
                "step_id": step.step_id,
                "name": step.name,
                "status": step.status.value,
                "execution_time": step.get_execution_time_str(),
                "success": step.check_success_criteria(),
                "error_message": step.error_message,
                "logs": step.logs
            })

        return {
            "protocol_id": self.protocol_id,
            "protocol_name": self.name,
            "deliverable_name": self.deliverable_name,
            "environment": self.environment,
            "overall_status": self.overall_status,
            "step_results": step_reports,
            "can_proceed": self.can_proceed_to_green_light(),
            "total_steps": self.total_steps,
            "passed_steps": self.passed_steps,
            "failed_steps": self.failed_steps,
            "skipped_steps": self.skipped_steps,
            "total_execution_time_ms": self.total_execution_time_ms,
            "compliance_flags": self.compliance_flags,
            "stakeholder_approvals": self.stakeholder_approvals,
            "timestamp": datetime.utcnow().isoformat()
        }

    def to_dict(self) -> Dict[str, Any]:
        return {
            "protocol_id": self.protocol_id,
            "name": self.name,
            "description": self.description,
            "deliverable_name": self.deliverable_name,
            "environment": self.environment,
            "validation_steps": [step.to_dict() for step in self.validation_steps],
            "created_at": self.created_at.isoformat(),
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "total_execution_time_ms": self.total_execution_time_ms,
            "total_steps": self.total_steps,
            "passed_steps": self.passed_steps,
            "failed_steps": self.failed_steps,
            "skipped_steps": self.skipped_steps,
            "overall_status": self.overall_status,
            "stakeholder_approvals": self.stakeholder_approvals,
            "compliance_flags": self.compliance_flags
        }


class ValidationProtocolRegistry:
    """Registry for managing validation protocols"""

    def __init__(self):
        self.protocols: Dict[str, ValidationProtocol] = {}
        self.deliverable_protocols: Dict[str, List[str]] = {}

    def register_protocol(self, protocol: ValidationProtocol):
        """Register a validation protocol"""
        self.protocols[protocol.protocol_id] = protocol

        # Index by deliverable
        deliverable = protocol.deliverable_name
        if deliverable not in self.deliverable_protocols:
            self.deliverable_protocols[deliverable] = []
        self.deliverable_protocols[deliverable].append(protocol.protocol_id)

    def get_protocol(self, protocol_id: str) -> Optional[ValidationProtocol]:
        """Get validation protocol by ID"""
        return self.protocols.get(protocol_id)

    def get_protocols_for_deliverable(self, deliverable_name: str) -> List[ValidationProtocol]:
        """Get all protocols for a deliverable"""
        protocol_ids = self.deliverable_protocols.get(deliverable_name, [])
        return [self.protocols[pid] for pid in protocol_ids if pid in self.protocols]

    def get_system_validation_status(self) -> Dict[str, Any]:
        """Get overall validation system status"""
        total_protocols = len(self.protocols)
        completed_protocols = sum(1 for p in self.protocols.values() if p.is_complete())
        passed_protocols = sum(1 for p in self.protocols.values() if p.overall_status == "completed")
        failed_protocols = sum(1 for p in self.protocols.values() if p.overall_status == "failed")

        # Check protocols ready for green light
        ready_for_green_light = sum(1 for p in self.protocols.values()
                                  if p.can_proceed_to_green_light())

        return {
            "total_validation_protocols": total_protocols,
            "completed_protocols": completed_protocols,
            "passed_protocols": passed_protocols,
            "failed_protocols": failed_protocols,
            "ready_for_green_light": ready_for_green_light,
            "deliverables_covered": len(self.deliverable_protocols),
            "timestamp": datetime.utcnow().isoformat()
        }
