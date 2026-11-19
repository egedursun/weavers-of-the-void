from typing import Annotated, Any

from pydantic import Field
from sqlalchemy import select

from aerona.constants.tool_inputs import REASON_MAX, REASON_MIN
from aerona.core.errors import ValidationFailedError
from aerona.core.grammar import spoken
from aerona.db.tables.folkways import BiasWeightRow, WitchHuntRow
from aerona.db.write_guard import held
from aerona.domain.enums.action import ActionKind
from aerona.domain.enums.agent import AgentKind
from aerona.domain.enums.chronicle import ChronicleKind
from aerona.domain.enums.entity import EntityType
from aerona.domain.enums.folkways import CharmPower, DecisionBias, ImpuritySource, MishapKind
from aerona.domain.enums.modifier import IncidentRole
from aerona.engine.folkways import control
from aerona.engine.folkways.biases import MIDDLE
from aerona.engine.primitives.queries import living_entity
from aerona.prompts import SonToolId
from aerona.prompts.tools.results import SonResult, result
from aerona.tools.framework.call import SonCall
from aerona.tools.framework.inputs import ToolInput
from aerona.tools.framework.spec import ToolMeta, ToolSpec, son_standard_action
from aerona.tools.framework.validation import fail
from aerona.tools.son.support import ensure_in_reach

Reason = Annotated[str, Field(min_length=REASON_MIN, max_length=REASON_MAX)]
SPAN = 100
MORTALS = frozenset({EntityType.MORTAL})
PEOPLES = frozenset({EntityType.PEOPLE})
TOWNS = frozenset({EntityType.SETTLEMENT})
ITEMS = frozenset({EntityType.ITEM})


class NudgeBiasInput(ToolInput):
    mortal_id: int
    bias: DecisionBias
    weight: int = Field(ge=0, le=SPAN)
    reason: Reason


class DeclareImpurityInput(ToolInput):
    people_id: int
    source: ImpuritySource
    reason: Reason


class BlessCharmInput(ToolInput):
    item_id: int
    power: CharmPower
    reason: Reason


class SendMisfortuneInput(ToolInput):
    town_id: int
    kind: MishapKind
    victim_id: int | None = None
    reason: Reason


class StirWitchHuntInput(ToolInput):
    town_id: int
    reason: Reason


def reason_of(error: ValidationFailedError) -> str:
    return str(error).rstrip(".")


async def reached(call: SonCall, node_id: int, kinds: frozenset[EntityType], refused: SonResult, missing: str) -> Any:
    found = await living_entity(call.session, node_id)
    if found is None or found.entity_type not in kinds:
        fail(refused, why=missing)
    await ensure_in_reach(call, found)
    if held(found.id):
        fail(refused, why="a stronger hand holds it")
    return found


async def nudge_bias(call: SonCall, args: NudgeBiasInput) -> str:
    mortal = await reached(call, args.mortal_id, MORTALS, SonResult.BIAS_REFUSED, "there is no such mortal")
    row = await call.session.get(BiasWeightRow, (mortal.id, args.bias))
    if row is not None and "weight" in row.locked:
        fail(SonResult.BIAS_REFUSED, why="a stronger hand holds that leaning")
    await control.set_bias(call.tick, mortal.id, args.bias, args.weight)
    call.target(mortal.id)
    told = spoken(args.bias)
    await call.record(
        "tools.son.nudge_bias",
        roles={IncidentRole.ACTOR: call.son.id, IncidentRole.SUBJECT: mortal.id},
        facts={"mortal": str(mortal.name), "bias": str(told), "reason": args.reason},
        kind=ChronicleKind.DIVINE_SIGN,
    )
    return result(SonResult.BIAS_NUDGED, mortal=mortal.name, bias=told, weight=args.weight, stronger=args.weight > MIDDLE)


async def declare_impurity(call: SonCall, args: DeclareImpurityInput) -> str:
    people = await reached(call, args.people_id, PEOPLES, SonResult.IMPURITY_REFUSED, "there is no such people")
    rules = call.tick.rules.purity
    await control.set_source(call.tick, people.id, args.source, (rules.weight_low + rules.weight_high) // 2, 1)
    call.target(people.id)
    told = spoken(args.source)
    await call.record(
        "tools.son.declare_impurity",
        roles={IncidentRole.ACTOR: call.son.id, IncidentRole.SUBJECT: people.id},
        facts={"people": people.name, "source": str(told), "reason": args.reason},
        kind=ChronicleKind.WORSHIP,
    )
    return result(SonResult.IMPURITY_DECLARED, people=people.name, source=told)


async def bless_charm(call: SonCall, args: BlessCharmInput) -> str:
    item = await reached(call, args.item_id, ITEMS, SonResult.CHARM_REFUSED, "there is no such item")
    row = await control.set_charm(call.tick, item.id, args.power, call.tick.rules.mishaps.charm_strength)
    if "real" not in row.locked:
        row.real = True
    call.target(item.id)
    told = spoken(args.power)
    await call.record(
        "tools.son.bless_charm",
        roles={IncidentRole.ACTOR: call.son.id, IncidentRole.SUBJECT: item.id},
        facts={"item": str(item.name), "power": str(told), "reason": args.reason},
        kind=ChronicleKind.DIVINE_SIGN,
    )
    return result(SonResult.CHARM_BLESSED, item=item.name, power=told)


async def send_misfortune(call: SonCall, args: SendMisfortuneInput) -> str:
    town = await reached(call, args.town_id, TOWNS, SonResult.MISFORTUNE_REFUSED, "there is no such town")
    if args.victim_id is not None:
        victim = await living_entity(call.session, args.victim_id)
        if victim is None or victim.location_id != town.id:
            fail(SonResult.MISFORTUNE_REFUSED, why="no such mortal lives in that town")
        if held(victim.id):
            fail(SonResult.MISFORTUNE_REFUSED, why="a stronger hand holds that life")
    row = await control.add_mishap(call.tick, town.id, args.kind, args.victim_id, call.son.id)
    call.target(town.id)
    told = spoken(args.kind)
    await call.record(
        "tools.son.send_misfortune",
        roles={IncidentRole.ACTOR: call.son.id, IncidentRole.SUBJECT: town.id},
        facts={"town": str(town.name), "kind": str(told), "reason": args.reason},
        kind=ChronicleKind.DIVINE_SIGN,
    )
    blamed = (row.attribution.value if row.attribution is not None else "chance").replace("_", " ")
    return result(SonResult.MISFORTUNE_SENT, town=town.name, kind=told, blamed=blamed)


async def stir_witch_hunt(call: SonCall, args: StirWitchHuntInput) -> str:
    town = await reached(call, args.town_id, TOWNS, SonResult.HUNT_REFUSED, "there is no such town")
    burning = await call.session.scalar(select(WitchHuntRow.id).where(WitchHuntRow.settlement_entity_id == town.id, WitchHuntRow.ended_epoch.is_(None)))
    if burning is not None:
        fail(SonResult.HUNT_REFUSED, why="a witch hunt already runs there")
    try:
        row = await control.start_hunt(call.tick, town.id, call.tick.rules.witchcraft.hunt_fervour)
    except ValidationFailedError as error:
        fail(SonResult.HUNT_REFUSED, why=reason_of(error))
    call.target(town.id)
    await call.record(
        "tools.son.stir_witch_hunt",
        roles={IncidentRole.ACTOR: call.son.id, IncidentRole.SUBJECT: town.id},
        facts={"town": str(town.name), "reason": args.reason},
        kind=ChronicleKind.WORSHIP,
    )
    return result(SonResult.HUNT_STIRRED, town=town.name, fervour=row.fervour)


def specs() -> list[ToolSpec[SonCall, Any]]:
    son = AgentKind.SON
    meta = ToolMeta(ActionKind.INFLUENCE, son_standard_action)
    return [
        ToolSpec(SonToolId.NUDGE_BIAS, son, NudgeBiasInput, meta, nudge_bias),
        ToolSpec(SonToolId.DECLARE_IMPURITY, son, DeclareImpurityInput, meta, declare_impurity),
        ToolSpec(SonToolId.BLESS_CHARM, son, BlessCharmInput, meta, bless_charm),
        ToolSpec(SonToolId.SEND_MISFORTUNE, son, SendMisfortuneInput, meta, send_misfortune),
        ToolSpec(SonToolId.STIR_WITCH_HUNT, son, StirWitchHuntInput, meta, stir_witch_hunt),
    ]
