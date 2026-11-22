from dataclasses import dataclass
from enum import StrEnum

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.catalog.creator import ACTION_PASSIONS, CREATOR_PASSIONS, polarity_of
from aerona.core.errors import NotFoundError, ValidationFailedError
from aerona.db.tables.agency import ActionRecordRow
from aerona.db.tables.cosmos import CreatorRow
from aerona.db.tables.lore import MessageRow
from aerona.db.tables.sons import SonRow
from aerona.domain.enums.action import ActionKind, ActionPolarity
from aerona.domain.enums.agent import MessageIntent
from aerona.domain.enums.chronicle import ChronicleKind
from aerona.domain.enums.creator import CreatorPassion
from aerona.domain.enums.modifier import IncidentRole
from aerona.domain.enums.node import ActorKind
from aerona.domain.enums.son import ReputationLabel, SonStatus
from aerona.engine.context import TickContext
from aerona.engine.divine.prayer_window import last_run, overdue_in_run, still_awaiting
from aerona.engine.gods.queries import creator_row
from aerona.engine.primitives.numbers import clamp_float, clamp_percent, decay_weight, decayed_value
from aerona.engine.primitives.queries import living_sons
from aerona.engine.recording.record import record
from aerona.rules.registry import Rules

TRACE_ONLY_KINDS = frozenset({ActionKind.DRAIN_ESSENCE, ActionKind.DEVOUR, ActionKind.DEMOTE})
NOTABLE_LABELS = frozenset({ReputationLabel.FORGOTTEN, ReputationLabel.HATED, ReputationLabel.LOVED, ReputationLabel.FEARED})


class TraceKind(StrEnum):
    DRAIN = "drain"
    DEVOUR = "devour"
    DEMOTE = "demote"
    STRIP = "strip"


@dataclass(frozen=True)
class Reputation:
    love: int
    fear: int
    forgotten: int
    unanswered: int
    last_contact: int
    label: ReputationLabel


@dataclass(frozen=True)
class ReputationAxes:
    love: int = 0
    fear: int = 0
    forgotten: int = 0


@dataclass(frozen=True)
class CosmosReputation:
    love: int
    fear: int
    forgotten: int
    label: ReputationLabel
    sons: tuple[tuple[SonRow, Reputation], ...]
    passions: tuple[CreatorPassion, ...]
    automatic: bool


def reputation_label(rules: Rules, love: int, fear: int, forgotten: int, loyalty: int) -> ReputationLabel:
    table = rules.reputation
    checks = (
        (forgotten >= table.forgotten_min_neglect and love < table.forgotten_love_below and fear < table.forgotten_fear_below, ReputationLabel.FORGOTTEN),
        (fear >= table.hated_min_fear and love < table.hated_love_below and loyalty < table.hated_loyalty_below, ReputationLabel.HATED),
        (fear >= table.respected_min_fear and love >= table.respected_min_love, ReputationLabel.RESPECTED),
        (fear >= table.feared_min_fear, ReputationLabel.FEARED),
        (love >= table.loved_min_love, ReputationLabel.LOVED),
        (forgotten >= table.distant_min_neglect, ReputationLabel.DISTANT),
    )
    return next((label for matched, label in checks if matched), ReputationLabel.ACKNOWLEDGED)


def event_polarity(kind: ActionKind) -> ActionPolarity:
    if kind in TRACE_ONLY_KINDS:
        return ActionPolarity.NEUTRAL
    return polarity_of(kind)


async def compute_reputation(session: AsyncSession, rules: Rules, son: SonRow, epoch: int, creator: CreatorRow | None) -> Reputation:
    table = rules.reputation
    horizon = epoch - table.window_epochs
    love = 0.0
    fear = 0.0
    last_contact = son.birth_epoch
    acts = await session.execute(
        select(ActionRecordRow.kind, ActionRecordRow.epoch).where(
            ActionRecordRow.target_node_id == son.id, ActionRecordRow.actor_kind == ActorKind.CREATOR, ActionRecordRow.epoch > horizon
        )
    )
    for kind, acted in acts:
        weight = decay_weight(table.decay_keep_pct, epoch - acted)
        polarity = event_polarity(kind)
        if polarity is ActionPolarity.BENEVOLENT:
            love += table.love_per_grace_event * weight
            last_contact = max(last_contact, acted)
        elif polarity is ActionPolarity.STERN:
            fear += table.fear_per_punish_event * weight
            last_contact = max(last_contact, acted)
    if creator is not None:
        messages = await session.execute(
            select(MessageRow.intent, MessageRow.epoch).where(
                MessageRow.sender_node_id == creator.id, MessageRow.recipient_node_id == son.id, MessageRow.epoch > horizon
            )
        )
        for intent, sent in messages:
            weight = decay_weight(table.decay_keep_pct, epoch - sent)
            if intent is MessageIntent.THREAT:
                fear += table.fear_per_threat * weight
            else:
                love += table.love_per_message * weight
            last_contact = max(last_contact, sent)
    if son.standing_order:
        last_contact = epoch
    unanswered = 0
    unanswered_weight = 0.0
    if creator is not None:
        unanswered, unanswered_weight = await _son_prayers(session, rules, son, creator, epoch)
    anger = creator.mood_anger if creator is not None else table.default_wrath
    interest = creator.mood_interest if creator is not None else table.default_attention
    loyalty = son.loyalty
    love_value = clamp_percent(
        table.love_base + love + loyalty / table.love_loyalty_divisor - unanswered_weight * table.love_per_unanswered_prayer + son.manual_love + son.trace_love
    )
    fear_value = clamp_percent(
        table.fear_base
        + fear
        + (anger - table.default_wrath) / table.fear_wrath_divisor
        + (table.chained_fear if son.chained else 0)
        + son.manual_fear
        + son.trace_fear
    )
    forgotten_value = clamp_percent(
        (epoch - last_contact) * table.neglect_per_epoch
        + unanswered_weight * table.neglect_per_unanswered_prayer
        + max(0, table.attention_threshold - interest) / table.neglect_attention_divisor
        + son.manual_forgotten
    )
    return Reputation(
        love=love_value,
        fear=fear_value,
        forgotten=forgotten_value,
        unanswered=unanswered,
        last_contact=last_contact,
        label=reputation_label(rules, love_value, fear_value, forgotten_value, loyalty),
    )


async def _son_prayers(session: AsyncSession, rules: Rules, son: SonRow, creator: CreatorRow, epoch: int) -> tuple[int, float]:
    table = rules.reputation
    statement = select(MessageRow.epoch, overdue_in_run(last_run(epoch))).where(
        MessageRow.sender_node_id == son.id,
        MessageRow.recipient_node_id == creator.id,
        still_awaiting(),
        MessageRow.intent != MessageIntent.CHAT,
        MessageRow.epoch > epoch - table.window_epochs,
    )
    rows = list(await session.execute(statement))
    return len(rows), sum(decay_weight(table.decay_keep_pct, epoch - sent) for sent, overdue in rows if overdue)


def store_reputation(son: SonRow, reputation: Reputation, epoch: int) -> None:
    son.reputation_love = reputation.love
    son.reputation_fear = reputation.fear
    son.reputation_forgotten = reputation.forgotten
    son.reputation_unanswered = reputation.unanswered
    son.reputation_last_contact_epoch = reputation.last_contact
    son.reputation_label = reputation.label
    son.reputation_epoch = epoch


async def refresh_reputation(session: AsyncSession, rules: Rules, son: SonRow, epoch: int) -> Reputation:
    reputation = await compute_reputation(session, rules, son, epoch, await creator_row(session))
    store_reputation(son, reputation, epoch)
    await session.flush()
    return reputation


def label_drift(rules: Rules, label: ReputationLabel) -> tuple[int, int]:
    table = rules.reputation
    return {
        ReputationLabel.LOVED: (table.loved_loyalty_gain, 0),
        ReputationLabel.RESPECTED: (table.respected_loyalty_gain, table.respected_wrath_gain),
        ReputationLabel.FEARED: (0, table.feared_wrath_gain),
        ReputationLabel.HATED: (-table.hated_loyalty_loss, table.hated_wrath_gain),
        ReputationLabel.FORGOTTEN: (-table.forgotten_loyalty_loss, 0),
        ReputationLabel.DISTANT: (-table.distant_loyalty_loss, 0),
        ReputationLabel.ACKNOWLEDGED: (0, 0),
    }[label]


def decay_pushes(rules: Rules, son: SonRow) -> None:
    table = rules.reputation
    son.manual_love = decayed_value(son.manual_love, table.manual_push_keep_pct, table.manual_push_floor)
    son.manual_fear = decayed_value(son.manual_fear, table.manual_push_keep_pct, table.manual_push_floor)
    son.manual_forgotten = decayed_value(son.manual_forgotten, table.manual_push_keep_pct, table.manual_push_floor)
    son.trace_love = decayed_value(son.trace_love, table.power_trace_keep_pct, table.power_trace_floor)
    son.trace_fear = decayed_value(son.trace_fear, table.power_trace_keep_pct, table.power_trace_floor)


async def drift_son(ctx: TickContext, son: SonRow, creator: CreatorRow | None) -> Reputation:
    previous = son.reputation_label
    reputation = await compute_reputation(ctx.session, ctx.rules, son, ctx.epoch, creator)
    loyalty_delta, wrath_delta = label_drift(ctx.rules, reputation.label)
    if son.rebel:
        loyalty_delta = max(0, loyalty_delta) + ctx.rules.reputation.rebel_loyalty_recovery
        wrath_delta = min(0, wrath_delta) - ctx.rules.reputation.rebel_wrath_cooling
    son.loyalty = clamp_percent(son.loyalty + loyalty_delta)
    son.wrath = clamp_percent(son.wrath + wrath_delta)
    store_reputation(son, reputation, ctx.epoch)
    decay_pushes(ctx.rules, son)
    if previous is not None and previous is not reputation.label and reputation.label in NOTABLE_LABELS:
        await record(
            ctx,
            "gods.reputation.change",
            roles={IncidentRole.ACTOR: son.id},
            facts={"label": reputation.label},
            kind=ChronicleKind.CREATOR_REPUTATION,
            son_id=son.id,
        )
        ctx.count("label_changes")
    await ctx.session.flush()
    return reputation


async def push_reputation(session: AsyncSession, rules: Rules, son: SonRow, delta: ReputationAxes, epoch: int) -> Reputation:
    if son.status is SonStatus.DEAD:
        raise ValidationFailedError(f"{son.name} is dead; your place in their eyes no longer changes.")
    cap = rules.reputation.manual_push_cap
    updated = (
        int(clamp_float(son.manual_love + delta.love, -cap, cap)),
        int(clamp_float(son.manual_fear + delta.fear, -cap, cap)),
        int(clamp_float(son.manual_forgotten + delta.forgotten, -cap, cap)),
    )
    if updated == (son.manual_love, son.manual_fear, son.manual_forgotten):
        raise ValidationFailedError(
            f"Manual push is at its limit: each may be at most ±{cap} (world rule reputation.manual_push_cap = {cap}); pushes decay every epoch."
        )
    son.manual_love, son.manual_fear, son.manual_forgotten = updated
    return await refresh_reputation(session, rules, son, epoch)


def trace_deltas(rules: Rules, kind: TraceKind) -> tuple[ReputationAxes, ReputationAxes, ReputationAxes]:
    table = rules.reputation
    if kind is TraceKind.DRAIN:
        return ReputationAxes(love=-table.drain_love_loss, fear=table.drain_fear), ReputationAxes(fear=table.drain_sibling_fear), ReputationAxes()
    if kind is TraceKind.DEVOUR:
        return ReputationAxes(), ReputationAxes(fear=table.devour_sibling_fear), ReputationAxes(love=-table.devour_friend_love_loss)
    if kind is TraceKind.DEMOTE:
        return ReputationAxes(love=-table.demote_love_loss, fear=table.demote_fear), ReputationAxes(fear=table.demote_sibling_fear), ReputationAxes()
    return ReputationAxes(love=-table.strip_power_love_loss, fear=table.strip_power_fear), ReputationAxes(fear=table.strip_power_sibling_fear), ReputationAxes()


async def leave_trace(
    session: AsyncSession, rules: Rules, kind: TraceKind, son_id: int, epoch: int, *, friends: frozenset[int] = frozenset()
) -> dict[int, ReputationAxes]:
    target_delta, sibling_delta, friend_delta = trace_deltas(rules, kind)
    cap = rules.reputation.power_trace_cap
    applied: dict[int, ReputationAxes] = {}
    for son in await living_sons(session):
        delta = target_delta if son.id == son_id else sibling_delta
        love = delta.love + (friend_delta.love if son.id in friends else 0)
        fear = delta.fear
        if not love and not fear:
            continue
        son.trace_love = int(clamp_float(son.trace_love + love, -cap, cap))
        son.trace_fear = int(clamp_float(son.trace_fear + fear, -cap, cap))
        await refresh_reputation(session, rules, son, epoch)
        applied[son.id] = ReputationAxes(love=love, fear=fear)
    return applied


async def read_passions(session: AsyncSession, rules: Rules, epoch: int) -> list[CreatorPassion]:
    table = rules.reputation
    statement = select(ActionRecordRow.kind).where(ActionRecordRow.actor_kind == ActorKind.CREATOR, ActionRecordRow.epoch > epoch - table.passion_window_epochs)
    scores = dict.fromkeys(CREATOR_PASSIONS, 0)
    for kind in await session.scalars(statement):
        for passion in ACTION_PASSIONS.get(kind, frozenset()):
            scores[passion] += table.passion_points_per_action
    ranked = sorted((passion for passion, score in scores.items() if score > 0), key=lambda passion: -scores[passion])
    return ranked[: table.max_passions] or [CreatorPassion.SILENCE]


async def creator_passions(session: AsyncSession, rules: Rules, epoch: int) -> tuple[list[CreatorPassion], bool]:
    creator = await creator_row(session)
    if creator is None:
        return [], True
    if not creator.passions_automatic:
        return list(creator.passions), False
    return list(creator.passions) or await read_passions(session, rules, epoch), True


async def refresh_automatic_passions(session: AsyncSession, rules: Rules, epoch: int) -> None:
    creator = await creator_row(session)
    if creator is not None and creator.passions_automatic:
        creator.passions = await read_passions(session, rules, epoch)
        await session.flush()


def clean_passions(rules: Rules, passions: list[CreatorPassion]) -> list[CreatorPassion]:
    cleaned = list(dict.fromkeys(passions))[: rules.reputation.max_passions]
    if not cleaned:
        raise ValidationFailedError(f"Pick at least one passion (at most {rules.reputation.max_passions}).")
    return cleaned


async def cosmos_reputation(session: AsyncSession, rules: Rules, epoch: int) -> CosmosReputation:
    creator = await creator_row(session)
    if creator is None:
        raise NotFoundError("The Creator has not been made yet.")
    entries: list[tuple[SonRow, Reputation]] = []
    for son in await living_sons(session):
        entries.append((son, await compute_reputation(session, rules, son, epoch, creator)))
    count = len(entries)
    love = round(sum(item.love for _, item in entries) / count) if count else 0
    fear = round(sum(item.fear for _, item in entries) / count) if count else 0
    forgotten = round(sum(item.forgotten for _, item in entries) / count) if count else 0
    passions, automatic = await creator_passions(session, rules, epoch)
    return CosmosReputation(
        love=love,
        fear=fear,
        forgotten=forgotten,
        label=reputation_label(rules, love, fear, forgotten, rules.reputation.default_loyalty),
        sons=tuple(entries),
        passions=tuple(passions),
        automatic=automatic,
    )
