from typing import Any

from sqlalchemy import select

from aerona.db.tables.climes import CosmopolitanCultureRow, CosmopolitanMemberRow
from aerona.domain.enums.action import ActionKind
from aerona.domain.enums.agent import AgentKind
from aerona.domain.enums.chronicle import ChronicleKind
from aerona.engine.climes import control
from aerona.prompts import MortalToolId
from aerona.prompts.tools.results import MortalResult, result
from aerona.tools.framework.call import MortalCall
from aerona.tools.framework.inputs import ToolInput
from aerona.tools.framework.spec import ToolMeta, ToolSpec, mortal_standard_action
from aerona.tools.framework.validation import fail
from aerona.tools.mortal import lines


class JoinRoadFolkInput(ToolInput):
    culture_id: int


async def join_road_folk(call: MortalCall, args: JoinRoadFolkInput) -> str:
    culture = await call.session.get(CosmopolitanCultureRow, args.culture_id)
    if culture is None:
        fail(MortalResult.ROAD_FOLK_DECLINED, why="no culture of a road goes by that name")
    town = call.me.location_id
    if town is None:
        fail(MortalResult.ROAD_FOLK_DECLINED, why="you have no town to bring into it")
    already = await call.session.scalar(
        select(CosmopolitanMemberRow.culture_id).where(CosmopolitanMemberRow.culture_id == culture.id, CosmopolitanMemberRow.community_entity_id == town)
    )
    if already is not None:
        fail(MortalResult.ROAD_FOLK_DECLINED, why="your town belongs to it already")
    await control.set_record(
        call.tick, "cosmopolitan_member", {"culture_id": culture.id, "community_entity_id": town}, {"share": call.tick.rules.cosmopolitan.join_share}
    )
    call.target(town)
    await call.chronicle(ChronicleKind.CULTURE, lines.JOIN_ROAD_FOLK, entity_ids=[call.me.id, town], me=call.me.name, culture=culture.name)
    return result(MortalResult.ROAD_FOLK_JOINED, culture=culture.name)


def specs() -> list[ToolSpec[MortalCall, Any]]:
    mortal = AgentKind.MORTAL
    meta = ToolMeta(ActionKind.INFLUENCE, mortal_standard_action)
    return [ToolSpec(MortalToolId.JOIN_ROAD_FOLK, mortal, JoinRoadFolkInput, meta, join_road_folk)]
