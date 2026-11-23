from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.catalog.life.powers import KEEP_APART_GIFTED_ATTITUDES, STANCE_ATTITUDE
from aerona.db.repositories.cosmos import CosmosRepository
from aerona.db.tables.concealment import HiddenTruthRow, PublicKnowledgeRow, TruthKeeperRow
from aerona.db.tables.ecology import SpeciesRangeRow
from aerona.db.tables.interconnect import IncidentRow
from aerona.db.tables.living import LivingLineRow, LivingLineTraitRow
from aerona.db.tables.mortal import MortalProfileRow
from aerona.db.tables.powers import PowerRow
from aerona.db.tables.warfare import CaptiveRow
from aerona.domain.enums.arcana import SpellForm, SpellTechnique
from aerona.domain.enums.bond import BondKind
from aerona.domain.enums.concealment import BreachCause, ConcealScope, HiddenTruthKind, KeeperRole
from aerona.domain.enums.ecology import RangeTrend
from aerona.domain.enums.entity import EntityStatus
from aerona.domain.enums.living import CultivationMethod, Fertility, LineOutcome, LineTrait
from aerona.domain.enums.powers import GiftedAttitude, GiftedStance, PowerOrigin, PowerState
from aerona.domain.enums.war import CaptiveStatus
from aerona.engine.concealment.truths import pass_on, slipped, strike_bargain
from aerona.engine.context import TickContext
from aerona.engine.living.lines import cross_wild
from aerona.engine.powers.kinds import others_in_danger
from aerona.engine.powers.phase import bind, transfer_power
from aerona.engine.powers.sources import take_cost
from aerona.engine.primitives.manual import manual_context
from aerona.engine.primitives.queries import connect
from tests.engine.core.factories import CoreWorld, mortal, tuned_rules


async def at(session: AsyncSession, epoch: int = 3, **rules: dict[str, int]) -> TickContext:
    cosmos = await CosmosRepository(session).require_cosmos()
    cosmos.epoch = epoch
    await session.flush()
    return await manual_context(session, "deepening_10", rules=tuned_rules(**rules))


def power(holder_id: int, strength: int = 6) -> PowerRow:
    return PowerRow(
        holder_node_id=holder_id,
        technique=SpellTechnique.PERCEIVE,
        form=SpellForm.MIND,
        strength=strength,
        control=50,
        origin=PowerOrigin.BORN,
        state=PowerState.ACTIVE,
        strain=0,
        strain_cap=50,
        uses=0,
        gained_epoch=1,
        locked=[],
    )


async def test_a_power_taken_from_another_leaves_its_first_holder_and_loses_strength(session: AsyncSession, world: CoreWorld) -> None:
    ctx = await at(session, powers={"transfer_loss_pct": 50})
    victim = await mortal(session, "Victim", world, world.regions[0].id)
    taker = await mortal(session, "Taker", world, world.regions[0].id)
    row = power(victim.id, 6)
    session.add(row)
    await session.flush()
    await transfer_power(ctx, row, victim, taker)
    assert row.holder_node_id == taker.id and row.origin is PowerOrigin.TRANSFER and row.strength == 3
    assert await session.scalar(select(IncidentRow.id).where(IncidentRow.kind == "power.transferred")) is not None


async def test_a_captive_power_is_bound_and_returns_when_freed(session: AsyncSession, world: CoreWorld) -> None:
    ctx = await at(session)
    holder = await mortal(session, "Captive Gifted", world, world.regions[0].id)
    captor = await mortal(session, "Captor", world, world.regions[0].id)
    row = power(holder.id)
    captive = CaptiveRow(captive_entity_id=holder.id, captor_entity_id=captor.id, status=CaptiveStatus.HELD, taken_epoch=1, locked=[])
    session.add_all([row, captive])
    await session.flush()
    await bind(ctx, row, holder)
    assert row.state is PowerState.BOUND
    captive.status = CaptiveStatus.RELEASED
    await session.flush()
    await bind(ctx, row, holder)
    assert row.state is PowerState.ACTIVE


async def test_kin_in_danger_wake_a_power_and_costs_fall_on_regard_and_fertility(session: AsyncSession, world: CoreWorld) -> None:
    ctx = await at(session)
    holder = await mortal(session, "Parent", world, world.regions[0].id)
    child = await mortal(session, "Child", world, world.regions[0].id, hp=5)
    await connect(session, holder.id, child.id, BondKind.PARENT_OF, 1)
    assert await others_in_danger(ctx, holder)
    profile = MortalProfileRow(entity_id=holder.id, fertility=50, infamy=0, locked=[])
    session.add(profile)
    await session.flush()
    await take_cost(ctx, holder, "fertility", 10)
    await take_cost(ctx, holder, "regard", 10)
    assert profile.fertility == 40 and profile.infamy > 0
    assert STANCE_ATTITUDE[GiftedStance.PITIED] is None
    assert GiftedAttitude.EXPLOITED in KEEP_APART_GIFTED_ATTITUDES


async def truth_about(session: AsyncSession, subject_id: int, scope: ConcealScope) -> HiddenTruthRow:
    truth = HiddenTruthRow(
        title="where the refuge lies",
        description="",
        subject_node_id=subject_id,
        kind=HiddenTruthKind.LOCATION,
        hidden_from=scope,
        strength=0,
        founded_epoch=1,
        tended_epoch=1,
        locked=[],
    )
    session.add(truth)
    await session.flush()
    return truth


async def test_children_let_slip_a_secret_and_go_betweens_turn_finders_into_keepers(session: AsyncSession, world: CoreWorld) -> None:
    ctx = await at(session, concealment={"children_breach": 100})
    keeper = await mortal(session, "Keeper", world, world.regions[0].id)
    baby = await mortal(session, "Baby", world, world.regions[0].id)
    baby.birth_epoch = ctx.epoch
    await connect(session, keeper.id, baby.id, BondKind.PARENT_OF, 1)
    truth = await truth_about(session, keeper.id, ConcealScope.A_HOUSE)
    assert await slipped(ctx, truth) is BreachCause.CHILDREN
    finder = await mortal(session, "Finder", world, world.regions[0].id)
    row = PublicKnowledgeRow(truth_id=truth.id, population_node_id=world.regions[0].id, know_pct=60, believe_pct=0, updated_epoch=1, locked=[])
    session.add(row)
    await session.flush()
    await strike_bargain(ctx, truth, row, [finder.id])
    await session.flush()
    kept = set(await session.scalars(select(TruthKeeperRow.keeper_node_id).where(TruthKeeperRow.truth_id == truth.id)))
    assert finder.id in kept and row.know_pct < 60


async def test_a_house_truth_passes_to_the_heir_of_a_dead_keeper(session: AsyncSession, world: CoreWorld) -> None:
    ctx = await at(session)
    elder = await mortal(session, "Elder", world, world.regions[0].id)
    heir = await mortal(session, "Heir", world, world.regions[0].id)
    await connect(session, elder.id, heir.id, BondKind.PARENT_OF, 1)
    truth = await truth_about(session, elder.id, ConcealScope.A_HOUSE)
    keeper = TruthKeeperRow(truth_id=truth.id, keeper_node_id=elder.id, role=KeeperRole.ARCHIVIST, locked=[])
    session.add(keeper)
    elder.status, elder.end_epoch = EntityStatus.DEAD, 2
    await session.flush()
    await pass_on(ctx, truth)
    assert keeper.keeper_node_id == heir.id


async def test_a_line_that_crosses_with_wild_kin_moves_their_fit(session: AsyncSession, world: CoreWorld) -> None:
    ctx = await at(session, living={"wild_cross_pct": 100})
    line = LivingLineRow(
        name="the bright line",
        method=CultivationMethod.HYBRIDISING,
        outcome=LineOutcome.EXCEEDED,
        stability=60,
        generation=1,
        drift_pct=0,
        fertility=Fertility.CROSSES_WILD,
        species_entity_id=world.species.id,
        founded_epoch=1,
        locked=[],
    )
    session.add(line)
    await session.flush()
    session.add(LivingLineTraitRow(line_id=line.id, trait=LineTrait.LIGHT_MAKING, strength=40, side_effect=False, locked=[]))
    wild = SpeciesRangeRow(
        species_entity_id=world.species.id,
        region_entity_id=world.regions[0].id,
        abundance=50,
        trend=RangeTrend.STEADY,
        fit=50,
        hunted=0,
        since_epoch=1,
        updated_epoch=1,
        locked=[],
    )
    session.add(wild)
    await session.flush()
    assert await cross_wild(ctx, line)
    assert wild.fit == 50 + ctx.rules.living.wild_cross_fit
