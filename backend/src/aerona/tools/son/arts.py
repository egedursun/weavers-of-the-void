from typing import Annotated, Any

from pydantic import Field

from aerona.constants.tool_inputs import REASON_MAX, REASON_MIN
from aerona.core.errors import ValidationFailedError
from aerona.db.tables.arts import ClubRow, ForgeryRow
from aerona.db.tables.constructs import ConstructRow
from aerona.db.tables.entities import EntityRow
from aerona.db.write_guard import held
from aerona.domain.enums.action import ActionKind
from aerona.domain.enums.agent import AgentKind
from aerona.domain.enums.arts import CanonPath
from aerona.domain.enums.chronicle import ChronicleKind
from aerona.domain.enums.constructs import CommandToken, OrderCondition, OrderKind
from aerona.domain.enums.culture import MagicSource
from aerona.domain.enums.entity import EntityType
from aerona.domain.enums.material import MaterialKind
from aerona.domain.enums.modifier import IncidentRole
from aerona.domain.enums.records import StepAction
from aerona.engine.arts import control as arts
from aerona.engine.constructs import control as constructs
from aerona.engine.primitives.queries import living_entity
from aerona.engine.recording.record import StepDraft
from aerona.prompts import SonToolId
from aerona.prompts.tools.results import SonResult, result
from aerona.tools.framework.call import SonCall
from aerona.tools.framework.inputs import ToolInput
from aerona.tools.framework.spec import ToolMeta, ToolSpec, son_standard_action
from aerona.tools.framework.validation import fail
from aerona.tools.son.support import ensure_in_reach

Reason = Annotated[str, Field(min_length=REASON_MIN, max_length=REASON_MAX)]
MORTALS = frozenset({EntityType.MORTAL})
TOWNS = frozenset({EntityType.SETTLEMENT})
PEOPLES = frozenset({EntityType.PEOPLE})
ARTWORKS = frozenset({EntityType.ARTWORK})
BEASTS = frozenset({EntityType.BEAST})
FACTIONS = frozenset({EntityType.FACTION})
FIRST = 1


class BuildConstructInput(ToolInput):
    maker_id: int
    material: MaterialKind | None = None
    source: MagicSource | None = None
    reason: Reason


class OrderConstructInput(ToolInput):
    construct_id: int
    kind: OrderKind
    target_id: int | None = None
    reason: Reason


class SeizeConstructInput(ToolInput):
    construct_id: int
    reason: Reason


class ExposeForgeryInput(ToolInput):
    forgery_id: int
    reason: Reason


class CanoniseWorkInput(ToolInput):
    people_id: int
    artwork_id: int
    reason: Reason


class InspireMovementInput(ToolInput):
    town_id: int
    reason: Reason


class RigMatchInput(ToolInput):
    home_id: int
    away_id: int
    winner_id: int
    reason: Reason


class SetBeastBountyInput(ToolInput):
    town_id: int
    beast_id: int
    reason: Reason


class MarkBirthInput(ToolInput):
    mortal_id: int
    dreaded: bool
    reason: Reason


async def reached(call: SonCall, entity_id: int | None, kinds: frozenset[EntityType], refused: SonResult, why: str) -> EntityRow:
    entity = await living_entity(call.session, entity_id)
    if entity is None or entity.entity_type not in kinds:
        fail(refused, why=why)
    await ensure_in_reach(call, entity)
    if held(entity.id):
        fail(refused, why="a stronger hand holds it")
    return entity


def reason_of(error: ValidationFailedError) -> str:
    return str(error).rstrip(".")


async def build_construct(call: SonCall, args: BuildConstructInput) -> str:
    maker = await reached(call, args.maker_id, MORTALS, SonResult.CONSTRUCT_REFUSED, "there is no such mortal")
    try:
        row = await constructs.build_construct(call.tick, maker.id, material=args.material, source=args.source, token=None, name=None)
    except ValidationFailedError as error:
        fail(SonResult.CONSTRUCT_REFUSED, why=reason_of(error))
    body = await call.session.get(EntityRow, row.entity_id)
    name = body.name if body is not None else "the construct"
    call.target(row.entity_id)
    await call.record(
        "tools.son.build_construct",
        roles={IncidentRole.ACTOR: call.son.id, IncidentRole.SUBJECT: [maker.id, row.entity_id]},
        facts={"maker_detail": str(maker.name), "name": str(name), "reason": args.reason},
        kind=ChronicleKind.CREATION,
    )
    return result(SonResult.CONSTRUCT_BUILT, maker=maker.name, name=name, material=row.material.value, source=row.power_source.value)


async def construct_of(call: SonCall, construct_id: int, refused: SonResult) -> EntityRow:
    body = await reached(call, construct_id, BEASTS, refused, "there is no such construct")
    if await call.session.get(ConstructRow, body.id) is None:
        fail(refused, why=f"{body.name} is a beast, not a construct")
    return body


async def order_construct(call: SonCall, args: OrderConstructInput) -> str:
    body = await construct_of(call, args.construct_id, SonResult.CONSTRUCT_ORDER_REFUSED)
    rules = await constructs.rules_of(call.tick, body.id)
    if rules is None:
        fail(SonResult.CONSTRUCT_ORDER_REFUSED, why="it carries no orders to add to")
    target = await living_entity(call.session, args.target_id) if args.target_id is not None else None
    if args.target_id is not None and target is None:
        fail(SonResult.CONSTRUCT_ORDER_REFUSED, why="there is no such target")
    try:
        await constructs.give_order(call.tick, rules.id, args.kind, target_id=args.target_id, priority=FIRST, condition=OrderCondition.ALWAYS, until_epoch=None)
    except ValidationFailedError as error:
        fail(SonResult.CONSTRUCT_ORDER_REFUSED, why=reason_of(error))
    aim = target.name if target is not None else "no one in particular"
    call.target(body.id)
    await call.record(
        "tools.son.order_construct",
        roles={IncidentRole.ACTOR: call.son.id, IncidentRole.SUBJECT: body.id},
        facts={"order": args.kind, "reason": args.reason},
        kind=ChronicleKind.CREATION,
    )
    return result(SonResult.CONSTRUCT_ORDERED, name=body.name, order=args.kind.value.replace("_", " "), target=aim)


async def seize_construct(call: SonCall, args: SeizeConstructInput) -> str:
    body = await construct_of(call, args.construct_id, SonResult.CONSTRUCT_SEIZE_REFUSED)
    rules = await constructs.rules_of(call.tick, body.id)
    if rules is None:
        fail(SonResult.CONSTRUCT_SEIZE_REFUSED, why="it answers no token at all")
    await constructs.edit_record(call.tick, "instruction_set", rules.id, {"command_token": CommandToken.WORD, "holder_node_id": call.son.id}, [])
    call.target(body.id)
    await call.record(
        "tools.son.seize_construct",
        roles={IncidentRole.ACTOR: call.son.id, IncidentRole.SUBJECT: body.id},
        facts={"reason": args.reason},
        kind=ChronicleKind.CREATION,
    )
    return result(SonResult.CONSTRUCT_SEIZED, name=body.name)


async def expose_forgery(call: SonCall, args: ExposeForgeryInput) -> str:
    row = await call.session.get(ForgeryRow, args.forgery_id)
    if row is None:
        fail(SonResult.FORGERY_EXPOSE_REFUSED, why="there is no such forgery")
    item = await reached(call, row.item_entity_id, frozenset(EntityType), SonResult.FORGERY_EXPOSE_REFUSED, "the forged thing is gone")
    try:
        await arts.expose_forgery(call.tick, row.id, None)
    except ValidationFailedError as error:
        fail(SonResult.FORGERY_EXPOSE_REFUSED, why=reason_of(error))
    call.target(item.id)
    await call.record(
        "tools.son.expose_forgery",
        roles={IncidentRole.ACTOR: call.son.id, IncidentRole.SUBJECT: item.id},
        facts={"item": str(item.name), "reason": args.reason},
        kind=ChronicleKind.CULTURE,
        steps=(StepDraft(StepAction.FIND_EVIDENCE, actor=call.son.id, target=item.id, record_table=ForgeryRow.__tablename__, record_key=str(row.id)),),
    )
    return result(SonResult.FORGERY_EXPOSED, item=item.name)


async def canonise_work(call: SonCall, args: CanoniseWorkInput) -> str:
    people = await reached(call, args.people_id, PEOPLES, SonResult.CANON_REFUSED, "there is no such people")
    work = await reached(call, args.artwork_id, ARTWORKS, SonResult.CANON_REFUSED, "there is no such work")
    try:
        await arts.canonise(call.tick, people.id, work.id, CanonPath.INSTITUTION)
    except ValidationFailedError as error:
        fail(SonResult.CANON_REFUSED, why=reason_of(error))
    call.target(work.id)
    await call.record(
        "tools.son.canonise_work",
        roles={IncidentRole.ACTOR: call.son.id, IncidentRole.SUBJECT: [people.id, work.id]},
        facts={"work": str(work.name), "people": people.name, "reason": args.reason},
        kind=ChronicleKind.CULTURE,
    )
    return result(SonResult.CANONISED, work=work.name, people=people.name)


async def inspire_movement(call: SonCall, args: InspireMovementInput) -> str:
    town = await reached(call, args.town_id, TOWNS, SonResult.MOVEMENT_REFUSED, "there is no such town")
    try:
        row = await arts.start_movement(call.tick, town.id)
    except ValidationFailedError as error:
        fail(SonResult.MOVEMENT_REFUSED, why=reason_of(error))
    faction = await call.session.get(EntityRow, row.faction_entity_id)
    name = faction.name if faction is not None else "a new school"
    call.target(row.faction_entity_id)
    await call.record(
        "tools.son.inspire_movement",
        roles={IncidentRole.ACTOR: call.son.id, IncidentRole.SUBJECT: [town.id, row.faction_entity_id]},
        facts={"town": str(town.name), "name": str(name), "reason": args.reason},
        kind=ChronicleKind.CULTURE,
    )
    return result(SonResult.MOVEMENT_INSPIRED, town=town.name, name=name)


async def club_of(call: SonCall, club_id: int) -> EntityRow:
    faction = await reached(call, club_id, FACTIONS, SonResult.MATCH_REFUSED, "there is no such club")
    if await call.session.get(ClubRow, faction.id) is None:
        fail(SonResult.MATCH_REFUSED, why=f"{faction.name} is not a club")
    return faction


async def rig_match(call: SonCall, args: RigMatchInput) -> str:
    home, away = await club_of(call, args.home_id), await club_of(call, args.away_id)
    if args.winner_id not in (home.id, away.id):
        fail(SonResult.MATCH_REFUSED, why="the winner must be one of the two clubs")
    try:
        await arts.stage_match(call.tick, home.id, away.id, args.winner_id)
    except ValidationFailedError as error:
        fail(SonResult.MATCH_REFUSED, why=reason_of(error))
    winner = home if args.winner_id == home.id else away
    call.target(winner.id)
    await call.record(
        "tools.son.rig_match",
        roles={IncidentRole.ACTOR: call.son.id, IncidentRole.CO_ACTOR: winner.id, IncidentRole.SUBJECT: [home.id, away.id]},
        facts={"reason": args.reason},
        kind=ChronicleKind.CULTURE,
    )
    return result(SonResult.MATCH_RIGGED, home=home.name, away=away.name, winner=winner.name)


async def set_beast_bounty(call: SonCall, args: SetBeastBountyInput) -> str:
    town = await reached(call, args.town_id, TOWNS, SonResult.BEAST_BOUNTY_REFUSED, "there is no such town")
    beast = await reached(call, args.beast_id, BEASTS, SonResult.BEAST_BOUNTY_REFUSED, "there is no such beast")
    try:
        row = await constructs.post_contract(call.tick, town.id, beast.id, call.tick.rules.monster_contracts.bounty)
    except ValidationFailedError as error:
        fail(SonResult.BEAST_BOUNTY_REFUSED, why=reason_of(error))
    call.target(beast.id)
    await call.record(
        "tools.son.set_beast_bounty",
        roles={IncidentRole.ACTOR: call.son.id, IncidentRole.SUBJECT: [town.id, beast.id]},
        facts={"town": str(town.name), "beast": str(beast.name), "reason": args.reason},
        kind=ChronicleKind.WORLD,
    )
    return result(SonResult.BEAST_BOUNTY_SET, town=town.name, beast=beast.name, bounty=row.bounty)


async def mark_birth(call: SonCall, args: MarkBirthInput) -> str:
    mortal = await reached(call, args.mortal_id, MORTALS, SonResult.BIRTH_MARK_REFUSED, "there is no such mortal")
    try:
        row = await constructs.cast_sign(call.tick, mortal.id)
        await constructs.edit_record(call.tick, "birth_sign", mortal.id, {"dreaded": args.dreaded}, [])
    except ValidationFailedError as error:
        fail(SonResult.BIRTH_MARK_REFUSED, why=reason_of(error))
    sign = "a dreaded sign" if args.dreaded else "a kindly sign"
    call.target(mortal.id)
    await call.record(
        "tools.son.mark_birth",
        roles={IncidentRole.ACTOR: call.son.id, IncidentRole.SUBJECT: mortal.id},
        facts={"mortal": str(mortal.name), "sign": str(sign), "reason": args.reason},
        kind=ChronicleKind.FATE,
    )
    return result(SonResult.BIRTH_MARKED, mortal=mortal.name, sign=sign, influence=row.influence.value)


def specs() -> list[ToolSpec[SonCall, Any]]:
    son = AgentKind.SON
    meta = ToolMeta(ActionKind.INFLUENCE, son_standard_action)
    return [
        ToolSpec(SonToolId.BUILD_CONSTRUCT, son, BuildConstructInput, meta, build_construct),
        ToolSpec(SonToolId.ORDER_CONSTRUCT, son, OrderConstructInput, meta, order_construct),
        ToolSpec(SonToolId.SEIZE_CONSTRUCT, son, SeizeConstructInput, meta, seize_construct),
        ToolSpec(SonToolId.EXPOSE_FORGERY, son, ExposeForgeryInput, meta, expose_forgery),
        ToolSpec(SonToolId.CANONISE_WORK, son, CanoniseWorkInput, meta, canonise_work),
        ToolSpec(SonToolId.INSPIRE_MOVEMENT, son, InspireMovementInput, meta, inspire_movement),
        ToolSpec(SonToolId.RIG_MATCH, son, RigMatchInput, meta, rig_match),
        ToolSpec(SonToolId.SET_BEAST_BOUNTY, son, SetBeastBountyInput, meta, set_beast_bounty),
        ToolSpec(SonToolId.MARK_BIRTH, son, MarkBirthInput, meta, mark_birth),
    ]
