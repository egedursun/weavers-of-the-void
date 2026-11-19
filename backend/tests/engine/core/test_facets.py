from dataclasses import replace

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.catalog.facets import FACETS
from aerona.db.tables.culture import HolderTechniqueRow
from aerona.db.tables.facets import FacetPracticeRow
from aerona.db.tables.interconnect import IncidentRow
from aerona.db.write_guard import HELD_SCOPE, HeldScope
from aerona.domain.enums.culture import Technique
from aerona.domain.enums.facets import FacetKind
from aerona.engine.context import TickContext
from aerona.engine.facets.practice import FacetTally, keep_facets
from aerona.engine.primitives.stats import stat
from tests.engine.core.factories import CoreWorld, settlement, tuned_rules


def quick(ctx: TickContext) -> TickContext:
    return replace(ctx, environment=replace(ctx.environment, rules=tuned_rules(facets={"drift_pct": 100})))


async def practice(session: AsyncSession, community_id: int, facet: FacetKind) -> FacetPracticeRow | None:
    found: FacetPracticeRow | None = await session.scalar(
        select(FacetPracticeRow).where(FacetPracticeRow.community_entity_id == community_id, FacetPracticeRow.facet == facet)
    )
    return found


def test_every_facet_has_a_source_and_acts_on_its_community() -> None:
    assert len(FACETS) == len(FacetKind)
    assert all(spec.groups > 0 and spec.effects for spec in FACETS.values())


async def test_a_known_technique_roots_its_practice_which_then_raises_its_town(session: AsyncSession, world: CoreWorld, ctx: TickContext) -> None:
    town = await settlement(session, "Ardun", world, world.regions[0])
    session.add(HolderTechniqueRow(holder_entity_id=town.id, technique=Technique.CROP_ROTATION, since_epoch=0, secret=False))
    await session.flush()
    before = stat(town, "prosperity") or 0
    tally = FacetTally()
    await keep_facets(quick(ctx), tally)
    row = await practice(session, town.id, FacetKind.AGRICULTURAL_SCIENCE)
    assert row is not None and row.level == 100 and tally.rooted >= 1
    assert (stat(town, "prosperity") or 0) > before
    rooted = await session.scalar(select(IncidentRow.id).where(IncidentRow.kind == "facets.took_root"))
    assert rooted is not None


async def test_a_held_level_stays_and_a_held_community_is_left_alone(session: AsyncSession, world: CoreWorld, ctx: TickContext) -> None:
    town = await settlement(session, "Bryn", world, world.regions[0])
    other = await settlement(session, "Cael", world, world.regions[0])
    session.add_all(
        [
            FacetPracticeRow(community_entity_id=town.id, facet=FacetKind.LOGIC, level=30, locked=["level"]),
            HolderTechniqueRow(holder_entity_id=other.id, technique=Technique.LOGIC, since_epoch=0, secret=False),
        ]
    )
    await session.flush()
    token = HELD_SCOPE.set(HeldScope(None, frozenset({other.id})))
    try:
        await keep_facets(quick(ctx), FacetTally())
    finally:
        HELD_SCOPE.reset(token)
    kept = await practice(session, town.id, FacetKind.LOGIC)
    assert kept is not None and kept.level == 30
    assert await practice(session, other.id, FacetKind.LOGIC) is None
