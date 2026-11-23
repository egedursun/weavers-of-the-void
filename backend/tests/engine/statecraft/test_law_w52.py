from aerona.catalog.law_areas import LAW_AREAS
from aerona.catalog.law_depth import COURT_BIAS
from aerona.catalog.life.customs import EVIDENCE, PATH_WAIT, RIGHT_GRIEVANCE
from aerona.catalog.life.polity import AREA_CLASH, CLAIM_STRENGTHS
from aerona.db.tables.customs import EvidenceRow, MembershipCategoryRow, MembershipRow
from aerona.db.tables.justice import CrimeCaseRow
from aerona.db.tables.settlement import SettlementProfileRow
from aerona.domain.enums.customs import EvidenceKind, MemberRight, Membership, Naturalisation
from aerona.domain.enums.justice import CaseStage
from aerona.domain.enums.law_depth import CourtLevel
from aerona.domain.enums.mortal import CrimeKind
from aerona.domain.enums.polity import ClaimBasis, LawArea, LawKind
from aerona.engine.customs.civics import lacking_rights, weight_of
from aerona.engine.customs.rights import voteless_share
from aerona.engine.law.jurisdictions import lean
from aerona.engine.polity.law_areas import area_weight
from tests.engine.society.factories import Realm, context, mortal, tuned
from tests.engine.statecraft.test_affairs import realm_of


def test_every_law_kind_sits_in_one_area_and_new_areas_hold_laws() -> None:
    assert LAW_AREAS[LawKind.GUILD_CHARTER] is LawArea.COMMERCE
    assert LAW_AREAS[LawKind.TITHE] is LawArea.FAITH and LAW_AREAS[LawKind.LABOUR_LAW] is LawArea.LABOUR
    assert set(AREA_CLASH) == set(LawArea) and set(COURT_BIAS) == set(CourtLevel)
    assert CLAIM_STRENGTHS[ClaimBasis.ADOPTION] and PATH_WAIT[Naturalisation.UNION] > 0
    assert EVIDENCE[EvidenceKind.HEARSAY].hearsay and set(RIGHT_GRIEVANCE) == set(MemberRight)


async def test_a_clash_weighs_by_area_and_a_military_court_leans_to_soldiers(realm: Realm) -> None:
    ctx = context(realm.session, tuned(law={"faith_clash_weight": 90}, courts={"military_bias": 50}))
    assert area_weight(ctx.rules, LawArea.FAITH) == 0.9
    case = CrimeCaseRow(crime=CrimeKind.THEFT, court=CourtLevel.MILITARY, evidence=50, stage=CaseStage.TRIAL, opened_epoch=3)
    lean(ctx, case, True)
    assert case.evidence == 40
    lean(ctx, case, False)
    assert case.evidence == 50


async def test_sworn_and_hearsay_evidence_weigh_by_kind(realm: Realm) -> None:
    ctx = context(realm.session, tuned(evidence={"hearsay_weight": 60}, oaths={"testimony_weight_pct": 50}))
    case = CrimeCaseRow(crime=CrimeKind.THEFT, evidence=0, stage=CaseStage.TRIAL, opened_epoch=3)
    heard = EvidenceRow(case_id=0, kind=EvidenceKind.HEARSAY, reliability=50, found_epoch=3, locked=[])
    sworn = EvidenceRow(case_id=0, kind=EvidenceKind.WITNESS, reliability=50, sworn=True, found_epoch=3, locked=[])
    assert await weight_of(ctx, case, heard) == 0.6
    assert await weight_of(ctx, case, sworn) == 1.5


async def test_those_lacking_rights_grow_restless_and_cannot_vote(realm: Realm) -> None:
    ctx = context(realm.session, tuned(membership={"vote_grievance": 50, "property_grievance": 50}))
    polity, town, _ = await realm_of(realm, "Corvane")
    folk = await mortal(realm, "Ash", location_id=town.id)
    realm.session.add(MembershipCategoryRow(polity_entity_id=polity.id, category=Membership.BOUND, rights=[], locked=[]))
    realm.session.add(MembershipRow(mortal_entity_id=folk.id, polity_entity_id=polity.id, category=Membership.BOUND, since_epoch=1, locked=[]))
    await realm.session.flush()
    profile = await realm.session.get(SettlementProfileRow, town.id)
    assert profile is not None
    before = profile.unrest
    await lacking_rights(ctx)
    assert profile.unrest > before
    assert await voteless_share(realm.session, polity.id) == 1.0
