from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.constants.units import PERCENT
from aerona.db.tables.agrarian import BrandRow
from aerona.db.tables.commerce import LeaseRow, PromotionRow, ShopRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.mortal import MortalProfileRow
from aerona.db.write_guard import held
from aerona.domain.enums.bond import BondKind
from aerona.domain.enums.commerce import LeaseDefault, LeaseThing, PromotionMedium
from aerona.domain.enums.culture import Technique
from aerona.domain.enums.entity import EntityStatus
from aerona.domain.enums.modifier import IncidentRole
from aerona.engine.context import TickContext
from aerona.engine.economy.purse import points_of
from aerona.engine.lore.research import techniques_of
from aerona.engine.primitives.queries import active_bonds
from aerona.engine.recording.record import record

REACH_COST = 10
TRUSTED_CLAIM = 75


@dataclass
class DealingsTally:
    promotions: int = 0
    leases: int = 0


def promotion_cost(reach: int) -> int:
    return max(1, reach // REACH_COST)


async def media_known(session: AsyncSession, place_id: int | None) -> bool:
    return place_id is not None and Technique.MASS_MEDIA in await techniques_of(session, place_id)


async def honesty_of(session: AsyncSession, holder: EntityRow) -> int:
    profile = await session.get(MortalProfileRow, holder.id)
    return profile.honour if profile is not None else TRUSTED_CLAIM


async def start_promotion(ctx: TickContext, holder: EntityRow, brand: BrandRow, tally: DealingsTally) -> PromotionRow | None:
    reach = min(PERCENT, await points_of(ctx.session, holder))
    cost = promotion_cost(reach)
    if reach <= 0 or await points_of(ctx.session, holder) < cost * 2:
        return None
    medium = PromotionMedium.MEDIA if await media_known(ctx.session, brand.community_entity_id) else PromotionMedium.DISPLAY
    row = PromotionRow(
        holder_node_id=holder.id,
        commodity=None,
        brand_id=brand.id,
        medium=medium,
        reach=reach,
        cost=cost,
        accuracy=await honesty_of(ctx.session, holder),
        started_epoch=ctx.epoch,
        locked=[],
    )
    ctx.session.add(row)
    await record(
        ctx, "commerce.promotion_run", roles={IncidentRole.ACTOR: holder.id}, facts={"medium": medium, "reach": reach}, place=brand.community_entity_id
    )
    tally.promotions += 1
    return row


async def promote_brands(ctx: TickContext, tally: DealingsTally) -> None:
    running = set(await ctx.session.scalars(select(PromotionRow.brand_id).where(PromotionRow.brand_id.is_not(None))))
    for brand in list(await ctx.session.scalars(select(BrandRow).where(BrandRow.owner_node_id.is_not(None)).order_by(BrandRow.id))):
        if brand.id in running or brand.owner_node_id is None or held(brand.owner_node_id):
            continue
        owner = await ctx.session.get(EntityRow, brand.owner_node_id)
        if owner is not None and owner.status is EntityStatus.CANON:
            await start_promotion(ctx, owner, brand, tally)


async def lease_shops(ctx: TickContext, tally: DealingsTally) -> None:
    leased = {(row.owner_node_id, row.lessee_node_id, row.thing_node_id) for row in await ctx.session.scalars(select(LeaseRow))}
    for shop in list(await ctx.session.scalars(select(ShopRow).where(ShopRow.structure_entity_id.is_not(None)).order_by(ShopRow.id))):
        if shop.structure_entity_id is None or held(shop.keeper_node_id) or held(shop.structure_entity_id):
            continue
        owners = [bond.source_node_id for bond in await active_bonds(ctx.session, [BondKind.OWNS], targets=[shop.structure_entity_id])]
        owner_id = min((owner for owner in owners if owner != shop.keeper_node_id), default=None)
        if owner_id is None or shop.keeper_node_id in owners or held(owner_id) or (owner_id, shop.keeper_node_id, shop.structure_entity_id) in leased:
            continue
        rent = ctx.rules.commerce.shop_rent
        row = LeaseRow(
            owner_node_id=owner_id,
            lessee_node_id=shop.keeper_node_id,
            thing_node_id=shop.structure_entity_id,
            thing=LeaseThing.STRUCTURE,
            rent=rent,
            term_epochs=ctx.rules.commerce.epochs(ctx.rules.commerce.shop_lease_years),
            on_default=LeaseDefault.EVICTION,
            signed_epoch=ctx.epoch,
            locked=[],
        )
        ctx.session.add(row)
        leased.add((owner_id, shop.keeper_node_id, shop.structure_entity_id))
        await record(
            ctx,
            "commerce.lease_signed",
            roles={IncidentRole.ACTOR: owner_id, IncidentRole.TARGET: shop.keeper_node_id, IncidentRole.SUBJECT: shop.structure_entity_id},
            facts={"thing": LeaseThing.STRUCTURE, "rent": rent},
            place=shop.settlement_entity_id,
        )
        tally.leases += 1
