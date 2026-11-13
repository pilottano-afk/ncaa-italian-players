from fastapi import FastAPI

app = FastAPI(
    title="NCAA Italian Players API",
    version="0.1.0",
    description="Real-data NCAA 2026-27 analytics API. No historical seasons or synthetic stats.",
)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "season": "2027", "season_label": "2026-27"}


@app.get("/api/v1/coverage")
def coverage() -> dict[str, object]:
    return {
        "season": 2027,
        "season_label": "2026-27",
        "historical_data_enabled": False,
        "sources": [],
        "status": "not_connected",
        "note": "No live source has been validated in this deployment yet.",
    }
