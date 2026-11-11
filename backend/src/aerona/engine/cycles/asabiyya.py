from dataclasses import dataclass, field

from sqlalchemy import select

from aerona.constants.units import PERCENT
from aerona.db.tables.cycles import AsabiyyaRow, PolityStressRow
from aerona.db.tables.demography import PeopleCultureRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.society import CommunitySocietyRow
from aerona.db.write_guard import held
from aerona.domain.enums.entity import EntityStatus, EntityType
from aerona.domain.enums.mind import ValueHolder
from aerona.domain.enums.society import SocialClass
from aerona.engine.collective.book import shift
from aerona.engine.context import TickContext
from aerona.engine.cycles.book import at_war, polities, psi_of, put, realm_towns
from aerona.engine.mind.book import Values, stored_values
from aerona.engine.notes import note
from aerona.engine.polity.regard import value_distance
from aerona.engine.primitives.distance import RegionAtlas
from aerona.engine.primitives.folk import homes_of
from aerona.rules.registry import Rules

HALF = PERCENT // 2


@dataclass
class AsabiyyaTally:
    risen: int = 0
    decayed: int = 0
    frontiers: int = 0


async def comfort(ctx: TickContext, town_ids: set[int]) -> float:
    total = 0.0
    weight = 0.0
    for town_id in town_ids:
        society = await ctx.session.get(CommunitySocietyRow, town_id)
        if society is None:
            continue
        for social_class in SocialClass:
            share = float(getattr(society, f"share_{social_class.value}"))
            total += share * int(getattr(society, f"satisfaction_{social_class.value}"))
            weight += share
    return total / weight if weight else 0.0


async def asabiyya_row(ctx: TickContext, holder_id: int) -> AsabiyyaRow:
    row = await ctx.session.get(AsabiyyaRow, holder_id)
    if row is None:
        row = AsabiyyaRow(holder_entity_id=holder_id, value=HALF, updated_epoch=ctx.epoch, locked=[])
        ctx.session.add(row)
    return row


@dataclass
class Frontiers:
    atlas: RegionAtlas
    living: dict[int, set[int]]
    values: dict[int, Values]
    threshold: float = 0.0
    distances: dict[tuple[int, int], int] = field(default_factory=dict)

    def distance(self, first: int, second: int) -> int:
        key = (min(first, second), max(first, second))
        if key not in self.distances:
            self.distances[key] = value_distance(self.values.get(first, {}), self.values.get(second, {}))
        return self.distances[key]

    def strangers(self, region: int, own: set[int]) -> set[int]:
        return {people for near in (region, *self.atlas.neighbours(region)) for people in self.living.get(near, set())} - own

    def measure(self, regions_of: dict[int, set[int]], rules: Rules) -> None:
        table = rules.asabiyya
        pairs = [self.distance(people, other) for people, regions in regions_of.items() for region in regions for other in self.strangers(region, {people})]
        mean = sum(pairs) / len(pairs) if pairs else 0.0
        self.threshold = max(float(table.frontier_floor), mean * table.frontier_ratio_pct / PERCENT)

    def count(self, regions: set[int], own: set[int]) -> int:
        return sum(1 for region in regions if any(self.distance(mine, other) >= self.threshold for other in self.strangers(region, own) for mine in own))


def generation_turned(ctx: TickContext) -> bool:
    span = max(1, ctx.rules.generations.youth_epochs)
    return ctx.epoch % span == 0


async def tend(
    ctx: TickContext, holder: EntityRow, row: AsabiyyaRow, *, frontier: int, war: bool, comfort_level: float, psi: int, tally: AsabiyyaTally
) -> None:
    table = ctx.rules.asabiyya
    put(row, "frontier", frontier, high=10**6)
    put(row, "conflict", row.conflict * (PERCENT - table.conflict_fade) / PERCENT + (PERCENT if war else 0) * table.conflict_rise / PERCENT)
    if generation_turned(ctx):
        put(row, "luxury_generations", row.luxury_generations + 1 if comfort_level >= table.luxury_at else 0, high=10**6)
    gain = min(table.frontier_cap, frontier * table.frontier_gain) + row.conflict * table.conflict_gain / PERCENT
    decay = (table.inland_decay if frontier == 0 else 0) + psi * table.psi_decay / PERCENT
    if row.luxury_generations >= table.luxury_generations:
        decay += table.luxury_decay * (row.luxury_generations - table.luxury_generations + 1)
    before = row.value
    shift(row, "value", gain - decay)
    row.updated_epoch = ctx.epoch
    if row.value > before:
        tally.risen += 1
    elif row.value < before:
        tally.decayed += 1
    if frontier:
        tally.frontiers += 1
    if before < table.surge_at <= row.value:
        await note(ctx, f"The frontier forged {holder.name} into one: its people stand together as never before.", key="asabiyya.surge", ids=[holder.id])
    if before >= table.soft_at > row.value:
        await note(
            ctx, f"Generations of ease have softened {holder.name}; its people no longer hold together as they did.", key="asabiyya.softened", ids=[holder.id]
        )


async def homeland_psi(ctx: TickContext, homes: set[int]) -> int:
    return max([await psi_of(ctx.session, home) for home in sorted(homes)], default=0)


async def keep_asabiyya(ctx: TickContext, tally: AsabiyyaTally) -> None:
    table = ctx.rules.asabiyya
    atlas = await RegionAtlas.load(ctx.session)
    peoples = list(
        await ctx.session.scalars(
            select(EntityRow).where(EntityRow.entity_type == EntityType.PEOPLE, EntityRow.status == EntityStatus.CANON).order_by(EntityRow.id)
        )
    )
    homes = {people.id: await homes_of(ctx.session, people) for people in peoples}
    regions_of = {people_id: {region for home in places if (region := atlas.top_region(home)) is not None} for people_id, places in homes.items()}
    living: dict[int, set[int]] = {}
    for people_id, regions in regions_of.items():
        for region in regions:
            living.setdefault(region, set()).add(people_id)
    frontiers = Frontiers(atlas, living, {people.id: await stored_values(ctx.session, ValueHolder.CULTURE, people.id) for people in peoples})
    frontiers.measure(regions_of, ctx.rules)
    for people in peoples:
        if held(people.id):
            continue
        frontier = frontiers.count(regions_of[people.id], {people.id})
        row = await asabiyya_row(ctx, people.id)
        await tend(
            ctx,
            people,
            row,
            frontier=frontier,
            war=await at_war(ctx, homes[people.id]),
            comfort_level=await comfort(ctx, homes[people.id]),
            psi=await homeland_psi(ctx, homes[people.id]),
            tally=tally,
        )
        culture = await ctx.session.get(PeopleCultureRow, people.id)
        if culture is not None:
            shift(culture, "cohesion", (row.value - HALF) * table.cohesion_pull / PERCENT)
    for polity, _ in await polities(ctx.session):
        if held(polity.id):
            continue
        towns = {town.id for town in await realm_towns(ctx.session, polity.id)}
        regions = {region for town in towns if (region := atlas.top_region(town)) is not None}
        own = {people for region in regions for people in living.get(region, set())}
        frontier = frontiers.count(regions, own)
        stress = await ctx.session.get(PolityStressRow, polity.id)
        row = await asabiyya_row(ctx, polity.id)
        war = await at_war(ctx, {polity.id, *towns})
        await tend(
            ctx, polity, row, frontier=frontier, war=war, comfort_level=await comfort(ctx, towns), psi=stress.psi if stress is not None else 0, tally=tally
        )
