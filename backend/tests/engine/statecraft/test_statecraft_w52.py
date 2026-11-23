from sqlalchemy import select

from aerona.catalog.statecraft import COUNCIL_TASKS, DEMANDS, MANDATE_TEXT, POSITION_TEXT
from aerona.db.tables.affairs import CourtPositionRow, MandateRow
from aerona.db.tables.belonging import SatireRow
from aerona.db.tables.bonds import BondRow
from aerona.db.tables.cosmos import AppliedFixupRow
from aerona.db.tables.mortal import MortalProfileRow
from aerona.db.tables.statecraft import CrisisRow
from aerona.domain.enums.belonging import SatireSource
from aerona.domain.enums.bond import BondKind
from aerona.domain.enums.statecraft import CouncilTask, CourtPosition, CrisisDemand, MandateKind, MandateState
from aerona.engine.polity.book import RealmBook
from aerona.engine.polity.council import EFFECTS, Work
from aerona.engine.polity.court import Seat, jester, seat_jesters, seer
from aerona.engine.polity.crisis_outcomes import concede
from aerona.engine.polity.mandates import ration_share, rationed
from tests.engine.society.factories import Realm, context, mortal, tuned
from tests.engine.statecraft.test_affairs import realm_of


def test_every_new_statecraft_value_has_its_catalogue_entry() -> None:
    assert COUNCIL_TASKS[CouncilTask.OVERSEE_WORKS].gain and not COUNCIL_TASKS[CouncilTask.TRAIN_TROOPS].gain
    assert MANDATE_TEXT[MandateKind.RATION] and MANDATE_TEXT[MandateKind.CORVEE]
    assert DEMANDS[CrisisDemand.HAND_OVER].person and not DEMANDS[CrisisDemand.OPEN_TRADE].person
    assert POSITION_TEXT[CourtPosition.JESTER] and POSITION_TEXT[CourtPosition.SEER]


async def test_a_ration_mandate_cuts_hunger_deaths_in_its_town(realm: Realm) -> None:
    ctx = context(realm.session, tuned(mandates={"ration_death_cut_pct": 40}))
    polity, town, ruler = await realm_of(realm, "Corvane")
    assert await ration_share(ctx, town.id) == 1.0
    realm.session.add(
        MandateRow(
            polity_entity_id=polity.id, issuer_node_id=ruler.id, kind=MandateKind.RATION, settlement_entity_id=town.id, issued_epoch=3, until_epoch=5, locked=[]
        )
    )
    await realm.session.flush()
    assert await rationed(realm.session, town.id)
    assert await ration_share(ctx, town.id) == 0.6
    row = await realm.session.scalar(select(MandateRow).where(MandateRow.settlement_entity_id == town.id))
    assert row is not None and row.state is MandateState.ACTIVE


async def test_a_promoting_officer_earns_on_open_roads_and_open_trade_is_conceded(realm: Realm) -> None:
    ctx = context(realm.session, tuned(council={"promote_trade_effect": 10}))
    polity, _, _ = await realm_of(realm, "Corvane")
    rival, _, _ = await realm_of(realm, "Dunmark")
    book = await RealmBook.load(realm.session)
    mine, theirs = book.realms[polity.id], book.realms[rival.id]
    before = mine.profile.treasury
    office = mine.offices[0]
    await EFFECTS[CouncilTask.PROMOTE_TRADE](ctx, book, Work(mine, office, 1.0))
    assert mine.profile.treasury == before
    crisis = CrisisRow(demander_entity_id=polity.id, target_entity_id=rival.id, demand=CrisisDemand.OPEN_TRADE, opened_epoch=3, locked=[])
    realm.session.add(crisis)
    await realm.session.flush()
    assert await concede(ctx, book, crisis, mine, theirs)
    bond = await realm.session.scalar(select(BondRow).where(BondRow.kind == BondKind.TRADES_WITH))
    assert bond is not None


async def test_a_jester_mocks_and_a_seer_sways_and_old_jesters_take_their_place(realm: Realm) -> None:
    ctx = context(realm.session, tuned(court={"seer_sway_pct": 100}))
    polity, town, ruler = await realm_of(realm, "Corvane")
    fool = await mortal(realm, "Pell", location_id=town.id)
    sage = await mortal(realm, "Iro", location_id=town.id)
    realm.session.add(MortalProfileRow(entity_id=sage.id, renown=80, locked=[]))
    await realm.session.flush()
    book = await RealmBook.load(realm.session)
    seat = book.realms[polity.id]
    await jester(ctx, Seat(seat, ruler, fool))
    jest = await realm.session.scalar(select(SatireRow).where(SatireRow.satirist_entity_id == fool.id))
    assert jest is not None and jest.source is SatireSource.JESTER
    before = seat.profile.legitimacy
    await seer(ctx, Seat(seat, ruler, sage))
    assert seat.profile.legitimacy > before
    assert await seat_jesters(realm.session, 3) == 1
    placed = await realm.session.get(CourtPositionRow, (polity.id, CourtPosition.JESTER))
    assert placed is not None and placed.holder_entity_id == fool.id
    assert await realm.session.get(AppliedFixupRow, "court.w52") is not None
