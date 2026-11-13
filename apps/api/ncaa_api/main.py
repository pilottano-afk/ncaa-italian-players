from fastapi import FastAPI

from ncaa_api.providers.cbbd import CollegeBasketballDataClient
from ncaa_api.sources import SOURCE_CATALOG, SourceHealth

app = FastAPI(
    title="NCAA Italian Players API",
    version="0.2.0",
    description="Real-data NCAA 2026-27 analytics API. No historical seasons or synthetic stats.",
)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "season": "2027", "season_label": "2026-27"}


@app.get("/api/v1/coverage")
def coverage() -> dict[str, object]:
    cbbd = CollegeBasketballDataClient()
    source_health = [
        SourceHealth.make(
            "sportsdataverse",
            "SportsDataverse NCAA MBB",
            "not_configured",
            message="Source catalogued; live dataset retrieval and coverage validation are pending.",
            documentation_url="https://github.com/sportsdataverse/ncaa-mbb-hoops-data",
        ).as_dict(),
        SourceHealth.make(
            "collegebasketballdata",
            "CollegeBasketballData.com",
            "configured" if cbbd.configured else "not_configured",
            message=(
                "API key not configured; no live request has been made."
                if not cbbd.configured
                else "API key is present; no live dataset request has been made yet."
            ),
            documentation_url="https://api.collegebasketballdata.com/data-availability",
        ).as_dict(),
    ]
    return {
        "season": 2027,
        "season_label": "2026-27",
        "historical_data_enabled": False,
        "sources": SOURCE_CATALOG,
        "source_health": source_health,
        "status": "not_connected",
        "note": "Catalogued sources are not yet evidence of imported or complete live data.",
    }
