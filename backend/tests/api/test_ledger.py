from tests.api.conftest import ApiWorld


async def test_ledger_lists_and_undoes_creator_actions(api: ApiWorld) -> None:
    edited = await api.http.patch("/api/creator", json={"title": "Keeper of Salt"})
    entry_id = edited.json()["ledger_entry_id"]
    ledger = (await api.http.get("/api/ledger")).json()
    assert entry_id in [item["entry"]["id"] for item in ledger["entries"]]
    undone = await api.http.post(f"/api/ledger/{entry_id}/undo")
    assert undone.status_code == 200, undone.text
    assert (await api.http.get("/api/creator")).json()["creator"]["title"] != "Keeper of Salt"
    assert (await api.http.post(f"/api/ledger/{entry_id}/undo")).status_code == 409
    assert (await api.http.post("/api/ledger/999999/undo")).status_code == 404
