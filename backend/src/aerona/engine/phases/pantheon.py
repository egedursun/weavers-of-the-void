from collections import Counter
from dataclasses import dataclass

from sqlalchemy import Select, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.catalog.gates import Gate, passes_gate
from aerona.constants.units import PERCENT
from aerona.core.errors import NotFoundError, ValidationFailedError
from aerona.db.repositories.bonds import BondDraft, BondRepository
from aerona.db.repositories.cosmos import CosmosRepository
from aerona.db.repositories.nodes import NodeRepository
from aerona.db.repositories.sons import SonRepository
from aerona.db.repositories.worlds import WorldRepository
from aerona.db.tables.bonds import BondRow
from aerona.db.tables.celestial import WorldRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.foreign_gods import ForeignGodRow
from aerona.db.tables.lore import ChronicleEntityRow, ChronicleRow
from aerona.db.tables.routes import JourneyRow, RouteRow
from aerona.db.tables.sons import SonRow
from aerona.domain.enums.bond import BondKind
from aerona.domain.enums.chronicle import ChronicleKind
from aerona.domain.enums.entity import EngineKind, EntityFlag, EntityOrigin, EntityStatus, EntityType
from aerona.domain.enums.foreign_god import ForeignGodPowerEffect, ForeignGodStatus
from aerona.domain.enums.limits import RELATION_MAX, RELATION_MIN
from aerona.domain.enums.node import NodeKind
from aerona.domain.enums.son import SonStatus, Stat
from aerona.domain.enums.war import WarCause
from aerona.domain.enums.world import Discovery
from aerona.engine.context import TickContext
from aerona.engine.cosmos.duels import ARENA_STATS, duel_history, duel_winner, son_duel
from aerona.engine.cosmos.foreign_gods import awaken_text, destroy_temple, god_faith, powers_of, stat_effect, wake, worshippers
from aerona.engine.cosmos.routes import RouteBook
from aerona.engine.cosmos.worlds import declare_holy_world
from aerona.engine.interconnect.annotations import reads, writes
from aerona.engine.notes import note
from aerona.engine.phase import Phase
from aerona.engine.primitives.manual import manual_context
from aerona.engine.primitives.numbers import clamp_int
from aerona.engine.primitives.prosperity import add_prosperity
from aerona.engine.primitives.queries import BondIndex, canon, flags_by_entity
from aerona.engine.primitives.stats import has_stat, headcount_value, stat_or
from aerona.engine.services.conflict import foreign_god_war
from aerona.engine.services.war import declare_war, is_community
from aerona.rules.registry import Rules

F = ForeignGodPowerEffect
NATIVE_TYPES = frozenset({EntityType.PEOPLE, EntityType.SETTLEMENT, EntityType.CULT})
BOOKKEEPING_KINDS = frozenset(
    {ChronicleKind.WORLD, ChronicleKind.ENGINE_RAW, ChronicleKind.SYSTEM, ChronicleKind.CREATOR_REPUTATION, ChronicleKind.EXISTENCE, ChronicleKind.FATE}
)
LAND_ORIGINS = frozenset({EntityOrigin.SON, EntityOrigin.MORTAL, EntityOrigin.CREATOR})
WAKE_PHRASES = {
    "son": "the footsteps of gods",
    "expedition": "foreign sails and opened roads",
    "event": "the noise of war and disaster",
    "land": "the reshaping of its land",
    "ruin": "old ruins rising from beneath the earth",
    "death": "the laments of the dead",
}
PROSPERITY_KEY = "prosperity"
INFLUENCE_KEY = "influence"


async def defeated_waking(ctx: TickContext) -> int:
    pantheon, gods_rules = ctx.rules.pantheon, ctx.rules.foreign_gods
    woken = 0
    for god in list(await ctx.session.scalars(select(ForeignGodRow).order_by(ForeignGodRow.id))):
        if god.status is not ForeignGodStatus.DEFEATED:
            god.defeated_epoch = None if god.status is ForeignGodStatus.AWAKE else god.defeated_epoch
            continue
        faith = round(await god_faith(ctx.session, ctx.rules, god.id))
        god.faith = faith
        start = god.defeated_epoch if god.defeated_epoch is not None else ctx.epoch
        god.defeated_epoch = start
        reviving = F.REVIVING in await powers_of(ctx.session, god.id)
        duration = max(
            1,
            round(
                (pantheon.foreign_wake_epochs - stat_effect(ctx.rules, god, Stat.ENDURANCE, gods_rules.wake_endurance))
                * (gods_rules.power_reviving / PERCENT if reviving else 1)
            ),
        )
        by_faith = pantheon.foreign_wake_faith > 0 and faith >= pantheon.foreign_wake_faith
        if ctx.epoch - start < duration and not by_faith:
            continue
        wake(god)
        god.defeated_epoch = None
        god.power = max(god.power, pantheon.foreign_wake_min_strength)
        god.stance = max(RELATION_MIN, god.stance - pantheon.foreign_wake_grudge)
        world = await ctx.session.get(WorldRow, god.world_id)
        cause = "its worshippers' faith raised it again" if by_faith else "epochs passed over the defeat and the wound closed"
        text = f"{world.name if world else 'A world'}'s defeated god {god.name} woke again: {cause}. It has not forgotten the grudge of defeat."
        await ctx.chronicle(ChronicleKind.FOREIGN_GOD, text, template_key="pantheon.defeated_woke", world_id=god.world_id)
        woken += 1
    return woken


@dataclass(frozen=True)
class WakeNoise:
    son: int
    expedition: int
    event: int
    land: int
    ruin: int
    death: int


async def _son_traces(session: AsyncSession, world_id: int, epoch: int) -> int:
    created = select(EntityRow.creator_son_id).where(EntityRow.world_id == world_id, EntityRow.birth_epoch == epoch, EntityRow.creator_son_id.is_not(None))
    chronicled = (
        select(ChronicleRow.son_id)
        .join(ChronicleEntityRow, ChronicleEntityRow.chronicle_id == ChronicleRow.id)
        .join(EntityRow, EntityRow.id == ChronicleEntityRow.entity_id)
        .where(ChronicleRow.epoch == epoch, ChronicleRow.son_id.is_not(None), EntityRow.world_id == world_id, ChronicleRow.kind.not_in(list(BOOKKEEPING_KINDS)))
    )
    active = set(await session.scalars(select(SonRow.id).where(SonRow.status == SonStatus.ACTIVE)))
    traced = {item for item in await session.scalars(created) if item is not None} | {item for item in await session.scalars(chronicled) if item is not None}
    return len(traced & active)


async def _count(session: AsyncSession, statement: Select[int]) -> int:
    return int(await session.scalar(statement) or 0)


async def wake_noise(session: AsyncSession, world_id: int, epoch: int) -> WakeNoise:
    journeys = select(func.count()).select_from(JourneyRow).where(JourneyRow.destination_world_id == world_id, JourneyRow.start_epoch == epoch)
    routes = (
        select(func.count()).select_from(RouteRow).where(RouteRow.created_epoch == epoch, or_(RouteRow.world_a_id == world_id, RouteRow.world_b_id == world_id))
    )
    born = select(EntityRow).where(EntityRow.world_id == world_id, EntityRow.birth_epoch == epoch)
    fresh = list(await session.scalars(born))
    ruins = await flags_by_entity(session, EntityFlag.RUIN) | await flags_by_entity(session, EntityFlag.PREVIOUS_CREATION)
    deaths = (
        select(func.count())
        .select_from(EntityRow)
        .where(
            EntityRow.world_id == world_id, EntityRow.entity_type == EntityType.MORTAL, EntityRow.status == EntityStatus.DEAD, EntityRow.end_epoch == epoch - 1
        )
    )
    return WakeNoise(
        son=await _son_traces(session, world_id, epoch),
        expedition=await _count(session, journeys) + await _count(session, routes),
        event=sum(1 for item in fresh if item.entity_type is EntityType.EVENT),
        land=sum(1 for item in fresh if item.entity_type in (EntityType.REGION, EntityType.PLACE) and item.origin in LAND_ORIGINS),
        ruin=sum(1 for item in fresh if item.id in ruins),
        death=await _count(session, deaths),
    )


def wake_points(rules: Rules, god: ForeignGodRow, noise: WakeNoise) -> tuple[int, float, dict[str, int]]:
    pantheon = rules.pantheon
    weighted = {
        "son": noise.son * pantheon.sleep_per_son,
        "event": noise.event * pantheon.sleep_per_event,
        "land": noise.land * pantheon.sleep_per_land,
        "death": noise.death * pantheon.sleep_per_death,
        "expedition": noise.expedition * pantheon.sleep_per_expedition,
        "ruin": noise.ruin * pantheon.sleep_per_relic,
    }
    ordinary = weighted["son"] + weighted["event"] + weighted["land"] + weighted["death"]
    events = weighted["expedition"] + weighted["ruin"]
    baseline = god.awakening_average if god.awakening_average is not None else ordinary
    raw = events + max(0.0, ordinary - baseline * pantheon.sleep_baseline_ignore_pct / PERCENT)
    new_baseline = baseline + (ordinary - baseline) * pantheon.sleep_average_weight_pct / PERCENT
    points = round(min(raw, pantheon.sleep_epoch_cap) if pantheon.sleep_epoch_cap > 0 else raw)
    return points, new_baseline, weighted


async def sleep_waking(ctx: TickContext) -> int:
    pantheon = ctx.rules.pantheon
    woken = 0
    for god in list(await ctx.session.scalars(select(ForeignGodRow).where(ForeignGodRow.status == ForeignGodStatus.ASLEEP).order_by(ForeignGodRow.id))):
        points, baseline, weighted = wake_points(ctx.rules, god, await wake_noise(ctx.session, god.world_id, ctx.epoch))
        god.awakening_average = baseline
        if not points:
            continue
        god.awakening_pressure += points
        if god.awakening_pressure < pantheon.sleep_wake_threshold:
            continue
        wake(god)
        top = [key for key, value in sorted(weighted.items(), key=lambda item: -item[1]) if value > 0][:2]
        causes = " and ".join(WAKE_PHRASES[key] for key in top) or "something unseen"
        world = await ctx.session.get(WorldRow, god.world_id)
        text = f"{world.name if world else 'A world'}'s sleeping god {god.name} woke: {causes} pulled it from its sleep."
        await ctx.chronicle(ChronicleKind.FOREIGN_GOD, text, template_key="pantheon.sleeper_woke", world_id=god.world_id)
        woken += 1
    return woken


async def _son_worshippers(session: AsyncSession) -> Counter[tuple[int, int]]:
    index = await BondIndex.load(session, [BondKind.WORSHIPS])
    sons = {son.id for son in await session.scalars(select(SonRow).where(SonRow.status == SonStatus.ACTIVE))}
    counts: Counter[tuple[int, int]] = Counter()
    for bond in index.bonds:
        if bond.target_node_id not in sons:
            continue
        worshipper = await session.get(EntityRow, bond.source_node_id)
        if worshipper is not None and worshipper.status is EntityStatus.CANON:
            counts[(worshipper.world_id, bond.target_node_id)] += 1
    return counts


async def auto_holy_worlds(ctx: TickContext) -> int:
    pantheon = ctx.rules.pantheon
    worlds = await WorldRepository(ctx.session).reachable_worlds()
    if pantheon.auto_holy_world_worshippers <= 0 or len(worlds) < 2:
        return 0
    open_worlds = set()
    for world in worlds:
        protector = await ctx.session.get(SonRow, world.patron_son_id) if world.patron_son_id is not None else None
        if protector is None or protector.status is SonStatus.DEAD:
            open_worlds.add(world.id)
    held = Counter(world.patron_son_id for world in worlds if world.patron_automatic and world.patron_son_id is not None)
    pairs = sorted(
        ((count, world_id, son_id) for (world_id, son_id), count in (await _son_worshippers(ctx.session)).items() if world_id in open_worlds),
        key=lambda item: (-item[0], item[1]),
    )
    claimed: set[int] = set()
    for count, world_id, son_id in pairs:
        if count < pantheon.auto_holy_world_worshippers or world_id in claimed or held[son_id] >= pantheon.auto_holy_world_per_son:
            continue
        son, holy = await ctx.session.get(SonRow, son_id), await ctx.session.get(WorldRow, world_id)
        if son is None or holy is None:
            continue
        await declare_holy_world(ctx, son, holy, automatic=True)
        claimed.add(world_id)
        held[son_id] += 1
    return len(claimed)


def rival_soften(rules: Rules, value: int) -> int:
    pantheon = rules.pantheon
    threshold = -pantheon.rival_relation
    return min(threshold, value + pantheon.rival_soften) if value < threshold else value


async def _rival_pairs(ctx: TickContext, book: RouteBook) -> list[tuple[int, SonRow, SonRow]]:
    sons = list(await ctx.session.scalars(select(SonRow).where(SonRow.status == SonStatus.ACTIVE).order_by(SonRow.id)))
    repository = SonRepository(ctx.session)
    pairs = []
    for index, first in enumerate(sons):
        for second in sons[index + 1 :]:
            value = await repository.relation(first.id, second.id)
            if value <= -ctx.rules.pantheon.rival_relation and book.reachable(first.current_world_id, second.current_world_id):
                pairs.append((value, first, second))
    return sorted(pairs, key=lambda item: (item[0], item[1].id, item[2].id))


async def rival_clashes(ctx: TickContext) -> int:
    pantheon = ctx.rules.pantheon
    if pantheon.rival_cap <= 0:
        return 0
    rng = ctx.rng("rivals")
    repository = SonRepository(ctx.session)
    clashes = 0
    for value, first, second in await _rival_pairs(ctx, await RouteBook.load(ctx.session, ctx.rules, ctx.epoch)):
        history = await duel_history(ctx.session, first.id, second.id, max(pantheon.rival_defeat_streak, 1) * 2 + 2)
        recent = history[0].epoch if history else None
        if (
            clashes >= pantheon.rival_cap
            or (recent is not None and ctx.epoch - recent < pantheon.rival_cooldown_epochs)
            or not rng.chance(pantheon.rival_chance)
        ):
            await repository.change_relation(first.id, second.id, rival_soften(ctx.rules, value) - value)
            continue
        restraint = pantheon.rival_mercy_restraint_pct / PERCENT
        weights = [max(0.0, son.wrath + son.ambition - son.mercy * restraint) + 1 for son in (first, second)]
        attacker = rng.weighted([first, second], weights)
        defender = second if attacker.id == first.id else first
        stat = rng.weighted(list(ARENA_STATS), [(attacker.stat(item) + defender.stat(item)) / 2 + 1 for item in ARENA_STATS])
        result = await son_duel(ctx, attacker, defender, stat, "old feud")
        await note(ctx, result.text, key="pantheon.rival_clash", son_id=attacker.id)
        clashes += 1
        await _loss_streak(ctx, first, second)
    return clashes


async def _loss_streak(ctx: TickContext, first: SonRow, second: SonRow) -> None:
    pantheon = ctx.rules.pantheon
    history = await duel_history(ctx.session, first.id, second.id, pantheon.rival_defeat_streak)
    winners = {duel_winner(row) for row in history}
    if len(history) < pantheon.rival_defeat_streak or len(winners) != 1:
        return
    winner_id = winners.pop()
    loser, winner = (second, first) if winner_id == first.id else (first, second)
    await SonRepository(ctx.session).change_relation(first.id, second.id, pantheon.rival_withdraw_relation)
    text = f"{loser.name}, beaten {pantheon.rival_defeat_streak} times in a row by {winner.name}, withdrew; the feud between them calmed for a while."
    await ctx.chronicle(ChronicleKind.CHALLENGE, text, template_key="pantheon.rival_withdrew", son_id=loser.id)


def power_share(rules: Rules, god: ForeignGodRow) -> float:
    return min(1.0, god.power / max(1, rules.foreign_gods.action_full_power))


def might_of(rules: Rules, god: ForeignGodRow) -> float:
    return min(1.0, god.faith / max(1, rules.foreign_gods.action_full_faith)) * power_share(rules, god)


async def attract(ctx: TickContext, god: ForeignGodRow, natives: list[EntityRow], powers: set[ForeignGodPowerEffect], index: BondIndex) -> int:
    pantheon, settings = ctx.rules.pantheon, ctx.rules.foreign_gods
    chance = (
        pantheon.foreign_attract_chance
        + stat_effect(ctx.rules, god, Stat.CHARISMA, settings.attract_charisma)
        + (settings.power_caller if F.CALLER in powers else 0)
    )
    rng = ctx.rng(f"attract.{god.id}")
    living = {son.id for son in await ctx.session.scalars(select(SonRow).where(SonRow.status != SonStatus.DEAD))}
    unclaimed = [item for item in natives if not index.outgoing(item.id, BondKind.WORSHIPS) and item.creator_son_id not in living][
        : pantheon.foreign_attract_targets
    ]
    drawn = 0
    for native in unclaimed:
        if rng.chance(chance * power_share(ctx.rules, god)):
            index.add(await BondRepository(ctx.session).connect(BondDraft(native.id, god.id, BondKind.WORSHIPS, ctx.epoch, "old god")))
            world = await ctx.session.get(WorldRow, god.world_id)
            await note(
                ctx, f"{native.name} began to worship {world.name if world else 'its world'}'s old god {god.name}.", key="pantheon.attracted", ids=[native.id]
            )
            drawn += 1
    return drawn


async def grow_power(ctx: TickContext, god: ForeignGodRow) -> None:
    pantheon = ctx.rules.pantheon
    faith = await god_faith(ctx.session, ctx.rules, god.id)
    god.faith = round(faith)
    threshold = pantheon.foreign_growth_faith - stat_effect(ctx.rules, god, Stat.MIGHT, ctx.rules.foreign_gods.growth_faith_might)
    if faith > threshold:
        god.power = min(PERCENT, god.power + pantheon.foreign_growth)


async def first_contact(ctx: TickContext, god: ForeignGodRow, book: RouteBook) -> bool:
    if god.contacted:
        return True
    son: SonRow | None = await ctx.session.scalar(
        select(SonRow).where(SonRow.status == SonStatus.ACTIVE, SonRow.current_world_id == god.world_id).order_by(SonRow.id).limit(1)
    )
    touched = any(route.active and god.world_id in (route.world_a_id, route.world_b_id) for route in book.routes)
    if son is None and not touched:
        return False
    god.contacted = True
    pantheon = ctx.rules.pantheon
    tone = (
        "Curiously." if god.stance >= pantheon.attitude_curious else "With hostility." if god.stance <= -pantheon.attitude_hostile else "Silently, measuring."
    )
    creator = await CosmosRepository(ctx.session).creator()
    world = await ctx.session.get(WorldRow, god.world_id)
    title = f", {god.title}" if god.title else ""
    owner = creator.name if creator else "the creator"
    text = f"First contact: {world.name if world else 'A world'}'s old god {god.name}{title} noticed {owner}'s pantheon. {tone}"
    await ctx.chronicle(ChronicleKind.FOREIGN_GOD, text, template_key="pantheon.first_contact", son_id=son.id if son else None, world_id=god.world_id)
    await note(ctx, f"{god.name} noticed the pantheon.", key="pantheon.noticed")
    return True


async def _son_worshipper(ctx: TickContext, world_id: int) -> tuple[EntityRow, BondRow] | None:
    nodes = NodeRepository(ctx.session)
    for entity in await canon(ctx.session, None, world_id):
        for bond in await BondRepository(ctx.session).outgoing(entity.id, BondKind.WORSHIPS):
            if await nodes.kind_of(bond.target_node_id) is NodeKind.SON:
                return entity, bond
    return None


async def steal_worshipper(ctx: TickContext, god: ForeignGodRow, victim: EntityRow, bond: BondRow) -> str:
    bonds = BondRepository(ctx.session)
    await bonds.deactivate(bond, ctx.epoch, "stolen by a foreign god")
    await bonds.connect(BondDraft(victim.id, god.id, BondKind.WORSHIPS, ctx.epoch, "stolen"))
    son = await ctx.session.get(SonRow, bond.target_node_id)
    name = son.name if son else "a son"
    if son is not None:
        son.wrath = min(PERCENT, son.wrath + ctx.rules.pantheon.foreign_steal_wrath)
    text = f"{god.name} turned {name}'s worshipper {victim.name} to itself."
    await ctx.chronicle(ChronicleKind.FOREIGN_GOD, text, template_key="pantheon.worshipper_stolen", entity_ids=[victim.id], son_id=son.id if son else None)
    return text


async def incite_holy_war(ctx: TickContext, god: ForeignGodRow, victim: EntityRow) -> str | None:
    if not is_community(victim):
        return None
    zealots = [item for item in await worshippers(ctx.session, god.id) if is_community(item) and item.id != victim.id]
    if not zealots:
        return None
    zealot = max(zealots, key=lambda item: (headcount_value(item) or 0, -item.id))
    reason = f"the will of {god.name}"
    if not await declare_war(ctx, zealot.id, victim.id, reason, cause=WarCause.FOREIGN_GOD):
        return None
    return f"{god.name} drove {zealot.name} to war against {victim.name}, who worship a son of the creator."


async def hostile_act(ctx: TickContext, god: ForeignGodRow, powers: set[ForeignGodPowerEffect]) -> str | None:
    pantheon, settings = ctx.rules.pantheon, ctx.rules.foreign_gods
    rng = ctx.rng(f"hostile.{god.id}")
    attack = (
        pantheon.foreign_attack_base_pct
        + stat_effect(ctx.rules, god, Stat.AGILITY, settings.attack_agility)
        + (settings.power_destroyer if F.DESTROYER in powers else 0)
    ) / PERCENT
    if not rng.probability((attack + (-god.stance) / pantheon.foreign_attack_hostility_divisor) * might_of(ctx.rules, god)):
        return None
    found = await _son_worshipper(ctx, god.world_id)
    steal = (
        pantheon.foreign_sacrifice_chance
        + stat_effect(ctx.rules, god, Stat.CUNNING, settings.steal_cunning)
        + (settings.power_thief if F.THIEF in powers else 0)
    )
    if found is not None and rng.chance(steal):
        return await steal_worshipper(ctx, god, *found)
    if found is not None and rng.chance(pantheon.foreign_holy_war_chance):
        text = await incite_holy_war(ctx, god, found[0])
        if text is not None:
            return text
    temple: EntityRow | None = await ctx.session.scalar(
        select(EntityRow)
        .where(EntityRow.world_id == god.world_id, EntityRow.engine_kind == EngineKind.TEMPLE, EntityRow.status == EntityStatus.CANON)
        .order_by(EntityRow.id)
        .limit(1)
    )
    if temple is None:
        return None
    await destroy_temple(ctx, god, temple)
    return f"{god.name} destroyed {temple.name}."


async def friendly_help(ctx: TickContext, god: ForeignGodRow, powers: set[ForeignGodPowerEffect]) -> int:
    pantheon, settings = ctx.rules.pantheon, ctx.rules.foreign_gods
    rng = ctx.rng(f"friendly.{god.id}")
    if not rng.chance((pantheon.foreign_friend_help_chance + stat_effect(ctx.rules, god, Stat.WISDOM, settings.help_wisdom)) * might_of(ctx.rules, god)):
        return 0
    bounty = settings.power_bountiful / PERCENT if F.FERTILE in powers else 1
    gift = max(0, round((pantheon.foreign_friend_prosperity + stat_effect(ctx.rules, god, Stat.CREATIVITY, settings.prosperity_creativity)) * bounty))
    helped = [item for item in await worshippers(ctx.session, god.id) if has_stat(item, PROSPERITY_KEY)][: pantheon.foreign_friend_help_targets]
    for believer in helped:
        add_prosperity(ctx.rules, believer, gift)
    return len(helped)


async def attitude_drift(ctx: TickContext, god: ForeignGodRow, natives: list[EntityRow]) -> None:
    pantheon = ctx.rules.pantheon
    rebels = int(
        await ctx.session.scalar(
            select(func.count()).select_from(SonRow).where(SonRow.current_world_id == god.world_id, SonRow.rebel.is_(True), SonRow.status != SonStatus.DEAD)
        )
        or 0
    )
    cursed = await flags_by_entity(ctx.session, EntityFlag.CURSED)
    drift = rebels * pantheon.foreign_rebel_attitude_drift + (pantheon.foreign_curse_attitude_drift if any(item.id in cursed for item in natives) else 0)
    god.stance = clamp_int(god.stance - drift, RELATION_MIN, RELATION_MAX)


async def awake_god_turn(ctx: TickContext, god: ForeignGodRow, book: RouteBook, index: BondIndex) -> None:
    natives = await canon(ctx.session, NATIVE_TYPES, god.world_id)
    powers = await powers_of(ctx.session, god.id)
    await attract(ctx, god, natives, powers, index)
    await grow_power(ctx, god)
    if not await first_contact(ctx, god, book):
        return
    if god.stance < 0:
        text = await hostile_act(ctx, god, powers)
        if text is not None:
            await note(ctx, text, key="pantheon.hostile")
    if god.stance >= ctx.rules.pantheon.foreign_friend_min_attitude:
        await friendly_help(ctx, god, powers)
    await attitude_drift(ctx, god, natives)


async def spontaneous_god_war(ctx: TickContext, book: RouteBook) -> str | None:
    pantheon, tools = ctx.rules.pantheon, ctx.rules.son_tools
    statement = select(ForeignGodRow).where(
        ForeignGodRow.status == ForeignGodStatus.AWAKE, ForeignGodRow.contacted.is_(True), ForeignGodRow.stance <= -pantheon.son_war_max_attitude
    )
    target: ForeignGodRow | None = await ctx.session.scalar(statement.order_by(ForeignGodRow.id).limit(1))
    if target is None:
        return None
    sons = [
        son
        for son in await ctx.session.scalars(select(SonRow).where(SonRow.status == SonStatus.ACTIVE).order_by(SonRow.id))
        if passes_gate(ctx.rules, son.rarity, Gate.FOREIGN_GOD_WAR)
        and son.essence >= tools.foreign_war_cost
        and book.reachable(son.current_world_id, target.world_id)
    ]
    if not sons:
        return None
    champion = max(sons, key=lambda son: (son.strength + son.will + son.level, -son.id))
    if not ctx.rng("god_war_roll").chance(pantheon.son_war_chance):
        return None
    result = await foreign_god_war(ctx, champion.id, target.id)
    await note(ctx, result.text, key="pantheon.spontaneous_god_war", son_id=champion.id)
    return result.text


async def outer_gnaw(ctx: TickContext) -> int:
    pantheon = ctx.rules.pantheon
    beings = await canon(ctx.session, [EntityType.OUTER_BEING])
    gnaw = sum(round(stat_or(being, INFLUENCE_KEY, pantheon.outer_default_influence) / pantheon.outer_gnaw_divisor) for being in beings)
    creator = await CosmosRepository(ctx.session).creator()
    if creator is None or gnaw <= 0:
        return 0
    creator.essence = max(0, creator.essence - gnaw)
    await note(ctx, f"The things outside gnawed {gnaw} from {creator.name}'s essence.", key="pantheon.outer_gnaw")
    return gnaw


@reads(
    "people.population",
    "settlement.population",
    "table.bodies",
    "table.bonds",
    "table.conditions",
    "table.cosmos",
    "table.entity_flags",
    "table.epoch_year_cursors",
    "table.foreign_god_powers",
    "table.god_conflicts",
    "table.injuries",
    "table.journeys",
    "table.memories",
    "table.minds",
    "table.nodes",
    "table.prostheses",
    "table.routes",
    "table.son_powers",
    "table.son_relations",
    "table.traits",
)
@writes(
    "table.bodies",
    "table.bonds",
    "table.chronicle",
    "table.chronicle_entities",
    "table.epoch_year_cursors",
    "table.foreign_gods",
    "table.god_conflicts",
    "table.incident_participants",
    "table.incidents",
    "table.injuries",
    "table.memories",
    "table.son_relations",
    "table.sons",
    "table.worlds",
)
async def pantheon_phase(ctx: TickContext) -> None:
    await defeated_waking(ctx)
    await sleep_waking(ctx)
    await auto_holy_worlds(ctx)
    await rival_clashes(ctx)
    book = await RouteBook.load(ctx.session, ctx.rules, ctx.epoch)
    index = await BondIndex.load(ctx.session, [BondKind.WORSHIPS])
    for god in list(await ctx.session.scalars(select(ForeignGodRow).where(ForeignGodRow.status == ForeignGodStatus.AWAKE).order_by(ForeignGodRow.id))):
        world = await ctx.session.get(WorldRow, god.world_id)
        if world is None or world.discovery is Discovery.FORGOTTEN:
            continue
        await awake_god_turn(ctx, god, book, index)
    await spontaneous_god_war(ctx, book)
    await outer_gnaw(ctx)
    await ctx.session.flush()


async def _god(session: AsyncSession, god_id: int) -> ForeignGodRow:
    god = await session.get(ForeignGodRow, god_id)
    if god is None:
        raise NotFoundError("No such foreign god.")
    return god


async def provoke_duel(session: AsyncSession, rules: Rules, challenger_id: int, defender_id: int, stat: Stat) -> str:
    if stat not in ARENA_STATS:
        raise ValidationFailedError("A duel is fought in strength, wisdom, cunning, charisma or will.")
    ctx = await manual_context(session, "duel", rules, key=f"{challenger_id}:{defender_id}")
    repository = SonRepository(session)
    challenger, defender = await repository.require_son(challenger_id), await repository.require_son(defender_id)
    if challenger.id == defender.id or challenger.status is not SonStatus.ACTIVE or defender.status is not SonStatus.ACTIVE:
        raise ValidationFailedError("Both sons must be awake and different.")
    return (await son_duel(ctx, challenger, defender, stat, "by the creator's will")).text


async def order_god_war(session: AsyncSession, rules: Rules, son_id: int, god_id: int) -> str:
    ctx = await manual_context(session, "god_war", rules, key=f"{son_id}:{god_id}")
    return (await foreign_god_war(ctx, son_id, god_id, "by the creator's command")).text


async def order_temple_raid(session: AsyncSession, rules: Rules, god_id: int, temple_id: int) -> str:
    ctx = await manual_context(session, "temple_raid", rules, key=f"{god_id}:{temple_id}")
    god = await _god(session, god_id)
    temple = await session.get(EntityRow, temple_id)
    if temple is None or temple.engine_kind is not EngineKind.TEMPLE or temple.status is not EntityStatus.CANON:
        raise NotFoundError("No such standing temple.")
    await destroy_temple(ctx, god, temple)
    return f"{god.name} destroyed {temple.name}."


async def wake_foreign_god(session: AsyncSession, rules: Rules, god_id: int) -> ForeignGodRow:
    god = await _god(session, god_id)
    if god.status is ForeignGodStatus.DEAD:
        raise ValidationFailedError(f"{god.name} is dead.")
    wake(god)
    god.defeated_epoch = None
    awaken_text(god)
    await session.flush()
    return god


async def run_pantheon_phase(session: AsyncSession, rules: Rules) -> None:
    await pantheon_phase(await manual_context(session, "pantheon", rules))


PHASES = (Phase("pantheon", pantheon_phase),)
