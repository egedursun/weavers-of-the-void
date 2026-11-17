from collections.abc import Sequence
from dataclasses import dataclass

from sqlalchemy import ColumnElement, delete, func, select

from aerona.constants.units import PERCENT
from aerona.db.repositories.cosmos import CosmosRepository
from aerona.db.repositories.worlds import WorldDraft, WorldRepository
from aerona.db.tables.celestial import WorldRow
from aerona.db.tables.entities import EntityFlagRow, EntityRow
from aerona.db.tables.interconnect import IncidentParticipantRow, IncidentRow
from aerona.db.tables.lore import ChronicleRow
from aerona.db.tables.prehistory import PrehistoryEventRow, PrehistoryRow
from aerona.db.write_guard import held
from aerona.domain.enums.chronicle import ChronicleKind
from aerona.domain.enums.entity import EntityFlag, EntityStatus, EntityType
from aerona.domain.enums.modifier import IncidentRole
from aerona.domain.enums.prehistory import PrehistoryKind, PrehistorySource, PrehistoryState
from aerona.domain.enums.world import Discovery, WorldType
from aerona.engine.context import TickContext
from aerona.engine.cosmos.orbits import planet_of
from aerona.engine.cosmos.world_views import view_of
from aerona.engine.primitives.numbers import clamp_int
from aerona.engine.recording.record import record as record_incident
from aerona.language.similarity import NamePool

LORE_FREE_KINDS = (ChronicleKind.CREATION, ChronicleKind.SYSTEM, ChronicleKind.ENGINE_RAW)
FALLEN_KINDS = (EntityType.POLITY,)
LEGEND_KINDS = (EntityType.LEGEND,)


@dataclass
class DigestTally:
    events: int = 0
    worlds_made: int = 0


async def kind_of_world(ctx: TickContext, world: WorldRow) -> PrehistoryKind:
    return (await view_of(ctx.session, ctx.rules, world.id)).prehistory_kind


def magnitude_of(value: int | None) -> int:
    return clamp_int(value or 0, 0, PERCENT)


async def last_incident_id(ctx: TickContext) -> int:
    found: int | None = await ctx.session.scalar(select(func.max(IncidentRow.id)))
    return found or 0


async def lore_free(ctx: TickContext, world_id: int) -> bool:
    written = await ctx.session.scalar(
        select(func.count()).select_from(ChronicleRow).where(ChronicleRow.world_id == world_id, ChronicleRow.kind.not_in(LORE_FREE_KINDS))
    )
    return not written


async def prehistory_of(ctx: TickContext, world: WorldRow, epochs: int, resolution: int) -> PrehistoryRow:
    row = await ctx.session.get(PrehistoryRow, world.id)
    if row is None:
        row = PrehistoryRow(
            world_id=world.id,
            kind=await kind_of_world(ctx, world),
            state=PrehistoryState.PLANNED,
            source=PrehistorySource.SIMULATED,
            epochs=epochs,
            resolution=resolution,
            birth_epoch=ctx.epoch,
            locked=[],
        )
        ctx.session.add(row)
        await ctx.session.flush()
    return row


async def keep_round(ctx: TickContext, row: PrehistoryRow, since: int, round_number: int) -> int:
    statement = (
        select(IncidentRow)
        .where(IncidentRow.id > since, IncidentRow.world_id == row.world_id)
        .order_by(IncidentRow.magnitude.desc(), IncidentRow.id)
        .limit(ctx.rules.prehistory.digest_size)
    )
    kept = 0
    for incident in await ctx.session.scalars(statement):
        ctx.session.add(
            PrehistoryEventRow(
                world_id=row.world_id,
                round=round_number,
                magnitude=magnitude_of(incident.magnitude),
                source=PrehistorySource.SIMULATED,
                incident_id=incident.id,
                locked=[],
            )
        )
        kept += 1
    await ctx.session.flush()
    return kept


async def prune_digest(ctx: TickContext, world_id: int, size: int) -> int:
    rows = list(
        await ctx.session.scalars(
            select(PrehistoryEventRow).where(PrehistoryEventRow.world_id == world_id).order_by(PrehistoryEventRow.magnitude.desc(), PrehistoryEventRow.id)
        )
    )
    dropped = [row for row in rows[size:] if "magnitude" not in (row.locked or [])]
    for row in dropped:
        await ctx.session.delete(row)
    await ctx.session.flush()
    return len(dropped)


async def strongest(ctx: TickContext, filters: Sequence[ColumnElement[bool]], limit: int) -> list[IncidentRow]:
    statement = select(IncidentRow).where(*filters).order_by(IncidentRow.magnitude.desc(), IncidentRow.id).limit(limit)
    return list(await ctx.session.scalars(statement))


async def borrow(ctx: TickContext, row: PrehistoryRow, incidents: Sequence[IncidentRow], source: PrehistorySource, *, subject: int | None = None) -> int:
    for incident in incidents:
        ctx.session.add(
            PrehistoryEventRow(
                world_id=row.world_id,
                round=0,
                magnitude=magnitude_of(incident.magnitude),
                source=source,
                incident_id=incident.id,
                subject_node_id=subject,
                source_world_id=row.source_world_id,
                mirrored=source is PrehistorySource.MIRRORED,
                locked=[],
            )
        )
    await ctx.session.flush()
    return len(incidents)


async def deeds_of(ctx: TickContext, row: PrehistoryRow, god_id: int | None) -> int:
    if god_id is None:
        return 0
    statement = (
        select(IncidentRow)
        .join(IncidentParticipantRow, IncidentParticipantRow.incident_id == IncidentRow.id)
        .where(IncidentParticipantRow.node_id == god_id, IncidentParticipantRow.role == IncidentRole.ACTOR)
        .order_by(IncidentRow.magnitude.desc(), IncidentRow.id)
        .limit(ctx.rules.prehistory.digest_size)
    )
    return await borrow(ctx, row, list(await ctx.session.scalars(statement)), PrehistorySource.DERIVED, subject=god_id)


async def souls_of(ctx: TickContext, row: PrehistoryRow, world: WorldRow) -> int:
    source = row.source_world_id or world.parent_world_id or (await CosmosRepository(ctx.session).require_cosmos()).primary_world_id
    if source is None or source == world.id:
        return 0
    row.source_world_id = source
    deaths = select(ChronicleRow.id).where(ChronicleRow.world_id == source, ChronicleRow.kind == ChronicleKind.DEATH)
    found = await strongest(ctx, (IncidentRow.chronicle_id.in_(deaths),), ctx.rules.prehistory.digest_size)
    return await borrow(ctx, row, found, PrehistorySource.DERIVED)


async def dreams_of(ctx: TickContext, row: PrehistoryRow, world: WorldRow) -> int:
    await ctx.session.execute(delete(PrehistoryEventRow).where(PrehistoryEventRow.world_id == world.id, PrehistoryEventRow.source == PrehistorySource.DREAMT))
    dreams = select(ChronicleRow.id).where(ChronicleRow.kind == ChronicleKind.DREAM, ChronicleRow.world_id != world.id)
    found = await strongest(ctx, (IncidentRow.chronicle_id.in_(dreams),), ctx.rules.prehistory.digest_size)
    return await borrow(ctx, row, found, PrehistorySource.DREAMT)


async def mirror_of(ctx: TickContext, row: PrehistoryRow, world: WorldRow) -> int:
    twin_id = row.source_world_id or world.mirror_twin_id
    if twin_id is None:
        return 0
    row.source_world_id = twin_id
    kept = 0
    for event in await ctx.session.scalars(select(PrehistoryEventRow).where(PrehistoryEventRow.world_id == twin_id).order_by(PrehistoryEventRow.id)):
        ctx.session.add(
            PrehistoryEventRow(
                world_id=world.id,
                round=event.round,
                magnitude=event.magnitude,
                source=PrehistorySource.MIRRORED,
                incident_id=event.incident_id,
                subject_node_id=event.subject_node_id,
                source_world_id=twin_id,
                mirrored=True,
                locked=[],
            )
        )
        kept += 1
    await ctx.session.flush()
    return kept


async def borrowed_from(ctx: TickContext, row: PrehistoryRow, source: int | None) -> int:
    if source is None or source == row.world_id:
        return 0
    row.source_world_id = source
    found = await strongest(ctx, (IncidentRow.world_id == source,), ctx.rules.prehistory.digest_size)
    return await borrow(ctx, row, found, PrehistorySource.DERIVED)


async def free_name(ctx: TickContext, base: str) -> str:
    taken = await ctx.session.scalars(select(WorldRow.name))
    return NamePool(list(taken), ctx.rules).unique(base)


async def make_lost_origin(ctx: TickContext, row: PrehistoryRow, ship: WorldRow, tally: DigestTally) -> WorldRow:
    planet = await planet_of(ctx.session, ship)
    origin = await WorldRepository(ctx.session).create_world(
        WorldDraft(
            name=await free_name(ctx, ship.name[::-1].capitalize()),
            world_type=WorldType.ORDINARY,
            orbit=planet.orbit,
            terrain_seed=f"{ship.terrain_seed}.origin",
            terrain_sea=ship.terrain_sea,
            terrain_mountains=ship.terrain_mountains,
            terrain_humidity=ship.terrain_humidity,
            danger=ship.danger,
            created_epoch=ctx.epoch,
            star_id=planet.star_id,
            discovery=Discovery.FORGOTTEN,
        )
    )
    row.source_world_id = origin.id
    ctx.session.add(
        PrehistoryRow(
            world_id=origin.id,
            kind=PrehistoryKind.FULL,
            state=PrehistoryState.DONE,
            source=PrehistorySource.DERIVED,
            birth_epoch=ctx.epoch,
            locked=[],
        )
    )
    write = await record_incident(
        ctx, "prehistory.lost_origin", roles={IncidentRole.SUBJECT: ship.id, IncidentRole.ORIGIN: origin.id}, world_id=ship.id, magnitude=PERCENT // 2
    )
    if write.incident_id is not None:
        incident = await ctx.session.get(IncidentRow, write.incident_id)
        if incident is not None:
            await borrow(ctx, row, [incident], PrehistorySource.DERIVED, subject=origin.id)
    tally.worlds_made += 1
    return origin


async def make_twin(ctx: TickContext, mirror: WorldRow, tally: DigestTally) -> WorldRow:
    twin = await WorldRepository(ctx.session).create_world(
        WorldDraft(
            name=await free_name(ctx, mirror.name[::-1].capitalize()),
            world_type=WorldType.ORDINARY,
            orbit=mirror.orbit,
            terrain_seed=f"{mirror.terrain_seed}.twin",
            terrain_sea=1 - mirror.terrain_sea,
            terrain_mountains=mirror.terrain_mountains,
            terrain_humidity=mirror.terrain_humidity,
            danger=mirror.danger,
            created_epoch=ctx.epoch,
            star_id=mirror.star_id,
            parent_world_id=mirror.parent_world_id,
            creator_son_id=mirror.creator_son_id,
        )
    )
    mirror.mirror_twin_id = twin.id
    twin.mirror_twin_id = mirror.id
    await ctx.session.flush()
    tally.worlds_made += 1
    return twin


async def backfill_world(ctx: TickContext, world: WorldRow) -> int:
    if held(world.id) or await ctx.session.get(PrehistoryRow, world.id) is not None:
        return 0
    row = PrehistoryRow(
        world_id=world.id,
        kind=await kind_of_world(ctx, world),
        state=PrehistoryState.DONE,
        source=PrehistorySource.BACKFILLED,
        birth_epoch=world.created_epoch or 0,
        locked=[],
    )
    ctx.session.add(row)
    await ctx.session.flush()
    remembered = list(
        await ctx.session.scalars(
            select(EntityRow)
            .where(
                EntityRow.world_id == world.id,
                (EntityRow.entity_type.in_(LEGEND_KINDS)) | (EntityRow.entity_type.in_(FALLEN_KINDS) & (EntityRow.status == EntityStatus.DEAD)),
            )
            .order_by(EntityRow.importance.desc().nulls_last(), EntityRow.id)
            .limit(ctx.rules.prehistory.digest_size)
        )
    )
    flagged = list(
        await ctx.session.scalars(
            select(EntityRow)
            .join(EntityFlagRow, EntityFlagRow.entity_id == EntityRow.id)
            .where(EntityRow.world_id == world.id, EntityFlagRow.flag.in_([EntityFlag.RUIN, EntityFlag.PREVIOUS_CREATION, EntityFlag.DEAD_LANGUAGE]))
            .order_by(EntityRow.id)
            .limit(ctx.rules.prehistory.digest_size)
        )
    )
    kept = 0
    for entity in dict.fromkeys([*remembered, *flagged]):
        ctx.session.add(
            PrehistoryEventRow(
                world_id=world.id,
                round=0,
                magnitude=magnitude_of(entity.importance),
                source=PrehistorySource.BACKFILLED,
                subject_node_id=entity.id,
                locked=[],
            )
        )
        kept += 1
    await ctx.session.flush()
    return kept
