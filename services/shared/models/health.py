"""
Health Check Result Model
Detailed health monitoring and status reporting for BookFairy services
Based on data-model.md specification and integration tests
"""
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from datetime import datetime
from enum import Enum


class HealthStatus(Enum):
    """Health status levels"""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    CRITICAL = "critical"
    UNKNOWN = "unknown"


class HealthCheckType(Enum):
    """Types of health checks"""
    HTTP_API = "http_api"           # REST API endpoint
    DATABASE = "database"          # Database connectivity
    CACHE = "cache"               # Cache service
    CONTAINER = "container"       # Docker container
    SYSTEM = "system"            # System resources
    DEPENDENCY = "dependency"     # Other service dependencies


@dataclass
class HealthCheckResult:
    """Result of a single health check"""

    check_id: str
    service_name: str
    check_type: HealthCheckType

    # Status and timing
    status: HealthStatus = HealthStatus.UNKNOWN
    response_time_ms: Optional[int] = None
    checked_at: datetime = field(default_factory=datetime.utcnow)

    # Details
    details: Dict[str, Any] = field(default_factory=dict)
    error_message: Optional[str] = None

    # Metadata
    check_name: str = ""
    endpoint: Optional[str] = None
    timeout_seconds: int = 30

    # Performance tracking
    consecutive_failures: int = 0
    last_failure_at: Optional[datetime] = None
    last_success_at: Optional[datetime] = None

    # Metrics
    metrics: Dict[str, Any] = field(default_factory=dict)  # CPU, memory, etc.

    def __post_init__(self):
        """Initialize health check result"""
        if not self.check_name:
            self.check_name = f"{self.service_name}_{self.check_type.value}_check"

    def record_success(self, response_time_ms: int, details: Optional[Dict[str, Any]] = None):
        """Record successful health check"""
        self.status = HealthStatus.HEALTHY
        self.response_time_ms = response_time_ms
        self.checked_at = datetime.utcnow()
        self.last_success_at = datetime.utcnow()
        self.consecutive_failures = 0
        self.error_message = None

        if details:
            self.details.update(details)

    def record_failure(self, error_message: str, details: Optional[Dict[str, Any]] = None):
        """Record failed health check"""
        self.status = HealthStatus.UNHEALTHY
        self.checked_at = datetime.utcnow()
        self.consecutive_failures += 1
        self.last_failure_at = datetime.utcnow()
        self.error_message = error_message

        if details:
            self.details.update(details)

    def is_critical_failure(self) -> bool:
        """Check if this represents a critical failure"""
        return (
            self.consecutive_failures >= 3 and
            self.status in [HealthStatus.CRITICAL, HealthStatus.UNHEALTHY]
        )

    def get_health_score(self) -> float:
        """Calculate health score (0.0 = worst, 1.0 = best)"""
        if self.status == HealthStatus.HEALTHY:
            base_score = 1.0
        elif self.status == HealthStatus.DEGRADED:
            base_score = 0.7
        elif self.status == HealthStatus.UNHEALTHY:
            base_score = 0.3
        elif self.status == HealthStatus.CRITICAL:
            base_score = 0.1
        else:
            base_score = 0.0

        # Penalties
        if self.consecutive_failures > 0:
            penalty = min(self.consecutive_failures * 0.1, 0.5)
            base_score -= penalty

        # Response time penalty
        if self.response_time_ms and self.response_time_ms > 5000:  # 5 seconds
            base_score -= 0.2

        return max(0.0, min(1.0, base_score))

    def to_dict(self) -> Dict[str, Any]:
        return {
            "check_id": self.check_id,
            "service_name": self.service_name,
            "check_type": self.check_type.value,
            "status": self.status.value,
            "response_time_ms": self.response_time_ms,
            "checked_at": self.checked_at.isoformat(),
            "details": self.details,
            "error_message": self.error_message,
            "check_name": self.check_name,
            "endpoint": self.endpoint,
            "timeout_seconds": self.timeout_seconds,
            "consecutive_failures": self.consecutive_failures,
            "last_failure_at": self.last_failure_at.isoformat() if self.last_failure_at else None,
            "last_success_at": self.last_success_at.isoformat() if self.last_success_at else None,
            "metrics": self.metrics,
            "health_score": self.get_health_score()
        }


@dataclass
class ServiceHealthSummary:
    """Comprehensive health summary for a service"""

    service_name: str
    overall_status: HealthStatus = HealthStatus.UNKNOWN

    # Health check results
    health_checks: List[HealthCheckResult] = field(default_factory=list)

    # Dependencies health
    dependency_status: Dict[str, HealthStatus] = field(default_factory=dict)

    # System resources
    system_metrics: Dict[str, Any] = field(default_factory=dict)

    # Summary stats
    last_updated: datetime = field(default_factory=datetime.utcnow)
    total_checks: int = 0
    healthy_checks: int = 0
    unhealthy_checks: int = 0

    def update_from_checks(self):
        """Update summary based on health check results"""
        self.last_updated = datetime.utcnow()

        if not self.health_checks:
            self.overall_status = HealthStatus.UNKNOWN
            return

        self.total_checks = len(self.health_checks)
        self.healthy_checks = sum(1 for check in self.health_checks
                                if check.status == HealthStatus.HEALTHY)
        self.unhealthy_checks = self.total_checks - self.healthy_checks

        # Determine overall status
        if self.healthy_checks == self.total_checks:
            self.overall_status = HealthStatus.HEALTHY
        elif self.healthy_checks >= self.total_checks * 0.8:  # 80% healthy
            self.overall_status = HealthStatus.DEGRADED
        elif self.healthy_checks > 0:
            self.overall_status = HealthStatus.UNHEALTHY
        else:
            self.overall_status = HealthStatus.CRITICAL

    def get_overall_health_score(self) -> float:
        """Calculate overall health score"""
        if not self.health_checks:
            return 0.0

        individual_scores = [check.get_health_score() for check in self.health_checks]
        return sum(individual_scores) / len(individual_scores)

    def get_critical_failures(self) -> List[HealthCheckResult]:
        """Get critical health check failures"""
        return [check for check in self.health_checks if check.is_critical_failure()]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "service_name": self.service_name,
            "overall_status": self.overall_status.value,
            "health_checks": [check.to_dict() for check in self.health_checks],
            "dependency_status": {k: v.value for k, v in self.dependency_status.items()},
            "system_metrics": self.system_metrics,
            "last_updated": self.last_updated.isoformat(),
            "total_checks": self.total_checks,
            "healthy_checks": self.healthy_checks,
            "unhealthy_checks": self.unhealthy_checks,
            "overall_health_score": self.get_overall_health_score()
        }


class HealthMonitorRegistry:
    """Registry for monitoring service health"""

    def __init__(self):
        self.service_health: Dict[str, ServiceHealthSummary] = {}
        self.health_history: Dict[str, List[HealthCheckResult]] = {}
        self.alerts: List[Dict[str, Any]] = []

    def register_service(self, service_name: str):
        """Register a service for health monitoring"""
        if service_name not in self.service_health:
            self.service_health[service_name] = ServiceHealthSummary(service_name=service_name)
            self.health_history[service_name] = []

    def record_health_check(self, result: HealthCheckResult):
        """Record a health check result"""
        service_name = result.service_name

        # Ensure service is registered
        self.register_service(service_name)

        # Add to history
        if service_name not in self.health_history:
            self.health_history[service_name] = []
        self.health_history[service_name].append(result)

        # Keep only last 100 results
        if len(self.health_history[service_name]) > 100:
            self.health_history[service_name] = self.health_history[service_name][-100:]

        # Update service summary
        summary = self.service_health[service_name]
        summary.health_checks.append(result)
        summary.update_from_checks()

        # Check for alerts
        self._check_for_alerts(result)

    def _check_for_alerts(self, result: HealthCheckResult):
        """Check for conditions that require alerts"""
        if result.is_critical_failure():
            self.alerts.append({
                "alert_id": f"crt-{result.check_id}-{int(datetime.utcnow().timestamp())}",
                "service_name": result.service_name,
                "alert_type": "critical_failure",
                "message": f"Critical health check failure for {result.service_name}: {result.check_name}",
                "timestamp": datetime.utcnow().isoformat(),
                "details": {
                    "check_id": result.check_id,
                    "check_name": result.check_name,
                    "consecutive_failures": result.consecutive_failures,
                    "error_message": result.error_message
                }
            })

    def get_service_health(self, service_name: str) -> Optional[ServiceHealthSummary]:
        """Get health summary for a service"""
        return self.service_health.get(service_name)

    def get_system_health_overview(self) -> Dict[str, Any]:
        """Get overall system health overview"""
        total_services = len(self.service_health)
        healthy_services = sum(1 for summary in self.service_health.values()
                             if summary.overall_status == HealthStatus.HEALTHY)

        # Calculate average health score
        health_scores = [summary.get_overall_health_score() for summary in self.service_health.values()]
        avg_health_score = sum(health_scores) / len(health_scores) if health_scores else 0.0

        return {
            "total_services": total_services,
            "healthy_services": healthy_services,
            "unhealthy_services": total_services - healthy_services,
            "average_health_score": avg_health_score,
            "services": {name: summary.to_dict() for name, summary in self.service_health.items()},
            "active_alerts": len(self.alerts),
            "timestamp": datetime.utcnow().isoformat()
        }

    def get_recent_health_history(self, service_name: str, limit: int = 10) -> List[HealthCheckResult]:
        """Get recent health check history for a service"""
        history = self.health_history.get(service_name, [])
        return history[-limit:]

    def get_active_alerts(self) -> List[Dict[str, Any]]:
        """Get active health alerts"""
        return self.alerts
