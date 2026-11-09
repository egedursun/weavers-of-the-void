from collections import Counter

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.db.repositories.entities import EntityDraft, EntityRepository
from aerona.db.tables.celestial import WorldRow
from aerona.db.tables.divine import NaturalLawProfileRow
from aerona.domain.enums.entity import EntityOrigin, EntityType
from aerona.domain.enums.society import NaturalLaw
from aerona.domain.models.entity_stats import NaturalLawStats, OuterBeingStats
from aerona.main import create_app
from aerona.services.player.catalog import ACTIONS
from aerona.settings import Settings
from tests.api.conftest import ApiWorld


async def bare(session: AsyncSession, name: str, entity_type: EntityType, stats: NaturalLawStats | OuterBeingStats) -> int:
    world = await session.scalar(select(WorldRow.id).order_by(WorldRow.id).limit(1))
    draft = EntityDraft(
        name=name, entity_type=entity_type, description="A record.", stats=stats, power_level=2, origin=EntityOrigin.CREATOR, birth_epoch=1, world_id=world
    )
    entity = await EntityRepository(session).create(draft)
    await session.flush()
    return entity.id


async def bare_law(session: AsyncSession) -> int:
    return await bare(session, "The Quiet Rule", EntityType.NATURAL_LAW, NaturalLawStats())


async def bare_being(session: AsyncSession) -> int:
    return await bare(session, "The Far Listener", EntityType.OUTER_BEING, OuterBeingStats(size=40, interest=40, influence=40))


def test_every_action_id_is_unique() -> None:
    counts = Counter(spec.id for spec in ACTIONS)
    assert [name for name, count in counts.items() if count > 1] == []


def test_every_api_schema_name_is_unique(settings: Settings) -> None:
    schemas = create_app(settings).openapi()["components"]["schemas"]
    assert [name for name in schemas if name.startswith("aerona__")] == []


async def test_a_son_s_divinity_reads_and_its_aims_and_wounds_are_set(api: ApiWorld) -> None:
    sons = (await api.http.get("/api/sons")).json()
    son_id = sons[0]["son"]["id"]
    set_aim = await api.http.post("/api/actions/god_goal:set", json={"god_id": son_id, "kind": "be_worshipped", "amount": 2})
    assert set_aim.status_code == 200, set_aim.text
    wound = await api.http.post("/api/actions/divine_wound:inflict", json={"god_id": son_id, "kind": "void_wound", "severity": 30})
    assert wound.status_code == 200, wound.text
    view = (await api.http.get(f"/api/gods/{son_id}/divinity")).json()
    assert [goal["kind"] for goal in view["goals"]] == ["be_worshipped"]
    assert [item["kind"] for item in view["wounds"]] == ["void_wound"]
    assert len(view["domains"]) == 2 and all(domain["hooks"] for domain in view["domains"])


async def test_the_creator_s_taboos_and_the_council_s_rulings_read_back(api: ApiWorld) -> None:
    taboo = await api.http.post("/api/actions/taboo:set", json={"act": "torture", "severity": 70})
    assert taboo.status_code == 200, taboo.text
    creator = (await api.http.get("/api/creator/divinity")).json()
    assert [row["act"] for row in creator["taboos"]] == ["torture"]
    decree = await api.http.post("/api/actions/ruling:decree", json={"motion": "cosmic_truce"})
    assert decree.status_code == 200, decree.text
    rulings = (await api.http.get("/api/council/rulings")).json()
    assert rulings["rulings"][0]["motion"] == "cosmic_truce" and rulings["rulings"][0]["active"]
    assert "none" not in rulings["motions"]


async def test_a_law_and_an_outer_being_without_a_working_read_as_drafts_and_take_one_at_once(api: ApiWorld) -> None:
    async with api.services.database.write() as session:
        law, being = await bare_law(session), await bare_being(session)
    draft = (await api.http.get(f"/api/entities/{law}/law-profile")).json()
    assert draft["drafted"] and draft["effect"] == "none"
    given = await api.http.post("/api/actions/law_profile:edit", json={"law_id": law, "values": {"effect": "bounty", "strength": 40}, "release": []})
    assert given.status_code == 200, given.text
    kept = (await api.http.get(f"/api/entities/{law}/law-profile")).json()
    assert not kept["drafted"] and kept["effect"] == "bounty" and kept["strength"] == 40
    retagged = await api.http.patch(f"/api/entities/{law}/tags", json={"law": "drought"})
    assert retagged.status_code == 200, retagged.text
    assert (await api.http.get(f"/api/entities/{law}/law-profile")).json()["effect"] == "drought"
    async with api.services.database.read() as session:
        profile = await session.get(NaturalLawProfileRow, law)
        assert profile is not None and profile.effect is NaturalLaw.DROUGHT
    outer = (await api.http.get(f"/api/entities/{being}/outer-profile")).json()
    assert outer["drafted"]
    fed = await api.http.post("/api/actions/outer_profile:edit", json={"being_id": being, "values": {"fed": 4}, "release": []})
    assert fed.status_code == 200, fed.text
    after = (await api.http.get(f"/api/entities/{being}/outer-profile")).json()
    assert not after["drafted"] and after["fed"] == 4 and after["hunger"] == outer["hunger"]
