from collections.abc import Awaitable, Callable, Mapping
from dataclasses import dataclass

from sqlalchemy import delete, select

from aerona.catalog.effect_packages import PACKAGES
from aerona.catalog.life.divine import HUNGER_LABELS
from aerona.catalog.outer_bargains import BARGAIN_GAINS
from aerona.constants.units import PERCENT
from aerona.core.dispatch import Handlers
from aerona.core.grammar import spoken
from aerona.core.random import SeededRandom
from aerona.core.total import total
from aerona.db.tables.bonds import BondRow
from aerona.db.tables.celestial import StarRow, WorldRow
from aerona.db.tables.culture import HolderLevelRow, LegendProfileRow
from aerona.db.tables.divine import BreachPointRow, OuterBeingProfileRow
from aerona.db.tables.entities import EntityFlagRow, EntityRow
from aerona.db.tables.faith import CultTenetRow, SpiritProfileRow
from aerona.db.tables.foreign_gods import OuterBargainRow
from aerona.db.tables.lore import LexemeRow
from aerona.db.tables.sons import SonPowerRow, SonRow
from aerona.db.write_guard import held
from aerona.domain.enums.affliction import Transmission
from aerona.domain.enums.bond import BondKind, BondState
from aerona.domain.enums.chronicle import ChronicleKind
from aerona.domain.enums.divine import BargainGain, BargainPrice, DivineWoundKind, OuterHunger, WoundCause
from aerona.domain.enums.domain import Domain
from aerona.domain.enums.entity import COMMUNITY_TYPES, EntityFlag, EntityStatus, EntityType
from aerona.domain.enums.faith import AfterlifeState, TenetKind
from aerona.domain.enums.limits import POWER_SLOTS
from aerona.domain.enums.modifier import IncidentRole
from aerona.domain.enums.outer import OuterFate
from aerona.domain.enums.society import KnowledgeBranch
from aerona.domain.enums.son import PowerEffect
from aerona.domain.enums.world import DARK_STAR_TYPES
from aerona.domain.models.entity_stats import CultStats, revised
from aerona.engine.body.afflictions import afflict
from aerona.engine.context import TickContext
from aerona.engine.cosmos.sanity import shift_sanity
from aerona.engine.divine.gods import faithful_communities
from aerona.engine.divine.wounds import inflict
from aerona.engine.lifecycle.states import ended_ids
from aerona.engine.primitives.numbers import clamp_int, clamp_percent
from aerona.engine.primitives.queries import connect
from aerona.engine.primitives.records import RecordSpec, open_record, retire_in
from aerona.engine.primitives.stats import FOLLOWERS_KEY, POPULATION_KEY, put_stat, stat_or
from aerona.engine.recording.record import record

LINE_DEPTH = 3

VOID_TENETS = (TenetKind.VOID_COMMUNION, TenetKind.FEEDING_THE_HUNGER, TenetKind.WHISPERED_SECRETS)


def reach_of(rules_size_per_region: int, being: EntityRow) -> int:
    return 1 + stat_or(being, "size", 0) // max(1, rules_size_per_region)


def oppose_cost(rules_cost_per_size: int, being: EntityRow) -> int:
    return max(1, round(stat_or(being, "size", 0) * rules_cost_per_size / PERCENT))


def drafted_outer(seed: int, being: EntityRow, epoch: int) -> OuterBeingProfileRow:
    hunger = SeededRandom.for_epoch(seed, 0, f"hunger.{being.id}").pick(list(OuterHunger))
    return OuterBeingProfileRow(outer_entity_id=being.id, hunger=hunger, reach=1, fed=0, updated_epoch=epoch, locked=[])


async def outer_profile(ctx: TickContext, being: EntityRow) -> OuterBeingProfileRow:
    row = await ctx.session.get(OuterBeingProfileRow, being.id)
    if row is None:
        row = drafted_outer(ctx.environment.world_seed, being, ctx.epoch)
        ctx.session.add(row)
        await ctx.session.flush()
    return row


EATERS: Handlers[OuterHunger, Callable[[TickContext, EntityRow, int], Awaitable[int]]] = Handlers(OuterHunger)


@EATERS.on(OuterHunger.SOULS)
async def eat_souls(ctx: TickContext, being: EntityRow, bite: int) -> int:
    souls = await ctx.session.scalars(
        select(EntityRow)
        .join(SpiritProfileRow, SpiritProfileRow.spirit_entity_id == EntityRow.id)
        .where(EntityRow.world_id == being.world_id, EntityRow.status == EntityStatus.CANON, SpiritProfileRow.state == AfterlifeState.IN_REALM)
        .order_by(EntityRow.id)
        .limit(bite)
    )
    eaten = 0
    for soul in souls:
        if not held(soul.id):
            await retire_in(ctx, soul, f"consumed by {being.name}", status=EntityStatus.DESTROYED)
            eaten += 1
    return eaten


@EATERS.on(OuterHunger.KNOWLEDGE)
async def eat_knowledge(ctx: TickContext, being: EntityRow, bite: int) -> int:
    holders = select(EntityRow.id).where(EntityRow.world_id == being.world_id, EntityRow.entity_type.in_(list(COMMUNITY_TYPES)))
    rows = await ctx.session.scalars(
        select(HolderLevelRow).where(HolderLevelRow.holder_entity_id.in_(holders), HolderLevelRow.level > 0).order_by(HolderLevelRow.level.desc()).limit(bite)
    )
    eaten = 0
    for row in rows:
        if "level" not in row.locked and not held(row.holder_entity_id):
            row.level -= 1
            eaten += 1
    return eaten


@EATERS.on(OuterHunger.LIGHT)
async def eat_light(ctx: TickContext, being: EntityRow, bite: int) -> int:
    world = await ctx.session.get(WorldRow, being.world_id)
    star = await ctx.session.get(StarRow, world.star_id) if world is not None and world.star_id is not None else None
    if star is None or star.star_type in DARK_STAR_TYPES or star.brightness <= 0:
        return 0
    taken = min(star.brightness, bite)
    star.brightness -= taken
    return taken


@EATERS.on(OuterHunger.NAMES)
async def eat_names(ctx: TickContext, being: EntityRow, bite: int) -> int:
    languages = select(EntityRow.id).where(EntityRow.world_id == being.world_id, EntityRow.entity_type == EntityType.LANGUAGE)
    words = list(await ctx.session.scalars(select(LexemeRow.id).where(LexemeRow.language_entity_id.in_(languages)).order_by(LexemeRow.id).limit(bite)))
    if words:
        await ctx.session.execute(delete(LexemeRow).where(LexemeRow.id.in_(words)))
    return len(words)


@EATERS.on(OuterHunger.MEMORIES)
async def eat_memories(ctx: TickContext, being: EntityRow, bite: int) -> int:
    legends = select(EntityRow.id).where(EntityRow.world_id == being.world_id, EntityRow.entity_type == EntityType.LEGEND)
    rows = await ctx.session.scalars(select(LegendProfileRow).where(LegendProfileRow.legend_entity_id.in_(legends)).order_by(LegendProfileRow.legend_entity_id))
    eaten = 0
    for row in rows:
        if "credence" not in row.locked and row.credence > 0 and eaten < bite:
            row.credence = clamp_int(row.credence - ctx.rules.outer_beings.memory_bite, 0, PERCENT)
            eaten += 1
    return eaten


async def open_breaches(ctx: TickContext, being: EntityRow, row: OuterBeingProfileRow) -> int:
    table = ctx.rules.outer_beings
    present = list(await ctx.session.scalars(select(BreachPointRow).where(BreachPointRow.outer_entity_id == being.id)))
    if len(present) >= row.reach:
        return 0
    taken = {breach.region_entity_id for breach in present}
    regions = await ctx.session.scalars(
        select(EntityRow.id)
        .where(EntityRow.world_id == being.world_id, EntityRow.entity_type == EntityType.REGION, EntityRow.status == EntityStatus.CANON)
        .order_by(EntityRow.id)
    )
    opened = 0
    for region in regions:
        if len(present) + opened >= row.reach:
            break
        if region in taken:
            continue
        ctx.session.add(
            BreachPointRow(outer_entity_id=being.id, world_id=being.world_id, region_entity_id=region, strength=table.breach_strength, opened_epoch=ctx.epoch)
        )
        opened += 1
    return opened


async def outer_feeding(ctx: TickContext) -> int:
    table = ctx.rules.outer_beings
    fed = 0
    beings = await ctx.session.scalars(
        select(EntityRow).where(EntityRow.entity_type == EntityType.OUTER_BEING, EntityRow.status == EntityStatus.CANON).order_by(EntityRow.id)
    )
    gone = await ended_ids(ctx.session)
    for being in list(beings):
        if held(being.id) or being.id in gone:
            continue
        row = await outer_profile(ctx, being)
        if row.fate is not OuterFate.ACTIVE:
            continue
        if "reach" not in row.locked:
            row.reach = reach_of(table.size_per_region, being)
        bite = max(1, round(stat_or(being, "interest", 0) * table.bite_per_interest / PERCENT))
        eaten = await EATERS[row.hunger](ctx, being, bite)
        if "fed" not in row.locked:
            row.fed += eaten
        if "unfed_epochs" not in row.locked:
            row.unfed_epochs = 0 if eaten else row.unfed_epochs + 1
        if eaten:
            influence = clamp_percent(stat_or(being, "influence", 0) + table.influence_per_meal)
            being.stats = revised(being.stats, {"influence": influence})
            fed += eaten
            await record(
                ctx,
                f"outer.fed_{row.hunger.value}",
                roles={IncidentRole.SUBJECT: being.id},
                facts={"being": str(being.name), "hunger_labels": HUNGER_LABELS[row.hunger].lower(), "eaten": str(eaten)},
                kind=ChronicleKind.OUTER_BEING,
                world_id=being.world_id,
            )
        await open_breaches(ctx, being, row)
        row.updated_epoch = ctx.epoch
    await breach_leaks(ctx)
    await ctx.session.flush()
    return fed


async def breach_pressure(ctx: TickContext) -> dict[int, int]:
    pressure: dict[int, int] = {}
    for row in await ctx.session.scalars(select(BreachPointRow)):
        if row.region_entity_id is not None:
            pressure[row.region_entity_id] = pressure.get(row.region_entity_id, 0) + row.strength
    return pressure


async def breach_leaks(ctx: TickContext) -> int:
    leaked = 0
    for row in await ctx.session.scalars(select(BreachPointRow).order_by(BreachPointRow.id)):
        world = await ctx.session.get(WorldRow, row.world_id)
        if world is not None and not held(row.outer_entity_id):
            world.leakage = clamp_percent(world.leakage + round(row.strength * ctx.rules.outer_beings.breach_leak_pct / PERCENT))
            leaked += 1
    return leaked


async def seed_void_tenets(ctx: TickContext, cult: EntityRow) -> int:
    seeded = 0
    for tenet in VOID_TENETS:
        if await ctx.session.get(CultTenetRow, (cult.id, tenet)) is None:
            ctx.session.add(CultTenetRow(cult_entity_id=cult.id, tenet=tenet, since_epoch=ctx.epoch))
            seeded += 1
    await ctx.session.flush()
    return seeded


async def void_rites(ctx: TickContext) -> int:
    table = ctx.rules.outer_beings
    done = 0
    cults = select(EntityFlagRow.entity_id).where(EntityFlagRow.flag == EntityFlag.OUTER_CULT)
    for cult in list(
        await ctx.session.scalars(select(EntityRow).where(EntityRow.id.in_(cults), EntityRow.status == EntityStatus.CANON).order_by(EntityRow.id))
    ):
        if held(cult.id):
            continue
        tenets = set(await ctx.session.scalars(select(CultTenetRow.tenet).where(CultTenetRow.cult_entity_id == cult.id)))
        home = await ctx.session.get(EntityRow, cult.location_id) if cult.location_id is not None else None
        if TenetKind.VOID_COMMUNION in tenets:
            shift_sanity(ctx.rules, cult, -table.communion_sanity)
            if home is not None and not held(home.id):
                shift_sanity(ctx.rules, home, -table.communion_sanity)
            world = await ctx.session.get(WorldRow, cult.world_id)
            if world is not None:
                world.leakage = clamp_percent(world.leakage + table.communion_leak)
        if TenetKind.FEEDING_THE_HUNGER in tenets:
            beings = await ctx.session.scalars(
                select(BondRow.target_node_id).where(BondRow.source_node_id == cult.id, BondRow.kind == BondKind.WORSHIPS, BondRow.state == BondState.ACTIVE)
            )
            for being_id in beings:
                row = await ctx.session.get(OuterBeingProfileRow, being_id)
                if row is not None and "fed" not in row.locked:
                    row.fed += max(1, stat_or(cult, "followers", 0) // max(1, table.followers_per_offering))
        if TenetKind.WHISPERED_SECRETS in tenets and home is not None and not held(home.id):
            level = await ctx.session.get(HolderLevelRow, (home.id, KnowledgeBranch.FORBIDDEN))
            if level is None:
                level = HolderLevelRow(
                    holder_entity_id=home.id,
                    branch=KnowledgeBranch.FORBIDDEN,
                    level=0,
                    practitioners=0,
                    progress=0,
                    secret=True,
                    updated_epoch=ctx.epoch,
                    locked=[],
                )
                ctx.session.add(level)
            if "progress" not in level.locked:
                level.progress = level.progress + table.whisper_progress
                if level.progress >= PERCENT and "level" not in level.locked:
                    level.level, level.progress = level.level + 1, 0
        done += 1
    await ctx.session.flush()
    return done


@dataclass(frozen=True)
class Bargain:
    son: SonRow
    being: EntityRow
    domain: Domain | None = None
    world_id: int | None = None


async def give_domain(ctx: TickContext, deal: Bargain) -> str:
    table = ctx.rules.outer_beings
    wound = await inflict(
        ctx, deal.son, DivineWoundKind.SEVERED_DOMAIN, WoundCause.OUTER_BARGAIN, severity=table.price_severity, cause_node_id=deal.being.id, domain=deal.domain
    )
    return f"gave up {spoken(wound.domain) if wound is not None and wound.domain is not None else 'a domain'}"


async def give_name(ctx: TickContext, deal: Bargain) -> str:
    table = ctx.rules.outer_beings
    await inflict(ctx, deal.son, DivineWoundKind.STOLEN_NAME, WoundCause.OUTER_BARGAIN, severity=table.price_severity, cause_node_id=deal.being.id)
    return "gave up their true name"


async def give_sanity(ctx: TickContext, deal: Bargain) -> str:
    target = deal.world_id if deal.world_id is not None else deal.being.world_id
    for entity in await ctx.session.scalars(
        select(EntityRow).where(EntityRow.world_id == target, EntityRow.status == EntityStatus.CANON, EntityRow.entity_type.in_(list(COMMUNITY_TYPES)))
    ):
        if not held(entity.id):
            shift_sanity(ctx.rules, entity, -ctx.rules.outer_beings.price_sanity)
    return "gave up a world's sanity"


async def give_worshippers(ctx: TickContext, deal: Bargain) -> str:
    table = ctx.rules.outer_bargains
    taken = 0
    for cult in await faithful_cults(ctx, deal.son.id):
        followers = stat_or(cult, FOLLOWERS_KEY, 0)
        lost = followers * table.worshippers_taken_pct // PERCENT
        if lost and not held(cult.id):
            put_stat(ctx.rules, cult, FOLLOWERS_KEY, followers - lost)
            taken += lost
    await inflict(
        ctx, deal.son, DivineWoundKind.LOST_WORSHIPPERS, WoundCause.OUTER_BARGAIN, severity=ctx.rules.outer_beings.price_severity, cause_node_id=deal.being.id
    )
    await record(
        ctx,
        "outer.price_paid",
        roles={IncidentRole.ACTOR: deal.son.id, IncidentRole.TARGET: deal.being.id},
        facts={"price": BargainPrice.WORSHIPPERS, "souls": taken},
    )
    return f"gave up the souls of {taken} of their faithful"


async def give_line(ctx: TickContext, deal: Bargain) -> str:
    marked = await bind_line(ctx, deal.son, deal.being)
    return f"bound their line, {marked} of it marked so far"


Price = Callable[[TickContext, Bargain], Awaitable[str]]
PRICES: Mapping[BargainPrice, Price] = total(
    BargainPrice,
    {
        BargainPrice.WORLD_SANITY: give_sanity,
        BargainPrice.DOMAIN: give_domain,
        BargainPrice.TRUE_NAME: give_name,
        BargainPrice.WORSHIPPERS: give_worshippers,
        BargainPrice.DESCENDANTS: give_line,
    },
)


async def pay_price(ctx: TickContext, son: SonRow, being: EntityRow, price: BargainPrice, *, domain: Domain | None = None, world_id: int | None = None) -> str:
    return await PRICES[price](ctx, Bargain(son, being, domain, world_id))


async def faithful_cults(ctx: TickContext, son_id: int) -> list[EntityRow]:
    statement = (
        select(EntityRow)
        .join(BondRow, BondRow.source_node_id == EntityRow.id)
        .where(BondRow.target_node_id == son_id, BondRow.kind == BondKind.WORSHIPS, BondRow.state == BondState.ACTIVE, EntityRow.entity_type == EntityType.CULT)
        .order_by(EntityRow.id)
    )
    return list(dict.fromkeys(await ctx.session.scalars(statement)))


async def line_of(ctx: TickContext, son_id: int) -> list[EntityRow]:
    found: dict[int, EntityRow] = {}
    frontier = [son_id]
    for _generation in range(LINE_DEPTH):
        children = await ctx.session.scalars(
            select(EntityRow)
            .join(BondRow, BondRow.target_node_id == EntityRow.id)
            .where(BondRow.source_node_id.in_(frontier), BondRow.kind == BondKind.PARENT_OF, BondRow.state == BondState.ACTIVE)
            .order_by(EntityRow.id)
        )
        frontier = [child.id for child in children if child.id not in found and child.status is EntityStatus.CANON]
        for child_id in frontier:
            child = await ctx.session.get(EntityRow, child_id)
            if child is not None:
                found[child_id] = child
    return [found[key] for key in sorted(found)]


async def bind_line(ctx: TickContext, son: SonRow, being: EntityRow) -> int:
    curses = sorted(kind for kind, spec in PACKAGES.items() if Transmission.CURSE in spec.transmissions)
    if not curses:
        return 0
    package = SeededRandom.for_epoch(son.id, being.id, "outer_line_curse").pick(curses)
    marked = 0
    for child in await line_of(ctx, son.id):
        if held(child.id):
            continue
        if await afflict(ctx, child, package, Transmission.CURSE, source_node_id=being.id) is not None:
            marked += 1
    return marked


async def gain_essence(ctx: TickContext, deal: Bargain, essence: int) -> str:
    gained = essence * BARGAIN_GAINS[BargainGain.ESSENCE].size(ctx.rules) // PERCENT
    deal.son.essence += gained
    return f"gained {gained} essence"


async def gain_might(ctx: TickContext, deal: Bargain, _essence: int) -> str:
    gained = ctx.rules.outer_beings.might_gain * BARGAIN_GAINS[BargainGain.MIGHT].size(ctx.rules) // PERCENT
    deal.son.might = clamp_int(deal.son.might + gained, 0, PERCENT)
    return f"gained {gained} might"


async def gain_power(ctx: TickContext, deal: Bargain, essence: int) -> str:
    used = set(await ctx.session.scalars(select(SonPowerRow.slot).where(SonPowerRow.son_id == deal.son.id)))
    free = next((slot for slot in range(POWER_SLOTS) if slot not in used), None)
    chance = BARGAIN_GAINS[BargainGain.POWER].size(ctx.rules)
    if free is None or not ctx.rng(f"outer_power.{deal.son.id}.{deal.being.id}.{ctx.epoch}").chance(chance):
        return await gain_essence(ctx, deal, essence)
    ctx.session.add(
        SonPowerRow(
            son_id=deal.son.id,
            slot=free,
            name=f"Gift of {deal.being.name}",
            description=f"A power given by {deal.being.name}.",
            effect=PowerEffect.ESSENCE_SPRING,
        )
    )
    return "gained a power"


async def gain_knowledge(ctx: TickContext, deal: Bargain, essence: int) -> str:
    homes = await faithful_communities(ctx.session, deal.son.id)
    known = {
        (row.holder_entity_id, row.branch)
        for row in await ctx.session.scalars(select(HolderLevelRow).where(HolderLevelRow.holder_entity_id.in_([home.id for home in homes])))
        if row.level > 0
    }
    reachable = [(home, branch) for home in homes for branch in KnowledgeBranch if (home.id, branch) not in known and not held(home.id)]
    if not reachable:
        return await gain_essence(ctx, deal, essence)
    home, branch = ctx.rng(f"outer_knowledge.{deal.son.id}.{deal.being.id}.{ctx.epoch}").pick(reachable)
    level = await ctx.session.get(HolderLevelRow, (home.id, branch))
    if level is None:
        level = HolderLevelRow(holder_entity_id=home.id, branch=branch, level=0, practitioners=0, progress=0, secret=True, updated_epoch=ctx.epoch, locked=[])
        ctx.session.add(level)
    if "progress" not in level.locked:
        level.progress += BARGAIN_GAINS[BargainGain.KNOWLEDGE].size(ctx.rules)
        if level.progress >= PERCENT and "level" not in level.locked:
            level.level, level.progress = level.level + 1, level.progress - PERCENT
    return f"gained knowledge of {spoken(branch)} for {home.name}"


async def gain_span(ctx: TickContext, deal: Bargain, _essence: int) -> str:
    restored = BARGAIN_GAINS[BargainGain.LONGEVITY].size(ctx.rules)
    deal.son.existence = clamp_int(deal.son.existence + restored, 0, PERCENT)
    deal.son.fading_epochs = 0
    return f"gained {restored} existence and a longer span"


Gain = Callable[[TickContext, Bargain, int], Awaitable[str]]
GAINS: Mapping[BargainGain, Gain] = total(
    BargainGain,
    {
        BargainGain.ESSENCE: gain_essence,
        BargainGain.POWER: gain_power,
        BargainGain.MIGHT: gain_might,
        BargainGain.KNOWLEDGE: gain_knowledge,
        BargainGain.LONGEVITY: gain_span,
    },
)


async def take_gain(ctx: TickContext, son: SonRow, being: EntityRow, gain: BargainGain, essence: int) -> str:
    return await GAINS[gain](ctx, Bargain(son, being), essence)


async def due_lines(ctx: TickContext) -> int:
    table = ctx.rules.outer_bargains
    settled = 0
    rows = await ctx.session.scalars(
        select(OuterBargainRow).where(OuterBargainRow.price == BargainPrice.DESCENDANTS, OuterBargainRow.paid.is_(False)).order_by(OuterBargainRow.son_id)
    )
    for row in list(rows):
        son = await ctx.session.get(SonRow, row.son_id)
        being = await ctx.session.get(EntityRow, row.outer_entity_id)
        if son is None or being is None or held(son.id):
            continue
        if ctx.epoch - row.epoch < table.epochs(table.descendants_years):
            await bind_line(ctx, son, being)
            continue
        row.paid = True
        settled += 1
        await record(
            ctx,
            "outer.price_paid",
            roles={IncidentRole.ACTOR: son.id, IncidentRole.TARGET: being.id},
            facts={"price": BargainPrice.DESCENDANTS, "souls": 0},
        )
    return settled


async def found_outer_cult(ctx: TickContext, entity: EntityRow) -> EntityRow:
    horror = ctx.rules.cosmic_horror
    population = stat_or(entity, POPULATION_KEY, horror.whisperers_default_population)
    cult = await open_record(
        ctx.session,
        ctx.epoch,
        RecordSpec(
            name=f"The outer cult of {entity.name}",
            entity_type=EntityType.CULT,
            body=f"A cult among {entity.name} that worships a being from outside the cosmos.",
            stats=CultStats(
                followers=max(horror.whisperers_min_followers, round(population * horror.whisperers_share_pct / PERCENT)),
                zeal=horror.whisperers_zealotry,
                influence=horror.whisperers_influence,
            ),
            power=horror.whisperers_power,
            world_id=entity.world_id,
            location_id=entity.id if entity.entity_type is EntityType.SETTLEMENT else entity.location_id,
            subtype="outer cult",
            flags=(EntityFlag.OUTER_CULT,),
            sanity=horror.whisperers_sanity,
        ),
    )
    await connect(ctx.session, cult.id, entity.id, BondKind.DESCENDS_FROM, ctx.epoch, description="born from within")
    await seed_void_tenets(ctx, cult)
    return cult
