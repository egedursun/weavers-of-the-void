from dataclasses import dataclass, field

from sqlalchemy import select

from aerona.catalog.spread_paths import SPREAD_PATHS
from aerona.constants.units import PERCENT
from aerona.db.tables.bonds import BondRow
from aerona.db.tables.disease import OutbreakRow
from aerona.db.tables.environment import RegionEnvironmentRow
from aerona.db.tables.gatherings import GatheringGuestRow, GatheringRow
from aerona.db.write_guard import held
from aerona.domain.enums.bond import BondKind
from aerona.domain.enums.disease import SpreadPath
from aerona.domain.enums.environment import RiverClass
from aerona.domain.enums.gathering import GatheringStatus
from aerona.domain.enums.modifier import IncidentRole
from aerona.engine.context import TickContext
from aerona.engine.disease.book import DiseaseBook
from aerona.engine.disease.outbreaks import open_outbreak
from aerona.engine.disease.vectors import routes_of
from aerona.engine.environment.geomorph import downhill
from aerona.engine.recording.record import record


@dataclass
class PathTally:
    carried: dict[SpreadPath, int] = field(default_factory=dict)


@dataclass(frozen=True)
class Carry:
    source: OutbreakRow
    region_id: int
    path: SpreadPath
    key: str


def travels_by(book: DiseaseBook, outbreak: OutbreakRow, path: SpreadPath) -> bool:
    profile = book.profiles.get(outbreak.disease_entity_id)
    if profile is None:
        return False
    return any(route in SPREAD_PATHS[path].routes for route, share in routes_of(book, profile) if share > 0)


async def carry(ctx: TickContext, book: DiseaseBook, move: Carry, tally: PathTally) -> None:
    disease = book.diseases.get(move.source.disease_entity_id)
    chance = SPREAD_PATHS[move.path].chance
    if disease is None or chance is None or held(move.region_id) or book.active_of(disease.id, move.region_id) is not None:
        return
    if not travels_by(book, move.source, move.path) or not ctx.rng(f"disease.path.{move.key}.{ctx.epoch}").chance(chance(ctx.rules)):
        return
    severity = max(1, move.source.severity * ctx.rules.spread.carried_severity_pct // PERCENT)
    await open_outbreak(ctx, book, disease, move.region_id, path=move.path, severity=severity, source=move.source)
    tally.carried[move.path] = tally.carried.get(move.path, 0) + 1
    await record(
        ctx,
        "disease.spread",
        roles={IncidentRole.SUBJECT: disease.id, IncidentRole.ORIGIN: move.source.region_entity_id, IncidentRole.PLACE: move.region_id},
        facts={"path": move.path, "severity": severity},
        place=move.region_id,
    )


def sources(book: DiseaseBook) -> list[OutbreakRow]:
    return sorted(book.outbreaks, key=lambda row: row.id)


async def by_waterway(ctx: TickContext, book: DiseaseBook, tally: PathTally) -> None:
    for outbreak in sources(book):
        ground = await ctx.session.get(RegionEnvironmentRow, outbreak.region_entity_id)
        if ground is None or ground.river_class is RiverClass.NONE:
            continue
        neighbours = book.atlas.neighbour_regions(outbreak.region_entity_id)
        grounds = {row.entity_id: row for row in await ctx.session.scalars(select(RegionEnvironmentRow).where(RegionEnvironmentRow.entity_id.in_(neighbours)))}
        lower = [
            region_id for region_id in downhill(book.atlas, grounds, outbreak.region_entity_id) if grounds[region_id].elevation_mean <= ground.elevation_mean
        ]
        if lower:
            await carry(ctx, book, Carry(outbreak, lower[0], SpreadPath.WATERWAY, f"water.{outbreak.id}"), tally)


async def by_wildlife(ctx: TickContext, book: DiseaseBook, tally: PathTally) -> None:
    for outbreak in sources(book):
        hosts = book.hosts.get(outbreak.disease_entity_id, set())
        if not hosts:
            continue
        for region_id in sorted(book.atlas.neighbour_regions(outbreak.region_entity_id)):
            if any(book.ranges.get((species_id, region_id), 0) > 0 for species_id in hosts):
                await carry(ctx, book, Carry(outbreak, region_id, SpreadPath.WILDLIFE, f"wild.{outbreak.id}.{region_id}"), tally)


async def by_migration(ctx: TickContext, book: DiseaseBook, tally: PathTally) -> None:
    moves = await ctx.session.scalars(select(BondRow).where(BondRow.kind == BondKind.MIGRATED_TO, BondRow.epoch == ctx.epoch).order_by(BondRow.id))
    for bond in moves:
        origin, home = book.atlas.top_region(bond.source_node_id), book.atlas.top_region(bond.target_node_id)
        if origin is None or home is None or origin == home:
            continue
        for outbreak in book.outbreaks_in(origin):
            await carry(ctx, book, Carry(outbreak, home, SpreadPath.MIGRATION, f"migrants.{bond.id}.{outbreak.id}"), tally)


async def by_gathering(ctx: TickContext, book: DiseaseBook, tally: PathTally) -> None:
    held_here = await ctx.session.scalars(
        select(GatheringRow).where(GatheringRow.epoch == ctx.epoch, GatheringRow.status == GatheringStatus.HELD).order_by(GatheringRow.id)
    )
    for gathering in held_here:
        place = book.atlas.top_region(gathering.place_entity_id) if gathering.place_entity_id is not None else None
        stricken = book.outbreaks_in(place)
        if not stricken:
            continue
        guests = await ctx.session.scalars(
            select(GatheringGuestRow.node_id)
            .where(GatheringGuestRow.gathering_id == gathering.id, GatheringGuestRow.attended.is_not(False))
            .order_by(GatheringGuestRow.node_id)
        )
        homes = sorted({home for guest in guests if (home := book.atlas.top_region(guest)) is not None and home != place})
        for home in homes:
            for outbreak in stricken:
                await carry(ctx, book, Carry(outbreak, home, SpreadPath.GATHERING, f"crowd.{gathering.id}.{home}.{outbreak.id}"), tally)


async def carry_by_paths(ctx: TickContext) -> PathTally:
    book = await DiseaseBook.load(ctx.session, ctx.rules, ctx.epoch)
    tally = PathTally()
    for step in (by_waterway, by_wildlife, by_migration, by_gathering):
        await step(ctx, book, tally)
    await ctx.session.flush()
    return tally
