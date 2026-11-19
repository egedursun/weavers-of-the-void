from typing import Any

from aerona.constants.units import PERCENT
from aerona.core.grammar import spoken
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.nature import FermentCultureRow
from aerona.db.write_guard import held
from aerona.domain.enums.action import ActionKind
from aerona.domain.enums.agent import AgentKind
from aerona.domain.enums.entity import EntityType
from aerona.domain.enums.modifier import IncidentRole
from aerona.domain.enums.nature import FermentKind
from aerona.engine.nature.microbes import live_cultures
from aerona.engine.primitives.numbers import clamp_int
from aerona.prompts import MortalToolId
from aerona.prompts.tools.results import MortalResult, result
from aerona.tools.framework.call import MortalCall
from aerona.tools.framework.inputs import ToolInput
from aerona.tools.framework.spec import ToolMeta, ToolSpec, mortal_standard_action
from aerona.tools.framework.validation import fail


class TendCultureInput(ToolInput):
    kind: FermentKind


async def tend_culture(call: MortalCall, args: TendCultureInput) -> str:
    me = call.me
    town = await call.session.get(EntityRow, me.location_id) if me.location_id is not None else None
    if town is None or town.entity_type is not EntityType.SETTLEMENT:
        fail(MortalResult.CULTURE_REFUSED, why="you must live in a town")
    if held(town.id):
        fail(MortalResult.CULTURE_REFUSED, why="a stronger hand holds your town")
    table = call.tick.rules.fermentation
    row = next((item for item in await live_cultures(call.session, [town.id]) if item.kind is args.kind), None)
    if row is None:
        row = FermentCultureRow(holder_entity_id=town.id, kind=args.kind, quality=table.start_quality, since_epoch=call.tick.epoch)
        row.locked = []
        call.session.add(row)
    elif "quality" not in row.locked:
        row.quality = clamp_int(row.quality + table.hand_tending, 0, PERCENT)
    await call.session.flush()
    call.target(town.id)
    kind = spoken(args.kind)
    await call.record(
        "tools.mortal.tend_culture",
        roles={IncidentRole.ACTOR: me.id, IncidentRole.PLACE: town.id},
        facts={"culture": args.kind, "quality": row.quality},
        place=town.id,
    )
    return result(MortalResult.CULTURE_TENDED, kind=kind, town=town.name, quality=row.quality)


def specs() -> list[ToolSpec[MortalCall, Any]]:
    mortal = AgentKind.MORTAL
    meta = ToolMeta(ActionKind.INFLUENCE, mortal_standard_action)
    return [ToolSpec(MortalToolId.TEND_CULTURE, mortal, TendCultureInput, meta, tend_culture)]
