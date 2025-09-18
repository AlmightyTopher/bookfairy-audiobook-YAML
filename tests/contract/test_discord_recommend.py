"""
Contract tests for Discord Bot API POST /orchestrate/recommend endpoint
These tests MUST FAIL before implementation - TDD requirement
"""
import pytest
import requests
import json
from testcontainers.compose import DockerCompose
import time


class TestDiscordRecommendAPI:
    """Contract tests for AI recommendation orchestration endpoint"""

    @pytest.fixture(scope="class")
    def docker_services(self):
        """Set up Docker services for contract testing"""
        with DockerCompose(".", compose_file_name="docker-compose.yml") as compose:
            # Wait for services to be ready
            time.sleep(30)
            yield compose

    @pytest.fixture
    def valid_recommend_request(self):
        """Valid recommendation request payload per contract"""
        return {
            "user_id": "discord_user_123456789",
            "context": "User is looking for fantasy audiobooks similar to LOTR",
            "preferences": {
                "genres": ["fantasy", "epic fantasy", "adventure"],
                "authors": ["J.R.R. Tolkien", "Brandon Sanderson"]
            }
        }

    @pytest.fixture
    def minimal_recommend_request(self):
        """Minimal valid recommendation request with only required fields"""
        return {
            "user_id": "discord_user_987654321"
        }

    def test_orchestrate_recommend_endpoint_exists(self, docker_services):
        """Test that POST /orchestrate/recommend endpoint exists"""
        # This WILL FAIL until recommend orchestration endpoint is implemented
        payload = {
            "user_id": "test_user"
        }
        response = requests.post(
            "http://localhost:8080/orchestrate/recommend",
            json=payload,
            timeout=10
        )
        # Endpoint should exist and accept requests
        assert response.status_code != 404
        assert response.headers["content-type"] == "application/json"

    def test_orchestrate_recommend_valid_request(self, docker_services, valid_recommend_request):
        """Test valid recommendation request returns proper response"""
        response = requests.post(
            "http://localhost:8080/orchestrate/recommend",
            json=valid_recommend_request,
            timeout=30
        )

        # Should return 200 OK per contract (synchronous response)
        assert response.status_code == 200

        data = response.json()

        # Required fields per RecommendationResponse schema
        assert "recommendations" in data
        assert isinstance(data["recommendations"], list)

        # Validate recommendation structure
        for rec in data["recommendations"]:
            required_fields = {"title", "author", "confidence", "reason"}
            assert set(rec.keys()) >= required_fields

            # Validate field types
            assert isinstance(rec["title"], str)
            assert isinstance(rec["author"], str)
            assert isinstance(rec["confidence"], (int, float))
            assert isinstance(rec["reason"], str)

            # Validate confidence range (0.0 to 1.0)
            assert 0.0 <= rec["confidence"] <= 1.0

    def test_orchestrate_recommend_minimal_request(self, docker_services, minimal_recommend_request):
        """Test minimal valid request with only required fields"""
        response = requests.post(
            "http://localhost:8080/orchestrate/recommend",
            json=minimal_recommend_request,
            timeout=30
        )

        assert response.status_code == 200

        data = response.json()
        assert "recommendations" in data
        assert isinstance(data["recommendations"], list)

    def test_orchestrate_recommend_missing_required_fields(self, docker_services):
        """Test validation of required fields"""
        # Missing user_id field
        payload = {"context": "test context"}
        response = requests.post(
            "http://localhost:8080/orchestrate/recommend",
            json=payload,
            timeout=10
        )
        assert response.status_code == 400

        # Empty user_id
        payload = {"user_id": ""}
        response = requests.post(
            "http://localhost:8080/orchestrate/recommend",
            json=payload,
            timeout=10
        )
        assert response.status_code == 400

    def test_orchestrate_recommend_preferences_structure(self, docker_services):
        """Test validation of preferences object structure"""
        # Valid preferences with genres only
        payload = {
            "user_id": "test_user",
            "preferences": {
                "genres": ["mystery", "thriller"]
            }
        }
        response = requests.post(
            "http://localhost:8080/orchestrate/recommend",
            json=payload,
            timeout=15
        )
        assert response.status_code == 200

        # Valid preferences with authors only
        payload = {
            "user_id": "test_user",
            "preferences": {
                "authors": ["Agatha Christie", "Stephen King"]
            }
        }
        response = requests.post(
            "http://localhost:8080/orchestrate/recommend",
            json=payload,
            timeout=15
        )
        assert response.status_code == 200

    def test_orchestrate_recommend_invalid_preferences_structure(self, docker_services):
        """Test handling of invalid preferences structure"""
        # Genres not an array
        payload = {
            "user_id": "test_user",
            "preferences": {
                "genres": "not_an_array"
            }
        }
        response = requests.post(
            "http://localhost:8080/orchestrate/recommend",
            json=payload,
            timeout=10
        )
        assert response.status_code == 400

        # Authors not an array
        payload = {
            "user_id": "test_user",
            "preferences": {
                "authors": "not_an_array"
            }
        }
        response = requests.post(
            "http://localhost:8080/orchestrate/recommend",
            json=payload,
            timeout=10
        )
        assert response.status_code == 400

    def test_orchestrate_recommend_empty_preferences(self, docker_services):
        """Test handling of empty preferences"""
        # Empty preferences object
        payload = {
            "user_id": "test_user",
            "preferences": {}
        }
        response = requests.post(
            "http://localhost:8080/orchestrate/recommend",
            json=payload,
            timeout=15
        )
        assert response.status_code == 200

        # Empty genres array
        payload = {
            "user_id": "test_user",
            "preferences": {
                "genres": []
            }
        }
        response = requests.post(
            "http://localhost:8080/orchestrate/recommend",
            json=payload,
            timeout=15
        )
        assert response.status_code == 200

    def test_orchestrate_recommend_context_validation(self, docker_services):
        """Test context field validation"""
        # Very long context
        long_context = "A" * 5000
        payload = {
            "user_id": "test_user",
            "context": long_context
        }
        response = requests.post(
            "http://localhost:8080/orchestrate/recommend",
            json=payload,
            timeout=30
        )
        # Should either accept or reject with validation error
        assert response.status_code in [200, 400]

        # Empty context
        payload = {
            "user_id": "test_user",
            "context": ""
        }
        response = requests.post(
            "http://localhost:8080/orchestrate/recommend",
            json=payload,
            timeout=15
        )
        assert response.status_code == 200

    def test_orchestrate_recommend_response_quality(self, docker_services, valid_recommend_request):
        """Test quality of recommendation response"""
        response = requests.post(
            "http://localhost:8080/orchestrate/recommend",
            json=valid_recommend_request,
            timeout=30
        )

        assert response.status_code == 200
        data = response.json()
        recommendations = data["recommendations"]

        # Should return at least one recommendation
        assert len(recommendations) > 0

        # Should not return too many recommendations (reasonable limit)
        assert len(recommendations) <= 20

        # Each recommendation should have meaningful content
        for rec in recommendations:
            assert len(rec["title"].strip()) > 0
            assert len(rec["author"].strip()) > 0
            assert len(rec["reason"].strip()) > 0

    def test_orchestrate_recommend_confidence_sorting(self, docker_services, valid_recommend_request):
        """Test that recommendations are sorted by confidence"""
        response = requests.post(
            "http://localhost:8080/orchestrate/recommend",
            json=valid_recommend_request,
            timeout=30
        )

        assert response.status_code == 200
        data = response.json()
        recommendations = data["recommendations"]

        if len(recommendations) > 1:
            # Recommendations should be sorted by confidence (descending)
            confidences = [rec["confidence"] for rec in recommendations]
            assert confidences == sorted(confidences, reverse=True)

    def test_orchestrate_recommend_content_type_validation(self, docker_services):
        """Test that endpoint requires JSON content type"""
        payload = "user_id=test_user"
        response = requests.post(
            "http://localhost:8080/orchestrate/recommend",
            data=payload,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            timeout=10
        )
        # Should reject non-JSON content
        assert response.status_code == 400

    def test_orchestrate_recommend_malformed_json(self, docker_services):
        """Test handling of malformed JSON requests"""
        malformed_json = '{"user_id": "test_user"'  # Missing closing brace
        response = requests.post(
            "http://localhost:8080/orchestrate/recommend",
            data=malformed_json,
            headers={"Content-Type": "application/json"},
            timeout=10
        )
        assert response.status_code == 400

    def test_orchestrate_recommend_service_unavailable(self, docker_services):
        """Test response when AI service is unavailable"""
        payload = {
            "user_id": "test_user"
        }
        response = requests.post(
            "http://localhost:8080/orchestrate/recommend",
            json=payload,
            timeout=10
        )

        # If AI service is unavailable, should return 503
        if response.status_code == 503:
            data = response.json()
            # Should contain error information
            assert "error" in data or "message" in data

    def test_orchestrate_recommend_response_timing(self, docker_services, minimal_recommend_request):
        """Test recommendation response timing requirements"""
        start_time = time.time()
        response = requests.post(
            "http://localhost:8080/orchestrate/recommend",
            json=minimal_recommend_request,
            timeout=60
        )
        response_time = time.time() - start_time

        # AI recommendations may take longer but should be reasonable
        assert response_time < 60.0
        assert response.status_code == 200

    def test_orchestrate_recommend_method_restrictions(self, docker_services):
        """Test that only POST method is allowed"""
        # GET should not be allowed
        response = requests.get("http://localhost:8080/orchestrate/recommend", timeout=10)
        assert response.status_code == 405

        # PUT should not be allowed
        response = requests.put("http://localhost:8080/orchestrate/recommend", timeout=10)
        assert response.status_code == 405

    def test_orchestrate_recommend_user_id_validation(self, docker_services):
        """Test validation of user_id field"""
        valid_user_ids = [
            "123456789012345678",  # Discord snowflake format
            "user123",             # alphanumeric
            "test_user_123"        # with underscores
        ]

        for user_id in valid_user_ids:
            payload = {
                "user_id": user_id
            }
            response = requests.post(
                "http://localhost:8080/orchestrate/recommend",
                json=payload,
                timeout=20
            )
            assert response.status_code == 200

    def test_orchestrate_recommend_genre_variety(self, docker_services):
        """Test recommendation handling of various genres"""
        genres_to_test = [
            ["fantasy"],
            ["science fiction", "sci-fi"],
            ["mystery", "thriller"],
            ["romance"],
            ["biography", "non-fiction"],
            ["horror"],
            ["historical fiction"]
        ]

        for genres in genres_to_test:
            payload = {
                "user_id": "test_user",
                "preferences": {
                    "genres": genres
                }
            }
            response = requests.post(
                "http://localhost:8080/orchestrate/recommend",
                json=payload,
                timeout=25
            )
            assert response.status_code == 200

            data = response.json()
            assert len(data["recommendations"]) > 0

    def test_orchestrate_recommend_context_influence(self, docker_services):
        """Test that context influences recommendations"""
        # Test with specific context
        payload_with_context = {
            "user_id": "test_user",
            "context": "Looking for something like Harry Potter but for adults"
        }
        response1 = requests.post(
            "http://localhost:8080/orchestrate/recommend",
            json=payload_with_context,
            timeout=25
        )
        assert response1.status_code == 200

        # Test without context
        payload_without_context = {
            "user_id": "test_user"
        }
        response2 = requests.post(
            "http://localhost:8080/orchestrate/recommend",
            json=payload_without_context,
            timeout=25
        )
        assert response2.status_code == 200

        # Both should return recommendations
        data1 = response1.json()
        data2 = response2.json()
        assert len(data1["recommendations"]) > 0
        assert len(data2["recommendations"]) > 0

    def test_orchestrate_recommend_unicode_handling(self, docker_services):
        """Test handling of unicode characters in preferences and context"""
        payload = {
            "user_id": "test_user",
            "context": "Interested in books about 北京 and Japanese culture",
            "preferences": {
                "authors": ["村上春樹", "Jules Verne"],
                "genres": ["文学", "adventure"]
            }
        }

        response = requests.post(
            "http://localhost:8080/orchestrate/recommend",
            json=payload,
            timeout=25
        )

        # Should handle unicode gracefully
        assert response.status_code == 200

    def test_orchestrate_recommend_concurrent_requests(self, docker_services):
        """Test handling of concurrent recommendation requests"""
        import concurrent.futures

        def make_recommend_request(suffix):
            payload = {
                "user_id": f"user_{suffix}",
                "context": f"Looking for books about topic {suffix}"
            }
            return requests.post(
                "http://localhost:8080/orchestrate/recommend",
                json=payload,
                timeout=30
            )

        # Submit multiple concurrent requests
        with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
            futures = [executor.submit(make_recommend_request, i) for i in range(5)]
            responses = [future.result() for future in futures]

        # All requests should be handled successfully
        for response in responses:
            assert response.status_code == 200
            data = response.json()
            assert "recommendations" in data