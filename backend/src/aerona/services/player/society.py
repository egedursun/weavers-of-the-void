from pydantic import Field

from aerona.core.errors import ValidationFailedError
from aerona.core.grammar import several
from aerona.domain.enums.action import ActionKind
from aerona.domain.enums.economy import CommodityKind
from aerona.domain.enums.entity import EngineKind
from aerona.domain.enums.material import MaterialKind
from aerona.domain.enums.society import Commodity, SocialClass
from aerona.engine.economy.resources import set_resource_yield
from aerona.engine.phases.culture_exchange import order_cultural_contact
from aerona.engine.phases.refugees import order_exodus
from aerona.engine.phases.society_economy import (
    Society,
    incite_class_uprising,
    order_forge,
    send_famine,
    send_plenty,
    set_class_shares,
    set_satisfaction,
    set_stores,
)
from aerona.engine.phases.trade import order_minting
from aerona.engine.phases.works import commission_work
from aerona.engine.phases.world_age import end_golden_age, proclaim_golden_age
from aerona.services.player.scope import Command, Effect, PlayerScope, player_action


class ClassShares(Command):
    entity_id: int
    shares: dict[SocialClass, float] = Field(min_length=1)


class Satisfaction(Command):
    entity_id: int
    values: dict[SocialClass, int] = Field(min_length=1)


class Stores(Command):
    entity_id: int
    stocks: dict[Commodity, int] = Field(min_length=1)


class SocietyTarget(Command):
    entity_id: int


class ClassUprising(Command):
    entity_id: int
    social_class: SocialClass | None = None


class ResourceCommodity(Command):
    resource_id: int
    commodity: CommodityKind
    material: MaterialKind | None = None


class Mint(Command):
    entity_id: int
    metal: MaterialKind | None = None


class Work(Command):
    community_id: int
    kind: EngineKind | None = None


class Exodus(Command):
    origin_id: int
    share_pct: int
    destination_id: int | None = None


class Contact(Command):
    source_id: int
    target_id: int
    first_contact: bool = False


class WorldTarget(Command):
    world_id: int


def _society_values(society: Society) -> dict[str, int | float | str | bool | None]:
    return {f"stock_{key.value}": value for key, value in society.stocks.items()}


@player_action("society:shares", ActionKind.SHAPE_SOCIETY)
async def shape_shares(scope: PlayerScope, command: ClassShares) -> Effect:
    society = await set_class_shares(await scope.context("class_shares"), command.entity_id, command.shares)
    values: dict[str, int | float | str | bool | None] = {f"share_{key.value}": value for key, value in society.shares.items()}
    return Effect("The classes were reshaped.", command.entity_id, values=values)


@player_action("society:satisfaction", ActionKind.SHAPE_SOCIETY)
async def shape_satisfaction(scope: PlayerScope, command: Satisfaction) -> Effect:
    society = await set_satisfaction(await scope.context("satisfaction"), command.entity_id, command.values)
    values: dict[str, int | float | str | bool | None] = {f"satisfaction_{key.value}": value for key, value in society.satisfaction.items()}
    return Effect("The classes' contentment was set.", command.entity_id, values=values)


@player_action("society:stores", ActionKind.SHAPE_SOCIETY)
async def shape_stores(scope: PlayerScope, command: Stores) -> Effect:
    society = await set_stores(await scope.context("stores"), command.entity_id, command.stocks)
    return Effect("The stores were set.", command.entity_id, values=_society_values(society))


@player_action("society:famine", ActionKind.DISASTER)
async def famine(scope: PlayerScope, command: SocietyTarget) -> Effect:
    society = await send_famine(await scope.context("famine"), command.entity_id)
    return Effect("Famine struck the granaries.", command.entity_id, values=_society_values(society))


@player_action("society:plenty", ActionKind.MIRACLE)
async def plenty(scope: PlayerScope, command: SocietyTarget) -> Effect:
    society = await send_plenty(await scope.context("plenty"), command.entity_id)
    return Effect("Plenty filled the granaries.", command.entity_id, values=_society_values(society))


@player_action("society:forge", ActionKind.PRODUCE)
async def forge(scope: PlayerScope, command: SocietyTarget) -> Effect:
    weapon = await order_forge(await scope.context("forge"), command.entity_id)
    return Effect(f"{weapon.name} was forged.", weapon.id, created_ids=(weapon.id,))


@player_action("society:uprising", ActionKind.INCITE_UPRISING)
async def class_uprising(scope: PlayerScope, command: ClassUprising) -> Effect:
    faction = await incite_class_uprising(await scope.context("class_uprising"), command.entity_id, command.social_class)
    return Effect(f"{faction.name} rose up.", faction.id, created_ids=(faction.id,))


@player_action("resource:commodity", ActionKind.EDIT_RECORD)
async def resource_commodity(scope: PlayerScope, command: ResourceCommodity) -> Effect:
    ctx = await scope.context("resource_commodity")
    profile = await set_resource_yield(ctx.session, ctx.rules, command.resource_id, command.commodity, command.material)
    yielded = " ".join(part for part in ((profile.material.value if profile.material else ""), command.commodity.value) if part).replace("_", " ")
    return Effect(f"The resource now yields {yielded}.", command.resource_id, values={"commodity": command.commodity, "material": profile.material})


@player_action("community:mint", ActionKind.MINT_COIN)
async def mint(scope: PlayerScope, command: Mint) -> Effect:
    currency = await order_minting(await scope.context("mint"), command.entity_id, command.metal)
    coin = currency.item_entity_id or command.entity_id
    return Effect(f"{currency.name} was struck.", coin, created_ids=(coin,), values={"currency_id": currency.id})


@player_action("community:work", ActionKind.BUILD)
async def raise_work(scope: PlayerScope, command: Work) -> Effect:
    work = await commission_work(await scope.context("commission_work"), command.community_id, command.kind)
    return Effect(f"{work.name} was raised.", work.id, created_ids=(work.id,))


@player_action("community:exodus", ActionKind.ORDER_EXODUS)
async def exodus(scope: PlayerScope, command: Exodus) -> Effect:
    result = await order_exodus(await scope.context("exodus"), command.origin_id, command.share_pct, command.destination_id)
    shelter = result.shelter.name if result.shelter is not None else "the wilds"
    return Effect(f"{result.refugees} left {result.origin.name} for {shelter}.", result.origin.id, values={"refugees": result.refugees})


@player_action("community:contact", ActionKind.CULTURAL_CONTACT)
async def contact(scope: PlayerScope, command: Contact) -> Effect:
    exchanged = await order_cultural_contact(await scope.context("cultural_contact"), command.source_id, command.target_id, first_contact=command.first_contact)
    return Effect(f"The two communities exchanged {exchanged} customs, words and beliefs.", command.target_id, values={"exchanged": exchanged})


@player_action("world:golden_age", ActionKind.GOLDEN_AGE)
async def golden_age(scope: PlayerScope, command: WorldTarget) -> Effect:
    count = await proclaim_golden_age(await scope.context("golden_age"), command.world_id)
    return Effect(f"A golden age dawned for {several(count, 'community', 'communities')}.", values={"communities": count})


@player_action("world:end_golden_age", ActionKind.GOLDEN_AGE)
async def close_golden_age(scope: PlayerScope, command: WorldTarget) -> Effect:
    if not await end_golden_age(await scope.context("end_golden_age"), command.world_id):
        raise ValidationFailedError("This world is not in a golden age.")
    return Effect("The golden age ended.")
