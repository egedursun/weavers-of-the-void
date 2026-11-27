import re

from sqlalchemy import or_, select

from aerona.catalog.body_plans import ATHERMIC_PLANS
from aerona.catalog.domestication import ATHERMIC_BIOCHEMISTRY
from aerona.catalog.flora import PRODUCT_BY_COMMODITY
from aerona.db.fixups import fixup_due
from aerona.db.kind_concepts.nature import PLANT_PARTS
from aerona.db.tables.cosmos import AppliedFixupRow
from aerona.db.tables.ecology import SpeciesProductRow, SpeciesProfileRow
from aerona.db.tables.kinds import GoodKindRow
from aerona.db.write_guard import held
from aerona.domain.enums.ecology import PlantYield, SpeciesClass, YieldProduct
from aerona.domain.enums.nature import Thermoregulation
from aerona.domain.enums.nature_kinds import ProductPart
from aerona.engine.context import TickContext

PRODUCTS_FIXUP = "plant_products.w52"
REGULATION_FIXUP = "thermo.w52"
KNOWN = frozenset(item.value for item in PlantYield)


async def renamed(ctx: TickContext, row: SpeciesProductRow, product: str, part: ProductPart | None) -> SpeciesProductRow:
    fresh = SpeciesProductRow(
        species_entity_id=row.species_entity_id,
        product=product,
        commodity=row.commodity,
        material=row.material,
        world_material_id=row.world_material_id,
        rate=row.rate,
        part=part,
        good_kind_id=row.good_kind_id,
        locked=list(row.locked or []),
    )
    await ctx.session.delete(row)
    await ctx.session.flush()
    ctx.session.add(fresh)
    return fresh


async def backfill_products(ctx: TickContext) -> int:
    if not await fixup_due(ctx.session, PRODUCTS_FIXUP):
        return 0
    ctx.session.add(AppliedFixupRow(key=PRODUCTS_FIXUP, result={}))
    plants = select(SpeciesProfileRow.species_entity_id).where(SpeciesProfileRow.species_class != SpeciesClass.ANIMAL)
    rows = list(
        await ctx.session.scalars(
            select(SpeciesProductRow)
            .where(SpeciesProductRow.species_entity_id.in_(plants), SpeciesProductRow.commodity.is_not(None))
            .order_by(SpeciesProductRow.species_entity_id, SpeciesProductRow.product)
        )
    )
    taken = {(row.species_entity_id, row.product) for row in rows}
    moved = 0
    for row in rows:
        matched = PRODUCT_BY_COMMODITY.get(row.commodity) if row.commodity is not None else None
        if row.product in KNOWN or matched is None or held(row.species_entity_id) or "product" in (row.locked or []):
            continue
        if (row.species_entity_id, matched.product.value) in taken:
            continue
        taken.add((row.species_entity_id, matched.product.value))
        await renamed(ctx, row, matched.product.value, PLANT_PARTS[matched.product])
        moved += 1
    return moved


async def backfill_regulation(ctx: TickContext) -> int:
    if not await fixup_due(ctx.session, REGULATION_FIXUP):
        return 0
    ctx.session.add(AppliedFixupRow(key=REGULATION_FIXUP, result={}))
    moved = 0
    rows = await ctx.session.scalars(
        select(SpeciesProfileRow)
        .where(
            or_(SpeciesProfileRow.biochemistry.in_(sorted(ATHERMIC_BIOCHEMISTRY)), SpeciesProfileRow.body_plan.in_(sorted(ATHERMIC_PLANS))),
            SpeciesProfileRow.thermoregulation != Thermoregulation.ATHERMIC,
        )
        .order_by(SpeciesProfileRow.species_entity_id)
    )
    for row in list(rows):
        if held(row.species_entity_id) or "thermoregulation" in (row.locked or []):
            continue
        row.thermoregulation = Thermoregulation.ATHERMIC
        moved += 1
    return moved


BEAST_PRODUCTS_FIXUP = "beast_products.w52"
BEAST_KNOWN = frozenset(item.value for item in YieldProduct)


def beast_category(text: str) -> YieldProduct | None:
    words = set(re.findall(r"[a-z]+", text.lower()))
    return next((item for item in YieldProduct if item.value in words or f"{item.value}s" in words), None)


async def backfill_beast_products(ctx: TickContext) -> int:
    if not await fixup_due(ctx.session, BEAST_PRODUCTS_FIXUP):
        return 0
    ctx.session.add(AppliedFixupRow(key=BEAST_PRODUCTS_FIXUP, result={}))
    animals = select(SpeciesProfileRow.species_entity_id).where(SpeciesProfileRow.species_class == SpeciesClass.ANIMAL)
    rows = list(
        await ctx.session.scalars(
            select(SpeciesProductRow)
            .where(SpeciesProductRow.species_entity_id.in_(animals))
            .order_by(SpeciesProductRow.species_entity_id, SpeciesProductRow.product)
        )
    )
    taken = {(row.species_entity_id, row.product) for row in rows}
    moved = 0
    for row in rows:
        if row.product in BEAST_KNOWN or held(row.species_entity_id) or "product" in (row.locked or []):
            continue
        kind = await ctx.session.get(GoodKindRow, row.good_kind_id) if row.good_kind_id is not None else None
        matched = beast_category(f"{row.product} {kind.name if kind is not None else ''}")
        if matched is None or (row.species_entity_id, matched.value) in taken:
            continue
        taken.add((row.species_entity_id, matched.value))
        await renamed(ctx, row, matched.value, row.part)
        moved += 1
    return moved
