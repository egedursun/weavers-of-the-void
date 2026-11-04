from sqlalchemy import select

from aerona.catalog.lore import ART_WORDS, ITEM_WORDS
from aerona.db.tables.cosmos import AppliedFixupRow
from aerona.db.tables.culture import ArtworkProfileRow, ItemProfileRow
from aerona.db.tables.economy import NodeMaterialRow
from aerona.db.tables.entities import EntityRow
from aerona.domain.enums.culture import ArtMedium, ItemClass
from aerona.domain.enums.economy import MaterialSlot
from aerona.domain.enums.entity import EntityStatus, EntityType
from aerona.domain.enums.material import MaterialKind
from aerona.engine.context import TickContext
from aerona.engine.economy.materials import set_node_material
from aerona.engine.lore import art, items

ITEMS_FIXUP = "lore.typed_items"
ARTWORKS_FIXUP = "lore.typed_artworks"


def legacy_text(entity: EntityRow) -> str:
    return f"{entity.name} {entity.subtype or ''}".lower()


def legacy_class(entity: EntityRow) -> ItemClass | None:
    text = legacy_text(entity)
    return next((item_class for item_class, words in ITEM_WORDS.items() if any(word in text for word in words)), None)


def legacy_medium(entity: EntityRow) -> ArtMedium | None:
    text = legacy_text(entity)
    return next((medium for medium, words in ART_WORDS.items() if any(word in text for word in words)), None)


def legacy_material(entity: EntityRow) -> str | None:
    subtype = (entity.subtype or "").strip().lower()
    return subtype if subtype in {kind.value for kind in MaterialKind} else None


async def unprofiled(ctx: TickContext, entity_type: EntityType, profile: type[ItemProfileRow] | type[ArtworkProfileRow]) -> list[EntityRow]:
    key = profile.item_entity_id if profile is ItemProfileRow else ArtworkProfileRow.artwork_entity_id
    rows = await ctx.session.scalars(
        select(EntityRow)
        .where(EntityRow.entity_type == entity_type, EntityRow.status != EntityStatus.REJECTED, EntityRow.id.not_in(select(key)))
        .order_by(EntityRow.id)
    )
    return list(rows)


def valid_material(key: str | None) -> bool:
    return key is None or key.startswith(items.WORLD_PREFIX) or key in {kind.value for kind in MaterialKind}


async def mend_materials(ctx: TickContext) -> int:
    mended = 0
    for row in list(await ctx.session.scalars(select(ItemProfileRow).order_by(ItemProfileRow.item_entity_id))):
        if valid_material(row.material) or "material" in row.locked:
            continue
        body = await ctx.session.get(NodeMaterialRow, (row.item_entity_id, MaterialSlot.BODY))
        row.material = items.material_key(body)
        mended += 1
    return mended


async def backfill_items(ctx: TickContext) -> int:
    if await ctx.session.get(AppliedFixupRow, ITEMS_FIXUP) is not None:
        return 0
    typed = 0
    for entity in await unprofiled(ctx, EntityType.ITEM, ItemProfileRow):
        row = await items.profile_of(ctx, entity, legacy_class(entity))
        material = legacy_material(entity)
        if row.material is None and material is not None:
            await set_node_material(ctx.session, entity.id, MaterialSlot.BODY, MaterialKind(material))
        typed += 1
    typed += await mend_materials(ctx)
    ctx.session.add(AppliedFixupRow(key=ITEMS_FIXUP, result={"items": typed}))
    await ctx.session.flush()
    return typed


async def backfill_artworks(ctx: TickContext) -> int:
    if await ctx.session.get(AppliedFixupRow, ARTWORKS_FIXUP) is not None:
        return 0
    typed = 0
    for entity in await unprofiled(ctx, EntityType.ARTWORK, ArtworkProfileRow):
        await art.profile_of(ctx, entity, legacy_medium(entity))
        typed += 1
    ctx.session.add(AppliedFixupRow(key=ARTWORKS_FIXUP, result={"artworks": typed}))
    await ctx.session.flush()
    return typed
