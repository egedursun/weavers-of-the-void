from tests.api.conftest import ApiWorld


async def test_model_metrics_and_health_report(api: ApiWorld) -> None:
    metrics = (await api.http.get("/api/metrics/models", params={"epochs": 5})).json()
    assert metrics["totals"]["calls"] == 0
    assert (await api.http.get("/api/metrics/models", params={"epochs": 0})).status_code == 400
    report = (await api.http.get("/api/health/report")).json()["report"]
    assert report["database"]["quick_check"] == "ok"
    assert not report["log_file"].startswith("/")
