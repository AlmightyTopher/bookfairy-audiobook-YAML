"""
Docker Container Model
Represents each containerized service with configuration and runtime state
Based on data-model.md specification and quickstart.md integration tests
"""
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from datetime import datetime
import json


@dataclass
class DockerContainer:
    """Core model representing a Docker container service"""

    # Core identification
    container_id: str
    service_name: str
    image_name: str

    # Runtime state
    status: str = "created"  # created, running, paused, stopped, exited, dead
    health_status: str = "unknown"  # healthy, unhealthy, starting, none, unknown
    restart_count: int = 0

    # Configuration
    ports: Dict[str, str] = field(default_factory=dict)  # host_port: container_port
    environment_variables: Dict[str, str] = field(default_factory=dict)
    volumes: List[str] = field(default_factory=list)
    networks: List[str] = field(default_factory=list)

    # Resource limits
    memory_limit: Optional[str] = None  # e.g., "512m", "1g"
    cpu_limit: Optional[float] = None   # CPU cores
    memory_usage: Optional[int] = None  # bytes
    cpu_usage_percent: Optional[float] = None

    # Health and monitoring
    health_check_url: Optional[str] = None
    health_check_interval: int = 30  # seconds
    health_check_timeout: int = 10   # seconds
    last_health_check: Optional[datetime] = None
    consecutive_failures: int = 0

    # Docker-specific metadata
    container_name: Optional[str] = None
    labels: Dict[str, str] = field(default_factory=dict)
    docker_network_mode: str = "bridge"
    restart_policy: str = "unless-stopped"

    # Governance and audit
    created_at: datetime = field(default_factory=datetime.utcnow)
    last_updated: datetime = field(default_factory=datetime.utcnow)
    audit_lens_applied: List[str] = field(default_factory=list)

    # Dependencies and relationships
    depends_on: List[str] = field(default_factory=list)  # Other service names
    required_by: List[str] = field(default_factory=list)  # Services that depend on this

    # Custom metadata for BookFairy services
    service_type: str = ""  # discord-bot, lazylibrarian, audiobookshelf, etc.
    version: Optional[str] = None
    official_image: bool = True  # Whether using official Docker image

    def __post_init__(self):
        """Validate container configuration after initialization"""
        if not self.container_name:
            self.container_name = f"bookfairy-{self.service_name}"

        # Auto-set service_type for known services
        if not self.service_type and self.service_name in [
            'discord-bot', 'lazylibrarian', 'prowlarr', 'qbittorrent',
            'audiobookshelf', 'lm-studio', 'redis'
        ]:
            self.service_type = self.service_name

    def update_status(self, new_status: str, health_status: Optional[str] = None):
        """Update container status and timestamp"""
        self.status = new_status
        if health_status:
            self.health_status = health_status
        self.last_updated = datetime.utcnow()

        # Reset consecutive failures on successful health check
        if health_status == "healthy":
            self.consecutive_failures = 0

    def record_health_failure(self):
        """Record a health check failure"""
        self.consecutive_failures += 1
        self.last_health_check = datetime.utcnow()

    def record_health_success(self):
        """Record a health check success"""
        self.consecutive_failures = 0
        self.last_health_check = datetime.utcnow()

    def is_healthy(self) -> bool:
        """Check if container is in healthy state"""
        return (
            self.status == "running" and
            self.health_status in ["healthy", "none"] and  # none = no health check configured
            self.consecutive_failures == 0
        )

    def get_health_score(self) -> float:
        """Return health score between 0.0 (dead) and 1.0 (perfect health)"""
        if self.status not in ["running", "healthy"]:
            return 0.0

        # Base health score
        base_score = 0.5  # Running but not perfectly healthy

        # Bonus for healthy status
        if self.health_status == "healthy":
            base_score += 0.4

        # Penalty for consecutive failures
        if self.consecutive_failures > 0:
            base_score -= min(self.consecutive_failures * 0.1, 0.4)

        # Penalty for resource usage near limits
        if self.memory_usage and self.memory_limit:
            # Parse memory limit (simplified)
            if isinstance(self.memory_limit, str):
                # Handle "512m", "1g" format
                if self.memory_limit.endswith('m'):
                    limit_mb = int(self.memory_limit[:-1])
                elif self.memory_limit.endswith('g'):
                    limit_mb = int(self.memory_limit[:-1]) * 1024
                else:
                    limit_mb = int(self.memory_limit)

                usage_mb = self.memory_usage / (1024 * 1024)
                if usage_mb > limit_mb * 0.8:  # Over 80% usage
                    base_score -= 0.2

        return max(0.0, min(1.0, base_score))

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            "container_id": self.container_id,
            "service_name": self.service_name,
            "image_name": self.image_name,
            "status": self.status,
            "health_status": self.health_status,
            "restart_count": self.restart_count,
            "ports": self.ports,
            "environment_variables": {k: "***" for k in self.environment_variables.keys()},  # Mask values
            "volumes": self.volumes,
            "networks": self.networks,
            "memory_limit": self.memory_limit,
            "cpu_limit": self.cpu_limit,
            "memory_usage": self.memory_usage,
            "cpu_usage_percent": self.cpu_usage_percent,
            "health_check_url": self.health_check_url,
            "health_check_interval": self.health_check_interval,
            "health_check_timeout": self.health_check_timeout,
            "last_health_check": self.last_health_check.isoformat() if self.last_health_check else None,
            "consecutive_failures": self.consecutive_failures,
            "container_name": self.container_name,
            "labels": self.labels,
            "docker_network_mode": self.docker_network_mode,
            "restart_policy": self.restart_policy,
            "created_at": self.created_at.isoformat(),
            "last_updated": self.last_updated.isoformat(),
            "audit_lens_applied": self.audit_lens_applied,
            "depends_on": self.depends_on,
            "required_by": self.required_by,
            "service_type": self.service_type,
            "version": self.version,
            "official_image": self.official_image,
            "health_score": self.get_health_score()
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'DockerContainer':
        """Create instance from dictionary"""
        # Handle datetime parsing
        for datetime_field in ['created_at', 'last_updated', 'last_health_check']:
            if data.get(datetime_field):
                data[datetime_field] = datetime.fromisoformat(data[datetime_field])

        return cls(**{k: v for k, v in data.items()
                     if k in cls.__dataclass_fields__ and k not in ['health_score']})

    def __repr__(self) -> str:
        return (f"DockerContainer(service_name='{self.service_name}', "
                f"status='{self.status}', health='{self.health_status}', "
                f"health_score={self.get_health_score():.2f})")


@dataclass
class ContainerHealthHistory:
    """Historical health data for a container"""

    container_id: str
    timestamp: datetime = field(default_factory=datetime.utcnow)
    status: str = ""
    health_status: str = ""
    memory_usage: Optional[int] = None
    cpu_usage_percent: Optional[float] = None
    response_time_ms: Optional[int] = None
    error_message: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "container_id": self.container_id,
            "timestamp": self.timestamp.isoformat(),
            "status": self.status,
            "health_status": self.health_status,
            "memory_usage": self.memory_usage,
            "cpu_usage_percent": self.cpu_usage_percent,
            "response_time_ms": self.response_time_ms,
            "error_message": self.error_message
        }


class DockerContainerRegistry:
    """Registry for managing multiple containers"""

    def __init__(self):
        self.containers: Dict[str, DockerContainer] = {}
        self.health_history: List[ContainerHealthHistory] = []

    def register_container(self, container: DockerContainer):
        """Register a new container"""
        self.containers[container.container_id] = container

    def unregister_container(self, container_id: str):
        """Unregister a container"""
        if container_id in self.containers:
            del self.containers[container_id]

    def get_container(self, container_id: str) -> Optional[DockerContainer]:
        """Get container by ID"""
        return self.containers.get(container_id)

    def get_containers_by_service(self, service_name: str) -> List[DockerContainer]:
        """Get all containers for a service"""
        return [c for c in self.containers.values() if c.service_name == service_name]

    def get_healthy_containers(self) -> List[DockerContainer]:
        """Get all healthy containers"""
        return [c for c in self.containers.values() if c.is_healthy()]

    def get_unhealthy_containers(self) -> List[DockerContainer]:
        """Get all unhealthy containers"""
        return [c for c in self.containers.values() if not c.is_healthy()]

    def record_health_check(self, container_id: str, health_data: Dict[str, Any]):
        """Record health check result"""
        history_entry = ContainerHealthHistory(
            container_id=container_id,
            **{k: v for k, v in health_data.items()
               if k in ContainerHealthHistory.__dataclass_fields__}
        )
        self.health_history.append(history_entry)

        # Update container status if provided
        container = self.containers.get(container_id)
        if container:
            if 'status' in health_data:
                container.update_status(health_data['status'],
                                       health_data.get('health_status'))

            if health_data.get('health_status') == 'healthy':
                container.record_health_success()
            elif health_data.get('health_status') in ['unhealthy', 'failed']:
                container.record_health_failure()

    def get_health_summary(self) -> Dict[str, Any]:
        """Get overall health summary"""
        total_containers = len(self.containers)
        healthy_containers = len(self.get_healthy_containers())

        return {
            "total_containers": total_containers,
            "healthy_containers": healthy_containers,
            "unhealthy_containers": total_containers - healthy_containers,
            "overall_health_percentage": (healthy_containers / total_containers * 100) if total_containers > 0 else 0,
            "containers": {cid: c.to_dict() for cid, c in self.containers.items()}
        }

    def apply_audit_lens(self, lens_name: str, lens_criteria: Dict[str, Any]) -> Dict[str, Any]:
        """Apply an audit lens to evaluate containers"""
        findings = []
        score = 0.0
        total_criteria = len(lens_criteria)

        for container in self.containers.values():
            container_findings = []

            # Container-specific audit lens application based on lens_name
            if lens_name == "safety-security":
                # Security audit lens
                if not container.ports:
                    container_findings.append("No ports configured - potential security issue")
                if any('password' in env.lower() or 'key' in env.lower()
                      for env in container.environment_variables.keys()):
                    container_findings.append("Potentially sensitive environment variables detected")
                if not container.labels.get('bookfairy.managed'):
                    container_findings.append("Not managed by BookFairy - governance gap")

            elif lens_name == "performance":
                # Performance audit lens
                if not container.memory_limit:
                    container_findings.append("No memory limit configured")
                if container.cpu_usage_percent and container.cpu_usage_percent > 80:
                    container_findings.append(".1f")
                if container.last_health_check and \
                   (datetime.utcnow() - container.last_health_check).seconds > 60:
                    container_findings.append("Health check outdated")

            elif lens_name == "reliability":
                # Reliability audit lens
                if container.restart_policy != "unless-stopped":
                    container_findings.append("Suboptimal restart policy")
                if container.consecutive_failures > 3:
                    container_findings.append(f"High consecutive failures: {container.consecutive_failures}")
                if container.status not in ["running", "healthy"]:
                    container_findings.append(f"Non-optimal status: {container.status}")

            elif lens_name == "observability":
                # Observability audit lens
                if not container.health_check_url:
                    container_findings.append("No health check URL configured")
                if not container.labels:
                    container_findings.append("No labels for monitoring and discovery")
                if container.last_health_check is None:
                    container_findings.append("No health check history")

            # Update score if no findings
            if not container_findings:
                score += 1.0 / total_criteria
            else:
                score += 0.5 / total_criteria  # Partial score for issues found

            container.audit_lens_applied.append(lens_name)

            findings.append({
                "container_id": container.container_id,
                "service_name": container.service_name,
                "findings": container_findings,
                "score": (1.0 - len(container_findings) * 0.2) if len(container_findings) <= 5 else 0.0
            })

        return {
            "lens_name": lens_name,
            "evaluation_score": min(1.0, score),
            "findings": findings,
            "recommendations": [
                "Address high-priority findings from audit lens evaluation",
                "Implement automated remediation for common issues",
                "Set up monitoring alerts based on audit findings"
            ]
        }
