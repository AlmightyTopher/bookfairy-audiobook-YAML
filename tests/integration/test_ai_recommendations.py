"""
Integration test for AI recommendation system
Based on quickstart.md Scenario 4
These tests MUST FAIL before implementation - TDD requirement
"""
import pytest
import requests
import time
import json
from testcontainers.compose import DockerCompose


@pytest.fixture(scope="session")
def bookfairy_stack():
    """Fixture that starts the full BookFairy Docker Compose stack"""
    compose = DockerCompose("bookfairy/docker-compose.yml")
    compose.start()
    time.sleep(30)  # Wait for all services to be ready
    yield compose
    compose.stop()


class TestAIRecommendations:
    """Test AI recommendation system integration"""

    def test_lm_studio_integration(self, bookfairy_stack):
        """Test LM Studio connection and response"""
        # This test will fail until LM Studio service is implemented
        response = requests.get("http://localhost:1234/v1/models")
        assert response.status_code == 200
        data = response.json()
        assert "models" in data

    def test_discord_bot_recommendation_orchestration(self, bookfairy_stack):
        """Test Discord bot orchestrates AI recommendations"""
        discord_bot_url = "http://localhost:8080"

        # Simulate user request for recommendations
        recommendation_request = {
            "user_id": "123456789",
            "books": ["The Hobbit", "Dune"],
            "preferences": {
                "genres": ["fantasy", "sci-fi"],
                "favorite_authors": ["J.R.R. Tolkien"]
            }
        }

        response = requests.post(
            f"{discord_bot_url}/orchestrate/recommend",
            json=recommendation_request,
            timeout=30
        )

        # Expected to fail until Discord bot and LM Studio are integrated
        assert response.status_code == 200
        data = response.json()
        assert "recommendations" in data
        assert len(data["recommendations"]) > 0

    def test_redis_caching_recommendations(self, bookfairy_stack):
        """Test Redis caches AI recommendations for performance"""
        import redis

        redis_client = redis.Redis(host='localhost', port=6379, decode_responses=True)

        # Check if Redis is accessible
        assert redis_client.ping() == True

        # Simulate storing and retrieving cached recommendation
        cache_key = "recommendation:user:123456789:session:abc123"
        mock_recommendations = {
            "books": ["The Lord of the Rings", "The Fellowship of the Ring"],
            "confidence_scores": [0.95, 0.87]
        }

        # Store in cache
        redis_client.set(cache_key, json.dumps(mock_recommendations), ex=3600)

        # Retrieve from cache
        cached_data = redis_client.get(cache_key)
        assert cached_data is not None
        retrieved_recommendations = json.loads(cached_data)
        assert retrieved_recommendations == mock_recommendations

    def test_audiobookshelf_metadata_enrichment(self, bookfairy_stack):
        """Test Audiobookshelf provides metadata for recommendations"""
        audiobookshelf_url = "http://localhost:13378"

        # Check Audiobookshelf health
        response = requests.get(f"{audiobookshelf_url}/api/healthcheck")
        assert response.status_code == 200

    def test_full_recommendation_pipeline(self, bookfairy_stack):
        """Test complete recommendation pipeline from Discord to delivery"""
        discord_bot_url = "http://localhost:8080"

        # Complete recommendation workflow
        pipeline_request = {
            "workflow_type": "recommendation",
            "user_context": {
                "user_id": "123456789",
                "reading_history": ["sci-fi", "fantasy"],
                "preferences": ["audiobook", "series"]
            },
            "quality_requirements": {
                "min_rating": 4.0,
                "max_complexity": "moderate",
                "preferred_narrators": ["any"]
            }
        }

        # Simulate Discord slash command workflow
        response = requests.post(
            f"{discord_bot_url}/workflow/recommendation",
            json=pipeline_request,
            timeout=60
        )

        # Expected to fail until full pipeline is implemented
        assert response.status_code == 200
        result = response.json()
        assert result["status"] == "success"
        assert "recommendations" in result
        assert "metadata" in result
        assert "workflow_id" in result
        assert result["recommendations"]["count"] > 0


if __name__ == "__main__":
    pytest.main([__file__])
