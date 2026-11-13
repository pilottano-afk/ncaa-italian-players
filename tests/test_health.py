from fastapi.testclient import TestClient

from ncaa_api.main import app


def test_health_is_scoped_to_2026_27() -> None:
    response = TestClient(app).get("/health")
    assert response.status_code == 200
    assert response.json()["season"] == "2027"
    assert response.json()["season_label"] == "2026-27"


def test_coverage_does_not_claim_live_sources() -> None:
    response = TestClient(app).get("/api/v1/coverage")
    assert response.status_code == 200
    payload = response.json()
    assert payload["historical_data_enabled"] is False
    assert payload["status"] == "not_connected"
    assert payload["sources"] == []
