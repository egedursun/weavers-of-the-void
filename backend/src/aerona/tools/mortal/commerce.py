from typing import Any

from pydantic import Field

from aerona.constants.units import PERCENT
from aerona.core.grammar import spoken
from aerona.db.tables.agrarian import BrandRow
from aerona.db.tables.commerce import LeaseRow, PromotionRow, ShopGoodRow, ShopRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.structures import StructureProfileRow
from aerona.db.write_guard import held
from aerona.domain.enums.action import ActionKind
from aerona.domain.enums.agent import AgentKind
from aerona.domain.enums.bond import BondKind
from aerona.domain.enums.commerce import LeaseDefault, LeaseThing, PromotionMedium, ShopForm
from aerona.domain.enums.economy import CommodityKind
from aerona.domain.enums.entity import EntityStatus, EntityType
from aerona.domain.enums.modifier import IncidentRole
from aerona.engine.commerce.dealings import media_known, promotion_cost
from aerona.engine.economy.purse import points_of
from aerona.engine.primitives.queries import active_bonds
from aerona.prompts import MortalToolId
from aerona.prompts.tools.results import MortalResult, result
from aerona.tools.framework.call import MortalCall
from aerona.tools.framework.inputs import ToolInput
from aerona.tools.framework.spec import ToolMeta, ToolSpec, mortal_standard_action
from aerona.tools.framework.validation import fail

GOODS_MAX = 6
RENT_MAX = 100
TERM_MAX = 10
LEASE_THINGS = {
    EntityType.REGION: LeaseThing.LAND,
    EntityType.STRUCTURE: LeaseThing.STRUCTURE,
    EntityType.VESSEL: LeaseThing.VESSEL,
    EntityType.ITEM: LeaseThing.ITEM,
    EntityType.BEAST: LeaseThing.ANIMAL,
}


class OpenShopInput(ToolInput):
    form: ShopForm
    goods_kinds: list[CommodityKind] = Field(min_length=1, max_length=GOODS_MAX)
    structure_id: int | None = None


class PromoteInput(ToolInput):
    medium: PromotionMedium
    claim_accuracy: int = Field(ge=0, le=PERCENT)
    reach: int = Field(default=30, ge=0, le=PERCENT)
    commodity: CommodityKind | None = None
    brand_id: int | None = None


class LeaseOutInput(ToolInput):
    thing_id: int
    lessee_id: int
    rent: int = Field(ge=0, le=RENT_MAX)
    term: int = Field(default=2, ge=1, le=TERM_MAX)
    on_default: LeaseDefault = LeaseDefault.EVICTION


async def open_shop(call: MortalCall, args: OpenShopInput) -> str:
    town = await call.session.get(EntityRow, call.me.location_id) if call.me.location_id is not None else None
    if town is None or town.entity_type is not EntityType.SETTLEMENT:
        fail(MortalResult.COMMERCE_REFUSED, why="a shop opens only in a town")
    if held(town.id):
        fail(MortalResult.COMMERCE_REFUSED, why="a god holds this town as it is")
    if args.structure_id is not None:
        profile = await call.session.get(StructureProfileRow, args.structure_id)
        if profile is None or profile.host_entity_id != town.id:
            fail(MortalResult.COMMERCE_REFUSED, why="that building is not in your town")
    shop = ShopRow(
        settlement_entity_id=town.id,
        structure_entity_id=args.structure_id,
        keeper_node_id=call.me.id,
        form=args.form,
        margin=call.rules.commerce.retail_margin_pct,
        opened_epoch=call.epoch,
        locked=[],
    )
    call.session.add(shop)
    await call.session.flush()
    call.session.add_all(ShopGoodRow(shop_id=shop.id, commodity=kind, keeper_node_id=call.me.id, locked=[]) for kind in sorted(set(args.goods_kinds)))
    call.target(town.id)
    await call.record("commerce.shop_opened", roles={IncidentRole.ACTOR: call.me.id, IncidentRole.PLACE: town.id}, facts={"form": args.form}, place=town.id)
    goods = ", ".join(spoken(kind) for kind in sorted(set(args.goods_kinds)))
    return result(MortalResult.SHOP_OPENED, form=spoken(args.form), town=town.name, goods=goods)


async def promote(call: MortalCall, args: PromoteInput) -> str:
    if args.brand_id is not None:
        brand = await call.session.get(BrandRow, args.brand_id)
        if brand is None or brand.owner_node_id != call.me.id:
            fail(MortalResult.COMMERCE_REFUSED, why="you own no such brand")
    if args.medium is PromotionMedium.MEDIA and not await media_known(call.session, call.me.location_id):
        fail(MortalResult.COMMERCE_REFUSED, why="your town has no means of reaching many at once")
    cost = promotion_cost(args.reach)
    if await points_of(call.session, call.me) < cost:
        fail(MortalResult.COMMERCE_REFUSED, why=f"spreading word that far costs {cost} of wealth each season and you have less")
    call.session.add(
        PromotionRow(
            holder_node_id=call.me.id,
            commodity=args.commodity,
            brand_id=args.brand_id,
            medium=args.medium,
            reach=args.reach,
            cost=cost,
            accuracy=args.claim_accuracy,
            started_epoch=call.epoch,
            locked=[],
        )
    )
    call.target(call.me.id)
    await call.record(
        "commerce.promotion_run", roles={IncidentRole.ACTOR: call.me.id}, facts={"medium": args.medium, "reach": args.reach}, place=call.me.location_id
    )
    return result(MortalResult.PROMOTED, medium=spoken(args.medium), reach=args.reach, cost=cost)


async def lease_out(call: MortalCall, args: LeaseOutInput) -> str:
    thing = await call.session.get(EntityRow, args.thing_id)
    owned = thing is not None and any(bond.target_node_id == thing.id for bond in await active_bonds(call.session, [BondKind.OWNS], sources=[call.me.id]))
    kind = LEASE_THINGS.get(thing.entity_type) if thing is not None else None
    if thing is None or not owned or kind is None:
        fail(MortalResult.COMMERCE_REFUSED, why="you can lease out only land, a building, a vessel, an item or a beast you own")
    lessee = await call.session.get(EntityRow, args.lessee_id)
    if lessee is None or lessee.status is not EntityStatus.CANON or lessee.id == call.me.id:
        fail(MortalResult.COMMERCE_REFUSED, why="there is no such lessee")
    if held(thing.id) or held(lessee.id):
        fail(MortalResult.COMMERCE_REFUSED, why="a god holds it as it is")
    call.session.add(
        LeaseRow(
            owner_node_id=call.me.id,
            lessee_node_id=lessee.id,
            thing_node_id=thing.id,
            thing=kind,
            rent=args.rent,
            term_epochs=args.term,
            on_default=args.on_default,
            signed_epoch=call.epoch,
            locked=[],
        )
    )
    call.target(lessee.id)
    await call.record(
        "commerce.lease_signed",
        roles={IncidentRole.ACTOR: call.me.id, IncidentRole.TARGET: lessee.id, IncidentRole.SUBJECT: thing.id},
        facts={"thing": kind, "rent": args.rent},
        place=call.me.location_id,
    )
    return result(MortalResult.LEASED_OUT, thing=thing.name, lessee=lessee.name, rent=args.rent)


def specs() -> list[ToolSpec[MortalCall, Any]]:
    meta = ToolMeta(ActionKind.ESTABLISH_TRADE, mortal_standard_action)
    return [
        ToolSpec(MortalToolId.OPEN_SHOP, AgentKind.MORTAL, OpenShopInput, meta, open_shop),
        ToolSpec(MortalToolId.PROMOTE, AgentKind.MORTAL, PromoteInput, meta, promote),
        ToolSpec(MortalToolId.LEASE_OUT, AgentKind.MORTAL, LeaseOutInput, meta, lease_out),
    ]
