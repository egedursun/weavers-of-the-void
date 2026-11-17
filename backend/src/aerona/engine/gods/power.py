from dataclasses import dataclass

from sqlalchemy import func, select

from aerona.catalog import god_lines
from aerona.catalog.rarities import build_rarity_table
from aerona.constants.units import PERCENT
from aerona.core.errors import ValidationFailedError
from aerona.core.grammar import spoken
from aerona.db.repositories.sons import PowerDraft, SonRepository
from aerona.db.tables.cosmos import CreatorRow
from aerona.db.tables.lore import ChronicleRow
from aerona.db.tables.sons import SonRow
from aerona.domain.enums.chronicle import ChronicleKind
from aerona.domain.enums.modifier import IncidentRole
from aerona.domain.enums.rarity import Rarity
from aerona.domain.enums.son import SonDeathCause, SonStatus, Stat
from aerona.domain.models.stats import STAT_CEILING, STAT_FLOOR
from aerona.engine.context import TickContext
from aerona.engine.gods.essence import gain
from aerona.engine.gods.god_death import GodDeath, god_death
from aerona.engine.gods.reputation import TraceKind, leave_trace
from aerona.engine.primitives.numbers import clamp_int, clamp_percent, ordinal
from aerona.engine.primitives.queries import living_sons
from aerona.engine.recording.record import record

DRAIN_KEYS = ("gods.power.drain",)


@dataclass(frozen=True)
class DrainResult:
    son: SonRow
    drawn: int
    gained: int


def living(son: SonRow | None) -> SonRow:
    if son is None:
        raise ValidationFailedError("No such son.")
    if son.status is SonStatus.DEAD:
        raise ValidationFailedError(f"{son.name} is dead.")
    return son


async def _drain_counts(ctx: TickContext, son_id: int) -> tuple[int, int]:
    base = select(func.count(ChronicleRow.id)).where(ChronicleRow.epoch == ctx.epoch, ChronicleRow.template_key.in_(DRAIN_KEYS))
    total = int(await ctx.session.scalar(base) or 0)
    own = int(await ctx.session.scalar(base.where(ChronicleRow.son_id == son_id)) or 0)
    return total, own


async def drained_recently(ctx: TickContext, son_id: int, spacing: int) -> bool:
    if spacing <= 0:
        return False
    statement = select(ChronicleRow.id).where(
        ChronicleRow.son_id == son_id, ChronicleRow.template_key.in_(DRAIN_KEYS), ChronicleRow.epoch > ctx.epoch - 1 - spacing
    )
    return await ctx.session.scalar(statement.limit(1)) is not None


async def drain_record(ctx: TickContext, creator: CreatorRow, son: SonRow, drawn: int, gained: int, *, spontaneous: bool, siblings: bool) -> None:
    _, times = await _drain_counts(ctx, son.id)
    await record(
        ctx,
        "gods.power.drain",
        roles={IncidentRole.ACTOR: creator.id, IncidentRole.VICTIM: son.id},
        facts={
            "drawn": drawn,
            "gained": gained,
            "times": times + 1,
            "anger": god_lines.DRAIN_ANGER if spontaneous else "",
            "again": god_lines.DRAIN_AGAIN if times else "",
            "witness": god_lines.DRAIN_WITNESS if siblings else "",
            "repeat": god_lines.DRAIN_REPEAT_SUFFIX.format(count=ordinal(times + 1)).rstrip(".") if times > 1 else "",
        },
        kind=ChronicleKind.CREATOR_HAND,
        son_id=son.id,
    )


async def drain_son(ctx: TickContext, creator: CreatorRow, son: SonRow, spontaneous: bool = False) -> DrainResult:
    rules = ctx.rules.god_power
    living(son)
    drawn = round(son.essence * rules.drain_son_pct / PERCENT)
    if drawn <= 0:
        raise ValidationFailedError(f"{son.name} has no essence left; nothing to drain.")
    _, earlier = await _drain_counts(ctx, son.id)
    fading = (rules.drain_repeat_keep_pct / PERCENT) ** earlier * (rules.auto_drain_effect_pct / PERCENT if spontaneous else 1)
    son.essence -= drawn
    son.existence = clamp_percent(son.existence - rules.drain_son_existence_loss)
    son.loyalty = clamp_percent(son.loyalty - round(rules.drain_son_loyalty_loss * fading))
    son.wrath = clamp_percent(son.wrath + round(rules.drain_son_wrath * fading))
    others = [other for other in await living_sons(ctx.session) if other.id != son.id]
    for other in others:
        other.loyalty = clamp_percent(other.loyalty + rules.drain_witness_loyalty)
    gained = gain(creator, drawn * rules.drain_son_efficiency_pct / PERCENT)
    await drain_record(ctx, creator, son, drawn, gained, spontaneous=spontaneous, siblings=bool(others))
    await leave_trace(ctx.session, ctx.rules, TraceKind.DRAIN, son.id, ctx.epoch)
    ctx.count("drains")
    return DrainResult(son, drawn, gained)


async def friends_of(ctx: TickContext, son: SonRow) -> frozenset[int]:
    repository = SonRepository(ctx.session)
    return frozenset([other.id for other in await living_sons(ctx.session) if other.id != son.id and await repository.relation(other.id, son.id) > 0])


async def devour_son(ctx: TickContext, creator: CreatorRow, son: SonRow, reason: str = "") -> tuple[GodDeath, int]:
    rules = ctx.rules.god_power
    living(son)
    gained = gain(creator, son.essence + son.might * rules.devour_son_essence_per_might + max(1, son.level) * rules.devour_son_essence_per_level)
    son.essence = 0
    friends = await friends_of(ctx, son)
    cause = god_lines.DEVOUR_CAUSE.format(creator=creator.name) + (f": {reason}" if reason else "")
    death = await god_death(ctx, son, cause, SonDeathCause.DEVOURED)
    for other in await living_sons(ctx.session):
        other.loyalty = clamp_percent(other.loyalty + rules.devour_son_witness_loyalty)
        if other.id in friends:
            other.wrath = clamp_percent(other.wrath + rules.devour_son_friend_wrath)
    await leave_trace(ctx.session, ctx.rules, TraceKind.DEVOUR, son.id, ctx.epoch, friends=friends)
    await record(
        ctx,
        "gods.power.devour",
        roles={IncidentRole.ACTOR: creator.id, IncidentRole.AUTHORITY: son.id},
        facts={"gained": gained},
        kind=ChronicleKind.CREATOR_HAND,
        son_id=son.id,
    )
    return death, gained


async def demote_son(ctx: TickContext, creator: CreatorRow, son: SonRow) -> Rarity:
    rules = ctx.rules.god_power
    living(son)
    old = son.rarity
    if old.rank <= 0:
        raise ValidationFailedError(f"{son.name} is already in the lowest class ({spoken(old)}).")
    new = Rarity.from_rank(old.rank - 1)
    ceiling = build_rarity_table(ctx.rules)[new].stat_max
    for stat in Stat:
        setattr(son, stat.value, clamp_int(min(son.stat(stat), ceiling), STAT_FLOOR, STAT_CEILING))
    son.loyalty = clamp_percent(son.loyalty - rules.demote_loyalty_loss)
    son.wrath = clamp_percent(son.wrath + rules.demote_wrath)
    son.rarity = new
    await record(
        ctx,
        "gods.power.demote",
        roles={IncidentRole.ACTOR: creator.id, IncidentRole.AUTHORITY: son.id},
        facts={"old": old, "new": new},
        kind=ChronicleKind.CREATOR_HAND,
        son_id=son.id,
    )
    await leave_trace(ctx.session, ctx.rules, TraceKind.DEMOTE, son.id, ctx.epoch)
    return new


async def strip_power(ctx: TickContext, creator: CreatorRow, son: SonRow, slot: int) -> int:
    rules = ctx.rules.god_power
    living(son)
    repository = SonRepository(ctx.session)
    powers = await repository.powers(son.id)
    chosen = next((power for power in powers if power.slot == slot), None)
    if chosen is None:
        raise ValidationFailedError("Choose the power to strip.")
    remaining = [PowerDraft(power.name, power.description, power.effect, power.param_entity_type, power.param_stat) for power in powers if power.slot != slot]
    await repository.set_powers(son.id, remaining)
    son.wrath = clamp_percent(son.wrath + rules.strip_power_wrath)
    gained = gain(creator, rules.strip_power_essence)
    await record(
        ctx,
        "gods.power.strip",
        roles={IncidentRole.ACTOR: creator.id, IncidentRole.AUTHORITY: son.id},
        facts={"power": str(chosen.name), "gained": gained},
        kind=ChronicleKind.CREATOR_HAND,
        son_id=son.id,
    )
    await leave_trace(ctx.session, ctx.rules, TraceKind.STRIP, son.id, ctx.epoch)
    return gained


async def absolute_command(ctx: TickContext, creator: CreatorRow, son: SonRow, command: str) -> str:
    rules = ctx.rules.god_power
    living(son)
    text = command.strip()[: ctx.rules.god_actions.inspiration_max_chars]
    if not text:
        raise ValidationFailedError("Write the command.")
    son.standing_order = text
    son.order_absolute = True
    son.loyalty = clamp_percent(son.loyalty - rules.absolute_command_loyalty_loss)
    await record(
        ctx,
        "gods.power.absolute_command",
        roles={IncidentRole.ACTOR: creator.id, IncidentRole.AUTHORITY: son.id},
        facts={"command": str(text)},
        kind=ChronicleKind.ORDER,
        son_id=son.id,
    )
    return text


async def declare_rebellion(ctx: TickContext, creator: CreatorRow, son: SonRow, manifesto: str, spontaneous: bool) -> None:
    tools = ctx.rules.son_tools
    son.rebel = True
    son.loyalty = clamp_percent(son.loyalty - tools.rebel_loyalty_loss)
    son.ambition = clamp_percent(son.ambition + tools.rebel_ambition)
    repository = SonRepository(ctx.session)
    for other in await living_sons(ctx.session):
        if other.id != son.id and other.loyalty >= tools.rebel_loyal_threshold:
            await repository.change_relation(son.id, other.id, -tools.rebel_sibling_relation)
    text = manifesto if spontaneous else f'"{manifesto}"'
    await record(
        ctx,
        "gods.power.rebellion_declared",
        roles={IncidentRole.ACTOR: son.id, IncidentRole.AUTHORITY: creator.id},
        facts={"manifesto": text},
        kind=ChronicleKind.REBELLION,
        son_id=son.id,
    )
    ctx.count("rebellions")


async def end_rebellion(ctx: TickContext, creator: CreatorRow, son: SonRow) -> None:
    son.rebel = False
    await record(
        ctx, "gods.power.rebellion_ended", roles={IncidentRole.ACTOR: son.id, IncidentRole.AUTHORITY: creator.id}, kind=ChronicleKind.REBELLION, son_id=son.id
    )
    ctx.count("rebellions_ended")
