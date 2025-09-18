#!/usr/bin/env python3
"""
BookFairy qBittorrent Service Integration
Implements real torrent download management and monitoring
Based on qBittorrent Web API specification
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
class TorrentInfo:
    """qBittorrent torrent information structure"""
    hash: str
    name: str
    size: int
    progress: float
    status: str
    download_speed: int
    upload_speed: int
    eta: Optional[int] = None
    ratio: float = 0.0
    added_on: Optional[int] = None
    completion_date: Optional[int] = None
    category: Optional[str] = None
    download_path: Optional[str] = None
    content_path: Optional[str] = None
    state: Optional[str] = None
    seeds: int = 0
    leechers: int = 0
    total_seeds: int = 0
    total_leechers: int = 0


@dataclass
class DownloadStats:
    """qBittorrent system statistics"""
    downloaded_bytes: int
    uploaded_bytes: int
    global_ratio: float
    session_downloaded_bytes: int
    session_uploaded_bytes: int
    session_ratio: float
    active_torrents: int
    total_torrents: int
    read_cache_hits: float
    read_cache_overload: int
    write_queue_overload: int
    queued_io_jobs: int
    average_time_queue: int
    total_buffering_queues: int


class QBittorrentService:
    """Real qBittorrent Web API integration service"""

    def __init__(self):
        self.base_url = os.getenv("QBITTORRENT_URL", "http://localhost:8081")
        self.username = os.getenv("QBITTORRENT_USERNAME", "admin")
        self.password = os.getenv("QBITTORRENT_PASSWORD", "")
        self._session = requests.Session()
        self._authenticated = False

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
        self._authenticate()
        print(f"QBittorrentService initialized - Connected: {self._authenticated}")

    def _audit_service_initialization(self):
        """Apply governance audit to service initialization"""
        audit_target = {
            "component": "qbittorrent_service",
            "action": "service_initialization",
            "configuration": {
                "has_url": bool(self.base_url),
                "has_credentials": bool(self.username and self.password),
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
                    print("   → Please verify qBittorrent security configuration")
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

    def _authenticate(self):
        """Authenticate with qBittorrent Web API"""
        if not self.password:
            print("❌ qBittorrent password not configured")
            return False

        try:
            auth_data = {
                'username': self.username,
                'password': self.password
            }

            auth_url = f"{self.base_url}/api/v2/auth/login"
            response = self._session.post(auth_url, data=auth_data, timeout=30)

            # qBittorrent doesn't return JSON on successful login, just a cookie
            if response.status_code == 200 and 'SID' in self._session.cookies:
                self._authenticated = True
                print("✅ Successfully authenticated with qBittorrent")
                return True
            else:
                print(f"❌ qBittorrent authentication failed: {response.status_code}")
                return False

        except Exception as e:
            print(f"❌ Authentication error: {e}")
            return False

    def _make_authenticated_request(self, endpoint: str, method: str = "GET",
                                   params: Optional[Dict] = None,
                                   data: Optional[Dict] = None) -> Dict[str, Any]:
        """Make authenticated API request to qBittorrent"""

        if not self._authenticated:
            if not self._authenticate():
                raise Exception("Not authenticated with qBittorrent")

        # Apply security audit to each API call
        audit_target = {
            "component": "qbittorrent_service",
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
                response = self._session.post(url, params=params, data=data, timeout=30)
            elif method == "GET":
                response = self._session.get(url, params=params, timeout=30)
            elif method == "PATCH":
                response = self._session.patch(url, params=params, data=data, timeout=30)
            elif method == "DELETE":
                response = self._session.delete(url, params=params, timeout=30)
            else:
                raise ValueError(f"Unsupported HTTP method: {method}")

            self.service_stats["successful_calls"] += 1

            # Apply data quality audit to responses
            data_audit_target = {
                "component": "qbittorrent_service",
                "action": "process_response",
                "response_code": response.status_code,
                "response_size": len(response.text)
            }
            data_findings = self.audit_framework.apply_lens(AuditLens.DATA_QUALITY_INTEGRITY, data_audit_target)

            if response.status_code == 200:
                # qBittorrent returns JSON for most endpoints
                if response.headers.get('Content-Type', '').startswith('application/json'):
                    return response.json()
                else:
                    return {"content": response.text}
            else:
                raise ValueError(f"API call failed: HTTP {response.status_code} - {response.text[:200]}")

        except Exception as e:
            self.service_stats["failed_calls"] += 1
            raise Exception(f"QBittorrent API error: {str(e)}")

    async def add_torrent(self, torrent_url: str, torrent_category: str = "audiobooks",
                         download_path: Optional[str] = None) -> str:
        """Add a torrent to qBittorrent for download"""

        # Apply ethics and compliance audit for download requests
        audit_target = {
            "component": "qbittorrent_service",
            "action": "add_torrent",
            "torrent_url": torrent_url,
            "category": torrent_category,
            "has_custom_path": bool(download_path)
        }
        ethics_findings = self.audit_framework.apply_lens(AuditLens.ETHICS_COMPLIANCE, audit_target)

        try:
            endpoint = "/api/v2/torrents/add"

            # Prepare parameters for adding torrent
            params = {
                'urls': torrent_url,
                'category': torrent_category,
                'contentLayout': 'Original',  # Preserves file structure
                'autoTMM': False  # Manual torrent management
            }

            if download_path:
                params['downloadPath'] = download_path

            response = self._make_authenticated_request(endpoint, "POST", None, params)

            success = response.get("success", False)
            if success:
                # Get the torrent hash/list to track it
                recent_torrents = await self.get_torrents(limit=5)
                torrent_hash = recent_torrents[0].hash if recent_torrents else None

                print(f"✅ Torrent added successfully: {torrent_url}")
                print(f"   Category: {torrent_category}")
                print(f"   Hash: {torrent_hash}")

                return torrent_hash
            else:
                print(f"❌ Failed to add torrent: {response.get('error', 'Unknown error')}")
                return ""

        except Exception as e:
            print(f"❌ Add torrent error: {e}")
            return ""

    async def get_torrents(self, category: Optional[str] = None, limit: int = 100) -> List[TorrentInfo]:
        """Get list of torrents from qBittorrent"""

        try:
            endpoint = "/api/v2/torrents/info"

            params = {'limit': limit}
            if category:
                params['category'] = category

            torrent_data = self._make_authenticated_request(endpoint, "GET", params)

            # Parse torrent list
            torrents = []
            for torrent in torrent_data[:limit]:
                torrent_info = TorrentInfo(
                    hash=torrent.get("hash", ""),
                    name=torrent.get("name", ""),
                    size=torrent.get("size", 0),
                    progress=torrent.get("progress", 0.0),
                    status=torrent.get("state", ""),
                    download_speed=torrent.get("dlspeed", 0),
                    upload_speed=torrent.get("upspeed", 0),
                    eta=torrent.get("eta"),
                    ratio=torrent.get("ratio", 0.0),
                    added_on=torrent.get("added_on"),
                    completion_date=torrent.get("completion_date"),
                    category=torrent.get("category"),
                    download_path=torrent.get("download_path"),
                    content_path=torrent.get("content_path"),
                    seeds=torrent.get("num_seeds", 0),
                    leechers=torrent.get("num_leechs", 0),
                    total_seeds=torrent.get("num_complete", 0),
                    total_leechers=torrent.get("num_incomplete", 0)
                )
                torrents.append(torrent_info)

            return torrents

        except Exception as e:
            print(f"❌ Get torrents error: {e}")
            return []

    async def get_torrent_info(self, torrent_hash: str) -> Optional[TorrentInfo]:
        """Get detailed information about a specific torrent"""

        try:
            endpoint = "/api/v2/torrents/info"

            params = {'hashes': torrent_hash}

            torrent_data = self._make_authenticated_request(endpoint, "GET", params)

            if torrent_data:
                torrent = torrent_data[0]  # Only one result expected
                torrent_info = TorrentInfo(
                    hash=torrent_hash,
                    name=torrent.get("name", ""),
                    size=torrent.get("size", 0),
                    progress=torrent.get("progress", 0.0),
                    status=torrent.get("state", ""),
                    download_speed=torrent.get("dlspeed", 0),
                    upload_speed=torrent.get("upspeed", 0),
                    eta=torrent.get("eta"),
                    ratio=torrent.get("ratio", 0.0),
                    added_on=torrent.get("added_on"),
                    completion_date=torrent.get("completion_date"),
                    category=torrent.get("category"),
                    download_path=torrent.get("download_path"),
                    content_path=torrent.get("content_path")
                )
                return torrent_info

            print(f"⚠️  No torrent found with hash: {torrent_hash}")
            return None

        except Exception as e:
            print(f"❌ Get torrent info error: {e}")
            return None

    async def pause_torrent(self, torrent_hash: str) -> bool:
        """Pause a torrent download"""

        try:
            endpoint = "/api/v2/torrents/pause"
            params = {'hashes': torrent_hash}

            response = self._make_authenticated_request(endpoint, "POST", None, params)

            success = response.get("success", False)
            if success:
                print(f"✅ Torrent paused: {torrent_hash}")
            else:
                print(f"❌ Failed to pause torrent: {torrent_hash}")

            return success

        except Exception as e:
            print(f"❌ Pause torrent error: {e}")
            return False

    async def resume_torrent(self, torrent_hash: str) -> bool:
        """Resume a paused torrent"""

        try:
            endpoint = "/api/v2/torrents/resume"
            params = {'hashes': torrent_hash}

            response = self._make_authenticated_request(endpoint, "POST", None, params)

            success = response.get("success", False)
            if success:
                print(f"✅ Torrent resumed: {torrent_hash}")
            else:
                print(f"❌ Failed to resume torrent: {torrent_hash}")

            return success

        except Exception as e:
            print(f"❌ Resume torrent error: {e}")
            return False

    async def delete_torrent(self, torrent_hash: str, delete_files: bool = False) -> bool:
        """Delete a torrent and optionally its files"""

        # Apply data management audit for file deletion
        audit_target = {
            "component": "qbittorrent_service",
            "action": "delete_torrent",
            "torrent_hash": torrent_hash,
            "delete_files": delete_files
        }
        data_audit_target = self.audit_framework.apply_lens(AuditLens.DATA_QUALITY_INTEGRITY, audit_target)

        try:
            endpoint = "/api/v2/torrents/delete"
            params = {
                'hashes': torrent_hash,
                'deleteFiles': str(delete_files).lower()
            }

            response = self._make_authenticated_request(endpoint, "POST", None, params)

            success = response.get("success", False)
            if success:
                print(f"✅ Torrent deleted: {torrent_hash} (files: {delete_files})")
            else:
                print(f"❌ Failed to delete torrent: {torrent_hash}")

            return success

        except Exception as e:
            print(f"❌ Delete torrent error: {e}")
            return False

    async def get_global_stats(self) -> DownloadStats:
        """Get qBittorrent global transfer statistics"""

        try:
            endpoint = "/api/v2/transfer/info"

            stats_data = self._make_authenticated_request(endpoint, "GET")

            global_stats = DownloadStats(
                downloaded_bytes=stats_data.get("dl_info_data", 0),
                uploaded_bytes=stats_data.get("up_info_data", 0),
                global_ratio=stats_data.get("global_ratio", 0.0),
                session_downloaded_bytes=stats_data.get("dl_rate", 0),
                session_uploaded_bytes=stats_data.get("up_rate", 0),
                session_ratio=0.0,  # Not directly available
                active_torrents=stats_data.get("dl_limiting_num", 0),
                total_torrents=stats_data.get("dl_num", 0),
                read_cache_hits=0.0,  # Not in basic API
                read_cache_overload=0,
                write_queue_overload=0,
                queued_io_jobs=0,
                average_time_queue=0,
                total_buffering_queues=0
            )

            print("📊 qBittorrent Global Stats:")
            print(f"   Active Downloads: {global_stats.active_torrents}")
            print(f"   Download Speed: {global_stats.session_downloaded_bytes:,} bytes/s")
            print(f"   Ratio: {global_stats.global_ratio:.3f}")

            return global_stats

        except Exception as e:
            print(f"❌ Get global stats error: {e}")
            return DownloadStats(
                downloaded_bytes=0,
                uploaded_bytes=0,
                global_ratio=0.0,
                session_downloaded_bytes=0,
                session_uploaded_bytes=0,
                session_ratio=0.0,
                active_torrents=0,
                total_torrents=0,
                read_cache_hits=0.0,
                read_cache_overload=0,
                write_queue_overload=0,
                queued_io_jobs=0,
                average_time_queue=0,
                total_buffering_queues=0
            )

    async def get_audiobook_torrents(self) -> List[TorrentInfo]:
        """Get all audiobook-related torrents"""

        try:
            # Get all torrents and filter by audiobook category
            all_torrents = await self.get_torrents(limit=200)

            # Filter for audiobook-related torrents
            audiobook_torrents = []
            for torrent in all_torrents:
                # Check if it's in audiobook category or contains audiobook-related keywords
                if (
                    torrent.category and "audiobook" in torrent.category.lower()
                ) or (
                    any(keyword in torrent.name.lower()
                        for keyword in ["audiobook", "audio book", ".m4b", ".mp3"])
                ):
                    audiobook_torrents.append(torrent)

            print(f"📚 Found {len(audiobook_torrents)} audiobook torrent(s)")
            return audiobook_torrents

        except Exception as e:
            print(f"❌ Get audiobook torrents error: {e}")
            return []

    async def check_service_health(self) -> HealthCheckResult:
        """Perform comprehensive qBittorrent health check"""

        audit_target = {
            "component": "qbittorrent_service",
            "action": "health_check"
        }
        reliability_findings = self.audit_framework.apply_lens(AuditLens.RELIABILITY_CONTINUITY, audit_target)

        result = HealthCheckResult(
            check_id=f"health_qbittorrent_{int(datetime.utcnow().timestamp())}",
            service_name="qbittorrent",
            check_type="http_api",
            endpoint="/api/v2/transfer/info"
        )

        try:
            start_time = datetime.utcnow()

            # Test qBittorrent connectivity by getting transfer info
            transfer_info = self._make_authenticated_request("/api/v2/transfer/info", "GET")
            response_time = int((datetime.utcnow() - start_time).total_seconds() * 1000)

            result.record_success(
                response_time_ms=response_time,
                details={
                    "api_reachable": True,
                    "transfer_info_available": bool(transfer_info),
                    "auth_working": self._authenticated,
                    "service_stats": self.service_stats
                }
            )

            self.service_stats["last_health_check"] = datetime.utcnow()
            self.service_stats["service_state"] = "healthy"

            return result

        except Exception as e:
            result.record_failure(f"QBittorrent health check failed: {str(e)}")
            self.service_stats["service_state"] = "unhealthy"
            self.service_stats["last_health_check"] = datetime.utcnow()
            return result

    def get_service_info(self) -> Dict[str, Any]:
        """Get comprehensive qBittorrent service information"""

        governance_audit_target = {
            "component": "qbittorrent_service",
            "action": "service_info"
        }
        governance_findings = self.audit_framework.apply_lens(AuditLens.GOVERNANCE_MANAGEMENT, governance_audit_target)

        return {
            "service_name": "qbittorrent",
            "type": "torrent_download",
            "description": "qBittorrent torrent download and management service",
            "base_url": self._get_url_pattern(self.base_url),
            "authenticated": self._authenticated,
            "service_stats": self.service_stats,
            "audit_findings_count": len(governance_findings) if governance_findings else 0,
            "last_updated": datetime.utcnow().isoformat()
        }


# REST API endpoint handlers for orchestration integration
async def handle_add_torrent(torrent_url: str, category: str = "audiobooks",
                           download_path: Optional[str] = None) -> Dict[str, Any]:
    """REST API handler for adding torrents"""

    try:
        service = QBittorrentService()
        torrent_hash = await service.add_torrent(torrent_url, category, download_path)

        return {
            "success": bool(torrent_hash),
            "service": "qbittorrent",
            "torrent_url": torrent_url,
            "torrent_hash": torrent_hash,
            "category": category,
            "download_path": download_path
        }

    except Exception as e:
        return {
            "success": False,
            "service": "qbittorrent",
            "torrent_url": torrent_url,
            "category": category,
            "error": str(e)
        }

async def handle_torrent_status(torrent_hash: str) -> Dict[str, Any]:
    """REST API handler for torrent status"""

    try:
        service = QBittorrentService()
        torrent_info = await service.get_torrent_info(torrent_hash)

        if torrent_info:
            return {
                "success": True,
                "service": "qbittorrent",
                "torrent": asdict(torrent_info)
            }
        else:
            return {
                "success": False,
                "service": "qbittorrent",
                "torrent_hash": torrent_hash,
                "error": "Torrent not found"
            }

    except Exception as e:
        return {
            "success": False,
            "service": "qbittorrent",
            "torrent_hash": torrent_hash,
            "error": str(e)
        }

async def handle_download_stats() -> Dict[str, Any]:
    """REST API handler for download statistics"""

    try:
        service = QBittorrentService()
        stats = await service.get_global_stats()

        return {
            "success": True,
            "service": "qbittorrent",
            "download_stats": asdict(stats)
        }

    except Exception as e:
        return {
            "success": False,
            "service": "qbittorrent",
            "error": str(e)
        }

async def handle_audiobook_torrents() -> Dict[str, Any]:
    """REST API handler for audiobook torrents"""

    try:
        service = QBittorrentService()
        audiobooks = await service.get_audiobook_torrents()

        return {
            "success": True,
            "service": "qbittorrent",
            "total_audiobooks": len(audiobooks),
            "audiobooks": [asdict(audiobook) for audiobook in audiobooks]
        }

    except Exception as e:
        return {
            "success": False,
            "service": "qbittorrent",
            "error": str(e)
        }

# Service registry for orchestration
qbittorrent_service = None

def get_service():
    """Get singleton service instance"""
    global qbittorrent_service
    if qbittorrent_service is None:
        qbittorrent_service = QBittorrentService()
    return qbittorrent_service

# Test script
async def test_service():
    """Test the qBittorrent service functionality"""

    print("🧪 Testing qBittorrent Service...")
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
        print("\n3. Testing Download Statistics:")
        try:
            stats = await service.get_global_stats()
            print(f"   Active downloads: {stats.active_torrents}")
            print(f"   Total torrents: {stats.total_torrents}")
        except Exception as e:
            print(f"   Error (expected if no qBittorrent running): {e}")

    print("\n✅ qBittorrent Service test completed!")
    print("🔗 Ready for integration with orchestration engine")

if __name__ == "__main__":
    asyncio.run(test_service())
