from collections.abc import Awaitable, Callable, Mapping
from dataclasses import dataclass
from enum import StrEnum

from sqlalchemy import select

from aerona.db.kind_concepts.registry import CONCEPTS
from aerona.db.tables.bonds import BondRow
from aerona.db.tables.cosmos import AppliedFixupRow
from aerona.db.tables.cuisine import CommunityDishRow, DishRow
from aerona.db.tables.culture import ItemProfileRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.factions import FactionProfileRow
from aerona.db.tables.kinds import GoodKindRow, KindHoldingRow
from aerona.db.tables.society_kinds import OrganisationKindRow, RankKindRow
from aerona.db.write_guard import held
from aerona.domain.enums.bond import BondKind, BondState
from aerona.domain.enums.culture import ItemClass
from aerona.domain.enums.entity import EntityStatus, EntityType
from aerona.domain.enums.kind_crafts import FurnishingCategory, GarmentCategory, InstrumentCategory, SubstanceCategory, ToolCategory
from aerona.domain.enums.kinds import KindConcept, KindSpread, KindStance
from aerona.engine.body.customs import people_of
from aerona.engine.context import TickContext
from aerona.engine.economy.stocks import holdings
from aerona.engine.kinds.acts import holding_index, make_kind
from aerona.engine.primitives.folk import present_among

LEGACY_FIXUP = "kinds.legacy_holdings"


async def give(ctx: TickContext, concept: KindConcept, kind_id: int, holder_id: int, strength: int) -> bool:
    if held(holder_id):
        return False
    index = await holding_index(ctx)
    if (concept, kind_id, holder_id) in index:
        return False
    row = KindHoldingRow(
        concept=concept,
        kind_id=kind_id,
        holder_node_id=holder_id,
        stance=KindStance.USES,
        strength=strength,
        spread=KindSpread.INVENTED,
        since_epoch=ctx.epoch,
        locked=[],
    )
    ctx.session.add(row)
    index[(concept, kind_id, holder_id)] = row
    return True


async def settlements(ctx: TickContext) -> list[EntityRow]:
    return list(
        await ctx.session.scalars(
            select(EntityRow).where(EntityRow.entity_type == EntityType.SETTLEMENT, EntityRow.status == EntityStatus.CANON).order_by(EntityRow.id)
        )
    )


async def goods_held(ctx: TickContext) -> int:
    built = {
        row.stocked_as: row.id for row in await ctx.session.scalars(select(GoodKindRow).where(GoodKindRow.built_in.is_(True))) if row.stocked_as is not None
    }
    given = 0
    for town in await settlements(ctx):
        for commodity, quantity in (await holdings(ctx.session, town.id)).items():
            kind_id = built.get(commodity)
            if kind_id is not None and quantity > 0 and await give(ctx, KindConcept.GOOD, kind_id, town.id, ctx.rules.kinds.adoption_strength):
                given += 1
    return given


async def dishes_held(ctx: TickContext) -> int:
    given = 0
    for row in list(await ctx.session.scalars(select(CommunityDishRow).order_by(CommunityDishRow.community_entity_id, CommunityDishRow.dish_id))):
        if await ctx.session.get(DishRow, row.dish_id) is not None and await give(ctx, KindConcept.DISH, row.dish_id, row.community_entity_id, row.popularity):
            given += 1
    return given


async def organisations_held(ctx: TickContext) -> int:
    built = {
        row.base: row.id for row in await ctx.session.scalars(select(OrganisationKindRow).where(OrganisationKindRow.built_in.is_(True))) if row.base is not None
    }
    given = 0
    for profile in list(await ctx.session.scalars(select(FactionProfileRow).order_by(FactionProfileRow.faction_entity_id))):
        kind_id = built.get(profile.kind)
        if kind_id is not None and await give(ctx, KindConcept.ORGANISATION, kind_id, profile.faction_entity_id, ctx.rules.kinds.founding_strength):
            given += 1
    return given


async def ranks_held(ctx: TickContext) -> int:
    built = {row.category: row.id for row in await ctx.session.scalars(select(RankKindRow).where(RankKindRow.built_in.is_(True)))}
    given = 0
    for town in await settlements(ctx):
        classes = set(
            await ctx.session.scalars(
                select(EntityRow.social_class).where(
                    EntityRow.entity_type == EntityType.MORTAL, EntityRow.status == EntityStatus.CANON, await present_among(ctx.session, [town.id])
                )
            )
        )
        for social_class in sorted(item for item in classes if item is not None):
            kind_id = built.get(social_class)
            if kind_id is not None and await give(ctx, KindConcept.RANK, kind_id, town.id, ctx.rules.kinds.adoption_strength):
                given += 1
    return given


@dataclass(frozen=True)
class ItemKind:
    concept: KindConcept
    category: StrEnum


C = ItemClass
ITEM_KINDS: Mapping[ItemClass, ItemKind] = {
    C.TOOL: ItemKind(KindConcept.TOOL, ToolCategory.CRAFTING),
    C.ASTROLABE: ItemKind(KindConcept.TOOL, ToolCategory.NAVIGATION),
    C.MAP: ItemKind(KindConcept.TOOL, ToolCategory.NAVIGATION),
    C.COMPUTER: ItemKind(KindConcept.TOOL, ToolCategory.COMPUTING),
    C.INSTRUMENT: ItemKind(KindConcept.INSTRUMENT, InstrumentCategory.STRING),
    C.CLOAK: ItemKind(KindConcept.GARMENT, GarmentCategory.OUTER_LAYER),
    C.PADDING: ItemKind(KindConcept.GARMENT, GarmentCategory.UNDERGARMENT),
    C.CROWN: ItemKind(KindConcept.GARMENT, GarmentCategory.HEAD),
    C.RING: ItemKind(KindConcept.GARMENT, GarmentCategory.ORNAMENT),
    C.JEWEL: ItemKind(KindConcept.GARMENT, GarmentCategory.ORNAMENT),
    C.MIRROR: ItemKind(KindConcept.FURNISHING, FurnishingCategory.DECORATION),
    C.VESSEL_OBJECT: ItemKind(KindConcept.FURNISHING, FurnishingCategory.STORAGE),
    C.DRUG: ItemKind(KindConcept.SUBSTANCE, SubstanceCategory.MEDICINAL),
}


async def owner_of(ctx: TickContext, item_id: int) -> int | None:
    statement = select(BondRow.source_node_id).where(BondRow.target_node_id == item_id, BondRow.kind == BondKind.OWNS, BondRow.state == BondState.ACTIVE)
    return await ctx.session.scalar(statement.order_by(BondRow.id.desc()).limit(1))


async def items_held(ctx: TickContext) -> int:
    made: dict[tuple[int, KindConcept, StrEnum], int] = {}
    given = 0
    query = select(ItemProfileRow).where(ItemProfileRow.item_class.in_(sorted(ITEM_KINDS))).order_by(ItemProfileRow.item_entity_id)
    profiles = await ctx.session.scalars(query)
    for profile in list(profiles):
        item = await ctx.session.get(EntityRow, profile.item_entity_id)
        owner_id = await owner_of(ctx, profile.item_entity_id) if item is not None and item.status is EntityStatus.CANON else None
        owner = await ctx.session.get(EntityRow, owner_id) if owner_id is not None else None
        people = await people_of(ctx.session, owner) if owner is not None else None
        kind = ITEM_KINDS.get(profile.item_class)
        spec = CONCEPTS.get(kind.concept) if kind is not None else None
        if kind is None or item is None or people is None or spec is None or held(people.id):
            continue
        key = (people.id, kind.concept, kind.category)
        if key not in made:
            values = {"name": item.name, "description": item.description, "category": kind.category}
            row = await make_kind(ctx, spec, {**values, "world_id": people.world_id, "origin_node_id": people.id})
            made[key] = row.id
        if await give(ctx, kind.concept, made[key], people.id, ctx.rules.kinds.adoption_strength):
            given += 1
    return given


GIVERS: tuple[tuple[str, Callable[[TickContext], Awaitable[int]]], ...] = (
    ("goods", goods_held),
    ("dishes", dishes_held),
    ("organisations", organisations_held),
    ("ranks", ranks_held),
    ("items", items_held),
)


async def legacy_holdings(ctx: TickContext) -> dict[str, int]:
    if await ctx.session.get(AppliedFixupRow, LEGACY_FIXUP) is not None:
        return {}
    result = {name: await giver(ctx) for name, giver in GIVERS}
    ctx.session.add(AppliedFixupRow(key=LEGACY_FIXUP, result=result))
    await ctx.session.flush()
    return result
