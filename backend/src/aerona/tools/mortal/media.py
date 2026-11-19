from typing import Annotated, Any

from pydantic import Field

from aerona.constants.schema import NAME_MAX_LENGTH
from aerona.constants.units import PERCENT
from aerona.core.grammar import spoken
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.interconnect import IncidentRow
from aerona.db.tables.media import MediaItemRow, MediaOutletRow, RecordMediumRow
from aerona.db.write_guard import held
from aerona.domain.enums.action import ActionKind
from aerona.domain.enums.agent import AgentKind
from aerona.domain.enums.entity import EntityType
from aerona.domain.enums.media import CensorMeasure, MediaItemKind, OutletFunding
from aerona.domain.enums.mind import ValueAxis
from aerona.domain.enums.modifier import IncidentRole
from aerona.engine.media.press import accuracy_for
from aerona.engine.numbers.book import towns_in
from aerona.prompts import MortalToolId
from aerona.prompts.tools.results import MortalResult, result
from aerona.tools.framework.call import MortalCall
from aerona.tools.framework.inputs import ToolInput
from aerona.tools.framework.spec import ToolMeta, ToolSpec, mortal_standard_action
from aerona.tools.framework.validation import fail
from aerona.tools.mortal.population import realm_ruled_by

OutletName = Annotated[str, Field(min_length=1, max_length=NAME_MAX_LENGTH)]
LEAN = 100
FIRST_STAFF = 2


class FoundOutletInput(ToolInput):
    name: OutletName
    medium_id: int | None = None
    stance: ValueAxis | None = None
    lean: int = Field(default=0, ge=-LEAN, le=LEAN)
    funding: OutletFunding = OutletFunding.SALES


class PublishItemInput(ToolInput):
    outlet_id: int
    kind: MediaItemKind
    subject_incident_id: int | None = None
    subject_node_id: int | None = None
    slant: int = Field(default=0, ge=-LEAN, le=LEAN)


class CensorOutletInput(ToolInput):
    outlet_id: int
    measure: CensorMeasure


async def found_outlet(call: MortalCall, args: FoundOutletInput) -> str:
    town = await call.session.get(EntityRow, call.me.location_id) if call.me.location_id is not None else None
    if town is None or town.entity_type is not EntityType.SETTLEMENT:
        fail(MortalResult.MEDIA_REFUSED, why="an outlet is founded in a town")
    if held(town.id):
        fail(MortalResult.MEDIA_REFUSED, why="a god holds this town as it is")
    medium = await call.session.get(RecordMediumRow, args.medium_id) if args.medium_id is not None else None
    if args.medium_id is not None and medium is None:
        fail(MortalResult.MEDIA_REFUSED, why="there is no such medium")
    outlet = MediaOutletRow(
        owner_node_id=call.me.id,
        seat_entity_id=town.id,
        medium_id=medium.id if medium is not None else None,
        name=args.name,
        stance=args.stance,
        lean=args.lean,
        funding=args.funding,
        staff=FIRST_STAFF,
        founded_epoch=call.epoch,
        locked=[],
    )
    call.session.add(outlet)
    await call.session.flush()
    call.target(town.id)
    await call.record("media.outlet_founded", roles={IncidentRole.ACTOR: call.me.id, IncidentRole.PLACE: town.id}, facts={"outlet": args.name}, place=town.id)
    return result(MortalResult.OUTLET_FOUNDED, outlet=args.name, town=town.name)


async def publish_item(call: MortalCall, args: PublishItemInput) -> str:
    outlet = await call.session.get(MediaOutletRow, args.outlet_id)
    if outlet is None or outlet.owner_node_id != call.me.id:
        fail(MortalResult.MEDIA_REFUSED, why="you own no such outlet")
    if held(outlet.seat_entity_id):
        fail(MortalResult.MEDIA_REFUSED, why="a god holds its town as it is")
    if args.subject_incident_id is not None and await call.session.get(IncidentRow, args.subject_incident_id) is None:
        fail(MortalResult.MEDIA_REFUSED, why="no such happening is on record")
    if args.subject_node_id is not None and await call.session.get(EntityRow, args.subject_node_id) is None:
        fail(MortalResult.MEDIA_REFUSED, why="there is no such subject")
    medium = await call.session.get(RecordMediumRow, outlet.medium_id) if outlet.medium_id is not None else None
    accuracy = accuracy_for(outlet, medium, args.slant) if args.subject_incident_id is not None else PERCENT // 2 - abs(args.slant) // 4
    call.session.add(
        MediaItemRow(
            outlet_id=outlet.id,
            owner_node_id=call.me.id,
            kind=args.kind,
            subject_incident_id=args.subject_incident_id,
            subject_node_id=args.subject_node_id,
            slant=args.slant,
            accuracy=max(0, accuracy),
            reach=outlet.reach,
            epoch=call.epoch,
            locked=[],
        )
    )
    call.target(outlet.seat_entity_id)
    await call.record(
        "media.item_published",
        roles={IncidentRole.ACTOR: call.me.id, IncidentRole.PLACE: outlet.seat_entity_id},
        facts={"kind": args.kind, "outlet": outlet.name},
    )
    return result(MortalResult.ITEM_PUBLISHED, kind=spoken(args.kind), outlet=outlet.name, reach=outlet.reach)


async def censor_outlet(call: MortalCall, args: CensorOutletInput) -> str:
    realm = await realm_ruled_by(call)
    outlet = await call.session.get(MediaOutletRow, args.outlet_id)
    if outlet is None or realm is None or outlet.seat_entity_id not in await towns_in(call.session, realm):
        fail(MortalResult.MEDIA_REFUSED, why="only the ruler of its realm acts on an outlet")
    if held(outlet.owner_node_id) or held(outlet.seat_entity_id):
        fail(MortalResult.MEDIA_REFUSED, why="a god holds it as it is")
    owner = outlet.owner_node_id
    if args.measure is CensorMeasure.CLOSE:
        await call.session.delete(outlet)
    elif args.measure is CensorMeasure.SEIZE:
        outlet.owner_node_id = realm
    else:
        outlet.censored = True
        if args.measure is CensorMeasure.LICENSE and "trust" not in (outlet.locked or []):
            outlet.trust = max(0, outlet.trust - PERCENT // 10)
    call.target(outlet.seat_entity_id)
    if args.measure is CensorMeasure.SEIZE:
        await call.record(
            "media.outlet_seized",
            roles={IncidentRole.ACTOR: realm, IncidentRole.TARGET: owner, IncidentRole.PLACE: outlet.seat_entity_id},
            facts={"outlet": outlet.name},
        )
    else:
        await call.record(
            "media.outlet_censored",
            roles={IncidentRole.TARGET: owner, IncidentRole.PLACE: outlet.seat_entity_id, IncidentRole.ACTOR: call.me.id},
            facts={"outlet": outlet.name, "measure": args.measure},
        )
    return result(MortalResult.OUTLET_CENSORED, outlet=outlet.name, measure=spoken(args.measure))


def specs() -> list[ToolSpec[MortalCall, Any]]:
    influence = ToolMeta(ActionKind.INFLUENCE, mortal_standard_action)
    return [
        ToolSpec(MortalToolId.FOUND_OUTLET, AgentKind.MORTAL, FoundOutletInput, influence, found_outlet),
        ToolSpec(MortalToolId.PUBLISH_ITEM, AgentKind.MORTAL, PublishItemInput, influence, publish_item),
        ToolSpec(MortalToolId.CENSOR_OUTLET, AgentKind.MORTAL, CensorOutletInput, ToolMeta(ActionKind.ENACT_LAW, mortal_standard_action), censor_outlet),
    ]
