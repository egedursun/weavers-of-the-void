from typing import Annotated, Any

from pydantic import Field

from aerona.constants.tool_inputs import REASON_MAX, REASON_MIN
from aerona.db.tables.settlement import DESIGN_PARAMETERS, DistrictDesignRow
from aerona.domain.enums.action import ActionKind
from aerona.domain.enums.agent import AgentKind
from aerona.domain.enums.chronicle import ChronicleKind
from aerona.domain.enums.entity import EntityType
from aerona.domain.enums.settlement import BuildMaterial, DistrictKind
from aerona.engine.settlement import control
from aerona.prompts import SonToolId
from aerona.prompts.tools.results import SonResult, result
from aerona.tools.framework.call import SonCall
from aerona.tools.framework.inputs import ToolInput
from aerona.tools.framework.spec import ToolMeta, ToolSpec
from aerona.tools.framework.validation import fail, require_canon, require_type
from aerona.tools.son import lines
from aerona.tools.son.support import ensure_in_reach, require_essence

NAME_MAX = 80


class RaiseDistrictInput(ToolInput):
    settlement_id: int
    kind: DistrictKind | None = None
    design_id: int | None = None
    material: BuildMaterial = BuildMaterial.STONE
    reason: Annotated[str, Field(min_length=REASON_MIN, max_length=REASON_MAX)]


class DesignDistrictInput(ToolInput):
    name: Annotated[str, Field(min_length=1, max_length=NAME_MAX)]
    base_kind: DistrictKind
    housing: int | None = Field(default=None, ge=0)
    food_store: int | None = Field(default=None, ge=0)
    goods_store: int | None = Field(default=None, ge=0)
    harbour: int | None = Field(default=None, ge=0)
    order: int | None = Field(default=None, ge=0, le=300)
    sanitation: int | None = Field(default=None, ge=-100, le=300)
    piety_floor: int | None = Field(default=None, ge=0, le=300)
    admin_pct: int | None = Field(default=None, ge=0, le=300)
    policing: int | None = Field(default=None, ge=0, le=300)
    investment_pct: int | None = Field(default=None, ge=0, le=300)
    tension_relief_pct: int | None = Field(default=None, ge=0, le=300)
    reason: Annotated[str, Field(min_length=REASON_MIN, max_length=REASON_MAX)]


async def raise_district(call: SonCall, args: RaiseDistrictInput) -> str:
    tools = call.rules.son_tools
    town = require_type(await require_canon(call.session, args.settlement_id), {EntityType.SETTLEMENT}, SonResult.DISTRICT_NOT_SETTLEMENT)
    await ensure_in_reach(call, town)
    if args.kind is None and args.design_id is None:
        fail(SonResult.DISTRICT_NO_KIND)
    require_essence(call, tools.raise_district_essence)
    district = await control.build_district(call.tick, town.id, args.kind, material=args.material, son_id=call.son.id, design_id=args.design_id)
    call.spend_essence(tools.raise_district_essence)
    call.target(town.id)
    label = district.kind.value.replace("_", " ")
    await call.chronicle(
        ChronicleKind.CIVILIZATION, lines.RAISE_DISTRICT, entity_ids=[town.id], son=call.son.name, district=label, town=town.name, reason=args.reason
    )
    return result(SonResult.DISTRICT_RAISED, district=label, name=town.name, level=district.level)


async def design_district(call: SonCall, args: DesignDistrictInput) -> str:
    tools = call.rules.son_tools
    if call.world_id is None:
        fail(SonResult.DISTRICT_NO_WORLD)
    require_essence(call, tools.design_district_essence)
    values = {key: value for key, value in args.model_dump().items() if key in DESIGN_PARAMETERS and value is not None}
    design: DistrictDesignRow = await control.create_design(
        call.tick, call.world_id, args.name, args.base_kind, values, description=args.reason, son_id=call.son.id
    )
    call.spend_essence(tools.design_district_essence)
    await call.chronicle(ChronicleKind.CIVILIZATION, lines.DESIGN_DISTRICT, son=call.son.name, design=design.name, base=args.base_kind.value.replace("_", " "))
    return result(SonResult.DISTRICT_DESIGNED, id=design.id, name=design.name)


def specs() -> list[ToolSpec[SonCall, Any]]:
    son = AgentKind.SON
    return [
        ToolSpec(
            SonToolId.RAISE_DISTRICT,
            son,
            RaiseDistrictInput,
            ToolMeta(ActionKind.BUILD, lambda rules: rules.son_tools.raise_district_ap, essence_cost=lambda rules: rules.son_tools.raise_district_essence),
            raise_district,
        ),
        ToolSpec(
            SonToolId.DESIGN_DISTRICT,
            son,
            DesignDistrictInput,
            ToolMeta(ActionKind.BUILD, lambda rules: rules.son_tools.design_district_ap, essence_cost=lambda rules: rules.son_tools.design_district_essence),
            design_district,
        ),
    ]
