from types import MappingProxyType
from zlib import crc32

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.catalog.vehicles import FRAMES, FrameSpec
from aerona.constants.units import PERCENT
from aerona.db.tables.collective import DesignRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.environment import RegionEnvironmentRow
from aerona.db.tables.vehicles import VehicleGroupRow
from aerona.db.write_guard import held
from aerona.domain.enums.economy import TradeMode
from aerona.domain.enums.environment import TerrainKind
from aerona.domain.enums.vehicles import VehicleDomain, VehicleFamily, VehicleFrame
from aerona.engine.body.customs import people_of
from aerona.engine.collective.designs import draw_design
from aerona.engine.context import TickContext
from aerona.engine.primitives.knowledge import KnowledgeMap
from aerona.engine.vehicles.fleet import opened
from aerona.engine.vehicles.groups import GroupReading, groups_of, read
from aerona.engine.vehicles.sections import StrikeResult, strike_group

D = VehicleDomain
Y = VehicleFamily
CARRIERS: MappingProxyType[TradeMode, tuple[frozenset[VehicleDomain], frozenset[VehicleFamily]]] = MappingProxyType(
    {
        TradeMode.ROAD: (frozenset({D.LAND}), frozenset({Y.CART, Y.WAGON, Y.MOTOR, Y.RAIL, Y.CONSTRUCT})),
        TradeMode.CARAVAN: (frozenset({D.LAND}), frozenset({Y.MOUNT, Y.CART, Y.WAGON})),
        TradeMode.RIVER: (frozenset({D.WATER}), frozenset({Y.BOAT, Y.GALLEY, Y.STEAM_SHIP})),
        TradeMode.SEA: (frozenset({D.WATER}), frozenset({Y.SAILING_SHIP, Y.STEAM_SHIP, Y.GALLEY, Y.BOAT, Y.LIVING})),
        TradeMode.SKY: (frozenset({D.AIR}), frozenset({Y.AIRSHIP, Y.BALLOON, Y.AIRCRAFT})),
    }
)


T = TerrainKind
SNOW_GROUNDS = frozenset({T.TUNDRA, T.ICE_SHEET, T.MOUNTAINS, T.HIGH_PASS})
FRAME_GROUNDS: MappingProxyType[VehicleFrame, frozenset[TerrainKind]] = MappingProxyType({VehicleFrame.SLEDGE: SNOW_GROUNDS})
NEAR_PCT = 80


def carries(mode: TradeMode, spec: FrameSpec) -> bool:
    domains, families = CARRIERS[mode]
    return spec.domain in domains and spec.family in families


def cargo_worth(spec: FrameSpec) -> int:
    return spec.cargo + spec.speed + spec.endurance // 2


def suits(spec: FrameSpec, ground: TerrainKind | None) -> bool:
    needs = FRAME_GROUNDS.get(spec.frame)
    return needs is None or ground in needs


def best_carrier(knowledge: KnowledgeMap, owner: EntityRow, mode: TradeMode, ground: TerrainKind | None = None) -> VehicleFrame | None:
    found = [spec for spec in FRAMES.values() if carries(mode, spec) and spec.cargo > 0 and suits(spec, ground) and opened(spec, knowledge, owner)]
    if not found:
        return None
    top = max(cargo_worth(spec) for spec in found)
    near = [spec for spec in found if cargo_worth(spec) * PERCENT >= top * NEAR_PCT]
    return min(near, key=lambda spec: crc32(f"{owner.id}.{spec.frame.value}".encode())).frame


async def ground_of(session: AsyncSession, place: EntityRow) -> TerrainKind | None:
    region = await session.get(RegionEnvironmentRow, place.location_id) if place.location_id is not None else None
    return region.dominant_terrain if region is not None else None


async def carrier_design(ctx: TickContext, owner: EntityRow, mode: TradeMode, knowledge: KnowledgeMap, ground: TerrainKind | None = None) -> DesignRow | None:
    people = await people_of(ctx.session, owner)
    maker = people if people is not None and not held(people.id) else owner
    statement = select(DesignRow).where(
        or_(DesignRow.owner_entity_id == owner.id, DesignRow.origin_node_id == maker.id), DesignRow.obsolete.is_(False), DesignRow.frame.is_not(None)
    )
    for design in await ctx.session.scalars(statement.order_by(DesignRow.epoch.desc(), DesignRow.id.desc())):
        if design.frame is not None and carries(mode, FRAMES[design.frame]) and design.cargo > 0 and suits(FRAMES[design.frame], ground):
            return design
    frame = best_carrier(knowledge, maker, mode, ground)
    return await draw_design(ctx, maker, frame, knowledge=knowledge) if frame is not None else None


async def carrier_group(session: AsyncSession, owner_id: int, mode: TradeMode) -> GroupReading | None:
    best: GroupReading | None = None
    for group in await groups_of(session, owner_id):
        reading = await read(session, group)
        if reading is None or reading.design.frame is None or not carries(mode, FRAMES[reading.design.frame]):
            continue
        if best is None or reading.cargo > best.cargo:
            best = reading
    return best


async def raid_carriers(ctx: TickContext, group: VehicleGroupRow, severity: int, slot: str) -> StrikeResult:
    return await strike_group(ctx, group, max(1, severity * group.count // 4), slot)
