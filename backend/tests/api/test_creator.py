from tests.api.conftest import ApiWorld, seeded


async def test_creator_reads_and_edits(api: ApiWorld) -> None:
    detail = (await api.http.get("/api/creator")).json()
    assert detail["creator"]["name"] == seeded(api).core.creator.name
    assert "label" in detail["mood"]
    edited = await api.http.patch("/api/creator", json={"title": "The Patient Flame"})
    assert edited.status_code == 200, edited.text
    assert edited.json()["ledger_entry_id"] is not None
    note = await api.http.put("/api/creator/note", json={"text": "Tend the salt."})
    assert note.status_code == 200
    mood = await api.http.put("/api/creator/mood", json={"anger": 40})
    assert mood.status_code == 200
    assert (await api.http.get("/api/creator")).json()["creator"]["title"] == "The Patient Flame"


async def test_creator_reputation_and_passions(api: ApiWorld) -> None:
    reputation = (await api.http.get("/api/creator/reputation")).json()
    assert reputation["all_passions"]
    automatic = await api.http.put("/api/creator/passions", json={"passions": [], "automatic": True})
    assert automatic.status_code == 200, automatic.text
    nudge = await api.http.post(f"/api/sons/{seeded(api).core.son.id}/reputation-nudge", json={"love": 5})
    assert nudge.status_code == 200, nudge.text


async def test_creator_content_jobs_need_the_language_model(api: ApiWorld) -> None:
    response = await api.http.post("/api/creator/portrait")
    assert response.status_code in (400, 409)
    revelation = await api.http.post("/api/revelations", json={"content": "A lake of salt appears."})
    assert revelation.status_code in (400, 409)
    unknown_field = await api.http.patch("/api/creator", json={"wings": 3})
    assert unknown_field.status_code == 400
