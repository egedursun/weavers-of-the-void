from tests.api.conftest import ApiWorld


async def test_goals_scenarios_and_opportunities(api: ApiWorld) -> None:
    goals = (await api.http.get("/api/goals")).json()
    assert goals["scenarios"]
    key = goals["scenarios"][0]["key"]
    started = await api.http.post("/api/scenarios", json={"key": key})
    assert started.status_code == 200, started.text
    running = (await api.http.get("/api/goals")).json()["running"]
    assert running
    abandoned = await api.http.post(f"/api/scenarios/{running[0]['id']}/abandon")
    assert abandoned.status_code == 200, abandoned.text
    assert (await api.http.post("/api/scenarios", json={"key": "no_such_goal"})).status_code == 400
    assert (await api.http.get("/api/opportunities")).status_code == 200
