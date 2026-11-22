from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.db.tables.bonds import BondRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.interconnect import IncidentRow
from aerona.db.tables.polity import ClaimRow, LawJurisdictionRow, LawProfileRow, PolityMemberRow, PolityProfileRow
from aerona.db.tables.restoration import RestorationRow
from aerona.db.tables.settlement import SettlementProfileRow
from aerona.domain.enums.bond import BondKind
from aerona.domain.enums.entity import EntityStatus, EntityType
from aerona.domain.enums.polity import ClaimBasis, DecisionRule, GovernmentKind, LawKind
from aerona.domain.enums.restoration import RestorationBasis, RestorationStage
from aerona.domain.enums.settlement import SizeTier
from aerona.domain.models.entity_stats import PolityStats
from aerona.engine.context import TickContext
from aerona.engine.polity.laws import enact
from aerona.engine.primitives.manual import manual_context
from aerona.engine.restoration.rise import RestorationTally, advance, press_claims, raise_movement, tend_restorations
from tests.engine.core.factories import CoreWorld, entity, mortal, settlement, tuned_rules


async def fallen_realm(session: AsyncSession, world: CoreWorld, *, unrest: int = 70) -> tuple[EntityRow, EntityRow]:
    town = await settlement(session, "Oldcrown", world, world.regions[0], population=3000)
    session.add(SettlementProfileRow(settlement_entity_id=town.id, size_tier=SizeTier.TOWN, unrest=unrest, locked=[]))
    fallen = await entity(session, "The Elder Realm", EntityType.POLITY, PolityStats(), world_id=world.world.id)
    fallen.status, fallen.end_epoch = EntityStatus.DEAD, 0
    session.add(
        PolityProfileRow(
            polity_entity_id=fallen.id,
            government=next(iter(GovernmentKind)),
            decision_rule=next(iter(DecisionRule)),
            core_entity_id=town.id,
            capital_entity_id=town.id,
            emblem={"field": "the old colours"},
        )
    )
    await session.flush()
    return fallen, town


async def claim_on(session: AsyncSession, world: CoreWorld, fallen: EntityRow, *, pressed: bool = False, name: str = "Aren Vost") -> EntityRow:
    pretender = await mortal(session, name, world, None)
    session.add(ClaimRow(claimant_entity_id=pretender.id, polity_entity_id=fallen.id, basis=next(iter(ClaimBasis)), pressed=pressed, locked=[]))
    await session.flush()
    return pretender


async def test_grievance_in_the_old_lands_turns_the_memory_of_a_fallen_realm_into_a_movement(ctx: TickContext, session: AsyncSession, world: CoreWorld) -> None:
    fallen, town = await fallen_realm(session, world)
    await claim_on(session, world, fallen)
    tally = await tend_restorations(ctx)
    row = await session.scalar(select(RestorationRow).where(RestorationRow.fallen_polity_id == fallen.id))
    assert row is not None and tally.begun == 1 and row.stage is RestorationStage.MOVEMENT and row.territories == [town.id]
    assert RestorationBasis.MEMORY.value in row.bases


async def test_a_rising_raises_the_old_realm_with_its_name_emblem_claims_and_laws(ctx: TickContext, session: AsyncSession, world: CoreWorld) -> None:
    fallen, town = await fallen_realm(session, world)
    pretender = await claim_on(session, world, fallen)
    await enact(ctx, fallen, LawKind.SERFDOM, {})
    tally = RestorationTally()
    row = await raise_movement(ctx, fallen, claimant=pretender.id, bases=[RestorationBasis.BLOODLINE], territories=[town.id], tally=tally)
    row.stage = RestorationStage.RISING
    assert await advance(ctx, row, tally) is RestorationStage.RESTORED
    restored = await session.get(EntityRow, row.restored_polity_id)
    assert restored is not None and restored.name == fallen.name and tally.restored == 1
    profile = await session.get(PolityProfileRow, restored.id)
    assert profile is not None and profile.emblem == {"field": "the old colours"}
    link = await session.scalar(select(BondRow).where(BondRow.source_node_id == restored.id, BondRow.kind == BondKind.DESCENDS_FROM))
    assert link is not None and link.target_node_id == fallen.id
    claim = await session.scalar(select(ClaimRow).where(ClaimRow.claimant_entity_id == pretender.id))
    assert claim is not None and claim.polity_entity_id == restored.id
    laws = (
        select(LawProfileRow.kind)
        .join(LawJurisdictionRow, LawJurisdictionRow.law_entity_id == LawProfileRow.law_entity_id)
        .where(LawJurisdictionRow.node_entity_id == restored.id)
    )
    assert LawKind.SERFDOM in set(await session.scalars(laws))


async def test_a_steady_realm_holding_the_old_lands_puts_the_rising_down(ctx: TickContext, session: AsyncSession, world: CoreWorld) -> None:
    fallen, town = await fallen_realm(session, world)
    holder = await entity(session, "The Steady Realm", EntityType.POLITY, PolityStats(), world_id=world.world.id)
    session.add(
        PolityProfileRow(
            polity_entity_id=holder.id, government=next(iter(GovernmentKind)), decision_rule=next(iter(DecisionRule)), core_entity_id=town.id, stability=90
        )
    )
    session.add(PolityMemberRow(polity_entity_id=holder.id, member_entity_id=town.id))
    tally = RestorationTally()
    row = await raise_movement(ctx, fallen, claimant=None, bases=[RestorationBasis.MEMORY], territories=[town.id], tally=tally)
    row.stage = RestorationStage.RISING
    assert await advance(ctx, row, tally) is RestorationStage.FAILED and tally.failed == 1
    assert await session.scalar(select(IncidentRow.id).where(IncidentRow.kind == "polity.restoration_failed")) is not None


async def test_an_unkept_memory_fades_and_the_movement_fails(session: AsyncSession, world: CoreWorld) -> None:
    ctx = await manual_context(session, "fade", tuned_rules(restoration={"memory_decay_per_epoch": 50}))
    fallen, town = await fallen_realm(session, world, unrest=0)
    row = await raise_movement(ctx, fallen, claimant=None, bases=[], territories=[town.id], tally=RestorationTally())
    row.memory = 10
    tally = await tend_restorations(ctx)
    assert row.stage is RestorationStage.FAILED and row.ended_epoch == ctx.epoch and tally.faded == 1


async def test_a_movement_with_enough_memory_rises(session: AsyncSession, world: CoreWorld) -> None:
    ctx = await manual_context(session, "rise", tuned_rules(restoration={"rising_chance_pct": 100, "memory_decay_per_epoch": 0}))
    fallen, town = await fallen_realm(session, world)
    row = await raise_movement(ctx, fallen, claimant=None, bases=[RestorationBasis.LAW], territories=[town.id], tally=RestorationTally())
    row.memory = 80
    tally = RestorationTally()
    assert await advance(ctx, row, tally) is RestorationStage.RISING and tally.rising == 1


async def test_pretenders_pressing_a_claim_on_a_fallen_realm_gain_a_restoration(ctx: TickContext, session: AsyncSession, world: CoreWorld) -> None:
    fallen, _town = await fallen_realm(session, world, unrest=0)
    pretender = await claim_on(session, world, fallen, pressed=True)
    claim = await session.scalar(select(ClaimRow).where(ClaimRow.claimant_entity_id == pretender.id))
    assert claim is not None
    claim.title_entity_id = fallen.id
    tally = RestorationTally()
    await press_claims(ctx, tally)
    row = await session.scalar(select(RestorationRow).where(RestorationRow.fallen_polity_id == fallen.id))
    assert row is not None and row.claimant_node_id == pretender.id and row.bases == [RestorationBasis.BLOODLINE.value] and tally.begun == 1
    row.stage = RestorationStage.FAILED
    later = await claim_on(session, world, fallen, pressed=True, name="Mira Vost")
    second = await session.scalar(select(ClaimRow).where(ClaimRow.claimant_entity_id == later.id))
    assert second is not None
    second.title_entity_id = fallen.id
    await session.flush()
    await press_claims(ctx, tally)
    raised = list(await session.scalars(select(RestorationRow).where(RestorationRow.fallen_polity_id == fallen.id).order_by(RestorationRow.id)))
    assert [item.claimant_node_id for item in raised] == [pretender.id, later.id] and tally.begun == 2
    raised[1].stage = RestorationStage.FAILED
    await press_claims(ctx, tally)
    assert tally.begun == 2


async def test_foreign_backing_carries_a_rising_past_a_steady_holder(ctx: TickContext, session: AsyncSession, world: CoreWorld) -> None:
    fallen, town = await fallen_realm(session, world)
    holder = await entity(session, "The Firm Realm", EntityType.POLITY, PolityStats(), world_id=world.world.id)
    rule = next(iter(DecisionRule))
    session.add(PolityProfileRow(polity_entity_id=holder.id, government=next(iter(GovernmentKind)), decision_rule=rule, core_entity_id=town.id, stability=70))
    session.add(PolityMemberRow(polity_entity_id=holder.id, member_entity_id=town.id))
    tally = RestorationTally()
    plain = await raise_movement(ctx, fallen, claimant=None, bases=[RestorationBasis.MEMORY], territories=[town.id], tally=tally)
    plain.stage = RestorationStage.RISING
    assert await advance(ctx, plain, tally) is RestorationStage.FAILED
    backed = await raise_movement(
        ctx, fallen, claimant=None, bases=[RestorationBasis.FOREIGN_BACKING, RestorationBasis.FAITH], territories=[town.id], tally=tally
    )
    backed.stage = RestorationStage.RISING
    assert await advance(ctx, backed, tally) is RestorationStage.RESTORED
    profile = await session.get(PolityProfileRow, backed.restored_polity_id)
    assert profile is not None and profile.legitimacy >= 15
