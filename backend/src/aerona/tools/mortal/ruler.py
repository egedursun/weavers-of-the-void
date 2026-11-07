from typing import Any

from sqlalchemy import select

from aerona.catalog.civics import OFFICE_GATES
from aerona.core.errors import ValidationFailedError
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.polity import OfficeRow
from aerona.domain.enums.action import ActionKind
from aerona.domain.enums.agent import AgentKind, TurnCounter
from aerona.domain.enums.chronicle import ChronicleKind
from aerona.domain.enums.entity import EntityStatus, EntityType
from aerona.domain.enums.polity import DecisionRule, LawKind, LegitimacyBasis, OfficeKind
from aerona.engine.lore.civics import realm_allows, unlearned
from aerona.engine.polity.book import Realm, RealmBook
from aerona.engine.polity.laws import LawBook, enact
from aerona.engine.polity.offices import appoint
from aerona.prompts import MortalToolId
from aerona.prompts.tools.results import MortalResult, result
from aerona.tools.framework.call import MortalCall
from aerona.tools.framework.spec import ToolMeta, ToolSpec, mortal_standard_action, no_cost
from aerona.tools.framework.validation import fail
from aerona.tools.mortal import lines
from aerona.tools.mortal.inputs import AppointOfficerInput, EnactLawInput, SetTaxInput
from aerona.tools.mortal.justice import bring_law, law_known

THRONES = (OfficeKind.RULER, OfficeKind.REGENT)
TAX_CAP = 50


async def throne_of(call: MortalCall) -> Realm:
    held = await call.session.scalar(
        select(OfficeRow.polity_entity_id).where(OfficeRow.holder_entity_id == call.me.id, OfficeRow.kind.in_(list(THRONES))).limit(1)
    )
    book = await RealmBook.load(call.session)
    realm = book.realms.get(held) if held is not None else None
    if realm is None:
        fail(MortalResult.NOT_A_RULER)
    return realm


async def enact_law(call: MortalCall, args: EnactLawInput) -> str:
    tools = call.rules.mortal_tools
    await call.within_limit(TurnCounter.LAWS_ENACTED, tools.enact_law_per_epoch, "mortal_tools.enact_law_per_epoch", MortalResult.LAW_LIMIT)
    realm = await throne_of(call)
    if realm.profile.decision_rule is not DecisionRule.AUTOCRATIC:
        text = await bring_law(call, realm, args.kind, args.params or {})
        await call.bump(TurnCounter.LAWS_ENACTED)
        return text
    await law_known(call, realm, args.kind)
    try:
        law = await enact(call.tick, realm.entity, args.kind, args.params or {}, by_id=call.me.id, basis=LegitimacyBasis.DECREE, name=args.name)
    except ValidationFailedError as error:
        fail(MortalResult.LAW_TERMS_INVALID, reason=str(error))
    await call.bump(TurnCounter.LAWS_ENACTED)
    call.target(law.id)
    await call.chronicle(
        ChronicleKind.CIVILIZATION, lines.LAW_LAID, entity_ids=[call.me.id, law.id, realm.entity.id], me=call.me.name, law=law.name, realm=realm.entity.name
    )
    return result(MortalResult.LAW_ENACTED, name=law.name, realm=realm.entity.name)


async def appoint_officer(call: MortalCall, args: AppointOfficerInput) -> str:
    tools = call.rules.mortal_tools
    await call.within_limit(
        TurnCounter.OFFICERS_APPOINTED, tools.appoint_officer_per_epoch, "mortal_tools.appoint_officer_per_epoch", MortalResult.OFFICER_LIMIT
    )
    realm = await throne_of(call)
    if args.office in THRONES:
        fail(MortalResult.OFFICE_NOT_APPOINTED)
    holder = await call.session.get(EntityRow, args.mortal_id) if args.mortal_id is not None else None
    if args.mortal_id is not None and (holder is None or holder.entity_type is not EntityType.MORTAL or holder.status is not EntityStatus.CANON):
        fail(MortalResult.OFFICE_NOT_APPOINTED)
    office = next((row for row in realm.offices if row.kind is args.office), None)
    needed = OFFICE_GATES.get(args.office)
    if office is None and not await realm_allows(call.session, realm, needed):
        fail(MortalResult.OFFICE_UNLEARNED, office=args.office.value.replace("_", " "), needs=unlearned(needed))
    if office is None:
        office = OfficeRow(polity_entity_id=realm.entity.id, kind=args.office, since_epoch=call.epoch, powers=[], locked=[])
        call.session.add(office)
        realm.offices.append(office)
        await call.session.flush()
    await appoint(call.tick, realm, office, holder, by_id=call.me.id, reason=f"appointed by {call.me.name}")
    await call.bump(TurnCounter.OFFICERS_APPOINTED)
    label = args.office.value.replace("_", " ")
    if holder is not None:
        call.target(holder.id)
    return result(MortalResult.OFFICER_APPOINTED, office=label, name=holder.name if holder is not None else "no one", realm=realm.entity.name)


async def set_tax(call: MortalCall, args: SetTaxInput) -> str:
    tools = call.rules.mortal_tools
    await call.within_limit(TurnCounter.TAXES_SET, tools.set_tax_per_epoch, "mortal_tools.set_tax_per_epoch", MortalResult.TAX_LIMIT)
    realm = await throne_of(call)
    laws = await LawBook.load(call.session)
    row = next(
        (
            laws.profiles[law_id]
            for law_id in laws.by_node.get(realm.entity.id, [])
            if law_id in laws.profiles and laws.profiles[law_id].kind is LawKind.TAX_RATE
        ),
        None,
    )
    rate = max(0, min(TAX_CAP, args.rate))
    if row is None:
        await enact(call.tick, realm.entity, LawKind.TAX_RATE, {"rate": rate}, by_id=call.me.id)
    elif "params" in row.locked:
        fail(MortalResult.TAX_HELD)
    else:
        row.params = {**row.params, "rate": rate}
    await call.bump(TurnCounter.TAXES_SET)
    return result(MortalResult.TAX_SET, rate=rate, realm=realm.entity.name)


def specs() -> list[ToolSpec[MortalCall, Any]]:
    mortal = AgentKind.MORTAL
    return [
        ToolSpec(MortalToolId.ENACT_LAW, mortal, EnactLawInput, ToolMeta(ActionKind.ENACT_LAW, mortal_standard_action), enact_law),
        ToolSpec(MortalToolId.APPOINT_OFFICER, mortal, AppointOfficerInput, ToolMeta(ActionKind.APPOINT_OFFICER, no_cost), appoint_officer),
        ToolSpec(MortalToolId.SET_TAX, mortal, SetTaxInput, ToolMeta(ActionKind.SET_TAX, no_cost), set_tax),
    ]
