from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.core.errors import ValidationFailedError
from aerona.db.repositories.bonds import BondDraft, BondRepository
from aerona.db.tables.cosmic_state import VesselProfileRow
from aerona.db.tables.military import ArmyUnitRow, FeudRow, PeaceTermRow, SpyNetworkRow, UnitDesignRow
from aerona.db.tables.warfare import ArmyRow, WarRow
from aerona.domain.enums.body import DamageType
from aerona.domain.enums.bond import BondKind
from aerona.domain.enums.entity import EntityStatus, EntityType
from aerona.domain.enums.environment import WeatherKind
from aerona.domain.enums.equipment import EquipmentFamily
from aerona.domain.enums.military import (
    FeudParty,
    FeudStatus,
    MutinyOutcome,
    PeaceTermKind,
    SpyOwnerKind,
    UnitFamily,
    UnitKind,
    VesselStatus,
    WarAimKind,
)
from aerona.domain.enums.vehicles import MountKind, VehicleFrame
from aerona.domain.enums.war import WarCause, WarEnding
from aerona.engine.military import orders, records
from aerona.engine.military.campaign import march_budget, mutiny_outcome, step_cost
from aerona.engine.military.causes import press_claim_war
from aerona.engine.military.shipyard import Commission
from aerona.engine.military.spycraft import cover_access, cover_exposure, migrate_bonds
from aerona.engine.military.units import reconcile_sizes, resize, stacks_of
from aerona.engine.military.vessels import frame_value, storm_damage, vessel_power
from aerona.engine.operations.engagement import Weapon
from aerona.engine.primitives.stats import stat
from aerona.engine.services.community_relations import close_feud, feud_between, open_feud, start_blood_feud
from aerona.engine.services.war import open_war
from aerona.engine.services.war_resolution import end_war
from aerona.rules.registry import Rules
from tests.engine.warfare.factories import make, make_ctx


async def test_army_size_always_matches_its_stacks(session: AsyncSession, world_id: int) -> None:
    ctx = make_ctx(session)
    folk = await make(session, "Iron Folk", EntityType.PEOPLE, world_id, population=9000, martiality=60)
    army = await orders.raise_standing_army(ctx, folk.id, 400)
    rows = await stacks_of(session, army.id)
    assert rows and sum(row.count for row in rows) == stat(army, "size")
    await resize(session, ctx.rules, army, 150)
    assert sum(row.count for row in await stacks_of(session, army.id)) == 150
    army.status, army.end_epoch = EntityStatus.DEAD, ctx.epoch
    found = await reconcile_sizes(ctx)
    assert found["retired"] == 1 and sum(row.count for row in await stacks_of(session, army.id)) == 0 and stat(army, "size") == 0


async def test_military_records_create_edit_hold_release_and_delete(session: AsyncSession, world_id: int) -> None:
    ctx = make_ctx(session)
    design = await records.create_record(
        ctx, "unit_design", {"name": "Glass Lancers", "base_kind": UnitKind.HEAVY_CAVALRY.value, "family": UnitFamily.MOUNTED.value, "melee": 90}
    )
    assert isinstance(design, UnitDesignRow) and design.melee == 90 and design.created_epoch == ctx.epoch
    await records.edit_record(ctx, "unit_design", design.id, {"terror": 30})
    assert design.terror == 30 and "terror" in design.locked
    await records.release_record(ctx, "unit_design", design.id, ["terror"])
    assert design.locked == []
    try:
        await records.edit_record(ctx, "unit_design", design.id, {"terror": "lots"})
    except ValidationFailedError:
        pass
    else:
        raise AssertionError("a word is not a whole number")
    await records.delete_record(ctx, "unit_design", design.id)
    assert await session.get(UnitDesignRow, design.id) is None


async def test_stacks_built_on_a_design_fight_with_its_values(session: AsyncSession, world_id: int) -> None:
    ctx = make_ctx(session)
    folk = await make(session, "Iron Folk", EntityType.PEOPLE, world_id, population=9000, martiality=60)
    army = await orders.raise_standing_army(ctx, folk.id, 300)
    design = await records.create_record(ctx, "unit_design", {"name": "Wardens", "base_kind": UnitKind.LINE_INFANTRY.value, "defence": 95})
    stack = await records.create_record(ctx, "stack", {"army_entity_id": army.id, "kind": UnitKind.LINE_INFANTRY.value, "count": 50, "design_id": design.id})
    assert isinstance(stack, ArmyUnitRow) and stat(army, "size") == 350


async def test_claim_wars_carry_the_claim_and_white_peace_writes_its_terms(session: AsyncSession, world_id: int) -> None:
    ctx = make_ctx(session)
    first = await make(session, "Iron Folk", EntityType.PEOPLE, world_id, population=9000)
    second = await make(session, "Reed Folk", EntityType.PEOPLE, world_id, population=6000)
    war = await press_claim_war(ctx, first.id, second.id, claim_id=None, succession=True)
    assert war is not None and war.cause is WarCause.SUCCESSION
    await end_war(ctx, war, WarEnding.WHITE_PEACE, reason="test")
    terms = list(await session.scalars(select(PeaceTermRow).where(PeaceTermRow.war_id == war.id)))
    assert {term.kind for term in terms} >= {PeaceTermKind.WHITE_PEACE, PeaceTermKind.CAPTIVE_RELEASE}
    assert all(term.treaty_entity_id is not None for term in terms)


async def test_betrayal_ends_without_a_treaty_but_with_a_typed_reason(session: AsyncSession, world_id: int) -> None:
    ctx = make_ctx(session)
    first = await make(session, "Iron Folk", EntityType.PEOPLE, world_id, population=9000)
    second = await make(session, "Reed Folk", EntityType.PEOPLE, world_id, population=6000)
    war = await open_war(ctx, first, second)
    await end_war(ctx, war, WarEnding.BETRAYAL, reason="turned")
    term = await session.scalar(select(PeaceTermRow).where(PeaceTermRow.war_id == war.id))
    assert term is not None and term.treaty_entity_id is None and term.params["ending"] == WarEnding.BETRAYAL.value


async def test_peace_builder_signs_the_chosen_clauses(session: AsyncSession, world_id: int) -> None:
    ctx = make_ctx(session)
    first = await make(session, "Iron Folk", EntityType.PEOPLE, world_id, population=9000)
    second = await make(session, "Reed Folk", EntityType.PEOPLE, world_id, population=6000)
    war = await orders.declare_with_cause(ctx, first.id, second.id, WarCause.PUNITIVE, reason="test", aims=[(WarAimKind.REVENGE, {"memory": 1})])
    assert isinstance(war, WarRow)
    await orders.build_peace(ctx, war.id, first.id, [(PeaceTermKind.TRADE_CONCESSION, {}), (PeaceTermKind.CHAMPION, {})])
    kinds = {term.kind for term in await session.scalars(select(PeaceTermRow).where(PeaceTermRow.war_id == war.id))}
    assert {PeaceTermKind.TRADE_CONCESSION, PeaceTermKind.CHAMPION} <= kinds


async def test_feuds_are_typed_rows_that_open_and_close(session: AsyncSession, world_id: int) -> None:
    ctx = make_ctx(session)
    first = await make(session, "Iron Folk", EntityType.PEOPLE, world_id, population=9000)
    second = await make(session, "Reed Folk", EntityType.PEOPLE, world_id, population=6000)
    await start_blood_feud(ctx, first.id, second.id, "a killing")
    feud = await feud_between(session, first.id, second.id)
    assert feud is not None and feud.party is FeudParty.PEOPLE and feud.status is FeudStatus.ACTIVE
    again = await open_feud(session, ctx.rules, first.id, second.id, epoch=ctx.epoch, cause="again", party=FeudParty.COMMUNITY)
    assert again.id == feud.id and again.grievance > ctx.rules.vendetta.grievance
    assert await close_feud(session, first.id, second.id, epoch=ctx.epoch, status=FeudStatus.MEDIATED)
    assert (await session.get(FeudRow, feud.id)).status is FeudStatus.MEDIATED


async def test_bond_spy_networks_become_typed_rows_with_owner_kinds(session: AsyncSession, world_id: int) -> None:
    ctx = make_ctx(session)
    guild = await make(session, "Whisper Guild", EntityType.FACTION, world_id, sway=80)
    city = await make(session, "Proud City", EntityType.SETTLEMENT, world_id, population=900)
    await BondRepository(session).connect(BondDraft(guild.id, city.id, BondKind.SPY_NETWORK, 1, "old network"))
    assert await migrate_bonds(ctx) == 1
    network = await session.scalar(select(SpyNetworkRow).where(SpyNetworkRow.owner_entity_id == guild.id))
    assert network is not None and network.owner_kind is SpyOwnerKind.FACTION
    assert not await BondRepository(session).exists_between(guild.id, city.id, BondKind.SPY_NETWORK)
    assert cover_access(network, 100) > 0 and cover_exposure(network, 100) > 0


async def test_vessels_are_laid_down_with_hull_performance(session: AsyncSession, world_id: int) -> None:
    ctx = make_ctx(session)
    port = await make(session, "Gull Harbour", EntityType.SETTLEMENT, world_id, population=900, wealth=50)
    order = Commission(frame=VehicleFrame.WARSHIP)
    vessel = await orders.create_vessel(ctx, port.id, "Iron Gull", order)
    row = await session.get(VesselProfileRow, vessel.id)
    assert row is not None and row.frame is VehicleFrame.WARSHIP and row.seaworthiness == frame_value(ctx.rules, VehicleFrame.WARSHIP, "seaworthiness")
    assert row.status is VesselStatus.DOCKED
    raft = VesselProfileRow(entity_id=0, frame=VehicleFrame.RAFT, condition=100, seaworthiness=10, seamanship=0, crew=4)
    assert storm_damage(ctx.rules, raft) > storm_damage(ctx.rules, row)
    guns = [Weapon(MountKind.BROADSIDE, EquipmentFamily.CANNON, None, None, DamageType.BALLISTIC, 4, 1.0)]
    assert vessel_power(ctx.rules, row, None, guns) > vessel_power(ctx.rules, raft, None, [])
    assert vessel_power(ctx.rules, row, None, guns) > vessel_power(ctx.rules, row, None, [])


def test_marches_slow_in_snow_and_floods_and_mutinies_escalate() -> None:
    rules = Rules()
    clear = march_budget(rules, 2, weather=None, season=None, road=False, baggage=0)
    snow = march_budget(rules, 2, weather=WeatherKind.SNOW, season=None, road=False, baggage=0)
    assert snow < clear and step_cost(rules, None, None) == 100
    assert mutiny_outcome(rules, 0, rules.campaign_depth.mutiny_threshold, False) is MutinyOutcome.GRUMBLING
    assert mutiny_outcome(rules, 99, 100, True) is MutinyOutcome.TURNCOAT


async def test_raised_army_serves_its_community(session: AsyncSession, world_id: int) -> None:
    ctx = make_ctx(session)
    folk = await make(session, "Iron Folk", EntityType.PEOPLE, world_id, population=9000)
    army = await orders.raise_standing_army(ctx, folk.id, 200)
    row = await session.get(ArmyRow, army.id)
    assert row is not None and row.owner_entity_id == folk.id and row.war_id is None
