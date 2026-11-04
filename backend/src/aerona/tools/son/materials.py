from typing import Annotated, Any

from pydantic import Field

from aerona.catalog.gates import Gate
from aerona.constants.units import PERCENT
from aerona.db.tables.celestial import WorldRow
from aerona.domain.enums.action import ActionKind
from aerona.domain.enums.agent import AgentKind
from aerona.domain.enums.chronicle import ChronicleKind
from aerona.domain.enums.economy import MaterialFamily
from aerona.domain.enums.material import MaterialKind
from aerona.domain.enums.society import KnowledgeBranch
from aerona.engine.economy.control_depth import Substance, create_material
from aerona.prompts import SonToolId
from aerona.prompts.tools.results import SonResult, result
from aerona.tools.framework.call import SonCall
from aerona.tools.framework.inputs import ToolInput
from aerona.tools.framework.spec import ToolMeta, ToolSpec, gate, son_standard_action
from aerona.tools.framework.validation import fail
from aerona.tools.son import lines
from aerona.tools.son.support import require_essence

NAME_MAX = 60
REASON_MIN = 3
REASON_MAX = 300
LEVEL_MAX = 20
Score = Annotated[int | None, Field(default=None, ge=0, le=PERCENT)]


class ForgeMaterialInput(ToolInput):
    world_id: int
    name: Annotated[str, Field(min_length=1, max_length=NAME_MAX)]
    family: MaterialFamily
    base_kind: MaterialKind | None = None
    hardness: Score = None
    toughness: Score = None
    weight: Score = None
    edge: Score = None
    conductivity: Score = None
    sanctity: Score = None
    corruption: Score = None
    rarity: Score = None
    base_value: Score = None
    decay: Score = None
    branch: KnowledgeBranch | None = None
    level: Annotated[int, Field(default=0, ge=0, le=LEVEL_MAX)] = 0
    place_id: int | None = None
    reason: Annotated[str, Field(min_length=REASON_MIN, max_length=REASON_MAX)]

    def values(self) -> dict[str, int]:
        keys = ("hardness", "toughness", "weight", "edge", "conductivity", "sanctity", "corruption", "rarity", "base_value", "decay")
        return {key: value for key in keys if (value := getattr(self, key)) is not None}


async def forge_material(call: SonCall, args: ForgeMaterialInput) -> str:
    world = await call.session.get(WorldRow, args.world_id)
    if world is None or (call.world_id != world.id and not await call.reachable_world(world.id)):
        fail(SonResult.NO_FORGE_WORLD, id=args.world_id)
    cost = call.rules.son_tools.forge_material_essence
    require_essence(call, cost)
    row = await create_material(
        call.tick,
        Substance(
            world_id=world.id,
            name=args.name,
            family=args.family,
            values=args.values(),
            base_kind=args.base_kind,
            branch=args.branch,
            level=args.level,
            place_id=args.place_id,
        ),
    )
    call.spend_essence(cost)
    if row.deposit_entity_id is not None:
        call.target(row.deposit_entity_id)
    await call.chronicle(
        ChronicleKind.RESOURCE,
        lines.FORGE_MATERIAL,
        entity_ids=[row.deposit_entity_id] if row.deposit_entity_id is not None else [],
        world_id=world.id,
        son=call.son.name,
        name=row.name or "",
        reason=args.reason,
    )
    return result(SonResult.MATERIAL_FORGED, name=row.name or "", id=row.id, vein=row.deposit_entity_id or 0)


def specs() -> list[ToolSpec[SonCall, Any]]:
    return [
        ToolSpec(
            SonToolId.FORGE_MATERIAL,
            AgentKind.SON,
            ForgeMaterialInput,
            ToolMeta(
                ActionKind.CREATE_ENTITY,
                son_standard_action,
                essence_cost=lambda rules: rules.son_tools.forge_material_essence,
                rarity_gate=gate(Gate.RARE_TOOLS),
            ),
            forge_material,
        )
    ]
