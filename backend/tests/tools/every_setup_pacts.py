from sqlalchemy.ext.asyncio import AsyncSession

from aerona.db.tables.communication import SignalLinkRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.factions import FactionProfileRow
from aerona.db.tables.lore import MessageRow
from aerona.db.tables.polity import TreatyPartyRow, TreatyProfileRow
from aerona.db.tables.renown import DeedRow
from aerona.domain.enums.agent import MessageIntent
from aerona.domain.enums.bond import BondKind
from aerona.domain.enums.communication import DispatchContent, DispatchState, EnvoyFate, Medium, SignalKind, SignalState
from aerona.domain.enums.entity import EntityType
from aerona.domain.enums.faction import FactionKind
from aerona.domain.enums.polity import PartyRole, TreatyKind, TreatyStatus
from aerona.domain.enums.renown import ReputationAxis
from aerona.domain.models.entity_stats import FactionStats, TreatyStats
from tests.tools.every_setup import other_realm, ruled_realm, second_mortal
from tests.tools.every_tool import Ids
from tests.tools.factories import EPOCH, Realm, connect, make_entity


async def treaty_of(session: AsyncSession, realm: Realm, parties: list[int]) -> int:
    treaty = await make_entity(session, "Pact of the Ford", EntityType.TREATY, world_id=realm.cosmos.world_id, stats=TreatyStats())
    session.add(TreatyProfileRow(treaty_entity_id=treaty.id, kind=TreatyKind.PEACE, status=TreatyStatus.IN_FORCE, signed_epoch=EPOCH, locked=[]))
    for party in parties:
        session.add(TreatyPartyRow(treaty_entity_id=treaty.id, party_node_id=party, role=PartyRole.SIGNATORY))
    await session.flush()
    return treaty.id


async def treaty_between_others(session: AsyncSession, realm: Realm) -> Ids:
    found = await ruled_realm(session, realm)
    first = await other_realm(session, realm, "Reed Throne")
    second = await other_realm(session, realm, "Fen Throne")
    return {**found, "treaty": await treaty_of(session, realm, [first, second])}


async def treaty_of_mine(session: AsyncSession, realm: Realm) -> Ids:
    found = await ruled_realm(session, realm)
    other = await other_realm(session, realm, "Reed Throne")
    return {**found, "treaty": await treaty_of(session, realm, [found["polity"], other])}


async def council_seat(session: AsyncSession, realm: Realm) -> Ids:
    found = await ruled_realm(session, realm)
    council = await make_entity(session, "Concord of Worlds", EntityType.FACTION, world_id=realm.cosmos.world_id, stats=FactionStats())
    session.add(FactionProfileRow(faction_entity_id=council.id, kind=FactionKind.INTERWORLD_FEDERATION))
    await connect(session, found["polity"], council.id, BondKind.MEMBER_OF)
    await session.flush()
    return {**found, "council": council.id}


async def envoy_at_court(session: AsyncSession, realm: Realm) -> Ids:
    found = await ruled_realm(session, realm)
    other = await other_realm(session, realm, "Reed Throne")
    envoy = await second_mortal(session, realm)
    session.add(
        MessageRow(
            epoch=EPOCH,
            sender_node_id=other,
            recipient_node_id=realm.settlement_id,
            intent=MessageIntent.DISPATCH,
            text="a proposal",
            medium=Medium.ENVOY,
            content=DispatchContent.PROPOSAL,
            state=DispatchState.DELIVERED,
            envoy_node_id=envoy["mortal"],
            envoy_fate=EnvoyFate.RECEIVED,
            payload={},
            arrival_epoch=EPOCH,
            locked=[],
        )
    )
    await session.flush()
    return {**found, "envoy": envoy["mortal"]}


async def station_here(session: AsyncSession, realm: Realm) -> Ids:
    town = await session.get(EntityRow, realm.settlement_id)
    assert town is not None and town.location_id is not None
    me = await session.get(EntityRow, realm.mortal_id)
    assert me is not None
    me.location_id = realm.settlement_id
    other = await other_realm(session, realm, "Reed Throne")
    link = SignalLinkRow(
        owner_node_id=other, kind=SignalKind.BEACON_CHAIN, from_region_id=town.location_id, to_region_id=town.location_id, state=SignalState.ACTIVE, locked=[]
    )
    session.add(link)
    await session.flush()
    return {"link": link.id}


async def deed_of_another(session: AsyncSession, realm: Realm) -> Ids:
    doer = await second_mortal(session, realm)
    deed = DeedRow(doer_node_id=doer["mortal"], axis=ReputationAxis.HEROISM, magnitude=40, epoch=EPOCH, witnesses=0, token=False, locked=[])
    session.add(deed)
    await session.flush()
    return {"deed": deed.id}
