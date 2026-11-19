from dataclasses import dataclass
from types import MappingProxyType

from sqlalchemy import select

from aerona.constants.units import PER_MILLE, PERCENT
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.gardens import GardenRow
from aerona.db.tables.museums import MuseumCollectionRow
from aerona.db.tables.orders import TouristFlowRow
from aerona.db.tables.settlement import SettlementProfileRow
from aerona.db.tables.sites import BattlefieldFeatureRow
from aerona.db.tables.structures import StructureProfileRow
from aerona.db.write_guard import held
from aerona.domain.enums.disease import OutbreakStatus, SpreadPath
from aerona.domain.enums.entity import EntityStatus, EntityType
from aerona.domain.enums.orders import TouristSight
from aerona.domain.enums.settlement import SizeTier
from aerona.domain.enums.structure import STANDING_STATES, StructureKind
from aerona.engine.context import TickContext
from aerona.engine.disease.book import DiseaseBook
from aerona.engine.disease.outbreaks import open_outbreak
from aerona.engine.economy.convoys import carry_culture
from aerona.engine.economy.purse import receive_coin
from aerona.engine.primitives.distance import RegionAtlas
from aerona.engine.primitives.naming import seed_of
from aerona.engine.primitives.numbers import round_half_up
from aerona.engine.primitives.stats import shift_stat, stat_or

SIGHT_KINDS: MappingProxyType[StructureKind, TouristSight] = MappingProxyType(
    {
        StructureKind.WONDER: TouristSight.WONDER,
        StructureKind.BATHHOUSE: TouristSight.BATHS,
        StructureKind.TEMPLE: TouristSight.SACRED,
        StructureKind.SHRINE: TouristSight.SACRED,
        StructureKind.MONASTERY: TouristSight.SACRED,
    }
)
GREAT_CITIES = (SizeTier.CITY, SizeTier.METROPOLIS, SizeTier.MEGALOPOLIS, SizeTier.WORLD_CITY)
SICK_SEVERITY = 20


@dataclass(frozen=True)
class Sight:
    entity: EntityRow
    kind: TouristSight
    host_id: int
    draw: int = 0


@dataclass
class TourismTally:
    flows: int = 0
    visitors: int = 0
    income: int = 0
    carried: int = 0
    sickened: int = 0


async def sights_of(ctx: TickContext, world_id: int) -> list[Sight]:
    found: list[Sight] = []
    rows = await ctx.session.execute(
        select(EntityRow, StructureProfileRow)
        .join(StructureProfileRow, StructureProfileRow.structure_entity_id == EntityRow.id)
        .where(
            EntityRow.world_id == world_id,
            EntityRow.status == EntityStatus.CANON,
            StructureProfileRow.kind.in_(list(SIGHT_KINDS)),
            StructureProfileRow.construction_state.in_(list(STANDING_STATES)),
            StructureProfileRow.host_entity_id.is_not(None),
        )
        .order_by(EntityRow.id)
    )
    for work, profile in rows.all():
        if profile.host_entity_id is not None:
            found.append(Sight(work, SIGHT_KINDS[profile.kind], profile.host_entity_id))
    marked = select(BattlefieldFeatureRow.place_entity_id).distinct()
    fields = await ctx.session.scalars(
        select(EntityRow).where(EntityRow.id.in_(marked), EntityRow.world_id == world_id, EntityRow.status == EntityStatus.CANON).order_by(EntityRow.id)
    )
    for site in fields:
        host = site if site.entity_type is EntityType.SETTLEMENT else await ctx.session.get(EntityRow, site.location_id or 0)
        if host is not None and host.entity_type is EntityType.SETTLEMENT:
            found.append(Sight(site, TouristSight.BATTLEFIELD, host.id))
    cities = await ctx.session.scalars(
        select(EntityRow)
        .join(SettlementProfileRow, SettlementProfileRow.settlement_entity_id == EntityRow.id)
        .where(EntityRow.world_id == world_id, EntityRow.status == EntityStatus.CANON, SettlementProfileRow.size_tier.in_(list(GREAT_CITIES)))
        .order_by(EntityRow.id)
    )
    found.extend(Sight(city, TouristSight.CITY, city.id) for city in cities)
    for hoard, keeper in await ctx.session.execute(
        select(MuseumCollectionRow, EntityRow)
        .join(EntityRow, EntityRow.id == MuseumCollectionRow.keeper_entity_id)
        .where(EntityRow.world_id == world_id, EntityRow.status == EntityStatus.CANON, EntityRow.entity_type == EntityType.SETTLEMENT)
        .order_by(MuseumCollectionRow.id)
    ):
        if hoard.prestige > 0:
            found.append(Sight(keeper, TouristSight.COLLECTION, keeper.id, hoard.prestige))
    for garden, town in await ctx.session.execute(
        select(GardenRow, EntityRow)
        .join(EntityRow, EntityRow.id == GardenRow.settlement_entity_id)
        .where(EntityRow.world_id == world_id, EntityRow.status == EntityStatus.CANON)
        .order_by(GardenRow.id)
    ):
        if garden.condition > 0:
            found.append(Sight(town, TouristSight.GARDEN, town.id, garden.condition // 2))
    return found


def renown_of(sight: Sight) -> int:
    return stat_or(sight.entity, "renown", 0) + stat_or(sight.entity, "splendor", 0) + stat_or(sight.entity, "prestige", 0) + sight.draw


async def spread_sickness(ctx: TickContext, book: DiseaseBook, atlas: RegionAtlas, host: EntityRow, origin: EntityRow) -> bool:
    there, home = atlas.top_region(host.id), atlas.top_region(origin.id)
    if there is None or home is None or there == home:
        return False
    for outbreak in book.outbreaks:
        disease = book.diseases.get(outbreak.disease_entity_id)
        if disease is not None and outbreak.region_entity_id == there and outbreak.status is not OutbreakStatus.ENDED:
            await open_outbreak(ctx, book, disease, home, path=SpreadPath.JOURNEY, severity=SICK_SEVERITY, source=outbreak)
            return True
    return False


async def travel(ctx: TickContext, origin: EntityRow, sight: Sight, tally: TourismTally, *, book: DiseaseBook, atlas: RegionAtlas) -> None:
    table = ctx.rules.tourism
    host = await ctx.session.get(EntityRow, sight.host_id)
    if host is None or host.status is not EntityStatus.CANON or held(host.id, sight.entity.id):
        return
    visitors = max(1, round_half_up(table.visitors * stat_or(origin, "population", 0) / PER_MILLE))
    income = visitors * table.spend
    ctx.session.add(
        TouristFlowRow(
            origin_entity_id=origin.id, sight_entity_id=sight.entity.id, sight=sight.kind, visitors=visitors, income=income, epoch=ctx.epoch, locked=[]
        )
    )
    await receive_coin(ctx.session, ctx.rules, host, income)
    for key in ("renown", "splendor", "prestige"):
        if key in (sight.entity.stats or {}):
            shift_stat(sight.entity, key, max(1, visitors * table.renown // PERCENT), 0)
            break
    rng = ctx.rng(seed_of("tourism", origin.id, sight.entity.id, ctx.epoch))
    if rng.chance(table.word_chance):
        await carry_culture(ctx, host, origin)
        tally.carried += 1
    if rng.chance(table.sickness_chance) and await spread_sickness(ctx, book, atlas, host, origin):
        tally.sickened += 1
    tally.flows += 1
    tally.visitors += visitors
    tally.income += income


async def keep_tourism(ctx: TickContext, tally: TourismTally) -> None:
    table = ctx.rules.tourism
    towns = list(
        await ctx.session.scalars(
            select(EntityRow).where(EntityRow.entity_type == EntityType.SETTLEMENT, EntityRow.status == EntityStatus.CANON).order_by(EntityRow.id)
        )
    )
    wealthy = [town for town in towns if stat_or(town, "prosperity", 0) >= table.wealthy_from and not held(town.id)]
    if not wealthy:
        return
    book = await DiseaseBook.load(ctx.session, ctx.rules, ctx.epoch)
    atlas = await RegionAtlas.load(ctx.session)
    sights: dict[int, list[Sight]] = {}
    for origin in wealthy:
        if origin.world_id not in sights:
            sights[origin.world_id] = await sights_of(ctx, origin.world_id)
        abroad = [sight for sight in sights[origin.world_id] if sight.host_id != origin.id]
        best = max(abroad, key=lambda sight: (renown_of(sight), -sight.entity.id), default=None)
        if best is not None:
            await travel(ctx, origin, best, tally, book=book, atlas=atlas)
    await ctx.session.flush()
