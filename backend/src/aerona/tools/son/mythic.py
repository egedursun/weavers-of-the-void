from typing import Annotated, Any

from pydantic import Field

from aerona.catalog.mythic import QUEST_PARTY_MAX
from aerona.constants.schema import NAME_MAX_LENGTH
from aerona.constants.tool_inputs import REASON_MAX, REASON_MIN
from aerona.db.tables.arcana import LawUpkeepRow
from aerona.db.tables.culture import LegendProfileRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.mythic import CosmicOfficeRow, GeasRow, ServitorRow
from aerona.domain.enums.action import ActionKind
from aerona.domain.enums.agent import AgentKind
from aerona.domain.enums.chronicle import ChronicleKind
from aerona.domain.enums.entity import EntityStatus, EntityType
from aerona.domain.enums.mind import ActKind
from aerona.domain.enums.mythic import CosmicOffice, GeasLayer, GeasMode, ServitorRank, ServitorRole
from aerona.domain.enums.society import NaturalLaw
from aerona.engine.arcana.enchantments import lay_enchantment as lay_law
from aerona.engine.mythic.geasa import lay_geas as lay
from aerona.engine.mythic.heroquests import begin_quest, fellows
from aerona.engine.mythic.servitors import make_servitor as make
from aerona.engine.mythic.servitors import wear
from aerona.prompts import SonToolId
from aerona.prompts.tools.results import SonResult, result
from aerona.tools.framework.call import SonCall
from aerona.tools.framework.inputs import ToolInput
from aerona.tools.framework.spec import ToolMeta, ToolSpec, son_standard_action
from aerona.tools.framework.validation import fail, require_canon, require_type
from aerona.tools.son import lines
from aerona.tools.son.support import ensure_in_reach, require_essence

Reason = Annotated[str, Field(min_length=REASON_MIN, max_length=REASON_MAX)]
STRENGTH_MAX = 100


class MakeServitorInput(ToolInput):
    name: Annotated[str, Field(min_length=1, max_length=NAME_MAX_LENGTH)]
    rank: ServitorRank
    role: ServitorRole
    post_id: int | None = None
    reason: Reason


class CommandServitorInput(ToolInput):
    servitor_id: int
    role: ServitorRole
    post_id: int | None = None
    reason: Reason


class ServitorInput(ToolInput):
    servitor_id: int
    reason: Reason


class LayGeasInput(ToolInput):
    bearer_id: int
    mode: GeasMode
    act: ActKind
    reason: Reason


class GeasInput(ToolInput):
    geas_id: int
    reason: Reason


class CallHeroquestInput(ToolInput):
    quester_id: int
    legend_id: int
    companion_ids: list[int] = Field(default_factory=list, max_length=QUEST_PARTY_MAX)
    reason: Reason


class OfficeInput(ToolInput):
    office: CosmicOffice
    reason: Reason


class EnchantInput(ToolInput):
    name: Annotated[str, Field(min_length=1, max_length=NAME_MAX_LENGTH)]
    effect: NaturalLaw
    region_id: int | None = None
    strength: Annotated[int, Field(ge=1, le=STRENGTH_MAX)]
    reason: Reason


class EndEnchantInput(ToolInput):
    law_id: int
    reason: Reason


async def mine(call: SonCall, servitor_id: int) -> ServitorRow:
    row = await call.session.get(ServitorRow, servitor_id)
    if row is None or row.god_node_id != call.son.id:
        fail(SonResult.SERVITOR_REFUSED, why="that servitor does not serve you")
    return row


async def make_servitor(call: SonCall, args: MakeServitorInput) -> str:
    cost = call.rules.servitors.make_cost
    require_essence(call, cost)
    post = await require_canon(call.session, args.post_id) if args.post_id is not None else None
    if post is not None:
        await ensure_in_reach(call, post)
    row = await make(
        call.tick, call.son.id, name=args.name, rank=args.rank, role=args.role, post_id=post.id if post else None, world_id=call.son.current_world_id
    )
    call.spend_essence(cost)
    call.target(row.spirit_entity_id)
    await call.chronicle(ChronicleKind.WORLD, lines.MAKE_SERVITOR, entity_ids=[row.spirit_entity_id], son=call.son.name, name=args.name, rank=args.rank.value)
    return result(SonResult.SERVITOR_MADE, name=args.name, id=row.spirit_entity_id)


async def command_servitor(call: SonCall, args: CommandServitorInput) -> str:
    row = await mine(call, args.servitor_id)
    post = await require_canon(call.session, args.post_id) if args.post_id is not None else None
    if "role" in row.locked or "post_entity_id" in row.locked:
        fail(SonResult.SERVITOR_REFUSED, why="a higher will holds its post")
    row.role, row.post_entity_id = args.role, post.id if post else None
    wear(call.rules, row)
    await call.session.flush()
    call.target(row.spirit_entity_id)
    return result(SonResult.SERVITOR_COMMANDED, role=args.role.value)


async def release_servitor(call: SonCall, args: ServitorInput) -> str:
    row = await mine(call, args.servitor_id)
    await call.session.delete(row)
    await call.session.flush()
    call.target(args.servitor_id)
    return result(SonResult.SERVITOR_RELEASED)


async def lay_geas(call: SonCall, args: LayGeasInput) -> str:
    bearer = require_type(
        await require_canon(call.session, args.bearer_id), frozenset({EntityType.MORTAL}), SonResult.GEAS_REFUSED, why="a geas is laid on a mortal"
    )
    await ensure_in_reach(call, bearer)
    row = await lay(call.tick, bearer, layer_node_id=call.son.id, layer=GeasLayer.GOD, mode=args.mode, act=args.act)
    call.target(bearer.id)
    await call.chronicle(ChronicleKind.WORLD, lines.LAY_GEAS, entity_ids=[bearer.id], son=call.son.name, bearer=bearer.name, reason=args.reason)
    return result(SonResult.GEAS_LAID, id=row.id, name=bearer.name)


async def lift_geas(call: SonCall, args: GeasInput) -> str:
    row = await call.session.get(GeasRow, args.geas_id)
    if row is None or row.layer_node_id != call.son.id:
        fail(SonResult.GEAS_REFUSED, why="you did not lay that geas")
    await call.session.delete(row)
    await call.session.flush()
    return result(SonResult.GEAS_LIFTED)


async def call_heroquest(call: SonCall, args: CallHeroquestInput) -> str:
    quester = require_type(
        await require_canon(call.session, args.quester_id), frozenset({EntityType.MORTAL}), SonResult.QUEST_REFUSED, why="only a mortal quests"
    )
    await ensure_in_reach(call, quester)
    legend = await call.session.get(LegendProfileRow, args.legend_id)
    if legend is None:
        fail(SonResult.QUEST_REFUSED, why="there is no such legend")
    party = await fellows(call.tick, quester, args.companion_ids)
    if isinstance(party, str):
        fail(SonResult.QUEST_REFUSED, why=party)
    row = await begin_quest(call.tick, quester, legend, party)
    call.target(quester.id)
    await call.chronicle(ChronicleKind.WORLD, lines.CALL_HEROQUEST, entity_ids=[quester.id], son=call.son.name, quester=quester.name, reason=args.reason)
    return result(SonResult.QUEST_CALLED, id=row.id, name=quester.name)


async def resign_office(call: SonCall, args: OfficeInput) -> str:
    row = await call.session.get(CosmicOfficeRow, args.office)
    if row is None or row.holder_node_id != call.son.id:
        fail(SonResult.OFFICE_REFUSED, why="you do not hold that office")
    if "holder_node_id" in row.locked:
        fail(SonResult.OFFICE_REFUSED, why="a higher will keeps you in it")
    row.holder_node_id, row.since_epoch = None, None
    await call.session.flush()
    return result(SonResult.OFFICE_RESIGNED, office=args.office.value)


async def lay_enchantment(call: SonCall, args: EnchantInput) -> str:
    region = await require_canon(call.session, args.region_id) if args.region_id is not None else None
    if region is not None:
        await ensure_in_reach(call, region)
    world = region.world_id if region is not None else call.son.current_world_id
    law = await lay_law(
        call.tick,
        call.son.id,
        name=args.name,
        effect=args.effect,
        world_id=world,
        region_id=region.id if region else None,
        strength=args.strength,
        vis_form=None,
    )
    call.target(law.law_entity_id)
    await call.chronicle(ChronicleKind.COSMIC_LAW, lines.LAY_ENCHANTMENT, entity_ids=[law.law_entity_id], son=call.son.name, name=args.name, reason=args.reason)
    return result(SonResult.ENCHANTMENT_LAID, id=law.law_entity_id, name=args.name)


async def end_enchantment(call: SonCall, args: EndEnchantInput) -> str:
    upkeep = await call.session.get(LawUpkeepRow, args.law_id)
    law = await call.session.get(EntityRow, args.law_id)
    if upkeep is None or law is None or upkeep.caster_node_id != call.son.id or law.status is not EntityStatus.CANON:
        fail(SonResult.ENCHANTMENT_REFUSED, why="it is not an enchantment you keep")
    law.status, law.end_epoch = EntityStatus.DESTROYED, call.epoch
    await call.session.flush()
    return result(SonResult.ENCHANTMENT_ENDED, name=law.name)


def specs() -> list[ToolSpec[SonCall, Any]]:
    son = AgentKind.SON
    meta = ToolMeta(ActionKind.INFLUENCE, son_standard_action)
    return [
        ToolSpec(SonToolId.MAKE_SERVITOR, son, MakeServitorInput, meta, make_servitor),
        ToolSpec(SonToolId.COMMAND_SERVITOR, son, CommandServitorInput, meta, command_servitor),
        ToolSpec(SonToolId.RELEASE_SERVITOR, son, ServitorInput, meta, release_servitor),
        ToolSpec(SonToolId.LAY_GEAS, son, LayGeasInput, meta, lay_geas),
        ToolSpec(SonToolId.LIFT_GEAS, son, GeasInput, meta, lift_geas),
        ToolSpec(SonToolId.CALL_HEROQUEST, son, CallHeroquestInput, meta, call_heroquest),
        ToolSpec(SonToolId.RESIGN_OFFICE, son, OfficeInput, meta, resign_office),
        ToolSpec(SonToolId.LAY_ENCHANTMENT, son, EnchantInput, meta, lay_enchantment),
        ToolSpec(SonToolId.END_ENCHANTMENT, son, EndEnchantInput, meta, end_enchantment),
    ]
