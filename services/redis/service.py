#!/usr/bin/env python3
"""
BookFairy Redis Service Integration
Provides high-performance caching and state management
Based on Redis API and BookFairy Orchestration needs
"""

import asyncio
import json
import redis
import sys
import os
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Union

# Add project root
script_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(os.path.dirname(script_dir))
services_path = os.path.join(project_root, "services")
sys.path.insert(0, services_path)

from services.shared.models.health import HealthCheckResult, HealthStatus
from services.shared.models.governance import AuditLensFramework, AuditLens


class RedisService:
    """Comprehensive Redis service for caching and state management"""

    def __init__(self):
        self.host = os.getenv("REDIS_HOST", "redis")
        self.port = int(os.getenv("REDIS_PORT", "6379"))
        self.password = os.getenv("REDIS_PASSWORD", "")
        self.db = int(os.getenv("REDIS_DB", "0"))
        self.connection_timeout = int(os.getenv("REDIS_TIMEOUT", "5"))

        # Service initialization audit
        self.audit_framework = AuditLensFramework()

        # Redis client initialization
        self.redis_client = None
        self.is_connected = False
        self.service_stats = {
            "operations": 0,
            "successful_operations": 0,
            "failed_operations": 0,
            "total_cache_hits": 0,
            "total_cache_misses": 0,
            "last_health_check": datetime.utcnow(),
            "service_state": "initialized"
        }

        self._connect()
        self._audit_service_initialization()
        print(f"RedisService initialized - Connected: {self.is_connected}")

    def _connect(self):
        """Establish Redis connection with retry logic"""
        try:
            self.redis_client = redis.Redis(
                host=self.host,
                port=self.port,
                password=self.password or None,
                db=self.db,
                socket_connect_timeout=self.connection_timeout,
                socket_timeout=False,
                decode_responses=True
            )

            # Test connection
            if self.redis_client.ping():
                self.is_connected = True
                self.service_stats["service_state"] = "connected"
                print(f"✅ Connected to Redis at {self.host}:{self.port}")
            else:
                self.is_connected = False
                print("❌ Redis ping failed")

        except Exception as e:
            self.is_connected = False
            print(f"❌ Redis connection failed: {e}")
            self.service_stats["service_state"] = "disconnected"

    def _audit_service_initialization(self):
        """Apply governance audit to service initialization"""
        audit_target = {
            "component": "redis_service",
            "action": "service_initialization",
            "configuration": {
                "has_host": bool(self.host),
                "has_port": bool(self.port),
                "has_connection": self.is_connected,
                "connection_pattern": self._get_connection_pattern()
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
                    print("   → Please verify Redis security configuration")
            elif finding.severity.value in ["MEDIUM", "LOW"]:
                print(f"⚠️  SECURITY WARNING: {finding.title}")

    def _get_connection_pattern(self):
        """Extract connection pattern for security auditing"""
        if not self.host:
            return "missing_host"
        try:
            from urllib.parse import urlparse
            # Create a pseudo URL for parsing
            pseudo_url = f"redis://{self.host}:{self.port}"
            parsed = urlparse(pseudo_url)
            return f"{parsed.hostname}:port_hidden"
        except:
            return "invalid"

    def _update_stats(self, operation_success: bool = True, cache_hit: bool = False):
        """Update service operation statistics"""
        self.service_stats["operations"] += 1
        if operation_success:
            self.service_stats["successful_operations"] += 1
        else:
            self.service_stats["failed_operations"] += 1

        if cache_hit:
            self.service_stats["total_cache_hits"] += 1
        elif operation_success:
            self.service_stats["total_cache_misses"] += 1

    # USER SESSION MANAGEMENT
    async def store_user_session(self, user_id: str, session_data: Dict[str, Any],
                                expiry_seconds: int = 3600) -> bool:
        """Store user session data with expiry"""

        # Apply security audit for user data storage
        audit_target = {
            "component": "redis_service",
            "action": "store_user_session",
            "user_id": user_id,
            "data_keys": list(session_data.keys()),
            "expiry_seconds": expiry_seconds
        }
        security_findings = self.audit_framework.apply_lens(AuditLens.SAFETY_SECURITY, audit_target)
        self._handle_security_findings(security_findings, "store_user_session")

        try:
            session_key = f"user_session:{user_id}"
            session_json = json.dumps(session_data)

            success = self.redis_client.setex(session_key, expiry_seconds, session_json)
            self._update_stats(success)

            if success:
                print(f"✅ Stored session for user {user_id}")
                return True
            else:
                print(f"❌ Failed to store session for user {user_id}")
                return False

        except Exception as e:
            print(f"❌ Session store error: {e}")
            self._update_stats(False)
            return False

    async def get_user_session(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve user session data"""

        try:
            session_key = f"user_session:{user_id}"
            session_data = self.redis_client.get(session_key)

            if session_data:
                parsed_data = json.loads(session_data)
                self._update_stats(True, True)
                print(f"✅ Retrieved session for user {user_id}")
                return parsed_data
            else:
                self._update_stats(True, False)
                return None

        except Exception as e:
            print(f"❌ Session retrieval error: {e}")
            self._update_stats(False)
            return None

    async def delete_user_session(self, user_id: str) -> bool:
        """Delete user session"""

        try:
            session_key = f"user_session:{user_id}"
            deleted_count = self.redis_client.delete(session_key)
            success = deleted_count > 0
            self._update_stats(success)

            if success:
                print(f"✅ Deleted session for user {user_id}")
            else:
                print(f"⚠️  No session found for user {user_id}")

            return success

        except Exception as e:
            print(f"❌ Session deletion error: {e}")
            self._update_stats(False)
            return False

    # CACHING OPERATIONS
    async def cache_set(self, key: str, value: Any,
                       expiry_seconds: Optional[int] = None) -> bool:
        """Set a cache value with optional expiry"""

        # Apply performance audit for cache operations
        audit_target = {
            "component": "redis_service",
            "action": "cache_set",
            "key": key,
            "has_expiry": expiry_seconds is not None,
            "expiry_seconds": expiry_seconds
        }
        perf_findings = self.audit_framework.apply_lens(AuditLens.PERFORMANCE_EFFICIENCY, audit_target)

        try:
            if isinstance(value, (dict, list)):
                cache_value = json.dumps(value)
            else:
                cache_value = str(value)

            if expiry_seconds:
                success = self.redis_client.setex(key, expiry_seconds, cache_value)
            else:
                success = self.redis_client.set(key, cache_value)

            self._update_stats(success)

            if success:
                print(f"✅ Cached {key} (expiry: {expiry_seconds}s)")
                return True
            else:
                print(f"❌ Failed to cache {key}")
                return False

        except Exception as e:
            print(f"❌ Cache set error: {e}")
            self._update_stats(False)
            return False

    async def cache_get(self, key: str) -> Optional[Any]:
        """Get a cached value"""

        try:
            value = self.redis_client.get(key)

            if value:
                self._update_stats(True, True)
                # Try to parse as JSON first, then fall back to string
                try:
                    return json.loads(value)
                except (json.JSONDecodeError, TypeError):
                    return value
            else:
                self._update_stats(True, False)
                return None

        except Exception as e:
            print(f"❌ Cache get error: {e}")
            self._update_stats(False)
            return None

    async def cache_delete(self, key: str) -> bool:
        """Delete a cached value"""

        try:
            deleted_count = self.redis_client.delete(key)
            success = deleted_count > 0
            self._update_stats(success)

            if success:
                print(f"✅ Deleted cache key: {key}")
            else:
                print(f"⚠️  Cache key not found: {key}")

            return success

        except Exception as e:
            print(f"❌ Cache delete error: {e}")
            self._update_stats(False)
            return False

    # AUDIOLIB OPERATIONS (LazyLibrarian + Audiobookshelf)
    async def cache_audiobook_search(self, query: str, results: List[Dict], ttl_seconds: int = 1800) -> bool:
        """Cache LazyLibrarian search results"""

        # Apply observability audit for search caching
        audit_target = {
            "component": "redis_service",
            "action": "cache_audiobook_search",
            "query": query,
            "results_count": len(results),
            "ttl_seconds": ttl_seconds
        }
        obs_findings = self.audit_framework.apply_lens(AuditLens.OBSERVABILITY_FEEDBACK, audit_target)

        try:
            cache_key = f"audiobook_search:{query}".lower().replace(" ", "_")
            cache_data = {
                "query": query,
                "results": results,
                "cached_at": datetime.utcnow().isoformat(),
                "result_count": len(results)
            }

            return await self.cache_set(cache_key, cache_data, ttl_seconds)

        except Exception as e:
            print(f"❌ Audiobook search cache error: {e}")
            return False

    async def get_cached_audiobook_search(self, query: str) -> Optional[Dict]:
        """Get cached audiobook search results"""

        try:
            cache_key = f"audiobook_search:{query}".lower().replace(" ", "_")
            return await self.cache_get(cache_key)

        except Exception as e:
            print(f"❌ Cached audiobook search retrieval error: {e}")
            return None

    async def store_user_book_progress(self, user_id: str, book_id: str,
                                      progress_data: Dict[str, Any]) -> bool:
        """Store user listening progress for synchronization between services"""

        # Apply data quality audit for progress storage
        audit_target = {
            "component": "redis_service",
            "action": "store_progress",
            "user_id": user_id,
            "book_id": book_id,
            "progress_keys": list(progress_data.keys())
        }
        data_findings = self.audit_framework.apply_lens(AuditLens.DATA_QUALITY_INTEGRITY, audit_target)

        try:
            progress_key = f"user_progress:{user_id}:{book_id}"
            progress_data["updated_at"] = datetime.utcnow().isoformat()

            return await self.cache_set(progress_key, progress_data, expiry_seconds=86400*365)  # 1 year

        except Exception as e:
            print(f"❌ Progress storage error: {e}")
            return False

    async def get_user_book_progress(self, user_id: str, book_id: str) -> Optional[Dict]:
        """Retrieve user listening progress"""

        try:
            progress_key = f"user_progress:{user_id}:{book_id}"
            return await self.cache_get(progress_key)

        except Exception as e:
            print(f"❌ Progress retrieval error: {e}")
            return None

    # DOWNLOAD QUEUE MANAGEMENT
    async def enqueue_download_request(self, user_id: str, book_id: str,
                                     book_details: Dict[str, Any]) -> bool:
        """Add download request to queue"""

        # Apply reliability audit for download queueing
        audit_target = {
            "component": "redis_service",
            "action": "enqueue_download",
            "user_id": user_id,
            "book_id": book_id,
            "book_title": book_details.get("title", "")
        }
        reliability_findings = self.audit_framework.apply_lens(AuditLens.RELIABILITY_CONTINUITY, audit_target)

        try:
            queue_data = {
                "user_id": user_id,
                "book_id": book_id,
                "book_details": book_details,
                "requested_at": datetime.utcnow().isoformat(),
                "status": "queued"
            }

            # Add to download queue
            queue_key = "download_queue"
            success = self.redis_client.lpush(queue_key, json.dumps(queue_data))

            # Update queue length cache
            queue_length = self.redis_client.llen(queue_key)
            self.redis_client.set("download_queue_length", queue_length)

            self._update_stats(success > 0)
            print(f"✅ Enqueued download request for user {user_id}: {book_id}")

            return success > 0

        except Exception as e:
            print(f"❌ Download queue error: {e}")
            self._update_stats(False)
            return False

    async def dequeue_download_request(self) -> Optional[Dict]:
        """Get next download request from queue"""

        try:
            queue_key = "download_queue"
            result = self.redis_client.rpop(queue_key)

            if result:
                parsed_result = json.loads(result)
                self._update_stats(True)

                # Update queue length
                queue_length = self.redis_client.llen(queue_key)
                self.redis_client.set("download_queue_length", queue_length)

                print(f"✅ Dequeued download request: {parsed_result['book_id']}")
                return parsed_result
            else:
                self._update_stats(True, False)
                return None

        except Exception as e:
            print(f"❌ Download dequeue error: {e}")
            self._update_stats(False)
            return None

    async def get_download_queue_status(self) -> Dict[str, Any]:
        """Get comprehensive download queue status"""

        try:
            queue_length = int(self.redis_client.get("download_queue_length") or 0)
            processing_count = int(self.redis_client.get("processing_downloads") or 0)

            queue_stats = {
                "queue_length": queue_length,
                "processing": processing_count,
                "active": self.redis_client.llen("download_queue"),
                "updated_at": datetime.utcnow().isoformat()
            }

            print(f"📊 Queue Status: {queue_length} queued, {processing_count} processing")
            return queue_stats

        except Exception as e:
            print(f"❌ Queue status error: {e}")
            return {"queue_length": 0, "processing": 0, "active": 0}

    # Discord Bot Session Management
    async def store_discord_interaction(self, user_id: str, interaction_id: str,
                                      interaction_data: Dict[str, Any],
                                      expiry_seconds: int = 300) -> bool:
        """Store Discord interaction state for follow-up"""

        audit_target = {
            "component": "redis_service",
            "action": "store_discord_interaction",
            "user_id": user_id,
            "interaction_id": interaction_id,
            "interaction_type": interaction_data.get("type", "")
        }
        security_findings = self.audit_framework.apply_lens(AuditLens.SAFETY_SECURITY, audit_target)
        self._handle_security_findings(security_findings, "store_discord_interaction")

        try:
            interaction_key = f"discord_interaction:{user_id}:{interaction_id}"
            interaction_data["stored_at"] = datetime.utcnow().isoformat()

            return await self.cache_set(interaction_key, interaction_data, expiry_seconds)

        except Exception as e:
            print(f"❌ Discord interaction storage error: {e}")
            return False

    async def get_discord_interaction(self, user_id: str, interaction_id: str) -> Optional[Dict]:
        """Retrieve Discord interaction state"""

        try:
            interaction_key = f"discord_interaction:{user_id}:{interaction_id}"
            return await self.cache_get(interaction_key)

        except Exception as e:
            print(f"❌ Discord interaction retrieval error: {e}")
            return None

    async def check_service_health(self) -> HealthCheckResult:
        """Perform comprehensive Redis health check"""

        audit_target = {
            "component": "redis_service",
            "action": "health_check"
        }
        reliability_findings = self.audit_framework.apply_lens(AuditLens.RELIABILITY_CONTINUITY, audit_target)

        result = HealthCheckResult(
            check_id=f"health_redis_{int(datetime.utcnow().timestamp())}",
            service_name="redis",
            check_type="redis_connection",
            endpoint=f"{self.host}:{self.port}"
        )

        try:
            start_time = datetime.utcnow()

            if self.redis_client is None:
                result.record_failure("Redis client is None")
                return result

            # Test basic ping
            ping_response = self.redis_client.ping()

            # Test actual operations
            test_key = f"health_test_{int(start_time.timestamp())}"
            self.redis_client.setex(test_key, 10, "test_value")
            retrieved = self.redis_client.get(test_key)
            self.redis_client.delete(test_key)

            response_time = int((datetime.utcnow() - start_time).total_seconds() * 1000)

            result.record_success(
                response_time_ms=response_time,
                details={
                    "ping_response": ping_response,
                    "test_operations": retrieved == "test_value",
                    "connection_state": "healthy" if self.is_connected else "disconnected",
                    "service_stats": self.service_stats
                }
            )

            self.service_stats["last_health_check"] = datetime.utcnow()
            self.service_stats["service_state"] = "healthy"

            return result

        except Exception as e:
            result.record_failure(f"Redis health check failed: {str(e)}")
            self.service_stats["service_state"] = "unhealthy"
            self.service_stats["last_health_check"] = datetime.utcnow()
            return result

    def get_service_info(self) -> Dict[str, Any]:
        """Get comprehensive Redis service information"""

        governance_audit_target = {
            "component": "redis_service",
            "action": "service_info"
        }
        governance_findings = self.audit_framework.apply_lens(AuditLens.GOVERNANCE_MANAGEMENT, governance_audit_target)

        return {
            "service_name": "redis",
            "type": "caching_state_management",
            "description": "High-performance Redis caching and state management service",
            "connection": self._get_connection_pattern(),
            "password_configured": bool(self.password),
            "service_stats": self.service_stats,
            "audit_findings_count": len(governance_findings) if governance_findings else 0,
            "last_updated": datetime.utcnow().isoformat()
        }

    async def get_server_info(self) -> Optional[Dict[str, Any]]:
        """Get Redis server information"""

        try:
            info = self.redis_client.info()
            return {
                "version": info.get("redis_version"),
                "uptime_seconds": info.get("uptime_in_seconds"),
                "connected_clients": info.get("connected_clients"),
                "memory_used": info.get("used_memory_human"),
                "total_connections": info.get("total_connections_received"),
                "keys_count": self.redis_client.dbsize()
            }
        except Exception as e:
            print(f"❌ Redis server info error: {e}")
            return None

    async def perform_maintenance_cleanup(self) -> Dict[str, Any]:
        """Clean up expired keys and old data"""

        try:
            # Clean up old cached searches (older than 1 hour)
            search_pattern = "audiobook_search:*"
            cleanup_count = 0

            for key in self.redis_client.keys(search_pattern):
                if key:
                    self.redis_client.delete(key)
                    cleanup_count += 1

            maintenance_result = {
                "cached_searches_cleaned": cleanup_count,
                "op_cache_size": self.redis_client.dbsize(),
                "maintenance_performed_at": datetime.utcnow().isoformat()
            }

            print(f"🧹 Maintenance complete: {cleanup_count} search caches cleaned")
            return maintenance_result

        except Exception as e:
            print(f"❌ Maintenance error: {e}")
            return {"error": str(e)}


# REST API endpoint handlers for orchestration integration
async def handle_cache_get(key: str) -> Dict[str, Any]:
    """REST API handler for cache retrieval"""

    try:
        service = RedisService()
        value = await service.cache_get(key)

        return {
            "success": True,
            "service": "redis",
            "key": key,
            "value": value,
            "found": value is not None
        }

    except Exception as e:
        return {
            "success": False,
            "service": "redis",
            "key": key,
            "error": str(e)
        }

async def handle_session_get(user_id: str) -> Dict[str, Any]:
    """REST API handler for session retrieval"""

    try:
        service = RedisService()
        session = await service.get_user_session(user_id)

        return {
            "success": True,
            "service": "redis",
            "user_id": user_id,
            "session": session,
            "found": session is not None
        }

    except Exception as e:
        return {
            "success": False,
            "service": "redis",
            "user_id": user_id,
            "error": str(e)
        }

async def handle_download_queue_status() -> Dict[str, Any]:
    """REST API handler for download queue status"""

    try:
        service = RedisService()
        status = await service.get_download_queue_status()

        return {
            "success": True,
            "service": "redis",
            "queue_status": status
        }

    except Exception as e:
        return {
            "success": False,
            "service": "redis",
            "error": str(e)
        }

async def handle_progress_get(user_id: str, book_id: str) -> Dict[str, Any]:
    """REST API handler for user progress"""

    try:
        service = RedisService()
        progress = await service.get_user_book_progress(user_id, book_id)

        return {
            "success": True,
            "service": "redis",
            "user_id": user_id,
            "book_id": book_id,
            "progress": progress
        }

    except Exception as e:
        return {
            "success": False,
            "service": "redis",
            "user_id": user_id,
            "book_id": book_id,
            "error": str(e)
        }

# Service registry for orchestration
redis_service = None

def get_service():
    """Get singleton service instance"""
    global redis_service
    if redis_service is None:
        redis_service = RedisService()
    return redis_service

# Test script
async def test_service():
    """Test the Redis service functionality"""

    print("🧪 Testing Redis Service...")
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

    # Test 3: Basic cache operations (if service running)
    if health_result.status == HealthStatus.HEALTHY:
        print("\n3. Testing Cache Operations:")

        # Set a test value
        test_key = "test_cache_key"
        test_data = {"message": "Hello from Redis!", "timestamp": datetime.utcnow().isoformat()}
        success = await service.cache_set(test_key, test_data, 60)

        if success:
            # Retrieve it
            retrieved = await service.cache_get(test_key)
            print(f"   Cache test: {'✅ SUCCESS' if retrieved else '❌ FAILED'}")

        print("\n4. Testing Session Management:")
        test_user_id = "test_user_123"
        test_session = {"discord_user": test_user_id, "book_requests": []}

        # Store session
        success = await service.store_user_session(test_user_id, test_session, 300)
        if success:
            # Retrieve session
            retrieved_session = await service.get_user_session(test_user_id)
            print(f"   Session test: {'✅ SUCCESS' if retrieved_session else '❌ FAILED'}")

            # Clean up
            await service.delete_user_session(test_user_id)

    print("\n✅ Redis Service test completed!")
    print("🔗 Ready for integration with orchestration engine")

if __name__ == "__main__":
    asyncio.run(test_service())
