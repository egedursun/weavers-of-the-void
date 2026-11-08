from aerona.catalog.discovery import BLUEPRINT_KINDS
from aerona.constants.units import PERCENT
from aerona.core.errors import NotFoundError, ValidationFailedError
from aerona.db.tables.celestial import WorldRow
from aerona.db.tables.discovery import BannedWorkRow, BlueprintRow, GreatPersonRow, PolityEraRow, ResearchIncidentRow, WorldEraRow
from aerona.db.tables.entities import EntityRow
from aerona.domain.enums.culture import Technique
from aerona.domain.enums.discovery import AgeKind, BlueprintKind, BlueprintSource, GreatField, ResearchIncident
from aerona.domain.enums.entity import EntityStatus, EntityType
from aerona.engine.context import TickContext
from aerona.engine.lore.dangers import strike
from aerona.engine.lore.eras import SCORE_CEILING, SCORE_FLOOR
from aerona.engine.lore.great_people import perform_deed
from aerona.engine.lore.learning_control import holder
from aerona.engine.polity.control import lock
from aerona.engine.primitives.numbers import clamp_int
from aerona.engine.primitives.queries import living_entity


async def raise_great(ctx: TickContext, mortal_id: int, field: GreatField, *, deed: bool) -> GreatPersonRow:
    mortal = await living_entity(ctx.session, mortal_id)
    if mortal is None or mortal.entity_type is not EntityType.MORTAL:
        raise NotFoundError("No such living mortal.")
    row = await ctx.session.get(GreatPersonRow, mortal.id)
    if row is None:
        row = GreatPersonRow(mortal_entity_id=mortal.id, field=field, holder_entity_id=mortal.location_id, promoted_epoch=ctx.epoch, deed_done=False, locked=[])
        ctx.session.add(row)
    row.field = field
    row.locked = lock(row.locked, "field")
    await ctx.session.flush()
    if deed:
        row.deed_done = False
        await perform_deed(ctx, row)
    await ctx.session.flush()
    return row


async def set_era(ctx: TickContext, polity_id: int, score: int | None, age: AgeKind | None, *, hold: bool) -> PolityEraRow:
    polity = await living_entity(ctx.session, polity_id)
    if polity is None or polity.entity_type is not EntityType.POLITY:
        raise NotFoundError("No such living realm.")
    row = await ctx.session.get(PolityEraRow, polity.id)
    if row is None:
        row = PolityEraRow(polity_entity_id=polity.id, score=0, age=AgeKind.NORMAL, since_epoch=ctx.epoch, lowest=0, locked=[])
        ctx.session.add(row)
    if score is not None:
        row.score = clamp_int(score, SCORE_FLOOR, SCORE_CEILING)
        row.locked = lock(row.locked, "score") if hold else [key for key in row.locked if key != "score"]
    if age is not None:
        if age is not row.age:
            row.age, row.since_epoch = age, ctx.epoch
            row.lowest = row.score if age is AgeKind.DARK else row.lowest
        row.locked = lock(row.locked, "age") if hold else [key for key in row.locked if key != "age"]
    if score is None and age is None and not hold:
        row.locked = []
    await ctx.session.flush()
    return row


async def set_world_era(ctx: TickContext, world_id: int, era: int, *, hold: bool) -> WorldEraRow:
    world = await ctx.session.get(WorldRow, world_id)
    if world is None:
        raise NotFoundError("No such world.")
    if era < 1:
        raise ValidationFailedError("A world's era starts at 1.")
    row = await ctx.session.get(WorldEraRow, world.id)
    if row is None:
        row = WorldEraRow(world_id=world.id, era=1, since_epoch=ctx.epoch, locked=[])
        ctx.session.add(row)
    if era != row.era:
        row.era, row.since_epoch = era, ctx.epoch
    row.locked = lock(row.locked, "era") if hold else [key for key in row.locked if key != "era"]
    await ctx.session.flush()
    return row


async def cause_incident(ctx: TickContext, holder_id: int, kind: ResearchIncident, technique: Technique | None) -> ResearchIncidentRow:
    await holder(ctx, holder_id)
    community = await ctx.session.get(EntityRow, holder_id)
    if community is None:
        raise NotFoundError("No such living community.")
    row = await strike(ctx, community, kind, technique=technique)
    await ctx.session.flush()
    return row


async def grant_design(ctx: TickContext, holder_id: int, kind: BlueprintKind, subject: str, *, quality: int, name: str | None) -> BlueprintRow:
    owner = await living_entity(ctx.session, holder_id)
    if owner is None or owner.status is not EntityStatus.CANON:
        raise NotFoundError("No such living holder.")
    if not subject.strip():
        raise ValidationFailedError("Name what the design is of.")
    if not 0 <= quality <= PERCENT:
        raise ValidationFailedError(f"A design's quality runs from 0 to {PERCENT}.")
    label = subject.strip().lower().replace(" ", "_")
    row = BlueprintRow(
        name=(name or "").strip() or f"{BLUEPRINT_KINDS[kind]}: {label.replace('_', ' ')}",
        kind=kind,
        subject=label,
        holder_node_id=owner.id,
        origin_node_id=owner.id,
        source=BlueprintSource.GRANTED,
        licensed_to=[],
        quality=quality,
        since_epoch=ctx.epoch,
        locked=[],
    )
    ctx.session.add(row)
    await ctx.session.flush()
    return row


async def set_ban(ctx: TickContext, polity_id: int, work_id: int, *, banned: bool) -> BannedWorkRow | None:
    polity = await living_entity(ctx.session, polity_id)
    work = await living_entity(ctx.session, work_id)
    if polity is None or polity.entity_type is not EntityType.POLITY:
        raise NotFoundError("No such living realm.")
    if work is None:
        raise NotFoundError("No such work.")
    row = await ctx.session.get(BannedWorkRow, (polity.id, work.id))
    if not banned:
        if row is not None:
            await ctx.session.delete(row)
            await ctx.session.flush()
        return None
    if row is None:
        row = BannedWorkRow(polity_entity_id=polity.id, work_entity_id=work.id, since_epoch=ctx.epoch, locked=["since_epoch"])
        ctx.session.add(row)
    await ctx.session.flush()
    return row
