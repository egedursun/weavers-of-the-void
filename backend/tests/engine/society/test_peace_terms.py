from sqlalchemy import select

from aerona.db.tables.bonds import BondRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.lifecycle import DesignatedHeirRow
from aerona.db.tables.military import WarAimRow
from aerona.db.tables.polity import ClaimRow
from aerona.db.tables.settlement import SettlementProfileRow
from aerona.db.tables.warfare import CaptiveRow, WarRow
from aerona.domain.enums.bond import BondKind
from aerona.domain.enums.entity import EntityStatus, EntityType
from aerona.domain.enums.military import WarAimKind
from aerona.domain.enums.polity import ClaimBasis, GovernmentKind
from aerona.domain.enums.settlement import SizeTier
from aerona.domain.enums.war import CaptiveStatus
from aerona.domain.models.entity_stats import CultStats
from aerona.engine.context import TickContext
from aerona.engine.military.aims import TERMS
from aerona.engine.polity.book import Realm, RealmBook
from aerona.engine.polity.formation import found_polity, set_ruler, sync_members
from aerona.engine.primitives.queries import connect
from aerona.engine.services.war import open_war
from tests.engine.society.factories import Realm as World
from tests.engine.society.factories import context, make, mortal, people, settlement, son

A = WarAimKind


async def realm_of(world: World, name: str) -> tuple[TickContext, Realm, EntityRow, EntityRow]:
    ctx = context(world.session)
    capital = await settlement(world, name)
    world.session.add(SettlementProfileRow(settlement_entity_id=capital.id, size_tier=SizeTier.TOWN, treasury=100, unrest=10, locked=[], foreigners={}))
    ruler = await mortal(world, f"Ruler of {name}", location_id=capital.id)
    book = await RealmBook.load(world.session)
    state = await found_polity(ctx, book, capital)
    await sync_members(ctx, book, state, {capital.id})
    set_ruler(ctx, state, ruler.id, "crowned")
    await world.session.flush()
    return ctx, state, capital, ruler


def aim(war: WarRow, side: EntityRow, kind: WarAimKind, **params: int | str | bool) -> WarAimRow:
    return WarAimRow(war_id=war.id, side_entity_id=side.id, kind=kind, params=params, achieved=1000, locked=[])


async def test_a_loser_gives_its_heir_as_hostage_and_a_victor_throws_off_tribute(realm: World) -> None:
    ctx, state, capital, ruler = await realm_of(realm, "Highwall")
    victor = await people(realm, "Iron Folk")
    war = await open_war(ctx, victor, capital)
    book = await RealmBook.load(realm.session)
    assert await TERMS[A.HUMILIATE](ctx, war, aim(war, victor, A.HUMILIATE), (victor, capital), book) is None
    heir = await mortal(realm, "Ivo", location_id=capital.id)
    realm.session.add(DesignatedHeirRow(ruler_entity_id=ruler.id, heir_entity_id=heir.id, epoch=1))
    await realm.session.flush()
    told = await TERMS[A.HUMILIATE](ctx, war, aim(war, victor, A.HUMILIATE), (victor, capital), book)
    assert told is not None and heir.name in told[0]
    row = await realm.session.scalar(select(CaptiveRow).where(CaptiveRow.captive_entity_id == heir.id))
    assert row is not None and row.status is CaptiveStatus.WARD
    assert await TERMS[A.LIBERATE](ctx, war, aim(war, victor, A.LIBERATE), (victor, capital), book) is None
    await connect(realm.session, victor.id, capital.id, BondKind.PAYS_TRIBUTE, 1)
    assert await TERMS[A.LIBERATE](ctx, war, aim(war, victor, A.LIBERATE), (victor, capital), book) is not None
    paying = await realm.session.scalar(select(BondRow).where(BondRow.source_node_id == victor.id, BondRow.kind == BondKind.PAYS_TRIBUTE))
    assert paying is not None and paying.state != "active"
    assert state.entity.id


async def test_a_won_claim_takes_the_throne_and_a_new_government_is_imposed(realm: World) -> None:
    ctx, state, capital, _ = await realm_of(realm, "Highwall")
    victor = await mortal(realm, "Rask")
    war = await open_war(ctx, await people(realm, "Iron Folk"), capital)
    book = await RealmBook.load(realm.session)
    assert await TERMS[A.PRESS_CLAIM](ctx, war, aim(war, victor, A.PRESS_CLAIM), (victor, capital), book) is None
    claim = ClaimRow(claimant_entity_id=victor.id, polity_entity_id=state.entity.id, basis=ClaimBasis.CONQUEST)
    realm.session.add(claim)
    await realm.session.flush()
    told = await TERMS[A.PRESS_CLAIM](ctx, war, aim(war, victor, A.PRESS_CLAIM, claim=claim.id), (victor, capital), book)
    assert told is not None and claim.pressed and claim.ended_epoch == ctx.epoch
    assert book.realm_of(capital.id) is not None and book.realm_of(capital.id).ruler_id == victor.id
    imposed = await TERMS[A.CHANGE_GOVERNMENT](ctx, war, aim(war, victor, A.CHANGE_GOVERNMENT, government="not a form"), (victor, capital), book)
    assert imposed is not None and book.realm_of(capital.id).profile.government is GovernmentKind.REPUBLIC


async def test_a_beaten_cult_is_broken_and_a_beaten_people_takes_the_victors_god(realm: World) -> None:
    ctx = context(realm.session)
    victor = await people(realm, "Iron Folk")
    cult = await make(realm.session, "The Pale Choir", EntityType.CULT, CultStats(zeal=50), world_id=realm.world.id)
    loser = await people(realm, "Reed Folk")
    war = await open_war(ctx, victor, loser)
    book = await RealmBook.load(realm.session)
    assert await TERMS[A.DESTROY_CULT](ctx, war, aim(war, victor, A.DESTROY_CULT), (victor, loser), book) is None
    told = await TERMS[A.DESTROY_CULT](ctx, war, aim(war, victor, A.DESTROY_CULT), (victor, cult), book)
    assert told is not None and cult.status is not EntityStatus.CANON
    god = await son(realm.session, "Vael", realm.world.id)
    told = await TERMS[A.CONVERT](ctx, war, aim(war, victor, A.CONVERT, god=god.id), (victor, loser), book)
    assert told is not None and "took the god" in told[0]
    worships = await realm.session.scalar(
        select(BondRow).where(BondRow.source_node_id == loser.id, BondRow.kind == BondKind.WORSHIPS, BondRow.state == "active")
    )
    assert worships is not None and worships.target_node_id == god.id
