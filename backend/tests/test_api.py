from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_health_check():
    """Verify the API is actually running before we test endpoints."""
    response = client.get("/")
    assert response.status_code == 200
    assert response.json() == {"status": "PantryPilot API is live"}

def test_recommendation_endpoint_format():
    """Verify the recommendation API accepts valid payloads and returns the correct schema structure."""
    payload = {
        "maxTotalMinutes": 30,
        "maxMissingIngredients": 2,
        "prioritizeIngredients": ["rice"],
        "excludeIngredients": ["peanut"],
        "assumeStaples": True,
        "limit": 5
    }
    
    # We expect a 200 OK even if the pantry is empty (it should return a graceful empty state message)
    response = client.post("/api/recommendations", json=payload)
    assert response.status_code == 200
    
    data = response.json()
    
    # Check that the required contract fields exist
    assert "algorithmVersion" in data
    assert "pantryItemCount" in data
    assert "results" in data
    assert isinstance(data["results"], list)

def test_recommendation_endpoint_invalid_payload():
    """Verify the API correctly rejects bad data types."""
    bad_payload = {
        "maxTotalMinutes": "thirty minutes", # This should be an integer
    }
    
    response = client.post("/api/recommendations", json=bad_payload)
    # FastAPI's Pydantic models should catch this and throw a 422 Unprocessable Entity
    assert response.status_code == 422