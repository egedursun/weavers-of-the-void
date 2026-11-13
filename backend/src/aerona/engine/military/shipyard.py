from dataclasses import dataclass, field

from sqlalchemy.ext.asyncio import AsyncSession

from aerona.catalog.vehicles import FRAMES
from aerona.constants.units import PERCENT
from aerona.db.tables.cosmic_state import VesselProfileRow
from aerona.db.tables.entities import EntityRow
from aerona.domain.enums.discovery import BlueprintKind
from aerona.domain.enums.economy import MaterialSlot
from aerona.domain.enums.material import MaterialKind
from aerona.domain.enums.military import VesselArmament, VesselStatus
from aerona.domain.enums.travel import VehicleKind
from aerona.domain.enums.vehicles import VehicleFrame
from aerona.engine.economy.materials import set_node_material
from aerona.engine.lore.blueprints import design_factor
from aerona.engine.military.vessels import frame_value
from aerona.engine.primitives.stats import set_stats
from aerona.rules.registry import Rules


@dataclass(frozen=True)
class Commission:
    frame: VehicleFrame | None = None
    armament: list[VesselArmament] | None = field(default=None)
    hull_material: MaterialKind | None = None
    fabric_material: MaterialKind | None = None
    home_port_id: int | None = None
    captain_id: int | None = None
    crew: int | None = None


async def commission(session: AsyncSession, rules: Rules, vessel: EntityRow, order: Commission) -> VesselProfileRow:
    hull = order.frame or VehicleFrame.BOAT
    spec = FRAMES[hull]
    row = await session.get(VesselProfileRow, vessel.id)
    if row is None:
        row = VesselProfileRow(entity_id=vessel.id, kind=VehicleKind.SHIP)
        session.add(row)
    row.kind = VehicleKind.SHIP
    row.frame = hull
    row.armament = [item.value for item in (order.armament if order.armament is not None else spec.armament)][: max(spec.slots, 0) or None]
    designed = await design_factor(session, rules, order.home_port_id or vessel.location_id, BlueprintKind.VESSEL, hull.value)
    row.seaworthiness = min(PERCENT, round(frame_value(rules, hull, "seaworthiness") * designed))
    row.crew = order.crew if order.crew is not None else spec.crew
    row.cargo_capacity = min(frame_value(rules, hull, "cargo"), row.crew * rules.seafaring.crew_per_cargo)
    row.condition = PERCENT
    row.status = VesselStatus.DOCKED
    row.home_port_entity_id = order.home_port_id or vessel.location_id
    row.captain_entity_id = order.captain_id
    row.renown = row.renown or 0
    row.voyages = row.voyages or 0
    row.locked = list(row.locked or [])
    set_stats(vessel, speed=min(PERCENT, frame_value(rules, hull, "speed")), crew=row.crew, strangeness=spec.strangeness)
    await session.flush()
    if order.hull_material is not None:
        await set_node_material(session, vessel.id, MaterialSlot.HULL, order.hull_material)
    if order.fabric_material is not None:
        await set_node_material(session, vessel.id, MaterialSlot.FABRIC, order.fabric_material)
    await session.flush()
    return row
