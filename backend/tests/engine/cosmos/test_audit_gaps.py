from dataclasses import dataclass, replace
from typing import Any

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.cartography.biomes import Biome
from aerona.constants.cartography import BIOME_COUNT
from aerona.core.random import RandomKey, SeededRandom
from aerona.db.repositories.entities import EntityRepository
from aerona.db.tables.anatomy import CreatureAttackRow
from aerona.db.tables.cosmos import AppliedFixupRow
from aerona.db.tables.divine import DivineWoundRow
from aerona.db.tables.ecology import BeastProfileRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.environment import RegionEnvironmentRow
from aerona.db.tables.military import SpyAgentRow, SpyNetworkRow
from aerona.db.tables.mortal import MarriageRow
from aerona.db.tables.physics import WorldPhysicsRow
from aerona.db.tables.settlement import SettlementProfileRow, SettlementTreasuryRow
from aerona.domain.enums.affliction import Transmission
from aerona.domain.enums.body import DamageType
from aerona.domain.enums.communication import SignalKind
from aerona.domain.enums.cosmography import DimensionKind, RiftCause, RiftState
from aerona.domain.enums.culture import Technique
from aerona.domain.enums.divine import DivineWoundKind, WoundCause
from aerona.domain.enums.ecology import AttackDelivery, AttackEffect, AttackRange
from aerona.domain.enums.entity import EntityFlag, EntityType
from aerona.domain.enums.environment import CoastKind, RiverClass, SoilKind, TemperatureBand, TerrainKind
from aerona.domain.enums.happening import RiverShiftCause
from aerona.domain.enums.intervention import Disaster
from aerona.domain.enums.material import MaterialKind
from aerona.domain.enums.military import AgentStatus
from aerona.domain.enums.mind import FocusKind, NeedKind
from aerona.domain.enums.mortal import MarriageEnd
from aerona.domain.enums.physics import CosmicFeatureKind
from aerona.domain.enums.relations import PersuasionAim
from aerona.domain.enums.settlement import SizeTier, TreasuryEntry
from aerona.domain.enums.son import SonDeathCause
from aerona.domain.enums.world import WorldType
from aerona.domain.models.entity_stats import BeastStats, LanguageStats, MortalStats, SettlementStats
from aerona.engine.communication import signals
from aerona.engine.context import TickContext
from aerona.engine.cosmos import physics_control
from aerona.engine.cosmos.features import omen_of
from aerona.engine.cosmos.ladder import DimensionDraft, create_dimension, ensure_ladder
from aerona.engine.cosmos.orbits import stony_share
from aerona.engine.cosmos.rifts import open_rift, tend_rift
from aerona.engine.cosmos.worldlife import tend_mood
from aerona.engine.divine.wounds import death_cause
from aerona.engine.ecology import beast_acts
from aerona.engine.environment import geomorph
from aerona.engine.environment.profile import Make, make_of, mineral_layers
from aerona.engine.lore.language import prestige_parts
from aerona.engine.military.siege import SackChoice, plunder_treasury
from aerona.engine.military.spycraft import retire_agents
from aerona.engine.mind import aspirations
from aerona.engine.mortal import course
from aerona.engine.mortal.kinship import marry
from aerona.engine.mortal.profile import ensure_profile
from aerona.engine.phases.disasters import DisasterWorld
from aerona.engine.phases.environment import fallback_geography
from aerona.engine.phases.physics import rescale_seams, settle_heavens
from aerona.engine.primitives.knowledge import LawBook
from aerona.engine.relations import persuasion
from aerona.engine.relations.persuasion import Argument, counsel_lift
from aerona.rules.registry import Rules
from tests.engine.cosmos.factories import EPOCH, Cosmos, make_entity, make_region, make_son, tick, tuned


def ground(region_id: int, world_id: int, **values: Any) -> RegionEnvironmentRow:
    base: dict[str, Any] = {
        "entity_id": region_id,
        "world_id": world_id,
        "dominant_terrain": TerrainKind.PLAIN,
        "elevation_mean": 20,
        "roughness": 20,
        "latitude": 40,
        "moisture": 50,
        "base_forest": 20,
        "forest_cover": 20,
        "base_wetland": 0,
        "wetland": 0,
        "river_class": RiverClass.NONE,
        "coast_kind": CoastKind.NONE,
        "soil": SoilKind.LOAM,
        "soil_fertility": 50,
        "soil_base": 50,
        "temperature": 15,
        "temperature_band": TemperatureBand.TEMPERATE,
        "rainfall": 50,
        "seasonality": 50,
        "disease_load": 10,
        "magic_density": 10,
        "defensibility": 20,
    }
    return RegionEnvironmentRow(**{**base, **values})


async def test_a_steady_rift_shrinks_as_a_closing_rift(ctx: TickContext, cosmos: Cosmos) -> None:
    await ensure_ladder(ctx.session, ctx.rules)
    plane = await create_dimension(ctx.session, ctx.rules, DimensionDraft("Astral Reach", DimensionKind.ASTRAL, ctx.epoch))
    region = await make_region(ctx.session, "Torn Field", cosmos.home.id)
    rift = await open_rift(ctx, cosmos.home, region, plane, RiftCause.GOD)
    rift.stability = 90
    await tend_rift(ctx, rift)
    assert rift.state is RiftState.OPEN
    await tend_rift(ctx, rift)
    assert rift.state is RiftState.CLOSING


async def test_a_realm_of_alchemists_builds_sending_stones(ctx: TickContext, monkeypatch: pytest.MonkeyPatch) -> None:
    async def knows(session: AsyncSession, owner: int, technique: Technique) -> bool:
        return technique is Technique.ALCHEMY

    monkeypatch.setattr(signals, "has_technique", knows)
    assert await signals.known_kind(ctx, 1) is SignalKind.BOUND_PAIR


async def test_a_chancellor_counsels_the_rulers_decision(ctx: TickContext, monkeypatch: pytest.MonkeyPatch) -> None:
    aims: list[PersuasionAim] = []

    async def adviser(session: AsyncSession, polity_id: int, *kinds: Any) -> int:
        return 7

    async def argue(ctx: TickContext, speaker: int, listener: int, appeal: Any, aim: PersuasionAim, **kwargs: Any) -> Argument:
        aims.append(aim)
        return Argument(score=100, success=True, record_id=None)

    monkeypatch.setattr(persuasion, "office_holder", adviser)
    monkeypatch.setattr(persuasion, "persuade", argue)
    assert await counsel_lift(ctx, 1, 2, 1) > 1
    assert aims == [PersuasionAim.DECISION]
    assert await counsel_lift(ctx, 1, None, 1) == 1.0


async def test_a_cold_childless_marriage_is_annulled_where_divorce_is_forbidden(
    session: AsyncSession, cosmos: Cosmos, rules: Rules, monkeypatch: pytest.MonkeyPatch
) -> None:
    first = await make_entity(session, "Ama", EntityType.MORTAL, MortalStats(), world_id=cosmos.home.id)
    second = await make_entity(session, "Ber", EntityType.MORTAL, MortalStats(), world_id=cosmos.home.id)
    profile, _ = await ensure_profile(session, first.id, EPOCH)
    row = await marry(session, first, second, EPOCH)

    async def forbidden(ctx: TickContext, mortal: Any) -> str:
        return "forbidden"

    @dataclass
    class Cold:
        value: int = -100

    async def cold(*args: Any) -> Cold:
        return Cold()

    monkeypatch.setattr(course, "divorce_custom", forbidden)
    monkeypatch.setattr(course, "opinion", cold)
    assert await course.match(tick(session, tuned(rules, "kinship", annulment_chance=100)), first, profile) == "annulled"
    assert (await session.get(MarriageRow, row.id)).cause_end is MarriageEnd.ANNULMENT


async def test_a_sacked_city_loses_its_treasury_to_the_victor(session: AsyncSession, ctx: TickContext, cosmos: Cosmos) -> None:
    town = await make_entity(session, "Ardun", EntityType.SETTLEMENT, SettlementStats(), world_id=cosmos.home.id)
    victor = await make_entity(session, "Varn", EntityType.SETTLEMENT, SettlementStats(), world_id=cosmos.home.id)
    profile = SettlementProfileRow(settlement_entity_id=town.id, size_tier=next(iter(SizeTier)), treasury=1000)
    session.add(profile)
    await session.flush()
    seized = await plunder_treasury(ctx, town, victor, SackChoice.SACK)
    assert seized == 1000 * ctx.rules.siege_depth.treasury_sack_pct // 100 and profile.treasury == 1000 - seized
    entry = await session.scalar(select(SettlementTreasuryRow).where(SettlementTreasuryRow.settlement_entity_id == town.id))
    assert entry is not None and entry.entry is TreasuryEntry.PLUNDER


async def test_a_son_slain_by_a_sibling_dies_of_it(session: AsyncSession, cosmos: Cosmos) -> None:
    victim = await make_son(session, "Veyr", world_id=cosmos.home.id)
    slayer = await make_son(session, "Oth", world_id=cosmos.home.id)
    wound = DivineWoundRow(god_node_id=victim.id, kind=DivineWoundKind.SHATTERED_MANIFESTATION, severity=80, healed=0, cause=WoundCause.DUEL)
    wound.cause_node_id = slayer.id
    session.add(wound)
    await session.flush()
    assert await death_cause(session, victim.id) is SonDeathCause.KILLED_BY_SIBLING
    assert await death_cause(session, slayer.id) is SonDeathCause.FADING


async def test_a_spy_retires_after_long_service(session: AsyncSession, cosmos: Cosmos, rules: Rules) -> None:
    owner = await make_entity(session, "Varn", EntityType.SETTLEMENT, SettlementStats(), world_id=cosmos.home.id)
    target = await make_entity(session, "Ardun", EntityType.SETTLEMENT, SettlementStats(), world_id=cosmos.home.id)
    network = SpyNetworkRow(owner_entity_id=owner.id, target_entity_id=target.id, since_epoch=1, agents=1)
    session.add(network)
    await session.flush()
    agent = SpyAgentRow(network_id=network.id, since_epoch=1, locked=[])
    session.add(agent)
    await session.flush()
    later = tick(session, rules, epoch=1 + rules.espionage.agent_service_epochs)
    assert await retire_agents(later, network) == 1
    assert agent.status is AgentStatus.RETIRED and network.agents == 0


async def test_an_earthquake_can_move_a_river(session: AsyncSession, cosmos: Cosmos, rules: Rules, monkeypatch: pytest.MonkeyPatch) -> None:
    region = await make_region(session, "Riverland", cosmos.home.id)
    session.add(ground(region.id, cosmos.home.id, river_class=RiverClass.RIVER))
    await session.flush()
    causes: list[RiverShiftCause] = []

    async def shifted(ctx: TickContext, source: int, target: Any, cause: RiverShiftCause, **kwargs: Any) -> str:
        causes.append(cause)
        return "moved"

    monkeypatch.setattr(geomorph, "shift_river", shifted)
    sure = tuned(rules, "geomorphology", river_shift_chance=100, river_shift_severity=0)
    assert await geomorph.river_after_quake(tick(session, sure), region, 100, region) == "moved"
    assert causes == [RiverShiftCause.QUAKE]


async def test_a_revived_language_holds_the_pride_of_its_revival(ctx: TickContext, cosmos: Cosmos) -> None:
    tongue = await make_entity(ctx.session, "Old Tongue", EntityType.LANGUAGE, LanguageStats(), world_id=cosmos.home.id)
    await EntityRepository(ctx.session).add_flag(tongue.id, EntityFlag.REVIVED_LANGUAGE, ctx.epoch)
    assert (await prestige_parts(ctx, tongue))["the pride of its revival"] == ctx.rules.prestige.revival


async def test_each_breath_strikes_in_its_own_way(ctx: TickContext, cosmos: Cosmos, monkeypatch: pytest.MonkeyPatch) -> None:
    beast = await make_entity(ctx.session, "Wyrm", EntityType.BEAST, BeastStats(), world_id=cosmos.home.id)
    town = await make_entity(ctx.session, "Ardun", EntityType.SETTLEMENT, SettlementStats(), world_id=cosmos.home.id)
    dweller = await make_entity(ctx.session, "Ama", EntityType.MORTAL, MortalStats(), world_id=cosmos.home.id, location_id=town.id)
    struck: list[Any] = []

    async def folk(ctx: TickContext, town: Any) -> list[Any]:
        return [dweller]

    async def hit(ctx: TickContext, bearer: Any, harm: Any, **kwargs: Any) -> None:
        struck.append(harm.damage_type)

    async def poison(ctx: TickContext, bearer: Any, package: Any, how: Transmission, **kwargs: Any) -> None:
        struck.append(how)

    async def snatch(ctx: TickContext, beast: Any, row: Any, town: Any, description: str) -> Any:
        struck.append(description)
        return dweller

    monkeypatch.setattr(beast_acts, "townsfolk", folk)
    monkeypatch.setattr(beast_acts, "apply_hits", hit)
    monkeypatch.setattr(beast_acts, "afflict", poison)
    monkeypatch.setattr(beast_acts, "seize", snatch)
    lair = BeastProfileRow(beast_entity_id=beast.id)
    for delivery, effect in (
        (AttackDelivery.BREATH, AttackEffect.HEAT),
        (AttackDelivery.BREATH, AttackEffect.COLD),
        (AttackDelivery.BREATH, AttackEffect.VENOM),
        (AttackDelivery.SPRAY, AttackEffect.ENTANGLE),
    ):
        attack = CreatureAttackRow(node_id=beast.id, delivery=delivery, effect=effect, range=AttackRange.NEAR, recharge=0, permanent=False)
        attack.locked = []
        await beast_acts.strike(ctx, beast, lair, town, attack)
    assert struck == [DamageType.FIRE, DamageType.COLD, Transmission.INHALATION, "taken by the spray of " + beast.name]


async def test_a_mortal_given_to_pleasure_takes_up_a_life_of_leisure(
    session: AsyncSession, ctx: TickContext, cosmos: Cosmos, monkeypatch: pytest.MonkeyPatch
) -> None:
    mortal = await make_entity(session, "Ama", EntityType.MORTAL, MortalStats(), world_id=cosmos.home.id)

    async def needs(session: AsyncSession, mortal_id: int) -> dict[NeedKind, int]:
        return {NeedKind.PLEASURE: 100}

    monkeypatch.setattr(aspirations, "needs_of", needs)
    assert await aspirations.settle_focus(ctx, mortal) is FocusKind.LEISURE


async def test_a_living_world_withdraws_into_itself_and_wakes_when_its_land_rests(ctx: TickContext, cosmos: Cosmos) -> None:
    cosmos.home.world_type, cosmos.home.mood = WorldType.LIVING, -95
    region = await make_region(ctx.session, "Scarred Vale", cosmos.home.id)
    land = ground(region.id, cosmos.home.id, mined=90, cleared=90)
    ctx.session.add(land)
    await ctx.session.flush()
    await tend_mood(ctx, cosmos.home, [land], 0)
    assert cosmos.home.consciousness_closed
    land.mined = land.cleared = 0
    await tend_mood(ctx, cosmos.home, [land], 0)
    assert not cosmos.home.consciousness_closed


async def test_a_comets_omen_weight_sets_how_often_it_moves_peoples(ctx: TickContext, cosmos: Cosmos) -> None:
    comet = await physics_control.create_feature(ctx, CosmicFeatureKind.PERIODIC_COMET, "Ashtail", {"star_id": cosmos.star.id})
    assert comet.omen_weight == 50 and omen_of(comet) == 1.0
    comet.omen_weight = 100
    assert omen_of(comet) == 2.0


def test_restless_ground_shakes_and_burning_hearts_erupt_more(rules: Rules) -> None:
    body = WorldPhysicsRow(world_id=1, tectonics=100, volcanism=40)
    world = DisasterWorld(LawBook({}), {}, bodies={1: body})
    assert world.nature_mult(rules, 1, Disaster.EARTHQUAKE) == 100 / rules.planetary_climate.tectonics_reference
    assert world.nature_mult(rules, 1, Disaster.ERUPTION) == 40 / rules.planetary_climate.volcanism_reference
    assert world.nature_mult(rules, 1, Disaster.FLOOD) == 1.0


def test_a_world_rich_in_iron_holds_richer_metal_seams(rules: Rules) -> None:
    iron = make_of(rules, WorldPhysicsRow(iron=60, rock=60, exotic=0))
    assert iron.metal == 2.0 and iron.stone == 1.0 and iron.rare == 1.0
    mix = [0] * BIOME_COUNT
    mix[Biome.DRY_HILLS] = 100
    geography = replace(fallback_geography(rules, EntityRow(is_water=False)), biome_mix=mix)
    plain = mineral_layers(rules, SeededRandom(RandomKey(7, 1, "seams")), geography, WorldType.ORDINARY, TerrainKind.HILLS, make=Make())
    rich = mineral_layers(rules, SeededRandom(RandomKey(7, 1, "seams")), geography, WorldType.ORDINARY, TerrainKind.HILLS, make=iron)
    assert rich.get(MaterialKind.IRON.value, 0) > plain.get(MaterialKind.IRON.value, 0)


def test_an_icy_body_warms_little_from_its_volcanoes() -> None:
    assert stony_share(WorldPhysicsRow(iron=10, rock=10, ice=80, gas=0)) == 0.2
    assert stony_share(WorldPhysicsRow(iron=30, rock=70, ice=0, gas=0)) == 1.0


async def test_seams_already_laid_follow_the_make_of_their_world_once(session: AsyncSession, cosmos: Cosmos, rules: Rules) -> None:
    await settle_heavens(session, rules)
    physics = await session.get(WorldPhysicsRow, cosmos.home.id)
    assert physics is not None
    physics.iron = 60
    region = await make_region(session, "Hills", cosmos.home.id)
    land = ground(region.id, cosmos.home.id, mineral_layers={"iron": 20, "stone": 30})
    session.add(land)
    await session.execute(AppliedFixupRow.__table__.delete().where(AppliedFixupRow.key.like("world_make.%")))
    await session.flush()
    assert await rescale_seams(session, rules) >= 1
    assert land.mineral_layers["iron"] == 40 and land.mineral_layers["stone"] == round(30 * physics.rock / rules.orbits.rock_reference)
    assert await rescale_seams(session, rules) == 0
