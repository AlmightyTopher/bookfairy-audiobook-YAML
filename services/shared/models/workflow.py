"""
Workflow State Model
Manages the state and lifecycle of BookFairy workflows
Based on data-model.md specification and quickstart.md integration tests
"""
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Union
from datetime import datetime, timedelta
from enum import Enum
import uuid


class WorkflowType(Enum):
    """Types of workflows supported by BookFairy"""
    SEARCH = "search"                    # Search for audiobooks
    DOWNLOAD = "download"               # Download specific audiobook
    PROCESS = "process"                 # Process downloaded files
    RECOMMEND = "recommend"             # AI recommendations
    BATCH_PROCESS = "batch_process"     # Process multiple items
    HEALTH_CHECK = "health_check"       # System health evaluation
    GOVERNANCE_AUDIT = "governance_audit" # Governance compliance check


class WorkflowStatus(Enum):
    """Workflow execution states"""
    PENDING = "pending"          # Waiting to start
    INITIALIZING = "initializing" # Setting up resources
    RUNNING = "running"         # Actively executing
    PAUSED = "paused"           # Temporarily suspended
    COMPLETED = "completed"     # Finished successfully
    FAILED = "failed"           # Failed with error
    CANCELLED = "cancelled"     # Manually cancelled
    TIMEOUT = "timeout"         # Timed out
    RETRYING = "retrying"       # Attempting retry


@dataclass
class WorkflowStep:
    """Represents a single step in a workflow"""

    step_id: str
    name: str
    description: str
    service_name: str  # Which service executes this step
    endpoint: str     # API endpoint to call
    method: str = "POST"  # HTTP method

    # Execution properties
    timeout_seconds: int = 300
    retry_count: int = 0
    max_retries: int = 3

    # Dependencies
    depends_on: List[str] = field(default_factory=list)  # Step IDs this depends on
    required: bool = True

    # Input/output mapping
    input_mapping: Dict[str, str] = field(default_factory=dict)  # Map workflow inputs to step inputs
    output_mapping: Dict[str, str] = field(default_factory=dict)  # Map step outputs to workflow context

    # Status
    status: WorkflowStatus = WorkflowStatus.PENDING
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    error_message: Optional[str] = None
    execution_time_ms: Optional[int] = None

    # Results
    result_data: Optional[Any] = None
    logs: List[str] = field(default_factory=list)

    def __post_init__(self):
        """Validate step configuration"""
        if not self.step_id:
            self.step_id = str(uuid.uuid4())

    def start_execution(self):
        """Mark step as started"""
        self.status = WorkflowStatus.RUNNING
        self.started_at = datetime.utcnow()

    def complete_execution(self, result: Any = None, execution_time: Optional[int] = None):
        """Mark step as completed successfully"""
        self.status = WorkflowStatus.COMPLETED
        self.completed_at = datetime.utcnow()
        self.result_data = result
        if execution_time:
            self.execution_time_ms = execution_time

    def fail_execution(self, error_message: str):
        """Mark step as failed"""
        self.status = WorkflowStatus.FAILED
        self.completed_at = datetime.utcnow()
        self.error_message = error_message

        # Calculate execution time if we have start time
        if self.started_at:
            execution_delta = self.completed_at - self.started_at
            self.execution_time_ms = int(execution_delta.total_seconds() * 1000)

    def can_execute(self) -> bool:
        """Check if step can be executed (all dependencies met)"""
        return (
            self.status == WorkflowStatus.PENDING and
            self.depends_on is None or len(self.depends_on) == 0
        )

    def is_completed(self) -> bool:
        """Check if step is completed"""
        return self.status == WorkflowStatus.COMPLETED

    def has_failed(self) -> bool:
        """Check if step has failed"""
        return self.status == WorkflowStatus.FAILED

    def get_execution_time_ms(self) -> Optional[int]:
        """Get total execution time in milliseconds"""
        if self.started_at and self.completed_at:
            delta = self.completed_at - self.started_at
            return int(delta.total_seconds() * 1000)
        return self.execution_time_ms

    def to_dict(self) -> Dict[str, Any]:
        return {
            "step_id": self.step_id,
            "name": self.name,
            "description": self.description,
            "service_name": self.service_name,
            "endpoint": self.endpoint,
            "method": self.method,
            "timeout_seconds": self.timeout_seconds,
            "retry_count": self.retry_count,
            "max_retries": self.max_retries,
            "depends_on": self.depends_on,
            "required": self.required,
            "input_mapping": self.input_mapping,
            "output_mapping": self.output_mapping,
            "status": self.status.value,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "error_message": self.error_message,
            "execution_time_ms": self.get_execution_time_ms(),
            "result_data": self.result_data,
            "logs": self.logs
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'WorkflowStep':
        """Create from dictionary"""
        # Handle enum conversion
        if 'status' in data:
            data['status'] = WorkflowStatus(data['status'])

        # Handle datetime parsing
        for datetime_field in ['started_at', 'completed_at']:
            if data.get(datetime_field):
                data[datetime_field] = datetime.fromisoformat(data[datetime_field])

        return cls(**data)


@dataclass
class WorkflowExecution:
    """Represents the state and context of a workflow execution"""

    workflow_id: str
    workflow_type: WorkflowType
    user_id: str

    # Workflow definition
    name: str
    description: str
    steps: List[WorkflowStep] = field(default_factory=list)

    # Execution state
    status: WorkflowStatus = WorkflowStatus.PENDING
    progress_percentage: float = 0.0
    current_step: Optional[str] = None  # Current step ID

    # Timing
    created_at: datetime = field(default_factory=datetime.utcnow)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    total_execution_time_ms: Optional[int] = None

    # Context and data
    input_parameters: Dict[str, Any] = field(default_factory=dict)
    context_data: Dict[str, Any] = field(default_factory=dict)  # Shared context between steps
    output_results: Dict[str, Any] = field(default_factory=dict)

    # Error handling
    failed_steps: List[str] = field(default_factory=list)
    error_message: Optional[str] = None

    # Retry and recovery
    retry_count: int = 0
    max_retries: int = 3
    last_retry_at: Optional[datetime] = None

    # Governance
    audit_lens_applied: List[str] = field(default_factory=list)

    def __post_init__(self):
        """Validate workflow configuration"""
        if not self.workflow_id:
            self.workflow_id = str(uuid.uuid4())

        # Validate step dependencies
        step_ids = {step.step_id for step in self.steps}
        for step in self.steps:
            for dep_id in step.depends_on:
                if dep_id not in step_ids:
                    raise ValueError(f"Step {step.step_id} depends on non-existent step {dep_id}")

    def start_workflow(self):
        """Mark workflow as started"""
        self.status = WorkflowStatus.RUNNING
        self.started_at = datetime.utcnow()

    def complete_workflow(self, results: Optional[Dict[str, Any]] = None):
        """Mark workflow as completed successfully"""
        self.status = WorkflowStatus.COMPLETED
        self.completed_at = datetime.utcnow()
        if results:
            self.output_results.update(results)
        self.progress_percentage = 100.0

        # Calculate total execution time
        if self.started_at:
            delta = self.completed_at - self.started_at
            self.total_execution_time_ms = int(delta.total_seconds() * 1000)

    def fail_workflow(self, error_message: str):
        """Mark workflow as failed"""
        self.status = WorkflowStatus.FAILED
        self.completed_at = datetime.utcnow()
        self.error_message = error_message

        # Calculate total execution time
        if self.started_at:
            delta = self.completed_at - self.started_at
            self.total_execution_time_ms = int(delta.total_seconds() * 1000)

    def cancel_workflow(self):
        """Mark workflow as cancelled"""
        self.status = WorkflowStatus.CANCELLED
        self.completed_at = datetime.utcnow()

    def add_step_result(self, step_id: str, result: Any):
        """Add result from a completed step"""
        self.context_data[f"step_{step_id}_result"] = result
        self.output_results[step_id] = result

    def get_next_executable_steps(self) -> List[WorkflowStep]:
        """Get steps that are ready to execute"""
        executable_steps = []

        for step in self.steps:
            if not step.can_execute():
                continue

            # Check if all dependencies are completed
            dependencies_met = True
            for dep_id in step.depends_on:
                dep_step = self.get_step(dep_id)
                if not dep_step or not dep_step.is_completed():
                    dependencies_met = False
                    break

            if dependencies_met:
                executable_steps.append(step)

        return executable_steps

    def get_step(self, step_id: str) -> Optional[WorkflowStep]:
        """Get step by ID"""
        return next((step for step in self.steps if step.step_id == step_id), None)

    def update_progress(self):
        """Update workflow progress based on completed steps"""
        if not self.steps:
            self.progress_percentage = 100.0
            return

        completed_steps = sum(1 for step in self.steps if step.is_completed())
        total_steps = len(self.steps)

        # Weight by whether steps are required
        required_steps = sum(1 for step in self.steps if step.required)
        required_completed = sum(
            1 for step in self.steps
            if step.required and step.is_completed()
        )

        if required_steps > 0:
            self.progress_percentage = (required_completed / required_steps) * 100.0
        else:
            self.progress_percentage = (completed_steps / total_steps) * 100.0

        # Cap at 95% until workflow is fully complete
        if self.progress_percentage >= 95.0 and self.status != WorkflowStatus.COMPLETED:
            self.progress_percentage = 95.0

    def can_retry(self) -> bool:
        """Check if workflow can be retried"""
        return (
            self.status in [WorkflowStatus.FAILED, WorkflowStatus.TIMEOUT] and
            self.retry_count < self.max_retries
        )

    def retry_workflow(self):
        """Retry workflow execution"""
        self.retry_count += 1
        self.last_retry_at = datetime.utcnow()
        self.status = WorkflowStatus.RETRYING
        self.error_message = None

        # Reset failed steps to pending
        for step in self.steps:
            if step.has_failed():
                step.status = WorkflowStatus.PENDING
                step.error_message = None
                step.started_at = None
                step.completed_at = None

        self.failed_steps.clear()
        self.progress_percentage = 0.0

    def is_completed_successfully(self) -> bool:
        """Check if workflow completed successfully"""
        return (
            self.status == WorkflowStatus.COMPLETED and
            len(self.failed_steps) == 0 and
            all(step.is_completed() for step in self.steps if step.required)
        )

    def is_stuck(self) -> bool:
        """Check if workflow is stuck (has pending steps but no progress)"""
        pending_steps = [step for step in self.steps if step.status == WorkflowStatus.PENDING]
        if not pending_steps:
            return False

        # Check if we've been in pending state too long
        if self.started_at:
            elapsed_time = (datetime.utcnow() - self.started_at).total_seconds()
            # Consider stuck if pending for more than 10 minutes with no progress
            return elapsed_time > 600 and self.progress_percentage < 10.0

        return False

    def get_execution_summary(self) -> Dict[str, Any]:
        """Get comprehensive execution summary"""
        total_steps = len(self.steps)
        completed_steps = sum(1 for step in self.steps if step.is_completed())
        failed_steps = len(self.failed_steps)

        step_summaries = []
        for step in self.steps:
            step_summaries.append({
                "step_id": step.step_id,
                "name": step.name,
                "status": step.status.value,
                "execution_time_ms": step.get_execution_time_ms(),
                "required": step.required
            })

        return {
            "workflow_id": self.workflow_id,
            "workflow_type": self.workflow_type.value,
            "status": self.status.value,
            "progress_percentage": self.progress_percentage,
            "total_steps": total_steps,
            "completed_steps": completed_steps,
            "failed_steps": failed_steps,
            "total_execution_time_ms": self.total_execution_time_ms,
            "step_summaries": step_summaries,
            "error_message": self.error_message,
            "retry_count": self.retry_count
        }

    def to_dict(self) -> Dict[str, Any]:
        return {
            "workflow_id": self.workflow_id,
            "workflow_type": self.workflow_type.value,
            "user_id": self.user_id,
            "name": self.name,
            "description": self.description,
            "steps": [step.to_dict() for step in self.steps],
            "status": self.status.value,
            "progress_percentage": self.progress_percentage,
            "current_step": self.current_step,
            "created_at": self.created_at.isoformat(),
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "total_execution_time_ms": self.total_execution_time_ms,
            "input_parameters": self.input_parameters,
            "context_data": self.context_data,
            "output_results": self.output_results,
            "failed_steps": self.failed_steps,
            "error_message": self.error_message,
            "retry_count": self.retry_count,
            "max_retries": self.max_retries,
            "last_retry_at": self.last_retry_at.isoformat() if self.last_retry_at else None,
            "audit_lens_applied": self.audit_lens_applied
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'WorkflowExecution':
        """Create from dictionary"""
        # Handle enum conversion
        if 'workflow_type' in data:
            data['workflow_type'] = WorkflowType(data['workflow_type'])
        if 'status' in data:
            data['status'] = WorkflowStatus(data['status'])

        # Handle datetime parsing
        for datetime_field in ['created_at', 'started_at', 'completed_at', 'last_retry_at']:
            if data.get(datetime_field):
                data[datetime_field] = datetime.fromisoformat(data[datetime_field])

        # Handle steps reconstruction
        steps_data = data.pop('steps', [])
        data['steps'] = [WorkflowStep.from_dict(step_data) for step_data in steps_data]

        return cls(**data)

    def __repr__(self) -> str:
        return (f"WorkflowExecution(id='{self.workflow_id}', "
                f"type={self.workflow_type.value}, "
                f"status={self.status.value}, "
                f"progress={self.progress_percentage:.1f}%)")


class WorkflowRegistry:
    """Registry for managing multiple workflow executions"""

    def __init__(self):
        self.workflows: Dict[str, WorkflowExecution] = {}
        self.active_workflows: Dict[str, List[str]] = {}  # user_id -> [workflow_ids]

    def register_workflow(self, workflow: WorkflowExecution):
        """Register a new workflow"""
        self.workflows[workflow.workflow_id] = workflow

        # Add to active workflows for this user
        if workflow.user_id not in self.active_workflows:
            self.active_workflows[workflow.user_id] = []
        self.active_workflows[workflow.user_id].append(workflow.workflow_id)

    def get_workflow(self, workflow_id: str) -> Optional[WorkflowExecution]:
        """Get workflow by ID"""
        return self.workflows.get(workflow_id)

    def get_user_workflows(self, user_id: str) -> List[WorkflowExecution]:
        """Get all workflows for a user"""
        workflow_ids = self.active_workflows.get(user_id, [])
        return [self.workflows[wid] for wid in workflow_ids if wid in self.workflows]

    def update_workflow_status(self, workflow_id: str, new_status: WorkflowStatus,
                              error_message: Optional[str] = None):
        """Update workflow status"""
        workflow = self.workflows.get(workflow_id)
        if workflow:
            if new_status == WorkflowStatus.FAILED and error_message:
                workflow.fail_workflow(error_message)
            elif new_status == WorkflowStatus.COMPLETED:
                workflow.complete_workflow()
            elif new_status == WorkflowStatus.CANCELLED:
                workflow.cancel_workflow()
            else:
                workflow.status = new_status

    def purge_completed_workflows(self, older_than_days: int = 7):
        """Purge completed workflows older than specified days"""
        cutoff_time = datetime.utcnow() - timedelta(days=older_than_days)

        workflows_to_purge = []
        for workflow_id, workflow in self.workflows.items():
            if (workflow.status in [WorkflowStatus.COMPLETED, WorkflowStatus.FAILED,
                                  WorkflowStatus.CANCELLED] and
                workflow.completed_at and workflow.completed_at < cutoff_time):
                workflows_to_purge.append(workflow_id)

        for workflow_id in workflows_to_purge:
            del self.workflows[workflow_id]

            # Remove from active workflows
            for user_workflows in self.active_workflows.values():
                if workflow_id in user_workflows:
                    user_workflows.remove(workflow_id)

    def get_system_status(self) -> Dict[str, Any]:
        """Get overall workflow system status"""
        total_workflows = len(self.workflows)
        status_counts = {}
        total_users = len(self.active_workflows)

        for workflow in self.workflows.values():
            status = workflow.status.value
            status_counts[status] = status_counts.get(status, 0) + 1

        # Calculate average progress for running workflows
        running_workflows = [w for w in self.workflows.values()
                           if w.status == WorkflowStatus.RUNNING]
        avg_progress = (sum(w.progress_percentage for w in running_workflows) /
                       len(running_workflows)) if running_workflows else 0.0

        return {
            "total_workflows": total_workflows,
            "total_users": total_users,
            "status_distribution": status_counts,
            "running_workflows": len(running_workflows),
            "average_progress": avg_progress,
            "completed_workflows": status_counts.get('completed', 0),
            "failed_workflows": status_counts.get('failed', 0),
            "timestamp": datetime.utcnow().isoformat()
        }
