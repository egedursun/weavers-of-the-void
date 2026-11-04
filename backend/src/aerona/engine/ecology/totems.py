from sqlalchemy import select

from aerona.constants.units import PERCENT
from aerona.db.tables.bonds import BondRow
from aerona.db.tables.culture import TraditionProfileRow
from aerona.db.tables.ecology import SpeciesProfileRow, SpeciesRangeRow
from aerona.db.tables.entities import EntityRow
from aerona.domain.enums.bond import BondKind, BondState
from aerona.domain.enums.culture import TraditionKind
from aerona.domain.enums.ecology import SIZE_ORDER, SizeClass
from aerona.domain.enums.entity import EntityStatus, EntityType
from aerona.domain.models.entity_stats import TraditionStats
from aerona.engine.context import TickContext
from aerona.engine.lore.traditions import cost_for
from aerona.engine.primitives.distance import RegionAtlas
from aerona.engine.primitives.queries import canon, connect
from aerona.engine.primitives.records import RecordSpec, create_record

GRAND = SIZE_ORDER.index(SizeClass.LARGE)


async def totem_of(ctx: TickContext, people_id: int) -> int | None:
    kept = select(BondRow.target_node_id).where(BondRow.source_node_id == people_id, BondRow.kind == BondKind.CELEBRATES, BondRow.state == BondState.ACTIVE)
    origins = select(TraditionProfileRow.origin_entity_id).where(TraditionProfileRow.tradition_entity_id.in_(kept))
    return await ctx.session.scalar(select(EntityRow.id).where(EntityRow.id.in_(origins), EntityRow.entity_type == EntityType.SPECIES).limit(1))


async def adopt_totems(ctx: TickContext) -> int:
    atlas = await RegionAtlas.load(ctx.session)
    adopted = 0
    for people in await canon(ctx.session, [EntityType.PEOPLE]):
        region = atlas.top_region(people.id)
        if region is None or await totem_of(ctx, people.id) is not None:
            continue
        if not ctx.rng(f"totem.{people.id}.{ctx.epoch}").chance(ctx.rules.totems.chance):
            continue
        rows = await ctx.session.execute(
            select(SpeciesRangeRow.species_entity_id, SpeciesProfileRow.size_class)
            .join(SpeciesProfileRow, SpeciesProfileRow.species_entity_id == SpeciesRangeRow.species_entity_id)
            .where(SpeciesRangeRow.region_entity_id == region, SpeciesRangeRow.abundance >= ctx.rules.totems.abundance)
            .order_by(SpeciesRangeRow.abundance.desc())
        )
        choice = next((species_id for species_id, size in rows if SIZE_ORDER.index(size) >= GRAND), None)
        species = await ctx.session.get(EntityRow, choice) if choice is not None else None
        if species is None or species.status is not EntityStatus.CANON:
            continue
        tradition = await create_record(
            ctx,
            RecordSpec(
                name=f"The Feast of the {species.name}",
                entity_type=EntityType.TRADITION,
                stats=TraditionStats(spread=PERCENT // 5, rigidity=PERCENT // 3),
                body=f"The {people.name} hold {species.name} as their emblem and will not hunt it.",
                power=2,
                world_id=people.world_id,
                location_id=people.location_id,
            ),
        )
        ctx.session.add(
            TraditionProfileRow(
                tradition_entity_id=tradition.id,
                kind=TraditionKind.FESTIVAL,
                calendar_slot=None,
                cost=cost_for(ctx, TraditionKind.FESTIVAL),
                effects={},
                taboo_target=None,
                origin_entity_id=species.id,
                updated_epoch=ctx.epoch,
                locked=[],
            )
        )
        await connect(ctx.session, people.id, tradition.id, BondKind.CELEBRATES, ctx.epoch, description="their totem")
        await connect(ctx.session, tradition.id, species.id, BondKind.TELLS_OF, ctx.epoch, description="the totem")
        adopted += 1
    return adopted
