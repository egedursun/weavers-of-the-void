from sqlalchemy import select

from aerona.db.tables.entities import EntityRow
from aerona.db.tables.mind import MemoryRow
from aerona.db.tables.mortal import MortalProfileRow
from aerona.db.tables.relations import RelationshipRow
from aerona.domain.enums.mind import MemoryKind, TraitKind
from aerona.domain.enums.relations import PassionKind, PassionSource
from aerona.engine.context import TickContext
from aerona.engine.mind.book import traits_of
from aerona.engine.primitives.stats import stat_or

Found = dict[tuple[PassionKind, int], tuple[int, PassionSource]]
MEMORY_PASSIONS = {
    MemoryKind.LAMENTED: PassionKind.GRIEF,
    MemoryKind.DREADS: PassionKind.FEAR,
    MemoryKind.HUMILIATED_ME: PassionKind.SHAME,
    MemoryKind.ENVIED: PassionKind.ENVY,
    MemoryKind.TAUGHT_ME: PassionKind.ADMIRATION,
}


def keep(found: Found, key: tuple[PassionKind, int], strength: int, source: PassionSource) -> None:
    if strength > found.get(key, (0, source))[0]:
        found[key] = (strength, source)


async def from_feelings(ctx: TickContext, mortal: EntityRow, found: Found) -> None:
    table = ctx.rules.passions
    at = table.relation_at
    for row in await ctx.session.scalars(select(RelationshipRow).where(RelationshipRow.holder_node_id == mortal.id)):
        if row.romance >= table.obsession_at:
            keep(found, (PassionKind.OBSESSION, row.subject_node_id), row.romance, PassionSource.RELATIONSHIP)
        if row.romance >= at and row.rivalry >= at:
            keep(found, (PassionKind.JEALOUSY, row.subject_node_id), row.rivalry, PassionSource.RELATIONSHIP)
        elif row.rivalry >= at:
            keep(found, (PassionKind.ENVY, row.subject_node_id), row.rivalry, PassionSource.RELATIONSHIP)
        if row.friendship >= at and row.familiarity >= at:
            subject = await ctx.session.get(EntityRow, row.subject_node_id)
            if subject is not None and stat_or(subject, "renown", 0) >= table.admired_renown:
                keep(found, (PassionKind.ADMIRATION, subject.id), row.friendship, PassionSource.RELATIONSHIP)
    for memory in await ctx.session.scalars(
        select(MemoryRow).where(MemoryRow.holder_node_id == mortal.id, MemoryRow.kind.in_(list(MEMORY_PASSIONS)), MemoryRow.subject_node_id.is_not(None))
    ):
        if memory.subject_node_id is not None and abs(memory.magnitude) >= table.memory_at:
            keep(found, (MEMORY_PASSIONS[memory.kind], memory.subject_node_id), abs(memory.magnitude), PassionSource.MEMORY)
    await from_temper(ctx, mortal, found)


async def from_temper(ctx: TickContext, mortal: EntityRow, found: Found) -> None:
    traits = await traits_of(ctx.session, mortal.id)
    profile = await ctx.session.get(MortalProfileRow, mortal.id)
    strength = ctx.rules.passions.temper_strength
    if TraitKind.AMBITIOUS in traits and profile is not None and profile.polity_id is not None:
        keep(found, (PassionKind.AMBITION, profile.polity_id), strength, PassionSource.UPBRINGING)
    if TraitKind.PROUD in traits and mortal.location_id is not None:
        keep(found, (PassionKind.PRIDE, mortal.location_id), strength, PassionSource.UPBRINGING)
    if TraitKind.CURIOUS in traits and mortal.world_id is not None:
        world_place = mortal.location_id
        if world_place is not None:
            keep(found, (PassionKind.CURIOSITY, world_place), strength, PassionSource.UPBRINGING)
