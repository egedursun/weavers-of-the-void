import re
from pathlib import Path

from sqlalchemy.ext.asyncio import AsyncSession

from aerona.db.tables.culture import TraditionEffectRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.faith import SpiritProfileRow
from aerona.db.tables.settlement import SettlementProfileRow
from aerona.domain.enums.body import HarmCause
from aerona.domain.enums.culture import TraditionEffectKind
from aerona.domain.enums.entity import EntityType
from aerona.domain.enums.faith import SpiritAlignment
from aerona.domain.enums.settlement import SizeTier
from aerona.domain.models.entity_stats import SpiritStats, TraditionStats
from aerona.engine.body.hits import cause_mix
from aerona.engine.lore.traditions import apply_effect, scar_youths
from aerona.engine.primitives.distance import RegionAtlas
from aerona.engine.primitives.manual import manual_context
from aerona.engine.primitives.stats import set_stats, stat
from aerona.rules.registry import Rules
from tests.engine.core.factories import CoreWorld, entity, mortal, settlement, tuned_rules
from tests.engine.cosmos.test_flora_rp2 import land

E = TraditionEffectKind
CAUSE = re.compile(r"HarmCause\.([A-Z_]+)")


def effect(kind: TraditionEffectKind, magnitude: int = 50) -> TraditionEffectRow:
    return TraditionEffectRow(tradition_entity_id=0, effect=kind, target="", magnitude=magnitude)


async def test_feasts_bless_births_harvests_and_roads(session: AsyncSession, world: CoreWorld) -> None:
    ctx = await manual_context(session, "test")
    town = await settlement(session, "Brookhold", world, world.regions[0], population=1000)
    atlas = await RegionAtlas.load(session)
    assert await apply_effect(ctx, town, effect(E.FERTILITY, 100), 1.0, atlas)
    assert (stat(town, "population") or 0) > 1000
    ground = await land(session, world.regions[0].id, world.world.id)
    before = ground.harvest_pct
    assert await apply_effect(ctx, town, effect(E.HARVEST), 1.0, atlas)
    assert ground.harvest_pct > before
    assert await apply_effect(ctx, town, effect(E.SAFETY), 1.0, atlas)


async def test_a_vigil_calms_crime_and_the_restless_dead(session: AsyncSession, world: CoreWorld) -> None:
    ctx = await manual_context(session, "test")
    atlas = await RegionAtlas.load(session)
    town = await settlement(session, "Brookhold", world, world.regions[0])
    profile = SettlementProfileRow(settlement_entity_id=town.id, size_tier=SizeTier.TOWN, treasury=0, unrest=10, crime=40, locked=[], foreigners={})
    session.add(profile)
    dead = await mortal(session, "Oren", world, town.id)
    shade = await entity(session, "Shade of Oren", EntityType.SPIRIT, SpiritStats(unrest=60), world_id=world.world.id, location_id=town.id)
    spirit = SpiritProfileRow(spirit_entity_id=shade.id, origin_mortal_id=dead.id, alignment=SpiritAlignment.VENGEFUL, veneration=0, locked=[])
    session.add(spirit)
    await session.flush()
    assert await apply_effect(ctx, town, effect(E.VIGIL, 100), 1.0, atlas)
    assert profile.crime < 40 and spirit.veneration > 0 and (stat(shade, "unrest") or 0) < 60
    assert await apply_effect(ctx, town, effect(E.PLACATION, 100), 1.0, atlas)


async def test_a_scarring_rite_marks_those_who_come_of_age(session: AsyncSession, world: CoreWorld) -> None:
    ctx = await manual_context(session, "test", rules=tuned_rules(traditions={"scar_rite_chance": 100}))
    town = await settlement(session, "Brookhold", world, world.regions[0])
    rite: EntityRow = await entity(session, "The Marking", EntityType.TRADITION, TraditionStats(), world_id=world.world.id)
    youth = await mortal(session, "Ivo", world, town.id, age=16)
    elder = await mortal(session, "Orrin", world, town.id, age=40)
    set_stats(youth, hp=60)
    assert await scar_youths(ctx, town, rite) == 1
    assert (stat(youth, "hp") or 0) < 60 and stat(elder, "hp") == 60


def test_every_cause_of_harm_the_engine_deals_has_a_mix_of_wounds() -> None:
    source = Path(__file__).resolve().parents[3] / "src" / "aerona"
    used = {HarmCause(match.lower()) for path in source.rglob("*.py") for match in CAUSE.findall(path.read_text(encoding="utf-8"))}
    rules = Rules().injury
    missing = [cause for cause in sorted(used) if not cause_mix(rules, cause)]
    assert missing == []
