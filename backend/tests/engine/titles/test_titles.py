from sqlalchemy import select

from aerona.db.tables.entities import EntityRow
from aerona.db.tables.polity import ClaimRow, OfficeRow, PolityProfileRow, PolityTerritoryRow
from aerona.db.tables.renown import RulerCurrencyRow
from aerona.db.tables.titles import DeJureLinkRow, TitleHolderRow, TitleProfileRow
from aerona.domain.enums.entity import EntityType
from aerona.domain.enums.polity import ClaimBasis, DecisionRule, GovernmentKind, OfficeKind
from aerona.domain.enums.titles import TitleTenure, TitleTier
from aerona.domain.models.entity_stats import PolityStats
from aerona.engine.polity.book import RealmBook
from aerona.engine.polity.titles import TitleTally, drift_lands, follow_rulers, press_claims, primary_title, seed_titles, usurp_and_create
from tests.engine.society.factories import Realm, context, make, mortal, tuned


async def kingdom(realm: Realm, name: str, ruler: EntityRow, tier: int, land: int) -> EntityRow:
    polity = await make(realm.session, name, EntityType.POLITY, PolityStats(), world_id=realm.world.id)
    realm.session.add(
        PolityProfileRow(
            polity_entity_id=polity.id,
            government=GovernmentKind.CHIEFDOM,
            decision_rule=DecisionRule.AUTOCRATIC,
            tier=tier,
            emblem={},
            legitimacy_parts={},
            locked=[],
        )
    )
    realm.session.add(OfficeRow(polity_entity_id=polity.id, kind=OfficeKind.RULER, holder_entity_id=ruler.id, powers=[]))
    realm.session.add(PolityTerritoryRow(polity_entity_id=polity.id, region_entity_id=land, control=80, locked=[]))
    await realm.session.flush()
    return polity


async def test_every_realm_founds_a_title_that_follows_its_throne(realm: Realm) -> None:
    ctx = context(realm.session)
    queen = await mortal(realm, "Aud")
    heir = await mortal(realm, "Bryn")
    polity = await kingdom(realm, "Varn", queen, 3, realm.region.id)
    tally = TitleTally()
    await seed_titles(ctx, await RealmBook.load(realm.session), tally)
    title = await primary_title(ctx, polity.id)
    assert title is not None and title.rank is TitleTier.REALM and title.holder_node_id == queen.id and title.emblem
    assert await realm.session.get(DeJureLinkRow, (title.title_entity_id, realm.region.id)) is not None
    office = await realm.session.scalar(select(OfficeRow).where(OfficeRow.polity_entity_id == polity.id))
    assert office is not None
    office.holder_entity_id = heir.id
    await realm.session.flush()
    await follow_rulers(ctx, await RealmBook.load(realm.session), tally)
    assert title.holder_node_id == heir.id and tally.passed == 1
    history = list(
        await realm.session.scalars(select(TitleHolderRow).where(TitleHolderRow.title_entity_id == title.title_entity_id).order_by(TitleHolderRow.id))
    )
    assert [row.tenure for row in history] == [TitleTenure.FOUNDED, TitleTenure.INHERITED] and history[0].until_epoch == ctx.epoch


async def test_held_lands_drift_and_foreign_lands_bring_claims(realm: Realm) -> None:
    ctx = context(realm.session, tuned(titles={"drift_years": 50}))
    first_ruler = await mortal(realm, "Cael")
    second_ruler = await mortal(realm, "Dov")
    first = await kingdom(realm, "Ostra", first_ruler, 1, realm.region.id)
    second = await kingdom(realm, "Pell", second_ruler, 1, realm.far_region.id)
    tally = TitleTally()
    await seed_titles(ctx, await RealmBook.load(realm.session), tally)
    assert tally.founded == 2
    realm.session.add(PolityTerritoryRow(polity_entity_id=first.id, region_entity_id=realm.far_region.id, control=60, locked=[]))
    await realm.session.flush()
    book = await RealmBook.load(realm.session)
    await press_claims(ctx, book, tally)
    claim = await realm.session.scalar(select(ClaimRow).where(ClaimRow.claimant_entity_id == first_ruler.id))
    assert claim is not None and claim.basis is ClaimBasis.DE_JURE and claim.polity_entity_id == second.id
    await drift_lands(ctx, book, tally)
    assert tally.drifted == 0
    held = await realm.session.scalar(select(PolityTerritoryRow).where(PolityTerritoryRow.polity_entity_id == second.id))
    assert held is not None
    await realm.session.delete(held)
    await realm.session.flush()
    await drift_lands(ctx, await RealmBook.load(realm.session), tally)
    mine = await primary_title(ctx, first.id)
    assert mine is not None and tally.drifted == 1
    assert await realm.session.get(DeJureLinkRow, (mine.title_entity_id, realm.far_region.id)) is not None
    assert await realm.session.scalar(select(TitleProfileRow).where(TitleProfileRow.polity_entity_id == second.id)) is not None


async def test_creating_a_higher_title_costs_its_holder_prestige(realm: Realm) -> None:
    ctx = context(realm.session, tuned(titles={"creation_prestige": 15}))
    king = await mortal(realm, "Ewan")
    polity = await kingdom(realm, "Quill", king, 1, realm.region.id)
    await seed_titles(ctx, await RealmBook.load(realm.session), TitleTally())
    profile = await realm.session.get(PolityProfileRow, polity.id)
    assert profile is not None
    profile.tier = 3
    realm.session.add(RulerCurrencyRow(subject_node_id=king.id, prestige=40, piety=0, dread=0, tyranny=0, updated_epoch=ctx.epoch, locked=[]))
    await realm.session.flush()
    tally = TitleTally()
    await usurp_and_create(ctx, await RealmBook.load(realm.session), tally)
    purse = await realm.session.get(RulerCurrencyRow, king.id)
    assert tally.created == 1 and purse is not None and purse.prestige == 25
