from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.db.tables.economy import CurrencyRow
from aerona.db.tables.entities import EntityRow, LanguageProfileRow
from aerona.db.tables.made import PeopleSubstrateRow, ReplicatorLineRow, ReplicatorPresenceRow
from aerona.db.tables.military import ArmyUnitRow
from aerona.db.tables.minds import MindProfileRow, MindStateRow
from aerona.db.tables.networks import NetworkNodeRow
from aerona.domain.enums.bond import BondKind
from aerona.domain.enums.constructs import MindWill
from aerona.domain.enums.entity import EntityStatus, EntityType
from aerona.domain.enums.made import RealmAwareness, RealmEntry, RealmPurpose, ReplicatorOutput, ReplicatorScale
from aerona.domain.enums.material import MaterialKind
from aerona.domain.enums.military import UnitKind
from aerona.domain.enums.mind import MemoryKind
from aerona.domain.enums.minds import MindAffect, MindMaking, MindOrigin, MindSeat, MindUpkeep
from aerona.domain.enums.mortal import CrimeKind, PunishmentKind
from aerona.domain.enums.networks import NetworkCarrier, NetworkRole, OutageCause
from aerona.domain.enums.tongues import LanguageModality
from aerona.domain.models.entity_stats import ArmyStats, LanguageStats, PeopleStats, PlaceStats, StructureStats
from aerona.engine.body.variants import fearless_share
from aerona.engine.made import control
from aerona.engine.made.realms import keep_realms
from aerona.engine.made.replicators import run_replicators
from aerona.engine.mind.memories import default_decay
from aerona.engine.minds.crimes import copying_crime
from aerona.engine.minds.making import missing_craft
from aerona.engine.minds.phase import tend_seat
from aerona.engine.minds.profiles import profile_of, seed_missing
from aerona.engine.minds.sentences import suffer_in_mind
from aerona.engine.networks.book import command_factor
from aerona.engine.networks.phase import keep_ledger
from aerona.engine.primitives.language_profile import DEFAULT_PHONOLOGY
from aerona.engine.primitives.queries import connect
from aerona.engine.sites.digs import sleepers_at, wake_sleepers
from aerona.engine.tongues.modality import settle_modalities
from aerona.services.integrity.minds_links import mend_minds_links
from tests.engine.core.factories import CoreWorld, entity, mortal, settlement
from tests.engine.core.test_minds_w44 import at, made_mind


async def test_an_army_of_constructs_and_a_mind_without_feeling_lose_no_morale(session: AsyncSession, world: CoreWorld) -> None:
    town = await settlement(session, "Ironvale", world, world.regions[0])
    host = await entity(session, "The Iron Host", EntityType.ARMY, ArmyStats(), world_id=world.world.id, location_id=town.id)
    session.add(ArmyUnitRow(army_entity_id=host.id, kind=UnitKind.CONSTRUCTS, count=300))
    session.add(ArmyUnitRow(army_entity_id=host.id, kind=UnitKind.LEVY, count=100))
    await session.flush()
    assert await fearless_share(session, host) == 0.75
    steward = await mortal(session, "Steward", world, town.id)
    ctx = await at(session, 2)
    mind = await made_mind(session, ctx, steward.id, steward.id)
    mind.affect = MindAffect.NONE
    await session.flush()
    assert await fearless_share(session, steward) == 1.0


async def test_a_running_control_network_lifts_an_army_and_a_downed_one_confuses_it(session: AsyncSession, world: CoreWorld) -> None:
    town = await settlement(session, "Signalford", world, world.regions[0])
    ruler = await mortal(session, "Orra", world, town.id)
    ctx = await at(session, 2)
    network = await control.found_network(ctx, ruler.id, "Signal line", NetworkCarrier.WIRED, town.id)
    network.carries_control = True
    await session.flush()
    assert await command_factor(session, ctx.rules, ruler.id, 2) > 1
    await control.cut_network(ctx, network.network_entity_id, OutageCause.STORM, 2, 50)
    assert await command_factor(session, ctx.rules, ruler.id, 2) < 1


async def test_a_mind_whose_seat_is_destroyed_ends_unless_a_saved_state_remains(session: AsyncSession, world: CoreWorld) -> None:
    town = await settlement(session, "Coreholm", world, world.regions[0])
    keeper = await mortal(session, "Ysel", world, town.id)
    ctx = await at(session, 2)
    rows = []
    for name in ("First Core", "Second Core"):
        core = await entity(session, name, EntityType.STRUCTURE, StructureStats(), world_id=world.world.id, location_id=town.id)
        servant = await mortal(session, f"Mind of {name}", world, town.id)
        mind = await made_mind(session, ctx, servant.id, keeper.id)
        mind.seat, mind.seat_node_id = MindSeat.STRUCTURE, core.id
        core.status, core.end_epoch = EntityStatus.DESTROYED, 1
        rows.append((servant, mind))
    session.add(MindStateRow(mind_node_id=rows[0][0].id, taken_epoch=1, fidelity_pct=90, holder_node_id=keeper.id, owner_node_id=keeper.id, locked=[]))
    await session.flush()
    for _, mind in rows:
        await tend_seat(ctx, mind)
    assert rows[0][1].dormant and rows[0][0].status is EntityStatus.CANON
    assert rows[1][0].status is not EntityStatus.CANON


async def test_making_asks_for_craft_recall_is_kept_and_copying_another_into_a_body_is_impersonation(session: AsyncSession, world: CoreWorld) -> None:
    town = await settlement(session, "Wrightmoor", world, world.regions[0])
    novice = await mortal(session, "Pell", world, town.id)
    steward = await mortal(session, "Steward", world, town.id)
    ctx = await at(session, 2)
    assert await missing_craft(session, ctx.rules, novice.id, MindMaking.CRAFT) is not None
    assert await missing_craft(session, ctx.rules, novice.id, MindMaking.DIVINE_GRANT) is not None
    mind = await made_mind(session, ctx, steward.id, steward.id)
    mind.perfect_recall = True
    await session.flush()
    assert await default_decay(session, ctx.rules, steward.id, MemoryKind.HARMED_ME) == 0
    assert await copying_crime(ctx, novice, mind, MindSeat.BODY) is CrimeKind.IMPERSONATION


async def test_only_minded_things_get_a_profile_and_empty_ones_are_mended_away(session: AsyncSession, world: CoreWorld) -> None:
    town = await settlement(session, "Hollowmere", world, world.regions[0])
    dweller = await mortal(session, "Brin", world, town.id)
    ctx = await at(session, 2)
    await seed_missing(session, ctx.rules, 2)
    assert await session.get(MindProfileRow, town.id) is None
    assert await session.get(MindProfileRow, dweller.id) is not None
    empty = await profile_of(session, ctx.rules, town.id, 2)
    assert empty.will is MindWill.NONE and not empty.souled
    await mend_minds_links(session)
    assert await session.scalar(select(MindProfileRow.node_id).where(MindProfileRow.node_id == town.id)) is None


async def test_the_law_can_sleep_a_made_mind_but_jails_a_born_one(session: AsyncSession, world: CoreWorld) -> None:
    town = await settlement(session, "Courtfall", world, world.regions[0])
    made = await mortal(session, "Unit Seven", world, town.id)
    born = await mortal(session, "Tamsin", world, town.id)
    ctx = await at(session, 2)
    mind = await made_mind(session, ctx, made.id, born.id)
    assert mind.origin is MindOrigin.MADE
    assert await suffer_in_mind(ctx, made, PunishmentKind.FORCED_DORMANCY, None) is PunishmentKind.FORCED_DORMANCY
    assert mind.dormant
    await profile_of(session, ctx.rules, born.id, 2)
    assert await suffer_in_mind(ctx, born, PunishmentKind.FORCED_DORMANCY, None) is PunishmentKind.IMPRISONMENT
    assert (await session.get(EntityRow, made.id)) is not None


async def test_a_realm_ends_with_its_destroyed_host_and_takes_its_unsaved_minds(session: AsyncSession, world: CoreWorld) -> None:
    town = await settlement(session, "Lanternby", world, world.regions[0])
    keeper = await mortal(session, "Ivo", world, town.id)
    dweller = await mortal(session, "Sel", world, town.id)
    ctx = await at(session, 2)
    works = await entity(session, "The Deep Works", EntityType.STRUCTURE, StructureStats(), world_id=world.world.id, location_id=town.id)
    draft = control.RealmDraft("The Quiet Hall", keeper.id, works.id, RealmPurpose.DWELLING, 100, RealmEntry.TRANSFER, RealmAwareness.KNOWS, MindUpkeep.NONE)
    realm = await control.make_realm(ctx, draft)
    mind = await profile_of(session, ctx.rules, dweller.id, 2)
    mind.seat, mind.seat_node_id = MindSeat.REALM, realm.dimension_id
    works.status, works.end_epoch = EntityStatus.DESTROYED, 2
    await session.flush()
    await keep_realms(await at(session, 3))
    assert realm.sealed and mind.seat is MindSeat.NONE and dweller.status is not EntityStatus.CANON


async def test_a_line_drifts_into_a_line_of_its_own_and_a_great_swarm_wakes(session: AsyncSession, world: CoreWorld) -> None:
    town = await settlement(session, "Greymarch", world, world.regions[0])
    owner = await mortal(session, "Hale", world, town.id)
    ctx = await at(session, 2)
    draft = control.LineDraft(
        "the grey line", ReplicatorScale.MACHINE, MaterialKind.IRON, ReplicatorOutput.GOODS, 0, 100, 90, False, owner.id, owner.id, world.regions[0].id, 50
    )
    line = await control.found_line(ctx, draft)
    session.add(ReplicatorPresenceRow(line_id=line.id, place_node_id=world.regions[1].id, mass=50, growth=100, locked=[]))
    await session.flush()
    await run_replicators(await at(session, 3, replicators={"drift_line_chance": 100, "wake_mass": 10, "wake_chance": 100}))
    drifted = await session.scalar(select(ReplicatorLineRow).where(ReplicatorLineRow.drifted_from_id == line.id))
    assert drifted is not None
    assert line.mind_node_id is not None
    swarm = await session.get(MindProfileRow, line.mind_node_id)
    assert swarm is not None and swarm.seat is MindSeat.BODIES and swarm.will is MindWill.EMERGENT


async def test_a_money_network_keeps_a_ledger_that_loses_trust_when_it_goes_down(session: AsyncSession, world: CoreWorld) -> None:
    first = await settlement(session, "Coinford", world, world.regions[0])
    second = await settlement(session, "Tallymere", world, world.regions[1])
    keeper = await mortal(session, "Wenna", world, first.id)
    ctx = await at(session, 2)
    network = await control.found_network(ctx, keeper.id, "Tally line", NetworkCarrier.WIRED, first.id)
    network.carries_money = True
    for town in (first, second):
        await control.join_network(ctx, network.network_entity_id, town.id, NetworkRole.HUB)
    entity_row = await session.get(EntityRow, network.network_entity_id)
    assert entity_row is not None
    rows = list(await session.scalars(select(NetworkNodeRow).where(NetworkNodeRow.network_entity_id == network.network_entity_id)))
    await keep_ledger(ctx, entity_row, network, rows)
    ledger = await session.scalar(select(CurrencyRow).where(CurrencyRow.issuer_entity_id == network.network_entity_id))
    assert ledger is not None and ledger.metal is None
    before = ledger.trust
    await control.cut_network(ctx, network.network_entity_id, OutageCause.STORM, 1, 50)
    assert ledger.trust < before


async def test_a_dig_wakes_the_minds_asleep_in_its_ruin(session: AsyncSession, world: CoreWorld) -> None:
    town = await settlement(session, "Ashgate", world, world.regions[0])
    leader = await mortal(session, "Corin", world, town.id)
    ruin = await entity(session, "The Sunken Vault", EntityType.PLACE, PlaceStats(), world_id=world.world.id, location_id=world.regions[0].id)
    sleeper = await mortal(session, "Warden", world, ruin.id)
    ctx = await at(session, 2)
    mind = await made_mind(session, ctx, sleeper.id, leader.id)
    mind.dormant = True
    await session.flush()
    assert await sleepers_at(ctx, ruin.id)
    assert await wake_sleepers(ctx, ruin, leader) == 1
    assert not mind.dormant


async def test_a_tongue_spoken_only_by_a_people_of_made_minds_becomes_data(session: AsyncSession, world: CoreWorld) -> None:
    folk = await entity(session, "The Lattice Folk", EntityType.PEOPLE, PeopleStats(population=40), world_id=world.world.id)
    tongue = await entity(session, "Lattice speech", EntityType.LANGUAGE, LanguageStats(), world_id=world.world.id)
    session.add(LanguageProfileRow(entity_id=tongue.id, phonology=DEFAULT_PHONOLOGY, seed="Lattice"))
    session.add(PeopleSubstrateRow(people_entity_id=folk.id, seat=MindSeat.NETWORK, origin=MindOrigin.MADE, share_pct=100, locked=[]))
    await session.flush()
    await connect(session, folk.id, tongue.id, BondKind.SPEAKS, 1)
    ctx = await at(session, 2)
    await settle_modalities(ctx)
    profile = await session.get(LanguageProfileRow, tongue.id)
    assert profile is not None and profile.modality is LanguageModality.DATA
