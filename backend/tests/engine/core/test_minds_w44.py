from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.db.repositories.cosmos import CosmosRepository
from aerona.db.tables.bonds import BondRow
from aerona.db.tables.communication import SignalLinkRow
from aerona.db.tables.estates import CompanyShareRow
from aerona.db.tables.made import AugmentRow, PeopleSubstrateRow, ReplicatorLineRow, ReplicatorPresenceRow
from aerona.db.tables.mind import MemoryRow, SkillRow
from aerona.db.tables.minds import MindProfileRow
from aerona.db.tables.mortal import MortalProfileRow
from aerona.db.tables.networks import NetworkGatewayRow, NetworkProfileRow
from aerona.domain.enums.bond import BondKind
from aerona.domain.enums.communication import SignalKind, SignalState
from aerona.domain.enums.constructs import MindWill
from aerona.domain.enums.entity import EntityType
from aerona.domain.enums.made import (
    AugmentKind,
    AugmentMake,
    AugmentSlot,
    EffectTarget,
    RealmAwareness,
    RealmEntry,
    RealmPurpose,
    ReplicatorOutput,
    ReplicatorScale,
    ReplicatorStage,
)
from aerona.domain.enums.material import MaterialKind
from aerona.domain.enums.mind import MemoryKind, SkillKind, SkillSource
from aerona.domain.enums.minds import MindOrigin, MindSeat, MindUpkeep, StateMedium
from aerona.domain.enums.networks import NetworkCarrier, OutageCause
from aerona.domain.models.entity_stats import FactionStats, PeopleStats
from aerona.engine.augments import install, keep_augments
from aerona.engine.context import TickContext
from aerona.engine.made import control
from aerona.engine.made.realms import keep_realms
from aerona.engine.made.replicators import run_replicators
from aerona.engine.mind.book import effective_skill
from aerona.engine.minds.continuity import copy_mind, restore_mind, save_mind
from aerona.engine.minds.profiles import profile_of
from aerona.engine.networks.backfill import relay_backfill
from aerona.engine.primitives.manual import manual_context
from aerona.services.integrity.minds_links import mend_minds_links
from tests.engine.core.factories import CoreWorld, entity, mortal, settlement, tuned_rules


async def at(session: AsyncSession, epoch: int, **rules: dict[str, int]) -> TickContext:
    cosmos = await CosmosRepository(session).require_cosmos()
    cosmos.epoch = epoch
    await session.flush()
    return await manual_context(session, "minds", rules=tuned_rules(**rules))


async def made_mind(session: AsyncSession, ctx: TickContext, node_id: int, maker_id: int) -> MindProfileRow:
    mind = await profile_of(session, ctx.rules, node_id, ctx.epoch)
    mind.seat, mind.seat_node_id, mind.origin, mind.made_by_node_id = MindSeat.BODY, node_id, MindOrigin.MADE, maker_id
    mind.copyable = mind.restorable = mind.transferable = mind.mergeable = True
    mind.fidelity_pct, mind.will = 90, MindWill.INSTRUCTED
    await session.flush()
    return mind


async def test_a_copy_is_less_faithful_than_its_source_and_a_restored_mind_remembers_the_gap(session: AsyncSession, world: CoreWorld) -> None:
    town = await settlement(session, "Lockfall", world, world.regions[0])
    maker = await mortal(session, "Avera", world, town.id)
    steward = await mortal(session, "Steward", world, town.id)
    ctx = await at(session, 2)
    source = await made_mind(session, ctx, steward.id, maker.id)
    copy = await copy_mind(ctx, steward.id, MindSeat.BODY, None)
    copied = await session.get(MindProfileRow, copy.id)
    assert copied is not None and copied.origin is MindOrigin.COPIED and copied.fidelity_pct < source.fidelity_pct
    bond = await session.scalar(select(BondRow).where(BondRow.source_node_id == copy.id, BondRow.kind == BondKind.COPY_OF))
    assert bond is not None and bond.target_node_id == steward.id
    state = await save_mind(ctx, steward.id, maker.id, maker.id, StateMedium.RECORD)
    source.dormant = True
    await session.flush()
    later = await at(session, 6)
    await restore_mind(later, state.id, MindSeat.BODY, None)
    gap = await session.scalar(select(MemoryRow).where(MemoryRow.holder_node_id == steward.id, MemoryRow.kind == MemoryKind.MEMORY_GAP))
    assert gap is not None and not source.dormant


async def test_an_augment_lifts_a_skill_and_too_many_strain_their_bearer(session: AsyncSession, world: CoreWorld) -> None:
    town = await settlement(session, "Brasshollow", world, world.regions[0])
    bearer = await mortal(session, "Tolen", world, town.id)
    session.add(
        SkillRow(
            holder_node_id=bearer.id, skill=SkillKind.ENGINEERING, subject_node_id=None, level=20, peak=20, xp=0, last_used_epoch=1, source=SkillSource.PRACTICE
        )
    )
    await session.flush()
    ctx = await at(session, 2)
    before = await effective_skill(session, bearer.id, SkillKind.ENGINEERING)
    effect = [(EffectTarget.SKILL, SkillKind.ENGINEERING.value, 20)]
    await install(
        ctx, bearer.id, slot=AugmentSlot.MIND, part=None, kind=AugmentKind.ENHANCEMENT, make=AugmentMake.MADE, quality=10, surgeon_id=None, effects=effect
    )
    assert await effective_skill(session, bearer.id, SkillKind.ENGINEERING) > before
    for _ in range(4):
        await install(
            ctx, bearer.id, slot=AugmentSlot.SKIN, part=None, kind=AugmentKind.COSMETIC, make=AugmentMake.MADE, quality=10, surgeon_id=None, effects=[]
        )
    await keep_augments(await at(session, 3, augments={"rejection_chance": 0}))
    strained = list(await session.scalars(select(AugmentRow).where(AugmentRow.bearer_node_id == bearer.id)))
    profile = await session.get(MortalProfileRow, bearer.id)
    assert any(row.strain >= 40 for row in strained) and profile is not None and profile.stress > 0


async def test_a_realm_stands_still_while_its_host_network_is_down_and_a_labour_realm_pays_its_keeper(session: AsyncSession, world: CoreWorld) -> None:
    town = await settlement(session, "Quietwater", world, world.regions[0])
    keeper = await mortal(session, "Mirel", world, town.id)
    worker = await mortal(session, "Ostin", world, town.id)
    ctx = await at(session, 2)
    network = await control.found_network(ctx, keeper.id, "Quietwater relay", NetworkCarrier.WIRED, town.id)
    draft = control.RealmDraft(
        "The Long Hall", keeper.id, network.network_entity_id, RealmPurpose.LABOUR, 300, RealmEntry.INTERFACE, RealmAwareness.KNOWS, MindUpkeep.NONE
    )
    realm = await control.make_realm(ctx, draft)
    mind = await profile_of(session, ctx.rules, worker.id, ctx.epoch)
    mind.seat, mind.seat_node_id = MindSeat.REALM, realm.dimension_id
    await session.flush()
    await keep_realms(await at(session, 3))
    assert mind.speed_pct == 300 and not mind.dormant
    await control.cut_network(await at(session, 4), network.network_entity_id, OutageCause.STORM, 2, 50)
    await keep_realms(await at(session, 4))
    assert mind.dormant and realm.frozen_until_epoch > 4


async def test_a_runaway_line_with_a_kill_switch_is_stopped(session: AsyncSession, world: CoreWorld) -> None:
    town = await settlement(session, "Greyfold", world, world.regions[0])
    owner = await mortal(session, "Hask", world, town.id)
    ctx = await at(session, 2)
    draft = control.LineDraft(
        "the grey line", ReplicatorScale.MACHINE, MaterialKind.IRON, ReplicatorOutput.DISASSEMBLY, 20, 0, 5, True, owner.id, owner.id, world.regions[0].id, 10
    )
    line = await control.found_line(ctx, draft)
    await run_replicators(await at(session, 3))
    refreshed = await session.get(ReplicatorLineRow, line.id)
    assert refreshed is not None and refreshed.stage is ReplicatorStage.STOPPED


async def test_signal_chains_become_relay_networks_once(session: AsyncSession, world: CoreWorld) -> None:
    town = await settlement(session, "Beaconreach", world, world.regions[0])
    keeper = await mortal(session, "Ilse", world, town.id)
    session.add(
        SignalLinkRow(
            owner_node_id=keeper.id, kind=next(iter(SignalKind)), from_region_id=world.regions[0].id, to_region_id=world.regions[1].id, state=SignalState.ACTIVE
        )
    )
    await session.flush()
    assert await relay_backfill(await at(session, 2)) == 1
    assert await relay_backfill(await at(session, 3)) == 0
    network = await session.scalar(select(NetworkProfileRow).where(NetworkProfileRow.owner_node_id == keeper.id))
    assert network is not None and network.carrier is NetworkCarrier.RELAY


async def test_integrity_balances_substrates_trims_shares_and_closes_a_gateway_to_itself(session: AsyncSession, world: CoreWorld) -> None:
    town = await settlement(session, "Fairhold", world, world.regions[0])
    keeper = await mortal(session, "Dov", world, town.id)
    folk = await entity(session, "Folk of Fairhold", EntityType.PEOPLE, PeopleStats(population=500), world_id=world.world.id)
    session.add(PeopleSubstrateRow(people_entity_id=folk.id, seat=MindSeat.BODY, origin=MindOrigin.BORN, share_pct=60, locked=[]))
    session.add(PeopleSubstrateRow(people_entity_id=folk.id, seat=MindSeat.NETWORK, origin=MindOrigin.MADE, share_pct=60, locked=[]))
    company = await entity(session, "Fair Company", EntityType.FACTION, FactionStats(), world_id=world.world.id, location_id=town.id)
    session.add(CompanyShareRow(company_entity_id=company.id, holder_node_id=keeper.id, share=90, locked=False))
    session.add(CompanyShareRow(company_entity_id=company.id, holder_node_id=folk.id, share=60, locked=False))
    ctx = await at(session, 2)
    network = await control.found_network(ctx, keeper.id, "Fair relay", NetworkCarrier.RELAY, town.id)
    looped = NetworkGatewayRow(
        first_network_id=network.network_entity_id, second_network_id=network.network_entity_id, toll=0, filter_pct=0, owner_node_id=None
    )
    looped.locked = []
    session.add(looped)
    await session.flush()
    assert await mend_minds_links(session) >= 3
    shares = list(await session.scalars(select(PeopleSubstrateRow.share_pct).where(PeopleSubstrateRow.people_entity_id == folk.id)))
    held = list(await session.scalars(select(CompanyShareRow.share).where(CompanyShareRow.company_entity_id == company.id)))
    assert sum(shares) == 100 and sum(held) == 100
    assert await session.scalar(select(NetworkGatewayRow.id).where(NetworkGatewayRow.first_network_id == NetworkGatewayRow.second_network_id)) is None
    presences = list(await session.scalars(select(ReplicatorPresenceRow)))
    assert all(row.mass >= 0 for row in presences)
