import math
from dataclasses import dataclass, replace

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.catalog import god_lines
from aerona.catalog.entity_types import can_contain
from aerona.catalog.stats import max_essence, max_hp
from aerona.constants.units import PERCENT
from aerona.db.repositories.bonds import BondDraft, BondRepository
from aerona.db.repositories.entities import EntityDraft, EntityRepository
from aerona.db.repositories.names import NameRepository
from aerona.db.repositories.sons import SonRepository
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.lore import ThreadLinkRow, ThreadRow
from aerona.db.tables.society import ResurrectionOrderRow
from aerona.db.tables.sons import SonRow
from aerona.domain.enums.bond import BondKind
from aerona.domain.enums.chronicle import ChronicleKind, ThreadLinkRole
from aerona.domain.enums.cosmography import PhenomenonCause, PhenomenonKind
from aerona.domain.enums.entity import EngineKind, EntityFlag, EntityOrigin, EntityStatus, EntityType
from aerona.domain.enums.son import SonDeathCause, SonStatus, Stat
from aerona.domain.enums.transform import GodDeathMode, TransformKind
from aerona.domain.models.entity_stats import CultStats, PlaceStats, SpiritStats
from aerona.domain.models.stats import STAT_CEILING, STAT_FLOOR
from aerona.engine.context import TickContext
from aerona.engine.cosmos.phenomena import form_phenomenon
from aerona.engine.divine.wounds import death_cause
from aerona.engine.gods.essence import gain
from aerona.engine.gods.queries import cosmos_row, creator_row, sons, worshippers_of
from aerona.engine.gods.stats import Trait, set_trait, trait_or
from aerona.engine.interconnect.annotations import reads, writes
from aerona.engine.primitives.numbers import clamp_int, clamp_percent
from aerona.engine.primitives.queries import canon, living_sons, top_region
from aerona.engine.primitives.stats import headcount
from aerona.engine.transform.bodies import living_body
from aerona.engine.transform.ledger import Ledger
from aerona.engine.transform.moves import move_bonds
from aerona.engine.transform.record import blocked, record_transformation
from aerona.rules.registry import Rules

FADING_WARN_TWO = 2
FADING_WARN_ONE = 1
DEVOTION_LOG_FLOOR = 10


@dataclass(frozen=True)
class GodDeath:
    corpse: EntityRow | None
    shade: EntityRow | None
    order: EntityRow | None
    apostates: int
    loyal: int


@dataclass(frozen=True)
class FadingStatus:
    son_id: int
    name: str
    status: SonStatus
    existence: int
    threshold: int
    counter: int
    duration: int
    fading: bool
    epochs_left: int | None


async def resurrection_orders(session: AsyncSession, son_id: int) -> list[EntityRow]:
    statement = (
        select(EntityRow)
        .join(ResurrectionOrderRow, ResurrectionOrderRow.cult_entity_id == EntityRow.id)
        .where(ResurrectionOrderRow.son_id == son_id, ResurrectionOrderRow.completed_epoch.is_(None), EntityRow.status == EntityStatus.CANON)
        .order_by(EntityRow.id)
    )
    return list(await session.scalars(statement))


async def _home_region(ctx: TickContext, son: SonRow, worshippers: list[EntityRow]) -> EntityRow | None:
    anchor = await ctx.session.get(EntityRow, son.anchor_entity_id) if son.anchor_entity_id is not None else None
    home = await top_region(ctx.session, anchor)
    if home is None and worshippers:
        home = await top_region(ctx.session, worshippers[0])
    if home is not None:
        return home
    regions = await canon(ctx.session, [EntityType.REGION])
    local = [region for region in regions if region.world_id == son.current_world_id]
    pool = local or regions
    return ctx.rng("god_death_home").pick(pool) if pool else None


async def _create(ctx: TickContext, draft: EntityDraft) -> EntityRow:
    name = await NameRepository(ctx.session).unique_name(draft.name)
    location = await ctx.session.get(EntityRow, draft.location_id) if draft.location_id is not None else None
    location_id = draft.location_id if location is not None and can_contain(location.entity_type, draft.entity_type) else None
    return await EntityRepository(ctx.session).create(replace(draft, name=name, location_id=location_id))


async def leave_cosmos(ctx: TickContext, son: SonRow, cause: str, successor_id: int, ledger: Ledger) -> GodDeath:
    moved = await move_bonds(ctx, ledger, son.id, successor_id, kinds=(BondKind.WORSHIPS,), reason=god_lines.OUTER_CULT_BOND)
    for column, value in (
        ("status", SonStatus.DEAD),
        ("death_epoch", ctx.epoch),
        ("death_cause", SonDeathCause.COSMIC_HORROR),
        ("rebel", False),
        ("fading_epochs", 0),
        ("body_entity_id", None),
    ):
        ledger.set(son, column, value)
    creator = await creator_row(ctx.session)
    successor = await ctx.session.get(EntityRow, successor_id)
    line = god_lines.GOD_LEFT_COSMOS
    await ctx.chronicle(
        ChronicleKind.DEATH,
        line.render(creator=creator.name if creator else "", son=son.name, cause=cause, successor=successor.name if successor else "", moved=moved),
        template_key=line.key,
        entity_ids=[successor_id],
        son_id=son.id,
    )
    ctx.count("god_deaths")
    await ctx.session.flush()
    return GodDeath(None, None, None, 0, moved)


async def sway_siblings(ctx: TickContext, son: SonRow) -> None:
    rules = ctx.rules.death
    repository = SonRepository(ctx.session)
    for sibling in await living_sons(ctx.session):
        relation = await repository.relation(sibling.id, son.id)
        if relation <= -rules.god_death_relation_threshold:
            sibling.fame += rules.god_death_enemy_renown
        elif relation >= rules.god_death_relation_threshold:
            sibling.wrath = clamp_percent(sibling.wrath + rules.god_death_friend_wrath)


async def god_death(
    ctx: TickContext,
    son: SonRow,
    cause: str,
    death_cause: SonDeathCause,
    *,
    mode: GodDeathMode = GodDeathMode.IN_COSMOS,
    successor_id: int | None = None,
    ledger: Ledger | None = None,
) -> GodDeath:
    if mode is GodDeathMode.LEFT_COSMOS and successor_id is not None:
        return await leave_cosmos(ctx, son, cause, successor_id, ledger or Ledger())
    rules = ctx.rules.death
    session = ctx.session
    worshippers = await worshippers_of(session, son.id)
    home = await _home_region(ctx, son, worshippers)
    world_id = home.world_id if home is not None else son.current_world_id
    corpse = await _create(
        ctx,
        EntityDraft(
            name=god_lines.CORPSE_NAME.format(son=son.name),
            entity_type=EntityType.PLACE,
            description=god_lines.CORPSE_DESCRIPTION.format(
                son=son.name,
                title=son.title,
                cause=cause,
                where=god_lines.CORPSE_WHERE_LAND.format(home=home.name) if home is not None else god_lines.CORPSE_WHERE_WORLD,
                domain_1=son.domain_primary.value,
                domain_2=son.domain_secondary.value,
            ),
            stats=PlaceStats(danger=rules.god_corpse_danger, fertility=rules.god_corpse_fertility, mystery=rules.god_corpse_mystery),
            power_level=rules.god_corpse_power,
            origin=EntityOrigin.ENGINE,
            birth_epoch=ctx.epoch,
            world_id=world_id,
            location_id=home.id if home is not None else None,
            engine_kind=EngineKind.GOD_CORPSE,
            pending_name=True,
            split_title=False,
        ),
    )
    if home is not None:
        await form_phenomenon(ctx, PhenomenonKind.GOD_CORPSE_AURA, home, PhenomenonCause.GOD_DEATH, cause_node_id=son.id)
    await record_transformation(ctx, TransformKind.GOD_CORPSE, son.id, corpse.id)
    shade = await _create(
        ctx,
        EntityDraft(
            name=god_lines.SHADE_NAME.format(son=son.name),
            entity_type=EntityType.SPIRIT,
            description=god_lines.SHADE_DESCRIPTION.format(son=son.name),
            stats=SpiritStats(strength=rules.god_shade_strength, unrest=rules.god_shade_unrest),
            power_level=rules.god_shade_power,
            origin=EntityOrigin.ENGINE,
            birth_epoch=ctx.epoch,
            world_id=corpse.world_id,
            location_id=corpse.id,
            engine_kind=EngineKind.GOD_SHADE,
            pending_name=True,
            split_title=False,
        ),
    )
    bonds = BondRepository(session)
    await bonds.connect(BondDraft(corpse.id, son.id, BondKind.TELLS_OF, ctx.epoch, god_lines.CORPSE_BOND))
    await bonds.connect(BondDraft(shade.id, son.id, BondKind.DESCENDS_FROM, ctx.epoch, god_lines.SHADE_BOND))
    rng = ctx.rng("apostasy")
    entities = EntityRepository(session)
    loyal: list[EntityRow] = []
    apostates = 0
    for worshipper in worshippers:
        if rng.chance(rules.apostasy_chance):
            await bonds.close_between(worshipper.id, son.id, [BondKind.WORSHIPS], ctx.epoch, "apostasy")
            await entities.add_flag(worshipper.id, EntityFlag.GODLESS, ctx.epoch)
            apostates += 1
        else:
            loyal.append(worshipper)
    total = sum(headcount(entity) or rules.resurrection_cult_default_population for entity in loyal)
    followers = clamp_int(total * rules.resurrection_cult_join_pct / PERCENT, rules.resurrection_cult_min_followers, rules.resurrection_cult_max_followers)
    order = await create_order(ctx, son, corpse, followers, god_lines.ORDER_DESCRIPTION.format(son=son.name))
    thread = ThreadRow(epoch=ctx.epoch, text=god_lines.DEATH_THREAD.format(son=son.name, where=home.name if home else god_lines.DEATH_THREAD_WORLD))
    session.add(thread)
    await session.flush()
    session.add_all(ThreadLinkRow(thread_id=thread.id, entity_id=entity.id, role=ThreadLinkRole.RELATED, epoch=ctx.epoch) for entity in (corpse, order, shade))
    son.status = SonStatus.DEAD
    son.death_epoch = ctx.epoch
    son.death_cause = death_cause
    son.corpse_entity_id = corpse.id
    son.body_entity_id = None
    son.rebel = False
    son.fading_epochs = 0
    creator = await creator_row(session)
    if creator is not None:
        gain(creator, son.essence / ctx.rules.death.dead_essence_divisor)
    await sway_siblings(ctx, son)
    line = god_lines.GOD_DEATH
    await ctx.chronicle(
        ChronicleKind.DEATH,
        line.render(creator=creator.name if creator else "", son=son.name, cause=cause, corpse=corpse.name, apostates=apostates, loyal=len(loyal)),
        template_key=line.key,
        entity_ids=[corpse.id, shade.id, order.id],
        son_id=son.id,
    )
    ctx.count("god_deaths")
    await session.flush()
    return GodDeath(corpse, shade, order, apostates, len(loyal))


async def create_order(ctx: TickContext, son: SonRow, location: EntityRow | None, followers: int, description: str) -> EntityRow:
    rules = ctx.rules.death
    order = await _create(
        ctx,
        EntityDraft(
            name=god_lines.ORDER_NAME.format(son=son.name),
            entity_type=EntityType.CULT,
            description=description,
            stats=CultStats(followers=followers, zeal=rules.resurrection_cult_zealotry, influence=rules.resurrection_cult_influence, devotion=0),
            power_level=rules.resurrection_cult_power,
            origin=EntityOrigin.ENGINE,
            birth_epoch=ctx.epoch,
            world_id=location.world_id if location is not None else son.current_world_id,
            location_id=location.id if location is not None else None,
            engine_kind=EngineKind.RESURRECTION_ORDER,
            pending_name=True,
            split_title=False,
        ),
    )
    ctx.session.add(ResurrectionOrderRow(cult_entity_id=order.id, son_id=son.id))
    await BondRepository(ctx.session).connect(BondDraft(order.id, son.id, BondKind.WORSHIPS, ctx.epoch, god_lines.ORDER_WORSHIP))
    await ctx.session.flush()
    return order


async def resurrect_son(ctx: TickContext, son: SonRow, path: str) -> None:
    rules = ctx.rules.death
    son.status = SonStatus.ACTIVE
    son.existence = rules.resurrected_existence
    son.hp = round(max_hp(ctx.rules, son.endurance) / rules.resurrected_hp_divisor)
    son.essence = round(max_essence(ctx.rules, son.might) / rules.resurrected_essence_divisor)
    son.fame += rules.resurrected_renown
    for stat in Stat:
        setattr(son, stat.value, clamp_int(son.stat(stat) - rules.resurrected_stat_loss, STAT_FLOOR, STAT_CEILING))
    son.death_epoch = None
    son.death_cause = None
    son.fading_epochs = 0
    entities = EntityRepository(ctx.session)
    corpse = await ctx.session.get(EntityRow, son.corpse_entity_id) if son.corpse_entity_id is not None else None
    if corpse is not None:
        await entities.add_flag(corpse.id, EntityFlag.EMPTY_TOMB, ctx.epoch)
    for order_row in await ctx.session.scalars(
        select(ResurrectionOrderRow).where(ResurrectionOrderRow.son_id == son.id, ResurrectionOrderRow.completed_epoch.is_(None))
    ):
        order_row.completed_epoch = ctx.epoch
        order = await ctx.session.get(EntityRow, order_row.cult_entity_id)
        if order is not None:
            set_trait(order, Trait.DEVOTION, 0)
            await entities.add_flag(order.id, EntityFlag.RESURRECTION_COMPLETE, ctx.epoch)
    line = god_lines.SON_RESURRECTED
    tomb = god_lines.EMPTY_TOMB_CLAUSE.format(corpse=corpse.name) if corpse is not None else ""
    await ctx.chronicle(
        ChronicleKind.RESURRECTION,
        line.render(son=son.name, path=path, tomb=tomb),
        template_key=line.key,
        entity_ids=[corpse.id] if corpse is not None else [],
        son_id=son.id,
    )
    ctx.count("resurrections")
    await ctx.session.flush()


async def creator_kills_son(ctx: TickContext, son: SonRow, reason: str | None = None) -> GodDeath:
    rules = ctx.rules.death
    creator = await creator_row(ctx.session)
    cause = reason or god_lines.GOD_DEATH_KILLED.format(creator=creator.name if creator else "")
    repository = SonRepository(ctx.session)
    relations = {sibling.id: await repository.relation(sibling.id, son.id) for sibling in await living_sons(ctx.session) if sibling.id != son.id}
    death = await god_death(ctx, son, cause, SonDeathCause.KILLED_BY_CREATOR)
    for sibling in await living_sons(ctx.session):
        sibling.loyalty = clamp_percent(sibling.loyalty + rules.kill_son_loyalty_gain)
        if relations.get(sibling.id, 0) > 0:
            sibling.wrath = clamp_percent(sibling.wrath + rules.kill_son_friend_wrath)
    await ctx.session.flush()
    return death


def fading_status(rules: Rules, son: SonRow) -> FadingStatus:
    threshold = rules.death.fading_threshold
    duration = rules.death.fading_death_epochs
    fading = son.existence <= threshold
    return FadingStatus(
        son_id=son.id,
        name=son.name,
        status=son.status,
        existence=son.existence,
        threshold=threshold,
        counter=son.fading_epochs,
        duration=duration,
        fading=fading,
        epochs_left=max(0, duration - son.fading_epochs) if fading else None,
    )


def epochs_until_resurrection(rules: Rules, son: SonRow, epoch: int) -> int:
    died = son.death_epoch if son.death_epoch is not None else epoch
    return max(0, died + rules.death.resurrection_min_epochs - epoch)


def devotion_gain(rules: Rules, order: EntityRow) -> int:
    death = rules.death
    followers = trait_or(order, Trait.FOLLOWERS, DEVOTION_LOG_FLOOR) or DEVOTION_LOG_FLOOR
    return round(
        math.log10(max(DEVOTION_LOG_FLOOR, followers)) * death.devotion_follower_log_mult
        + trait_or(order, Trait.INFLUENCE, 0) / death.devotion_influence_divisor
        + trait_or(order, Trait.ZEAL, 0) / death.devotion_zealotry_divisor
    )


async def tend_dead_son(ctx: TickContext, son: SonRow) -> bool:
    rules = ctx.rules.death
    rng = ctx.rng(f"resurrection.{son.id}")
    corpse = await ctx.session.get(EntityRow, son.corpse_entity_id) if son.corpse_entity_id is not None else None
    for order in await resurrection_orders(ctx.session, son.id):
        devotion = min(rules.devotion_cap, trait_or(order, Trait.DEVOTION, 0) + devotion_gain(ctx.rules, order))
        set_trait(order, Trait.DEVOTION, devotion)
        ready = devotion >= rules.resurrection_devotion_required and corpse is not None and corpse.status is EntityStatus.CANON
        if ready and epochs_until_resurrection(ctx.rules, son, ctx.epoch) == 0 and rng.chance(rules.cult_resurrection_chance):
            await resurrect_son(ctx, son, god_lines.RESURRECTION_BY_RITE.format(order=order.name))
            return True
    await ctx.session.flush()
    return False


async def fallen_body_died(ctx: TickContext, mortal: EntityRow) -> None:
    son = await ctx.session.scalar(select(SonRow).where(SonRow.body_entity_id == mortal.id, SonRow.status == SonStatus.FALLEN))
    if son is not None:
        await god_death(ctx, son, god_lines.FALLEN_BODY_DIED.format(body=mortal.name), SonDeathCause.OTHER)


async def falls_instead(ctx: TickContext, son: SonRow) -> bool:
    return await living_body(ctx.session, son) is not None and not await blocked(ctx, TransformKind.FALL, son.id)


async def tend_living_son(ctx: TickContext, son: SonRow) -> bool:
    rules = ctx.rules.death
    if son.status is SonStatus.FALLEN and not rules.fading_applies_to_fallen:
        son.fading_epochs = 0
        return False
    if son.existence > rules.fading_threshold:
        son.fading_epochs = 0
        return False
    son.fading_epochs += 1
    left = rules.fading_death_epochs - son.fading_epochs
    if left <= 0:
        if await falls_instead(ctx, son):
            return False
        await god_death(ctx, son, god_lines.GOD_DEATH_FADED, await death_cause(ctx.session, son.id))
        return True
    line = None
    if left == FADING_WARN_TWO:
        line = god_lines.FADING_TWO
    elif left == FADING_WARN_ONE:
        line = god_lines.FADING_ONE
    elif son.fading_epochs == 1:
        line = god_lines.FADING_MANY
    if line is not None:
        await ctx.chronicle(ChronicleKind.EXISTENCE, line.render(son=son.name, left=left), template_key=line.key, son_id=son.id)
    return False


@reads("table.cosmos")
@writes("table.sons")
async def gods_fate(ctx: TickContext) -> None:
    if await cosmos_row(ctx.session) is None:
        return
    for son in await sons(ctx.session):
        if son.status is SonStatus.DEAD:
            await tend_dead_son(ctx, son)
        elif await tend_living_son(ctx, son):
            ctx.count("faded")
    await ctx.session.flush()
