from fastapi.testclient import TestClient

from ncaa_api.main import app

client = TestClient(app)


def test_health_is_scoped_to_2026_27() -> None:
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["season"] == "2027"
    assert response.json()["season_label"] == "2026-27"


def test_coverage_lists_sources_without_claiming_live_data(monkeypatch) -> None:
    # The test suite may provide a disposable PostgreSQL DATABASE_URL.
    # Remove it here so this test checks the unconfigured-source state deterministically.
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.delenv("NCAA_DATABASE_URL", raising=False)
    response = client.get("/api/v1/coverage")
    assert response.status_code == 200
    payload = response.json()
    assert payload["historical_data_enabled"] is False
    assert payload["status"] == "not_configured"
    assert {source["id"] for source in payload["sources"]} == {
        "sportsdataverse",
        "collegebasketballdata",
    }
    assert payload["source_health"][0]["state"] == "not_checked"
    assert payload["source_health"][1]["state"] == "not_configured"
