from sqlalchemy import select

from aerona.db.tables.entities import EntityRow
from aerona.db.tables.intrigue import HookRow
from aerona.db.tables.justice import CaseWitnessRow
from aerona.db.tables.polity import OfficeRow, PolityMemberRow, PolityProfileRow, SentenceRow
from aerona.db.tables.settlement import SettlementInfrastructureRow, SettlementProfileRow
from aerona.domain.enums.entity import EntityType
from aerona.domain.enums.intrigue import HookSource, HookStrength
from aerona.domain.enums.justice import CaseStage, Deposition, TrialKind, Verdict
from aerona.domain.enums.mortal import CrimeKind
from aerona.domain.enums.polity import DecisionRule, GovernmentKind, LawKind, OfficeKind
from aerona.domain.enums.settlement import SizeTier
from aerona.domain.enums.society import SocialClass
from aerona.domain.models.entity_stats import PolityStats
from aerona.engine.polity.laws import LawBook, enact
from aerona.engine.polity.trials import TrialTally, frame_case, injustices, open_case, tend_cases, try_case
from aerona.engine.settlement.book import Town
from aerona.rules.registry import Rules
from tests.engine.society.factories import Realm, context, make, mortal, settlement, tuned

OPEN = {"witnesses": 3, "speak_pct": 100, "name_at": 0, "standard": 0}


async def court(realm: Realm, name: str) -> tuple[Town, EntityRow, EntityRow]:
    entity = await settlement(realm, name)
    profile = SettlementProfileRow(settlement_entity_id=entity.id, size_tier=SizeTier.TOWN, treasury=50, unrest=10, locked=[], foreigners={})
    realm.session.add(profile)
    judge = await mortal(realm, "Justiciar Hale", location_id=entity.id)
    polity = await make(realm.session, f"Realm of {name}", EntityType.POLITY, PolityStats(), world_id=realm.world.id)
    realm.session.add(
        PolityProfileRow(
            polity_entity_id=polity.id,
            government=GovernmentKind.CHIEFDOM,
            decision_rule=DecisionRule.AUTOCRATIC,
            capital_entity_id=entity.id,
            emblem={},
            legitimacy_parts={},
            locked=[],
        )
    )
    realm.session.add(OfficeRow(polity_entity_id=polity.id, kind=OfficeKind.RULER, holder_entity_id=judge.id, powers=[]))
    realm.session.add(PolityMemberRow(polity_entity_id=polity.id, member_entity_id=entity.id))
    await realm.session.flush()
    town = Town(entity, profile, SettlementInfrastructureRow(settlement_entity_id=entity.id, locked=[]), [])
    return town, judge, polity


async def thief(realm: Realm, town: Town, name: str) -> EntityRow:
    found = await mortal(realm, name, location_id=town.entity.id)
    found.social_class = SocialClass.OUTCAST
    await realm.session.flush()
    return found


async def test_a_crime_becomes_a_case_that_witnesses_carry_to_a_verdict_and_a_sentence(realm: Realm) -> None:
    rules = tuned(trials=OPEN)
    town, judge, _ = await court(realm, "Saltmere")
    culprit = await thief(realm, town, "Kel")
    for name in ("Ana", "Bo", "Cy"):
        await mortal(realm, name, location_id=town.entity.id)
    ctx = context(realm.session, rules, epoch=3)
    case = await open_case(ctx, town, await LawBook.load(realm.session), judge=judge)
    assert case is not None and case.stage is CaseStage.TRIAL and case.accused_entity_id == culprit.id
    witnesses = list(await realm.session.scalars(select(CaseWitnessRow).where(CaseWitnessRow.case_id == case.id)))
    assert len(witnesses) == 3 and all(row.testimony is Deposition.ACCUSES for row in witnesses)
    tally = TrialTally()
    await tend_cases(context(realm.session, rules, epoch=3), tally)
    assert case.stage is CaseStage.TRIAL
    await tend_cases(context(realm.session, rules, epoch=4), tally)
    assert case.verdict is Verdict.GUILTY and not case.wrongful and tally.convicted == 1
    sentence = await realm.session.scalar(select(SentenceRow).where(SentenceRow.case_id == case.id))
    assert sentence is not None and sentence.mortal_entity_id == culprit.id


async def test_weak_evidence_blames_a_scapegoat_and_the_wrongful_conviction_breeds_grievance(realm: Realm) -> None:
    rules = tuned(trials={**OPEN, "name_at": 100, "scapegoat_pct": 100, "speak_pct": 0})
    town, judge, _ = await court(realm, "Dunmere")
    culprit = await thief(realm, town, "Rook")
    await mortal(realm, "Wren", location_id=town.entity.id)
    ctx = context(realm.session, rules, epoch=3)
    case = await open_case(ctx, town, await LawBook.load(realm.session), judge=judge)
    assert case is not None and case.accused_entity_id not in (None, culprit.id)
    await tend_cases(context(realm.session, rules, epoch=4), TrialTally())
    assert case.verdict is Verdict.GUILTY and case.wrongful
    assert town.profile.unrest > 10
    assert await injustices(context(realm.session, rules, epoch=4), town.entity.id) == 1


async def test_an_investigator_tortures_only_where_the_penal_code_allows(realm: Realm) -> None:
    rules = tuned(trials={**OPEN, "name_at": 100, "torture_reading": -100, "torture_evidence": 100, "scapegoat_pct": 0})
    town, judge, polity = await court(realm, "Ironmere")
    await thief(realm, town, "Vane")
    ctx = context(realm.session, rules, epoch=3)
    spared = await open_case(ctx, town, await LawBook.load(realm.session), judge=judge)
    assert spared is not None and not spared.tortured and spared.verdict is Verdict.DROPPED
    polity_row = await realm.session.get(EntityRow, polity.id)
    assert polity_row is not None
    await enact(ctx, polity_row, LawKind.PENAL_CODE, {"torture": "allowed", "trial": "jury"})
    case = await open_case(context(realm.session, rules, epoch=4), town, await LawBook.load(realm.session), judge=judge)
    assert case is not None and case.tortured and case.trial is TrialKind.JURY


async def test_a_framing_scheme_forges_a_case_and_a_hooked_witness_turns(realm: Realm) -> None:
    rules = tuned(trials={"standard": 100})
    town, judge, _ = await court(realm, "Lowmere")
    target = await mortal(realm, "Isa", location_id=town.entity.id)
    framer = await mortal(realm, "Jory", location_id=town.entity.id)
    ctx = context(realm.session, rules, epoch=3)
    case = await frame_case(ctx, target, framer.id, CrimeKind.TREASON)
    assert case is not None and case.forged and case.culprit_entity_id is None and case.accused_entity_id == target.id
    realm.session.add(HookRow(holder_node_id=target.id, target_node_id=framer.id, strength=HookStrength.STRONG, source=HookSource.SECRET, created_epoch=1))
    await realm.session.flush()
    await try_case(context(realm.session, rules, epoch=4), case, await LawBook.load(realm.session), TrialTally())
    witness = await realm.session.get(CaseWitnessRow, (case.id, framer.id))
    assert witness is not None and witness.testimony is Deposition.SHIELDS
    assert case.verdict is Verdict.ACQUITTED and judge.id == case.judge_entity_id
    assert Rules().trials.standard == 50
