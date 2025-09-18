"""
Service Map Model
Manages relationships and connections between services
Based on data-model.md specification and quickstart.md integration tests
"""
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set, Tuple, Any
from datetime import datetime
import json
from enum import Enum


class ConnectionType(Enum):
    """Types of service connections"""
    HTTP_API = "http_api"           # REST API calls
    DATABASE = "database"          # Database connections
    CACHE = "cache"               # Redis/cache connections
    MESSAGE_QUEUE = "message_queue" # Message queue communications
    FILE_SHARE = "file_share"      # Shared file systems
    NETWORK = "network"           # Direct network connections


@dataclass
class ServiceConnection:
    """Represents a connection between two services"""

    source_service: str
    target_service: str
    connection_type: ConnectionType
    connection_details: Dict[str, Any] = field(default_factory=dict)

    # Connection properties
    required: bool = True  # Whether this connection is mandatory
    bidirectional: bool = False  # If connection works both ways
    priority: int = 1  # Connection priority (1=high, 3=low)

    # Runtime state
    status: str = "unknown"  # connected, disconnected, failed, degraded
    last_tested: Optional[datetime] = None
    latency_ms: Optional[int] = None
    error_message: Optional[str] = None

    # Governance
    audit_lens_applied: List[str] = field(default_factory=list)

    def __post_init__(self):
        """Validate connection after initialization"""
        if self.source_service == self.target_service:
            raise ValueError("Source and target services cannot be the same")

    def test_connection(self) -> Dict[str, Any]:
        """Test the connection between services"""
        # This would be implemented with actual connection testing logic
        # For now, return mock results that will be updated by actual tests
        self.last_tested = datetime.utcnow()

        return {
            "source_service": self.source_service,
            "target_service": self.target_service,
            "connection_type": self.connection_type.value,
            "status": self.status,
            "latency_ms": self.latency_ms,
            "last_tested": self.last_tested.isoformat(),
            "error_message": self.error_message
        }

    def update_status(self, new_status: str, latency: Optional[int] = None,
                     error: Optional[str] = None):
        """Update connection status"""
        self.status = new_status
        self.latency_ms = latency
        self.error_message = error
        self.last_tested = datetime.utcnow()

    def is_healthy(self) -> bool:
        """Check if connection is healthy"""
        return self.status in ["connected", "healthy"]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "source_service": self.source_service,
            "target_service": self.target_service,
            "connection_type": self.connection_type.value,
            "connection_details": self.connection_details,
            "required": self.required,
            "bidirectional": self.bidirectional,
            "priority": self.priority,
            "status": self.status,
            "last_tested": self.last_tested.isoformat() if self.last_tested else None,
            "latency_ms": self.latency_ms,
            "error_message": self.error_message,
            "audit_lens_applied": self.audit_lens_applied
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ServiceConnection':
        """Create from dictionary"""
        # Convert string to enum
        if isinstance(data.get('connection_type'), str):
            data['connection_type'] = ConnectionType(data['connection_type'])

        # Parse datetime
        if data.get('last_tested'):
            data['last_tested'] = datetime.fromisoformat(data['last_tested'])

        return cls(**data)


@dataclass
class BookFairyService:
    """Represents a service in the BookFairy architecture"""

    service_name: str
    service_type: str  # discord-bot, lazylibrarian, etc.
    display_name: str
    description: str

    # Service attributes
    official_image: bool = True
    version: Optional[str] = None
    category: str = ""  # acquisition, organization, ai, storage, etc.

    # Endpoints and configuration
    api_port: Optional[int] = None
    web_ui_port: Optional[int] = None
    health_endpoint: Optional[str] = None

    # Dependencies
    dependencies: List[str] = field(default_factory=list)  # Services this depends on
    dependents: List[str] = field(default_factory=list)    # Services that depend on this

    # Resource requirements (estimates for planning)
    estimated_memory_mb: int = 512
    estimated_cpu_cores: float = 0.5

    # Runtime state
    container_id: Optional[str] = None
    status: str = "stopped"  # running, stopped, failed, degraded
    health_score: float = 0.0

    # Governance
    created_at: datetime = field(default_factory=datetime.utcnow)
    audit_lens_applied: List[str] = field(default_factory=list)

    # Custom service-specific configuration
    service_config: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        """Set defaults based on service type"""
        # Auto-set category based on service type
        if not self.category:
            category_map = {
                'discord-bot': 'orchestration',
                'lazylibrarian': 'acquisition',
                'prowlarr': 'indexing',
                'qbittorrent': 'download',
                'audiobookshelf': 'organization',
                'lm-studio': 'ai',
                'redis': 'storage'
            }
            self.category = category_map.get(self.service_type, 'utility')

        # Auto-set health endpoints for known services
        if not self.health_endpoint:
            endpoint_map = {
                'discord-bot': '/health',
                'lazylibrarian': '/health',
                'prowlarr': '/health',
                'qbittorrent': '/api/v2/app/version',
                'audiobookshelf': '/healthcheck',
                'redis': '/health'
            }
            self.health_endpoint = endpoint_map.get(self.service_type)

        # Auto-set resource estimates
        resource_map = {
            'discord-bot': (1024, 1.0),     # 1GB RAM, 1 cpu
            'lazylibrarian': (512, 0.5),    # 512MB RAM, 0.5 cpu
            'prowlarr': (512, 0.5),
            'qbittorrent': (1024, 1.0),     # For download processing
            'audiobookshelf': (512, 0.5),
            'lm-studio': (4096, 2.0),       # GPU ML workloads
            'redis': (1024, 0.5)
        }
        if (self.service_type in resource_map and
            self.estimated_memory_mb == 512 and self.estimated_cpu_cores == 0.5):
            self.estimated_memory_mb, self.estimated_cpu_cores = resource_map[self.service_type]

    def get_health_url(self) -> Optional[str]:
        """Get the full health check URL"""
        if self.api_port and self.health_endpoint:
            return f"http://localhost:{self.api_port}{self.health_endpoint}"
        return None

    def get_connections(self) -> List[ServiceConnection]:
        """Get all connections for this service (to be filled by ServiceMap)"""
        # This will be overridden by ServiceMap
        return []

    def is_core_service(self) -> bool:
        """Check if this is a core BookFairy service"""
        return self.service_type in ['discord-bot', 'lazylibrarian', 'audiobookshelf']

    def is_infrastructure_service(self) -> bool:
        """Check if this is infrastructure utility service"""
        return self.service_type in ['redis', 'prowlarr']

    def requires_gpu(self) -> bool:
        """Check if service requires GPU"""
        return self.service_type in ['lm-studio']

    def to_dict(self) -> Dict[str, Any]:
        return {
            "service_name": self.service_name,
            "service_type": self.service_type,
            "display_name": self.display_name,
            "description": self.description,
            "official_image": self.official_image,
            "version": self.version,
            "category": self.category,
            "api_port": self.api_port,
            "web_ui_port": self.web_ui_port,
            "health_endpoint": self.health_endpoint,
            "dependencies": self.dependencies,
            "dependents": self.dependents,
            "estimated_memory_mb": self.estimated_memory_mb,
            "estimated_cpu_cores": self.estimated_cpu_cores,
            "container_id": self.container_id,
            "status": self.status,
            "health_score": self.health_score,
            "created_at": self.created_at.isoformat(),
            "audit_lens_applied": self.audit_lens_applied,
            "service_config": self.service_config
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'BookFairyService':
        """Create from dictionary"""
        if data.get('created_at'):
            data['created_at'] = datetime.fromisoformat(data['created_at'])

        return cls(**data)


class ServiceMap:
    """Manages the complete service map and relationships"""

    def __init__(self):
        self.services: Dict[str, BookFairyService] = {}
        self.connections: List[ServiceConnection] = []
        self.last_updated: datetime = datetime.utcnow()

    # Service Management
    def add_service(self, service: BookFairyService):
        """Add a service to the map"""
        self.services[service.service_name] = service
        self._update_dependencies(service.service_name)
        self.last_updated = datetime.utcnow()

    def remove_service(self, service_name: str):
        """Remove a service from the map"""
        if service_name in self.services:
            # Remove connections involving this service
            self.connections = [
                conn for conn in self.connections
                if conn.source_service != service_name and conn.target_service != service_name
            ]

            # Update dependents lists
            for service in self.services.values():
                if service_name in service.dependents:
                    service.dependents.remove(service_name)

            del self.services[service_name]
            self.last_updated = datetime.utcnow()

    def get_service(self, service_name: str) -> Optional[BookFairyService]:
        """Get service by name"""
        return self.services.get(service_name)

    # Connection Management
    def add_connection(self, connection: ServiceConnection):
        """Add a connection between services"""
        # Validate services exist
        if (connection.source_service not in self.services or
            connection.target_service not in self.services):
            raise ValueError("Source or target service not found in service map")

        self.connections.append(connection)
        self._update_dependencies(connection.source_service)
        self.last_updated = datetime.utcnow()

    def get_connections_for_service(self, service_name: str) -> List[ServiceConnection]:
        """Get all connections for a specific service"""
        return [
            conn for conn in self.connections
            if conn.source_service == service_name or conn.target_service == service_name
        ]

    def get_required_connections(self) -> List[ServiceConnection]:
        """Get all required connections"""
        return [conn for conn in self.connections if conn.required]

    def test_all_connections(self) -> Dict[str, Any]:
        """Test all connections and return status"""
        results = []
        healthy_count = 0
        total_count = len(self.connections)

        for connection in self.connections:
            test_result = connection.test_connection()
            results.append(test_result)

            if connection.is_healthy():
                healthy_count += 1

        return {
            "total_connections": total_count,
            "healthy_connections": healthy_count,
            "failed_connections": total_count - healthy_count,
            "health_percentage": (healthy_count / total_count * 100) if total_count > 0 else 0,
            "connection_results": results,
            "timestamp": datetime.utcnow().isoformat()
        }

    # Dependency Analysis
    def _update_dependencies(self, service_name: str):
        """Update dependency relationships"""
        service = self.services.get(service_name)
        if not service:
            return

        # Find all outgoing connections (dependencies)
        outgoing_connections = [
            conn for conn in self.connections
            if conn.source_service == service_name
        ]

        service.dependencies = list(set(
            conn.target_service for conn in outgoing_connections
        ))

        # Find all incoming connections (dependents)
        incoming_connections = [
            conn for conn in self.connections
            if conn.target_service == service_name
        ]

        service.dependents = list(set(
            conn.source_service for conn in incoming_connections
        ))

    def get_dependency_chain(self, service_name: str) -> List[List[str]]:
        """Get dependency chains starting from a service"""
        chains = []
        visited = set()

        def dfs(current_chain: List[str]):
            current_service = current_chain[-1]

            if current_service in visited:
                return  # Avoid cycles

            visited.add(current_service)

            service = self.services.get(current_service)
            if not service:
                return

            # If this service has no dependencies, it's a complete chain
            if not service.dependencies:
                chains.append(current_chain.copy())
                visited.remove(current_service)
                return

            # Continue the chain with dependencies
            for dependency in service.dependencies:
                if dependency not in current_chain:  # Avoid cycles
                    dfs(current_chain + [dependency])

            visited.remove(current_service)

        dfs([service_name])
        return chains

    def get_startup_order(self) -> List[str]:
        """Calculate optimal service startup order"""
        # Simple topological sort based on dependencies
        startup_order = []
        visited = set()
        visiting = set()

        def visit(service_name: str):
            if service_name in visiting:
                raise ValueError(f"Circular dependency detected involving {service_name}")
            if service_name in visited:
                return

            visiting.add(service_name)

            service = self.services.get(service_name)
            if service:
                # Visit dependencies first
                for dependency in service.dependencies:
                    visit(dependency)

            visiting.remove(service_name)
            visited.add(service_name)
            startup_order.append(service_name)

        # Visit all services
        for service_name in self.services.keys():
            if service_name not in visited:
                visit(service_name)

        return startup_order

    # Status and Health
    def get_overall_health(self) -> Dict[str, Any]:
        """Get overall health status of the service map"""
        total_services = len(self.services)
        healthy_services = sum(1 for s in self.services.values() if s.status == "running")
        total_connections = len(self.connections)
        healthy_connections = sum(1 for c in self.connections if c.is_healthy())

        # Calculate service health categories
        service_status_count = {}
        for service in self.services.values():
            status = service.status
            service_status_count[status] = service_status_count.get(status, 0) + 1

        return {
            "timestamp": datetime.utcnow().isoformat(),
            "services": {
                "total": total_services,
                "healthy": healthy_services,
                "by_status": service_status_count
            },
            "connections": {
                "total": total_connections,
                "healthy": healthy_connections if total_connections > 0 else 0
            },
            "overall_health_score": (
                (healthy_services + healthy_connections) /
                (total_services + total_connections) * 100
            ) if (total_services + total_connections) > 0 else 0
        }

    # Governance and Audit
    def apply_audit_lens(self, lens_name: str, lens_criteria: Dict[str, Any]) -> Dict[str, Any]:
        """Apply audit lens to service map and connections"""
        findings = []
        overall_score = 0.0

        # Apply lens to services
        for service in self.services.values():
            service_findings = []

            if lens_name == "scalability":
                # Check service scalability
                if service.is_core_service() and service.estimated_cpu_cores < 1.0:
                    service_findings.append(f"Core service {service.service_name} has low CPU allocation")
                if service.requires_gpu() and not service.service_config.get('gpu_enabled'):
                    service_findings.append(f"GPU-required service {service.service_name} not configured for GPU")

            elif lens_name == "reliability":
                # Check dependency relationships
                if len(service.dependencies) > 3:
                    service_findings.append(f"High dependency count: {len(service.dependencies)}")
                if service.is_core_service() and len(service.dependents) > 5:
                    service_findings.append(f"High dependent count for core service: {len(service.dependents)}")

            service.audit_lens_applied.append(lens_name)
            findings.append({
                "service_name": service.service_name,
                "findings": service_findings
            })

            if not service_findings:
                overall_score += 1.0 / len(self.services)

        # Apply lens to connections
        for connection in self.connections:
            connection.audit_lens_applied.append(lens_name)

        return {
            "lens_name": lens_name,
            "evaluation_score": min(1.0, overall_score),
            "services_evaluated": len(self.services),
            "connections_evaluated": len(self.connections),
            "findings": findings,
            "recommendations": [
                f"Address findings from {lens_name} audit lens",
                "Review service dependency topology for optimization",
                "Ensure connection reliability meets SLA requirements"
            ]
        }

    # Serialization
    def to_dict(self) -> Dict[str, Any]:
        """Export service map to dictionary"""
        return {
            "services": {name: service.to_dict() for name, service in self.services.items()},
            "connections": [conn.to_dict() for conn in self.connections],
            "last_updated": self.last_updated.isoformat()
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ServiceMap':
        """Import service map from dictionary"""
        service_map = cls()

        # Load last updated time
        if data.get('last_updated'):
            service_map.last_updated = datetime.fromisoformat(data['last_updated'])

        # Load services
        for service_data in data.get('services', {}).values():
            service = BookFairyService.from_dict(service_data)
            service_map.services[service.service_name] = service

        # Load connections
        for conn_data in data.get('connections', []):
            connection = ServiceConnection.from_dict(conn_data)
            service_map.connections.append(connection)

        return service_map

    def __repr__(self) -> str:
        return (f"ServiceMap(services={len(self.services)}, "
                f"connections={len(self.connections)}, "
                f"last_updated={self.last_updated})")
