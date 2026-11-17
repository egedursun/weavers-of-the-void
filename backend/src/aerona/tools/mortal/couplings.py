from typing import Annotated, Any

from pydantic import Field
from sqlalchemy import select

from aerona.constants.schema import KEY_MAX_LENGTH
from aerona.core.errors import ValidationFailedError
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.military import ArmyOfficerRow, ArmyProfileRow
from aerona.db.tables.warfare import ArmyRow, SiegeRow, WarRow, WarSideRow
from aerona.db.write_guard import held
from aerona.domain.enums.action import ActionKind
from aerona.domain.enums.agent import AgentKind
from aerona.domain.enums.couplings import FieldAgreementKind
from aerona.domain.enums.military import ArmyRole
from aerona.domain.enums.modifier import IncidentRole
from aerona.domain.enums.polity import CLOSURES, LawKind, LegitimacyBasis, OfficeKind
from aerona.domain.enums.war import SiegeStatus, WarStatus
from aerona.engine.couplings.field import agree, commander_of, offer_terms
from aerona.engine.couplings.offices import office_count
from aerona.engine.polity.control import create_office as make_office
from aerona.engine.polity.laws import enact
from aerona.engine.primitives.stats import stat_or
from aerona.prompts import MortalToolId
from aerona.prompts.tools.results import MortalResult, result
from aerona.tools.framework.call import MortalCall
from aerona.tools.framework.inputs import ToolInput
from aerona.tools.framework.spec import ToolMeta, ToolSpec, mortal_standard_action
from aerona.tools.framework.validation import fail
from aerona.tools.mortal.ruler import throne_of


class ParleyInput(ToolInput):
    foe_id: int


class TermsInput(ToolInput):
    town_id: int


class ClosureInput(ToolInput):
    kind: LawKind


class OfficeInput(ToolInput):
    kind: OfficeKind
    title: Annotated[str, Field(max_length=KEY_MAX_LENGTH)] | None = None


async def commanded(call: MortalCall) -> int | None:
    led = await call.session.scalar(select(ArmyRow.entity_id).where(ArmyRow.commander_entity_id == call.me.id, ArmyRow.disbanded_epoch.is_(None)).limit(1))
    if led is not None:
        return led
    return await call.session.scalar(
        select(ArmyOfficerRow.army_entity_id)
        .where(ArmyOfficerRow.mortal_entity_id == call.me.id, ArmyOfficerRow.role == ArmyRole.COMMANDER, ArmyOfficerRow.until_epoch.is_(None))
        .limit(1)
    )


async def owner_of(call: MortalCall, army_id: int) -> int | None:
    army = await call.session.get(ArmyRow, army_id)
    return army.owner_entity_id if army is not None else None


async def war_between(call: MortalCall, first: int | None, second: int | None) -> WarRow | None:
    if first is None or second is None:
        return None
    mine = select(WarSideRow.war_id).where(WarSideRow.entity_id == first, WarSideRow.left_epoch.is_(None))
    theirs = select(WarSideRow.war_id).where(WarSideRow.entity_id == second, WarSideRow.left_epoch.is_(None))
    return await call.session.scalar(select(WarRow).where(WarRow.id.in_(mine), WarRow.id.in_(theirs), WarRow.status != WarStatus.ENDED).limit(1))


async def parley(call: MortalCall, args: ParleyInput) -> str:
    army_id = await commanded(call)
    if army_id is None:
        fail(MortalResult.PARLEY_REFUSED, why="you command no army")
    foe = await call.session.get(EntityRow, args.foe_id)
    mine, theirs = await call.session.get(ArmyProfileRow, army_id), await call.session.get(ArmyProfileRow, args.foe_id)
    if foe is None or mine is None or theirs is None or mine.region_entity_id is None or mine.region_entity_id != theirs.region_entity_id:
        fail(MortalResult.PARLEY_REFUSED, why="no enemy army stands in your land")
    war = await war_between(call, await owner_of(call, army_id), await owner_of(call, args.foe_id))
    other = await commander_of(call.tick, args.foe_id)
    if war is None or other is None or held(other.id):
        fail(MortalResult.PARLEY_REFUSED, why="that army is not at war with yours or has no commander to speak for it")
    table = call.rules.field_diplomacy
    margin = stat_or(call.me, "charisma", 0) - stat_or(other, "charisma", 0)
    truce = abs(margin) <= table.parley_margin or margin > 0
    term = call.tick.epoch + table.truce_epochs
    kind = FieldAgreementKind.TRUCE if truce else FieldAgreementKind.PARLEY
    await agree(
        call.tick, war.id, kind, commander=call.me.id, counterpart=other.id, place=mine.region_entity_id, term=term if truce else call.tick.epoch, honour=margin
    )
    await call.record(
        "tools.mortal.parley_truce" if truce else "tools.mortal.parley",
        roles={IncidentRole.ENVOY: call.me.id, IncidentRole.OPPONENT: other.id},
        facts={"war": war.event_entity_id, "margin": margin},
    )
    return result(MortalResult.PARLEY_TRUCE, foe=other.name, term=term) if truce else result(MortalResult.PARLEY_FAILED, foe=other.name)


async def offer(call: MortalCall, args: TermsInput) -> str:
    army_id = await commanded(call)
    owner = await owner_of(call, army_id) if army_id is not None else None
    siege = await call.session.scalar(
        select(SiegeRow)
        .where(SiegeRow.besieged_entity_id == args.town_id, SiegeRow.status == SiegeStatus.ONGOING, SiegeRow.besieger_entity_id == owner)
        .limit(1)
    )
    town = await call.session.get(EntityRow, args.town_id)
    if siege is None or town is None:
        fail(MortalResult.TERMS_IMPOSSIBLE, why="your army besieges no such town")
    if held(town.id):
        fail(MortalResult.TERMS_IMPOSSIBLE, why="a stronger hand holds that town")
    await call.record("tools.mortal.terms", roles={IncidentRole.ENVOY: call.me.id, IncidentRole.TARGET: town.id}, facts={"rounds": siege.rounds}, place=town.id)
    table = call.rules.field_diplomacy
    if siege.rounds < table.fraternise_rounds and siege.supplies > table.terms_supplies:
        return result(MortalResult.TERMS_REFUSED, town=town.name)
    await offer_terms(call.tick, siege)
    return result(MortalResult.TERMS_ACCEPTED, town=town.name)


async def declare_closure(call: MortalCall, args: ClosureInput) -> str:
    if args.kind not in CLOSURES:
        fail(MortalResult.LAW_TERMS_INVALID, reason="that is not a closure of waters or grounds.")
    realm = await throne_of(call)
    try:
        law = await enact(call.tick, realm.entity, args.kind, {}, by_id=call.me.id, basis=LegitimacyBasis.DECREE)
    except ValidationFailedError as error:
        fail(MortalResult.LAW_TERMS_INVALID, reason=str(error))
    call.target(law.id)
    await call.record(
        "tools.mortal.closure",
        roles={IncidentRole.ACTOR: call.me.id, IncidentRole.PRODUCT: law.id, IncidentRole.AUTHORITY: realm.entity.id},
        facts={"law": args.kind},
    )
    return result(MortalResult.CLOSURE_DECLARED, law=law.name, realm=realm.entity.name)


async def create_office(call: MortalCall, args: OfficeInput) -> str:
    realm = await throne_of(call)
    cost = call.rules.offices_made.cost
    if realm.profile.treasury < cost:
        fail(MortalResult.OFFICE_NOT_MADE, why="the treasury cannot pay for it")
    try:
        await make_office(call.tick, realm.entity.id, args.kind, title=args.title, powers=None, region_id=None, target_id=None, holder_id=None)
    except ValidationFailedError as error:
        fail(MortalResult.OFFICE_NOT_MADE, why=str(error).rstrip("."))
    realm.profile.treasury -= cost
    await call.record(
        "tools.mortal.office", roles={IncidentRole.ACTOR: call.me.id, IncidentRole.AUTHORITY: realm.entity.id}, facts={"office": args.kind, "cost": cost}
    )
    return result(MortalResult.OFFICE_MADE, realm=realm.entity.name, count=await office_count(call.tick, realm.entity.id))


def specs() -> list[ToolSpec[MortalCall, Any]]:
    meta = ToolMeta(ActionKind.INFLUENCE, mortal_standard_action)
    return [
        ToolSpec(MortalToolId.PARLEY, AgentKind.MORTAL, ParleyInput, meta, parley),
        ToolSpec(MortalToolId.OFFER_TERMS, AgentKind.MORTAL, TermsInput, meta, offer),
        ToolSpec(MortalToolId.DECLARE_CLOSURE, AgentKind.MORTAL, ClosureInput, meta, declare_closure),
        ToolSpec(MortalToolId.CREATE_OFFICE, AgentKind.MORTAL, OfficeInput, meta, create_office),
    ]
