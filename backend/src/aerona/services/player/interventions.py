import json
from enum import StrEnum
from typing import Any

from pydantic import BaseModel
from sqlalchemy import func, select

from aerona.catalog.interventions import DISASTERS, MIRACLES
from aerona.catalog.stats import max_essence, max_hp
from aerona.core.errors import ValidationFailedError
from aerona.db.repositories.bonds import BondRepository
from aerona.db.repositories.entities import EntityRepository
from aerona.db.tables.bonds import BondRow
from aerona.db.tables.entities import EntityRow
from aerona.domain.enums.action import ActionKind
from aerona.domain.enums.bond import BondKind, BondState
from aerona.domain.enums.chronicle import ChronicleKind
from aerona.domain.enums.entity import LOCATION_TYPES, EntityFlag, EntityStatus, EntityType
from aerona.domain.enums.intervention import Disaster, InterventionKind, Miracle
from aerona.domain.enums.job import JobKind
from aerona.domain.enums.limits import PERCENT_MAX
from aerona.domain.enums.son import SonStatus, Stat
from aerona.domain.models.stats import STAT_CEILING
from aerona.engine.context import TickContext
from aerona.engine.gods.interventions import MiracleEffect, apply_miracle
from aerona.engine.gods.power import end_rebellion
from aerona.engine.gods.stats import Trait, add_trait
from aerona.engine.phases.disasters import apply_disaster, record_disaster_event
from aerona.engine.phases.society_support.knowledge import teach
from aerona.engine.primitives.numbers import clamp_percent
from aerona.engine.services.war import ongoing_wars
from aerona.events.kinds import EventKind
from aerona.jobs.context import JobContext
from aerona.rules.registry import Rules
from aerona.services.player import guards
from aerona.services.player.chronicle import tell
from aerona.services.player.lines import (
    BLESSED,
    CHAINED,
    CURSED,
    DEFIANT,
    DISASTER,
    EXILED,
    KNOWLEDGE_FORGOTTEN,
    KNOWLEDGE_TAUGHT,
    LIGHTNING,
    MIRACLE,
    PARDONED,
    PEACE_EFFECT,
    SUPPRESS_FAILED,
    SUPPRESSED,
)
from aerona.services.player.ports import RevelationRequest
from aerona.services.player.runtime import CostedJob, PlayerRuntime, submit_costed, unavailable
from aerona.services.player.scope import ActionOutcome, Command, Effect, PlayerScope, player_action

CURSE_TRAITS = (Trait.PROSPERITY, Trait.FERTILITY, Trait.STRENGTH, Trait.DEFENSE, Trait.WEALTH, Trait.ABUNDANCE, Trait.INFLUENCE)
PEACE_REASON = "a miracle of peace"


class BlessingKind(StrEnum):
    ESSENCE = "essence"
    HP = "hp"
    STAT = "stat"
    EXISTENCE = "existence"


class PunishmentKind(StrEnum):
    LIGHTNING = "lightning"
    CHAIN = "chain"
    EXILE = "exile"
    SUPPRESS = "suppress"
    PARDON = "pardon"


class Revelation(Command):
    content: str
    entity_type: str | None = None
    world_id: int | None = None
    mechanic: str | None = None


class Bless(Command):
    son_id: int
    kind: BlessingKind
    stat: Stat | None = None


class Punish(Command):
    son_id: int
    kind: PunishmentKind


class Intervene(Command):
    entity_id: int
    action: InterventionKind
    miracle: Miracle | None = None
    disaster: Disaster | None = None
    knowledge_id: int | None = None


class SetKnowledge(Command):
    entity_id: int
    knowledge_id: int
    known: bool = True


class KnownKnowledge(BaseModel):
    id: int
    name: str
    branch: str | None


async def revelation(runtime: PlayerRuntime, rules: Rules, command: Revelation) -> ActionOutcome:
    if not command.content.strip():
        raise ValidationFailedError("A revelation needs content.")
    author = runtime.ports.revelations
    if author is None:
        raise unavailable("A revelation")
    async with runtime.database.read() as session:
        await guards.target_world(session, command.world_id)
    request = RevelationRequest(command.content.strip(), command.entity_type, command.world_id, command.mechanic)

    async def work(context: JobContext) -> dict[str, Any] | None:
        context.report(0.0, "revelation")
        record_id = await author.reveal(request)
        runtime.bus.publish(EventKind.REVELATION, {"record_id": record_id})
        return {"record_id": record_id}

    job = CostedJob("revelation", ActionKind.REVELATION, JobKind.REVELATION, "revelation", rules.costs.revelation, "costs.revelation")
    return await submit_costed(runtime, rules, job, command, work)


@player_action("bless", ActionKind.BLESS_ESSENCE)
async def bless(scope: PlayerScope, command: Bless) -> Effect:
    son = await guards.living_son(scope.session, command.son_id)
    rules = scope.rules
    actions = rules.god_actions
    costs = rules.costs
    creator = await scope.creator()
    if command.kind is BlessingKind.ESSENCE:
        ceiling = max_essence(rules, son.might)
        if son.essence >= ceiling:
            raise ValidationFailedError(f"{son.name}'s essence is already full.")
        spent = guards.charge(creator, costs.bless_essence, "costs.bless_essence")
        son.essence = min(ceiling, son.essence + actions.bless_essence_amount)
        gift, kind = f"+{actions.bless_essence_amount} essence", ActionKind.BLESS_ESSENCE
    elif command.kind is BlessingKind.HP:
        ceiling = max_hp(rules, son.endurance)
        if son.hp >= ceiling:
            raise ValidationFailedError(f"{son.name}'s health is already full.")
        spent = guards.charge(creator, costs.bless_hp, "costs.bless_hp")
        son.hp = ceiling
        gift, kind = "full health", ActionKind.BLESS_HP
    elif command.kind is BlessingKind.STAT:
        if command.stat is None:
            raise ValidationFailedError("Choose the stat to bless.")
        current = int(getattr(son, command.stat.value))
        if current >= STAT_CEILING:
            raise ValidationFailedError(f"{son.name}'s {command.stat.value} is already at its peak.")
        spent = guards.charge(creator, costs.bless_stat, "costs.bless_stat")
        setattr(son, command.stat.value, min(STAT_CEILING, current + actions.bless_stat_amount))
        gift, kind = f"+{actions.bless_stat_amount} {command.stat.value}", ActionKind.BLESS_STAT
    else:
        if son.existence >= PERCENT_MAX:
            raise ValidationFailedError(f"{son.name}'s existence is already whole.")
        spent = guards.charge(creator, costs.bless_essence, "costs.bless_essence")
        son.existence = clamp_percent(son.existence + actions.bless_existence_amount)
        gift, kind = f"+{actions.bless_existence_amount} existence", ActionKind.BLESS_EXISTENCE
    son.loyalty = clamp_percent(son.loyalty + actions.bless_loyalty)
    ctx = await scope.context("bless")
    message = await tell(ctx, BLESSED, son_id=son.id, creator=creator.name, son=son.name, gift=gift)
    return Effect(message, son.id, essence_spent=spent, kind=kind, tool=f"bless:{command.kind.value}")


async def _suppress(scope: PlayerScope, ctx: TickContext, son_id: int) -> Effect:
    actions = scope.rules.god_actions
    son = await guards.living_son(scope.session, son_id)
    if not son.rebel:
        raise ValidationFailedError(f"{son.name} is not in rebellion.")
    creator = await scope.creator()
    spent = guards.charge(creator, scope.rules.balance.suppress_revolt, "balance.suppress_revolt")
    rng = ctx.rng(f"suppress.{son.id}")
    god_roll = actions.suppress_base + creator.essence // actions.suppress_essence_divisor + rng.die(actions.suppress_die)
    son_roll = round(son.will + son.strength * actions.suppress_son_strength_pct / 100 + son.level * actions.suppress_son_per_level) + rng.die(
        actions.suppress_die
    )
    if god_roll >= son_roll:
        son.rebel = False
        son.loyalty = clamp_percent(son.loyalty + actions.suppress_loyalty_gain)
        son.hp = max(1, round(son.hp * actions.suppress_hp_left_pct / 100))
        son.fame = max(0, son.fame - actions.suppress_renown_loss)
        line, kind = SUPPRESSED, ActionKind.SUPPRESS_REBELLION
    else:
        son.fame += actions.suppress_fail_renown
        son.ambition = clamp_percent(son.ambition + actions.suppress_fail_ambition)
        creator.essence = max(0, creator.essence - actions.suppress_fail_essence)
        line, kind = SUPPRESS_FAILED, ActionKind.SUPPRESS_FAILED
    message = await tell(ctx, line, son_id=son.id, kind=ChronicleKind.REBELLION, creator=creator.name, son=son.name, god=god_roll, son_roll=son_roll)
    return Effect(message, son.id, essence_spent=spent, kind=kind, values={"won": god_roll >= son_roll})


async def _pardon(scope: PlayerScope, ctx: TickContext, son_id: int) -> Effect:
    son = await guards.living_son(scope.session, son_id)
    if son.status is not SonStatus.EXILED and not son.chained and not son.rebel:
        raise ValidationFailedError(f"{son.name} has nothing to be pardoned for.")
    creator = await scope.creator()
    if son.status is SonStatus.EXILED:
        son.status = SonStatus.ACTIVE
    if son.rebel:
        await end_rebellion(ctx, creator, son)
    son.chained = False
    son.loyalty = clamp_percent(son.loyalty + scope.rules.god_actions.pardon_loyalty)
    message = await tell(ctx, PARDONED, son_id=son.id, creator=creator.name, son=son.name)
    return Effect(message, son.id, kind=ActionKind.FORGIVE)


@player_action("punish", ActionKind.LIGHTNING)
async def punish(scope: PlayerScope, command: Punish) -> Effect:
    ctx = await scope.context("punish")
    if command.kind is PunishmentKind.SUPPRESS:
        return await _suppress(scope, ctx, command.son_id)
    if command.kind is PunishmentKind.PARDON:
        return await _pardon(scope, ctx, command.son_id)
    son = await guards.living_son(scope.session, command.son_id)
    actions = scope.rules.god_actions
    creator = await scope.creator()
    spent = 0
    if command.kind is PunishmentKind.LIGHTNING:
        spent = guards.charge(creator, scope.rules.costs.lightning, "costs.lightning")
        son.hp = max(1, son.hp - round(max_hp(scope.rules, son.endurance) * actions.lightning_hp_pct / 100))
        line, kind = LIGHTNING, ActionKind.LIGHTNING
    elif command.kind is PunishmentKind.CHAIN:
        if son.chained:
            raise ValidationFailedError(f"{son.name} is already chained.")
        if son.last_acted_epoch >= ctx.epoch:
            raise ValidationFailedError(f"{son.name} already acted this epoch; chains come too late.")
        son.chained = True
        line, kind = CHAINED, ActionKind.CHAIN
    else:
        if son.status is SonStatus.EXILED:
            raise ValidationFailedError(f"{son.name} is already in exile.")
        son.status = SonStatus.EXILED
        line, kind = EXILED, ActionKind.EXILE_SON
    message = await tell(ctx, line, son_id=son.id, creator=creator.name, son=son.name)
    if son.will > actions.defiant_will:
        son.loyalty = clamp_percent(son.loyalty - actions.punish_defiant_loyalty_loss)
        son.wrath = clamp_percent(son.wrath + actions.punish_defiant_wrath)
        message = f"{message} {await tell(ctx, DEFIANT, son_id=son.id, son=son.name)}"
    else:
        son.loyalty = clamp_percent(son.loyalty + actions.punish_submissive_loyalty)
        son.wrath = clamp_percent(son.wrath + actions.punish_submissive_wrath)
    return Effect(message, son.id, essence_spent=spent, kind=kind, tool=f"punish:{command.kind.value}")


async def _fingerprint(scope: PlayerScope, target: EntityRow) -> str:
    flags = sorted(flag.value for flag in await EntityRepository(scope.session).flags(target.id))
    enemies = await scope.session.scalar(
        select(func.count())
        .select_from(BondRow)
        .where(
            BondRow.kind == BondKind.ENEMY,
            BondRow.state == BondState.ACTIVE,
            (BondRow.source_node_id == target.id) | (BondRow.target_node_id == target.id),
        )
    )
    wars = len(await ongoing_wars(scope.session, target.id))
    return json.dumps([target.stats.model_dump(mode="json"), flags, enemies, wars, target.status.value], sort_keys=True)


MIRACLE_NOTES = {
    MiracleEffect.HEALTH: "health restored",
    MiracleEffect.CURSE_LIFTED: "curse lifted",
    MiracleEffect.BOUNTY: "the land and stores filled",
    MiracleEffect.DEFENSE: "defence rose",
    MiracleEffect.SHIELD: "shielded from the next disaster",
}


async def _miracle(ctx: TickContext, target: EntityRow, miracle: Miracle) -> list[str]:
    outcome = await apply_miracle(ctx, target, miracle, PEACE_REASON)
    notes: list[str] = []
    for effect in outcome.effects:
        if effect is MiracleEffect.GROWTH:
            notes.extend(f"{key.value} grew" for key in outcome.grown)
        elif effect is MiracleEffect.SENSES:
            notes.append(f"{', '.join(outcome.restored)} came to their senses")
        elif effect is MiracleEffect.PEACE:
            notes.append(f"{PEACE_EFFECT} ({outcome.peace_made})")
        else:
            notes.append(MIRACLE_NOTES[effect])
    return notes


async def _curse(ctx: TickContext, target: EntityRow) -> list[str]:
    loss = ctx.rules.god_actions.curse_stat_loss
    notes = [key.value for key in CURSE_TRAITS if add_trait(target, key, -loss)]
    if await EntityRepository(ctx.session).add_flag(target.id, EntityFlag.CURSED, ctx.epoch):
        notes.append("marked as cursed")
    await ctx.session.flush()
    return notes


@player_action("intervene", ActionKind.MIRACLE)
async def intervene(scope: PlayerScope, command: Intervene) -> Effect:
    target = await guards.canon_entity(scope.session, command.entity_id)
    creator = await scope.creator()
    costs = scope.rules.intervention_costs
    ctx = await scope.context(f"intervene.{command.action.value}")
    tool = f"intervene:{command.action.value}"
    if command.action is InterventionKind.MIRACLE:
        if command.miracle is None:
            raise ValidationFailedError(f"Choose a miracle: {', '.join(MIRACLES)}.")
        spent = guards.charge(creator, costs.miracle, "intervention_costs.miracle")
        before = await _fingerprint(scope, target)
        notes = await _miracle(ctx, target, command.miracle)
        if await _fingerprint(scope, target) == before:
            raise ValidationFailedError(f"The miracle found nothing to change in {target.name}; the essence was returned.")
        label = MIRACLES[command.miracle].label.lower()
        message = await tell(
            ctx, MIRACLE, ids=[target.id], kind=ChronicleKind.MIRACLE, creator=creator.name, label=label, entity=target.name, effects=", ".join(notes) or label
        )
        return Effect(message, target.id, essence_spent=spent, kind=ActionKind.MIRACLE, tool=tool)
    if command.action is InterventionKind.DISASTER:
        if command.disaster is None:
            raise ValidationFailedError(f"Choose a disaster: {', '.join(DISASTERS)}.")
        if target.entity_type not in LOCATION_TYPES:
            raise ValidationFailedError("Disasters strike regions, places and settlements.")
        spent = guards.charge(creator, costs.disaster, "intervention_costs.disaster")
        actions = scope.rules.god_actions
        impact = await apply_disaster(ctx, target, command.disaster, actions.disaster_severity_pct / 100)
        event = await record_disaster_event(ctx, target, command.disaster, actions.disaster_event_severity, impact)
        detail = f"; {'; '.join(impact.notes)}" if impact.notes else ""
        label = DISASTERS[command.disaster].label.lower()
        message = await tell(
            ctx, DISASTER, ids=[target.id, event.id], kind=ChronicleKind.DISASTER, creator=creator.name, label=label, entity=target.name, notes=detail
        )
        return Effect(message, target.id, essence_spent=spent, created_ids=(event.id,), kind=ActionKind.DISASTER, tool=tool, values={"dead": len(impact.dead)})
    if command.action is InterventionKind.TEACH_KNOWLEDGE:
        if command.knowledge_id is None:
            raise ValidationFailedError("Choose the knowledge to teach.")
        knowledge = await guards.canon_entity(scope.session, command.knowledge_id, "This knowledge")
        if knowledge.entity_type is not EntityType.KNOWLEDGE:
            raise ValidationFailedError("Only a knowledge record can be taught.")
        spent = guards.charge(creator, costs.teach_knowledge, "intervention_costs.teach_knowledge")
        if not await teach(ctx, target.id, knowledge, f"taught by {creator.name}"):
            raise ValidationFailedError(f"{target.name} already knows {knowledge.name}; the essence was returned.")
        message = await tell(
            ctx,
            KNOWLEDGE_TAUGHT,
            ids=[target.id, knowledge.id],
            kind=ChronicleKind.KNOWLEDGE,
            creator=creator.name,
            entity=target.name,
            knowledge=knowledge.name,
        )
        return Effect(message, target.id, essence_spent=spent, kind=ActionKind.TEACH_KNOWLEDGE, tool=tool)
    spent = guards.charge(creator, costs.curse, "intervention_costs.curse")
    before = await _fingerprint(scope, target)
    notes = await _curse(ctx, target)
    if await _fingerprint(scope, target) == before:
        raise ValidationFailedError(f"The curse found nothing to wither in {target.name}; the essence was returned.")
    message = await tell(ctx, CURSED, ids=[target.id], creator=creator.name, entity=target.name, effects=", ".join(notes))
    return Effect(message, target.id, essence_spent=spent, kind=ActionKind.CURSE, tool=tool)


async def known_knowledge(scope: PlayerScope, entity_id: int) -> list[KnownKnowledge]:
    await guards.entity(scope.session, entity_id)
    rows = await scope.session.scalars(
        select(EntityRow)
        .join(BondRow, BondRow.target_node_id == EntityRow.id)
        .where(
            BondRow.source_node_id == entity_id,
            BondRow.kind == BondKind.KNOWS,
            BondRow.state == BondState.ACTIVE,
            EntityRow.entity_type == EntityType.KNOWLEDGE,
            EntityRow.status == EntityStatus.CANON,
        )
        .order_by(EntityRow.id)
    )
    return [KnownKnowledge(id=row.id, name=row.name, branch=row.knowledge_branch.value if row.knowledge_branch else None) for row in rows]


@player_action("knowledge:set", ActionKind.EDIT_RECORD)
async def set_knowledge(scope: PlayerScope, command: SetKnowledge) -> Effect:
    target = await guards.canon_entity(scope.session, command.entity_id)
    knowledge = await guards.entity(scope.session, command.knowledge_id)
    if knowledge.entity_type is not EntityType.KNOWLEDGE:
        raise ValidationFailedError("Only a knowledge record can be known.")
    creator = await scope.creator()
    ctx = await scope.context("knowledge_set")
    if command.known:
        if not await teach(ctx, target.id, knowledge, f"by {creator.name}'s hand"):
            raise ValidationFailedError(f"{target.name} already knows {knowledge.name}.")
        message = await tell(
            ctx,
            KNOWLEDGE_TAUGHT,
            ids=[target.id, knowledge.id],
            kind=ChronicleKind.KNOWLEDGE,
            creator=creator.name,
            entity=target.name,
            knowledge=knowledge.name,
        )
        return Effect(message, target.id)
    closed = await BondRepository(scope.session).close_between(target.id, knowledge.id, [BondKind.KNOWS], ctx.epoch, "forgotten by the god's hand")
    if not closed:
        raise ValidationFailedError(f"{target.name} does not know {knowledge.name}.")
    message = await tell(ctx, KNOWLEDGE_FORGOTTEN, ids=[target.id, knowledge.id], kind=ChronicleKind.KNOWLEDGE, entity=target.name, knowledge=knowledge.name)
    return Effect(message, target.id)
