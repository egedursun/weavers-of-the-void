from aerona.db.tables.justice import CaseWitnessRow
from aerona.domain.enums.justice import Deposition, TrialKind
from aerona.domain.enums.mortal import CrimeKind
from aerona.engine.polity.trials import TRIALS, report_crime
from aerona.engine.primitives.stats import set_stats, stat
from tests.engine.justice.test_trials import court, thief
from tests.engine.society.factories import Realm, context, mortal, tuned


async def test_a_jury_weighs_evidence_and_accusing_witnesses(realm: Realm) -> None:
    ctx = context(realm.session, tuned(trials={"standard": 60}))
    town, _, _ = await court(realm, "Saltmere")
    culprit = await thief(realm, town, "Rask")
    case = await report_crime(ctx, town.entity.id, culprit.id, CrimeKind.THEFT)
    assert case is not None
    case.evidence = 10
    assert not await TRIALS[TrialKind.JURY](ctx, case, culprit)
    witness = await mortal(realm, "Ilsa", location_id=town.entity.id)
    realm.session.add(CaseWitnessRow(case_id=case.id, witness_entity_id=witness.id, testimony=Deposition.ACCUSES, reliability=100))
    case.evidence = 59
    await realm.session.flush()
    assert await TRIALS[TrialKind.JURY](ctx, case, culprit)


async def test_a_trial_by_combat_wounds_the_loser_and_convicts_a_beaten_accused(realm: Realm) -> None:
    ctx = context(realm.session, tuned(trials={"combat_hp": 10}))
    town, _, _ = await court(realm, "Saltmere")
    accused = await thief(realm, town, "Rask")
    case = await report_crime(ctx, town.entity.id, accused.id, CrimeKind.THEFT)
    assert case is not None
    investigator = case.investigator_entity_id
    case.investigator_entity_id = None
    assert not await TRIALS[TrialKind.COMBAT](ctx, case, accused)
    case.investigator_entity_id = investigator
    champion = await mortal(realm, "Bram", location_id=town.entity.id)
    set_stats(champion, strength=100)
    set_stats(accused, strength=0)
    realm.session.add(CaseWitnessRow(case_id=case.id, witness_entity_id=champion.id, testimony=Deposition.ACCUSES, reliability=50))
    await realm.session.flush()
    hp = stat(accused, "hp") or 0
    assert await TRIALS[TrialKind.COMBAT](ctx, case, accused)
    assert (stat(accused, "hp") or 0) < hp


async def test_an_ordeal_burns_and_spares_the_innocent_more_often(realm: Realm) -> None:
    town, _, _ = await court(realm, "Saltmere")
    culprit = await thief(realm, town, "Rask")
    innocent = await mortal(realm, "Ilsa", location_id=town.entity.id)
    sure = context(realm.session, tuned(trials={"ordeal_pct": 100}))
    case = await report_crime(sure, town.entity.id, culprit.id, CrimeKind.THEFT)
    assert case is not None
    hp = stat(innocent, "hp") or 0
    assert not await TRIALS[TrialKind.ORDEAL](sure, case, innocent)
    assert (stat(innocent, "hp") or 0) < hp
    assert await TRIALS[TrialKind.ORDEAL](sure, case, culprit)
