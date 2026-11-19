from typing import Any

from aerona.core.grammar import spoken
from aerona.db.tables.folkways import CharmRow
from aerona.db.write_guard import held
from aerona.domain.enums.action import ActionKind
from aerona.domain.enums.agent import AgentKind
from aerona.domain.enums.chronicle import ChronicleKind
from aerona.domain.enums.entity import EntityType
from aerona.domain.enums.folkways import CharmPower, PurityState
from aerona.domain.enums.modifier import IncidentRole
from aerona.engine.body.customs import people_of
from aerona.engine.folkways.mishaps import make_charm
from aerona.engine.folkways.purity import PurityTally, methods_of, purify, purity_of
from aerona.engine.folkways.witchcraft import WitchTally, accuse
from aerona.engine.primitives.queries import living_entity
from aerona.engine.sacred.places import town_of
from aerona.prompts import MortalToolId
from aerona.prompts.tools.results import MortalResult, result
from aerona.tools.framework.call import MortalCall
from aerona.tools.framework.inputs import ToolInput
from aerona.tools.framework.spec import ToolMeta, ToolSpec, mortal_standard_action
from aerona.tools.framework.validation import fail


class PurifySelfInput(ToolInput):
    pass


class AccuseOfWitchcraftInput(ToolInput):
    accused_id: int


class MakeCharmInput(ToolInput):
    power: CharmPower


async def purify_self(call: MortalCall, args: PurifySelfInput) -> str:
    row = await purity_of(call.tick, call.me.id)
    if row.state is PurityState.PURE:
        fail(MortalResult.PURIFY_DECLINED, why="no impurity is on you")
    if "state" in row.locked:
        fail(MortalResult.PURIFY_DECLINED, why="a stronger hand holds your state")
    folk = await people_of(call.session, call.me)
    methods = await methods_of(call.tick, folk.id) if folk is not None else []
    if not methods:
        fail(MortalResult.PURIFY_DECLINED, why="your people know no way to purify")
    row.until_epoch = None
    tally = PurityTally()
    await purify(call.tick, call.me, row, methods, tally)
    call.target(call.me.id)
    await call.record("tools.mortal.purify_self", roles={IncidentRole.ACTOR: call.me.id}, kind=ChronicleKind.WORSHIP)
    return result(MortalResult.PURIFIED if tally.purified else MortalResult.STILL_IMPURE, state=spoken(row.state))


async def accuse_of_witchcraft(call: MortalCall, args: AccuseOfWitchcraftInput) -> str:
    town = await town_of(call.session, call.me)
    accused = await living_entity(call.session, args.accused_id)
    if town is None:
        fail(MortalResult.WITCH_ACCUSATION_DECLINED, why="you live in no town")
    if accused is None or accused.entity_type is not EntityType.MORTAL or accused.id == call.me.id or accused.location_id != call.me.location_id:
        fail(MortalResult.WITCH_ACCUSATION_DECLINED, why="no such neighbour lives beside you")
    if held(accused.id):
        fail(MortalResult.WITCH_ACCUSATION_DECLINED, why="a stronger hand holds them")
    row = await accuse(call.tick, town, call.me, WitchTally(), named=accused)
    if row is None:
        fail(MortalResult.WITCH_ACCUSATION_DECLINED, why="no court would hear it")
    call.target(accused.id)
    await call.record(
        "tools.mortal.accuse_of_witchcraft", roles={IncidentRole.ACCUSER: call.me.id, IncidentRole.ACCUSED: accused.id}, place=accused.location_id
    )
    return result(MortalResult.WITCH_ACCUSED, accused=accused.name)


async def make_a_charm(call: MortalCall, args: MakeCharmInput) -> str:
    row: CharmRow | None = await make_charm(call.tick, call.me.id, args.power)
    if row is None:
        fail(MortalResult.CHARM_DECLINED, why="you own no item that is not already a charm")
    item = await living_entity(call.session, row.item_entity_id)
    name = item.name if item is not None else "your item"
    call.target(call.me.id)
    await call.record("tools.mortal.make_charm", roles={IncidentRole.ACTOR: call.me.id}, facts={"item": str(name)}, kind=ChronicleKind.CULTURE)
    return result(MortalResult.CHARM_MADE, item=name, power=spoken(args.power), real=row.real)


def specs() -> list[ToolSpec[MortalCall, Any]]:
    mortal = AgentKind.MORTAL
    meta = ToolMeta(ActionKind.INFLUENCE, mortal_standard_action)
    return [
        ToolSpec(MortalToolId.PURIFY_SELF, mortal, PurifySelfInput, meta, purify_self),
        ToolSpec(MortalToolId.ACCUSE_OF_WITCHCRAFT, mortal, AccuseOfWitchcraftInput, meta, accuse_of_witchcraft),
        ToolSpec(MortalToolId.MAKE_CHARM, mortal, MakeCharmInput, meta, make_a_charm),
    ]
