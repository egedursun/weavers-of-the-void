from dataclasses import dataclass

from sqlalchemy import select

from aerona.constants.units import PERCENT
from aerona.db.tables.bonds import BondRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.minds import MindProfileRow
from aerona.db.tables.powers import MagicSystemLinkRow, MagicSystemRow, PowerRestrictionRow, PowerRow, PowerSourceRow
from aerona.domain.enums.bond import BondKind, BondState
from aerona.domain.enums.entity import EntityType
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
    SystemRelation,
)
from aerona.engine.arcana.resistance import carries_iron, sanctity_at
from aerona.engine.concealment.truths import overt_breach
from aerona.engine.context import TickContext
from aerona.engine.mind.split import attribute
from aerona.engine.mortal.standing import add_infamy, add_renown
from aerona.engine.notes import note
from aerona.engine.polity.laws import law_param
from aerona.engine.powers import effects
from aerona.engine.powers.devices import devices_of
from aerona.engine.powers.sources import draw, hazard_of, knows_source, polity_of, resistances_of, source_level
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


async def restriction_factor(ctx: TickContext, power: PowerRow, user: EntityRow, target: EntityRow | None) -> float | None:
    gain = 0
    for row in await ctx.session.scalars(select(PowerRestrictionRow).where(PowerRestrictionRow.power_id == power.id, PowerRestrictionRow.broken.is_(False))):
        if row.kind is RestrictionKind.NEVER_ON_SELF and (target is None or target.id == user.id):
            return None
        if row.kind is RestrictionKind.ONLY_IN_PLACE and row.ref_node_id is not None and user.location_id != row.ref_node_id:
            return None
        if (
            row.kind is RestrictionKind.ONLY_AGAINST
            and row.ref_node_id is not None
            and (target is None or row.ref_node_id not in {target.id, target.affiliated_entity_id})
        ):
            return None
        if row.kind is RestrictionKind.MUST_TOUCH and target is not None and target.location_id != user.location_id:
            return None
        gain += row.strength_gain_pct
    return 1 + min(gain, ctx.rules.powers.restriction_cap_pct) / PERCENT


async def seated_apart(ctx: TickContext, target: EntityRow, power: PowerRow) -> bool:
    mind = await ctx.session.get(MindProfileRow, target.id)
    return power.form.value in MIND_FORMS and mind is not None and mind.seat in MADE_SEATS


async def resistance(ctx: TickContext, target: EntityRow | None, kinds: list[ResistanceKind], user: EntityRow) -> float:
    if target is None or target.id == user.id or target.entity_type is not EntityType.MORTAL:
        return 0.0
    total = 0
    if ResistanceKind.WILL in kinds:
        total += await attribute(ctx.session, ctx.rules, target, Attribute.WILLPOWER) // 2
    if ResistanceKind.DISCIPLINE in kinds:
        total += await attribute(ctx.session, ctx.rules, target, Attribute.FOCUS) // 2
    if ResistanceKind.FAITH in kinds:
        total += stat_or(target, "piety", 0) // 2
    if ResistanceKind.SANCTITY in kinds:
        total += await sanctity_at(ctx, target) // 2
    if ResistanceKind.MATERIAL in kinds and await carries_iron(ctx, target):
        total += PERCENT // 4
    if ResistanceKind.COUNTER_SOURCE in kinds:
        counter = await ctx.session.scalar(select(PowerRow.id).where(PowerRow.holder_node_id == target.id, PowerRow.state == PowerState.ACTIVE).limit(1))
        total += PERCENT // 4 if counter is not None else 0
    if (
        ResistanceKind.DISTANCE in kinds
        and target.location_id != user.location_id
        and PowerDeviceEffect.EXTEND_RANGE not in await devices_of(ctx.session, [user.id])
    ):
        total += PERCENT // 4
    return min(1.0, total / (PERCENT * 2))


async def system_factor(ctx: TickContext, power: PowerRow, target: EntityRow | None) -> float:
    system = await ctx.session.get(MagicSystemRow, power.system_id) if power.system_id is not None else None
    if system is None:
        return 1.0
    spread = (PERCENT - system.predictability) / PERCENT * ctx.rules.magic_systems.spread_pct / PERCENT
    factor = 1 + (ctx.rng(f"power.spread.{power.id}.{ctx.epoch}").random() * 2 - 1) * spread
    if target is None:
        return factor
    theirs = set(await ctx.session.scalars(select(PowerRow.system_id).where(PowerRow.holder_node_id == target.id, PowerRow.system_id.is_not(None))))
    opposed = await ctx.session.scalar(
        select(MagicSystemLinkRow.id).where(
            MagicSystemLinkRow.relation == SystemRelation.OPPOSES,
            ((MagicSystemLinkRow.first_system_id == system.id) & MagicSystemLinkRow.second_system_id.in_(theirs))
            | ((MagicSystemLinkRow.second_system_id == system.id) & MagicSystemLinkRow.first_system_id.in_(theirs)),
        )
    )
    return factor * (1 - ctx.rules.magic_systems.oppose_pct / PERCENT) if opposed is not None else factor


async def linked_strength(ctx: TickContext, user: EntityRow, power: PowerRow) -> float:
    partners = select(BondRow.target_node_id).where(BondRow.source_node_id == user.id, BondRow.kind == BondKind.LINKED_WITH, BondRow.state == BondState.ACTIVE)
    joined = await ctx.session.scalars(
        select(PowerRow.strength).where(PowerRow.holder_node_id.in_(partners), PowerRow.form == power.form, PowerRow.state.in_(list(USABLE)))
    )
    return 1 + sum(joined) * ctx.rules.powers.link_pct / PERCENT / max(1, power.strength)


async def allowed(ctx: TickContext, user: EntityRow, power: PowerRow, source: PowerSourceRow | None) -> str | None:
    if power.state not in USABLE:
        return "the power is not awake"
    if source is not None and not await knows_source(ctx.session, [user.id, *([user.location_id] if user.location_id is not None else [])], source):
        return f"no one here knows how to draw on {source.name}"
    town = user.location_id
    polity = await polity_of(ctx.session, town)
    if source is not None and await source_level(ctx.session, user.id, town, polity, source.id) is SourceLawLevel.BANNED:
        return f"drawing on {source.name} is banned here"
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
        power.state = PowerState.BURNED_OUT
        await note(ctx, f"The power of {user.name} gave out.", key="power.burned_out", ids=[user.id])
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
    if source is not None and await hazard_of(ctx, user, source) is PowerHazard.INJURY:
        await effects.scar(ctx, user, table.scar_hp)
    power.uses += 1
    power.last_used_epoch = ctx.epoch
    if done is not None and power.visibility is not PowerVisibility.HIDDEN:
        await overt_breach(ctx, user, power.visibility is PowerVisibility.OVERT, await witnesses_of(ctx, user))
    if done is not None and power.visibility is PowerVisibility.OVERT and not misfired and user.entity_type is EntityType.MORTAL:
        await add_renown(ctx.session, user.id, ctx.rules.powered_society.renown_per_use, ctx.epoch, rules=ctx.rules)
        if effect is effects.E.DAMAGE:
            await add_infamy(ctx.session, user.id, ctx.rules.powered_society.infamy_per_harm, ctx.epoch, rules=ctx.rules)
    return Outcome(done, misfired, over, resisted >= 1.0)
