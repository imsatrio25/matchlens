import pytest
from fastapi.testclient import TestClient
from backend.main import app

client = TestClient(app)

def test_health_endpoint():
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"

def test_galaxy_endpoint():
    response = client.get("/api/galaxy")
    assert response.status_code == 200
    data = response.json()
    assert "nodes" in data
    assert "clusters" in data
    assert len(data["nodes"]) > 0

def test_search_endpoint():
    response = client.get("/api/search?q=Salah")
    assert response.status_code == 200
    results = response.json()
    assert len(results) >= 1
    assert "Salah" in results[0]["name"]

def test_player_dossier_endpoint():
    galaxy_resp = client.get("/api/galaxy")
    assert galaxy_resp.status_code == 200
    player_id = galaxy_resp.json()["nodes"][0]["player_id"]
    response = client.get(f"/api/players/{player_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["player_id"] == player_id
    assert "trajectories" in data
    assert "radar" in data

def test_player_dossier_not_found():
    response = client.get("/api/players/non_existent_player_id_999999")
    assert response.status_code == 404

def test_scout_analyze_mock():
    # Test scout blurb generation endpoint
    galaxy_resp = client.get("/api/galaxy")
    assert galaxy_resp.status_code == 200
    player_id = galaxy_resp.json()["nodes"][0]["player_id"]
    response = client.post("/api/scout/analyze", json={"player_id": player_id})
    assert response.status_code in [200, 503]
    if response.status_code == 200:
        data = response.json()
        assert "memo" in data
        assert "player_name" in data

def test_scout_query_mock():
    response = client.post("/api/scout/query", json={"query": "Find me young undervalued wingers"})
    assert response.status_code == 200
    data = response.json()
    assert "response" in data
    assert "recommended_players" in data
