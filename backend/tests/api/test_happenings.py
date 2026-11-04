from tests.api.conftest import ApiWorld, seeded


async def test_an_event_set_down_by_the_player_reads_back_with_its_phase_and_footprint(api: ApiWorld) -> None:
    region = seeded(api).core.regions[0].id
    created = await api.http.post(
        "/api/actions/event:create", json={"kind": "festival_of_note", "where_id": region, "name": "the Lantern Feast", "severity": 35}
    )
    assert created.status_code == 200, created.text
    event_id = created.json()["created_ids"][0]
    view = (await api.http.get(f"/api/entities/{event_id}/event")).json()
    assert view["kind"] == "festival_of_note" and view["phase"] == "onset" and not view["ended"]
    assert [item["region_id"] for item in view["footprint"]] == [region]
    assert view["incident_text"] and "festival_of_note" in view["kinds"]
    assert [step["phase"] for step in view["steps"]] == ["onset", "aftermath"]
    held = await api.http.post("/api/actions/event:phase", json={"event_id": event_id, "phase": "peak", "hold": True})
    assert held.status_code == 200, held.text
    view = (await api.http.get(f"/api/entities/{event_id}/event")).json()
    assert view["phase"] == "peak" and "phase" in view["locked"]
    here = (await api.http.get(f"/api/entities/{region}/happenings")).json()
    assert event_id in [item["entity_id"] for item in here["events"]]


async def test_a_region_reports_its_shape(api: ApiWorld) -> None:
    region = seeded(api).core.regions[0].id
    response = await api.http.get(f"/api/entities/{region}/land-shape")
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["region_id"] == region and body["desertification"] == 0 and body["shifts"] == []
    shaped = await api.http.post("/api/actions/land:shape", json={"region_id": region, "volcanic": True, "volcanic_pressure": 60})
    assert shaped.status_code == 200, shaped.text
    body = (await api.http.get(f"/api/entities/{region}/land-shape")).json()
    assert body["volcanic"] and body["volcanic_pressure"] == 60 and body["eruption_chance"] > 0
    assert set(body["locked"]) == {"volcanic", "volcanic_pressure"}
