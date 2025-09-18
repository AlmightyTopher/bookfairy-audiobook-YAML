#!/usr/bin/env python3
"""
BookFairy Prowlarr Service Integration
Implements indexer management and content discovery
Based on Prowlarr API specification
"""

import asyncio
import requests
import json
import sys
import os
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict

# Add project root
script_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(os.path.dirname(script_dir))
services_path = os.path.join(project_root, "services")
sys.path.insert(0, services_path)

from services.shared.models.health import HealthCheckResult, HealthStatus
from services.shared.models.governance import AuditLensFramework, AuditLens


@dataclass
class IndexerInfo:
    """Prowlarr indexer information structure"""
    id: int
    name: str
    implementation_name: str
    implementation: str
    config_contract: str
    protocol: str
    categories: List[Dict]
    tags: List[str]
    fields: List[Dict]
    enabled: bool = True
    priority: int = 1
    download_weight: int = 0
    recent_teaser_hash: Optional[str] = None


@dataclass
class IndexerStats:
    """Prowlarr indexer statistics"""
    number_of_grabbed_releases: int
    number_of_failed_grabbed_releases: int
    number_of_indexer_queries: int
    number_of_failed_indexer_queries: int
    number_of_queries_per_day: List[Dict]
    number_of_grabbed_releases_per_day: List[Dict]
    indexer_status: List[Dict]


@dataclass
class SearchResult:
    """Prowlarr search result structure"""
    guid: str
    info_url: str
    download_url: str
    title: str
    publish_date: str
    size: int
    indexer_id: int
    indexer: str
    seeders: int
    leechers: int
    download_probability: float
    minimum_ratio: float
    minimum_seed_time: int
    categories: List[int]


class ProwlarrService:
    """Real Prowlarr API integration service"""

    def __init__(self):
        self.base_url = os.getenv("PROWLAAR_URL", "http://localhost:9696")
        self.api_key = os.getenv("PROWLAAR_API_KEY")
        self._headers = {
            "Content-Type": "application/json",
            "X-Api-Key": self.api_key
        }

        # Service initialization audit
        self.audit_framework = AuditLensFramework()

        # Stats for governance monitoring
        self.service_stats = {
            "api_calls": 0,
            "successful_calls": 0,
            "failed_calls": 0,
            "last_health_check": datetime.utcnow(),
            "service_state": "initialized"
        }

        self._audit_service_initialization()
        print(f"ProwlarrService initialized - API: {self.base_url}")

    def _audit_service_initialization(self):
        """Apply governance audit to service initialization"""
        audit_target = {
            "component": "prowlarr_service",
            "action": "service_initialization",
            "configuration": {
                "has_url": bool(self.base_url),
                "has_api_key": bool(self.api_key),
                "url_pattern": self._get_url_pattern(self.base_url)
            }
        }

        findings = self.audit_framework.apply_lens(AuditLens.SAFETY_SECURITY, audit_target)
        self._handle_security_findings(findings, "service_initialization")
        return findings

    def _handle_security_findings(self, findings, context):
        """Handle security audit findings appropriately"""
        for finding in findings:
            if finding.severity.value in ["CRITICAL", "HIGH"]:
                print(f"🚨 SECURITY FINDING: {finding.title} - {finding.description}")
                if finding.lens_type == AuditLens.SAFETY_SECURITY:
                    print("   → Please verify Prowlarr API key configuration")
            elif finding.severity.value in ["MEDIUM", "LOW"]:
                print(f"⚠️  SECURITY WARNING: {finding.title}")

    def _get_url_pattern(self, url):
        """Extract URL pattern for security auditing"""
        if not url:
            return "missing"
        try:
            from urllib.parse import urlparse
            parsed = urlparse(url)
            return f"{parsed.scheme}:{parsed.netloc.split(':')[0]}:port_hidden"
        except:
            return "invalid"

    def _make_authenticated_request(self, endpoint: str, method: str = "GET",
                                   params: Optional[Dict] = None,
                                   data: Optional[Dict] = None) -> Dict[str, Any]:
        """Make authenticated API request to Prowlarr"""

        # Apply security audit to each API call
        audit_target = {
            "component": "prowlarr_service",
            "action": "api_call",
            "endpoint": endpoint,
            "method": method,
            "has_params": bool(params),
            "has_data": bool(data)
        }
        security_findings = self.audit_framework.apply_lens(AuditLens.SAFETY_SECURITY, audit_target)
        self._handle_security_findings(security_findings, "api_call")

        # Update stats
        self.service_stats["api_calls"] += 1

        try:
            # Build full URL
            url = f"{self.base_url}/api/v3{endpoint}"

            # Make request based on method
            if method == "POST":
                response = requests.post(url, headers=self._headers, params=params, json=data, timeout=30)
            elif method == "GET":
                response = requests.get(url, headers=self._headers, params=params, timeout=30)
            elif method == "PUT":
                response = requests.put(url, headers=self._headers, params=params, json=data, timeout=30)
            elif method == "DELETE":
                response = requests.delete(url, headers=self._headers, params=params, timeout=30)
            else:
                raise ValueError(f"Unsupported HTTP method: {method}")

            self.service_stats["successful_calls"] += 1

            # Apply data quality audit to responses
            data_audit_target = {
                "component": "prowlarr_service",
                "action": "process_response",
                "response_code": response.status_code,
                "response_size": len(response.text)
            }
            data_findings = self.audit_framework.apply_lens(AuditLens.DATA_QUALITY_INTEGRITY, data_audit_target)

            if response.status_code == 200:
                return response.json()
            else:
                raise ValueError(f"API call failed: HTTP {response.status_code} - {response.text[:200]}")

        except Exception as e:
            self.service_stats["failed_calls"] += 1
            raise Exception(f"Prowlarr API error: {str(e)}")

    async def search_indexers(self, query: str, categories: List[int] = [2000, 5000, 7000],
                             type_filter: str = "torrent",
                             offset: int = 0, limit: int = 20) -> List[SearchResult]:
        """Search across all configured indexers"""

        # Apply performance efficiency audit
        audit_target = {
            "component": "prowlarr_service",
            "action": "search_indexers",
            "query": query,
            "max_results": limit,
            "category_count": len(categories)
        }
        perf_findings = self.audit_framework.apply_lens(AuditLens.PERFORMANCE_EFFICIENCY, audit_target)

        try:
            endpoint = "/search"
            params = {
                "query": query,
                "categories": ",".join(map(str, categories)),
                "type": type_filter,
                "offset": offset,
                "limit": limit
            }

            search_results = self._make_authenticated_request(endpoint, "GET", params)

            # Parse into SearchResult objects
            results = []
            if isinstance(search_results, list):
                for result in search_results[:limit]:
                    search_result = SearchResult(
                        guid=result.get("guid", ""),
                        info_url=result.get("infoUrl", ""),
                        download_url=result.get("downloadUrl", ""),
                        title=result.get("title", ""),
                        publish_date=result.get("publishDate", ""),
                        size=result.get("size", 0),
                        indexer_id=result.get("indexerId", 0),
                        indexer=result.get("indexer", ""),
                        seeders=result.get("seeders", 0),
                        leechers=result.get("leechers", 0),
                        download_probability=result.get("downloadProbability", 0.0),
                        minimum_ratio=result.get("minimumRatio", 0.0),
                        minimum_seed_time=result.get("minimumSeedTime", 0),
                        categories=result.get("categories", [])
                    )
                    results.append(search_result)

            print(f"✅ Found {len(results)} results across indexers for: '{query}'")
            return results

        except Exception as e:
            print(f"❌ Indexer search failed: {e}")
            return []

    async def get_indexers(self) -> List[IndexerInfo]:
        """Get all configured indexers"""

        try:
            endpoint = "/indexer"
            indexer_data = self._make_authenticated_request(endpoint, "GET")

            # Parse into IndexerInfo objects
            indexers = []
            if isinstance(indexer_data, list):
                for indexer in indexer_data:
                    indexer_info = IndexerInfo(
                        id=indexer.get("id", 0),
                        name=indexer.get("name", ""),
                        implementation_name=indexer.get("implementationName", ""),
                        implementation=indexer.get("implementation", ""),
                        config_contract=indexer.get("configContract", ""),
                        protocol=indexer.get("protocol", ""),
                        categories=indexer.get("categories", []),
                        tags=indexer.get("tags", []),
                        fields=indexer.get("fields", []),
                        enabled=indexer.get("enabled", True),
                        priority=indexer.get("priority", 1),
                        download_weight=indexer.get("downloadWeight", 0),
                        recent_teaser_hash=indexer.get("recentTeaserHash")
                    )
                    indexers.append(indexer_info)

            print(f"📊 Retrieved {len(indexers)} indexers")
            return indexers

        except Exception as e:
            print(f"❌ Get indexers error: {e}")
            return []

    async def get_indexer_stats(self) -> IndexerStats:
        """Get indexer statistics"""

        try:
            endpoint = "/indexer"  # Note: This should be adjusted based on Prowlarr's actual API
            stats_data = self._make_authenticated_request(endpoint, "GET")

            # Parse statistics (this may need adjustment based on actual Prowlarr API)
            if isinstance(stats_data, list) and len(stats_data) > 0:
                # This is placeholder logic - actual stats endpoint may be different
                sample_indexer = stats_data[0]

                # Placeholder stats structure
                indexer_stats = IndexerStats(
                    number_of_grabbed_releases=0,
                    number_of_failed_grabbed_releases=0,
                    number_of_indexer_queries=0,
                    number_of_failed_indexer_queries=0,
                    number_of_queries_per_day=[],
                    number_of_grabbed_releases_per_day=[],
                    indexer_status=[{
                        "id": sample_indexer.get("id", 0),
                        "name": sample_indexer.get("name", ""),
                        "enabled": sample_indexer.get("enabled", True),
                        "last_sync": datetime.utcnow().isoformat()
                    }]
                )

                print("📊 Indexer statistics retrieved")
                return indexer_stats
            else:
                return IndexerStats(
                    number_of_grabbed_releases=0,
                    number_of_failed_grabbed_releases=0,
                    number_of_indexer_queries=0,
                    number_of_failed_indexer_queries=0,
                    number_of_queries_per_day=[],
                    number_of_grabbed_releases_per_day=[],
                    indexer_status=[]
                )

        except Exception as e:
            print(f"❌ Get indexer stats error: {e}")
            return IndexerStats(
                number_of_grabbed_releases=0,
                number_of_failed_grabbed_releases=0,
                number_of_indexer_queries=0,
                number_of_failed_indexer_queries=0,
                number_of_queries_per_day=[],
                number_of_grabbed_releases_per_day=[],
                indexer_status=[]
            )

    async def add_indexer(self, indexer_config: Dict[str, Any]) -> bool:
        """Add a new indexer configuration"""

        # Apply governance audit for indexer management
        audit_target = {
            "component": "prowlarr_service",
            "action": "add_indexer",
            "indexer_name": indexer_config.get("name", ""),
            "implementation": indexer_config.get("implementation", ""),
            "protocol": indexer_config.get("protocol", "")
        }
        gov_findings = self.audit_framework.apply_lens(AuditLens.GOVERNANCE_MANAGEMENT, audit_target)

        try:
            endpoint = "/indexer"
            response = self._make_authenticated_request(endpoint, "POST", data=indexer_config)

            if response.get("id"):
                print(f"✅ Added indexer: {indexer_config.get('name', 'Unknown')}")
                return True
            else:
                print(f"❌ Failed to add indexer: {response.get('message', 'Unknown error')}")
                return False

        except Exception as e:
            print(f"❌ Add indexer error: {e}")
            return False

    async def delete_indexer(self, indexer_id: int) -> bool:
        """Delete an indexer configuration"""

        try:
            endpoint = f"/indexer/{indexer_id}"
            response = self._make_authenticated_request(endpoint, "DELETE")

            success = response is None or not response.get("message")  # 204 No Content or empty response
            if success:
                print(f"✅ Deleted indexer ID: {indexer_id}")
            else:
                print(f"❌ Failed to delete indexer {indexer_id}: {response.get('message', 'Error')}")
            return success

        except Exception as e:
            print(f"❌ Delete indexer error: {e}")
            return False

    async def update_indexer(self, indexer_id: int, updates: Dict[str, Any]) -> bool:
        """Update indexer configuration"""

        try:
            endpoint = f"/indexer/{indexer_id}"
            response = self._make_authenticated_request(endpoint, "PUT", data=updates)

            if response.get("id"):
                print(f"✅ Updated indexer ID: {indexer_id}")
                return True
            else:
                print(f"❌ Failed to update indexer {indexer_id}: {response.get('message', 'Error')}")
                return False

        except Exception as e:
            print(f"❌ Update indexer error: {e}")
            return False

    async def test_indexer(self, indexer_id: int) -> Dict[str, Any]:
        """Test indexer connectivity and functionality"""

        # Apply observability audit for testing
        audit_target = {
            "component": "prowlarr_service",
            "action": "test_indexer",
            "indexer_id": indexer_id
        }
        obs_findings = self.audit_framework.apply_lens(AuditLens.OBSERVABILITY_FEEDBACK, audit_target)

        try:
            endpoint = f"/indexer/test/{indexer_id}"
            test_result = self._make_authenticated_request(endpoint, "POST")

            success = test_result.get("isValid", False)
            message = test_result.get("message", "Test completed")

            result_info = {
                "indexer_id": indexer_id,
                "is_valid": success,
                "message": message,
                "last_tested": datetime.utcnow().isoformat()
            }

            print(f"✅ Indexer test completed: {success}")
            return result_info

        except Exception as e:
            print(f"❌ Indexer test error: {e}")
            return {
                "indexer_id": indexer_id,
                "is_valid": False,
                "message": str(e),
                "last_tested": datetime.utcnow().isoformat()
            }

    async def get_capabilities(self) -> List[str]:
        """Get comprehensive indexer capabilities"""

        try:
            indexers = await self.get_indexers()

            # Extract unique capabilities
            capabilities = []
            implementations = set()
            protocols = set()
            categories = set()

            for indexer in indexers:
                if indexer.enabled:
                    implementations.add(indexer.implementation_name)
                    protocols.add(indexer.protocol)
                    for category in indexer.categories:
                        category_id = category.get("id")
                        if category_id:
                            categories.add(category_id)

            capabilities = {
                "supported_implementations": list(implementations),
                "supported_protocols": list(protocols),
                "supported_categories": list(categories),
                "total_indexers": len([i for i in indexers if i.enabled]),
                "total_disabled": len([i for i in indexers if not i.enabled])
            }

            print("🔧 Indexer capabilities retrieved")
            return capabilities

        except Exception as e:
            print(f"❌ Get capabilities error: {e}")
            return {
                "supported_implementations": [],
                "supported_protocols": [],
                "supported_categories": [],
                "total_indexers": 0,
                "total_disabled": 0
            }

    async def check_service_health(self) -> HealthCheckResult:
        """Perform comprehensive Prowlarr health check"""

        audit_target = {
            "component": "prowlarr_service",
            "action": "health_check"
        }
        reliability_findings = self.audit_framework.apply_lens(AuditLens.RELIABILITY_CONTINUITY, audit_target)

        result = HealthCheckResult(
            check_id=f"health_prowlarr_{int(datetime.utcnow().timestamp())}",
            service_name="prowlarr",
            check_type="http_api",
            endpoint="/api/v3/system/status"
        )

        try:
            start_time = datetime.utcnow()

            # Test Prowlarr connectivity by getting system status
            system_status = self._make_authenticated_request("/system/status", "GET")
            response_time = int((datetime.utcnow() - start_time).total_seconds() * 1000)

            result.record_success(
                response_time_ms=response_time,
                details={
                    "api_reachable": True,
                    "version": system_status.get("version", "unknown"),
                    "startup_time": system_status.get("startupTime"),
                    "apps_supported": system_status.get("appProfiles"),
                    "service_stats": self.service_stats
                }
            )

            self.service_stats["last_health_check"] = datetime.utcnow()
            self.service_stats["service_state"] = "healthy"

            return result

        except Exception as e:
            result.record_failure(f"Prowlarr health check failed: {str(e)}")
            self.service_stats["service_state"] = "unhealthy"
            self.service_stats["last_health_check"] = datetime.utcnow()
            return result

    def get_service_info(self) -> Dict[str, Any]:
        """Get comprehensive Prowlarr service information"""

        # Apply governance audit
        governance_audit_target = {
            "component": "prowlarr_service",
            "action": "service_info"
        }
        governance_findings = self.audit_framework.apply_lens(AuditLens.GOVERNANCE_MANAGEMENT, governance_audit_target)

        return {
            "service_name": "prowlarr",
            "type": "indexer_management",
            "description": "Prowlarr indexer management and content discovery service",
            "base_url": self._get_url_pattern(self.base_url),
            "api_key_configured": bool(self.api_key),
            "service_stats": self.service_stats,
            "audit_findings_count": len(governance_findings) if governance_findings else 0,
            "last_updated": datetime.utcnow().isoformat()
        }


# REST API endpoint handlers for orchestration integration
async def handle_search_indexers(query: str, categories: List[int] = None,
                                type_filter: str = "torrent", limit: int = 20) -> Dict[str, Any]:
    """REST API handler for cross-indexer search"""

    try:
        service = ProwlarrService()

        # Default audiobook categories if none specified
        if not categories:
            categories = [2000, 5000, 7000]  # Audiobooks, Audio, Other categories

        results = await service.search_indexers(query, categories, type_filter, limit=limit)

        return {
            "success": True,
            "service": "prowlarr",
            "query": query,
            "categories": categories,
            "type_filter": type_filter,
            "total_results": len(results),
            "search_results": [asdict(result) for result in results]
        }

    except Exception as e:
        return {
            "success": False,
            "service": "prowlarr",
            "query": query,
            "categories": categories or [],
            "error": str(e)
        }

async def handle_get_indexers() -> Dict[str, Any]:
    """REST API handler for indexer list"""

    try:
        service = ProwlarrService()
        indexers = await service.get_indexers()

        return {
            "success": True,
            "service": "prowlarr",
            "total_indexers": len(indexers),
            "enabled_indexers": len([i for i in indexers if i.enabled]),
            "indexers": [asdict(indexer) for indexer in indexers]
        }

    except Exception as e:
        return {
            "success": False,
            "service": "prowlarr",
            "error": str(e)
        }

async def handle_test_indexer(indexer_id: int) -> Dict[str, Any]:
    """REST API handler for indexer testing"""

    try:
        service = ProwlarrService()
        test_result = await service.test_indexer(indexer_id)

        return {
            "success": True,
            "service": "prowlarr",
            "indexer_id": indexer_id,
            "test_result": test_result
        }

    except Exception as e:
        return {
            "success": False,
            "service": "prowlarr",
            "indexer_id": indexer_id,
            "error": str(e)
        }

async def handle_get_capabilities() -> Dict[str, Any]:
    """REST API handler for indexer capabilities"""

    try:
        service = ProwlarrService()
        capabilities = await service.get_capabilities()

        return {
            "success": True,
            "service": "prowlarr",
            "capabilities": capabilities
        }

    except Exception as e:
        return {
            "success": False,
            "service": "prowlarr",
            "error": str(e)
        }

# Service registry for orchestration
prowlarr_service = None

def get_service():
    """Get singleton service instance"""
    global prowlarr_service
    if prowlarr_service is None:
        prowlarr_service = ProwlarrService()
    return prowlarr_service

# Test script
async def test_service():
    """Test the Prowlarr service functionality"""

    print("🧪 Testing Prowlarr Service...")
    print("=" * 50)

    service = get_service()

    # Test 1: Health check
    print("\n1. Testing Health Check:")
    health_result = await service.check_service_health()
    print(f"   Status: {health_result.status.value}")
    if health_result.error_message:
        print(f"   Error: {health_result.error_message}")
    else:
        print(f"   Response time: {health_result.response_time_ms}ms")

    # Test 2: Service info
    print("\n2. Service Information:")
    info = service.get_service_info()
    for key, value in info.items():
        print(f"   {key}: {value}")

    # Test 3: Basic functionality (if service running)
    if health_result.status == HealthStatus.HEALTHY:
        print("\n3. Testing Capabilities:")
        try:
            capabilities = await service.get_capabilities()
            print(f"   Supported implementations: {capabilities.get('supported_implementations', [])}")
            print(f"   Total indexers: {capabilities.get('total_indexers', 0)}")
        except Exception as e:
            print(f"   Error (expected if no Prowlarr running): {e}")

    print("\n✅ Prowlarr Service test completed!")
    print("🔗 Ready for integration with orchestration engine")

if __name__ == "__main__":
    asyncio.run(test_service())
