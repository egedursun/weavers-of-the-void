from collections import Counter
from itertools import pairwise

from sqlalchemy import select

from aerona.constants.units import PERCENT
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.interconnect import IncidentRow
from aerona.db.tables.lore import ChronicleRow
from aerona.db.tables.storyteller import StorytellerRow
from aerona.db.tables.storyteller_depth import RegionalTensionRow, SubsystemTensionRow
from aerona.domain.enums.chronicle import ChronicleKind
from aerona.domain.enums.entity import EntityType
from aerona.domain.enums.modifier import IncidentRole
from aerona.domain.enums.storyteller import StorytellerProfile
from aerona.engine.context import TickContext
from aerona.engine.primitives.numbers import clamp_int
from aerona.engine.recording.record import record as record_incident
from aerona.rules.registry import Rules

HOPS = 4
TENSE_KINDS = frozenset(
    {
        ChronicleKind.WAR,
        ChronicleKind.WAR_OF_GODS,
        ChronicleKind.ARMY,
        ChronicleKind.DEATH,
        ChronicleKind.DISASTER,
        ChronicleKind.REBELLION,
        ChronicleKind.HORROR,
        ChronicleKind.OUTER_BEING,
        ChronicleKind.APOCALYPSE,
        ChronicleKind.INTRIGUE,
    }
)


def along_curve(points: list[list[int]], epoch: int) -> int | None:
    ordered = sorted((int(point[0]), int(point[1])) for point in points if len(point) == 2)
    if not ordered:
        return None
    if epoch <= ordered[0][0]:
        return clamp_int(ordered[0][1], 0, PERCENT)
    for (start, low), (end, high) in pairwise(ordered):
        if start <= epoch <= end:
            span = max(1, end - start)
            return clamp_int(low + (high - low) * (epoch - start) // span, 0, PERCENT)
    return clamp_int(ordered[-1][1], 0, PERCENT)


def deeper_aim(rules: Rules, row: StorytellerRow, epoch: int) -> int | None:
    table = rules.storyteller_depth
    shaped = along_curve(row.target_points or [], epoch)
    if shaped is not None:
        return shaped
    if row.profile is StorytellerProfile.SLOW_BURN:
        return clamp_int(table.slow_burn_step * epoch, 0, PERCENT)
    if row.profile is StorytellerProfile.EPISODIC:
        return table.episode_peak if (epoch + row.cycle_offset) % table.episode_epochs == table.episode_epochs - 1 else rules.storyteller.steady_target // 2
    return None


async def region_of(ctx: TickContext, place_id: int | None) -> int | None:
    for _ in range(HOPS):
        place = await ctx.session.get(EntityRow, place_id) if place_id is not None else None
        if place is None:
            return None
        if place.entity_type is EntityType.REGION:
            return place.id
        place_id = place.location_id
    return None


async def measure_parts(ctx: TickContext, world_id: int) -> int:
    scale = ctx.rules.storyteller.tension_scale
    carry = ctx.rules.storyteller.tension_carry_pct
    by_region: Counter[int] = Counter()
    by_subsystem: Counter[str] = Counter()
    for kind, place, magnitude, told in await ctx.session.execute(
        select(IncidentRow.kind, IncidentRow.place_entity_id, IncidentRow.magnitude, ChronicleRow.kind)
        .outerjoin(ChronicleRow, ChronicleRow.id == IncidentRow.chronicle_id)
        .where(IncidentRow.epoch == ctx.epoch, IncidentRow.world_id == world_id)
    ):
        by_subsystem[str(kind).split(".", 1)[0]] += int(magnitude)
        found = await region_of(ctx, place) if told in TENSE_KINDS else None
        if found is not None:
            by_region[found] += int(magnitude)
    crises = 0
    measured = {row.region_entity_id: row for row in await ctx.session.scalars(select(RegionalTensionRow).where(RegionalTensionRow.world_id == world_id))}
    for region_id in sorted(set(by_region) | set(measured)):
        row = measured.get(region_id) or await ctx.session.get(RegionalTensionRow, region_id)
        if row is None:
            row = RegionalTensionRow(region_entity_id=region_id, world_id=world_id, locked=[])
            ctx.session.add(row)
        if "tension" not in row.locked:
            row.tension = clamp_int(row.tension * carry // PERCENT + by_region[region_id] * PERCENT // scale, 0, PERCENT)
        was = row.crisis
        row.crisis, row.updated_epoch = row.tension >= ctx.rules.storyteller_depth.region_crisis_at, ctx.epoch
        if row.crisis and not was:
            await record_incident(ctx, "storyteller.region_crisis", roles={IncidentRole.SUBJECT: region_id}, facts={"tension": row.tension}, place=region_id)
        crises += row.crisis
    known = {row.subsystem: row for row in await ctx.session.scalars(select(SubsystemTensionRow).where(SubsystemTensionRow.world_id == world_id))}
    for subsystem in sorted(set(known) | set(by_subsystem)):
        weight = by_subsystem[subsystem]
        part = known.get(subsystem)
        if part is None:
            part = SubsystemTensionRow(world_id=world_id, subsystem=subsystem, locked=[])
            ctx.session.add(part)
        if "tension" not in part.locked:
            part.tension = clamp_int(part.tension * carry // PERCENT + weight * PERCENT // scale, 0, PERCENT)
        part.updated_epoch = ctx.epoch
    return crises
