from sqlalchemy.ext.asyncio import AsyncSession

from aerona.db.tables.economy import LoanRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.finance import SpeculationRow
from aerona.db.tables.polity import PolityMemberRow, PolityProfileRow
from aerona.domain.enums.bond import BondKind
from aerona.domain.enums.chronicle import WritingSystem
from aerona.domain.enums.economy import CommodityKind, LoanStatus
from aerona.domain.enums.entity import EntityType
from aerona.domain.enums.finance import SpeculationStatus
from aerona.domain.enums.polity import DecisionRule, GovernmentKind
from aerona.domain.models.entity_stats import LanguageStats, PolityStats, SettlementStats
from aerona.engine.economy.purse import give_coin
from aerona.engine.primitives.language_profile import language_profile
from aerona.rules.registry import Rules
from tests.tools.every_setup import ruler
from tests.tools.factories import Realm, connect, make_entity

Ids = dict[str, int]


async def script_ruler(session: AsyncSession, realm: Realm) -> Ids:
    found = await ruler(session, realm)
    language = await session.get(EntityRow, realm.language_id)
    assert language is not None
    (await language_profile(session, language)).writing_system = WritingSystem.ALPHABET
    await connect(session, realm.settlement_id, realm.language_id, BondKind.SPEAKS)
    town = await make_entity(session, "Lowmere", EntityType.SETTLEMENT, world_id=realm.cosmos.world_id, stats=SettlementStats(population=400))
    tongue = await make_entity(session, "Lowtongue", EntityType.LANGUAGE, world_id=realm.cosmos.world_id, stats=LanguageStats())
    await language_profile(session, tongue)
    await connect(session, town.id, found["polity"], BondKind.MEMBER_OF)
    session.add(PolityMemberRow(polity_entity_id=found["polity"], member_entity_id=town.id))
    await connect(session, town.id, tongue.id, BondKind.SPEAKS)
    await session.flush()
    return {**found, "subject_tongue": tongue.id}


async def indebted_realm(session: AsyncSession, realm: Realm) -> Ids:
    found = await ruler(session, realm)
    session.add(
        LoanRow(
            lender_entity_id=realm.faction_id,
            borrower_entity_id=found["polity"],
            principal=40,
            interest_pct=10,
            issued_epoch=1,
            due_epoch=4,
            status=LoanStatus.OPEN,
            purpose="war",
        )
    )
    await session.flush()
    return found


async def foreign_debtor(session: AsyncSession, realm: Realm) -> Ids:
    found = await ruler(session, realm)
    debtor = await make_entity(session, "Low Crown", EntityType.POLITY, world_id=realm.cosmos.world_id, stats=PolityStats())
    session.add(PolityProfileRow(polity_entity_id=debtor.id, government=next(iter(GovernmentKind)), decision_rule=next(iter(DecisionRule))))
    session.add(
        LoanRow(
            lender_entity_id=realm.faction_id,
            borrower_entity_id=debtor.id,
            principal=40,
            interest_pct=10,
            issued_epoch=1,
            due_epoch=4,
            status=LoanStatus.OPEN,
            purpose="debt",
        )
    )
    await session.flush()
    return {**found, "debtor": debtor.id}


async def held_loan(session: AsyncSession, realm: Realm) -> Ids:
    loan = LoanRow(
        lender_entity_id=realm.mortal_id,
        borrower_entity_id=realm.settlement_id,
        principal=30,
        interest_pct=10,
        issued_epoch=1,
        due_epoch=4,
        status=LoanStatus.OPEN,
        purpose="trade",
    )
    session.add(loan)
    mortal = await session.get(EntityRow, realm.mortal_id)
    assert mortal is not None
    await give_coin(session, Rules(), mortal, 500)
    buyer = await session.get(EntityRow, realm.faction_id)
    assert buyer is not None
    await give_coin(session, Rules(), buyer, 500)
    await session.flush()
    return {"loan": loan.id, "buyer": realm.faction_id}


async def hoarded_market(session: AsyncSession, realm: Realm) -> Ids:
    found = await ruler(session, realm)
    session.add(PolityMemberRow(polity_entity_id=found["polity"], member_entity_id=realm.settlement_id))
    session.add(
        SpeculationRow(
            merchant_node_id=realm.faction_id,
            market_node_id=realm.settlement_id,
            commodity=CommodityKind.GRAIN,
            units=20,
            price=10,
            status=SpeculationStatus.HOARDING,
            opened_epoch=1,
            gain=0,
            locked=[],
        )
    )
    await session.flush()
    return found
