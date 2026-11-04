from typing import Annotated, Any

from pydantic import Field
from sqlalchemy import select

from aerona.constants.tool_inputs import REASON_MAX, REASON_MIN
from aerona.constants.units import PERCENT
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.environment import PlaceEnvironmentRow, RegionEnvironmentRow
from aerona.db.tables.place import PlaceProfileRow
from aerona.domain.enums.action import ActionKind
from aerona.domain.enums.agent import AgentKind
from aerona.domain.enums.chronicle import ChronicleKind
from aerona.domain.enums.entity import EntityStatus, EntityType
from aerona.domain.enums.place import SecretKind, SecretOrigin
from aerona.engine.environment.places import NEXUS_FIELD, SACREDNESS_LOCK, place_kind_of, write_kind
from aerona.engine.environment.secrets import draft_for, hide
from aerona.engine.primitives.numbers import clamp_int
from aerona.prompts import SonToolId
from aerona.prompts.tools.results import CommonResult, SonResult, result
from aerona.tools.framework.call import SonCall
from aerona.tools.framework.inputs import ToolInput
from aerona.tools.framework.spec import ToolMeta, ToolSpec, son_standard_action
from aerona.tools.framework.validation import fail
from aerona.tools.son import lines
from aerona.tools.son.support import ensure_in_reach, require_essence

Reason = Annotated[str, Field(min_length=REASON_MIN, max_length=REASON_MAX)]


class HideSecretInput(ToolInput):
    place_id: int
    kind: SecretKind
    strength: Annotated[int, Field(ge=0, le=PERCENT)] = 50
    reason: Reason


class PlaceActInput(ToolInput):
    place_id: int
    reason: Reason


async def _place(call: SonCall, place_id: int) -> EntityRow:
    place = await call.session.get(EntityRow, place_id)
    if place is None or place.status is not EntityStatus.CANON:
        fail(CommonResult.NO_SUCH_ENTITY, id=place_id)
    if place.entity_type is not EntityType.PLACE:
        fail(SonResult.NOT_A_PLACE, name=place.name)
    await ensure_in_reach(call, place)
    return place


async def _profile(call: SonCall, place: EntityRow) -> PlaceProfileRow:
    profile = await call.session.get(PlaceProfileRow, place.id)
    if profile is None:
        profile = await write_kind(call.session, call.rules, place.id, await place_kind_of(call.session, place.id))
    return profile


async def hide_secret(call: SonCall, args: HideSecretInput) -> str:
    cost = call.rules.places.hide_secret_essence
    require_essence(call, cost)
    place = await _place(call, args.place_id)
    ground = await call.session.get(PlaceEnvironmentRow, place.id)
    region = await call.session.get(RegionEnvironmentRow, ground.region_entity_id) if ground is not None and ground.region_entity_id is not None else None
    draft = draft_for(args.kind, args.strength, call.rng(f"hide.{place.id}"), region)
    hide(call.tick, place.id, draft, SecretOrigin.SON, call.son.id)
    call.spend_essence(cost)
    call.target(place.id)
    await call.chronicle(
        ChronicleKind.WORLD, lines.HIDE_SECRET, entity_ids=[place.id], world_id=place.world_id, son=call.son.name, place=place.name, reason=args.reason
    )
    return result(SonResult.SECRET_HIDDEN, name=place.name)


async def sanctify_place(call: SonCall, args: PlaceActInput) -> str:
    cost = call.rules.places.sanctify_essence
    require_essence(call, cost)
    place = await _place(call, args.place_id)
    profile = await _profile(call, place)
    profile.sacredness = clamp_int(profile.sacredness + call.rules.places.sanctify_amount, 0, PERCENT)
    profile.locked = sorted({*profile.locked, SACREDNESS_LOCK})
    call.spend_essence(cost)
    call.target(place.id)
    await call.chronicle(
        ChronicleKind.WORLD, lines.SANCTIFY_PLACE, entity_ids=[place.id], world_id=place.world_id, son=call.son.name, place=place.name, reason=args.reason
    )
    return result(SonResult.PLACE_SANCTIFIED, name=place.name, sacredness=profile.sacredness)


async def raise_nexus(call: SonCall, args: PlaceActInput) -> str:
    cost = call.rules.places.raise_nexus_essence
    require_essence(call, cost)
    place = await _place(call, args.place_id)
    ground = await call.session.scalar(select(PlaceEnvironmentRow).where(PlaceEnvironmentRow.entity_id == place.id))
    if ground is None:
        fail(SonResult.NOT_A_PLACE, name=place.name)
    if ground.nexus:
        fail(SonResult.NEXUS_ALREADY, name=place.name)
    ground.nexus = True
    ground.locked = sorted({*ground.locked, NEXUS_FIELD})
    call.spend_essence(cost)
    call.target(place.id)
    await call.chronicle(
        ChronicleKind.COSMIC, lines.RAISE_NEXUS, entity_ids=[place.id], world_id=place.world_id, son=call.son.name, place=place.name, reason=args.reason
    )
    return result(SonResult.NEXUS_RAISED, name=place.name)


def specs() -> list[ToolSpec[SonCall, Any]]:
    son = AgentKind.SON
    return [
        ToolSpec(
            SonToolId.HIDE_SECRET,
            son,
            HideSecretInput,
            ToolMeta(ActionKind.HIDE_SECRET, son_standard_action, essence_cost=lambda rules: rules.places.hide_secret_essence),
            hide_secret,
        ),
        ToolSpec(
            SonToolId.SANCTIFY_PLACE,
            son,
            PlaceActInput,
            ToolMeta(ActionKind.SANCTIFY_PLACE, son_standard_action, essence_cost=lambda rules: rules.places.sanctify_essence),
            sanctify_place,
        ),
        ToolSpec(
            SonToolId.RAISE_NEXUS,
            son,
            PlaceActInput,
            ToolMeta(ActionKind.RAISE_NEXUS, son_standard_action, essence_cost=lambda rules: rules.places.raise_nexus_essence),
            raise_nexus,
        ),
    ]
