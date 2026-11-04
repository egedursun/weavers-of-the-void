from dataclasses import dataclass
from typing import cast

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.constants.units import PERCENT
from aerona.db.repositories.entities import EntityDraft, EntityRepository
from aerona.db.tables.culture import TraditionParticipationRow, TraditionProfileRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.faith import CultTenetRow
from aerona.db.tables.interconnect import ModifierRow
from aerona.db.tables.mind import TraitRow
from aerona.db.tables.polity import LawJurisdictionRow, LawProfileRow, TreatyClauseRow, TreatyPartyRow, TreatyProfileRow
from aerona.domain.enums.bond import BondKind
from aerona.domain.enums.culture import TraditionKind
from aerona.domain.enums.entity import EngineKind, EntityFlag, EntityOrigin, EntityType
from aerona.domain.enums.environment import TerrainKind, WeatherEffect, WeatherKind
from aerona.domain.enums.faith import TenetKind
from aerona.domain.enums.mind import TraitKind, TraitSource
from aerona.domain.enums.modifier import ModifierOp, ModifierSource
from aerona.domain.enums.polity import ClauseKind, Jurisdiction, LawArea, LawKind, TreatyKind
from aerona.domain.models.entity_stats import ArmyStats, LawStats, TraditionStats, TreatyStats
from aerona.engine.body.book import effective, ensure_body
from aerona.engine.environment.book import EnvironmentBook
from aerona.engine.interconnect.derived import derive_tick_modifiers, environment_drafts
from aerona.engine.phases.climate import law_fertility
from aerona.engine.primitives.knowledge import LawBook
from aerona.engine.primitives.modifiers import ModifierDraft, ModifierIndex, add_modifier, live_modifiers, virtual_value
from aerona.engine.primitives.queries import add_flag
from aerona.engine.primitives.stats import base_stat, stat
from aerona.rules.registry import Rules
from tests.engine.warfare.factories import bond, make, make_ctx

RULES = Rules()
OTHER_STATS = {EntityType.LAW: LawStats, EntityType.TREATY: TreatyStats, EntityType.TRADITION: TraditionStats, EntityType.ARMY: ArmyStats}


async def record(session: AsyncSession, name: str, entity_type: EntityType, world_id: int, **stats: int) -> EntityRow:
    draft = EntityDraft(
        name=name,
        entity_type=entity_type,
        description=f"The {name}.",
        stats=OTHER_STATS[entity_type](**stats),
        power_level=3,
        origin=EntityOrigin.ENGINE,
        birth_epoch=1,
        world_id=world_id,
        split_title=False,
    )
    return await EntityRepository(session).create(draft)


async def _rows(session: AsyncSession, source: ModifierSource) -> list[ModifierRow]:
    return list(await session.scalars(select(ModifierRow).where(ModifierRow.source_kind == source).order_by(ModifierRow.id)))


async def test_wounds_and_temperament_become_modifiers_and_count_once(session: AsyncSession, world_id: int) -> None:
    mortal = await make(session, "Varn", EntityType.MORTAL, world_id, strength=60, agility=50, intellect=40, charisma=30, hp=40, age=30, lifespan=70)
    body = await ensure_body(session, RULES, mortal, 1)
    body.melee = 50
    session.add(TraitRow(node_id=mortal.id, trait=TraitKind.BRAVE, source=TraitSource.BIRTH, epoch=1))
    await session.flush()
    before = await effective(session, mortal, "strength", rules=RULES)
    await derive_tick_modifiers(make_ctx(session, RULES))
    injury = [row for row in await _rows(session, ModifierSource.INJURY) if row.target_key == "strength"]
    trait = [row for row in await _rows(session, ModifierSource.TRAIT) if row.target_key == "strength"]
    assert [row.magnitude for row in injury] == [0.5]
    assert trait and trait[0].magnitude > 1
    index = await ModifierIndex.load(session, 10)
    with live_modifiers(index, 10, RULES):
        assert stat(mortal, "strength") == round(60 * 0.5 * trait[0].magnitude)
        assert await effective(session, mortal, "strength", rules=RULES) == pytest.approx(before)


async def test_laws_treaties_structures_tenets_and_traditions_derive_modifiers(session: AsyncSession, world_id: int) -> None:
    town = await make(session, "Varn", EntityType.SETTLEMENT, world_id, population=900, defense=30, prosperity=40, piety=20, wealth=30)
    other = await make(session, "Osk", EntityType.SETTLEMENT, world_id, population=500, defense=30, prosperity=40, piety=20, wealth=30)
    law = await record(session, "Standing Host", EntityType.LAW, world_id)
    session.add(LawProfileRow(law_entity_id=law.id, kind=LawKind.STANDING_ARMY, area=LawArea.PENAL, enforcement=50))
    session.add(LawJurisdictionRow(law_entity_id=law.id, node_entity_id=town.id, jurisdiction=Jurisdiction.POLITY))
    treaty = await record(session, "Pact of Osk", EntityType.TREATY, world_id)
    session.add(TreatyProfileRow(treaty_entity_id=treaty.id, kind=TreatyKind.TRADE_PACT, signed_epoch=1, until_epoch=None, ended_epoch=None))
    session.add_all([TreatyPartyRow(treaty_entity_id=treaty.id, party_node_id=town.id), TreatyPartyRow(treaty_entity_id=treaty.id, party_node_id=other.id)])
    session.add(TreatyClauseRow(treaty_entity_id=treaty.id, kind=next(iter(ClauseKind)), obligor_node_id=other.id))
    await make(session, "Varn Temple", EntityType.STRUCTURE, world_id, location_id=town.id, engine_kind=EngineKind.TEMPLE, function=100, durability=80)
    cult = await make(session, "Flame", EntityType.CULT, world_id, followers=300, zeal=40, influence=30)
    session.add(CultTenetRow(cult_entity_id=cult.id, tenet=TenetKind.PROSELYTISM))
    feast = await record(session, "Feast", EntityType.TRADITION, world_id)
    session.add(TraditionProfileRow(tradition_entity_id=feast.id, kind=TraditionKind.OFFERING, effects={"piety": 2}))
    session.add(TraditionParticipationRow(tradition_entity_id=feast.id, community_entity_id=town.id, participation=100))
    await session.flush()
    await derive_tick_modifiers(make_ctx(session, RULES))
    law_rows = await _rows(session, ModifierSource.LAW)
    assert [(row.target_node_id, row.target_key, row.magnitude) for row in law_rows] == [(town.id, "defense", RULES.modifiers.law_standing_army_defense / 2)]
    treaty_rows = await _rows(session, ModifierSource.TREATY)
    assert {(row.target_node_id, row.target_key) for row in treaty_rows} == {(town.id, "wealth"), (other.id, "wealth")}
    structure = await _rows(session, ModifierSource.STRUCTURE)
    assert [(row.target_node_id, row.target_key, row.magnitude) for row in structure] == [(town.id, "piety", RULES.modifiers.structure_temple_piety)]
    doctrine = await _rows(session, ModifierSource.DOCTRINE)
    assert [(row.target_node_id, row.target_key) for row in doctrine] == [(cult.id, "influence")]
    tradition = await _rows(session, ModifierSource.TRADITION)
    assert [(row.target_node_id, row.target_key, row.magnitude) for row in tradition] == [(town.id, "piety", 2)]


async def test_curses_and_blessings_follow_their_flags_and_bonds(session: AsyncSession, world_id: int) -> None:
    town = await make(session, "Varn", EntityType.SETTLEMENT, world_id, population=900, prosperity=40, piety=20, wealth=30)
    hero = await make(session, "Asa", EntityType.MORTAL, world_id, strength=50, charisma=40, hp=30, age=20, lifespan=60)
    await add_flag(session, town.id, EntityFlag.CURSED, 1)
    await bond(session, town.id, hero.id, BondKind.BLESSED)
    await derive_tick_modifiers(make_ctx(session, RULES))
    curses = await _rows(session, ModifierSource.CURSE)
    assert {row.target_key for row in curses} == {"prosperity", "wealth"}
    assert all(row.op is ModifierOp.MULTIPLY and row.magnitude == RULES.modifiers.curse_stat_pct / PERCENT for row in curses)
    blessings = await _rows(session, ModifierSource.BLESSING)
    assert {(row.target_node_id, row.target_key, row.source_node_id) for row in blessings} == {(hero.id, "strength", town.id), (hero.id, "charisma", town.id)}


async def test_a_held_derived_modifier_survives_the_next_draw(session: AsyncSession, world_id: int) -> None:
    town = await make(session, "Varn", EntityType.SETTLEMENT, world_id, population=900, prosperity=40, wealth=30)
    await add_flag(session, town.id, EntityFlag.CURSED, 1)
    ctx = make_ctx(session, RULES)
    await derive_tick_modifiers(ctx)
    row = next(item for item in await _rows(session, ModifierSource.CURSE) if item.target_key == "prosperity")
    row.magnitude, row.held = 0.5, True
    await session.flush()
    await derive_tick_modifiers(ctx)
    prosperity = [item for item in await _rows(session, ModifierSource.CURSE) if item.target_key == "prosperity"]
    assert [(item.id, item.magnitude) for item in prosperity] == [(row.id, 0.5)]


@dataclass
class StubWeather:
    kind: WeatherKind
    effects: dict[WeatherEffect, int]

    def effect(self, effect: WeatherEffect) -> int:
        return self.effects.get(effect, 0)


@dataclass
class StubRegion:
    entity_id: int
    world_id: int
    dominant_terrain: TerrainKind
    seasonality: int


class StubBook:
    def __init__(self, region: StubRegion, weather: StubWeather) -> None:
        self.region = region
        self.sky = weather

    def region_of(self, entity_id: int) -> StubRegion:
        return self.region

    def growing_season(self, world_id: int) -> None:
        return None

    def travel_season(self, world_id: int) -> None:
        return None

    def weather(self, *args: object) -> StubWeather:
        return self.sky


async def test_ground_seasons_and_weather_become_modifiers(session: AsyncSession, world_id: int) -> None:
    town = await make(session, "Varn", EntityType.SETTLEMENT, world_id, population=900, prosperity=40, defense=20)
    army = await record(session, "Host", EntityType.ARMY, world_id, size=100, morale=60)
    region = StubRegion(entity_id=town.id, world_id=world_id, dominant_terrain=TerrainKind.MOUNTAINS, seasonality=50)
    weather = StubWeather(WeatherKind.BLIZZARD, {WeatherEffect.GROWTH: -40, WeatherEffect.MORALE: -20, WeatherEffect.COLD: 90})
    drafts = environment_drafts(make_ctx(session, RULES), cast(EnvironmentBook, StubBook(region, weather)), [town], [army])
    found = {(draft.target_node_id, draft.target_key, draft.source_kind): draft.magnitude for draft in drafts}
    assert found[(town.id, "defense", ModifierSource.TERRAIN)] == RULES.modifiers.terrain_rough_defense
    assert found[(town.id, "prosperity", ModifierSource.SEASON)] == pytest.approx(1 - 0.5 * RULES.modifiers.season_prosperity_pct / PERCENT)
    assert found[(town.id, "prosperity", ModifierSource.WEATHER)] == round(-40 * RULES.modifiers.weather_prosperity_pct / PERCENT)
    assert found[(army.id, "morale", ModifierSource.WEATHER)] < 0


class BountyLaws:
    def has(self, law: object, world_id: int | None) -> bool:
        return str(law).endswith("bounty")


async def test_natural_laws_multiply_fertility_without_drifting_its_base(session: AsyncSession, world_id: int) -> None:
    region = await make(session, "Vale", EntityType.REGION, world_id, fertility=60)
    ctx = make_ctx(session, RULES)
    ctx._laws = cast(LawBook, BountyLaws())
    await law_fertility(ctx)
    await law_fertility(ctx)
    rows = await _rows(session, ModifierSource.NATURAL_LAW)
    assert [(row.target_node_id, row.magnitude) for row in rows] == [(region.id, 1 + RULES.climate_effects.bounty_law_fertility / PERCENT)]
    index = await ModifierIndex.load(session, 10)
    with live_modifiers(index, 10, RULES):
        assert base_stat(region, "fertility") == 60
        assert stat(region, "fertility") == round(60 * (1 + RULES.climate_effects.bounty_law_fertility / PERCENT))


async def test_player_modifiers_on_growth_reach_the_virtual_key(session: AsyncSession, world_id: int) -> None:
    folk = await make(session, "Reed Folk", EntityType.PEOPLE, world_id, population=900)
    await add_modifier(session, ModifierDraft(folk.id, "growth", ModifierOp.MULTIPLY, 1.5, ModifierSource.PLAYER, "player.modifier", start_epoch=1))
    index = await ModifierIndex.load(session, 10)
    with live_modifiers(index, 10, RULES):
        assert virtual_value(folk.id, "growth") == 1.5
