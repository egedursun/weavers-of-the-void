from typing import Any

from sqlalchemy import select

from aerona.catalog.civics import LAW_GATES
from aerona.core.errors import ValidationFailedError
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.polity import LawProfileRow, OfficeRow
from aerona.domain.enums.action import ActionKind
from aerona.domain.enums.agent import AgentKind
from aerona.domain.enums.entity import EntityStatus, EntityType
from aerona.domain.enums.justice import TrialKind
from aerona.domain.enums.modifier import IncidentRole
from aerona.domain.enums.mortal import CrimeKind
from aerona.domain.enums.polity import DecisionRule, LawKind, LegitimacyBasis, OfficeKind
from aerona.engine.lore.civics import realm_allows, unlearned
from aerona.engine.mortal.justice import CRIME_TEXT
from aerona.engine.polity.book import Realm, RealmBook
from aerona.engine.polity.enactment import COUNCIL, law_title, pending_kind, propose
from aerona.engine.polity.laws import LawBook
from aerona.engine.polity.trials import TRIAL_TEXT, accuse_case
from aerona.prompts import MortalToolId
from aerona.prompts.tools.results import MortalResult, result
from aerona.tools.framework.call import MortalCall
from aerona.tools.framework.inputs import ToolInput
from aerona.tools.framework.spec import ToolMeta, ToolSpec, mortal_standard_action
from aerona.tools.framework.validation import fail

SEATS = frozenset({OfficeKind.RULER, *COUNCIL})
BASES = {
    DecisionRule.AUTOCRATIC: LegitimacyBasis.DECREE,
    DecisionRule.COUNCIL: LegitimacyBasis.COUNCIL,
    DecisionRule.ASSEMBLY: LegitimacyBasis.COUNCIL,
    DecisionRule.DIVINE: LegitimacyBasis.DIVINE,
}


class ProposeLawInput(ToolInput):
    kind: LawKind
    params: dict[str, int | str | bool] | None = None


class AccuseInput(ToolInput):
    accused_id: int
    crime: CrimeKind


async def seat_of(call: MortalCall) -> Realm | None:
    polity = await call.session.scalar(
        select(OfficeRow.polity_entity_id).where(OfficeRow.holder_entity_id == call.me.id, OfficeRow.kind.in_(list(SEATS))).order_by(OfficeRow.id).limit(1)
    )
    book = await RealmBook.load(call.session)
    return book.realms.get(polity) if polity is not None else None


async def law_known(call: MortalCall, realm: Realm, kind: LawKind) -> None:
    needed = LAW_GATES.get(kind)
    if not await realm_allows(call.session, realm, needed):
        fail(MortalResult.PROPOSAL_REFUSED, why=f"the realm has not yet learned {unlearned(needed)}, which such a law needs")


async def bring_law(call: MortalCall, realm: Realm, kind: LawKind, params: dict[str, int | str | bool]) -> str:
    await law_known(call, realm, kind)
    if await pending_kind(call.tick, realm.entity.id, kind) is not None:
        fail(MortalResult.PROPOSAL_REFUSED, why="a proposal of that kind is already under debate")
    current = next((row for row in (await laws_of(call, realm)) if row.kind is kind), None)
    try:
        row = await propose(
            call.tick,
            realm,
            kind,
            params,
            champion_id=call.me.id,
            basis=BASES[realm.profile.decision_rule],
            law_id=current.law_entity_id if current is not None else None,
        )
    except ValidationFailedError as error:
        fail(MortalResult.LAW_TERMS_INVALID, reason=str(error))
    if row is None:
        fail(MortalResult.PROPOSAL_REFUSED, why="the realm already debates as many laws as it can, or a god holds it")
    title = law_title(kind)
    call.target(realm.entity.id)
    await call.record("tools.mortal.law_proposed", roles={IncidentRole.ACTOR: call.me.id, IncidentRole.AUTHORITY: realm.entity.id}, facts={"law": kind})
    return result(MortalResult.LAW_PROPOSED, law=title, realm=realm.entity.name, stall=call.rules.enactment.stall_epochs)


async def laws_of(call: MortalCall, realm: Realm) -> list[LawProfileRow]:
    book = await LawBook.load(call.session)
    return [book.profiles[law_id] for law_id in book.by_node.get(realm.entity.id, []) if law_id in book.profiles]


async def propose_law(call: MortalCall, args: ProposeLawInput) -> str:
    realm = await seat_of(call)
    if realm is None:
        fail(MortalResult.PROPOSAL_REFUSED, why="you hold no throne or council seat in a realm")
    return await bring_law(call, realm, args.kind, args.params or {})


async def accuse(call: MortalCall, args: AccuseInput) -> str:
    accused = await call.session.get(EntityRow, args.accused_id)
    if accused is None or accused.entity_type is not EntityType.MORTAL or accused.status is not EntityStatus.CANON:
        fail(MortalResult.ACCUSATION_REFUSED, why="there is no such living mortal")
    if accused.id == call.me.id:
        fail(MortalResult.ACCUSATION_REFUSED, why="you cannot accuse yourself")
    if accused.location_id is None or accused.location_id != call.me.location_id:
        fail(MortalResult.ACCUSATION_REFUSED, why="they do not live in your settlement")
    case = await accuse_case(call.tick, call.me, accused, args.crime)
    if case is None:
        fail(MortalResult.ACCUSATION_REFUSED, why="there is no court where they live, or a god shields them")
    place = await call.session.get(EntityRow, accused.location_id)
    crime = CRIME_TEXT[args.crime]
    call.target(accused.id)
    await call.record(
        "tools.mortal.accusation",
        roles={IncidentRole.ACCUSER: call.me.id, IncidentRole.ACCUSED: accused.id},
        facts={"crime": args.crime},
        place=accused.location_id,
    )
    return result(
        MortalResult.ACCUSATION_MADE,
        accused=accused.name,
        crime=crime,
        place=place.name if place is not None else "the settlement",
        trial=TRIAL_TEXT[case.trial or TrialKind.JUDGE],
    )


def specs() -> list[ToolSpec[MortalCall, Any]]:
    meta = ToolMeta(ActionKind.INFLUENCE, mortal_standard_action)
    return [
        ToolSpec(MortalToolId.PROPOSE_LAW, AgentKind.MORTAL, ProposeLawInput, meta, propose_law),
        ToolSpec(MortalToolId.ACCUSE, AgentKind.MORTAL, AccuseInput, meta, accuse),
    ]
