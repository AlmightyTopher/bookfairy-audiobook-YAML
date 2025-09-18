#!/usr/bin/env python3
"""
BookFairy LazyLibrarian Service Integration
Implements real audiobook search and download functionality
Based on LazyLibrarian API specification
"""

import asyncio
import json
import requests
import sys
import os
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
import urllib.parse

# Add project root
script_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(os.path.dirname(script_dir))
services_path = os.path.join(project_root, "services")
sys.path.insert(0, services_path)

from services.shared.models.health import HealthCheckResult, HealthStatus
from services.shared.models.governance import AuditLensFramework, AuditLens


@dataclass
class AudiobookResult:
    """Audiobook search result from LazyLibrarian"""
    bookid: str
    title: str
    author: str
    pubdate: Optional[str] = None
    isbn: Optional[str] = None
    coverurl: Optional[str] = None
    summary: Optional[str] = None
    genres: Optional[str] = None
    series: Optional[str] = None
    seriesnum: Optional[str] = None
    status: str = "available"
    downloadurl: Optional[str] = None


class LazyLibrarianService:
    """Real LazyLibrarian API integration service"""

    def __init__(self):
        self.base_url = os.getenv("LAZYLIBRARIAN_URL", "http://localhost:5299")
        self.api_key = os.getenv("LAZYLIBRARIAN_API_KEY")
        self._headers = {"Content-Type": "application/json"}

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
        print(f"LazyLibrarianService initialized - API: {self.base_url}")

    def _audit_service_initialization(self):
        """Apply governance audit to service initialization"""
        audit_target = {
            "component": "lazylibrarian_service",
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
                    print("   → Please verify LazyLibrarian configuration")
            elif finding.severity.value in ["MEDIUM", "LOW"]:
                print(f"⚠️  SECURITY WARNING: {finding.title}")

    def _get_url_pattern(self, url):
        """Extract URL pattern for security auditing"""
        if not url:
            return "missing"
        try:
            parsed = urllib.parse.urlparse(url)
            return f"{parsed.scheme}:{parsed.netloc.split(':')[0]}:port_hidden"
        except:
            return "invalid"

    def _make_authenticated_request(self, endpoint: str, method: str = "GET",
                                   params: Optional[Dict] = None,
                                   data: Optional[Dict] = None) -> Dict[str, Any]:
        """Make authenticated API request to LazyLibrarian"""

        # Apply security audit to each API call
        audit_target = {
            "component": "lazylibrarian_service",
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
            # Build full URL and parameters
            url = f"{self.base_url}/{endpoint}"
            request_params = params or {}
            if self.api_key:
                request_params["api_key"] = self.api_key

            # Make request
            if method == "POST":
                response = requests.post(url, params=request_params, json=data,
                                       headers=self._headers, timeout=30)
            elif method == "GET":
                response = requests.get(url, params=request_params,
                                      headers=self._headers, timeout=30)
            elif method == "PUT":
                response = requests.put(url, params=request_params, json=data,
                                      headers=self._headers, timeout=30)
            else:
                raise ValueError(f"Unsupported HTTP method: {method}")

            self.service_stats["successful_calls"] += 1

            # Apply data quality audit to responses
            data_audit_target = {
                "component": "lazylibrarian_service",
                "action": "process_response",
                "response_code": response.status_code,
                "response_size": len(response.text)
            }
            data_findings = self.audit_framework.apply_lens(AuditLens.DATA_QUALITY_INTEGRITY, data_audit_target)

            if response.status_code == 200:
                return response.json()
            else:
                raise ValueError(f"API call failed: HTTP {response.status_code} - {response.text}")

        except Exception as e:
            self.service_stats["failed_calls"] += 1
            raise Exception(f"LazyLibrarian API error: {str(e)}")

    async def search_audiobooks(self, query: str, max_results: int = 10) -> List[AudiobookResult]:
        """Search for audiobooks using real LazyLibrarian API"""

        # Apply performance efficiency audit
        audit_target = {
            "component": "lazylibrarian_service",
            "action": "search_audiobooks",
            "query": query,
            "max_results": max_results
        }
        perf_findings = self.audit_framework.apply_lens(AuditLens.PERFORMANCE_EFFICIENCY, audit_target)

        try:
            # Real LazyLibrarian search API
            params = {
                "searchterm": query,
                "limit": max_results
            }

            search_results = self._make_authenticated_request("api/search", "GET", params)

            # Parse results into AudiobookResult objects
            audiobooks = []
            if "books" in search_results and search_results["books"]:
                for book_data in search_results["books"][:max_results]:
                    audiobook = AudiobookResult(
                        bookid=book_data.get("bookid", ""),
                        title=book_data.get("title", ""),
                        author=book_data.get("author", ""),
                        pubdate=book_data.get("pubdate"),
                        isbn=book_data.get("isbn"),
                        coverurl=book_data.get("coverurl"),
                        summary=book_data.get("summary"),
                        genres=book_data.get("genres"),
                        series=book_data.get("series"),
                        seriesnum=book_data.get("seriesnum"),
                        downloadurl=book_data.get("downloadurl")
                    )
                    audiobooks.append(audiobook)

            # Apply observability audit to search results
            obs_audit_target = {
                "component": "lazylibrarian_service",
                "action": "search_results",
                "query": query,
                "results_count": len(audiobooks),
                "max_results": max_results
            }
            obs_findings = self.audit_framework.apply_lens(AuditLens.OBSERVABILITY_FEEDBACK, obs_audit_target)

            print(f"✅ Found {len(audiobooks)} audiobooks for: '{query}'")
            return audiobooks

        except Exception as e:
            print(f"❌ Search failed: {e}")
            return []

    async def get_book_details(self, book_id: str) -> Optional[AudiobookResult]:
        """Get detailed information about specific audiobook"""

        try:
            # Real LazyLibrarian book details API
            params = {
                "id": book_id
            }

            book_data = self._make_authenticated_request("api/book", "GET", params)

            if book_data and "book" in book_data:
                book = book_data["book"]
                audiobook = AudiobookResult(
                    bookid=book.get("bookid", book_id),
                    title=book.get("title", ""),
                    author=book.get("author", ""),
                    pubdate=book.get("pubdate"),
                    isbn=book.get("isbn"),
                    coverurl=book.get("coverurl"),
                    summary=book.get("summary"),
                    genres=book.get("genres"),
                    series=book.get("series"),
                    seriesnum=book.get("seriesnum"),
                    status=book.get("status", "available"),
                    downloadurl=book.get("downloadurl")
                )
                return audiobook

            print(f"⚠️  No details found for book: {book_id}")
            return None

        except Exception as e:
            print(f"❌ Failed to get book details: {e}")
            return None

    async def request_download(self, book_id: str) -> bool:
        """Request LazyLibrarian to download a specific audiobook"""

        # Apply ethics and compliance audit to download requests
        audit_target = {
            "component": "lazylibrarian_service",
            "action": "request_download",
            "book_id": book_id
        }
        ethics_findings = self.audit_framework.apply_lens(AuditLens.ETHICS_COMPLIANCE, audit_target)

        try:
            # Real LazyLibrarian download API
            download_params = {
                "id": book_id
            }

            response = self._make_authenticated_request("api/download", "POST", download_params)

            success = response.get("success", False)
            message = response.get("message", "Download requested")

            if success:
                print(f"✅ Download requested for book: {book_id}")
                print(f"   Message: {message}")
            else:
                print(f"❌ Download request failed for book: {book_id}")
                print(f"   Message: {message}")

            return success

        except Exception as e:
            print(f"❌ Download request error: {e}")
            return False

    async def get_download_status(self, book_id: str) -> Dict[str, Any]:
        """Check download status of a specific audiobook"""

        try:
            # Real LazyLibrarian status API
            params = {
                "id": book_id
            }

            status_data = self._make_authenticated_request("api/status", "GET", params)

            status_info = {
                "book_id": book_id,
                "status": status_data.get("status", "unknown"),
                "progress": status_data.get("progress", 0),
                "message": status_data.get("message", "Status retrieved"),
                "last_updated": datetime.utcnow().isoformat()
            }

            print(f"📊 Download status for {book_id}: {status_info['status']} ({status_info['progress']}%)")
            return status_info

        except Exception as e:
            print(f"❌ Failed to get download status: {e}")
            return {
                "book_id": book_id,
                "status": "error",
                "progress": 0,
                "message": str(e),
                "last_updated": datetime.utcnow().isoformat()
            }

    async def get_library_stats(self) -> Dict[str, Any]:
        """Get comprehensive library statistics"""

        try:
            # Real LazyLibrarian stats API
            stats_data = self._make_authenticated_request("api/stats", "GET")

            library_stats = {
                "total_books": stats_data.get("total_books", 0),
                "total_authors": stats_data.get("total_authors", 0),
                "total_series": stats_data.get("total_series", 0),
                "books_downloaded": stats_data.get("books_downloaded", 0),
                "books_wanted": stats_data.get("books_wanted", 0),
                "books_pending": stats_data.get("books_pending", 0),
                "discord_bot_requests_served": stats_data.get("discord_requests", 0),
                "last_updated": datetime.utcnow().isoformat()
            }

            print("📚 Library Statistics:")
            print(f"   Books: {library_stats['total_books']}")
            print(f"   Downloaded: {library_stats['books_downloaded']}")
            print(f"   Pending: {library_stats['books_pending']}")

            return library_stats

        except Exception as e:
            print(f"❌ Failed to get library stats: {e}")
            return {
                "error": str(e),
                "total_books": 0,
                "last_updated": datetime.utcnow().isoformat()
            }

    async def check_service_health(self) -> HealthCheckResult:
        """Perform comprehensive health check of LazyLibrarian service"""

        audit_target = {
            "component": "lazylibrarian_service",
            "action": "health_check"
        }
        reliability_findings = self.audit_framework.apply_lens(AuditLens.RELIABILITY_CONTINUITY, audit_target)

        result = HealthCheckResult(
            check_id=f"health_lazylibrarian_{int(datetime.utcnow().timestamp())}",
            service_name="lazylibrarian",
            check_type="http_api",
            endpoint="/api?t=ping"
        )

        try:
            # Test LazyLibrarian connectivity with ping
            start_time = datetime.utcnow()
            ping_response = self._make_authenticated_request("t=ping", "GET")
            response_time = int((datetime.utcnow() - start_time).total_seconds() * 1000)

            result.record_success(
                response_time_ms=response_time,
                details={
                    "api_reachable": True,
                    "api_response": bool(ping_response),
                    "service_stats": self.service_stats
                }
            )

            self.service_stats["last_health_check"] = datetime.utcnow()
            self.service_stats["service_state"] = "healthy"

            return result

        except Exception as e:
            result.record_failure(f"LazyLibrarian health check failed: {str(e)}")
            self.service_stats["service_state"] = "unhealthy"
            self.service_stats["last_health_check"] = datetime.utcnow()
            return result

    def get_service_info(self) -> Dict[str, Any]:
        """Get comprehensive service information"""

        governance_audit_target = {
            "component": "lazylibrarian_service",
            "action": "service_info"
        }
        governance_findings = self.audit_framework.apply_lens(AuditLens.GOVERNANCE_MANAGEMENT, governance_audit_target)

        return {
            "service_name": "lazylibrarian",
            "type": "audiobook_management",
            "description": "LazyLibrarian audiobook search and acquisition service",
            "base_url": self._get_url_pattern(self.base_url),
            "api_key_configured": bool(self.api_key),
            "service_stats": self.service_stats,
            "audit_findings_count": len(governance_findings) if governance_findings else 0,
            "last_updated": datetime.utcnow().isoformat()
        }


# REST API endpoint handlers for orchestration integration
async def handle_audiobook_search(query: str, max_results: int = 10) -> Dict[str, Any]:
    """REST API handler for audiobook search"""

    try:
        service = LazyLibrarianService()
        results = await service.search_audiobooks(query, max_results)

        return {
            "success": True,
            "service": "lazylibrarian",
            "query": query,
            "total_results": len(results),
            "audiobooks": [asdict(result) for result in results]
        }

    except Exception as e:
        return {
            "success": False,
            "service": "lazylibrarian",
            "query": query,
            "error": str(e)
        }

async def handle_book_download(book_id: str) -> Dict[str, Any]:
    """REST API handler for audiobook download"""

    try:
        service = LazyLibrarianService()
        success = await service.request_download(book_id)

        return {
            "success": success,
            "service": "lazylibrarian",
            "book_id": book_id,
            "message": "Download request submitted"
        }

    except Exception as e:
        return {
            "success": False,
            "service": "lazylibrarian",
            "book_id": book_id,
            "error": str(e)
        }

async def handle_library_stats() -> Dict[str, Any]:
    """REST API handler for library statistics"""

    try:
        service = LazyLibrarianService()
        stats = await service.get_library_stats()

        return {
            "success": True,
            "service": "lazylibrarian",
            "library_stats": stats
        }

    except Exception as e:
        return {
            "success": False,
            "service": "lazylibrarian",
            "error": str(e)
        }

# Service registry for orchestration
lazylibrarian_service = None

def get_service():
    """Get singleton service instance"""
    global lazylibrarian_service
    if lazylibrarian_service is None:
        lazylibrarian_service = LazyLibrarianService()
    return lazylibrarian_service

# Test script
async def test_service():
    """Test the LazyLibrarian service functionality"""

    print("🧪 Testing LazyLibrarian Service...")
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
        print("25")

    # Test 3: Library stats (if service is running)
    if health_result.status == HealthStatus.HEALTHY:
        print("\n3. Testing Library Stats:")
        try:
            stats = await service.get_library_stats()
            print(f"   Total books: {stats.get('total_books', 'N/A')}")
        except Exception as e:
            print(f"   Error (expected if no LazyLibrarian running): {e}")

    print("\n✅ LazyLibrarian Service test completed!")
    print("🔗 Ready for integration with orchestration engine")

if __name__ == "__main__":
    asyncio.run(test_service())
