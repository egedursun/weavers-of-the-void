from sqlalchemy.ext.asyncio import AsyncSession

from aerona.db.tables.estates import CompanyProfileRow
from aerona.db.tables.made import (
    AugmentRow,
    DataStoreContentRow,
    DataStoreRow,
    MadeRealmRow,
    MadeRelicRow,
    PatternRightRow,
    ReplicatorLineRow,
    ReplicatorPresenceRow,
    SalvageSiteRow,
)
from aerona.db.tables.minds import MindProfileRow, MindStateRow
from aerona.db.tables.networks import NetworkNodeRow, NetworkProfileRow
from aerona.domain.enums.constructs import MindWill
from aerona.domain.enums.cosmography import DimensionKind
from aerona.domain.enums.entity import EntityType
from aerona.domain.enums.made import (
    AugmentKind,
    AugmentMake,
    AugmentSlot,
    CompanyCharter,
    DataContent,
    RealmAwareness,
    RealmEntry,
    RealmPurpose,
    RelicState,
    RelicUse,
    ReplicatorOutput,
    ReplicatorScale,
    ReplicatorStage,
)
from aerona.domain.enums.material import MaterialKind
from aerona.domain.enums.minds import MindOrigin, MindPurpose, MindSeat, MindUpkeep, StateMedium
from aerona.domain.enums.networks import NetworkCarrier, NetworkRole
from aerona.domain.enums.society import Commodity
from aerona.domain.models.entity_stats import FactionStats, NetworkStats
from aerona.engine.cosmos.ladder import DimensionDraft, create_dimension
from aerona.rules.registry import Rules
from tests.tools.every_setup import second_mortal, second_settlement
from tests.tools.every_setup_arts import built_construct
from tests.tools.factories import Realm, make_entity

Ids = dict[str, int]
EPOCH = 1


def made_profile(node_id: int, maker_id: int) -> MindProfileRow:
    return MindProfileRow(
        node_id=node_id,
        seat=MindSeat.BODY,
        seat_node_id=node_id,
        origin=MindOrigin.MADE,
        will=MindWill.INSTRUCTED,
        purpose=MindPurpose.SERVANT,
        capacity=40,
        speed_pct=100,
        stability=90,
        fidelity_pct=95,
        upkeep=MindUpkeep.MAINTENANCE,
        pausable=True,
        copyable=True,
        restorable=True,
        mergeable=True,
        transferable=True,
        dormant=False,
        perfect_recall=True,
        made_by_node_id=maker_id,
        maker_bond=20,
        drift_pct=0,
        souled=False,
        run_epochs=0,
        updated_epoch=EPOCH,
        locked=[],
    )


async def made_mind(session: AsyncSession, realm: Realm) -> Ids:
    found = await built_construct(session, realm)
    session.add(made_profile(found["construct"], realm.mortal_id))
    await session.flush()
    return {**found, "mind": found["construct"]}


async def two_made_minds(session: AsyncSession, realm: Realm) -> Ids:
    first = await made_mind(session, realm)
    other = await make_entity(session, "Second made body of the vale", EntityType.STRUCTURE, world_id=realm.cosmos.world_id, location_id=realm.settlement_id)
    session.add(made_profile(other.id, realm.mortal_id))
    await session.flush()
    return {**first, "second_mind": other.id}


async def saved_state(session: AsyncSession, realm: Realm) -> Ids:
    found = await made_mind(session, realm)
    state = MindStateRow(mind_node_id=found["mind"], taken_epoch=EPOCH, fidelity_pct=90, holder_node_id=realm.mortal_id, medium_kind=StateMedium.RECORD)
    state.sealed, state.copies, state.owner_node_id, state.locked = False, 1, realm.mortal_id, []
    session.add(state)
    await session.flush()
    return {**found, "state": state.id}


async def network(session: AsyncSession, realm: Realm) -> Ids:
    other = await second_mortal(session, realm)
    town = await second_settlement(session, realm)
    node = await make_entity(
        session, "Vale relay", EntityType.NETWORK, world_id=realm.cosmos.world_id, location_id=town["settlement"], stats=NetworkStats(reach=1)
    )
    session.add(NetworkProfileRow(network_entity_id=node.id, carrier=NetworkCarrier.RELAY, owner_node_id=other["mortal"], founded_epoch=EPOCH, locked=[]))
    session.add(
        NetworkNodeRow(
            network_entity_id=node.id, member_node_id=town["settlement"], role=NetworkRole.HUB, dependency_pct=20, security=10, joined_epoch=EPOCH, locked=[]
        )
    )
    await session.flush()
    return {"network": node.id, "member": town["settlement"], "owner": other["mortal"]}


async def store(session: AsyncSession, realm: Realm) -> Ids:
    row = DataStoreRow(holder_node_id=realm.mortal_id, security=10, owner_node_id=realm.mortal_id, locked=[])
    session.add(row)
    await session.flush()
    session.add(DataStoreContentRow(store_id=row.id, content=DataContent.SECRET, subject_node_id=realm.people_id, reference=None, epoch=EPOCH, locked=[]))
    await session.flush()
    return {"store": row.id}


async def borne_augment(session: AsyncSession, realm: Realm) -> Ids:
    row = AugmentRow(
        bearer_node_id=realm.mortal_id,
        slot=AugmentSlot.WHOLE_BODY,
        part=None,
        kind=AugmentKind.ENHANCEMENT,
        make=AugmentMake.MADE,
        quality=50,
        upkeep=MindUpkeep.MAINTENANCE,
        integration=60,
        strain=0,
        installed_by_node_id=None,
        installed_epoch=EPOCH,
        locked=[],
    )
    session.add(row)
    await session.flush()
    return {"augment": row.id}


async def replicator(session: AsyncSession, realm: Realm) -> Ids:
    row = ReplicatorLineRow(
        name="the vale line",
        scale=ReplicatorScale.MACHINE,
        feedstock=MaterialKind.IRON,
        output=ReplicatorOutput.GOODS,
        growth_pct=10,
        error_pct=5,
        set_id=None,
        containment=60,
        kill_switch=True,
        owner_node_id=realm.mortal_id,
        maker_node_id=realm.mortal_id,
        mind_node_id=None,
        stage=ReplicatorStage.WORKING,
        drifted_from_id=None,
        founded_epoch=EPOCH,
        locked=[],
    )
    session.add(row)
    await session.flush()
    session.add(ReplicatorPresenceRow(line_id=row.id, place_node_id=realm.cosmos.region_id, mass=10, growth=100, locked=[]))
    await session.flush()
    return {"line": row.id}


async def made_realm(session: AsyncSession, realm: Realm, *, sealed: bool = False) -> Ids:
    dimension = await create_dimension(session, Rules(), DimensionDraft(name="The vale realm", kind=DimensionKind.MADE, epoch=EPOCH))
    row = MadeRealmRow(
        dimension_id=dimension.id,
        host_node_id=realm.settlement_id,
        keeper_node_id=realm.mortal_id,
        realm_purpose=RealmPurpose.DWELLING,
        time_ratio_pct=100,
        fidelity=100,
        entry=RealmEntry.INTERFACE,
        aware_inside=RealmAwareness.KNOWS,
        upkeep=MindUpkeep.NONE,
        frozen_until_epoch=0,
        sealed=sealed,
        locked=[],
    )
    session.add(row)
    await session.flush()
    return {"realm": dimension.id}


async def sealed_realm(session: AsyncSession, realm: Realm) -> Ids:
    return await made_realm(session, realm, sealed=True)


async def relic(session: AsyncSession, realm: Realm) -> Ids:
    item = await make_entity(session, "Old engine of the vale", EntityType.ITEM, world_id=realm.cosmos.world_id, location_id=realm.settlement_id)
    session.add(
        MadeRelicRow(
            thing_node_id=item.id,
            make_knowledge=9,
            repair_knowledge=8,
            function_state=RelicState.FAILING,
            understood_pct=0,
            use=RelicUse.AS_MADE,
            is_relic=True,
            updated_epoch=EPOCH,
            locked=[],
        )
    )
    await session.flush()
    return {"relic": item.id}


async def salvage_site(session: AsyncSession, realm: Realm) -> Ids:
    site = await make_entity(session, "Fallen works of the vale", EntityType.STRUCTURE, world_id=realm.cosmos.world_id, location_id=realm.settlement_id)
    session.add(SalvageSiteRow(site_entity_id=site.id, yield_left=20, rights_holder_node_id=None, last_salvaged_epoch=None, locked=[]))
    await session.flush()
    return {"site": site.id}


async def company(session: AsyncSession, realm: Realm) -> Ids:
    faction = await make_entity(
        session, "Vale company", EntityType.FACTION, world_id=realm.cosmos.world_id, location_id=realm.settlement_id, stats=FactionStats()
    )
    session.add(CompanyProfileRow(faction_entity_id=faction.id, charter=CompanyCharter.FREE, headquarters_entity_id=realm.settlement_id, locked=[]))
    await session.flush()
    return {"company": faction.id}


async def pattern(session: AsyncSession, realm: Realm) -> Ids:
    other = await second_mortal(session, realm)
    row = PatternRightRow(commodity=Commodity.GOODS, holder_node_id=other["mortal"], licence_fee=0, open=False, since_epoch=EPOCH, locked=[])
    session.add(row)
    await session.flush()
    return {"pattern": row.id}
