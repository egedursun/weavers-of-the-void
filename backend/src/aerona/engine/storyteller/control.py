from sqlalchemy import select

from aerona.constants.units import PERCENT
from aerona.core.errors import ValidationFailedError
from aerona.db.base import Base
from aerona.db.repositories.cosmos import CosmosRepository
from aerona.db.tables.ages import (
    AGE_FIELDS,
    ARC_FIELDS,
    BEAT_FIELDS,
    ECHO_FIELDS,
    FIGURE_FIELDS,
    FORECAST_FIELDS,
    FORMATION_FIELDS,
    SEASON_FIELDS,
    SETUP_FIELDS,
    TRANSFORMATION_FIELDS,
    AgeEchoRow,
    AgeRow,
    ArcBeatRow,
    ArcFigureRow,
    ArcRow,
    EcoTransformationRow,
    FormationHistoryRow,
    IrregularSeasonRow,
    SetupRow,
    WinterForecastRow,
)
from aerona.db.tables.celestial import WorldRow
from aerona.db.tables.cycles import LongPlanRow
from aerona.db.tables.physics import WorldPhysicsRow
from aerona.domain.enums.ages import AgeCycle, ArcRole, ArcStage, ArcTemplate, SeasonCause, SetupKind
from aerona.domain.enums.cycles import LongPlanKind
from aerona.domain.enums.entity import EntityType
from aerona.engine.collective.control import of_type, saved
from aerona.engine.context import TickContext
from aerona.engine.cosmos.formation import FormationTally, history_of, mark_craters, shape
from aerona.engine.cycles.control import node_exists
from aerona.engine.cycles.ecology import work_of
from aerona.engine.divine.control import apply
from aerona.engine.environment.long_seasons import SeasonTally, begin, forecast
from aerona.engine.gatherings.control import Values, allowed, found
from aerona.engine.storyteller.ages import turn_age
from aerona.engine.storyteller.arcs import open_arc

PEOPLES = frozenset({EntityType.PEOPLE})


async def world_of(ctx: TickContext, world_id: int) -> WorldRow:
    return await found(ctx, WorldRow, world_id, "world")


async def read_formation(ctx: TickContext, world_id: int, reshape: bool) -> FormationHistoryRow:
    world = await world_of(ctx, world_id)
    old = await ctx.session.get(FormationHistoryRow, world.id)
    if old is not None:
        await ctx.session.delete(old)
        await ctx.session.flush()
    physics = await ctx.session.get(WorldPhysicsRow, world.id)
    row = await history_of(ctx, world, physics, fresh=reshape)
    ctx.session.add(row)
    await ctx.session.flush()
    if reshape and physics is not None:
        await shape(ctx, world, physics, row)
    await mark_craters(ctx, world, row, FormationTally())
    await ctx.session.flush()
    return row


async def reshape_world(ctx: TickContext, world_id: int) -> FormationHistoryRow:
    world = await world_of(ctx, world_id)
    row = await found(ctx, FormationHistoryRow, world.id, "formation history")
    physics = await found(ctx, WorldPhysicsRow, world.id, "world physics")
    await shape(ctx, world, physics, row)
    await ctx.session.flush()
    return row


async def unsettle_seasons(ctx: TickContext, world_id: int, by_node_id: int | None) -> IrregularSeasonRow:
    world = await world_of(ctx, world_id)
    if await ctx.session.get(IrregularSeasonRow, world.id) is not None:
        raise ValidationFailedError(f"The seasons of {world.name} already run irregular.")
    return await begin(ctx, world, SeasonCause.DIVINE, by_node_id)


async def read_winter(ctx: TickContext, world_id: int) -> int:
    world = await world_of(ctx, world_id)
    row = await found(ctx, IrregularSeasonRow, world.id, "irregular season")
    tally = SeasonTally()
    await forecast(ctx, world, row, tally)
    return tally.forecasts


async def set_forecast(ctx: TickContext, world_id: int, people_id: int, predicted_end_epoch: int, heeded: bool) -> WinterForecastRow:
    await world_of(ctx, world_id)
    await of_type(ctx, people_id, PEOPLES, "a people")
    row = await ctx.session.scalar(select(WinterForecastRow).where(WinterForecastRow.world_id == world_id, WinterForecastRow.people_entity_id == people_id))
    if row is None:
        row = await saved(ctx, WinterForecastRow(world_id=world_id, people_entity_id=people_id, made_epoch=ctx.epoch, locked=[]))
    apply(row, {"predicted_end_epoch": predicted_end_epoch, "heeded": heeded}, [])
    await ctx.session.flush()
    return row


async def aim_transformation(ctx: TickContext, plan_id: int, moisture: int, forest: int, fertility: int) -> EcoTransformationRow:
    plan = await found(ctx, LongPlanRow, plan_id, "long plan")
    if plan.kind is not LongPlanKind.ECOLOGICAL_TRANSFORMATION:
        raise ValidationFailedError("Only a plan to remake the land can aim the land.")
    row = await work_of(ctx, plan)
    apply(row, {"target_moisture": moisture, "target_forest": forest, "target_fertility": fertility}, [])
    await ctx.session.flush()
    return row


async def set_cycle(ctx: TickContext, cycle: AgeCycle) -> AgeCycle:
    cosmos = await CosmosRepository(ctx.session).require_cosmos()
    cosmos.age_cycle = cycle
    await ctx.session.flush()
    return cycle


async def turn_now(ctx: TickContext) -> AgeRow:
    cosmos = await CosmosRepository(ctx.session).require_cosmos()
    if cosmos.age_cycle is not AgeCycle.CYCLIC:
        raise ValidationFailedError("Only a cyclic cosmos turns its ages; make the cosmos cyclic first.")
    return await turn_age(ctx, cosmos.apocalypse_variant)


async def add_echo(ctx: TickContext, age_id: int, template: ArcTemplate, source_id: int | None, weight: int) -> AgeEchoRow:
    await found(ctx, AgeRow, age_id, "age")
    if source_id is not None:
        await node_exists(ctx, source_id, "source")
    return await saved(ctx, AgeEchoRow(age_id=age_id, template=template, source_node_id=source_id, weight=max(0, min(PERCENT, weight)), locked=[]))


async def begin_arc(ctx: TickContext, subject_id: int, template: ArcTemplate, figure_id: int | None, role: ArcRole | None) -> ArcRow:
    await node_exists(ctx, subject_id, "subject")
    figures: tuple[tuple[int, ArcRole], ...] = ()
    if figure_id is not None:
        await node_exists(ctx, figure_id, "figure")
        figures = ((figure_id, role or ArcRole.ALLY),)
    return await open_arc(ctx, subject_id, template, figures)


async def press_arc(ctx: TickContext, arc_id: int, drama: int) -> ArcRow:
    row = await found(ctx, ArcRow, arc_id, "arc")
    apply(row, {"drama": max(0, min(PERCENT, drama))}, [])
    await ctx.session.flush()
    return row


async def add_figure(ctx: TickContext, arc_id: int, node_id: int, role: ArcRole) -> ArcFigureRow:
    arc = await found(ctx, ArcRow, arc_id, "arc")
    await node_exists(ctx, node_id, "figure")
    if node_id == arc.subject_node_id:
        raise ValidationFailedError("The subject of a tale is not one of its figures.")
    if await ctx.session.get(ArcFigureRow, (arc_id, node_id)) is not None:
        raise ValidationFailedError("That figure is already in the tale.")
    return await saved(ctx, ArcFigureRow(arc_id=arc_id, node_id=node_id, role=role, locked=[]))


async def add_beat(ctx: TickContext, arc_id: int, stage: ArcStage, text: str) -> ArcBeatRow:
    arc = await found(ctx, ArcRow, arc_id, "arc")
    row = await saved(ctx, ArcBeatRow(arc_id=arc.id, stage=stage, text=text, epoch=ctx.epoch, locked=[]))
    if "stage" not in arc.locked:
        arc.stage = stage
        arc.beats += 1
        arc.last_beat_epoch = ctx.epoch
    await ctx.session.flush()
    return row


async def add_setup(ctx: TickContext, kind: SetupKind, source_id: int, subject_id: int | None) -> SetupRow:
    if subject_id is not None:
        await node_exists(ctx, subject_id, "subject")
    return await saved(ctx, SetupRow(kind=kind, source_id=source_id, subject_node_id=subject_id, opened_epoch=ctx.epoch, locked=[]))


EDITABLE: dict[str, tuple[type[Base], tuple[str, ...], str]] = {
    "formation": (FormationHistoryRow, FORMATION_FIELDS, "formation history"),
    "irregular_season": (IrregularSeasonRow, SEASON_FIELDS, "irregular season"),
    "winter_forecast": (WinterForecastRow, FORECAST_FIELDS, "forecast"),
    "eco_transformation": (EcoTransformationRow, TRANSFORMATION_FIELDS, "transformation"),
    "age": (AgeRow, AGE_FIELDS, "age"),
    "age_echo": (AgeEchoRow, ECHO_FIELDS, "echo"),
    "arc": (ArcRow, ARC_FIELDS, "tale"),
    "arc_figure": (ArcFigureRow, FIGURE_FIELDS, "figure"),
    "arc_beat": (ArcBeatRow, BEAT_FIELDS, "beat"),
    "setup": (SetupRow, SETUP_FIELDS, "setup"),
}


async def edit_record(ctx: TickContext, kind: str, key: object, values: Values, release: list[str]) -> Base:
    table, fields, label = EDITABLE[kind]
    row = apply(await found(ctx, table, key, label), allowed(values, fields, label), release)
    await ctx.session.flush()
    return row


async def delete_record(ctx: TickContext, kind: str, key: object) -> None:
    table, _, label = EDITABLE[kind]
    await ctx.session.delete(await found(ctx, table, key, label))
    await ctx.session.flush()
