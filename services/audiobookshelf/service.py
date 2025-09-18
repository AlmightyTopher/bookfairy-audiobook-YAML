#!/usr/bin/env python3
"""
BookFairy Audiobookshelf Service Integration
Implements real audiobook library management and streaming
Based on Audiobookshelf API specification
"""

import asyncio
import json
import requests
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
class LibraryItem:
    """Audiobookshelf library item structure"""
    id: str
    name: str
    media_type: str
    size: int
    duration: Optional[float] = None
    tracks: Optional[List[Dict]] = None
    metadata: Optional[Dict] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


@dataclass
class LibraryStat:
    """Audiobookshelf library statistics"""
    total_items: int
    total_duration: float
    total_size: int
    total_authors: int
    total_series: int
    genre_counts: Dict[str, int]
    updated_at: str


class AudiobookshelfService:
    """Real Audiobookshelf API integration service"""

    def __init__(self):
        self.base_url = os.getenv("AUDIOBOOKSHELF_URL", "http://localhost:13378")
        self.api_key = os.getenv("AUDIOBOOKSHELF_API_KEY")
        self._headers = {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}

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
        print(f"AudiobookshelfService initialized - API: {self.base_url}")

    def _audit_service_initialization(self):
        """Apply governance audit to service initialization"""
        audit_target = {
            "component": "audiobookshelf_service",
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
                    print("   → Please verify Audiobookshelf configuration")
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
        """Make authenticated API request to Audiobookshelf"""

        # Apply security audit to each API call
        audit_target = {
            "component": "audiobookshelf_service",
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
            url = f"{self.base_url}{endpoint}"

            # Make request based on method
            if method == "POST":
                response = requests.post(url, headers=self._headers, params=params, json=data, timeout=30)
            elif method == "GET":
                response = requests.get(url, headers=self._headers, params=params, timeout=30)
            elif method == "PATCH":
                response = requests.patch(url, headers=self._headers, params=params, json=data, timeout=30)
            elif method == "DELETE":
                response = requests.delete(url, headers=self._headers, params=params, timeout=30)
            else:
                raise ValueError(f"Unsupported HTTP method: {method}")

            self.service_stats["successful_calls"] += 1

            # Apply data quality audit to responses
            data_audit_target = {
                "component": "audiobookshelf_service",
                "action": "process_response",
                "response_code": response.status_code,
                "response_size": len(response.text)
            }
            data_findings = self.audit_framework.apply_lens(AuditLens.DATA_QUALITY_INTEGRITY, data_audit_target)

            if response.status_code == 200:
                if response.headers.get('Content-Type', '').startswith('application/json'):
                    return response.json()
                else:
                    return {"content": response.text}
            else:
                raise ValueError(f"API call failed: HTTP {response.status_code} - {response.text[:200]}")

        except Exception as e:
            self.service_stats["failed_calls"] += 1
            raise Exception(f"Audiobookshelf API error: {str(e)}")

    async def search_library(self, query: str, max_results: int = 20) -> List[LibraryItem]:
        """Search Audiobookshelf library for audiobooks"""

        # Apply performance efficiency audit
        audit_target = {
            "component": "audiobookshelf_service",
            "action": "search_library",
            "query": query,
            "max_results": max_results
        }
        perf_findings = self.audit_framework.apply_lens(AuditLens.PERFORMANCE_EFFICIENCY, audit_target)

        try:
            # Real Audiobookshelf search API
            params = {
                "query": query,
                "limit": max_results
            }

            search_results = self._make_authenticated_request("/api/libraries/search", "GET", params)

            # Parse results into LibraryItem objects
            audiobooks = []
            if "results" in search_results and "books" in search_results["results"]:
                for book in search_results["results"]["books"][:max_results]:
                    audiobook = LibraryItem(
                        id=book.get("id", ""),
                        name=book.get("title", ""),
                        media_type=book.get("mediaType", "audiobook"),
                        size=book.get("size", 0),
                        duration=book.get("duration"),
                        metadata={
                            "author": book.get("author", {}),
                            "series": book.get("series", {}),
                            "genres": book.get("genres", []),
                            "publishedDate": book.get("publishedDate"),
                            "description": book.get("description")
                        }
                    )
                    audiobooks.append(audiobook)

            return audiobooks

        except Exception as e:
            print(f"❌ Library search failed: {e}")
            return []

    async def get_library_stats(self) -> LibraryStat:
        """Get comprehensive Audiobookshelf library statistics"""

        try:
            # Real Audiobookshelf stats API
            stats_data = self._make_authenticated_request("/api/libraries/stats", "GET")

            library_stats = LibraryStat(
                total_items=stats_data.get("totalItems", 0),
                total_duration=stats_data.get("totalDuration", 0.0),
                total_size=stats_data.get("totalSize", 0),
                total_authors=stats_data.get("totalAuthors", 0),
                total_series=stats_data.get("totalSeries", 0),
                genre_counts=stats_data.get("genreCounts", {}),
                updated_at=datetime.utcnow().isoformat()
            )

            print("📚 Audiobookshelf Library Statistics:")
            print(f"   Total Items: {library_stats.total_items}")
            print(f"   Authors: {library_stats.total_authors}")
            print(f"   Series: {library_stats.total_series}")
            print(f"   Duration: {library_stats.total_duration:.1f} hours")

            return library_stats

        except Exception as e:
            print(f"❌ Failed to get library stats: {e}")
            return LibraryStat(
                total_items=0,
                total_duration=0.0,
                total_size=0,
                total_authors=0,
                total_series=0,
                genre_counts={},
                updated_at=datetime.utcnow().isoformat()
            )

    async def get_user_preferences(self, user_id: str) -> Dict[str, Any]:
        """Get user listening preferences and settings"""

        try:
            # Real Audiobookshelf user preferences API
            user_data = self._make_authenticated_request("/api/me", "GET")

            preferences = {
                "user_id": user_id,
                "preferred_formats": user_data.get("settings", {}).get("preferredAudioFormats", []),
                "bookmarks": user_data.get("mediaProgress", []),
                "play_offset": user_data.get("playOffset", 0),
                "playback_rate": user_data.get("settings", {}).get("playbackRate", 1.0),
                "created_at": datetime.utcnow().isoformat()
            }

            return preferences

        except Exception as e:
            print(f"❌ Failed to get user preferences: {e}")
            return {
                "user_id": user_id,
                "preferred_formats": ["mp3"],
                "play_offset": 0,
                "playback_rate": 1.0,
                "created_at": datetime.utcnow().isoformat()
            }

    async def add_bookmark(self, user_id: str, book_id: str, position: float,
                          description: Optional[str] = None) -> bool:
        """Add a bookmark for user's listening position"""

        # Apply observability audit for user interaction tracking
        audit_target = {
            "component": "audiobookshelf_service",
            "action": "add_bookmark",
            "user_id": user_id,
            "book_id": book_id,
            "position": position,
            "has_description": bool(description)
        }
        obs_findings = self.audit_framework.apply_lens(AuditLens.OBSERVABILITY_FEEDBACK, audit_target)

        try:
            bookmark_data = {
                "bookId": book_id,
                "position": position,
                "description": description or f"Bookmark at {position}s"
            }

            response = self._make_authenticated_request("/api/me/progress", "POST", None, bookmark_data)

            success = response.get("success", False)
            if success:
                print(f"✅ Bookmark added for {book_id} by {user_id} at {position}s")
            else:
                print(f"❌ Failed to add bookmark for {book_id}")

            return success

        except Exception as e:
            print(f"❌ Bookmark creation error: {e}")
            return False

    async def get_media_progress(self, user_id: str, book_id: str) -> Dict[str, Any]:
        """Get user's listening progress for a specific audiobook"""

        try:
            # Real Audiobookshelf media progress API
            params = {"bookId": book_id}
            progress_data = self._make_authenticated_request("/api/me/progress", "GET", params)

            progress = {
                "user_id": user_id,
                "book_id": book_id,
                "current_time": progress_data.get("currentTime", 0.0),
                "is_finished": progress_data.get("isFinished", False),
                "duration": progress_data.get("duration", 0.0),
                "progress_percentage": progress_data.get("progress", 0.0),
                "last_updated": progress_data.get("updatedAt", datetime.utcnow().isoformat())
            }

            return progress

        except Exception as e:
            print(f"❌ Failed to get media progress: {e}")
            return {
                "user_id": user_id,
                "book_id": book_id,
                "current_time": 0.0,
                "is_finished": False,
                "duration": 0.0,
                "progress_percentage": 0.0,
                "last_updated": datetime.utcnow().isoformat()
            }

    async def check_service_health(self) -> HealthCheckResult:
        """Perform comprehensive health check of Audiobookshelf service"""

        audit_target = {
            "component": "audiobookshelf_service",
            "action": "health_check"
        }
        reliability_findings = self.audit_framework.apply_lens(AuditLens.RELIABILITY_CONTINUITY, audit_target)

        result = HealthCheckResult(
            check_id=f"health_audiobookshelf_{int(datetime.utcnow().timestamp())}",
            service_name="audiobookshelf",
            check_type="http_api",
            endpoint="/healthcheck"
        )

        try:
            # Test Audiobookshelf connectivity with health endpoint
            start_time = datetime.utcnow()
            health_response = self._make_authenticated_request("/healthcheck", "GET")
            response_time = int((datetime.utcnow() - start_time).total_seconds() * 1000)

            result.record_success(
                response_time_ms=response_time,
                details={
                    "api_reachable": True,
                    "service_healthy": health_response.get("healthy", False),
                    "database_status": health_response.get("databaseConnection", False),
                    "service_stats": self.service_stats
                }
            )

            self.service_stats["last_health_check"] = datetime.utcnow()
            self.service_stats["service_state"] = "healthy"

            return result

        except Exception as e:
            result.record_failure(f"Audiobookshelf health check failed: {str(e)}")
            self.service_stats["service_state"] = "unhealthy"
            self.service_stats["last_health_check"] = datetime.utcnow()
            return result

    def get_service_info(self) -> Dict[str, Any]:
        """Get comprehensive Audiobookshelf service information"""

        governance_audit_target = {
            "component": "audiobookshelf_service",
            "action": "service_info"
        }
        governance_findings = self.audit_framework.apply_lens(AuditLens.GOVERNANCE_MANAGEMENT, governance_audit_target)

        return {
            "service_name": "audiobookshelf",
            "type": "audiobook_library",
            "description": "Audiobookshelf library management and streaming service",
            "base_url": self._get_url_pattern(self.base_url),
            "api_key_configured": bool(self.api_key),
            "service_stats": self.service_stats,
            "audit_findings_count": len(governance_findings) if governance_findings else 0,
            "last_updated": datetime.utcnow().isoformat()
        }

    async def get_recently_added(self, limit: int = 10) -> List[LibraryItem]:
        """Get recently added audiobooks"""

        try:
            # Real Audiobookshelf recent items API
            params = {"limit": limit}
            recent_data = self._make_authenticated_request("/api/libraries/recent", "GET", params)

            recent_items = []
            if "recent" in recent_data:
                for item in recent_data["recent"][:limit]:
                    library_item = LibraryItem(
                        id=item.get("id", ""),
                        name=item.get("title", ""),
                        media_type=item.get("mediaType", "audiobook"),
                        size=item.get("size", 0),
                        duration=item.get("duration"),
                        metadata={"addedAt": item.get("addedAt")},
                        created_at=item.get("addedAt"),
                        updated_at=item.get("updatedAt")
                    )
                    recent_items.append(library_item)

            return recent_items

        except Exception as e:
            print(f"❌ Failed to get recently added items: {e}")
            return []


# REST API endpoint handlers for orchestration integration
async def handle_library_search(query: str, max_results: int = 10) -> Dict[str, Any]:
    """REST API handler for library search"""

    try:
        service = AudiobookshelfService()
        results = await service.search_library(query, max_results)

        return {
            "success": True,
            "service": "audiobookshelf",
            "query": query,
            "total_results": len(results),
            "audiobooks": [asdict(result) for result in results]
        }

    except Exception as e:
        return {
            "success": False,
            "service": "audiobookshelf",
            "query": query,
            "error": str(e)
        }

async def handle_library_stats() -> Dict[str, Any]:
    """REST API handler for library statistics"""

    try:
        service = AudiobookshelfService()
        stats = await service.get_library_stats()

        return {
            "success": True,
            "service": "audiobookshelf",
            "library_stats": asdict(stats)
        }

    except Exception as e:
        return {
            "success": False,
            "service": "audiobookshelf",
            "error": str(e)
        }

async def handle_user_progress(user_id: str, book_id: str) -> Dict[str, Any]:
    """REST API handler for user progress"""

    try:
        service = AudiobookshelfService()
        progress = await service.get_media_progress(user_id, book_id)

        return {
            "success": True,
            "service": "audiobookshelf",
            "user_progress": progress
        }

    except Exception as e:
        return {
            "success": False,
            "service": "audiobookshelf",
            "user_id": user_id,
            "book_id": book_id,
            "error": str(e)
        }

# Service registry for orchestration
audiobookshelf_service = None

def get_service():
    """Get singleton service instance"""
    global audiobookshelf_service
    if audiobookshelf_service is None:
        audiobookshelf_service = AudiobookshelfService()
    return audiobookshelf_service

# Test script
async def test_service():
    """Test the Audiobookshelf service functionality"""

    print("🧪 Testing Audiobookshelf Service...")
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

    # Test 3: Library stats (if service is running)
    if health_result.status == HealthStatus.HEALTHY:
        print("\n3. Testing Library Stats:")
        try:
            stats = await service.get_library_stats()
            print(f"   Total books: {stats.total_items}")
        except Exception as e:
            print(f"   Error (expected if no Audiobookshelf running): {e}")

    print("\n✅ Audiobookshelf Service test completed!")
    print("🔗 Ready for integration with orchestration engine")

if __name__ == "__main__":
    asyncio.run(test_service())
