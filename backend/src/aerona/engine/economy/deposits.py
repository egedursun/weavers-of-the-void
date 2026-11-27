from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.catalog.goods_tables import BYPRODUCTS, DIFFICULTY, ORIGIN_BASE, ORIGIN_WORDS
from aerona.catalog.materials import MATERIALS
from aerona.constants.units import PERCENT
from aerona.db.fixups import fixup_due
from aerona.db.tables.cosmos import AppliedFixupRow
from aerona.db.tables.economy import PHYSICS_COLUMNS, PROPERTY_COLUMNS, ResourceProfileRow, WorldMaterialRow
from aerona.db.tables.entities import EntityRow
from aerona.domain.enums.economy import CommodityKind, MaterialFamily, MaterialOrigin
from aerona.domain.enums.entity import EntityType
from aerona.domain.enums.material import MaterialKind
from aerona.domain.enums.modifier import IncidentRole
from aerona.domain.models.entity_stats import ResourceStats
from aerona.engine.context import TickContext
from aerona.engine.economy.resources import RENEWABLE
from aerona.engine.primitives.numbers import clamp_int, round_half_up
from aerona.engine.primitives.records import RecordSpec, create_record
from aerona.engine.recording.record import record

FAMILY_BASE: dict[MaterialFamily, MaterialKind] = {
    MaterialFamily.ORGANIC: MaterialKind.WOOD,
    MaterialFamily.STONE: MaterialKind.STONE,
    MaterialFamily.METAL: MaterialKind.IRON,
    MaterialFamily.PRECIOUS: MaterialKind.SILVER,
    MaterialFamily.EXOTIC: MaterialKind.STAR_METAL,
}
PHYSICS_FIXUP = "materials.physics"


def physics_base(row: WorldMaterialRow) -> MaterialKind:
    if row.base_kind is not None:
        return row.base_kind
    return ORIGIN_BASE.get(row.origin, FAMILY_BASE[row.family])


async def backfill_physics(session: AsyncSession) -> int:
    if not await fixup_due(session, PHYSICS_FIXUP):
        return 0
    rows = [row for row in await session.scalars(select(WorldMaterialRow).order_by(WorldMaterialRow.id)) if physics_unset(row)]
    for row in rows:
        spec = MATERIALS[physics_base(row)]
        for column in PHYSICS_COLUMNS:
            setattr(row, column, getattr(spec, column))
    session.add(AppliedFixupRow(key=PHYSICS_FIXUP, result={"materials": len(rows)}))
    await session.flush()
    return len(rows)


def physics_unset(row: WorldMaterialRow) -> bool:
    table = WorldMaterialRow.__table__
    return all(getattr(row, column) == getattr(table.c[column].default, "arg", None) for column in PHYSICS_COLUMNS)


@dataclass(frozen=True)
class Deposit:
    name: str
    body: str
    place: EntityRow
    commodity: CommodityKind
    material: MaterialKind | None = None
    world_material_id: int | None = None
    reserve: int = 0
    richness: int = 60
    quality: int = 60
    revealed: bool = True
    pending: bool = False


def describe(props: dict[str, int]) -> str:
    def word(value: int, low: str, high: str) -> str:
        return high if value >= PERCENT * 2 // 3 else low if value <= PERCENT // 3 else f"neither {low} nor {high}"

    return (
        f"It is {word(props['hardness'], 'soft', 'hard')}, {word(props['toughness'], 'brittle', 'tough')} and {word(props['weight'], 'light', 'heavy')}; "
        f"its edge is {word(props['edge'], 'dull', 'keen')}, it {'drinks' if props['conductivity'] >= PERCENT // 2 else 'resists'} magic, "
        f"and it is {'holy' if props['sanctity'] > props['corruption'] else 'tainted'} to the touch."
    )


async def open_deposit(ctx: TickContext, deposit: Deposit) -> EntityRow:
    table = ctx.rules.extraction
    reserve = deposit.reserve or table.deposit_reserve
    abundance = clamp_int(round_half_up(reserve * PERCENT / max(1, reserve)), 0, PERCENT)
    resource = await create_record(
        ctx,
        RecordSpec(
            entity_type=EntityType.RESOURCE,
            name=deposit.name,
            body=deposit.body,
            stats=ResourceStats(abundance=abundance, value=deposit.richness, might=deposit.quality),
            power=6,
            location_id=deposit.place.id,
            world_id=deposit.place.world_id,
            subtype="deposit",
            pending=deposit.pending,
        ),
    )
    byproduct = BYPRODUCTS.get(deposit.material) if deposit.material is not None else None
    ctx.session.add(
        ResourceProfileRow(
            resource_entity_id=resource.id,
            commodity=deposit.commodity,
            material=deposit.material,
            world_material_id=deposit.world_material_id,
            reserve=reserve,
            initial_reserve=reserve,
            richness=deposit.richness,
            regeneration=round_half_up(reserve * table.renewable_regen_pct / PERCENT) if deposit.commodity in RENEWABLE else 0,
            extraction_difficulty=DIFFICULTY.get(deposit.commodity, 30),
            required_branch=MATERIALS[deposit.material].branch if deposit.material is not None else None,
            required_level=MATERIALS[deposit.material].level if deposit.material is not None else 0,
            quality=deposit.quality,
            byproduct_material=byproduct[0] if byproduct is not None else None,
            byproduct_pct=byproduct[1] if byproduct is not None else 0,
            revealed=deposit.revealed,
        )
    )
    await ctx.session.flush()
    return resource


async def has_substance(ctx: TickContext, source_node_id: int) -> bool:
    found = await ctx.session.scalar(select(WorldMaterialRow.id).where(WorldMaterialRow.source_node_id == source_node_id).limit(1))
    return found is not None


async def new_substance(
    ctx: TickContext, origin: MaterialOrigin, place: EntityRow, *, source_node_id: int | None, base: MaterialKind | None = None
) -> WorldMaterialRow:
    spread = ctx.rules.materials.world_material_spread
    rng = ctx.rng(f"substance.{origin.value}.{source_node_id or place.id}")
    kind = base or ORIGIN_BASE.get(origin, FAMILY_BASE[MaterialFamily.EXOTIC])
    spec = MATERIALS[kind]
    values = {column: clamp_int(getattr(spec, column) + rng.die(2 * spread + 1) - spread - 1, 0, PERCENT) for column in PROPERTY_COLUMNS}
    row = WorldMaterialRow(
        world_id=place.world_id,
        origin=origin,
        base_kind=None,
        family=MaterialFamily.EXOTIC,
        branch=spec.branch,
        level=spec.level,
        source_node_id=source_node_id,
        created_epoch=ctx.epoch,
        description=describe(values),
        **values,
    )
    ctx.session.add(row)
    await ctx.session.flush()
    deposit = await open_deposit(
        ctx,
        Deposit(
            name=f"Vein of an Unnamed Substance near {place.name}",
            body=f"A substance of its own came from {ORIGIN_WORDS[origin]}. {row.description}",
            place=place,
            commodity=CommodityKind.ORE,
            world_material_id=row.id,
            richness=clamp_int(values["rarity"], 1, PERCENT),
            quality=clamp_int(values["base_value"], 0, PERCENT),
            pending=True,
        ),
    )
    row.deposit_entity_id = deposit.id
    await record(
        ctx,
        f"material.substance_{origin.value}",
        roles={IncidentRole.PRODUCT: deposit.id, IncidentRole.PLACE: place.id},
        facts={"origin": origin, "rarity": values["rarity"], "base_value": values["base_value"]},
        place=place.id,
    )
    return row
