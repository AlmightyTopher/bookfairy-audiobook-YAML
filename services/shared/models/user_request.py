"""
User Request Model
Handles Discord bot interactions and user request processing
Based on data-model.md specification and integration tests
"""
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Union
from datetime import datetime
from enum import Enum
import uuid


class RequestType(Enum):
    """Types of user requests supported by BookFairy"""
    SEARCH = "search"                        # Search for audiobooks
    DOWNLOAD = "download"                    # Request download of specific book
    RECOMMEND = "recommend"                  # Get AI recommendations
    STATUS = "status"                        # Check workflow status
    LIST = "list"                           # List available items
    HELP = "help"                           # Show help information
    HEALTH = "health"                        # Health check request
    AUDIT = "audit"                          # Governance audit request
    ADMIN = "admin"                          # Administrative commands


class RequestPriority(Enum):
    """Priority levels for processing requests"""
    LOW = "low"         # Background processing, non-urgent
    NORMAL = "normal"   # Standard user requests
    HIGH = "high"       # Important but not critical
    URGENT = "urgent"   # Requires immediate attention
    CRITICAL = "critical"  # System-critical requests


class RequestSource(Enum):
    """Source of the user request"""
    DISCORD_SLASH_COMMAND = "discord_slash"
    DISCORD_MESSAGE = "discord_message"
    DISCORD_BUTTON = "discord_button"
    DISCORD_SELECT_MENU = "discord_select"
    API_DIRECT = "api_direct"
    WEB_INTERFACE = "web_interface"
    INTERNAL = "internal"  # Internal system requests


@dataclass
class UserRequest:
    """Represents a user request from Discord or other sources"""

    request_id: str
    user_id: str
    request_type: RequestType

    # Request content
    content: str
    parameters: Dict[str, Any] = field(default_factory=dict)

    # Source information
    source: RequestSource = RequestSource.INTERNAL
    channel_id: Optional[str] = None
    message_id: Optional[str] = None
    guild_id: Optional[str] = None

    # Processing status
    priority: RequestPriority = RequestPriority.NORMAL
    status: str = "pending"  # pending, processing, completed, failed, cancelled
    progress_percentage: float = 0.0

    # Timing
    created_at: datetime = field(default_factory=datetime.utcnow)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    estimated_completion_seconds: Optional[int] = None

    # Results and responses
    response_data: Optional[Any] = None
    error_message: Optional[str] = None
    workflow_id: Optional[str] = None  # If request spawned a workflow

    # Retry and rate limiting
    retry_count: int = 0
    max_retries: int = 3
    rate_limit_exceeded: bool = False

    # Governance and audit
    audit_lens_applied: List[str] = field(default_factory=list)
    risk_assessment_score: Optional[float] = None
    compliance_flags: List[str] = field(default_factory=list)

    # User context
    user_context: Dict[str, Any] = field(default_factory=dict)  # Reading preferences, history, etc.
    session_id: Optional[str] = None

    def __post_init__(self):
        """Validate request configuration"""
        if not self.request_id:
            self.request_id = str(uuid.uuid4())

        # Auto-detect priority based on request type if not specified
        if self.priority == RequestPriority.NORMAL:
            priority_map = {
                RequestType.HEALTH: RequestPriority.LOW,
                RequestType.SEARCH: RequestPriority.NORMAL,
                RequestType.DOWNLOAD: RequestPriority.HIGH,
                RequestType.AUDIT: RequestPriority.HIGH,
                RequestType.ADMIN: RequestPriority.CRITICAL,
            }
            self.priority = priority_map.get(self.request_type, RequestPriority.NORMAL)

    def start_processing(self):
        """Mark request as started"""
        self.status = "processing"
        self.started_at = datetime.utcnow()

    def complete_request(self, response_data: Any = None):
        """Mark request as completed successfully"""
        self.status = "completed"
        self.completed_at = datetime.utcnow()
        self.response_data = response_data

        # Calculate actual completion time
        if self.started_at:
            delta = self.completed_at - self.started_at
            actual_seconds = int(delta.total_seconds())

    def fail_request(self, error_message: str):
        """Mark request as failed"""
        self.status = "failed"
        self.completed_at = datetime.utcnow()
        self.error_message = error_message

    def cancel_request(self):
        """Mark request as cancelled"""
        self.status = "cancelled"
        self.completed_at = datetime.utcnow()

    def can_retry(self) -> bool:
        """Check if request can be retried"""
        return (
            self.status == "failed" and
            self.retry_count < self.max_retries and
            not self.rate_limit_exceeded
        )

    def retry_request(self):
        """Retry the request"""
        self.retry_count += 1
        self.status = "retrying"
        self.error_message = None
        self.completed_at = None

    def is_urgent(self) -> bool:
        """Check if request is urgent or critical"""
        return self.priority in [RequestPriority.URGENT, RequestPriority.CRITICAL]

    def requires_immediate_attention(self) -> bool:
        """Check if request needs immediate processing"""
        urgent_status = self.is_urgent()
        high_priority_pending = (self.priority == RequestPriority.HIGH and
                               self.status == "pending")
        critical_error = (self.status == "failed" and
                         any(flag in self.compliance_flags for flag in ["security", "data_loss"]))

        return urgent_status or high_priority_pending or critical_error

    def get_processing_time_seconds(self) -> Optional[int]:
        """Get total processing time in seconds"""
        if self.started_at and self.completed_at:
            delta = self.completed_at - self.started_at
            return int(delta.total_seconds())
        elif self.started_at:
            # Still processing
            delta = datetime.utcnow() - self.started_at
            return int(delta.total_seconds())
        return None

    def should_be_rate_limited(self, user_request_history: List['UserRequest'],
                              rate_limit_window_seconds: int = 60,
                              max_requests_per_window: int = 10) -> bool:
        """Check if request should be rate limited based on user history"""

        # Check requests in the current window
        current_time = datetime.utcnow()
        window_start = current_time.timestamp() - rate_limit_window_seconds

        recent_requests = [
            req for req in user_request_history
            if req.created_at.timestamp() >= window_start and
               req.user_id == self.user_id and
               req.status != "cancelled"
        ]

        if len(recent_requests) >= max_requests_per_window:
            self.rate_limit_exceeded = True
            return True

        return False

    def get_discord_embed_data(self) -> Dict[str, Any]:
        """Get data formatted for Discord embed response"""
        embed_color = {
            "pending": 0xFFFF00,    # Yellow
            "processing": 0x00FF00, # Green
            "completed": 0x0000FF,  # Blue
            "failed": 0xFF0000,    # Red
            "cancelled": 0x808080   # Gray
        }.get(self.status, 0xFFFFFF)

        embed_data = {
            "title": ".1f",
            "description": self.content[:200] + "..." if len(self.content) > 200 else self.content,
            "color": embed_color,
            "fields": [
                {
                    "name": "Type",
                    "value": self.request_type.value.title(),
                    "inline": True
                },
                {
                    "name": "Priority",
                    "value": self.priority.value.title(),
                    "inline": True
                },
                {
                    "name": "Status",
                    "value": self.status.title(),
                    "inline": True
                }
            ]
        }

        # Add completion time if available
        if self.completed_at and self.started_at:
            processing_time = self.get_processing_time_seconds()
            if processing_time:
                embed_data["fields"].append({
                    "name": "Processing Time",
                    "value": ".1f",
                    "inline": True
                })

        # Add error message if failed
        if self.error_message and self.status == "failed":
            embed_data["fields"].append({
                "name": "Error",
                "value": self.error_message[:100] + "..." if len(self.error_message) > 100 else self.error_message
            })

        # Add workflow ID if available
        if self.workflow_id:
            embed_data["fields"].append({
                "name": "Workflow ID",
                "value": self.workflow_id,
                "inline": True
            })

        # Add timestamp
        created_timestamp = int(self.created_at.timestamp())
        embed_data["timestamp"] = created_timestamp

        return embed_data

    def apply_audit_lens(self, lens_name: str) -> Dict[str, Any]:
        """Apply governance audit lens to the request"""
        findings = []

        if lens_name == "safety-security":
            # Check for potentially sensitive content or parameters
            sensitive_indicators = ["password", "key", "token", "secret", "credential"]

            for param_name in self.parameters.keys():
                if any(indicator in param_name.lower() for indicator in sensitive_indicators):
                    findings.append(f"Sensitive parameter detected: {param_name}")

            if len(self.content) > 1000:
                findings.append("Unusually long request content - potential abuse")

        elif lens_name == "performance":
            # Check for performance implications
            if self.estimated_completion_seconds and self.estimated_completion_seconds > 300:
                findings.append("Long-running request - consider user feedback during execution")

            if self.priority == RequestPriority.CRITICAL and self.request_type == RequestType.SEARCH:
                findings.append("Critical priority on potentially slow request type")

        elif lens_name == "communication":
            # Check for clarity and completeness
            if len(self.content.strip()) < 3:
                findings.append("Very short request content - may lack detail")

            if len(self.parameters) > 10:
                findings.append("Large number of parameters - request may be too complex")

        self.audit_lens_applied.append(lens_name)

        return {
            "lens_name": lens_name,
            "findings": findings,
            "score": (1.0 - len(findings) * 0.1) if len(findings) <= 10 else 0.0
        }

    def to_dict(self) -> Dict[str, Any]:
        return {
            "request_id": self.request_id,
            "user_id": self.user_id,
            "request_type": self.request_type.value,
            "content": self.content,
            "parameters": self.parameters,
            "source": self.source.value,
            "channel_id": self.channel_id,
            "message_id": self.message_id,
            "guild_id": self.guild_id,
            "priority": self.priority.value,
            "status": self.status,
            "progress_percentage": self.progress_percentage,
            "created_at": self.created_at.isoformat(),
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "estimated_completion_seconds": self.estimated_completion_seconds,
            "response_data": self.response_data,
            "error_message": self.error_message,
            "workflow_id": self.workflow_id,
            "retry_count": self.retry_count,
            "max_retries": self.max_retries,
            "rate_limit_exceeded": self.rate_limit_exceeded,
            "audit_lens_applied": self.audit_lens_applied,
            "risk_assessment_score": self.risk_assessment_score,
            "compliance_flags": self.compliance_flags,
            "user_context": self.user_context,
            "session_id": self.session_id
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'UserRequest':
        """Create from dictionary"""
        # Handle enum conversion
        for enum_field, enum_class in [
            ('request_type', RequestType),
            ('source', RequestSource),
            ('priority', RequestPriority)
        ]:
            if enum_field in data:
                data[enum_field] = enum_class(data[enum_field])

        # Handle datetime parsing
        for datetime_field in ['created_at', 'started_at', 'completed_at']:
            if data.get(datetime_field):
                data[datetime_field] = datetime.fromisoformat(data[datetime_field])

        return cls(**data)

    def __repr__(self) -> str:
        return (f"UserRequest(id='{self.request_id[:8]}...', "
                f"type={self.request_type.value}, "
                f"priority={self.priority.value}, "
                f"status='{self.status}')")


@dataclass
class UserSession:
    """Represents a user session for maintaining context"""

    session_id: str
    user_id: str
    guild_id: Optional[str] = None

    # Session state
    active: bool = True
    created_at: datetime = field(default_factory=datetime.utcnow)
    last_activity: datetime = field(default_factory=datetime.utcnow)
    expires_at: Optional[datetime] = None

    # User preferences and context
    preferences: Dict[str, Any] = field(default_factory=dict)
    conversation_history: List[Dict[str, Any]] = field(default_factory=list)

    # Rate limiting
    request_count_last_minute: int = 0
    request_count_last_hour: int = 0
    last_request_timestamp: Optional[datetime] = None

    def __post_init__(self):
        """Initialize session"""
        if not self.session_id:
            self.session_id = str(uuid.uuid4())

    def record_request(self):
        """Record a new request for rate limiting"""
        current_time = datetime.utcnow()
        self.last_activity = current_time
        self.last_request_timestamp = current_time

        # Update request counts (simplified sliding window)
        self.request_count_last_minute += 1
        self.request_count_last_hour += 1

    def is_rate_limited(self, max_per_minute: int = 10, max_per_hour: int = 50) -> bool:
        """Check if session is rate limited"""
        return (
            self.request_count_last_minute >= max_per_minute or
            self.request_count_last_hour >= max_per_hour
        )

    def reset_rate_limits(self):
        """Reset rate limiting counters"""
        self.request_count_last_minute = 0
        self.request_count_last_hour = 0

    def add_to_history(self, interaction: Dict[str, Any]):
        """Add interaction to conversation history"""
        self.conversation_history.append({
            "timestamp": datetime.utcnow().isoformat(),
            **interaction
        })

        # Keep only last 50 interactions
        if len(self.conversation_history) > 50:
            self.conversation_history = self.conversation_history[-50:]

    def get_recent_history(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent conversation history"""
        return self.conversation_history[-limit:]

    def is_expired(self) -> bool:
        """Check if session has expired"""
        if not self.expires_at:
            return False
        return datetime.utcnow() > self.expires_at

    def to_dict(self) -> Dict[str, Any]:
        return {
            "session_id": self.session_id,
            "user_id": self.user_id,
            "guild_id": self.guild_id,
            "active": self.active,
            "created_at": self.created_at.isoformat(),
            "last_activity": self.last_activity.isoformat(),
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
            "preferences": self.preferences,
            "conversation_history": self.conversation_history,
            "request_count_last_minute": self.request_count_last_minute,
            "request_count_last_hour": self.request_count_last_hour,
            "last_request_timestamp": self.last_request_timestamp.isoformat() if self.last_request_timestamp else None
        }


class RequestRegistry:
    """Registry for managing user requests"""

    def __init__(self):
        self.requests: Dict[str, UserRequest] = {}
        self.active_requests: Dict[str, List[str]] = {}  # user_id -> [request_ids]
        self.user_sessions: Dict[str, UserSession] = {}

    def register_request(self, request: UserRequest):
        """Register a new request"""
        self.requests[request.request_id] = request

        # Add to active requests for this user
        if request.user_id not in self.active_requests:
            self.active_requests[request.user_id] = []
        self.active_requests[request.user_id].append(request.request_id)

    def get_request(self, request_id: str) -> Optional[UserRequest]:
        """Get request by ID"""
        return self.requests.get(request_id)

    def get_user_requests(self, user_id: str) -> List[UserRequest]:
        """Get all requests for a user"""
        request_ids = self.active_requests.get(user_id, [])
        return [self.requests[rid] for rid in request_ids if rid in self.requests]

    def get_pending_requests(self) -> List[UserRequest]:
        """Get all pending requests"""
        return [req for req in self.requests.values() if req.status == "pending"]

    def get_urgent_requests(self) -> List[UserRequest]:
        """Get all urgent/critical requests"""
        return [req for req in self.requests.values() if req.is_urgent()]

    def get_user_session(self, user_id: str, guild_id: Optional[str] = None) -> UserSession:
        """Get or create user session"""
        session_key = f"{user_id}:{guild_id}" if guild_id else user_id

        if session_key not in self.user_sessions:
            session = UserSession(
                session_id="",  # Will be auto-generated
                user_id=user_id,
                guild_id=guild_id,
                preferences=self._get_default_preferences(user_id)
            )
            self.user_sessions[session_key] = session

        return self.user_sessions[session_key]

    def _get_default_preferences(self, user_id: str) -> Dict[str, Any]:
        """Get default user preferences"""
        # This could load from database or provide sensible defaults
        return {
            "max_daily_requests": 100,
            "preferred_format": "audiobook",
            "notification_level": "important_only",
            "language": "en",
            "timezone": "UTC"
        }

    def update_request_status(self, request_id: str, new_status: str):
        """Update request status"""
        request = self.requests.get(request_id)
        if request:
            request.status = new_status
            if new_status in ["completed", "failed", "cancelled"]:
                request.completed_at = datetime.utcnow()

    def cleanup_completed_requests(self, older_than_hours: int = 24):
        """Clean up old completed requests"""
        cutoff_time = datetime.utcnow().timestamp() - (older_than_hours * 3600)

        to_remove = []
        for request_id, request in self.requests.items():
            if (request.status in ["completed", "failed", "cancelled"] and
                request.completed_at and
                request.completed_at.timestamp() < cutoff_time):
                to_remove.append(request_id)

        for request_id in to_remove:
            del self.requests[request_id]

            # Remove from active requests
            for user_requests in self.active_requests.values():
                if request_id in user_requests:
                    user_requests.remove(request_id)

    def get_system_status(self) -> Dict[str, Any]:
        """Get overall request system status"""
        total_requests = len(self.requests)
        status_counts = {}
        total_users = len(self.active_requests)

        # Count requests by status
        for request in self.requests.values():
            status = request.status
            status_counts[status] = status_counts.get(status, 0) + 1

        # Get urgent requests count
        urgent_count = len(self.get_urgent_requests())
        pending_count = len(self.get_pending_requests())

        return {
            "total_requests": total_requests,
            "total_users": total_users,
            "status_distribution": status_counts,
            "urgent_requests": urgent_count,
            "pending_requests": pending_count,
            "active_sessions": len(self.user_sessions),
            "timestamp": datetime.utcnow().isoformat()
        }
