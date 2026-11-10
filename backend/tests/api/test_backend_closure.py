from pathlib import Path

import pytest
from sqlalchemy import select

from aerona.db.repositories.bonds import BondDraft, BondRepository
from aerona.db.repositories.chronicle import ChronicleDraft, ChronicleRepository
from aerona.db.repositories.foreign_gods import ForeignGodDraft, ForeignGodRepository
from aerona.db.repositories.sons import SonRepository
from aerona.db.tables.bonds import BondRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.foreign_gods import ForeignGodPowerRow
from aerona.db.tables.lore import LexemeRow
from aerona.domain.enums.bond import BondKind, BondState
from aerona.domain.enums.chronicle import ChronicleKind
from aerona.domain.enums.domain import Domain
from aerona.domain.enums.entity import EntityType
from aerona.domain.enums.foreign_god import ForeignGodPowerEffect
from aerona.domain.models.entity_stats import PeopleStats
from aerona.domain.models.stats import StatBlock
from tests.api.conftest import ApiWorld, seeded
from tests.api.test_images import png
from tests.engine.core.factories import add_empty_world, entity, son_draft


async def test_distribution_preview_ranks_donors_by_worship_and_guardianship(api: ApiWorld) -> None:
    core = seeded(api).core
    async with api.services.database.write() as session:
        sons = SonRepository(session)
        loved = await sons.create(son_draft("Loved", core.world.id))
        lonely = await sons.create(son_draft("Lonely", core.world.id))
        await BondRepository(session).connect(BondDraft(core.people.id, loved.id, BondKind.WORSHIPS, 1))
        empty, regions = await add_empty_world(session)
        await entity(session, "Far Folk", EntityType.PEOPLE, PeopleStats(population=500), world_id=empty.id, location_id=regions[0].id)
        loved_id, lonely_id, empty_id = loved.id, lonely.id, empty.id
    preview = (await api.http.get("/api/sons/distribution-preview")).json()
    scores = {item["son_id"]: item["score"] for item in preview["candidates"]}
    assert scores[loved_id] > scores[lonely_id]
    assert [item["score"] for item in preview["candidates"]] == sorted(scores.values())
    assert preview["next_son_id"] == min(preview["candidates"], key=lambda item: (item["score"], item["son_id"]))["son_id"]
    assert preview["godless_world_ids"] == [empty_id]


async def test_chronicle_world_filter_follows_the_linked_records(api: ApiWorld) -> None:
    core = seeded(api).core
    async with api.services.database.write() as session:
        other, regions = await add_empty_world(session, "Thule")
        repository = ChronicleRepository(session)
        home = await repository.append(ChronicleDraft(1, ChronicleKind.WORLD, "Home line.", (core.regions[0].id,)))
        far = await repository.append(ChronicleDraft(1, ChronicleKind.WORLD, "Far line.", (regions[0].id,)))
        home_id, far_id, other_id = home.row.id, far.row.id, other.id
    main = {item["id"] for item in (await api.http.get("/api/chronicle", params={"world_id": core.world.id, "limit": 200})).json()["items"]}
    distant = {item["id"] for item in (await api.http.get("/api/chronicle", params={"world_id": other_id, "limit": 200})).json()["items"]}
    assert home_id in main and far_id not in main
    assert far_id in distant and home_id not in distant


async def test_any_chronicle_line_can_be_pinned_as_a_notification(api: ApiWorld) -> None:
    core = seeded(api).core
    async with api.services.database.write() as session:
        written = await ChronicleRepository(session).append(ChronicleDraft(1, ChronicleKind.WORLD, "A quiet harvest.", (core.people.id,)))
        line_id = written.row.id
    pinned = await api.http.post(f"/api/notifications/from-chronicle/{line_id}")
    assert pinned.status_code == 200, pinned.text
    body = pinned.json()
    assert body["chronicle_id"] == line_id and body["target_node_id"] == core.people.id
    again = (await api.http.post(f"/api/notifications/from-chronicle/{line_id}")).json()
    assert again["id"] == body["id"]
    assert (await api.http.post("/api/notifications/from-chronicle/999999")).status_code == 404


async def test_secondary_backup_folder_is_a_setting(api: ApiWorld, tmp_path: Path) -> None:
    target = tmp_path / "mirror"
    assert (await api.http.get("/api/backups/secondary")).json()["directory"] is None
    stored = await api.http.put("/api/backups/secondary", json={"directory": str(target)})
    assert stored.status_code == 200, stored.text
    assert stored.json()["directory"] == str(target)
    taken = (await api.http.post("/api/backups")).json()
    assert (target / taken["file"]).is_file()
    assert (await api.http.put("/api/backups/secondary", json={"directory": "relative/path"})).status_code == 400
    cleared = await api.http.put("/api/backups/secondary", json={"directory": None})
    assert cleared.json()["directory"] is None


async def test_saved_genesis_settings_and_engine_seed_are_readable(api: ApiWorld) -> None:
    core = seeded(api).core
    genesis = (await api.http.get("/api/genesis/settings")).json()
    assert genesis["seed_idea"] == core.cosmos.seed_idea and genesis["settings"] is None
    seed = (await api.http.get("/api/engine/seed")).json()
    assert seed["world_seed"] == core.cosmos.rng_seed and seed["epoch"] == core.cosmos.epoch
    assert {"travel", "exploration", "pantheon", "beyond"} <= set(seed["phase_streams"])


@pytest.mark.parametrize("phase", ["travel", "exploration", "pantheon", "beyond"])
async def test_engine_steps_run_by_name_and_replay_their_seed(api: ApiWorld, phase: str) -> None:
    ran = await api.http.post("/api/actions/engine:run_phase", json={"phase": phase})
    assert ran.status_code == 200, ran.text
    assert ran.json()["message"].startswith(f"The {phase} step ran now")
    replayed = (await api.http.post("/api/actions/engine:run_phase", json={"phase": phase, "replay": True})).json()
    assert replayed["values"]["stream"] == phase
    assert replayed["values"]["world_seed"] == seeded(api).core.cosmos.rng_seed


async def test_foreign_god_detail_reports_deathless_from_the_server(api: ApiWorld) -> None:
    core = seeded(api).core
    async with api.services.database.write() as session:
        god = await ForeignGodRepository(session).create(
            ForeignGodDraft(name="Ushmar", world_id=core.world.id, domain_primary=Domain.DEATH, power=40, stats=StatBlock.uniform(50), created_epoch=1)
        )
        session.add(ForeignGodPowerRow(god_id=god.id, slot=0, name="Unending", effect=ForeignGodPowerEffect.DEATHLESS, description="It does not die."))
        mortal = await ForeignGodRepository(session).create(
            ForeignGodDraft(name="Kell", world_id=core.world.id, domain_primary=Domain.SEA, power=40, stats=StatBlock.uniform(50), created_epoch=1)
        )
        god_id, mortal_id = god.id, mortal.id
    detail = (await api.http.get(f"/api/foreign-gods/{god_id}")).json()
    plain = (await api.http.get(f"/api/foreign-gods/{mortal_id}")).json()
    rules = api.services.rules.current.god_power
    assert detail["deathless"] is True and str(rules.kill_immortal_foreign_mult) in detail["deathless_caption"]
    assert [power["effect"] for power in detail["powers"]] == ["deathless"]
    assert plain["deathless"] is False and plain["deathless_caption"] is None
    assert detail["kill_cost"] > plain["kill_cost"]


async def test_image_records_carry_their_mime_and_digest(api: ApiWorld) -> None:
    town = seeded(api).core.extra["town"].id
    image = (await api.http.post("/api/images", params={"node_id": town}, content=png(), headers={"content-type": "image/png"})).json()
    assert image["mime"] == "image/png"
    assert len(image["sha256"]) == 64


async def test_creator_adds_words_through_the_language_route(api: ApiWorld) -> None:
    language = seeded(api).core.language
    added = await api.http.post(f"/api/languages/{language.id}/words", json={"words": [{"word": "zelvar", "meaning": "dawn"}]})
    assert added.status_code == 200, added.text
    async with api.services.database.read() as session:
        words = list(await session.scalars(select(LexemeRow.word).where(LexemeRow.language_entity_id == language.id)))
    assert "zelvar" in words


async def test_data_repairs_close_mismatched_location_bonds(api: ApiWorld) -> None:
    core = seeded(api).core
    async with api.services.database.write() as session:
        people = await session.get(EntityRow, core.people.id)
        assert people is not None
        stale = await session.scalar(
            select(BondRow).where(BondRow.source_node_id == people.id, BondRow.kind == BondKind.INSIDE, BondRow.state == BondState.ACTIVE)
        )
        assert stale is not None
        moved_to = next(region.id for region in core.regions if region.id != stale.target_node_id)
        people.location_id = moved_to
        stale_id = stale.id
    started = (await api.http.post("/api/maintenance/tasks/data_repairs/run")).json()
    await api.wait_job(started["job_id"])
    async with api.services.database.read() as session:
        row = await session.get(BondRow, stale_id)
    assert row is not None and row.state is not BondState.ACTIVE
