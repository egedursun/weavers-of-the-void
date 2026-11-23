from sqlalchemy.ext.asyncio import AsyncSession

from aerona.db.tables.arts import ArtPriceRow, ClubRow, ForgeryRow, MatchRow
from aerona.db.tables.constructs import ConstructRow, InstructionOrderRow, InstructionSetRow
from aerona.db.tables.contracts import MonsterContractRow
from aerona.db.tables.culture import ArtworkProfileRow, HolderTechniqueRow
from aerona.db.tables.ecology import BeastProfileRow
from aerona.db.tables.factions import FactionProfileRow
from aerona.db.tables.mortal import MortalProfileRow
from aerona.domain.enums.arts import ClubKind, ForgeryKind
from aerona.domain.enums.bond import BondKind
from aerona.domain.enums.constructs import CommandToken, ContractStatus, OrderKind
from aerona.domain.enums.culture import ArtMode, Technique
from aerona.domain.enums.ecology import BeastTemper
from aerona.domain.enums.entity import EntityType
from aerona.domain.enums.faction import FactionKind
from aerona.domain.models.entity_stats import ArtworkStats, BeastStats, FactionStats
from aerona.engine.primitives.queries import connect
from tests.tools.every_setup import second_mortal
from tests.tools.factories import Realm, make_entity

Ids = dict[str, int]
EPOCH = 1


async def art_work(session: AsyncSession, realm: Realm) -> Ids:
    work = await make_entity(
        session, "The Long Stair", EntityType.ARTWORK, world_id=realm.cosmos.world_id, location_id=realm.settlement_id, stats=ArtworkStats()
    )
    session.add(ArtworkProfileRow(artwork_entity_id=work.id, medium=ArtMode.FLAT_IMAGE, author_entity_id=realm.mortal_id, quality=60, locked=[]))
    await session.flush()
    return {"artwork": work.id}


async def renowned_critic(session: AsyncSession, realm: Realm) -> Ids:
    found = await art_work(session, realm)
    profile = await session.get(MortalProfileRow, realm.mortal_id)
    if profile is None:
        session.add(MortalProfileRow(entity_id=realm.mortal_id, renown=80, locked=[]))
    else:
        profile.renown = 80
    session.add(ArtPriceRow(artwork_entity_id=found["artwork"], price=50, locked=[]))
    await session.flush()
    return found


async def known_technique(session: AsyncSession, realm: Realm) -> Ids:
    session.add(HolderTechniqueRow(holder_entity_id=realm.mortal_id, technique=next(iter(Technique)), since_epoch=EPOCH))
    await session.flush()
    return {}


async def sold_work(session: AsyncSession, realm: Realm) -> Ids:
    other = await second_mortal(session, realm)
    work = await make_entity(
        session, "The Short Stair", EntityType.ARTWORK, world_id=realm.cosmos.world_id, location_id=realm.settlement_id, stats=ArtworkStats()
    )
    session.add(ArtworkProfileRow(artwork_entity_id=work.id, medium=ArtMode.FLAT_IMAGE, author_entity_id=other["mortal"], quality=40, locked=[]))
    session.add(ArtPriceRow(artwork_entity_id=work.id, price=0, locked=["price"]))
    await connect(session, other["mortal"], work.id, BondKind.OWNS, EPOCH)
    await session.flush()
    return {"artwork": work.id, "seller": other["mortal"]}


async def forged_work(session: AsyncSession, realm: Realm) -> Ids:
    found = await art_work(session, realm)
    copy = await make_entity(
        session, "The Echo Stair", EntityType.ARTWORK, world_id=realm.cosmos.world_id, location_id=realm.settlement_id, stats=ArtworkStats()
    )
    row = ForgeryRow(
        item_entity_id=copy.id, kind=ForgeryKind.ARTWORK, forger_entity_id=realm.mortal_id, original_entity_id=found["artwork"], skill=40, locked=[]
    )
    session.add(row)
    await session.flush()
    return {**found, "forgery": row.id, "copy": copy.id}


async def club_of(session: AsyncSession, realm: Realm, name: str) -> int:
    faction = await make_entity(session, name, EntityType.FACTION, world_id=realm.cosmos.world_id, location_id=realm.settlement_id, stats=FactionStats())
    session.add(
        FactionProfileRow(
            faction_entity_id=faction.id, kind=FactionKind.CLUB, home_entity_id=realm.settlement_id, influence_over={}, cohort_share={}, locked=[]
        )
    )
    session.add(ClubRow(faction_entity_id=faction.id, kind=ClubKind.TEAM_GAME, fandom=60, locked=[]))
    await session.flush()
    return faction.id


async def two_clubs(session: AsyncSession, realm: Realm) -> Ids:
    return {"home": await club_of(session, realm, "Wellbrook Reds"), "away": await club_of(session, realm, "Wellbrook Greys")}


async def played_match(session: AsyncSession, realm: Realm) -> Ids:
    clubs = await two_clubs(session, realm)
    match = MatchRow(home_entity_id=clubs["home"], away_entity_id=clubs["away"], winner_entity_id=clubs["away"], epoch=EPOCH, locked=[])
    session.add(match)
    await session.flush()
    return {**clubs, "match": match.id}


async def wild_beast(session: AsyncSession, realm: Realm) -> Ids:
    beast = await make_entity(
        session, "The Grey Hunger", EntityType.BEAST, world_id=realm.cosmos.world_id, location_id=realm.cosmos.region_id, stats=BeastStats(hp=60, danger=40)
    )
    session.add(BeastProfileRow(beast_entity_id=beast.id, temper=BeastTemper.HUNGRY, raids=2, lair_place_id=realm.cosmos.place_id, hoard={}, locked=[]))
    await session.flush()
    return {"beast": beast.id}


async def posted_contract(session: AsyncSession, realm: Realm) -> Ids:
    found = await wild_beast(session, realm)
    row = MonsterContractRow(community_entity_id=realm.settlement_id, beast_entity_id=found["beast"], bounty=30, status=ContractStatus.POSTED, locked=[])
    session.add(row)
    await session.flush()
    return {**found, "contract": row.id}


async def built_construct(session: AsyncSession, realm: Realm) -> Ids:
    body = await make_entity(
        session, "Clay construct of the vale", EntityType.BEAST, world_id=realm.cosmos.world_id, location_id=realm.cosmos.region_id, stats=BeastStats(hp=60)
    )
    session.add(BeastProfileRow(beast_entity_id=body.id, temper=BeastTemper.BOUND, bound_to_node_id=realm.mortal_id, lifespan=1_000_000, hoard={}, locked=[]))
    session.add(ConstructRow(entity_id=body.id, maker_entity_id=realm.mortal_id, locked=[]))
    rules = InstructionSetRow(owner_entity_id=body.id, command_token=CommandToken.WORD, holder_node_id=realm.mortal_id, locked=[])
    session.add(rules)
    await session.flush()
    order = InstructionOrderRow(set_id=rules.id, kind=OrderKind.GUARD, target_node_id=realm.settlement_id, locked=[])
    session.add(order)
    await session.flush()
    return {"construct": body.id, "set": rules.id, "order": order.id}
