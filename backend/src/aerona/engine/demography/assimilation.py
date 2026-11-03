from aerona.db.tables.demography import PeopleCultureRow
from aerona.db.tables.entities import EntityRow
from aerona.domain.enums.bond import BondKind
from aerona.domain.enums.chronicle import ChronicleKind
from aerona.domain.enums.entity import EntityStatus, EntityType
from aerona.engine.body.customs import culture_of
from aerona.engine.context import TickContext
from aerona.engine.interconnect.flows import FlowCategory, flowing
from aerona.engine.mind.space import value_distance
from aerona.engine.notes import note
from aerona.engine.primitives.distance import RegionAtlas
from aerona.engine.primitives.queries import active_bonds, canon, connect
from aerona.engine.primitives.records import retire_in
from aerona.engine.primitives.stats import headcount_bounds, set_stats, stat

ASSIMILATION_CAP = 1


async def tongues(ctx: TickContext, entity_id: int) -> set[int]:
    return {bond.target_node_id for bond in await active_bonds(ctx.session, [BondKind.SPEAKS], sources=[entity_id])}


async def absorber_for(ctx: TickContext, atlas: RegionAtlas, people: EntityRow, peoples: list[EntityRow]) -> EntityRow | None:
    table = ctx.rules.peoples
    home = atlas.top_region(people.id)
    if home is None:
        return None
    near = {home, *atlas.neighbour_regions(home)}
    spoken = await tongues(ctx, people.id)
    values = await culture_of(ctx.session, people.id)
    best: EntityRow | None = None
    for other in peoples:
        if other.id == people.id or atlas.top_region(other.id) not in near:
            continue
        if not spoken & await tongues(ctx, other.id):
            continue
        if value_distance(values, await culture_of(ctx.session, other.id)) >= table.assimilation_distance:
            continue
        if (stat(other, "population") or 0) <= (stat(people, "population") or 0):
            continue
        if best is None or (stat(other, "population") or 0) > (stat(best, "population") or 0):
            best = other
    return best


async def assimilate(ctx: TickContext) -> int:
    table = ctx.rules.peoples
    atlas = await RegionAtlas.load(ctx.session)
    peoples = await canon(ctx.session, [EntityType.PEOPLE])
    merged = 0
    for people in sorted(peoples, key=lambda item: (stat(item, "population") or 0, item.id)):
        if merged >= ASSIMILATION_CAP or people.status is not EntityStatus.CANON:
            break
        culture = await ctx.session.get(PeopleCultureRow, people.id)
        if culture is None or culture.cohesion >= table.assimilation_cohesion:
            continue
        absorber = await absorber_for(ctx, atlas, people, peoples)
        if absorber is None:
            continue
        moving = stat(people, "population") or 0
        _, cap = headcount_bounds(ctx.rules, absorber)
        with flowing(FlowCategory.MERGE):
            set_stats(absorber, population=min(cap, (stat(absorber, "population") or 0) + moving))
            set_stats(people, population=0)
        for bond in await active_bonds(ctx.session, [BondKind.DESCENDS_FROM], targets=[people.id]):
            await connect(ctx.session, bond.source_node_id, absorber.id, BondKind.DESCENDS_FROM, ctx.epoch, description="absorbed")
        await connect(ctx.session, people.id, absorber.id, BondKind.DESCENDS_FROM, ctx.epoch, description="assimilated into")
        await retire_in(ctx, people, f"assimilated into {absorber.name}", status=EntityStatus.DESTROYED)
        merged += 1
        await note(
            ctx,
            f"{people.name}, weakened and speaking the same tongue, slowly became {absorber.name}; their name survives only in old songs.",
            key="peoples.assimilated",
            ids=[people.id, absorber.id],
            kind=ChronicleKind.CULTURE,
        )
    return merged
