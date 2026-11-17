from sqlalchemy import select

from aerona.constants.units import PERCENT
from aerona.db.repositories.entities import EntityRepository
from aerona.db.tables.bonds import BondRow
from aerona.db.tables.culture import TraditionProfileRow
from aerona.db.tables.ecology import SpeciesProfileRow, SpeciesRangeRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.sons import SonRow
from aerona.domain.enums.bond import BondKind, BondState
from aerona.domain.enums.culture import TraditionFunction
from aerona.domain.enums.domain import Domain
from aerona.domain.enums.ecology import SIZE_ORDER, SizeClass
from aerona.domain.enums.entity import EntityStatus, EntityType
from aerona.domain.enums.society import CreatureTrait
from aerona.domain.models.entity_stats import TraditionStats
from aerona.engine.context import TickContext
from aerona.engine.lore.traditions import cost_for
from aerona.engine.notes import note
from aerona.engine.primitives.distance import RegionAtlas
from aerona.engine.primitives.queries import canon, close, connect
from aerona.engine.primitives.records import RecordSpec, create_record

GRAND = SIZE_ORDER.index(SizeClass.LARGE)


async def totem_of(ctx: TickContext, people_id: int) -> int | None:
    kept = select(BondRow.target_node_id).where(BondRow.source_node_id == people_id, BondRow.kind == BondKind.CELEBRATES, BondRow.state == BondState.ACTIVE)
    origins = select(TraditionProfileRow.origin_entity_id).where(TraditionProfileRow.tradition_entity_id.in_(kept))
    return await ctx.session.scalar(select(EntityRow.id).where(EntityRow.id.in_(origins), EntityRow.entity_type == EntityType.SPECIES).limit(1))


async def found_totem(ctx: TickContext, people: EntityRow, species: EntityRow) -> EntityRow:
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
            kind=TraditionFunction.FESTIVAL,
            calendar_slot=None,
            cost=cost_for(ctx, TraditionFunction.FESTIVAL),
            effects={},
            taboo_target=None,
            origin_entity_id=species.id,
            updated_epoch=ctx.epoch,
            locked=[],
        )
    )
    await connect(ctx.session, people.id, tradition.id, BondKind.CELEBRATES, ctx.epoch, description="their totem")
    await connect(ctx.session, tradition.id, species.id, BondKind.TELLS_OF, ctx.epoch, description="the totem")
    return tradition


async def drop_totem(ctx: TickContext, people_id: int) -> int:
    kept = await ctx.session.scalars(
        select(BondRow).where(BondRow.source_node_id == people_id, BondRow.kind == BondKind.CELEBRATES, BondRow.state == BondState.ACTIVE)
    )
    dropped = 0
    for bond in list(kept):
        profile = await ctx.session.get(TraditionProfileRow, bond.target_node_id)
        origin = await ctx.session.get(EntityRow, profile.origin_entity_id) if profile is not None and profile.origin_entity_id is not None else None
        if origin is not None and origin.entity_type is EntityType.SPECIES:
            await close(ctx.session, bond, ctx.epoch, "the totem was set aside")
            dropped += 1
    return dropped


async def hunt_gods(ctx: TickContext) -> int:
    linked = 0
    for son in list(await ctx.session.scalars(select(SonRow).order_by(SonRow.id))):
        if not son.alive or Domain.HUNT not in son.domains:
            continue
        keepers = await ctx.session.scalars(
            select(BondRow.source_node_id).where(BondRow.target_node_id == son.id, BondRow.kind == BondKind.WORSHIPS, BondRow.state == BondState.ACTIVE)
        )
        for keeper in sorted(set(keepers)):
            totem = await totem_of(ctx, keeper)
            profile = await ctx.session.get(SpeciesProfileRow, totem) if totem is not None else None
            if profile is None or profile.sacred_to_node_id is not None or "sacred_to_node_id" in profile.locked:
                continue
            profile.sacred_to_node_id = son.id
            await EntityRepository(ctx.session).add_trait(profile.species_entity_id, CreatureTrait.SACRED_ANIMAL)
            species = await ctx.session.get(EntityRow, profile.species_entity_id)
            await note(
                ctx,
                f"{son.name} of the Hunt was seen wearing the head of the {species.name if species else 'beast'}; its kind is holy to the god.",
                key="ecology.animal_god",
                ids=[profile.species_entity_id],
                son_id=son.id,
            )
            linked += 1
    return linked


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
        await found_totem(ctx, people, species)
        adopted += 1
    return adopted
