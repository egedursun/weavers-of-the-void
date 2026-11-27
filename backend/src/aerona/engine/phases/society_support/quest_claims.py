from collections.abc import Awaitable, Callable, Mapping
from dataclasses import dataclass

from aerona.constants.units import PERCENT
from aerona.core.total import partial, total
from aerona.db.repositories.bonds import BondDraft, BondRepository
from aerona.db.repositories.entities import EntityRepository
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.lore import ThreadRow
from aerona.db.tables.warfare import HeroQuestRow
from aerona.db.write_guard import held
from aerona.domain.enums.body import HarmCause
from aerona.domain.enums.bond import BondKind
from aerona.domain.enums.chronicle import ThreadStatus
from aerona.domain.enums.entity import EntityFlag, EntityStatus, EntityType
from aerona.domain.enums.quests import QuestAim, QuestReward, QuestScale, QuestTargetKind
from aerona.engine.context import TickContext
from aerona.engine.mortal.standing import shift_standing
from aerona.engine.phases.society_support.knowledge import teach
from aerona.engine.primitives.numbers import clamp_int
from aerona.engine.primitives.queries import close
from aerona.engine.primitives.records import retire
from aerona.engine.primitives.stats import set_stats, shift_stat, stat_or
from aerona.engine.records import death_path

ClaimFacts = Mapping[str, int]


@dataclass(frozen=True)
class Claim:
    hero: EntityRow
    quest: HeroQuestRow
    target: EntityRow
    side: EntityRow


async def find(ctx: TickContext, claim: Claim) -> ClaimFacts:
    bonds = BondRepository(ctx.session)
    for held_by in await bonds.incoming(claim.target.id, BondKind.OWNS):
        if held_by.source_node_id != claim.hero.id:
            await close(ctx.session, held_by, ctx.epoch, f"taken up by {claim.hero.name}")
    await bonds.connect(BondDraft(claim.hero.id, claim.target.id, BondKind.OWNS, ctx.epoch, "found by quest"))
    return {}


async def learn(ctx: TickContext, claim: Claim) -> ClaimFacts:
    await teach(ctx, claim.side.id, claim.target, f"{claim.hero.name} recovered it")
    await EntityRepository(ctx.session).remove_flag(claim.target.id, EntityFlag.LOST)
    return {}


async def avenge(ctx: TickContext, claim: Claim) -> ClaimFacts:
    await death_path(ctx, claim.target, f"killed by {claim.hero.name} in vengeance", claim.hero.id, "vengeance", harm=HarmCause.DUEL)
    return {}


async def resolve(ctx: TickContext, claim: Claim) -> ClaimFacts:
    thread = await ctx.session.get(ThreadRow, claim.quest.thread_id) if claim.quest.thread_id is not None else None
    if thread is not None and thread.status is ThreadStatus.OPEN:
        thread.status, thread.closed_epoch, thread.closing_text = ThreadStatus.CLOSED, ctx.epoch, f"resolved by {claim.hero.name}"
    return {}


async def hunt(ctx: TickContext, claim: Claim) -> ClaimFacts:
    shift_stat(claim.target, "population", -1, 0)
    return {}


async def destroy(ctx: TickContext, claim: Claim) -> ClaimFacts:
    if claim.target.entity_type is EntityType.MORTAL:
        await death_path(ctx, claim.target, f"destroyed by {claim.hero.name}", claim.hero.id, "quest", harm=HarmCause.DUEL)
    else:
        await retire(ctx.session, claim.target, ctx.epoch, f"Epoch {ctx.epoch}: destroyed by {claim.hero.name}.", status=EntityStatus.DESTROYED)
    return {}


async def restore(ctx: TickContext, claim: Claim) -> ClaimFacts:
    await EntityRepository(ctx.session).remove_flag(claim.target.id, EntityFlag.LOST)
    shift_stat(claim.target, "prosperity", ctx.rules.heroes.quest_charisma_gain, 0)
    return {}


async def free(ctx: TickContext, claim: Claim) -> ClaimFacts:
    bonds = BondRepository(ctx.session)
    for bond in await bonds.incoming(claim.target.id, BondKind.HOLDS_CAPTIVE):
        await bonds.deactivate(bond, ctx.epoch, f"freed by {claim.hero.name}")
    return {}


async def bind(ctx: TickContext, claim: Claim) -> ClaimFacts:
    await BondRepository(ctx.session).connect(BondDraft(claim.side.id, claim.target.id, BondKind.HOLDS_CAPTIVE, ctx.epoch, f"bound by {claim.hero.name}"))
    return {}


async def reach(ctx: TickContext, claim: Claim) -> ClaimFacts:
    claim.hero.location_id = claim.target.location_id if claim.target.location_id is not None else claim.target.id
    if claim.quest.target_kind is QuestTargetKind.PLACE:
        await EntityRepository(ctx.session).remove_flag(claim.target.id, EntityFlag.LOST)
    return {}


async def deliver(ctx: TickContext, claim: Claim) -> ClaimFacts:
    await BondRepository(ctx.session).connect(BondDraft(claim.side.id, claim.target.id, BondKind.OWNS, ctx.epoch, f"brought by {claim.hero.name}"))
    return {}


async def protect(ctx: TickContext, claim: Claim) -> ClaimFacts:
    await BondRepository(ctx.session).connect(BondDraft(claim.hero.id, claim.target.id, BondKind.PROTECTS, ctx.epoch, "sworn by quest"))
    return {}


async def reconcile(ctx: TickContext, claim: Claim) -> ClaimFacts:
    closed = await BondRepository(ctx.session).close_between(claim.side.id, claim.target.id, [BondKind.ENEMY, BondKind.RIVAL], ctx.epoch, "reconciled")
    return {"quarrels_closed": int(bool(closed))}


async def prove(ctx: TickContext, claim: Claim) -> ClaimFacts:
    set_stats(claim.hero, charisma=clamp_int(stat_or(claim.hero, "charisma", 0) + ctx.rules.heroes.quest_charisma_gain, 0, PERCENT))
    return {}


CLAIMS: Mapping[QuestAim, Callable[[TickContext, Claim], Awaitable[ClaimFacts]]] = total(
    QuestAim,
    {
        QuestAim.FIND: find,
        QuestAim.RESTORE: restore,
        QuestAim.DESTROY: destroy,
        QuestAim.FREE: free,
        QuestAim.BIND: bind,
        QuestAim.REACH: reach,
        QuestAim.LEARN: learn,
        QuestAim.RETURN: deliver,
        QuestAim.PROTECT: protect,
        QuestAim.AVENGE: avenge,
        QuestAim.HUNT: hunt,
        QuestAim.DELIVER: deliver,
        QuestAim.RECONCILE: reconcile,
        QuestAim.PROVE: prove,
        QuestAim.RESOLVE: resolve,
    },
)


REWARD_KEYS = partial(
    QuestReward,
    {
        QuestReward.RENOWN: "renown",
        QuestReward.STANDING: "honour",
        QuestReward.KNOWLEDGE: "intellect",
        QuestReward.ITEM: "wealth",
        QuestReward.CURE: "hp",
        QuestReward.PEACE: "loyalty",
    },
    without=(QuestReward.POWER, QuestReward.OFFICE),
)


SCALE_PCT: Mapping[QuestScale, Callable[[TickContext], int]] = total(
    QuestScale,
    {
        QuestScale.PERSONAL: lambda _ctx: PERCENT,
        QuestScale.LEGENDARY: lambda ctx: ctx.rules.heroes.legendary_quest_reward_pct,
    },
)


async def gained(ctx: TickContext, hero: EntityRow, key: str, amount: int) -> None:
    if not held(hero.id):
        await shift_standing(ctx.session, hero, key, amount, ctx.epoch, default=0)


async def reward_hero(ctx: TickContext, hero: EntityRow, reward: QuestReward, scale: QuestScale) -> None:
    step = ctx.rules.heroes.quest_charisma_gain * SCALE_PCT[scale](ctx) // PERCENT
    if reward is QuestReward.POWER:
        hero.power_level = clamp_int(hero.power_level + 1, 0, 12)
    elif reward is QuestReward.OFFICE:
        hero.importance = (hero.importance or 0) + 1
    else:
        await gained(ctx, hero, REWARD_KEYS[reward], step)
