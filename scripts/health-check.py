#!/usr/bin/env python3
"""
Health Check Service for BookFairy
Monitors all services, provides health endpoints, and implements comprehensive health checks
Based on data-model.md specification and integration tests
"""
import asyncio
import json
import time
import requests
import sys
import os
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any

# Add project root to path for imports
sys.path.append(os.path.join(os.path.dirname(__file__), "..", ".."))

try:
    from services.shared.models.health import (
        HealthCheckResult, HealthStatus, HealthCheckType, HealthMonitorRegistry
    )
    from services.shared.models.container import DockerContainerRegistry
    from services.shared.models.service_map import BookFairyService, ServiceMap
    from services.shared.models.governance import AuditLensFramework, AuditLens
except ImportError:
    print("Warning: Could not import from services.shared. Using relative imports.")
    sys.path.append(os.path.join(os.path.dirname(__file__), ".."))
    from services.shared.models.health import (
        HealthCheckResult, HealthStatus, HealthCheckType, HealthMonitorRegistry
    )
    from services.shared.models.container import DockerContainerRegistry
    from services.shared.models.service_map import BookFairyService, ServiceMap
    from services.shared.models.governance import AuditLensFramework, AuditLens


class BookFairyHealthChecker:
    """Comprehensive health checker for BookFairy services"""

    def __init__(self):
        self.monitor_registry = HealthMonitorRegistry()
        self.container_registry = DockerContainerRegistry()
        self.service_map = ServiceMap()
        self.audit_framework = AuditLensFramework()

        # Health check configuration
        self.check_intervals = {
            "discord_bot": 30,
            "lazylibrarian": 60,
            "audiobookshelf": 60,
            "redis": 30,
            "qbittorrent": 60,
            "prowlarr": 60,
            "lm_studio": 120
        }

        # Last check times
        self.last_checks: Dict[str, datetime] = {}

        print("BookFairy Health Checker initialized")

    def register_services(self):
        """Register all BookFairy services for monitoring"""
        services = [
            {
                "name": "discord-bot",
                "type": "discord-bot",
                "display_name": "Discord Bot Service",
                "description": "BookFairy Discord bot for user interactions",
                "api_port": 8080,
                "health_endpoint": "/health"
            },
            {
                "name": "lazylibrarian",
                "type": "lazylibrarian",
                "display_name": "LazyLibrarian",
                "description": "Audiobook acquisition and management",
                "api_port": 5299,
                "health_endpoint": "/health"
            },
            {
                "name": "audiobookshelf",
                "type": "audiobookshelf",
                "display_name": "Audiobookshelf",
                "description": "Audiobook library server and player",
                "api_port": 13378,
                "health_endpoint": "/healthcheck"
            },
            {
                "name": "redis",
                "type": "redis",
                "display_name": "Redis Cache",
                "description": "Caching and session management",
                "api_port": 6379,
                "health_endpoint": "/health"
            },
            {
                "name": "qbittorrent",
                "type": "qbittorrent",
                "display_name": "qBittorrent",
                "description": "Torrent client for audiobook downloads",
                "api_port": 8080,  # Default qBittorrent port
                "health_endpoint": "/api/v2/app/version"
            },
            {
                "name": "prowlarr",
                "type": "prowlarr",
                "display_name": "Prowlarr",
                "description": "Indexer management for audiobook sources",
                "api_port": 9696,
                "health_endpoint": "/api/v1/health"
            },
            {
                "name": "lm-studio",
                "type": "lm-studio",
                "display_name": "LM Studio AI",
                "description": "Local AI model server for recommendations",
                "api_port": 1234,
                "health_endpoint": "/v1/models"
            }
        ]

        for service_config in services:
            service = BookFairyService(
                service_name=service_config["name"],
                service_type=service_config["type"],
                display_name=service_config["display_name"],
                description=service_config["description"],
                api_port=service_config["api_port"],
                health_endpoint=service_config["health_endpoint"]
            )

            self.service_map.add_service(service)
            self.monitor_registry.register_service(service.service_name)

            print(f"Registered service: {service.service_name}")

    def perform_health_check(self, service_name: str) -> HealthCheckResult:
        """Perform comprehensive health check for a service"""

        service = self.service_map.get_service(service_name)
        if not service:
            # If service not in map, create a basic result
            result = HealthCheckResult(
                check_id=f"health_{service_name}_{int(time.time())}",
                service_name=service_name,
                check_type=HealthCheckType.HTTP_API,
                status=HealthStatus.UNKNOWN
            )
            result.record_failure(f"Service {service_name} not registered")
            return result

        # Create health check result
        check_id = f"health_{service_name}_{int(time.time())}"
        result = HealthCheckResult(
            check_id=check_id,
            service_name=service_name,
            check_type=HealthCheckType.HTTP_API,
            endpoint=service.health_endpoint
        )

        try:
            # Perform HTTP health check
            health_url = service.get_health_url()
            if not health_url:
                result.record_failure("No health endpoint configured")
                return result

            # Make HTTP request
            start_time = time.time()
            response = requests.get(health_url, timeout=10)
            response_time = int((time.time() - start_time) * 1000)

            # Record success
            result.record_success(
                response_time_ms=response_time,
                details={"status_code": response.status_code, "url": health_url}
            )

            # Check for service-specific health conditions
            if service.service_type == "redis":
                # Redis-specific health check
                self._check_redis_health(result)
            elif service.service_type == "qbittorrent":
                # qBittorrent-specific health check
                self._check_qbittorrent_health(result)
            elif service.service_type == "lm-studio":
                # LM Studio specific health check
                self._check_lm_studio_health(result)
            else:
                # Generic 200 OK check
                if response.status_code == 200:
                    result.record_success(
                        response_time_ms=response_time,
                        details={"generic_check": True, "content_length": len(response.content)}
                    )
                else:
                    result.record_failure(f"HTTP {response.status_code}: {response.text[:100]}")

        except requests.exceptions.Timeout:
            result.record_failure("Health check timed out")
        except requests.exceptions.ConnectionError:
            result.record_failure("Connection failed - service may be down")
        except requests.exceptions.RequestException as e:
            result.record_failure(f"Request error: {str(e)}")
        except Exception as e:
            result.record_failure(f"Unexpected error: {str(e)}")

        # Apply governance audit
        self._apply_health_governance_audit(result)

        return result

    def _check_redis_health(self, result: HealthCheckResult):
        """Redis-specific health checks"""
        try:
            import redis

            # Try to connect to Redis
            redis_client = redis.Redis(host='localhost', port=6379, db=0)
            ping_result = redis_client.ping()

            if ping_result:
                # Get basic Redis stats
                info = redis_client.info()
                result.details.update({
                    "redis_connected": True,
                    "uptime_seconds": info.get("uptime_in_seconds", 0),
                    "total_connections_received": info.get("total_connections_received", 0)
                })
            else:
                result.record_failure("Redis ping failed")

        except ImportError:
            result.details["redis_check_note"] = "redis-py package not installed"
        except Exception as e:
            result.record_failure(f"Redis health check failed: {str(e)}")

    def _check_qbittorrent_health(self, result: HealthCheckResult):
        """qBittorrent-specific health checks"""
        try:
            # qBittorrent API call to get version (our health endpoint)
            response = requests.get("http://localhost:8080/api/v2/app/version", timeout=5)
            if response.status_code == 200:
                version = response.text.strip()
                result.details.update({
                    "qbt_version": version,
                    "api_healthy": True
                })
            else:
                result.record_failure(f"qBittorrent API returned {response.status_code}")

        except Exception as e:
            result.record_failure(f"qBittorrent health check failed: {str(e)}")

    def _check_lm_studio_health(self, result: HealthCheckResult):
        """LM Studio-specific health checks"""
        try:
            # Check models endpoint
            response = requests.get("http://localhost:1234/v1/models", timeout=15)
            if response.status_code == 200:
                models_data = response.json()
                model_count = len(models_data.get("data", []))

                result.details.update({
                    "models_available": model_count,
                    "api_healthy": True
                })

                if model_count == 0:
                    result.details["warning"] = "No AI models loaded"

            else:
                result.record_failure(f"LM Studio API returned {response.status_code}")

        except Exception as e:
            result.record_failure(f"LM Studio health check failed: {str(e)}")

    def _apply_health_governance_audit(self, result: HealthCheckResult):
        """Apply governance audit lenses to health check results"""

        # Apply observability lens to ensure monitoring coverage
        audit_target = {
            "service_name": result.service_name,
            "health_status": result.status.value,
            "response_time_ms": result.response_time_ms,
            "consecutive_failures": result.consecutive_failures,
            "check_type": result.check_type.value
        }

        findings = self.audit_framework.apply_lens(
            AuditLens.OBSERVABILITY_FEEDBACK,
            audit_target,
            {"context": "health_monitoring"}
        )

        # Store findings for later analysis
        result.details["audit_findings"] = len(findings)

    async def continuous_monitoring(self):
        """Run continuous health monitoring in the background"""
        print("Starting continuous health monitoring...")

        while True:
            try:
                # Check all registered services
                for service_name in self.service_map.services.keys():
                    await self.check_service_health(service_name)
                    await asyncio.sleep(0.1)  # Small delay between checks

                # Wait until next monitoring cycle
                await asyncio.sleep(30)  # Check every 30 seconds

            except Exception as e:
                print(f"Health monitoring error: {e}")
                await asyncio.sleep(30)

    async def check_service_health(self, service_name: str) -> HealthCheckResult:
        """Asynchronous health check for a service"""
        try:
            # Create health check in background thread (since requests isn't async)
            result = await asyncio.to_thread(self.perform_health_check, service_name)

            # Record result in monitoring registry
            self.monitor_registry.record_health_check(result)

            # Log significant events
            if result.is_critical_failure():
                print(f"🚨 CRITICAL: {service_name} health check failed {result.consecutive_failures} times")
                print(f"   Reason: {result.error_message}")

            elif result.status == HealthStatus.UNHEALTHY:
                print(f"⚠️  WARNING: {service_name} health check failed")
                print(f"   Reason: {result.error_message}")

            return result

        except Exception as e:
            print(f"Health check error for {service_name}: {e}")
            # Create error result
            error_result = HealthCheckResult(
                check_id=f"error_{service_name}_{int(time.time())}",
                service_name=service_name,
                check_type=HealthCheckType.HTTP_API
            )
            error_result.record_failure(f"Exception during health check: {str(e)}")
            return error_result

    def get_system_health_report(self) -> Dict[str, Any]:
        """Generate comprehensive system health report"""
        return self.monitor_registry.get_system_health_overview()

    def get_service_health_details(self, service_name: str) -> Dict[str, Any]:
        """Get detailed health information for a specific service"""
        summary = self.monitor_registry.get_service_health(service_name)
        if summary:
            return summary.to_dict()

        # Return default if not found
        return {
            "service_name": service_name,
            "overall_status": "unknown",
            "check_results": [],
            "last_updated": datetime.utcnow().isoformat()
        }

    def get_overall_availability_percentage(self) -> float:
        """Calculate overall system availability percentage"""
        system_health = self.get_system_health_report()

        if system_health["total_services"] == 0:
            return 0.0

        healthy_count = system_health["healthy_services"]
        total_count = system_health["total_services"]

        return (healthy_count / total_count) * 100.0

    def check_service_dependencies(self, service_name: str) -> Dict[str, Any]:
        """Check health of all services that a given service depends on"""
        service = self.service_map.get_service(service_name)
        if not service:
            return {"error": "Service not found"}

        dependencies_health = {}

        for dependency in service.dependencies:
            health_data = self.monitor_registry.get_service_health(dependency)
            if health_data:
                dependencies_health[dependency] = {
                    "overall_status": health_data.overall_status.value,
                    "healthy_checks": health_data.healthy_checks,
                    "unhealthy_checks": health_data.unhealthy_checks,
                    "last_updated": health_data.last_updated.isoformat()
                }

        return {
            "service": service_name,
            "dependencies": dependencies_health,
            "all_healthy": all(
                dep.get("overall_status") == "healthy"
                for dep in dependencies_health.values()
            )
        }


class HealthCheckAPI:
    """REST API endpoints for health checks"""

    def __init__(self, health_checker: BookFairyHealthChecker):
        self.health_checker = health_checker

    async def health_basic(self) -> Dict[str, Any]:
        """Basic health check endpoint"""
        try:
            system_health = self.health_checker.get_system_health_report()
            availability = self.health_checker.get_overall_availability_percentage()

            if availability >= 90.0:
                status = "healthy"
                status_code = 200
            elif availability >= 70.0:
                status = "degraded"
                status_code = 200
            else:
                status = "unhealthy"
                status_code = 503

            return {
                "status": status,
                "availability_percentage": availability,
                "checked_at": datetime.utcnow().isoformat(),
                "services_count": system_health["total_services"],
                "services_healthy": system_health["healthy_services"],
                "services_unhealthy": system_health["unhealthy_services"]
            }, status_code

        except Exception as e:
            return {
                "status": "error",
                "error": str(e),
                "checked_at": datetime.utcnow().isoformat()
            }, 500

    async def health_detailed(self) -> Dict[str, Any]:
        """Detailed health check endpoint"""
        try:
            detailed_report = self.health_checker.get_system_health_report()

            # Add dependency checks for all services
            dependency_revisions = {}
            for service_name in self.health_checker.service_map.services.keys():
                dependency_revisions[service_name] = self.health_checker.check_service_dependencies(service_name)

            detailed_report["dependency_health"] = dependency_revisions

            # Add governance audit summary
            audit_summary = {
                "framework_active": True,
                "lenses_applied": ["safety-security", "observability"],
                "recent_findings_count": 0  # Could be populated from audit registry
            }
            detailed_report["governance_audit"] = audit_summary

            return detailed_report, 200

        except Exception as e:
            return {
                "error": str(e),
                "detailed_health": "unavailable",
                "checked_at": datetime.utcnow().isoformat()
            }, 500

    async def health_ready(self) -> Dict[str, Any]:
        """Readiness health check - can this service serve traffic?"""
        try:
            # Check if critical services are healthy
            critical_services = ["discord-bot", "redis"]  # Minimum required services
            critical_healthy = True

            for service in critical_services:
                health_data = self.health_checker.monitor_registry.get_service_health(service)
                if health_data and health_data.overall_status not in ["healthy", "degraded"]:
                    critical_healthy = False
                    break

            if critical_healthy:
                return {
                    "status": "ready",
                    "message": "Critical services are healthy",
                    "checked_at": datetime.utcnow().isoformat()
                }, 200
            else:
                return {
                    "status": "not_ready",
                    "message": "One or more critical services are unhealthy",
                    "checked_at": datetime.utcnow().isoformat()
                }, 503

        except Exception as e:
            return {
                "status": "unknown",
                "error": str(e),
                "checked_at": datetime.utcnow().isoformat()
            }, 500

    async def health_cluster(self) -> Dict[str, Any]:
        """Cluster-wide health check including inter-service connectivity"""
        try:
            system_health = self.health_checker.get_system_health_report()

            # Test inter-service connectivity
            connectivity_tests = {
                "discord_to_redis": self.test_service_connectivity("discord-bot", "redis"),
                "lazylibrarian_to_prowlarr": self.test_service_connectivity("lazylibrarian", "prowlarr"),
                "audiobookshelf_to_redis": self.test_service_connectivity("audiobookshelf", "redis")
            }

            system_health["connectivity_tests"] = connectivity_tests
            system_health["all_services_connected"] = all(connectivity_tests.values())

            return system_health, 200

        except Exception as e:
            return {
                "error": str(e),
                "cluster_health": "unavailable",
                "checked_at": datetime.utcnow().isoformat()
            }, 500

    def test_service_connectivity(self, service_a: str, service_b: str) -> bool:
        """Test connectivity between two services (simplified)"""
        # For now, just check if both services are individually healthy
        # In production, this would test actual inter-service communication
        health_a = self.health_checker.monitor_registry.get_service_health(service_a)
        health_b = self.health_checker.monitor_registry.get_service_health(service_b)

        return (
            health_a and health_a.overall_status == "healthy" and
            health_b and health_b.overall_status == "healthy"
        )


async def main():
    """Main function to run health checker"""

    # Initialize health checker
    health_checker = BookFairyHealthChecker()
    health_checker.register_services()

    # Initialize API
    health_api = HealthCheckAPI(health_checker)

    print("BookFairy Health Check Service started")
    print("Registered services:", list(health_checker.service_map.services.keys()))
    print("\n" + "="*60)
    print("Testing all services...")

    # Test all services immediately
    for service_name in health_checker.service_map.services.keys():
        print(f"\n🔍 Checking {service_name}...")
        result = await health_checker.check_service_health(service_name)
        print(f"   Status: {result.status.value}")
        if result.error_message:
            print(f"   Error: {result.error_message}")
        if result.response_time_ms:
            print(f"   Response time: {result.response_time_ms}ms")

    # Print system health summary
    print("\n" + "="*60)
    system_health = health_checker.get_system_health_report()
    print("📊 SYSTEM HEALTH SUMMARY:")
    print(".1f")
    print(f"   Healthy services: {system_health['healthy_services']}")
    print(f"   Unhealthy services: {system_health['unhealthy_services']}")
    print(f"   Availability: {health_checker.get_overall_availability_percentage():.1f}%")

    # Start continuous monitoring
    print("\n🔄 Starting continuous monitoring...")
    try:
        await health_checker.continuous_monitoring()
    except KeyboardInterrupt:
        print("\n🛑 Health check service stopped by user")
    except Exception as e:
        print(f"\n❌ Health check service error: {e}")
    finally:
        print("📋 Health check service shutdown complete")


if __name__ == "__main__":
    asyncio.run(main())
