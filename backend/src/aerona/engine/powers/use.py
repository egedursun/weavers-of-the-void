from collections.abc import Awaitable, Callable, Mapping
from dataclasses import dataclass

from sqlalchemy import select

from aerona.catalog.kinds.resistances import RESISTANCES
from aerona.constants.units import PERCENT
from aerona.core.total import total
from aerona.db.tables.bonds import BondRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.minds import MindProfileRow
from aerona.db.tables.powers import MagicSystemLinkRow, MagicSystemRow, PowerRestrictionRow, PowerRow, PowerSourceRow
from aerona.domain.enums.arcana import SpellForm, SpellTechnique
from aerona.domain.enums.bond import BondKind, BondState
from aerona.domain.enums.entity import EntityType
from aerona.domain.enums.fortune import FortuneSourceKind
from aerona.domain.enums.made import EffectTarget
from aerona.domain.enums.mind import Attribute
from aerona.domain.enums.minds import MindSeat
from aerona.domain.enums.polity import LawKind
from aerona.domain.enums.powers import (
    PowerDeviceEffect,
    PowerHazard,
    PowerState,
    PowerVisibility,
    ResistanceKind,
    RestrictionKind,
    SourceLawLevel,
)
from aerona.engine.arcana.resistance import carries_iron, sanctity_at
from aerona.engine.concealment.truths import overt_breach
from aerona.engine.context import TickContext
from aerona.engine.economy.purse import points_of, shift_points
from aerona.engine.fortune.profiles import shift_fortune
from aerona.engine.mind.split import attribute
from aerona.engine.mortal.standing import add_infamy, add_renown
from aerona.engine.notes import note
from aerona.engine.polity.laws import law_param
from aerona.engine.powers import effects
from aerona.engine.powers.devices import devices_of
from aerona.engine.powers.kinds import SEASONS, access_refused, licence_refused, structure_holds, suffer, system_bond
from aerona.engine.powers.sources import draw, drawn_from_land, hazard_of, knows_source, patron_short, polity_of, resistances_of, source_level, tide_factor
from aerona.engine.primitives.augment_bonus import bonus
from aerona.engine.primitives.folk import present_among
from aerona.engine.primitives.numbers import clamp_int, round_half_up
from aerona.engine.primitives.stats import stat_or

WITNESSES = 5
MADE_SEATS = frozenset({MindSeat.OBJECT, MindSeat.NETWORK, MindSeat.STRUCTURE, MindSeat.MEDIUM})
USABLE = frozenset({PowerState.ACTIVE, PowerState.STRAINED, PowerState.EMERGING})
MIND_FORMS = frozenset({"mind", "emotion"})


@dataclass(frozen=True)
class Outcome:
    done: str | None
    misfired: bool
    strained: bool
    resisted: bool
    reason: str | None = None


async def device_factor(ctx: TickContext, user: EntityRow) -> tuple[float, int]:
    share = ctx.rules.powers.device_pct / PERCENT
    found = await devices_of(ctx.session, [user.id])
    strength = 1 + share * found.count(PowerDeviceEffect.AMPLIFY)
    control = round(PERCENT * share) * found.count(PowerDeviceEffect.STABILISE)
    return strength, control


async def dampened(ctx: TickContext, target: EntityRow | None, user: EntityRow) -> float:
    holders = [user.location_id] if user.location_id is not None else []
    if target is not None:
        holders += [target.id] + ([target.location_id] if target.location_id is not None else [])
    found = await devices_of(ctx.session, holders)
    damp = found.count(PowerDeviceEffect.DAMPEN) + found.count(PowerDeviceEffect.SHIELD)
    return max(0.0, 1 - damp * ctx.rules.powers.device_pct / PERCENT)


@dataclass(frozen=True)
class Asked:
    row: PowerRestrictionRow
    power: PowerRow
    user: EntityRow
    target: EntityRow | None


async def on_self(_ctx: TickContext, asked: Asked) -> bool:
    return asked.target is None or asked.target.id == asked.user.id


async def out_of_place(_ctx: TickContext, asked: Asked) -> bool:
    return asked.row.ref_node_id is not None and asked.user.location_id != asked.row.ref_node_id


async def wrong_target(_ctx: TickContext, asked: Asked) -> bool:
    ref, target = asked.row.ref_node_id, asked.target
    return ref is not None and (target is None or ref not in {target.id, target.affiliated_entity_id})


async def out_of_reach(_ctx: TickContext, asked: Asked) -> bool:
    return asked.target is not None and asked.target.location_id != asked.user.location_id


async def unseen(ctx: TickContext, asked: Asked) -> bool:
    return not await witnesses_of(ctx, asked.user)


async def seen(ctx: TickContext, asked: Asked) -> bool:
    return bool(await witnesses_of(ctx, asked.user))


async def out_of_time(ctx: TickContext, asked: Asked) -> bool:
    return not await in_its_time(ctx, asked.power)


async def unpaid(ctx: TickContext, asked: Asked) -> bool:
    if await points_of(ctx.session, asked.user) <= 0:
        return True
    await shift_points(ctx.session, asked.user, -1)
    return False


async def kept(_ctx: TickContext, _asked: Asked) -> bool:
    return False


BLOCKS: Mapping[RestrictionKind, Callable[[TickContext, Asked], Awaitable[bool]]] = total(
    RestrictionKind,
    {
        RestrictionKind.NEVER_ON_SELF: on_self,
        RestrictionKind.ONLY_IN_PLACE: out_of_place,
        RestrictionKind.ONLY_AGAINST: wrong_target,
        RestrictionKind.MUST_TOUCH: out_of_reach,
        RestrictionKind.MUST_BE_SEEN: unseen,
        RestrictionKind.MUST_BE_UNSEEN: seen,
        RestrictionKind.ONLY_AT_TIME: out_of_time,
        RestrictionKind.PRICE_EACH_USE: unpaid,
        RestrictionKind.SPOKEN_VOW: kept,
        RestrictionKind.FORBIDDEN_ACT: kept,
    },
)


async def restriction_factor(ctx: TickContext, power: PowerRow, user: EntityRow, target: EntityRow | None) -> float | None:
    gain = 0
    for row in await ctx.session.scalars(select(PowerRestrictionRow).where(PowerRestrictionRow.power_id == power.id, PowerRestrictionRow.broken.is_(False))):
        if await BLOCKS[row.kind](ctx, Asked(row, power, user, target)):
            return None
        gain += row.strength_gain_pct
    return 1 + min(gain, ctx.rules.powers.restriction_cap_pct) / PERCENT


async def in_its_time(ctx: TickContext, power: PowerRow) -> bool:
    if power.source_id is None:
        return ctx.epoch % SEASONS == 0
    return await tide_factor(ctx, power.source_id) >= 1.0


async def seated_apart(ctx: TickContext, target: EntityRow, power: PowerRow) -> bool:
    mind = await ctx.session.get(MindProfileRow, target.id)
    return power.form.value in MIND_FORMS and mind is not None and mind.seat in MADE_SEATS


async def dampeners(ctx: TickContext, target: EntityRow, _user: EntityRow) -> int:
    return (await devices_of(ctx.session, [target.id])).count(PowerDeviceEffect.DAMPEN) * PERCENT


async def willpower(ctx: TickContext, target: EntityRow, _user: EntityRow) -> int:
    return await attribute(ctx.session, ctx.rules, target, Attribute.WILLPOWER)


async def focus(ctx: TickContext, target: EntityRow, _user: EntityRow) -> int:
    return await attribute(ctx.session, ctx.rules, target, Attribute.FOCUS)


async def piety(_ctx: TickContext, target: EntityRow, _user: EntityRow) -> int:
    return stat_or(target, "piety", 0)


async def sanctity(ctx: TickContext, target: EntityRow, _user: EntityRow) -> int:
    return await sanctity_at(ctx, target)


async def iron(ctx: TickContext, target: EntityRow, _user: EntityRow) -> int:
    return PERCENT if await carries_iron(ctx, target) else 0


async def counter_power(ctx: TickContext, target: EntityRow, _user: EntityRow) -> int:
    counter = await ctx.session.scalar(select(PowerRow.id).where(PowerRow.holder_node_id == target.id, PowerRow.state == PowerState.ACTIVE).limit(1))
    return PERCENT if counter is not None else 0


async def distance(ctx: TickContext, target: EntityRow, user: EntityRow) -> int:
    far = target.location_id != user.location_id
    return PERCENT if far and PowerDeviceEffect.EXTEND_RANGE not in await devices_of(ctx.session, [user.id]) else 0


async def nothing(_ctx: TickContext, _target: EntityRow, _user: EntityRow) -> int:
    return 0


RESISTANCE_READERS: Mapping[str, Callable[[TickContext, EntityRow, EntityRow], Awaitable[int]]] = {
    "devices": dampeners,
    "willpower": willpower,
    "focus": focus,
    "piety": piety,
    "sanctity": sanctity,
    "iron": iron,
    "counter_power": counter_power,
    "distance": distance,
    "nothing": nothing,
}


async def resistance(ctx: TickContext, target: EntityRow | None, kinds: list[ResistanceKind], user: EntityRow) -> float:
    if target is None or target.id == user.id or target.entity_type is not EntityType.MORTAL or kinds == [ResistanceKind.NONE]:
        return 0.0
    total = 0
    for kind in kinds:
        total += await bonus(ctx.session, target.id, EffectTarget.RESISTANCE, kind.value)
        spec = RESISTANCES[kind]
        total += await RESISTANCE_READERS[spec.reads](ctx, target, user) * spec.share_pct // PERCENT
    return min(1.0, total / (PERCENT * 2))


async def system_factor(ctx: TickContext, power: PowerRow, target: EntityRow | None) -> float:
    system = await ctx.session.get(MagicSystemRow, power.system_id) if power.system_id is not None else None
    if system is None:
        return 1.0
    spread = (PERCENT - system.predictability) / PERCENT * ctx.rules.magic_systems.spread_pct / PERCENT
    factor = 1 + (ctx.rng(f"power.spread.{power.id}.{ctx.epoch}").random() * 2 - 1) * spread
    factor *= await structure_holds(ctx, power)
    if target is None:
        return factor
    theirs = set(await ctx.session.scalars(select(PowerRow.system_id).where(PowerRow.holder_node_id == target.id, PowerRow.system_id.is_not(None))))
    links = await ctx.session.scalars(
        select(MagicSystemLinkRow.relation).where(
            ((MagicSystemLinkRow.first_system_id == system.id) & MagicSystemLinkRow.second_system_id.in_(theirs))
            | ((MagicSystemLinkRow.second_system_id == system.id) & MagicSystemLinkRow.first_system_id.in_(theirs)),
        )
    )
    for relation in set(links):
        factor *= await system_bond(ctx, relation)
    return factor


async def linked_strength(ctx: TickContext, user: EntityRow, power: PowerRow) -> float:
    partners = select(BondRow.target_node_id).where(BondRow.source_node_id == user.id, BondRow.kind == BondKind.LINKED_WITH, BondRow.state == BondState.ACTIVE)
    joined = await ctx.session.scalars(
        select(PowerRow.strength).where(PowerRow.holder_node_id.in_(partners), PowerRow.form == power.form, PowerRow.state.in_(list(USABLE)))
    )
    return 1 + sum(joined) * ctx.rules.powers.link_pct / PERCENT / max(1, power.strength)


async def source_refused(ctx: TickContext, user: EntityRow, source: PowerSourceRow) -> str | None:
    refused = await access_refused(ctx, user, source)
    if refused is not None:
        return refused
    polity = await polity_of(ctx.session, user.location_id)
    level = await source_level(ctx.session, user.id, user.location_id, polity, source.id)
    if level is SourceLawLevel.BANNED:
        return f"drawing on {source.name} is banned here"
    return await licence_refused(ctx, user, polity) if level is SourceLawLevel.LICENSED else None


async def allowed(ctx: TickContext, user: EntityRow, power: PowerRow, source: PowerSourceRow | None) -> str | None:
    if power.state not in USABLE:
        return "the power is not awake"
    if source is not None and not await knows_source(ctx.session, [user.id, *([user.location_id] if user.location_id is not None else [])], source):
        return f"no one here knows how to draw on {source.name}"
    town = user.location_id
    if source is not None and (refused := await source_refused(ctx, user, source)) is not None:
        return refused
    if source is not None and (short := await patron_short(ctx, user, source.id, power.strength)) is not None:
        return short
    if power.form.value in MIND_FORMS and town is not None and str(await law_param(ctx.session, town, LawKind.POWER_LAW, "mind_powers")) == "banned":
        return "powers over minds are banned here"
    return None


async def strain(ctx: TickContext, user: EntityRow, power: PowerRow, strength: int) -> bool:
    table = ctx.rules.powers
    if "strain" not in power.locked:
        power.strain += strength * table.strain_per_use + power.range_km // 100 * table.range_strain
    over = power.strain * PERCENT >= power.strain_cap * table.harm_at_pct
    if over:
        await effects.scar(ctx, user, table.scar_hp)
        if "state" not in power.locked:
            power.state = PowerState.STRAINED
    if power.strain * PERCENT >= power.strain_cap * table.burnout_at_pct and "state" not in power.locked:
        power.state = PowerState.EXHAUSTED
        await note(ctx, f"The power of {user.name} gave out.", key="power.exhausted", ids=[user.id])
    return over


async def witnesses_of(ctx: TickContext, user: EntityRow) -> list[int]:
    if user.location_id is None:
        return []
    rows = await ctx.session.scalars(
        select(EntityRow.id)
        .where(await present_among(ctx.session, [user.location_id]), EntityRow.entity_type == EntityType.MORTAL, EntityRow.id != user.id)
        .order_by(EntityRow.id)
        .limit(WITNESSES)
    )
    return list(rows)


async def use(ctx: TickContext, power: PowerRow, user: EntityRow, target: EntityRow | None) -> Outcome:
    table = ctx.rules.powers
    source = await ctx.session.get(PowerSourceRow, power.source_id) if power.source_id is not None else None
    refused = await allowed(ctx, user, power, source)
    if refused is not None:
        return Outcome(None, False, False, False, refused)
    restricted = await restriction_factor(ctx, power, user, target)
    if restricted is None:
        return Outcome(None, False, False, False, "its restrictions forbid this use")
    rng = ctx.rng(f"power.use.{power.id}.{ctx.epoch}.{target.id if target is not None else 0}")
    amplified, steadied = await device_factor(ctx, user)
    control = clamp_int(power.control + steadied, 0, PERCENT)
    misfired = control < table.misfire_below and rng.chance(table.misfire_chance)
    aimed = user if misfired and target is not None else target
    drawn = await draw(ctx, user, source, power.strength) if source is not None else 1.0
    factor = drawn * restricted * amplified * await linked_strength(ctx, user, power) * await system_factor(ctx, power, aimed)
    factor *= await dampened(ctx, aimed, user)
    resisted = await resistance(ctx, aimed, await resistances_of(ctx.session, source.id) if source is not None else [ResistanceKind.WILL], user)
    if aimed is not None and await seated_apart(ctx, aimed, power):
        resisted = 1.0
    magnitude = round_half_up(power.strength * PERCENT / 10 * factor * (1 - resisted))
    if misfired:
        magnitude = round_half_up(magnitude * (1 + (PERCENT - control) / PERCENT))
    effect = effects.effect_for(power.technique, power.form, on_self=aimed is None or aimed.id == user.id)
    act = effects.Act(user, aimed, magnitude, power.id, table.span_epochs)
    done = await effects.apply(ctx, effect, act, power.form) if magnitude > 0 else None
    over = await strain(ctx, user, power, power.strength)
    if over and done is not None and rng.chance(table.growth_chance) and "strength" not in power.locked:
        power.strength = min(10, power.strength + 1)
    hazard = await hazard_of(ctx, user, source) if source is not None else None
    if hazard is not None and await suffer(ctx, user, power, hazard) == PowerHazard.DEPLETION.value and source is not None:
        await drawn_from_land(ctx, user, source, power.strength)
    if done is not None and power.form is SpellForm.FATE:
        await shift_fortune(
            ctx, (aimed or user).id, magnitude // 4 if power.technique is not SpellTechnique.DESTROY else -magnitude // 4, FortuneSourceKind.FATE_POWER, user.id
        )
    power.uses += 1
    power.last_used_epoch = ctx.epoch
    if done is not None and power.visibility is not PowerVisibility.HIDDEN:
        await overt_breach(ctx, user, power.visibility is PowerVisibility.OVERT, await witnesses_of(ctx, user))
    if done is not None and power.visibility is PowerVisibility.OVERT and not misfired and user.entity_type is EntityType.MORTAL:
        await add_renown(ctx.session, user.id, ctx.rules.powered_society.renown_per_use, ctx.epoch, rules=ctx.rules)
        if effect is effects.E.DAMAGE:
            await add_infamy(ctx.session, user.id, ctx.rules.powered_society.infamy_per_harm, ctx.epoch, rules=ctx.rules)
    return Outcome(done, misfired, over, resisted >= 1.0)
