from dataclasses import dataclass

from sqlalchemy import select

from aerona.catalog.collective import COLLECTION_FORMATIVE, FORMATIVE_SHIFTS
from aerona.catalog.life.demography import MINOR_BANDS
from aerona.constants.units import PERCENT
from aerona.db.tables.ages import IrregularSeasonRow
from aerona.db.tables.collective import GenerationRow
from aerona.db.tables.cosmos import AppliedFixupRow
from aerona.db.tables.demography import CohortRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.gatherings import CollectionMemberRow, CollectionPlaceRow, CollectionRow
from aerona.db.tables.settlement import SettlementProfileRow
from aerona.db.tables.society import CommunitySocietyRow
from aerona.db.write_guard import held
from aerona.domain.enums.collective import FormativeKind
from aerona.domain.enums.gathering import CollectionRole
from aerona.domain.enums.mind import ValueAxis, ValueHolder
from aerona.domain.enums.modifier import IncidentRole
from aerona.engine.body.customs import people_of
from aerona.engine.collective.book import population_of, shift, towns
from aerona.engine.context import TickContext
from aerona.engine.mind.book import stored_values, write_values
from aerona.engine.primitives.numbers import clamp_int, round_half_up
from aerona.engine.primitives.stats import stat_or
from aerona.engine.recording.record import record

VALUE_SPAN = 100


@dataclass
class GenerationTally:
    shaped: int = 0
    formed: int = 0
    passed: int = 0


def window_of(epoch: int, span: int) -> int:
    return epoch - epoch % max(1, span)


async def formative_now(ctx: TickContext, town: EntityRow) -> set[FormativeKind]:
    found: set[FormativeKind] = set()
    rows = await ctx.session.execute(
        select(CollectionRow.kind, CollectionMemberRow.role)
        .outerjoin(CollectionMemberRow, (CollectionMemberRow.collection_id == CollectionRow.id) & (CollectionMemberRow.node_id == town.id))
        .join(CollectionPlaceRow, CollectionPlaceRow.collection_id == CollectionRow.id, isouter=True)
        .where(CollectionRow.start_epoch == ctx.epoch, (CollectionPlaceRow.place_entity_id == town.id) | (CollectionMemberRow.node_id == town.id))
    )
    for kind, role in rows:
        if kind in COLLECTION_FORMATIVE:
            found.add(COLLECTION_FORMATIVE[kind])
        if role is CollectionRole.WINNER:
            found.add(FormativeKind.VICTORY)
        elif role is CollectionRole.LOSER:
            found.add(FormativeKind.DEFEAT)
    society = await ctx.session.get(CommunitySocietyRow, town.id)
    if society is not None and society.golden_age_since_epoch is not None:
        found.add(FormativeKind.GOLDEN_AGE)
    if town.world_id is not None and await under_long_season(ctx, town.world_id, ctx.epoch, ctx.epoch):
        found.add(FormativeKind.LONG_SEASON)
    return found


async def under_long_season(ctx: TickContext, world_id: int, first: int, last: int) -> bool:
    spells = await ctx.session.scalars(select(IrregularSeasonRow).where(IrregularSeasonRow.world_id == world_id).order_by(IrregularSeasonRow.id))
    return any(row.spell_started_epoch <= last and first < row.spell_started_epoch + row.spell_length for row in spells)


async def children_of_town(ctx: TickContext, town_id: int) -> int:
    rows = await ctx.session.scalars(select(CohortRow.count).where(CohortRow.community_entity_id == town_id, CohortRow.age_band.in_(sorted(MINOR_BANDS))))
    return sum(rows)


async def people_weight(ctx: TickContext, town: EntityRow, people: EntityRow) -> float:
    return min(1.0, population_of(town) / max(1, stat_or(people, "population", 0)))


async def lean_culture(ctx: TickContext, town: EntityRow, shifts: dict[str, int], share: float) -> None:
    people = await people_of(ctx.session, town)
    if people is None or held(people.id) or not shifts:
        return
    values = dict(await stored_values(ctx.session, ValueHolder.CULTURE, people.id))
    weight = await people_weight(ctx, town, people) * share
    for axis, amount in shifts.items():
        key = ValueAxis(axis)
        values[key] = clamp_int(values.get(key, 0) + amount * weight, -VALUE_SPAN, VALUE_SPAN)
    await write_values(ctx.session, ValueHolder.CULTURE, people.id, values)


async def shape_youth(ctx: TickContext, town: EntityRow, tally: GenerationTally) -> None:
    table = ctx.rules.generations
    start = window_of(ctx.epoch, table.youth_epochs)
    row = await ctx.session.get(GenerationRow, (town.id, start))
    if row is None:
        row = GenerationRow(community_entity_id=town.id, generation_epoch=start, formative=[], value_shifts={}, alive=0, locked=[])
        ctx.session.add(row)
        await ctx.session.flush()
    if "alive" not in row.locked:
        row.alive = await children_of_town(ctx, town.id)
    events = await formative_now(ctx, town)
    if not events or "formative" in row.locked:
        return
    formative = list(row.formative)
    shifts = dict(row.value_shifts)
    for event in sorted(events):
        if event.value in formative:
            continue
        formative.append(event.value)
        mark = table.long_season_mark if event is FormativeKind.LONG_SEASON else table.shift
        for axis, sign in FORMATIVE_SHIFTS[event]:
            shifts[axis.value] = clamp_int(shifts.get(axis.value, 0) + sign * mark, -VALUE_SPAN, VALUE_SPAN)
        tally.shaped += 1
        await record(ctx, "generation.formed", roles={IncidentRole.PLACE: town.id}, facts={"kind": event, "born": start}, place=town.id)
    row.formative = formative
    if "value_shifts" not in row.locked:
        row.value_shifts = shifts


async def come_of_age(ctx: TickContext, town: EntityRow, tally: GenerationTally) -> None:
    table = ctx.rules.generations
    if ctx.epoch % max(1, table.youth_epochs):
        return
    previous = await ctx.session.get(GenerationRow, (town.id, ctx.epoch - table.youth_epochs))
    if previous is None or not previous.value_shifts:
        return
    await lean_culture(ctx, town, previous.value_shifts, 1.0)
    tally.formed += 1
    await record(
        ctx,
        "generations.came_of_age",
        roles={IncidentRole.PLACE: town.id},
        facts={"formative": [FormativeKind(kind) for kind in previous.formative], "born": previous.generation_epoch, "alive": previous.alive},
        place=town.id,
    )


async def pass_on(ctx: TickContext, town: EntityRow, profile: SettlementProfileRow, tally: GenerationTally) -> None:
    table = ctx.rules.generations
    rows = await ctx.session.scalars(
        select(GenerationRow).where(GenerationRow.community_entity_id == town.id, GenerationRow.passed_epoch.is_(None)).order_by(GenerationRow.generation_epoch)
    )
    for row in list(rows):
        age = ctx.epoch - row.generation_epoch - table.youth_epochs
        if age < 0 or row.locked:
            continue
        remaining = table.lifespan_epochs - age
        if remaining <= 0:
            row.alive, row.passed_epoch = 0, ctx.epoch
            share = (PERCENT - table.inherited_pct) / PERCENT
            await lean_culture(ctx, town, {axis: -amount for axis, amount in row.value_shifts.items()}, share)
            shift(profile, "unrest", table.turnover_unrest)
            tally.passed += 1
            if row.formative:
                await record(
                    ctx,
                    "generations.passed",
                    roles={IncidentRole.PLACE: town.id},
                    facts={"formative": [FormativeKind(kind) for kind in row.formative], "born": row.generation_epoch, "unrest": table.turnover_unrest},
                    place=town.id,
                )
        else:
            row.alive = round_half_up(row.alive * remaining / (remaining + 1))


GENERATIONS_FIXUP = "generations.w52"


async def backfill_long_seasons(ctx: TickContext) -> int:
    if await ctx.session.get(AppliedFixupRow, GENERATIONS_FIXUP) is not None:
        return 0
    marked = 0
    span = max(1, ctx.rules.generations.youth_epochs)
    for row in list(await ctx.session.scalars(select(GenerationRow).order_by(GenerationRow.community_entity_id, GenerationRow.generation_epoch))):
        town = await ctx.session.get(EntityRow, row.community_entity_id)
        if town is None or town.world_id is None or held(town.id) or "formative" in row.locked or FormativeKind.LONG_SEASON.value in row.formative:
            continue
        if await under_long_season(ctx, town.world_id, row.generation_epoch, row.generation_epoch + span - 1):
            row.formative = [*row.formative, FormativeKind.LONG_SEASON.value]
            marked += 1
    ctx.session.add(AppliedFixupRow(key=GENERATIONS_FIXUP, result={"generations": marked}))
    await ctx.session.flush()
    return marked


async def keep_generations(ctx: TickContext, tally: GenerationTally) -> None:
    await backfill_long_seasons(ctx)
    for town, profile in await towns(ctx):
        if held(town.id):
            continue
        await shape_youth(ctx, town, tally)
        await come_of_age(ctx, town, tally)
        await pass_on(ctx, town, profile, tally)
    await ctx.session.flush()
