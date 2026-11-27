from sqlalchemy import select

from aerona.db.tables.bonds import BondRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.intrigue import FavourRow
from aerona.db.tables.polity import OfficeRow, PolityMemberRow, PolityProfileRow, PolityTerritoryRow, TreatyPartyRow, TreatyProfileRow, VassalageRow
from aerona.db.tables.statecraft import CrisisBackerRow, CrisisRow, DiplomacyProfileRow, PolityRegardRow, SphereRow
from aerona.domain.enums.bond import BondKind
from aerona.domain.enums.entity import EntityStatus, EntityType
from aerona.domain.enums.polity import DecisionRule, GovernmentKind, OfficeKind, RegionalStanding, TreatyKind
from aerona.domain.enums.statecraft import CrisisDemand, CrisisSide, CrisisState, SubjectKind
from aerona.domain.enums.war import WarCause
from aerona.domain.models.entity_stats import PolityStats
from aerona.engine.polity.book import RealmBook
from aerona.engine.polity.coalitions import CoalitionTally, tend_coalitions
from aerona.engine.polity.crises import CrisisTally, Verdict, crisis_instead
from aerona.engine.polity.crisis_outcomes import settle
from aerona.engine.polity.law_effects import may_coin
from aerona.engine.polity.regard import RegardTally, on_conquest, tend_regard
from aerona.engine.polity.spheres import SphereTally, tend_spheres
from aerona.engine.polity.subjects import SubjectTally, forbidden_war, kind_for, pays_tribute, sends_levies, tend_subjects
from aerona.engine.polity.wars import comrades
from aerona.engine.primitives.distance import RegionAtlas
from tests.engine.society.factories import Realm, context, make, mortal, people, settlement, tuned


async def polity(realm: Realm, name: str, *, treasury: int = 100, standing: RegionalStanding = RegionalStanding.MINOR_POWER) -> tuple[EntityRow, EntityRow]:
    core = await people(realm, f"Folk of {name}")
    found = await make(realm.session, name, EntityType.POLITY, PolityStats(), world_id=realm.world.id)
    realm.session.add(
        PolityProfileRow(
            polity_entity_id=found.id,
            government=GovernmentKind.CHIEFDOM,
            decision_rule=DecisionRule.AUTOCRATIC,
            core_entity_id=core.id,
            treasury=treasury,
            standing=standing,
            emblem={},
            legitimacy_parts={},
            locked=[],
        )
    )
    realm.session.add(PolityMemberRow(polity_entity_id=found.id, member_entity_id=core.id))
    await realm.session.flush()
    return found, core


async def test_a_conquest_alarms_its_neighbours_and_the_fearful_band_into_a_coalition(realm: Realm) -> None:
    rules = tuned(statecraft={"conquest_threat": 100, "far_threat_pct": 100, "coalition_war_pct": 0})
    ctx = context(realm.session, rules)
    aggressor, _ = await polity(realm, "Iron Crown")
    first, _ = await polity(realm, "Reed Throne")
    second, _ = await polity(realm, "Salt Throne")
    assert await on_conquest(ctx, aggressor.id) == 2
    regard = await realm.session.get(PolityRegardRow, (first.id, aggressor.id))
    assert regard is not None and regard.threat >= rules.diplomacy.coalition_threshold
    tally = CoalitionTally()
    await tend_coalitions(ctx, tally)
    assert tally.formed == 1
    coalition = await realm.session.scalar(select(TreatyProfileRow).where(TreatyProfileRow.kind == TreatyKind.COALITION))
    assert coalition is not None
    await tend_regard(ctx, RegardTally())
    assert regard.threat == 100 - rules.statecraft.threat_decay
    assert await realm.session.get(DiplomacyProfileRow, second.id) is not None


async def test_a_coalition_never_binds_the_power_it_was_formed_against(realm: Realm) -> None:
    rules = tuned(statecraft={"coalition_war_pct": 0, "coalition_members": 2})
    ctx = context(realm.session, rules)
    feared, feared_core = await polity(realm, "Iron Crown")
    first, _ = await polity(realm, "Reed Throne")
    second, _ = await polity(realm, "Salt Throne")
    for holder in (first, second, feared):
        realm.session.add(PolityRegardRow(holder_entity_id=holder.id, subject_entity_id=feared.id, threat=100, trust=0, epoch=1, locked=[]))
    await realm.session.flush()
    await tend_coalitions(ctx, CoalitionTally())
    bound = set(await realm.session.scalars(select(TreatyPartyRow.party_node_id)))
    assert bound and feared_core.id not in bound


async def test_a_claim_war_opens_a_crisis_and_a_concession_pays_and_rewards_backers(realm: Realm) -> None:
    ctx = context(realm.session, tuned(statecraft={"crisis_pct": 100}))
    demander, demander_core = await polity(realm, "Lion Throne", treasury=0)
    target, target_core = await polity(realm, "Hart Throne", treasury=200)
    backer, _ = await polity(realm, "Owl Throne")
    assert await crisis_instead(ctx, demander_core.id, target_core.id, WarCause.CLAIM)
    crisis = await realm.session.scalar(select(CrisisRow))
    assert crisis is not None and crisis.demand is CrisisDemand.CEDE_REGION and crisis.state is CrisisState.ESCALATING
    crisis.demand, crisis.amount = CrisisDemand.PAY, 50
    realm.session.add(CrisisBackerRow(crisis_id=crisis.id, backer_entity_id=backer.id, side=CrisisSide.DEMANDER, promised=20, swing=True))
    await realm.session.flush()
    book = await RealmBook.load(realm.session)
    await settle(ctx, book, Verdict(crisis, CrisisState.CONCEDED), CrisisTally())
    assert crisis.state is CrisisState.CONCEDED
    assert book.realms[demander.id].profile.treasury == 50 and book.realms[target.id].profile.treasury == 150
    favour = await realm.session.scalar(select(FavourRow).where(FavourRow.owed_by_node_id == demander.id))
    assert favour is not None and favour.owed_to_node_id == backer.id


async def test_a_debt_war_against_a_realm_in_debt_demands_no_payment(realm: Realm) -> None:
    ctx = context(realm.session, tuned(statecraft={"crisis_pct": 100}))
    _, creditor_core = await polity(realm, "Gull Throne")
    _, debtor_core = await polity(realm, "Moth Throne", treasury=-40)
    assert not await crisis_instead(ctx, creditor_core.id, debtor_core.id, WarCause.DEBT)
    assert await realm.session.scalar(select(CrisisRow)) is None


async def test_a_crisis_that_no_one_yields_becomes_war(realm: Realm) -> None:
    ctx = context(realm.session)
    demander, demander_core = await polity(realm, "Wolf Throne")
    target, target_core = await polity(realm, "Bear Throne")
    crisis = CrisisRow(demander_entity_id=demander.id, target_entity_id=target.id, demand=CrisisDemand.PAY, amount=10, opened_epoch=1, locked=[])
    realm.session.add(crisis)
    await realm.session.flush()
    await settle(ctx, await RealmBook.load(realm.session), Verdict(crisis, CrisisState.WAR), CrisisTally())
    assert crisis.state is CrisisState.WAR
    enemy = await realm.session.scalar(select(BondRow).where(BondRow.kind == BondKind.ENEMY, BondRow.source_node_id == demander_core.id))
    assert enemy is not None and enemy.target_node_id == target_core.id


async def test_spheres_are_contested_and_the_great_powers_meet_in_summits(realm: Realm) -> None:
    ctx = context(realm.session, tuned(statecraft={"summit_years": 50, "sphere_contest": 40}))
    strong, _ = await polity(realm, "Sun Crown", standing=RegionalStanding.GREAT_POWER)
    weak, _ = await polity(realm, "Moon Crown", standing=RegionalStanding.GREAT_POWER)
    client, _ = await polity(realm, "Star Crown")
    realm.session.add(SphereRow(power_entity_id=strong.id, client_entity_id=client.id, strength=60, since_epoch=1))
    realm.session.add(SphereRow(power_entity_id=weak.id, client_entity_id=client.id, strength=30, since_epoch=1))
    await realm.session.flush()
    tally = SphereTally()
    await tend_spheres(ctx, tally)
    assert await realm.session.get(SphereRow, (weak.id, client.id)) is None and tally.lost == 1
    winner = await realm.session.get(SphereRow, (strong.id, client.id))
    assert winner is not None and winner.strength > 60
    assert tally.summits == 1
    trust = await realm.session.get(PolityRegardRow, (strong.id, weak.id))
    assert trust is not None and trust.trust > 50


async def test_subject_kinds_bind_tribute_levies_war_and_coin(realm: Realm) -> None:
    ctx = context(realm.session)
    overlord, _ = await polity(realm, "High Crown")
    vassal, vassal_core = await polity(realm, "Low Crown")
    other, other_core = await polity(realm, "Far Crown")
    row = VassalageRow(vassal_entity_id=vassal.id, overlord_entity_id=overlord.id, kind=SubjectKind.TRIBUTARY, locked=[])
    realm.session.add(row)
    await realm.session.flush()
    assert pays_tribute(row) and not sends_levies(row)
    assert await forbidden_war(ctx, vassal_core.id, other_core.id, WarCause.HOSTILITY)
    assert not await forbidden_war(ctx, vassal_core.id, other_core.id, WarCause.INDEPENDENCE)
    assert not await may_coin(realm.session, ctx.rules, vassal_core.id)
    row.private_war, row.coinage = True, True
    assert not await forbidden_war(ctx, vassal_core.id, other_core.id, WarCause.HOSTILITY)
    row.kind = SubjectKind.PERSONAL_UNION
    await realm.session.flush()
    tally = SubjectTally()
    await tend_subjects(ctx, tally)
    await realm.session.flush()
    assert tally.dissolved == 1 and await realm.session.get(VassalageRow, vassal.id) is None
    assert other.id != overlord.id


async def test_subjects_become_tributaries_clients_or_protectorates_and_are_defended(realm: Realm) -> None:
    ctx = context(realm.session, tuned(statecraft={"protectorate_tiers": 2}))
    overlord, overlord_core = await polity(realm, "Great Crown")
    vassal, vassal_core = await polity(realm, "Small Crown")
    lord = await mortal(realm, "Lord of the Small Crown")
    realm.session.add(OfficeRow(polity_entity_id=vassal.id, kind=OfficeKind.RULER, holder_entity_id=lord.id, locked=[]))
    await realm.session.flush()
    book = await RealmBook.load(realm.session)
    high, low = book.realms[overlord.id], book.realms[vassal.id]
    assert await kind_for(ctx, book, low, high) is SubjectKind.TRIBUTARY
    realm.session.add(SphereRow(power_entity_id=overlord.id, client_entity_id=vassal.id, strength=50, since_epoch=1))
    await realm.session.flush()
    assert await kind_for(ctx, book, low, high) is SubjectKind.CLIENT
    await realm.session.delete(await realm.session.get(SphereRow, (overlord.id, vassal.id)))
    for found in (overlord, vassal):
        realm.session.add(PolityTerritoryRow(polity_entity_id=found.id, region_entity_id=realm.region.id, control=80, locked=[]))
    second_town = await settlement(realm, "Small Crown Market")
    realm.session.add(PolityMemberRow(polity_entity_id=vassal.id, member_entity_id=second_town.id))
    high.profile.tier, low.profile.tier = 3, 0
    await realm.session.flush()
    book = await RealmBook.load(realm.session)
    high, low = book.realms[overlord.id], book.realms[vassal.id]
    assert await kind_for(ctx, book, low, high) is SubjectKind.PROTECTORATE
    row = VassalageRow(vassal_entity_id=vassal.id, overlord_entity_id=overlord.id, kind=SubjectKind.PROTECTORATE, locked=[])
    realm.session.add(row)
    await realm.session.flush()
    book = await RealmBook.load(realm.session)
    assert overlord_core.id in comrades(book, vassal_core.id)
    row.kind = SubjectKind.VASSAL
    assert overlord_core.id not in comrades(book, vassal_core.id)


async def test_the_realm_book_lasts_through_births_and_is_read_again_when_a_realm_comes_goes_or_changes(realm: Realm) -> None:
    first, _ = await polity(realm, "Ashmark")
    book = await RealmBook.load(realm.session)
    assert first.id in book.realms
    await people(realm, "Wanderers")
    await realm.session.flush()
    kept = await RealmBook.load(realm.session)
    assert kept.realms is book.realms and kept.atlas is await RegionAtlas.load(realm.session)
    second, _ = await polity(realm, "Birchmark")
    grown = await RealmBook.load(realm.session)
    assert grown.realms is not book.realms and second.id in grown.realms
    first.status, first.end_epoch = EntityStatus.DEAD, 2
    fallen = await RealmBook.load(realm.session)
    assert fallen is not grown and first.id not in fallen.realms and second.id in fallen.realms
    assert await RealmBook.load(realm.session) is fallen
