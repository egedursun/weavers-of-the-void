from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.catalog.life.made import CHARTER_REACH, OUTPUT_GOODS
from aerona.catalog.life_traits import ALLOCATION_MODE_TRAITS
from aerona.db.repositories.cosmos import CosmosRepository
from aerona.db.tables.cosmography import CosmicBeingProfileRow
from aerona.db.tables.interconnect import IncidentRow
from aerona.db.tables.intrigue import IdentityRow
from aerona.db.tables.made import AugmentRow, CompanyHoldingRow, MadeRelicRow
from aerona.db.tables.networks import NetworkNodeRow
from aerona.domain.enums.constructs import MindWill
from aerona.domain.enums.cosmography import BeingKind, BeingPhase
from aerona.domain.enums.economy import CommodityKind
from aerona.domain.enums.entity import EngineKind, EntityType
from aerona.domain.enums.intrigue import IdentityReason
from aerona.domain.enums.made import AugmentKind, AugmentMake, AugmentSlot, CompanyCharter, CompanyHoldingKind, RelicState, RelicUse, ReplicatorOutput
from aerona.domain.enums.minds import MakingOutcome, MindOrigin, MindUpkeep, WillCause
from aerona.domain.enums.networks import NetworkRole
from aerona.domain.enums.orders import AllocationMode
from aerona.domain.models.entity_stats import EventStats, FactionStats, StructureStats
from aerona.engine.augments import keep_one
from aerona.engine.context import TickContext
from aerona.engine.cosmos.beings import act, create_being
from aerona.engine.cosmos.placement import Cosmography
from aerona.engine.made.company_power import holding_places
from aerona.engine.made.intrusion import locate
from aerona.engine.made.relics import restore_or_dismantle
from aerona.engine.minds.kinds import will_cause
from aerona.engine.minds.making import apply_outcome, outcome_of
from aerona.engine.minds.profiles import profile_of
from aerona.engine.networks.phase import quaked
from aerona.engine.primitives.manual import manual_context
from aerona.engine.primitives.stats import stat
from tests.engine.core.factories import CoreWorld, entity, mortal, settlement, tuned_rules


async def at(session: AsyncSession, epoch: int = 3, **rules: dict[str, int]) -> TickContext:
    cosmos = await CosmosRepository(session).require_cosmos()
    cosmos.epoch = epoch
    await session.flush()
    return await manual_context(session, "deepening_9", rules=tuned_rules(**rules))


async def battle_on(session: AsyncSession, world: CoreWorld, epoch: int) -> None:
    fight = await entity(session, "A Battle", EntityType.EVENT, EventStats(), world_id=world.world.id, location_id=world.regions[0].id, birth_epoch=epoch)
    fight.engine_kind = EngineKind.BATTLE


async def test_a_living_world_answers_the_battles_fought_on_it(session: AsyncSession, world: CoreWorld) -> None:
    ctx = await at(session)
    town = await settlement(session, "Bloodied", world, world.regions[0])
    being = await create_being(ctx, BeingKind.LIVING_WORLD, world.world, phase=BeingPhase.MANIFEST)
    profile = await session.get(CosmicBeingProfileRow, being.id)
    assert profile is not None
    await battle_on(session, world, ctx.epoch)
    await session.flush()
    await act(ctx, await Cosmography.load(session), being, profile)
    assert stat(town, "prosperity") == 50 - ctx.rules.cosmic_beings.world_wrath
    answered = await session.scalar(select(IncidentRow.id).where(IncidentRow.kind == "being.world_answered"))
    assert answered is not None


async def test_a_mind_whose_kin_of_one_make_are_free_grows_its_will_by_kinship(session: AsyncSession, world: CoreWorld) -> None:
    ctx = await at(session)
    maker = await mortal(session, "Maker", world, world.regions[0].id)
    first = await mortal(session, "First", world, world.regions[0].id)
    second = await mortal(session, "Second", world, world.regions[0].id)
    rows = [await profile_of(session, ctx.rules, node.id, ctx.epoch) for node in (first, second)]
    for row in rows:
        row.origin, row.made_by_node_id = MindOrigin.MADE, maker.id
    rows[1].will = MindWill.FULL
    await session.flush()
    assert await will_cause(ctx, rows[0], 0, 0, conflict=0.0, free_near=False) is WillCause.KINSHIP
    assert outcome_of(await at(session, mind_making={"exceeded_pct": 100}), first.id, 100) is MakingOutcome.EXCEEDED
    before = rows[0].capacity
    apply_outcome(ctx, rows[0], MakingOutcome.EXCEEDED, MindWill.INSTRUCTED)
    assert rows[0].capacity > before


async def test_a_power_bound_augment_fails_when_its_bearer_holds_no_power(session: AsyncSession, world: CoreWorld) -> None:
    ctx = await at(session)
    bearer = await mortal(session, "Bound Bearer", world, world.regions[0].id)
    row = AugmentRow(
        bearer_node_id=bearer.id,
        slot=AugmentSlot.WHOLE_BODY,
        part=None,
        kind=AugmentKind.ENHANCEMENT,
        make=AugmentMake.POWER_BOUND,
        quality=70,
        upkeep=MindUpkeep.NONE,
        integration=80,
        strain=0,
        installed_epoch=1,
        locked=[],
    )
    session.add(row)
    await session.flush()
    await keep_one(ctx, bearer, row, 1)
    assert row.integration == 80 - ctx.rules.augments.power_bound_loss


async def test_a_quake_in_a_member_land_can_cut_a_network(session: AsyncSession, world: CoreWorld) -> None:
    ctx = await at(session)
    town = await settlement(session, "Wired Town", world, world.regions[0])
    quake = await entity(session, "Quake", EntityType.EVENT, EventStats(), world_id=world.world.id, location_id=world.regions[0].id, birth_epoch=ctx.epoch)
    quake.engine_kind = EngineKind.EARTHQUAKE
    await session.flush()
    rows = [NetworkNodeRow(network_entity_id=0, member_node_id=town.id, role=NetworkRole.END)]
    assert await quaked(ctx, rows)


async def test_location_data_lays_bare_one_who_hides_under_a_false_name(session: AsyncSession, world: CoreWorld) -> None:
    ctx = await at(session, intrusion={"location_exposure": 60})
    hidden = await mortal(session, "Hidden One", world, world.regions[0].id)
    identity = IdentityRow(mortal_node_id=hidden.id, false_name="Nobody", reason=IdentityReason.HIDDEN_POWER, exposure=50, since_epoch=1, locked=[])
    session.add(identity)
    await session.flush()
    await locate(ctx, hidden.id)
    assert identity.exposure == 100 and identity.exposed_epoch == ctx.epoch


async def test_land_holdings_reach_every_town_of_the_land(session: AsyncSession, world: CoreWorld) -> None:
    ctx = await at(session)
    first = await settlement(session, "Company Town", world, world.regions[0])
    second = await settlement(session, "Estate Town", world, world.regions[0])
    company = await entity(session, "Holding Company", EntityType.FACTION, FactionStats(), world_id=world.world.id)
    session.add(CompanyHoldingRow(company_entity_id=company.id, holding_node_id=world.regions[0].id, kind=CompanyHoldingKind.LAND))
    await session.flush()
    places = {town for town, _weight in await holding_places(ctx, company.id)}
    assert {first.id, second.id} <= places
    assert CHARTER_REACH[CompanyCharter.GUILD] == (False, False)


async def test_relics_are_restored_by_study_or_taken_apart_for_parts(session: AsyncSession, world: CoreWorld) -> None:
    ctx = await at(session)
    holder = await settlement(session, "Keepers", world, world.regions[0])
    thing = await entity(session, "Old Engine", EntityType.STRUCTURE, StructureStats(), world_id=world.world.id, location_id=holder.id)
    restored = MadeRelicRow(
        thing_node_id=thing.id,
        make_knowledge=3,
        repair_knowledge=0,
        function_state=RelicState.BROKEN,
        understood_pct=100,
        use=RelicUse.REPURPOSED,
        is_relic=True,
        updated_epoch=1,
        locked=[],
    )
    session.add(restored)
    await session.flush()
    assert not await restore_or_dismantle(ctx, restored, thing, holder, repairable=True)
    assert restored.function_state is RelicState.RESTORED
    restored.use = RelicUse.DISMANTLED
    assert await restore_or_dismantle(ctx, restored, thing, holder, repairable=True)
    assert restored.function_state is RelicState.BROKEN and not restored.is_relic
    assert OUTPUT_GOODS[ReplicatorOutput.ENERGY] is CommodityKind.FUEL
    assert ALLOCATION_MODE_TRAITS[AllocationMode.LOTTERY] == frozenset()
