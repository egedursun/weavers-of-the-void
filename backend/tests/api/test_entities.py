from sqlalchemy import select

from aerona.db.repositories.bonds import BondDraft, BondRepository
from aerona.db.tables.entities import EntityRow
from aerona.domain.enums.bond import BondKind
from aerona.domain.enums.entity import EntityType
from tests.api.conftest import ApiWorld, seeded


async def test_entity_list_is_paginated_and_filtered(api: ApiWorld) -> None:
    page = (await api.http.get("/api/entities", params={"limit": 2})).json()
    assert len(page["items"]) == 2
    assert page["total"] > 2
    peoples = (await api.http.get("/api/entities", params={"type": "people"})).json()
    assert {item["entity_type"] for item in peoples["items"]} == {"people"}
    found = (await api.http.get("/api/entities", params={"q": "Harrow"})).json()
    assert [item["name"] for item in found["items"]] == ["Harrowmere"]
    assert (await api.http.get("/api/entities", params={"limit": 0})).status_code == 400


async def test_entity_detail_windows_relations(api: ApiWorld) -> None:
    world = seeded(api).core
    detail = (await api.http.get(f"/api/entities/{world.extra['town'].id}")).json()
    assert detail["entity"]["name"] == "Harrowmere"
    assert detail["bond_total"] >= len(detail["bonds"])
    insight = detail["insight"]
    assert insight["society"] is not None and set(insight["society"]["shares"]) >= {"farmer", "merchant"}
    assert insight["exploration"] is not None and insight["exploration"]["regions"] >= 1
    assert insight["life"] is None
    people = (await api.http.get(f"/api/entities/{world.people.id}")).json()["insight"]
    assert people["capacity"] is not None and people["capacity"]["capacity"] >= 0
    bonds = (await api.http.get(f"/api/entities/{world.extra['town'].id}/bonds", params={"limit": 1})).json()
    assert len(bonds["items"]) == 1
    assert (await api.http.get("/api/entities/999999")).status_code == 404


async def test_entity_edits_and_bonds(api: ApiWorld) -> None:
    world = seeded(api).core
    town = world.extra["town"].id
    assert (await api.http.put(f"/api/entities/{town}/favorite", json={"favorite": True})).status_code == 200
    assert [item["id"] for item in (await api.http.get("/api/favorites")).json()] == [town]
    assert (await api.http.put(f"/api/entities/{town}/note", json={"text": "Watch the harbour."})).status_code == 200
    archived = await api.http.put(f"/api/entities/{town}/archive", json={"mode": "atlas"})
    assert archived.status_code == 200, archived.text
    moved = await api.http.put(f"/api/entities/{town}/map-position", json={"x": 120.4, "y": 80.6})
    assert moved.status_code == 200
    link = await api.http.post(
        "/api/links", json={"source_id": town, "target_id": world.extra["feast"].id, "kind": "celebrates", "description": "every spring"}
    )
    assert link.status_code in (200, 400), link.text
    merge = await api.http.post(f"/api/entities/{town}/merge", json={"other_id": world.extra["port"].id, "confirm": "merge"})
    assert merge.status_code == 400
    edit = await api.http.patch(f"/api/entities/{town}", json={"description": ""})
    assert edit.status_code == 400


async def test_entity_jobs_need_the_language_model(api: ApiWorld) -> None:
    town = seeded(api).core.extra["town"].id
    for path in ("deepen", "image-prompt", "suggest-links"):
        assert (await api.http.post(f"/api/entities/{town}/{path}")).status_code == 409


async def test_entity_insight_shows_life_lineage_and_prerequisites(api: ApiWorld) -> None:
    async with api.services.database.write() as session:
        sage = await session.scalar(select(EntityRow).where(EntityRow.name == "Ilvane"))
        lover = await session.scalar(select(EntityRow).where(EntityRow.name == "Corwen"))
        lore = list(await session.scalars(select(EntityRow).where(EntityRow.entity_type == EntityType.KNOWLEDGE).order_by(EntityRow.id)))
        assert sage is not None and lover is not None and len(lore) >= 2
        bonds = BondRepository(session)
        await bonds.connect(BondDraft(lover.id, sage.id, BondKind.DESCENDS_FROM, 1))
        await bonds.connect(BondDraft(lore[1].id, lore[0].id, BondKind.DESCENDS_FROM, 1))
    insight = (await api.http.get(f"/api/entities/{sage.id}")).json()["insight"]
    assert insight["life"] is not None and insight["life"]["lifespan"] >= insight["life"]["lifespan_base"]
    assert [item["id"] for item in insight["descendants"]] == [lover.id]
    child = (await api.http.get(f"/api/entities/{lover.id}")).json()["insight"]
    assert [item["id"] for item in child["ancestors"]] == [sage.id]
    knowledge = {item["knowledge"]["id"]: item for item in (await api.http.get("/api/knowledge")).json()}
    assert [item["id"] for item in knowledge[lore[1].id]["prerequisites"]] == [lore[0].id]


async def test_the_atlas_can_hide_what_history_has_archived(api: ApiWorld) -> None:
    town = seeded(api).core.extra["town"].id
    everything = (await api.http.get("/api/entities", params={"limit": 200})).json()
    assert (await api.http.put(f"/api/entities/{town}/archive", json={"mode": "history"})).status_code == 200
    shown = (await api.http.get("/api/entities", params={"limit": 200, "hide_archived": True})).json()
    assert town in {item["id"] for item in everything["items"]}
    assert town not in {item["id"] for item in shown["items"]} and shown["total"] < everything["total"]
