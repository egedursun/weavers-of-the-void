from sqlalchemy import select

from aerona.db.tables.affairs import CouncilSeatRow, CourtPositionRow, CourtRow, ElectionRow, MandateRow, PolicyApprovalRow, ResolutionRow, TaxPolicyRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.estates import EstateProfileRow
from aerona.db.tables.factions import FactionProfileRow
from aerona.db.tables.finance import TradePolicyRow
from aerona.db.tables.intrigue import SecretRow
from aerona.db.tables.polity import OfficeRow, PolityMemberRow, PolityProfileRow
from aerona.db.tables.relations import RelationshipRow
from aerona.db.tables.settlement import SettlementProfileRow
from aerona.db.tables.society_depth import PolityLoyaltyRow
from aerona.domain.enums.bond import BondKind
from aerona.domain.enums.economy import CommodityKind
from aerona.domain.enums.entity import EngineKind, EntityType
from aerona.domain.enums.faction import FactionKind
from aerona.domain.enums.finance import TradePolicyKind
from aerona.domain.enums.intrigue import IntrigueSecret
from aerona.domain.enums.polity import DecisionRule, GovernmentKind, LawKind, OfficeKind
from aerona.domain.enums.settlement import SizeTier
from aerona.domain.enums.society import SocialClass
from aerona.domain.enums.statecraft import CouncilTask, CourtPosition, MandateKind, MandateState, ResolutionKind, ResolutionState, TaxKind
from aerona.domain.models.entity_stats import FactionStats, PolityStats
from aerona.engine.factions.movements import ground_of, independence
from aerona.engine.polity.assembly import AssemblyTally, tend_assemblies
from aerona.engine.polity.book import RealmBook
from aerona.engine.polity.council import CouncilTally, tend_council
from aerona.engine.polity.court import CourtTally, tend_courts
from aerona.engine.polity.elections import ElectionTally, tend_elections
from aerona.engine.polity.laws import LawBook, enact
from aerona.engine.polity.mandates import MandateTally, issue, tend_mandates
from aerona.engine.polity.policy import PolicyTally, revolution, tend_policy
from aerona.engine.polity.revenue import RevenueTally, tend_revenue
from tests.engine.society.factories import Realm, context, link, make, mortal, people, settlement, tuned


async def realm_of(realm: Realm, name: str, rule: DecisionRule = DecisionRule.AUTOCRATIC) -> tuple[EntityRow, EntityRow, EntityRow]:
    town = await settlement(realm, f"{name} Town")
    realm.session.add(SettlementProfileRow(settlement_entity_id=town.id, size_tier=SizeTier.TOWN, treasury=50, unrest=70, locked=[], foreigners={}))
    ruler = await mortal(realm, f"Ruler of {name}", location_id=town.id)
    polity = await make(realm.session, name, EntityType.POLITY, PolityStats(), world_id=realm.world.id)
    realm.session.add(
        PolityProfileRow(
            polity_entity_id=polity.id,
            government=GovernmentKind.MONARCHY,
            decision_rule=rule,
            capital_entity_id=town.id,
            core_entity_id=town.id,
            administration=60,
            legitimacy=50,
            emblem={},
            legitimacy_parts={},
            locked=[],
        )
    )
    realm.session.add(OfficeRow(polity_entity_id=polity.id, kind=OfficeKind.RULER, holder_entity_id=ruler.id, powers=[]))
    realm.session.add(PolityMemberRow(polity_entity_id=polity.id, member_entity_id=town.id))
    await realm.session.flush()
    return polity, town, ruler


async def test_officers_work_their_tasks_and_a_scornful_spymaster_leaks(realm: Realm) -> None:
    ctx = context(realm.session, tuned(affairs={"leak_below": 100}))
    polity, town, ruler = await realm_of(realm, "Corvane")
    rival, _, rival_ruler = await realm_of(realm, "Dunmark")
    spy = await mortal(realm, "Vesk", location_id=town.id)
    realm.session.add(OfficeRow(polity_entity_id=polity.id, kind=OfficeKind.SPYMASTER, holder_entity_id=spy.id, powers=[]))
    realm.session.add(SecretRow(holder_node_id=ruler.id, kind=IntrigueSecret.DEBT, known_by=[], created_epoch=1, locked=[]))
    await realm.session.flush()
    tally = CouncilTally()
    await tend_council(ctx, tally)
    office = await realm.session.scalar(select(OfficeRow).where(OfficeRow.kind == OfficeKind.SPYMASTER))
    assert office is not None and office.task is CouncilTask.DISRUPT_SCHEMES and office.diligence == 50
    secret = await realm.session.scalar(select(SecretRow).where(SecretRow.holder_node_id == ruler.id))
    assert secret is not None and rival_ruler.id in secret.known_by and tally.leaks == 1
    assert rival.id != polity.id


async def test_an_assembly_elects_its_council_by_class_and_estate(realm: Realm) -> None:
    ctx = context(realm.session)
    polity, town, _ = await realm_of(realm, "Lysmere", DecisionRule.ASSEMBLY)
    estate = await make(realm.session, "Lords of Lysmere", EntityType.FACTION, FactionStats(), world_id=realm.world.id)
    realm.session.add(FactionProfileRow(faction_entity_id=estate.id, kind=FactionKind.ESTATE, home_entity_id=town.id, influence_over={}, locked=[]))
    realm.session.add(
        EstateProfileRow(faction_entity_id=estate.id, polity_entity_id=polity.id, social_class=SocialClass.NOBLE, loyalty=60, influence=20, locked=[])
    )
    await realm.session.flush()
    tally = ElectionTally()
    await tend_elections(ctx, tally)
    assert tally.held_elections == 1
    election = await realm.session.scalar(select(ElectionRow).where(ElectionRow.polity_entity_id == polity.id))
    assert election is not None
    seats = list(await realm.session.scalars(select(CouncilSeatRow).where(CouncilSeatRow.polity_entity_id == polity.id)))
    assert sum(row.seats for row in seats) == election.seats


async def test_farmed_taxes_and_greed_breed_corruption_and_a_poll_tax_fills_the_treasury(realm: Realm) -> None:
    ctx = context(realm.session, tuned(affairs={"corruption_drift_pct": 100}))
    polity, _, _ = await realm_of(realm, "Garrow")
    realm.session.add(TaxPolicyRow(polity_entity_id=polity.id, kind=TaxKind.POLL, rate=20, farmed=True, locked=[]))
    await realm.session.flush()
    tally = RevenueTally()
    await tend_revenue(ctx, tally)
    profile = await realm.session.get(PolityProfileRow, polity.id)
    assert profile is not None and profile.corruption >= ctx.rules.affairs.farm_corruption
    poll = await realm.session.get(TaxPolicyRow, (polity.id, TaxKind.POLL))
    assert poll is not None and poll.take > 0 and tally.farmed == 1
    assert await realm.session.get(TaxPolicyRow, (polity.id, TaxKind.LAND)) is not None


async def test_mandates_calm_ban_and_fail_at_a_cost(realm: Realm) -> None:
    ctx = context(realm.session, tuned(affairs={"mandate_epochs": 1}), epoch=3)
    polity, town, _ = await realm_of(realm, "Harrowmere")
    book = await RealmBook.load(realm.session)
    target = book.realms[polity.id]
    ban = await issue(ctx, target, MandateKind.EXPORT_BAN, settlement_id=None, commodity=CommodityKind.GRAIN)
    assert ban is not None
    embargo = await realm.session.scalar(select(TradePolicyRow).where(TradePolicyRow.issuer_node_id == polity.id))
    assert embargo is not None and embargo.kind is TradePolicyKind.EMBARGO
    order = await issue(ctx, target, MandateKind.PRODUCE, settlement_id=town.id, commodity=CommodityKind.WEAPONS, amount=10)
    assert order is not None
    tally = MandateTally()
    await tend_mandates(context(realm.session, ctx.rules, epoch=4), tally)
    assert order.state is MandateState.FAILED and ban.state is MandateState.MET
    profile = await realm.session.get(PolityProfileRow, polity.id)
    assert profile is not None and profile.legitimacy < 50
    curfew = await realm.session.scalar(select(MandateRow).where(MandateRow.kind == MandateKind.CURFEW))
    assert curfew is not None


async def test_laws_move_class_approval_and_a_revolution_rewrites_the_fundamental_law(realm: Realm) -> None:
    ctx = context(realm.session)
    polity, _, _ = await realm_of(realm, "Iskar")
    entity = await realm.session.get(EntityRow, polity.id)
    assert entity is not None
    await enact(ctx, entity, LawKind.SLAVERY, {"status": "allowed"})
    await tend_policy(ctx, PolicyTally())
    bound = await realm.session.get(PolicyApprovalRow, (polity.id, SocialClass.SERF_OR_SLAVE))
    nobles = await realm.session.get(PolicyApprovalRow, (polity.id, SocialClass.NOBLE))
    assert bound is not None and bound.approval < 0 and nobles is not None and nobles.approval > 0
    book = await RealmBook.load(realm.session)
    assert await revolution(ctx, book.realms[polity.id], await LawBook.load(realm.session))
    await tend_policy(ctx, PolicyTally())
    profile = await realm.session.get(PolityProfileRow, polity.id)
    assert profile is not None and profile.decision_rule is DecisionRule.ASSEMBLY and profile.government is GovernmentKind.REPUBLIC


async def test_an_assembly_binds_its_members_to_an_embargo_until_it_lapses(realm: Realm) -> None:
    ctx = context(realm.session, tuned(affairs={"resolution_pct": 100, "resolution_epochs": 1}), epoch=3)
    first, first_town, _ = await realm_of(realm, "Aster")
    second, second_town, _ = await realm_of(realm, "Brume")
    foe, foe_town, _ = await realm_of(realm, "Cinder")
    assembly = await make(realm.session, "Concord of Worlds", EntityType.FACTION, FactionStats(), world_id=realm.world.id)
    assembly.engine_kind = EngineKind.INTERWORLD_FEDERATION
    for town in (first_town, second_town):
        await link(realm.session, town.id, assembly.id, BondKind.MEMBER_OF)
    await link(realm.session, foe_town.id, first_town.id, BondKind.ENEMY)
    tally = AssemblyTally()
    await tend_assemblies(ctx, tally)
    resolution = await realm.session.scalar(select(ResolutionRow))
    assert resolution is not None and resolution.kind is ResolutionKind.EMBARGO and resolution.state is ResolutionState.PASSED
    embargoes = list(await realm.session.scalars(select(TradePolicyRow).where(TradePolicyRow.kind == TradePolicyKind.EMBARGO)))
    assert {row.issuer_node_id for row in embargoes} == {first.id, second.id} and all(row.partner_node_id == foe.id for row in embargoes)
    await tend_assemblies(context(realm.session, ctx.rules, epoch=4), tally)
    await realm.session.flush()
    assert resolution.state is ResolutionState.LAPSED and tally.lapsed == 1
    assert list(await realm.session.scalars(select(TradePolicyRow).where(TradePolicyRow.kind == TradePolicyKind.EMBARGO))) == []


async def test_a_court_gathers_courtiers_fills_positions_and_shines(realm: Realm) -> None:
    ctx = context(realm.session, tuned(affairs={"talent_pct": 0}))
    polity, town, ruler = await realm_of(realm, "Velmar")
    courtier = await mortal(realm, "Ansel", location_id=town.id)
    realm.session.add(RelationshipRow(holder_node_id=courtier.id, subject_node_id=ruler.id, friendship=20, kinds=[], since_epoch=1, last_epoch=1))
    await realm.session.flush()
    tally = CourtTally()
    await tend_courts(ctx, tally)
    court = await realm.session.get(CourtRow, polity.id)
    assert court is not None and court.courtiers == 1 and court.grandeur > 0
    steward = await realm.session.get(CourtPositionRow, (polity.id, CourtPosition.STEWARD))
    assert steward is not None and steward.holder_entity_id == courtier.id
    profile = await realm.session.get(PolityProfileRow, polity.id)
    assert profile is not None and profile.treasury >= ctx.rules.affairs.steward_gain


async def test_a_distinct_cohesive_people_with_grievances_yearns_to_break_away(realm: Realm) -> None:
    ctx = context(realm.session)
    polity, town, _ = await realm_of(realm, "Orveth")
    folk = await people(realm, "Folk of the Fens")
    await link(realm.session, town.id, folk.id, BondKind.DESCENDS_FROM)
    await realm.session.flush()
    book = await RealmBook.load(realm.session)
    realm_row = book.realms[polity.id]
    ground = await ground_of(ctx, town, realm_row, await LawBook.load(realm.session))
    calm = await independence(ctx, ground)
    realm.session.add(PolityLoyaltyRow(polity_entity_id=polity.id, member_entity_id=town.id, grievances=40, parts={}, locked=[]))
    await realm.session.flush()
    stirred = await independence(ctx, ground)
    assert stirred > calm > 0
