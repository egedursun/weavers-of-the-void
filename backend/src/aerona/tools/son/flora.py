from typing import Any

from sqlalchemy import func, select

from aerona.catalog.gates import Gate
from aerona.db.tables.ecology import SpeciesProfileRow
from aerona.db.tables.flora import PlantProfileRow, RegionCropRow
from aerona.domain.enums.action import ActionKind
from aerona.domain.enums.agent import AgentKind
from aerona.domain.enums.chronicle import ChronicleKind
from aerona.domain.enums.ecology import GROWN, SOWN, Cultivation
from aerona.domain.enums.entity import EntityType
from aerona.domain.enums.modifier import IncidentRole
from aerona.engine.ecology.flora_control import plant_of, set_crop
from aerona.prompts import SonToolId
from aerona.prompts.tools.results import SonResult, result
from aerona.tools.framework.call import SonCall
from aerona.tools.framework.inputs import ToolInput
from aerona.tools.framework.spec import ToolMeta, ToolSpec, gate, son_standard_action
from aerona.tools.framework.validation import fail, require_canon, require_type
from aerona.tools.son.support import ensure_in_reach, grant


class SowInput(ToolInput):
    region_id: int
    plant_id: int


async def sow_crop(call: SonCall, args: SowInput) -> str:
    table = call.rules.flora
    region = await require_canon(call.session, args.region_id)
    require_type(region, {EntityType.REGION}, SonResult.SOW_PLACE)
    plant_entity = await require_canon(call.session, args.plant_id)
    require_type(plant_entity, {EntityType.SPECIES}, SonResult.NOT_A_PLANT)
    profile = await call.session.get(SpeciesProfileRow, plant_entity.id)
    if profile is None or profile.species_class not in GROWN:
        fail(SonResult.NOT_A_PLANT)
    await ensure_in_reach(call, region)
    sown = await call.session.scalar(select(func.count()).select_from(RegionCropRow).where(RegionCropRow.region_entity_id == region.id))
    if await call.session.get(RegionCropRow, (region.id, plant_entity.id)) is None and int(sown or 0) >= table.crop_cap:
        fail(SonResult.CROP_FULL, place=region.name, count=int(sown or 0))
    if call.son.essence < table.sow_cost:
        fail(SonResult.TEACH_ESSENCE, cost=table.sow_cost)
    plant: PlantProfileRow = await plant_of(call.tick, plant_entity.id)
    if plant.cultivation not in SOWN and "cultivation" not in plant.locked:
        plant.cultivation, plant.since_epoch = Cultivation.CULTIVATED, call.epoch
    row = await set_crop(call.tick, region.id, plant_entity.id, table.sow_share, hold=False, release=[])
    call.spend_essence(table.sow_cost)
    call.target(region.id)
    gained = await grant(call, call.son, call.rules.son_tools.knowledge_xp, call.rules.son_tools.knowledge_renown)
    await call.record(
        "tools.son.sow_crop",
        roles={IncidentRole.ACTOR: call.son.id, IncidentRole.SUBJECT: plant_entity.id, IncidentRole.PLACE: region.id},
        place=region.id,
        kind=ChronicleKind.RESOURCE,
    )
    return result(SonResult.CROP_SOWN, id=plant_entity.id, name=plant_entity.name, share=row.share, place=region.name, gained=gained)


def specs() -> list[ToolSpec[SonCall, Any]]:
    return [
        ToolSpec(
            SonToolId.SOW_CROP,
            AgentKind.SON,
            SowInput,
            ToolMeta(ActionKind.RESHAPE_LAND, son_standard_action, essence_cost=lambda rules: rules.flora.sow_cost, rarity_gate=gate(Gate.INFLUENCE_TOOLS)),
            sow_crop,
        )
    ]
