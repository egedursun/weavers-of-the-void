from typing import Any

from aerona.db.tables.entities import EntityRow
from aerona.db.tables.intrigue import TrueNameRow
from aerona.domain.enums.action import ActionKind
from aerona.domain.enums.agent import AgentKind
from aerona.domain.enums.entity import EntityStatus, EntityType
from aerona.domain.enums.modifier import IncidentRole
from aerona.engine.primitives.queries import top_region
from aerona.engine.transform.bodies import lift_fallen
from aerona.prompts import MortalToolId
from aerona.prompts.tools.results import MortalResult, result
from aerona.tools.framework.call import MortalCall
from aerona.tools.framework.inputs import ToolInput
from aerona.tools.framework.spec import ToolMeta, ToolSpec, mortal_standard_action
from aerona.tools.framework.validation import fail


class SeekTrueNameInput(ToolInput):
    keeper_id: int
    bearer_id: int | None = None


async def same_land(call: MortalCall, keeper: EntityRow) -> bool:
    if keeper.location_id == call.me.location_id:
        return True
    mine, theirs = await top_region(call.session, call.me), await top_region(call.session, keeper)
    return mine is not None and theirs is not None and mine.id == theirs.id


async def seek_true_name(call: MortalCall, args: SeekTrueNameInput) -> str:
    bearer_id = args.bearer_id if args.bearer_id is not None else call.me.id
    row = await call.session.get(TrueNameRow, bearer_id)
    bearer = await call.session.get(EntityRow, bearer_id)
    keeper = await call.session.get(EntityRow, args.keeper_id)
    if row is None or bearer is None:
        fail(MortalResult.TRUE_NAME_REFUSED, why="that one has no true name to find")
    if call.me.id in row.known_by:
        fail(MortalResult.TRUE_NAME_REFUSED, why="you already know it")
    if keeper is None or keeper.status is not EntityStatus.CANON or not await same_land(call, keeper):
        fail(MortalResult.TRUE_NAME_REFUSED, why="no such keeper dwells in your land")
    if keeper.entity_type is not EntityType.BEAST and keeper.id not in row.known_by:
        fail(MortalResult.TRUE_NAME_REFUSED, why=f"{keeper.name} does not keep that name")
    if not call.tick.rng(f"seek_name.{call.me.id}.{bearer_id}.{call.tick.epoch}").chance(call.rules.transform.seek_name_chance):
        return result(MortalResult.TRUE_NAME_HIDDEN, keeper=keeper.name, bearer=bearer.name)
    row.known_by = sorted({*row.known_by, call.me.id})
    if bearer_id == call.me.id:
        await lift_fallen(call.tick, call.me.id, call.rules.transform.true_name_existence)
    await call.record("tools.mortal.true_name", roles={IncidentRole.LEARNER: call.me.id, IncidentRole.TEACHER: keeper.id})
    return result(MortalResult.TRUE_NAME_LEARNED, bearer=bearer.name, name=row.name)


def specs() -> list[ToolSpec[MortalCall, Any]]:
    meta = ToolMeta(ActionKind.INFLUENCE, mortal_standard_action)
    return [ToolSpec(MortalToolId.SEEK_TRUE_NAME, AgentKind.MORTAL, SeekTrueNameInput, meta, seek_true_name)]
