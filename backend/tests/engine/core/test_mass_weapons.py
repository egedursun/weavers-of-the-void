from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.db.repositories.cosmos import CosmosRepository
from aerona.db.tables.culture import HolderTechniqueRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.interconnect import IncidentRow
from aerona.db.tables.mass_weapons import DeterrencePostureRow, MassWeaponRow, WarRemnantRow
from aerona.db.tables.mind import MemoryRow
from aerona.db.tables.polity import PolityMemberRow, PolityProfileRow, TreatyClauseRow, TreatyProfileRow
from aerona.db.tables.warfare import BattleRow, WarRow, WarSideRow
from aerona.domain.enums.bond import BondKind
from aerona.domain.enums.culture import Technique
from aerona.domain.enums.entity import EntityType
from aerona.domain.enums.mass_weapons import MassHarm, MassReach, Posture, ProgrammeStage, RemnantKind
from aerona.domain.enums.polity import ClauseKind, DecisionRule, GovernmentKind, TreatyKind
from aerona.domain.enums.war import BattleOutcome, WarCause, WarSide
from aerona.domain.models.entity_stats import EventStats, PolityStats
from aerona.engine.context import TickContext
from aerona.engine.mass_weapons.book import ArsenalTally
from aerona.engine.mass_weapons.deterrence import DETERRENCE_CAP, declare, deterrence, expose_bluffs
from aerona.engine.mass_weapons.limits import bind_arsenals, past_limit
from aerona.engine.mass_weapons.programme import begin, work_on
from aerona.engine.mass_weapons.remnants import after_wars, clear, tend_remnants
from aerona.engine.mass_weapons.use import use_weapon
from aerona.engine.primitives.manual import manual_context
from aerona.engine.primitives.stats import stat
from aerona.engine.services.war import held_back
from tests.engine.core.factories import CoreWorld, bond, entity, settlement, tuned_rules


def stage_of(weapon: MassWeaponRow) -> ProgrammeStage:
    return weapon.stage


async def realm(session: AsyncSession, world: CoreWorld, name: str, region: int = 0) -> tuple[EntityRow, EntityRow]:
    town = await settlement(session, f"{name} Seat", world, world.regions[region], population=5000)
    polity = await entity(session, name, EntityType.POLITY, PolityStats(), world_id=world.world.id)
    rule = next(iter(DecisionRule))
    session.add(PolityProfileRow(polity_entity_id=polity.id, government=next(iter(GovernmentKind)), decision_rule=rule, core_entity_id=town.id, treasury=5000))
    session.add(PolityMemberRow(polity_entity_id=polity.id, member_entity_id=town.id))
    await session.flush()
    return polity, town


async def test_a_programme_grows_ready_through_its_stages_and_rivals_see_it(session: AsyncSession, world: CoreWorld) -> None:
    ctx = await manual_context(session, "programme", tuned_rules(mass_weapons={"readiness_step": 100, "stage_visibility_pct": 100}))
    holder, _town = await realm(session, world, "The Forging Crown")
    rival, _seat = await realm(session, world, "The Watching Crown", 1)
    await bond(session, holder.id, rival.id, BondKind.ENEMY)
    tally = ArsenalTally()
    weapon = await begin(ctx, holder, MassHarm.BLAST, MassReach.REGION, tally)
    assert weapon.stage is ProgrammeStage.SOUGHT and rival.id in weapon.seen_by
    await work_on(ctx, weapon, tally)
    await work_on(ctx, weapon, tally)
    assert stage_of(weapon) is ProgrammeStage.READY and weapon.count == 1 and tally.built == 1


async def test_a_credible_posture_holds_attackers_back_and_a_bluff_is_exposed(session: AsyncSession, world: CoreWorld) -> None:
    ctx = await manual_context(session, "posture", tuned_rules(mass_weapons={"deterrence_attack_cut_pct": 100, "bluff_exposure_pct": 100}))
    holder, town = await realm(session, world, "The Warding Crown")
    attacker, _seat = await realm(session, world, "The Hungry Crown", 1)
    bystander, _other = await realm(session, world, "The Idle Crown", 2)
    tally = ArsenalTally()
    posture = await declare(ctx, holder, attacker.id, Posture.FIRST_USE, tally)
    posture.credibility = 100
    assert await deterrence(ctx, attacker.id, town.id) == DETERRENCE_CAP
    assert await deterrence(ctx, bystander.id, town.id) == 0
    await expose_bluffs(ctx, tally)
    assert posture.credibility == 100 - ctx.rules.mass_weapons.bluff_loss and tally.bluffs == 1


async def test_a_use_kills_across_its_reach_leaves_a_remnant_is_remembered_and_nears_the_end(ctx: TickContext, session: AsyncSession, world: CoreWorld) -> None:
    holder, _seat = await realm(session, world, "The Grim Crown", 1)
    victim, town = await realm(session, world, "The Struck Crown")
    weapon = MassWeaponRow(holder_entity_id=holder.id, harm=MassHarm.BLAST, reach=MassReach.REGION, stage=ProgrammeStage.READY, count=1, seen_by=[], locked=[])
    session.add(weapon)
    await session.flush()
    cosmos = await CosmosRepository(session).require_cosmos()
    doom, people = cosmos.doom_clock, stat(town, "population") or 0
    killed = await use_weapon(ctx, weapon, town, ArsenalTally())
    assert killed > 0 and (stat(town, "population") or 0) == people - killed and weapon.count == 0
    remnant = await session.scalar(select(WarRemnantRow).where(WarRemnantRow.region_entity_id == world.regions[0].id))
    assert remnant is not None and remnant.kind is RemnantKind.BURIED_CHARGES and remnant.weapon_id == weapon.id
    assert cosmos.doom_clock > doom or cosmos.doom_fraction > 0
    grief = await session.scalar(select(MemoryRow).where(MemoryRow.holder_node_id == town.id, MemoryRow.subject_node_id == holder.id))
    assert grief is not None and grief.magnitude < 0 and victim.id != holder.id
    assert await session.scalar(select(IncidentRow.id).where(IncidentRow.kind == "war.mass_weapon_used")) is not None


async def test_remnants_harm_those_who_live_with_them_fade_and_are_cleared(ctx: TickContext, session: AsyncSession, world: CoreWorld) -> None:
    owner, town = await realm(session, world, "The Scarred Crown")
    remnant = WarRemnantRow(region_entity_id=world.regions[0].id, kind=RemnantKind.FALLOUT, density=100, decay_per_epoch=10, locked=[])
    session.add(remnant)
    await session.flush()
    people = stat(town, "population") or 0
    await tend_remnants(ctx, ArsenalTally())
    assert (stat(town, "population") or 0) < people and remnant.density == 90
    tally = ArsenalTally()
    cleared = await clear(ctx, owner, world.regions[0].id, 1000, tally)
    assert cleared == ctx.rules.mass_weapons.clearance_per_budget * 10 and remnant.cleared == cleared and remnant.density == 90 - cleared


async def test_an_ended_war_fought_with_powder_leaves_buried_charges_where_it_was_fought(ctx: TickContext, session: AsyncSession, world: CoreWorld) -> None:
    first, town = await realm(session, world, "The Powder Crown")
    second, _seat = await realm(session, world, "The Pike Crown", 1)
    session.add(HolderTechniqueRow(holder_entity_id=first.id, technique=Technique.GUNPOWDER))
    event = await entity(session, "The Smoke War", EntityType.EVENT, EventStats(), world_id=world.world.id)
    war = WarRow(event_entity_id=event.id, world_id=world.world.id, cause=WarCause.HOSTILITY, started_epoch=0, ended_epoch=ctx.epoch)
    session.add(war)
    await session.flush()
    session.add_all(
        [
            WarSideRow(war_id=war.id, entity_id=first.id, side=WarSide.ATTACKER, joined_epoch=0),
            WarSideRow(war_id=war.id, entity_id=second.id, side=WarSide.DEFENDER, joined_epoch=0),
        ]
    )
    outcome = next(iter(BattleOutcome))
    session.add(
        BattleRow(
            war_id=war.id, epoch=ctx.epoch, sequence=1, place_entity_id=town.id, winner_entity_id=first.id, loser_entity_id=second.id, outcome=outcome, gap=1.0
        )
    )
    await session.flush()
    await after_wars(ctx, ArsenalTally())
    remnant = await session.scalar(select(WarRemnantRow).where(WarRemnantRow.war_id == war.id))
    assert remnant is not None and remnant.kind is RemnantKind.BURIED_CHARGES and remnant.region_entity_id == world.regions[0].id


async def test_armed_rivals_bind_their_arsenals_and_a_build_past_the_limit_breaks_it(session: AsyncSession, world: CoreWorld) -> None:
    ctx = await manual_context(session, "limit", tuned_rules(mass_weapons={"limit_treaty_chance_pct": 100}))
    first, _town = await realm(session, world, "The First Arsenal")
    second, _seat = await realm(session, world, "The Second Arsenal", 1)
    weapons = [
        MassWeaponRow(holder_entity_id=holder.id, harm=MassHarm.FIRE, reach=MassReach.SETTLEMENT, stage=ProgrammeStage.READY, count=1, seen_by=[], locked=[])
        for holder in (first, second)
    ]
    session.add_all(weapons)
    await session.flush()
    tally = ArsenalTally()
    await bind_arsenals(ctx, tally)
    treaty = await session.scalar(select(TreatyProfileRow).where(TreatyProfileRow.kind == TreatyKind.ARMS_LIMIT))
    assert treaty is not None and tally.treaties == 1
    clause = await session.scalar(
        select(TreatyClauseRow).where(TreatyClauseRow.kind == ClauseKind.MASS_WEAPON_LIMIT, TreatyClauseRow.obligor_node_id == first.id)
    )
    assert clause is not None and not await past_limit(ctx, {first.id}, clause)
    weapons[0].count = 2
    assert await past_limit(ctx, {first.id}, clause)
    assert await session.scalar(select(DeterrencePostureRow.id)) is None


async def test_a_declaration_of_war_on_a_deterring_holder_is_held_back(session: AsyncSession, world: CoreWorld) -> None:
    ctx = await manual_context(session, "deterred", tuned_rules(mass_weapons={"deterrence_attack_cut_pct": 100}))
    holder, town = await realm(session, world, "The Feared Crown")
    attacker, _seat = await realm(session, world, "The Bold Crown", 1)
    posture = await declare(ctx, holder, None, Posture.RETALIATION_ONLY, ArsenalTally())
    posture.credibility = 100
    assert await held_back(ctx, attacker.id, town.id, brokered=False)
    assert not await held_back(ctx, attacker.id, town.id, brokered=True)
