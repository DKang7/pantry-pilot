from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_invalid_inventory_request():
    # Tests that invalid data is rejected with a 422 Unprocessable Entity error
    response = client.post("/api/inventory", json={"item_name": "Apple", "quantity": 0})
    assert response.status_code == 422