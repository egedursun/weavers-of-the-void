from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.db.tables.ecology import SpeciesProfileRow, SpeciesRangeRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.environment import RegionEnvironmentRow
from aerona.db.tables.evolution import LineageMarkRow
from aerona.db.write_guard import held
from aerona.domain.enums.affliction import PackageKind, Transmission
from aerona.domain.enums.bond import BondKind
from aerona.domain.enums.entity import EntityType
from aerona.engine.body.afflictions import afflict
from aerona.engine.context import TickContext
from aerona.engine.notes import note
from aerona.engine.primitives.queries import active_bonds, canon

BLESSING = PackageKind.DIVINE_BLESSING
TAINT = PackageKind.VOID_TAINT


@dataclass
class LineageTally:
    blessed: int = 0
    tainted: int = 0


async def marks_of(session: AsyncSession, species_id: int) -> list[LineageMarkRow]:
    return list(await session.scalars(select(LineageMarkRow).where(LineageMarkRow.species_entity_id == species_id).order_by(LineageMarkRow.package)))


async def mark(ctx: TickContext, species: EntityRow, package: PackageKind, *, blessing: bool, source_node_id: int | None) -> LineageMarkRow:
    row = await ctx.session.get(LineageMarkRow, (species.id, package))
    if row is None:
        row = LineageMarkRow(species_entity_id=species.id, package=package, blessing=blessing, source_node_id=source_node_id, epoch=ctx.epoch, locked=[])
        ctx.session.add(row)
        await ctx.session.flush()
    return row


async def tainted_lands(ctx: TickContext) -> dict[int, set[int]]:
    leaking = {
        row.entity_id for row in await ctx.session.scalars(select(RegionEnvironmentRow).where(RegionEnvironmentRow.leak >= ctx.rules.lineages.taint_leak))
    }
    found: dict[int, set[int]] = {}
    for row in await ctx.session.scalars(select(SpeciesRangeRow).where(SpeciesRangeRow.abundance > 0, SpeciesRangeRow.region_entity_id.in_(leaking))):
        found.setdefault(row.species_entity_id, set()).add(row.region_entity_id)
    return found


async def mark_lineages(ctx: TickContext, tally: LineageTally) -> None:
    table = ctx.rules.lineages
    tainted = await tainted_lands(ctx)
    for species in await canon(ctx.session, [EntityType.SPECIES]):
        if held(species.id):
            continue
        profile = await ctx.session.get(SpeciesProfileRow, species.id)
        if profile is None:
            continue
        rng = ctx.rng(f"lineage.{species.id}")
        if profile.sacred_to_node_id is not None and await ctx.session.get(LineageMarkRow, (species.id, BLESSING)) is None and rng.chance(table.blessing_pct):
            await mark(ctx, species, BLESSING, blessing=True, source_node_id=profile.sacred_to_node_id)
            tally.blessed += 1
            await note(ctx, f"The line of {species.name} carries a blessing now, from parent to young.", key="ecology.lineage_blessed", ids=[species.id])
        curse = await active_bonds(ctx.session, [BondKind.CURSED], targets=[species.id])
        if curse and await ctx.session.get(LineageMarkRow, (species.id, TAINT)) is None:
            await mark(ctx, species, TAINT, blessing=False, source_node_id=curse[-1].source_node_id)
            tally.tainted += 1
            await note(ctx, f"The curse on {species.name} passes from parent to young.", key="ecology.lineage_cursed", ids=[species.id])
        elif species.id in tainted and await ctx.session.get(LineageMarkRow, (species.id, TAINT)) is None and rng.chance(table.taint_pct):
            await mark(ctx, species, TAINT, blessing=False, source_node_id=None)
            tally.tainted += 1
            await note(
                ctx, f"The line of {species.name} is tainted by the leaking land, from parent to young.", key="ecology.lineage_tainted", ids=[species.id]
            )


async def pass_to_beast(ctx: TickContext, beast: EntityRow, species_id: int | None) -> int:
    if species_id is None:
        return 0
    given = 0
    for row in await marks_of(ctx.session, species_id):
        if await afflict(ctx, beast, row.package, Transmission.BIRTH, source_node_id=row.source_node_id) is not None:
            given += 1
    return given
