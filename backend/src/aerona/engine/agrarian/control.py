from sqlalchemy import select

from aerona.constants.units import PERCENT
from aerona.core.errors import NotFoundError, ValidationFailedError
from aerona.db.base import Base
from aerona.db.tables.agrarian import (
    AID_FIELDS,
    BRAND_FIELDS,
    CENTRAL_FIELDS,
    COMMONS_FIELDS,
    FAMINE_FIELDS,
    INTENSITY_FIELDS,
    KEYSTONE_FIELDS,
    NUTRIENT_FIELDS,
    PERENNIAL_FIELDS,
    PREPAREDNESS_FIELDS,
    REBUILD_FIELDS,
    RESERVE_FIELDS,
    RING_FIELDS,
    BrandRow,
    CentralPlaceRow,
    CommonsRow,
    FamineLoreRow,
    GameReserveRow,
    IntensificationRow,
    KeystoneResourceRow,
    LandRingRow,
    PerennialRow,
    PreparednessRow,
    ReconstructionRow,
    ReliefAidRow,
    SoilNutrientRow,
)
from aerona.db.tables.celestial import WorldRow
from aerona.db.tables.economy import WorkshopRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.living import LivingLineRow
from aerona.db.tables.settlement import SettlementProfileRow
from aerona.domain.enums.agrarian import (
    AidKind,
    CommonsKind,
    CommonsRule,
    KeystoneUse,
    NutrientKind,
    PerennialKind,
    PreparednessKind,
    RebuildCause,
    RebuildPlan,
)
from aerona.domain.enums.economy import CommodityKind
from aerona.domain.enums.entity import EntityType
from aerona.engine.agrarian.book import fell_plantings
from aerona.engine.agrarian.lands import enclose, holdings, mature_epochs
from aerona.engine.agrarian.resilience import ResilienceTally, aid_from, finish
from aerona.engine.agrarian.ruin import mark_ruin
from aerona.engine.collective.control import of_type, saved
from aerona.engine.context import TickContext
from aerona.engine.cycles.control import node_exists, put_values
from aerona.engine.divine.control import apply
from aerona.engine.gatherings.control import Values, allowed, found
from aerona.engine.notes import note
from aerona.engine.polity.book import RealmBook
from aerona.engine.primitives.records import definite

REGIONS = frozenset({EntityType.REGION})
SETTLEMENTS = frozenset({EntityType.SETTLEMENT})
PEOPLES = frozenset({EntityType.PEOPLE})
SPECIES = frozenset({EntityType.SPECIES})
CULTS = frozenset({EntityType.CULT})
GIVERS = frozenset({EntityType.POLITY, EntityType.CULT})


async def set_ring(ctx: TickContext, region_id: int, values: Values) -> LandRingRow:
    await of_type(ctx, region_id, REGIONS, "a land")
    row = await ctx.session.get(LandRingRow, region_id) or await saved(ctx, LandRingRow(region_entity_id=region_id, updated_epoch=ctx.epoch, locked=[]))
    if values.get("market_entity_id") is not None:
        await of_type(ctx, int(values["market_entity_id"]), SETTLEMENTS, "a settlement")
    return await put_values(ctx, row, values, RING_FIELDS, "ring of land use")


async def set_central(ctx: TickContext, settlement_id: int, values: Values) -> CentralPlaceRow:
    await of_type(ctx, settlement_id, SETTLEMENTS, "a settlement")
    row = await ctx.session.get(CentralPlaceRow, settlement_id) or await saved(
        ctx, CentralPlaceRow(settlement_entity_id=settlement_id, updated_epoch=ctx.epoch, locked=[])
    )
    return await put_values(ctx, row, values, CENTRAL_FIELDS, "central place")


async def set_nutrient(ctx: TickContext, region_id: int, nutrient: NutrientKind, values: Values) -> SoilNutrientRow:
    await of_type(ctx, region_id, REGIONS, "a land")
    row = await ctx.session.get(SoilNutrientRow, (region_id, nutrient)) or await saved(
        ctx, SoilNutrientRow(region_entity_id=region_id, nutrient=nutrient, updated_epoch=ctx.epoch, locked=[])
    )
    return await put_values(ctx, row, values, NUTRIENT_FIELDS, "soil nutrient")


async def set_intensity(ctx: TickContext, region_id: int, values: Values) -> IntensificationRow:
    await of_type(ctx, region_id, REGIONS, "a land")
    row = await ctx.session.get(IntensificationRow, region_id) or await saved(
        ctx, IntensificationRow(region_entity_id=region_id, updated_epoch=ctx.epoch, locked=[])
    )
    return await put_values(ctx, row, values, INTENSITY_FIELDS, "farming intensity")


async def plant(
    ctx: TickContext, region_id: int, kind: PerennialKind, *, species_id: int | None, owner_id: int | None, area: int, line_id: int | None = None
) -> PerennialRow:
    region = await of_type(ctx, region_id, REGIONS, "a land")
    if species_id is not None:
        await of_type(ctx, species_id, SPECIES, "a species")
    if owner_id is not None:
        await node_exists(ctx, owner_id, "owner")
    if line_id is not None and await ctx.session.get(LivingLineRow, line_id) is None:
        raise NotFoundError("No such living line.")
    row = await saved(
        ctx,
        PerennialRow(
            region_entity_id=region_id,
            kind=kind,
            species_entity_id=species_id,
            line_id=line_id,
            owner_node_id=owner_id,
            area=area,
            mature_epochs=mature_epochs(ctx, kind),
            planted_epoch=ctx.epoch,
            locked=[],
        ),
    )
    await note(ctx, f"A new {kind.value} was planted in {region.name}.", key="perennials.planted", ids=[region.id])
    return row


async def fell(ctx: TickContext, perennial_id: int) -> PerennialRow:
    row = await found(ctx, PerennialRow, perennial_id, "planting")
    region = await of_type(ctx, row.region_entity_id, REGIONS, "a land")
    row.locked = [item for item in row.locked if item not in {"maturity", "condition"}]
    await fell_plantings(ctx, region, PERCENT)
    await ctx.session.flush()
    return row


async def open_commons(ctx: TickContext, region_id: int, kind: CommonsKind, rule: CommonsRule, steward_id: int | None) -> CommonsRow:
    await of_type(ctx, region_id, REGIONS, "a land")
    if steward_id is not None:
        await of_type(ctx, steward_id, SETTLEMENTS, "a settlement")
    if await ctx.session.scalar(select(CommonsRow.id).where(CommonsRow.region_entity_id == region_id, CommonsRow.kind == kind).limit(1)) is not None:
        raise ValidationFailedError("That land already holds such a common.")
    return await saved(ctx, CommonsRow(region_entity_id=region_id, kind=kind, rule=rule, steward_entity_id=steward_id, since_epoch=ctx.epoch, locked=[]))


async def enclose_common(ctx: TickContext, commons_id: int, encloser_id: int) -> CommonsRow:
    row = await found(ctx, CommonsRow, commons_id, "common")
    if row.rule is CommonsRule.ENCLOSED:
        raise ValidationFailedError("That common is already enclosed.")
    encloser: EntityRow = await found(ctx, EntityRow, encloser_id, "encloser")
    row.locked = [item for item in row.locked if item not in {"rule", "encloser_node_id", "dispossessed"}]
    await enclose(ctx, await holdings(ctx), row, encloser, await RealmBook.load(ctx.session))
    await ctx.session.flush()
    return row


async def declare_reserve(ctx: TickContext, region_id: int, holder_id: int, species_id: int | None, strictness: int) -> GameReserveRow:
    region = await of_type(ctx, region_id, REGIONS, "a land")
    await node_exists(ctx, holder_id, "holder")
    if species_id is not None:
        await of_type(ctx, species_id, SPECIES, "a species")
    row = await saved(
        ctx,
        GameReserveRow(
            region_entity_id=region_id, holder_node_id=holder_id, species_entity_id=species_id, strictness=strictness, since_epoch=ctx.epoch, locked=[]
        ),
    )
    await note(ctx, f"The game of {region.name} is reserved; the folk may no longer hunt there.", key="game.reserved", ids=[region.id])
    return row


async def set_famine(ctx: TickContext, people_id: int, values: Values) -> FamineLoreRow:
    await of_type(ctx, people_id, PEOPLES, "a people")
    row = await ctx.session.get(FamineLoreRow, people_id) or await saved(ctx, FamineLoreRow(people_entity_id=people_id, updated_epoch=ctx.epoch, locked=[]))
    return await put_values(ctx, row, values, FAMINE_FIELDS, "famine lore")


async def build_work(ctx: TickContext, settlement_id: int, kind: PreparednessKind, level: int) -> PreparednessRow:
    town = await of_type(ctx, settlement_id, SETTLEMENTS, "a settlement")
    row = await ctx.session.get(PreparednessRow, (settlement_id, kind)) or await saved(
        ctx, PreparednessRow(settlement_entity_id=settlement_id, kind=kind, level=0, built_epoch=ctx.epoch, locked=[])
    )
    row = await put_values(ctx, row, {"level": level, "condition": PERCENT}, PREPAREDNESS_FIELDS, "disaster work")
    row.built_epoch = ctx.epoch
    await note(ctx, f"{town.name} raised its {kind.value}s to level {level}.", key="resilience.built", ids=[town.id])
    return row


async def send_aid(ctx: TickContext, giver_id: int, settlement_id: int, kind: AidKind, amount: int) -> ReliefAidRow:
    giver = await of_type(ctx, giver_id, GIVERS, "a realm or a cult")
    town = await of_type(ctx, settlement_id, SETTLEMENTS, "a settlement")
    book = await RealmBook.load(ctx.session)
    own = book.member_of.get(town.id)
    row = await aid_from(
        ctx,
        giver,
        book.realms.get(giver.id),
        event=None,
        town=town,
        receiver=book.realms.get(own) if own is not None else None,
        tally=ResilienceTally(),
        kind=kind,
        amount=amount,
    )
    if row is None:
        raise ValidationFailedError("No aid could be sent.")
    await ctx.session.flush()
    return row


async def begin_rebuild(ctx: TickContext, settlement_id: int, cause: RebuildCause, plan: RebuildPlan) -> ReconstructionRow:
    town = await of_type(ctx, settlement_id, SETTLEMENTS, "a settlement")
    row = await mark_ruin(ctx, town, cause)
    if row is None:
        raise ValidationFailedError(f"{town.name} cannot be rebuilt now.")
    return await put_values(ctx, row, {"plan": plan.value}, REBUILD_FIELDS, "rebuilding")


async def finish_rebuild(ctx: TickContext, rebuild_id: int) -> ReconstructionRow:
    row = await found(ctx, ReconstructionRow, rebuild_id, "rebuilding")
    if row.finished_epoch is not None:
        raise ValidationFailedError("That rebuilding is already finished.")
    town = await of_type(ctx, row.settlement_entity_id, SETTLEMENTS, "a settlement")
    profile = await found(ctx, SettlementProfileRow, town.id, "town")
    row.progress = PERCENT
    await finish(ctx, row, town, profile)
    await ctx.session.flush()
    return row


async def designate_keystone(
    ctx: TickContext,
    world_id: int,
    name: str,
    *,
    use: KeystoneUse,
    producer_id: int | None = None,
    source_id: int | None = None,
    commodity: CommodityKind | None = None,
    cult_id: int | None = None,
    son_id: int | None = None,
) -> KeystoneResourceRow:
    await found(ctx, WorldRow, world_id, "world")
    if producer_id is not None:
        await found(ctx, EntityRow, producer_id, "producer")
    if source_id is not None:
        await of_type(ctx, source_id, REGIONS, "a land")
    if cult_id is not None:
        await of_type(ctx, cult_id, CULTS, "a cult")
    keystone = await ctx.session.scalar(select(KeystoneResourceRow).where(KeystoneResourceRow.world_id == world_id).limit(1))
    if keystone is None:
        keystone = await saved(ctx, KeystoneResourceRow(world_id=world_id, name=name, designated_epoch=ctx.epoch, locked=[]))
    keystone.designated_by_son_id = son_id
    values = {"name": name, "use": use.value, "producer_entity_id": producer_id, "source_region_entity_id": source_id, "cult_entity_id": cult_id}
    if commodity is not None:
        values["commodity"] = commodity.value
    keystone = await put_values(ctx, keystone, values, KEYSTONE_FIELDS, "keystone resource")
    await note(
        ctx,
        f"{definite(name)} became what the whole world depends on.",
        key="keystone.designated",
        ids=[item for item in (producer_id, source_id, cult_id) if item],
    )
    return keystone


async def found_brand(ctx: TickContext, workshop_id: int, name: str) -> BrandRow:
    workshop = await found(ctx, WorkshopRow, workshop_id, "workshop")
    if await ctx.session.scalar(select(BrandRow.id).where(BrandRow.workshop_id == workshop_id).limit(1)) is not None:
        raise ValidationFailedError("That workshop already has a brand.")
    row = await saved(
        ctx,
        BrandRow(
            workshop_id=workshop.id,
            community_entity_id=workshop.community_entity_id,
            owner_node_id=workshop.owner_node_id or workshop.community_entity_id,
            name=name,
            since_epoch=ctx.epoch,
            locked=[],
        ),
    )
    await note(ctx, f"The {name} is known for its work; buyers ask for it by name.", key="brands.earned", ids=[workshop.community_entity_id])
    return row


EDITABLE: dict[str, tuple[type[Base], tuple[str, ...], str]] = {
    "land_ring": (LandRingRow, RING_FIELDS, "ring of land use"),
    "central_place": (CentralPlaceRow, CENTRAL_FIELDS, "central place"),
    "soil_nutrient": (SoilNutrientRow, NUTRIENT_FIELDS, "soil nutrient"),
    "intensification": (IntensificationRow, INTENSITY_FIELDS, "farming intensity"),
    "perennial": (PerennialRow, PERENNIAL_FIELDS, "planting"),
    "commons": (CommonsRow, COMMONS_FIELDS, "common"),
    "game_reserve": (GameReserveRow, RESERVE_FIELDS, "game reserve"),
    "famine_lore": (FamineLoreRow, FAMINE_FIELDS, "famine lore"),
    "preparedness": (PreparednessRow, PREPAREDNESS_FIELDS, "disaster work"),
    "relief": (ReliefAidRow, AID_FIELDS, "aid"),
    "reconstruction": (ReconstructionRow, REBUILD_FIELDS, "rebuilding"),
    "keystone": (KeystoneResourceRow, KEYSTONE_FIELDS, "keystone resource"),
    "brand": (BrandRow, BRAND_FIELDS, "brand"),
}


async def edit_record(ctx: TickContext, kind: str, key: object, values: Values, release: list[str]) -> Base:
    table, fields, label = EDITABLE[kind]
    row = apply(await found(ctx, table, key, label), allowed(values, fields, label), release)
    await ctx.session.flush()
    return row


async def delete_record(ctx: TickContext, kind: str, key: object) -> None:
    table, _, label = EDITABLE[kind]
    await ctx.session.delete(await found(ctx, table, key, label))
    await ctx.session.flush()
