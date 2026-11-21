from typing import Any

from pydantic import Field
from sqlalchemy import select

from aerona.db.tables.entities import EntityRow
from aerona.db.tables.polity import ClaimRow
from aerona.db.tables.restoration import RestorationRow
from aerona.db.write_guard import held
from aerona.domain.enums.action import ActionKind
from aerona.domain.enums.agent import AgentKind
from aerona.domain.enums.entity import EntityStatus, EntityType
from aerona.domain.enums.restoration import OPEN_STAGES, RestorationBasis, RestorationStage
from aerona.engine.restoration.rise import RestorationTally, old_lands, raise_movement, resisted, restore
from aerona.prompts import MortalToolId
from aerona.prompts.tools.results import MortalResult, result
from aerona.tools.framework.call import MortalCall
from aerona.tools.framework.inputs import ToolInput
from aerona.tools.framework.spec import ToolMeta, ToolSpec, mortal_standard_action
from aerona.tools.framework.validation import fail

BASES_MAX = 5
TERRITORIES_MAX = 24


class RaiseRestorationInput(ToolInput):
    fallen_polity_id: int
    bases: list[RestorationBasis] = Field(min_length=1, max_length=BASES_MAX)
    territory_ids: list[int] = Field(default_factory=list, max_length=TERRITORIES_MAX)


class RestorePolityInput(ToolInput):
    restoration_id: int


async def fallen_realm(call: MortalCall, fallen_id: int) -> EntityRow:
    fallen = await call.session.get(EntityRow, fallen_id)
    if fallen is None or fallen.entity_type is not EntityType.POLITY or fallen.status is EntityStatus.CANON:
        fail(MortalResult.RESTORATION_REFUSED, why="only a realm that has fallen can be raised again")
    if held(fallen.id):
        fail(MortalResult.RESTORATION_REFUSED, why="a god holds it as it is")
    return fallen


async def raise_restoration_tool(call: MortalCall, args: RaiseRestorationInput) -> str:
    fallen = await fallen_realm(call, args.fallen_polity_id)
    lands = await old_lands(call.tick, fallen.id)
    claim = await call.session.scalar(select(ClaimRow.id).where(ClaimRow.claimant_entity_id == call.me.id, ClaimRow.polity_entity_id == fallen.id).limit(1))
    if call.me.location_id not in lands and claim is None:
        fail(MortalResult.RESTORATION_REFUSED, why="you raise a fallen realm from its old lands or by your own claim to it")
    strangers = [node for node in args.territory_ids if node not in lands]
    if strangers:
        fail(MortalResult.RESTORATION_REFUSED, why="a restoration seeks only the old lands of the fallen realm")
    row = await raise_movement(call.tick, fallen, claimant=call.me.id, bases=list(args.bases), territories=list(args.territory_ids), tally=RestorationTally())
    call.target(fallen.id)
    return result(MortalResult.RESTORATION_RAISED, realm=fallen.name, restoration=row.id, memory=row.memory, lands=len(row.territories or []))


async def restore_polity_tool(call: MortalCall, args: RestorePolityInput) -> str:
    row = await call.session.get(RestorationRow, args.restoration_id)
    if row is None or row.stage not in OPEN_STAGES:
        fail(MortalResult.RESTORATION_REFUSED, why="there is no such restoration still under way")
    if row.claimant_node_id != call.me.id:
        fail(MortalResult.RESTORATION_REFUSED, why="only the one who leads the restoration can raise the realm")
    await fallen_realm(call, row.fallen_polity_id)
    if row.memory < call.tick.rules.restoration.rising_memory:
        fail(MortalResult.RESTORATION_REFUSED, why=f"its memory of {row.memory} is too weak to rise; it needs {call.tick.rules.restoration.rising_memory}")
    if await resisted(call.tick, row):
        fail(MortalResult.RESTORATION_REFUSED, why="the realms that hold its old lands are too steady to let it rise")
    row.stage = RestorationStage.RISING
    realm = await restore(call.tick, row, RestorationTally())
    if realm is None:
        fail(MortalResult.RESTORATION_REFUSED, why="none of its old lands could be taken back")
    call.target(realm.id)
    return result(MortalResult.POLITY_RESTORED, realm=realm.name)


def specs() -> list[ToolSpec[MortalCall, Any]]:
    act = ToolMeta(ActionKind.INFLUENCE, mortal_standard_action)
    return [
        ToolSpec(MortalToolId.RAISE_RESTORATION, AgentKind.MORTAL, RaiseRestorationInput, act, raise_restoration_tool),
        ToolSpec(MortalToolId.RESTORE_POLITY, AgentKind.MORTAL, RestorePolityInput, act, restore_polity_tool),
    ]
