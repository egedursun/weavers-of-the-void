from sqlalchemy import func, select

from aerona.catalog import god_lines
from aerona.constants.units import PERCENT
from aerona.db.repositories.names import NameRepository
from aerona.db.tables.bonds import BondRow
from aerona.db.tables.ecology import BeastProfileRow, SpeciesRangeRow, SpeciesYieldRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.sons import SonRow
from aerona.domain.enums.bond import BondKind, BondState
from aerona.domain.enums.ecology import SizeClass
from aerona.domain.enums.economy import GoodsFlow
from aerona.domain.enums.entity import EntityStatus, EntityType
from aerona.domain.enums.transform import TransformKind, TransformTrigger
from aerona.domain.models.entity_stats import PlaceStats, SpeciesStats, SpiritStats
from aerona.engine.context import TickContext
from aerona.engine.economy.stocks import GoodsLedger
from aerona.engine.primitives.numbers import clamp_percent
from aerona.engine.primitives.queries import canon, top_region
from aerona.engine.primitives.records import RecordSpec
from aerona.engine.primitives.stats import stat_or
from aerona.engine.transform.ledger import Ledger
from aerona.engine.transform.moves import bind, make
from aerona.engine.transform.record import blocked, record_transformation

Push = tuple[int, TransformTrigger]


async def offspring_of(ctx: TickContext, beast_id: int) -> int:
    found = await ctx.session.scalar(
        select(func.count())
        .select_from(BondRow)
        .where(BondRow.source_node_id == beast_id, BondRow.kind == BondKind.PARENT_OF, BondRow.state == BondState.ACTIVE)
    )
    return int(found or 0)


async def god_touched(ctx: TickContext, beast_id: int) -> bool:
    found = await ctx.session.scalar(
        select(BondRow.id).where(
            BondRow.target_node_id == beast_id,
            BondRow.kind == BondKind.BLESSED,
            BondRow.state == BondState.ACTIVE,
            BondRow.source_node_id.in_(select(SonRow.id)),
        )
    )
    return found is not None


async def founded(ctx: TickContext, beast_id: int) -> bool:
    found = await ctx.session.scalar(
        select(BondRow.id)
        .join(EntityRow, EntityRow.id == BondRow.source_node_id)
        .where(BondRow.target_node_id == beast_id, BondRow.kind == BondKind.DESCENDS_FROM, EntityRow.entity_type == EntityType.SPECIES)
    )
    return found is not None


async def progenitor_pressures(ctx: TickContext) -> dict[int, Push]:
    need = ctx.rules.transform.progenitor_offspring
    found: dict[int, Push] = {}
    for beast in await canon(ctx.session, [EntityType.BEAST]):
        if await founded(ctx, beast.id):
            continue
        if await offspring_of(ctx, beast.id) >= need or await god_touched(ctx, beast.id):
            found[beast.id] = (PERCENT, TransformTrigger.ENGINE)
    return found


async def beast_check(ctx: TickContext, beast_id: int) -> str | None:
    beast = await ctx.session.get(EntityRow, beast_id)
    if beast is None or beast.entity_type is not EntityType.BEAST or beast.status is not EntityStatus.CANON:
        return "Only a living beast can found a line of its own."
    if await founded(ctx, beast.id):
        return f"{beast.name} has already founded a line."
    return None


async def found_line(ctx: TickContext, beast_id: int, ledger: Ledger) -> int:
    beast = await ctx.session.get_one(EntityRow, beast_id)
    profile = await ctx.session.get(BeastProfileRow, beast.id)
    species = await make(
        ctx,
        ledger,
        RecordSpec(
            entity_type=EntityType.SPECIES,
            name=await NameRepository(ctx.session).unique_name(f"Children of {beast.name}"),
            body=f"A line bred from the beast {beast.name}, carrying its traits and its legend.",
            stats=SpeciesStats(
                strength=clamp_percent(stat_or(beast, "strength", PERCENT // 2)),
                intelligence=clamp_percent(profile.intelligence) if profile is not None else None,
                danger=clamp_percent(stat_or(beast, "danger", PERCENT // 2)),
                abundance=ctx.rules.transform.progenitor_offspring,
            ),
            power=max(1, beast.power_level // 2),
            world_id=beast.world_id,
            location_id=beast.location_id,
        ),
    )
    region = await top_region(ctx.session, beast)
    if region is not None:
        row = SpeciesRangeRow(
            species_entity_id=species.id,
            region_entity_id=region.id,
            abundance=ctx.rules.transform.progenitor_offspring,
            since_epoch=ctx.epoch,
            updated_epoch=ctx.epoch,
            locked=[],
        )
        ctx.session.add(row)
        await ctx.session.flush()
        ledger.added(row)
    await bind(ctx, ledger, (species.id, beast.id, BondKind.DESCENDS_FROM), f"bred from {beast.name}")
    for legend in await ctx.session.scalars(
        select(BondRow.source_node_id).where(BondRow.target_node_id == beast.id, BondRow.kind == BondKind.TELLS_OF, BondRow.state == BondState.ACTIVE)
    ):
        await bind(ctx, ledger, (legend, species.id, BondKind.TELLS_OF), f"told of {beast.name}'s line")
    return species.id


def colossal(ctx: TickContext, beast: EntityRow, profile: BeastProfileRow | None) -> bool:
    return (profile is not None and profile.size_class is SizeClass.COLOSSAL) or beast.power_level >= ctx.rules.transform.colossal_power


async def colossal_remains(ctx: TickContext, beast: EntityRow, profile: BeastProfileRow | None) -> EntityRow | None:
    if not colossal(ctx, beast, profile) or await blocked(ctx, TransformKind.COLOSSAL_CORPSE, beast.id):
        return None
    ledger = Ledger()
    place = await make(
        ctx,
        ledger,
        RecordSpec(
            entity_type=EntityType.PLACE,
            name=await NameRepository(ctx.session).unique_name(god_lines.CORPSE_NAME.format(son=beast.name)),
            body=f"The body of the beast {beast.name}, become a place of its own.",
            stats=PlaceStats(danger=clamp_percent(stat_or(beast, "danger", PERCENT // 2)), mystery=PERCENT // 2),
            power=max(1, beast.power_level // 2),
            world_id=beast.world_id,
            location_id=beast.location_id,
        ),
    )
    goods = GoodsLedger(ctx.session, ctx.epoch)
    if profile is not None and profile.species_entity_id is not None:
        for item in list(await ctx.session.scalars(select(SpeciesYieldRow).where(SpeciesYieldRow.species_entity_id == profile.species_entity_id))):
            if item.commodity is not None and item.material is not None:
                amount = ctx.rules.beasts.corpse_yield * item.rate * ctx.rules.transform.colossal_yield
                await goods.add(place.id, item.commodity, amount, GoodsFlow.EXTRACTION, material=item.material, world_material_id=item.world_material_id)
    shade = await make(
        ctx,
        ledger,
        RecordSpec(
            entity_type=EntityType.SPIRIT,
            name=await NameRepository(ctx.session).unique_name(god_lines.SHADE_NAME.format(son=beast.name)),
            body=f"What still moves in the remains of {beast.name}.",
            stats=SpiritStats(strength=clamp_percent(beast.power_level // 2), unrest=PERCENT // 2),
            power=max(1, beast.power_level // 4),
            world_id=beast.world_id,
            location_id=place.id,
        ),
    )
    await bind(ctx, ledger, (place.id, beast.id, BondKind.TELLS_OF), f"the remains of {beast.name}")
    await bind(ctx, ledger, (shade.id, place.id, BondKind.PART_OF), f"haunts the remains of {beast.name}")
    await record_transformation(ctx, TransformKind.COLOSSAL_CORPSE, beast.id, place.id, ledger=ledger)
    return place
