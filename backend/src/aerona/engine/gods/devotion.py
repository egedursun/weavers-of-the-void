from dataclasses import dataclass
from enum import StrEnum

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.catalog import god_lines
from aerona.constants.units import PERCENT
from aerona.core.errors import ValidationFailedError
from aerona.core.grammar import fill
from aerona.db.repositories.bonds import BondDraft, BondRepository
from aerona.db.repositories.sons import SonRepository
from aerona.db.tables.bonds import BondRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.foreign_gods import ForeignGodRow
from aerona.db.tables.sons import SonRow
from aerona.domain.enums.body import HarmCause
from aerona.domain.enums.bond import BondKind, BondState
from aerona.domain.enums.chronicle import ChronicleKind
from aerona.domain.enums.entity import COMMUNITY_TYPES, EntityStatus, EntityType
from aerona.domain.enums.foreign_god import ForeignGodStatus
from aerona.domain.enums.mind import ActKind
from aerona.domain.enums.son import SonStatus
from aerona.domain.enums.war import WarCause
from aerona.engine.context import TickContext
from aerona.engine.gods.god_death import create_order, epochs_until_resurrection, resurrection_orders
from aerona.engine.gods.mortality import mortal_dies
from aerona.engine.gods.queries import worshippers_of
from aerona.engine.gods.stats import Trait, headcount_floor, headcount_trait, set_trait, trait, trait_or
from aerona.engine.mind.hooks import judged
from aerona.engine.primitives.queries import top_region
from aerona.rules.registry import Rules

PAYMENT_TRAITS = (Trait.WEALTH, Trait.PROSPERITY, Trait.CRAFT)
BLOOD_TYPES = frozenset({EntityType.PEOPLE, EntityType.SETTLEMENT, EntityType.CULT})
RITE_TYPES = frozenset(COMMUNITY_TYPES | {EntityType.MORTAL})


class RiteKind(StrEnum):
    PRAYER = "prayer"
    OFFERING = "offering"
    BLOOD = "blood"
    LIFE = "life"
    RITE = "rite"


class SchemeKind(StrEnum):
    RITE = "rite"
    DESCENT = "descent"
    BARGAIN = "bargain"


@dataclass(frozen=True)
class OrderState:
    id: int
    name: str
    devotion: int
    followers: int


@dataclass(frozen=True)
class ResurrectionState:
    son_id: int
    name: str
    death_epoch: int | None
    earliest_epoch: int | None
    remaining: int
    corpse: EntityRow | None
    orders: tuple[OrderState, ...]
    faithful: tuple[EntityRow, ...]
    devotion: int


@dataclass(frozen=True)
class DevotionResult:
    contribution: int
    devotion: int
    order_id: int | None
    text: str
    slept: bool = False


def scheme_cost(rules: Rules, kind: SchemeKind) -> int:
    death = rules.death
    return {SchemeKind.RITE: death.sibling_rite_cost, SchemeKind.DESCENT: death.sibling_descent_cost, SchemeKind.BARGAIN: death.sibling_bargain_cost}[kind]


async def resurrection_state(session: AsyncSession, rules: Rules, son: SonRow, epoch: int) -> ResurrectionState | None:
    if son.status is not SonStatus.DEAD:
        return None
    orders = await resurrection_orders(session, son.id)
    corpse = await session.get(EntityRow, son.corpse_entity_id) if son.corpse_entity_id is not None else None
    faithful = tuple(entity for entity in await worshippers_of(session, son.id) if entity.entity_type in COMMUNITY_TYPES)
    states = tuple(OrderState(order.id, order.name, trait_or(order, Trait.DEVOTION, 0), trait_or(order, Trait.FOLLOWERS, 0)) for order in orders)
    return ResurrectionState(
        son_id=son.id,
        name=son.name,
        death_epoch=son.death_epoch,
        earliest_epoch=son.death_epoch + rules.death.resurrection_min_epochs if son.death_epoch is not None else None,
        remaining=epochs_until_resurrection(rules, son, epoch),
        corpse=corpse,
        orders=states,
        faithful=faithful,
        devotion=max([state.devotion for state in states], default=0),
    )


async def add_devotion(ctx: TickContext, son: SonRow, amount: int, source: EntityRow | None) -> EntityRow:
    orders = await resurrection_orders(ctx.session, son.id)
    order = max(orders, key=lambda row: (trait_or(row, Trait.DEVOTION, 0), -row.id), default=None)
    if order is None:
        corpse = await ctx.session.get(EntityRow, son.corpse_entity_id) if son.corpse_entity_id is not None else None
        location = corpse
        if location is None and source is not None and source.location_id is not None:
            location = await ctx.session.get(EntityRow, source.location_id)
        description = god_lines.ORDER_REBORN_DESCRIPTION.format(source=source.name if source else god_lines.ORDER_REBORN_SOURCE, son=son.name)
        order = await create_order(ctx, son, location, ctx.rules.death.new_cult_followers, description)
    set_trait(order, Trait.DEVOTION, min(ctx.rules.death.devotion_cap, max(0, trait_or(order, Trait.DEVOTION, 0) + amount)))
    await ctx.session.flush()
    return order


def _pay(entity: EntityRow, amount: int) -> tuple[Trait, int] | None:
    for key in PAYMENT_TRAITS:
        value = trait(entity, key)
        if value is not None:
            if value < amount:
                raise ValidationFailedError(f"{entity.name} is not wealthy enough to make an offering.")
            set_trait(entity, key, value - amount)
            return key, amount
    return None


def can_afford_offering(rules: Rules, entity: EntityRow) -> bool:
    return any((trait(entity, key) or 0) >= rules.death.offering_cost for key in PAYMENT_TRAITS)


async def _same_people(session: AsyncSession, victim: EntityRow, worshipper: EntityRow) -> bool:
    if victim.location_id == worshipper.id:
        return True
    lives = await BondRepository(session).active_between(victim.id, worshipper.id, [BondKind.LIVES_IN, BondKind.MEMBER_OF])
    if lives:
        return True
    victim_region = await top_region(session, victim)
    worshipper_region = await top_region(session, worshipper)
    return victim_region is not None and worshipper_region is not None and victim_region.id == worshipper_region.id


async def resurrection_rite(ctx: TickContext, worshipper: EntityRow, son: SonRow, kind: RiteKind, victim: EntityRow | None = None) -> DevotionResult:
    death = ctx.rules.death
    if son.status is not SonStatus.DEAD:
        raise ValidationFailedError("A resurrection rite is only for a dead god.")
    if worshipper.status is not EntityStatus.CANON or worshipper.entity_type not in RITE_TYPES:
        raise ValidationFailedError("Only a living community or mortal performs the rite.")
    if kind is RiteKind.PRAYER:
        contribution, cost = death.prayer_devotion, god_lines.RITE_COST_PRAYER
    elif kind in (RiteKind.OFFERING, RiteKind.RITE):
        amount = death.offering_cost if kind is RiteKind.OFFERING else death.rite_prosperity_cost
        paid = _pay(worshipper, amount)
        if paid is None:
            raise ValidationFailedError(f"{worshipper.name} has no wealth to offer.")
        contribution = death.offering_devotion if kind is RiteKind.OFFERING else death.rite_devotion
        cost = god_lines.RITE_COST_PAID.format(source=god_lines.RITE_COST_SOURCES[paid[0].value], amount=paid[1])
    elif kind is RiteKind.BLOOD:
        key = headcount_trait(worshipper)
        if key is None:
            raise ValidationFailedError(f"{worshipper.name} is not a crowd that can give a blood sacrifice.")
        current = trait_or(worshipper, key, 0)
        lost = max(1, round(current * death.sacrifice_population_pct / PERCENT))
        set_trait(worshipper, key, max(headcount_floor(ctx.rules, key), current - lost))
        contribution, cost = death.sacrifice_devotion, fill(god_lines.RITE_COST_LIVES, count=lost)
    else:
        chosen = victim if victim is not None else (worshipper if worshipper.entity_type is EntityType.MORTAL else None)
        if chosen is None or chosen.entity_type is not EntityType.MORTAL or chosen.status is not EntityStatus.CANON:
            raise ValidationFailedError("A life sacrifice needs a living named mortal.")
        if chosen.id != worshipper.id and worshipper.entity_type is not EntityType.MORTAL and not await _same_people(ctx.session, chosen, worshipper):
            raise ValidationFailedError(f"{chosen.name} is not one of {worshipper.name}'s people.")
        await mortal_dies(
            ctx, chosen, god_lines.RITE_SACRIFICE_REASON.format(son=son.name), None if chosen.id == worshipper.id else worshipper.id, harm=HarmCause.SACRIFICE
        )
        await judged(ctx, worshipper.id, chosen.id, ActKind.HUMAN_SACRIFICE, note=chosen.name)
        contribution, cost = death.self_sacrifice_devotion, god_lines.RITE_COST_LIFE.format(victim=chosen.name)
    corpse = await ctx.session.get(EntityRow, son.corpse_entity_id) if son.corpse_entity_id is not None else None
    worshipper_region = await top_region(ctx.session, worshipper)
    corpse_region = await top_region(ctx.session, corpse)
    pilgrimage = worshipper_region is not None and corpse_region is not None and worshipper_region.id == corpse_region.id
    if pilgrimage:
        contribution = round(contribution * death.pilgrimage_multiplier_pct / PERCENT)
    order = await add_devotion(ctx, son, contribution, worshipper)
    devotion = trait_or(order, Trait.DEVOTION, 0)
    line = god_lines.RITE
    text = line.render(
        worshipper=worshipper.name,
        kind=god_lines.RITE_KIND_NAMES[kind.value],
        son=son.name,
        cost=cost,
        pilgrimage=god_lines.RITE_PILGRIMAGE if pilgrimage else "",
        devotion=devotion,
    )
    await ctx.chronicle(ChronicleKind.RESURRECTION, text, template_key=line.key, entity_ids=[worshipper.id, order.id])
    ctx.count("rites")
    return DevotionResult(contribution, devotion, order.id, text)


async def _bargain_god(session: AsyncSession, son: SonRow) -> ForeignGodRow | None:
    statement = select(ForeignGodRow).where(ForeignGodRow.status == ForeignGodStatus.AWAKE).order_by(ForeignGodRow.id)
    gods = list(await session.scalars(statement))
    local = [god for god in gods if god.world_id == son.current_world_id]
    pool = local or gods
    return pool[0] if pool else None


async def sibling_scheme(ctx: TickContext, sibling: SonRow, son: SonRow, kind: SchemeKind) -> DevotionResult:
    death = ctx.rules.death
    if son.status is not SonStatus.DEAD:
        raise ValidationFailedError("A resurrection scheme is only for a dead sibling.")
    if sibling.status is not SonStatus.ACTIVE or sibling.id == son.id:
        raise ValidationFailedError("Only an awake sibling can scheme.")
    cost = scheme_cost(ctx.rules, kind)
    if sibling.essence < cost:
        raise ValidationFailedError(f"{kind.value} needs {cost} essence; {sibling.name} has {sibling.essence} (world rule death.sibling_{kind.value}_cost).")
    contribution = 0
    extra = ""
    slept = False
    if kind is SchemeKind.RITE:
        contribution = death.sibling_rite_devotion
    elif kind is SchemeKind.DESCENT:
        if ctx.rng("descent").chance(death.sibling_descent_success):
            contribution = death.sibling_descent_devotion
            extra = god_lines.SCHEME_DESCENT_SUCCESS.format(son=son.name)
        else:
            sibling.status = SonStatus.ASLEEP
            sibling.sleep_epochs_left = death.sibling_descent_sleep_epochs
            slept = True
            extra = god_lines.SCHEME_DESCENT_FAILURE.format(sibling=sibling.name, epochs=death.sibling_descent_sleep_epochs)
    else:
        god = await _bargain_god(ctx.session, son)
        if god is None:
            raise ValidationFailedError("There is no awake foreign god to bargain with.")
        faithful = [entity for entity in await worshippers_of(ctx.session, son.id) if entity.entity_type in COMMUNITY_TYPES]
        if faithful:
            community = faithful[0]
            bonds = BondRepository(ctx.session)
            await bonds.close_between(community.id, son.id, [BondKind.WORSHIPS], ctx.epoch, "bargain")
            await bonds.connect(BondDraft(community.id, god.id, BondKind.WORSHIPS, ctx.epoch, god_lines.SCHEME_BARGAIN_VOW.format(sibling=sibling.name)))
            extra = god_lines.SCHEME_BARGAIN_PRICE.format(community=community.name, god=god.name)
        else:
            extra = god_lines.SCHEME_BARGAIN_PROMISE.format(god=god.name)
        contribution = death.sibling_bargain_devotion
    sibling.essence -= cost
    order = await add_devotion(ctx, son, contribution, None) if contribution else None
    devotion = trait_or(order, Trait.DEVOTION, 0) if order is not None else 0
    if contribution:
        await SonRepository(ctx.session).change_relation(sibling.id, son.id, death.sibling_scheme_relation_gain, god_lines.SCHEME_RELATION_NOTE)
    line = god_lines.SCHEME
    text = line.render(
        sibling=sibling.name,
        kind=god_lines.SCHEME_KIND_NAMES[kind.value],
        son=son.name,
        cost=cost,
        extra=extra,
        devotion=god_lines.SCHEME_DEVOTION.format(devotion=devotion) if order is not None else "",
    )
    await ctx.chronicle(ChronicleKind.RESURRECTION, text, template_key=line.key, entity_ids=[order.id] if order is not None else [], son_id=sibling.id)
    ctx.count("schemes")
    await ctx.session.flush()
    return DevotionResult(contribution, devotion, order.id if order is not None else None, text, slept)


async def scatter_bones(ctx: TickContext, sibling: SonRow, son: SonRow) -> DevotionResult:
    death = ctx.rules.death
    if son.status is not SonStatus.DEAD:
        raise ValidationFailedError("Only a dead sibling's bones can be scattered.")
    if sibling.status is not SonStatus.ACTIVE or sibling.id == son.id:
        raise ValidationFailedError("Only an awake sibling can scatter the bones.")
    cost = death.scatter_bones_cost
    if sibling.essence < cost:
        raise ValidationFailedError(f"Scattering the bones needs {cost} essence; {sibling.name} has {sibling.essence}.")
    sibling.essence -= cost
    bonds = BondRepository(ctx.session)
    orders = await resurrection_orders(ctx.session, son.id)
    for order in orders:
        set_trait(order, Trait.DEVOTION, max(0, trait_or(order, Trait.DEVOTION, 0) - death.scatter_bones_devotion_loss))
        if not await bonds.exists_between(order.id, sibling.id, BondKind.ENEMY):
            await bonds.connect(
                BondDraft(order.id, sibling.id, BondKind.ENEMY, ctx.epoch, god_lines.SCATTER_ENEMY.format(son=son.name), war_cause=WarCause.SCHISM)
            )
    await SonRepository(ctx.session).change_relation(sibling.id, son.id, -death.scatter_bones_devotion_loss / 2, god_lines.SCATTER_NOTE)
    line = god_lines.SCATTER
    text = line.render(sibling=sibling.name, son=son.name, cost=cost, loss=death.scatter_bones_devotion_loss)
    await ctx.chronicle(ChronicleKind.RESURRECTION, text, template_key=line.key, entity_ids=[order.id for order in orders], son_id=sibling.id)
    ctx.count("scatterings")
    await ctx.session.flush()
    return DevotionResult(-death.scatter_bones_devotion_loss, max([trait_or(order, Trait.DEVOTION, 0) for order in orders], default=0), None, text)


async def awake_foreign_gods(session: AsyncSession) -> list[ForeignGodRow]:
    statement = select(ForeignGodRow).where(ForeignGodRow.status == ForeignGodStatus.AWAKE).order_by(ForeignGodRow.id)
    return list(await session.scalars(statement))


async def worships_node(session: AsyncSession, entity_id: int, node_id: int) -> bool:
    statement = select(BondRow.id).where(
        BondRow.source_node_id == entity_id, BondRow.target_node_id == node_id, BondRow.kind == BondKind.WORSHIPS, BondRow.state == BondState.ACTIVE
    )
    return await session.scalar(statement.limit(1)) is not None
