from sqlalchemy.ext.asyncio import AsyncSession

from aerona.db.tables.entities import EntityRow
from aerona.db.tables.factions import FactionProfileRow
from aerona.db.tables.justice import CrimeCaseRow
from aerona.db.tables.polity import ClaimRow
from aerona.domain.enums.bond import BondKind
from aerona.domain.enums.entity import EntityType
from aerona.domain.enums.faction import FactionKind
from aerona.domain.enums.justice import CaseStage
from aerona.domain.enums.mortal import CrimeKind
from aerona.domain.enums.polity import ClaimBasis
from aerona.domain.models.entity_stats import FactionStats
from tests.tools.every_setup import other_realm, ruler, second_mortal
from tests.tools.factories import EPOCH, Realm, connect, make_entity

Ids = dict[str, int]


async def court_seat(session: AsyncSession, realm: Realm) -> Ids:
    return {**await ruler(session, realm), **await second_mortal(session, realm)}


async def held_claim(session: AsyncSession, realm: Realm) -> Ids:
    found = await ruler(session, realm)
    rival = await other_realm(session, realm, "Briar Throne")
    session.add(ClaimRow(claimant_entity_id=realm.mortal_id, polity_entity_id=rival, basis=ClaimBasis.ADOPTION, strength=40, since_epoch=EPOCH, locked=[]))
    await session.flush()
    return {**found, "rival": rival}


async def ruled_heir(session: AsyncSession, realm: Realm) -> Ids:
    found = await court_seat(session, realm)
    await connect(session, realm.mortal_id, realm.settlement_id, BondKind.RULES)
    return found


async def free_body(session: AsyncSession, realm: Realm) -> Ids:
    me = await session.get(EntityRow, realm.mortal_id)
    assert me is not None
    me.location_id = realm.settlement_id
    body = await make_entity(
        session, "Millers of the Ford", EntityType.FACTION, world_id=realm.cosmos.world_id, location_id=realm.settlement_id, stats=FactionStats()
    )
    return {"faction": body.id}


async def open_case(session: AsyncSession, realm: Realm) -> Ids:
    me = await session.get(EntityRow, realm.mortal_id)
    assert me is not None
    me.location_id = realm.settlement_id
    other = await second_mortal(session, realm)
    case = CrimeCaseRow(
        settlement_entity_id=realm.settlement_id, crime=CrimeKind.THEFT, accused_entity_id=other["mortal"], stage=CaseStage.INVESTIGATION, opened_epoch=EPOCH
    )
    session.add(case)
    await session.flush()
    return {"case": case.id}


async def led_faction(session: AsyncSession, realm: Realm) -> Ids:
    body = await make_entity(session, "Ford Party", EntityType.FACTION, world_id=realm.cosmos.world_id, location_id=realm.settlement_id, stats=FactionStats())
    session.add(
        FactionProfileRow(
            faction_entity_id=body.id,
            kind=FactionKind.PARTY,
            home_entity_id=realm.settlement_id,
            leader_entity_id=realm.mortal_id,
            influence_over={},
            locked=[],
        )
    )
    await session.flush()
    return {"faction": body.id}
