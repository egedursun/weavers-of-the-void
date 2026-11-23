import secrets
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.constants.units import PERCENT
from aerona.core.errors import NotFoundError, ValidationFailedError
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.environment import PlaceEnvironmentRow, RegionEnvironmentRow
from aerona.db.tables.happenings import RiverShiftRow
from aerona.db.tables.region import PolityMapKnowledgeRow, RegionDangerRow, RegionMemoryRow
from aerona.domain.enums.entity import EntityType
from aerona.domain.enums.environment import RiverClass, WaterSource
from aerona.domain.enums.happening import RiverShiftCause
from aerona.domain.enums.region import DangerHarm, DangerOrigin, DangerSource, MemoryOrigin, RegionMemoryKind
from aerona.engine.environment.control import hold, region_ground
from aerona.engine.environment.dangers import reaches, sync_stat
from aerona.engine.environment.geomorph import shape_of
from aerona.engine.primitives.distance import RegionAtlas
from aerona.engine.primitives.numbers import clamp_int
from aerona.rules.registry import Rules

RIVER_ORDER = tuple(RiverClass)
PLAYER_KEY = "player"


async def region_entity(session: AsyncSession, region_id: int) -> EntityRow:
    found = await session.get(EntityRow, region_id)
    if found is None or found.entity_type is not EntityType.REGION:
        raise NotFoundError("No such region.")
    return found


async def resync(session: AsyncSession, rules: Rules, region_id: int) -> None:
    region = await session.get(EntityRow, region_id)
    if region is not None:
        await session.flush()
        sync_stat(rules, region, list(await session.scalars(select(RegionDangerRow).where(RegionDangerRow.region_entity_id == region_id))))


async def set_danger(
    session: AsyncSession,
    rules: Rules,
    region_id: int,
    source: DangerSource,
    strength: int,
    *,
    epoch: int,
    held: bool,
    origin: DangerOrigin = DangerOrigin.PLAYER,
    son_id: int | None = None,
    targets: list[DangerHarm] | None = None,
) -> RegionDangerRow:
    region = await region_entity(session, region_id)
    ground = await region_ground(session, region.id)
    row = await session.scalar(select(RegionDangerRow).where(RegionDangerRow.region_entity_id == region.id, RegionDangerRow.source == source))
    if row is None:
        row = RegionDangerRow(world_id=ground.world_id, region_entity_id=region.id, source=source, since_epoch=epoch)
        session.add(row)
    row.strength = clamp_int(strength, 0, PERCENT)
    if targets is not None:
        row.harmed = allowed_targets(rules, source, targets)
    row.origin = origin
    row.son_id = son_id
    row.held = held
    row.updated_epoch = epoch
    await resync(session, rules, region.id)
    return row


async def danger_row(session: AsyncSession, danger_id: int) -> RegionDangerRow:
    row = await session.get(RegionDangerRow, danger_id)
    if row is None:
        raise NotFoundError("No such danger.")
    return row


def allowed_targets(rules: Rules, source: DangerSource, targets: list[DangerHarm]) -> list[str]:
    allowed = set(reaches(rules, source))
    refused = sorted(harm.value for harm in targets if harm not in allowed)
    if refused:
        raise ValidationFailedError(f"That danger cannot reach {', '.join(refused)}.")
    return sorted({harm.value for harm in targets})


async def edit_danger(
    session: AsyncSession,
    rules: Rules,
    danger_id: int,
    *,
    strength: int | None,
    held: bool | None,
    epoch: int,
    targets: list[DangerHarm] | None = None,
) -> RegionDangerRow:
    row = await danger_row(session, danger_id)
    if targets is not None:
        row.harmed = allowed_targets(rules, row.source, targets)
    if strength is not None:
        row.strength = clamp_int(strength, 0, PERCENT)
        if row.origin is DangerOrigin.DERIVED:
            row.origin = DangerOrigin.PLAYER
    if held is not None:
        row.held = held
    row.updated_epoch = epoch
    await resync(session, rules, row.region_entity_id)
    return row


async def release_danger(session: AsyncSession, rules: Rules, danger_id: int) -> RegionDangerRow:
    row = await danger_row(session, danger_id)
    if not row.held:
        raise ValidationFailedError("This danger is not held.")
    row.held = False
    await resync(session, rules, row.region_entity_id)
    return row


async def delete_danger(session: AsyncSession, rules: Rules, danger_id: int) -> RegionDangerRow:
    row = await danger_row(session, danger_id)
    await session.delete(row)
    await resync(session, rules, row.region_entity_id)
    return row


async def sanctify(session: AsyncSession, rules: Rules, region_id: int, sacredness: int | None, *, held: bool) -> RegionEnvironmentRow:
    region = await region_entity(session, region_id)
    ground = await region_ground(session, region.id)
    ground.sacredness = clamp_int(sacredness if sacredness is not None else rules.terrain.sanctify_default, 0, PERCENT)
    hold(ground, "sacredness", held)
    return ground


async def add_memory(
    session: AsyncSession, region_id: int, kind: RegionMemoryKind, magnitude: int, title: str, *, epoch: int, held: bool, subject_id: int | None = None
) -> RegionMemoryRow:
    region = await region_entity(session, region_id)
    ground = await region_ground(session, region.id)
    row = RegionMemoryRow(
        world_id=ground.world_id,
        region_entity_id=region.id,
        kind=kind,
        magnitude=clamp_int(magnitude, 0, PERCENT),
        epoch=max(0, epoch),
        source_key=f"{PLAYER_KEY}:{secrets.token_hex(8)}",
        subject_node_id=subject_id,
        title=title,
        origin=MemoryOrigin.PLAYER,
        held=held,
    )
    session.add(row)
    await session.flush()
    return row


async def memory_row(session: AsyncSession, memory_id: int) -> RegionMemoryRow:
    row = await session.get(RegionMemoryRow, memory_id)
    if row is None:
        raise NotFoundError("No such memory.")
    return row


@dataclass(frozen=True)
class MemoryEdit:
    kind: RegionMemoryKind | None = None
    magnitude: int | None = None
    title: str | None = None
    held: bool | None = None


async def edit_memory(session: AsyncSession, memory_id: int, edit: MemoryEdit) -> RegionMemoryRow:
    row = await memory_row(session, memory_id)
    if edit.kind is not None:
        row.kind = edit.kind
    if edit.magnitude is not None:
        row.magnitude = clamp_int(edit.magnitude, 0, PERCENT)
    if edit.title is not None:
        row.title = edit.title
    if edit.held is not None:
        row.held = edit.held
    await session.flush()
    return row


async def delete_memory(session: AsyncSession, memory_id: int) -> RegionMemoryRow:
    row = await memory_row(session, memory_id)
    await session.delete(row)
    await session.flush()
    return row


async def set_knowledge(session: AsyncSession, polity_id: int, region_id: int, level: int, *, held: bool, epoch: int) -> PolityMapKnowledgeRow:
    polity = await session.get(EntityRow, polity_id)
    if polity is None or polity.entity_type is not EntityType.POLITY:
        raise NotFoundError("No such realm.")
    await region_entity(session, region_id)
    row = await session.get(PolityMapKnowledgeRow, (polity_id, region_id))
    if row is None:
        row = PolityMapKnowledgeRow(polity_entity_id=polity_id, region_entity_id=region_id)
        session.add(row)
    row.level = clamp_int(level, 0, PERCENT)
    row.held = held
    row.updated_epoch = epoch
    await session.flush()
    return row


async def release_knowledge(session: AsyncSession, polity_id: int, region_id: int) -> PolityMapKnowledgeRow:
    row = await session.get(PolityMapKnowledgeRow, (polity_id, region_id))
    if row is None or not row.held:
        raise ValidationFailedError("That realm's knowledge of this region is not held.")
    row.held = False
    await session.flush()
    return row


@dataclass(frozen=True)
class Redirected:
    source: RegionEnvironmentRow
    target: RegionEnvironmentRow
    river: RiverClass
    dried: int
    watered: int


def rank(river: RiverClass) -> int:
    return RIVER_ORDER.index(river)


async def redirect_river(
    session: AsyncSession, rules: Rules, from_region_id: int, to_region_id: int, *, epoch: int, cause: RiverShiftCause = RiverShiftCause.PLAYER
) -> Redirected:
    if from_region_id == to_region_id:
        raise ValidationFailedError("A river is turned from one region into another.")
    source = await region_ground(session, (await region_entity(session, from_region_id)).id)
    target = await region_ground(session, (await region_entity(session, to_region_id)).id)
    if to_region_id not in (await RegionAtlas.load(session)).neighbour_regions(from_region_id):
        raise ValidationFailedError("A river can only be turned into a neighbouring region.")
    if source.river_class is RiverClass.NONE:
        raise ValidationFailedError("There is no river here to turn.")
    river = source.river_class
    left = RiverClass.STREAM if rules.terrain.redirect_leaves_stream and rank(river) > rank(RiverClass.STREAM) else RiverClass.NONE
    source.river_class = left
    target.river_class = river if rank(river) > rank(target.river_class) else RIVER_ORDER[min(len(RIVER_ORDER) - 1, rank(target.river_class) + 1)]
    hold(source, "river_class", True)
    hold(target, "river_class", True)
    dried = watered = 0
    places = await session.scalars(select(PlaceEnvironmentRow).where(PlaceEnvironmentRow.region_entity_id.in_([from_region_id, to_region_id])))
    for place in places:
        if "water_source" in place.locked:
            continue
        if place.region_entity_id == from_region_id and place.water_source is WaterSource.RIVER and left is RiverClass.NONE:
            place.water_source = WaterSource.NONE
            dried += 1
        elif place.region_entity_id == to_region_id and place.water_source is WaterSource.NONE:
            place.water_source = WaterSource.RIVER
            watered += 1
    for ground in (source, target):
        shape = await shape_of(session, ground.entity_id, ground.world_id)
        shape.river_course = ground.river_class
        shape.course_changed_epoch = epoch
    session.add(
        RiverShiftRow(world_id=source.world_id, from_region_id=source.entity_id, to_region_id=target.entity_id, epoch=epoch, river_class=river, cause=cause)
    )
    await session.flush()
    return Redirected(source, target, river, dried, watered)
