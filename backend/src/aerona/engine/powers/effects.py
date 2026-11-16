from collections.abc import Awaitable, Callable
from dataclasses import dataclass

from sqlalchemy import func, select

from aerona.constants.units import PERCENT
from aerona.db.tables.collective import AccountRow
from aerona.db.tables.constructs import InstructionSetRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.intrigue import SecretRow
from aerona.db.tables.minds import MindProfileRow
from aerona.db.tables.mortal import MortalProfileRow
from aerona.db.tables.powers import PowerRow, PowerSpanRow
from aerona.db.tables.sacred import ForesightRow
from aerona.db.tables.structures import StructureProfileRow
from aerona.db.write_guard import held
from aerona.domain.enums.arcana import SpellForm, SpellTechnique
from aerona.domain.enums.body import DamageType, HarmCause, InjuryKind
from aerona.domain.enums.culture import ProphecyPredicate, RiteEffectKind
from aerona.domain.enums.entity import EntityStatus, EntityType
from aerona.domain.enums.environment import WeatherKind
from aerona.domain.enums.made import Authenticity
from aerona.domain.enums.mind import MemoryKind
from aerona.domain.enums.minds import MindSeat
from aerona.domain.enums.mortal import CrimeKind
from aerona.domain.enums.powers import PowerState
from aerona.domain.enums.sacred import ForesightSource
from aerona.engine.body.healing import mend
from aerona.engine.body.hits import Harm
from aerona.engine.context import TickContext
from aerona.engine.environment.control import force_weather
from aerona.engine.intrigue.secrets import learn
from aerona.engine.lifecycle.wounds import apply_hits
from aerona.engine.lore.intel import gain_intel
from aerona.engine.mind.memories import remember
from aerona.engine.minds.crimes import mind_crime
from aerona.engine.minds.profiles import is_made, profile_of
from aerona.engine.minds.sentences import forced_edit
from aerona.engine.primitives.distance import RegionAtlas
from aerona.engine.primitives.numbers import clamp_int, clamp_percent, round_half_up
from aerona.engine.primitives.stats import set_stats, stat_or
from aerona.engine.sacred.foresight import foresee, likely_futures
from aerona.engine.services.community_relations import change_relation

T = SpellTechnique
F = SpellForm
E = RiteEffectKind

HARM_TYPES = {
    F.FIRE: DamageType.FIRE,
    F.WATER: DamageType.COLD,
    F.AIR: DamageType.BLUNT,
    F.EARTH: DamageType.BLUNT,
    F.FORCE: DamageType.BLUNT,
    F.SOUND: DamageType.BLUNT,
    F.MIND: DamageType.PSYCHIC,
    F.EMOTION: DamageType.PSYCHIC,
    F.LIGHT: DamageType.FIRE,
}
FORM_WEATHER = {F.AIR: WeatherKind.STORM, F.WATER: WeatherKind.RAIN, F.FIRE: WeatherKind.HEAT_WAVE, F.IMAGE: WeatherKind.FOG}


@dataclass(frozen=True)
class Act:
    user: EntityRow
    target: EntityRow | None
    magnitude: int
    power_id: int | None = None
    span: int = 1


def effect_for(technique: SpellTechnique, form: SpellForm, *, on_self: bool) -> RiteEffectKind:
    paired = {
        (T.CONTROL, F.SPACE): E.MOVE_SELF if on_self else E.MOVE_TARGET,
        (T.CONTROL, F.FORCE): E.PUSH,
        (T.TRANSFORM, F.EARTH): E.SHAPE_MATTER,
        (T.TRANSFORM, F.WATER): E.SHAPE_MATTER,
        (T.PERCEIVE, F.INFORMATION): E.READ_RECORD,
        (T.CONTROL, F.MACHINE): E.SEIZE_MACHINE,
        (T.TRANSFORM, F.INFORMATION): E.ALTER_RECORD,
        (T.PERCEIVE, F.EMOTION): E.SENSE_EMOTION,
        (T.CONTROL, F.EMOTION): E.SWAY_EMOTION,
        (T.CONTROL, F.FATE): E.TURN_FORTUNE,
        (T.PERCEIVE, F.SPIRIT): E.PROJECT_SELF,
        (T.CONTROL, F.SPIRIT): E.POSSESS,
        (T.CONTROL, F.MIND): E.SWAY_EMOTION,
        (T.TRANSFORM, F.MIND): E.ALTER_RECORD,
        (T.PERCEIVE, F.MIND): E.SCRY,
        (T.WARD, F.IMAGE): E.CONCEAL,
        (T.WARD, F.MIND): E.CONCEAL,
        (T.CONTROL, F.TIME): E.HASTEN if on_self else E.SLOW,
        (T.TRANSFORM, F.TIME): E.RENEW if on_self else E.AGE,
        (T.PERCEIVE, F.TIME): E.FORESEE,
        (T.TRANSFORM, F.BODY): E.CHANGE_FORM if on_self else E.HEAL,
        (T.CONTROL, F.AIR): E.WEATHER_CHANGE,
        (T.CONTROL, F.WATER): E.WEATHER_CHANGE,
    }
    if (technique, form) in paired:
        return paired[(technique, form)]
    by_technique = {
        T.DRAIN: E.DRAIN_LIFE if form in {F.BODY, F.PLANT, F.ANIMAL} else E.DRAIN_POWER,
        T.MIMIC: E.COPY_POWER,
        T.WARD: E.NULLIFY if form in {F.SPIRIT, F.VOID} else E.WARD,
        T.PERCEIVE: E.SCRY,
    }
    if technique in by_technique:
        return by_technique[technique]
    if technique in {T.CREATE, T.TRANSFORM} and form in {F.BODY, F.PLANT}:
        return E.HEAL
    return E.DAMAGE if technique in {T.DESTROY, T.CONTROL, T.TRANSFORM} else E.BLESS


async def span(ctx: TickContext, act: Act, effect: RiteEffectKind, *, prior: int = 0) -> PowerSpanRow:
    row = PowerSpanRow(
        power_id=act.power_id,
        user_node_id=act.user.id,
        target_node_id=act.target.id if act.target is not None else None,
        effect=effect,
        amount=act.magnitude,
        prior=prior,
        began_epoch=ctx.epoch,
        until_epoch=ctx.epoch + max(1, act.span),
        locked=[],
    )
    ctx.session.add(row)
    return row


def living(target: EntityRow | None) -> EntityRow | None:
    return target if target is not None and target.status is EntityStatus.CANON and not held(target.id) else None


async def harm(ctx: TickContext, act: Act, damage_type: DamageType = DamageType.BLUNT) -> str | None:
    victim = living(act.target)
    if victim is None or victim.entity_type is not EntityType.MORTAL:
        return None
    reason = f"was struck down by the power of {act.user.name}"
    await apply_hits(ctx, victim, Harm(act.magnitude, HarmCause.POWER, reason, damage_type=damage_type, source_node_id=act.user.id, killer_id=act.user.id))
    return f"struck {victim.name}"


async def heal(ctx: TickContext, act: Act) -> str | None:
    patient = living(act.target) or act.user
    mended = await mend(ctx, patient, healer_id=act.user.id)
    return f"mended {patient.name}" if mended else None


async def bless(ctx: TickContext, act: Act) -> str | None:
    target = living(act.target) or act.user
    profile = await ctx.session.get(MortalProfileRow, target.id)
    if profile is None or "stress" in (profile.locked or []):
        return None
    profile.stress = clamp_percent(profile.stress - act.magnitude)
    return f"eased {target.name}"


async def read_mind(ctx: TickContext, act: Act) -> str | None:
    target = living(act.target)
    if target is None:
        return None
    await gain_intel(ctx, act.user.id, target.id, act.magnitude)
    found = 0
    for secret in list(await ctx.session.scalars(select(SecretRow).where(SecretRow.holder_node_id == target.id).order_by(SecretRow.id))):
        if found * PERCENT >= act.magnitude * ctx.rules.powers.secrets_per_strength:
            break
        if act.user.id not in secret.known_by and await learn(ctx, secret, act.user.id):
            found += 1
    return f"read the mind of {target.name}"


async def sway(ctx: TickContext, act: Act) -> str | None:
    target = living(act.target)
    if target is None:
        return None
    profile = await ctx.session.get(MortalProfileRow, target.id)
    if profile is not None and "stress" not in (profile.locked or []):
        profile.stress = clamp_percent(profile.stress + act.magnitude // 2)
    if act.magnitude >= ctx.rules.powers.compulsion_at:
        await remember(
            ctx.session, ctx.rules, holder_id=target.id, subject_id=act.user.id, kind=MemoryKind.COMPELLED_ME, magnitude=-act.magnitude, epoch=ctx.epoch
        )
        await change_relation(ctx, target.id, act.user.id, -act.magnitude, MemoryKind.COMPELLED_ME, note="bent by a power over the mind")
        await mind_crime(ctx, act.user.id, CrimeKind.MIND_COMPULSION)
        return f"compelled {target.name}"
    await change_relation(ctx, target.id, act.user.id, act.magnitude // 2, MemoryKind.GOODWILL, note="swayed by a power")
    return f"swayed {target.name}"


async def sense(ctx: TickContext, act: Act) -> str | None:
    target = living(act.target)
    if target is None:
        return None
    await gain_intel(ctx, act.user.id, target.id, act.magnitude // 2)
    return f"sensed what {target.name} felt"


async def move_target(ctx: TickContext, act: Act) -> str | None:
    target = living(act.target)
    if target is None or target.entity_type not in {EntityType.MORTAL, EntityType.BEAST, EntityType.ITEM} or act.user.location_id is None:
        return None
    target.location_id = act.user.location_id
    return f"brought {target.name} across the distance"


async def move_self(ctx: TickContext, act: Act) -> str | None:
    target = act.target
    if target is None or held(act.user.id):
        return None
    place = target.location_id if target.entity_type in {EntityType.MORTAL, EntityType.ITEM, EntityType.BEAST} else target.id
    if place is None:
        return None
    act.user.location_id = place
    return f"crossed to {target.name} without the road"


async def push(ctx: TickContext, act: Act) -> str | None:
    target = living(act.target)
    if target is not None and target.entity_type is EntityType.STRUCTURE:
        return await shape_matter(ctx, Act(act.user, target, -act.magnitude, act.power_id))
    return await harm(ctx, act)


async def shape_matter(ctx: TickContext, act: Act) -> str | None:
    target = living(act.target)
    work = await ctx.session.get(StructureProfileRow, target.id) if target is not None else None
    if target is None or work is None or "condition" in work.locked:
        return None
    work.condition = clamp_percent(work.condition + act.magnitude)
    return f"reshaped {target.name}"


async def read_record(ctx: TickContext, act: Act) -> str | None:
    target = living(act.target)
    if target is None:
        return None
    await gain_intel(ctx, act.user.id, target.id, act.magnitude)
    return f"read the records of {target.name}"


async def seize_machine(ctx: TickContext, act: Act) -> str | None:
    target = living(act.target)
    orders = await ctx.session.scalar(select(InstructionSetRow).where(InstructionSetRow.owner_entity_id == target.id)) if target is not None else None
    if target is None or orders is None or "holder_node_id" in orders.locked:
        return None
    orders.holder_node_id = act.user.id
    return f"seized {target.name}"


async def alter_record(ctx: TickContext, act: Act) -> str | None:
    target = living(act.target)
    if target is None:
        return None
    mind = await ctx.session.get(MindProfileRow, target.id)
    if mind is not None and is_made(mind) and act.magnitude >= ctx.rules.powers.compulsion_at:
        await forced_edit(ctx, mind)
        await mind_crime(ctx, act.user.id, CrimeKind.FORCED_EDIT)
        return f"edited the mind of {target.name}"
    account = await ctx.session.scalar(select(AccountRow).where(AccountRow.subject_node_id == target.id).order_by(AccountRow.id.desc()).limit(1))
    if account is None or "authenticity" in account.locked:
        return None
    account.authenticity = Authenticity.ALTERED
    return f"altered what was told of {target.name}"


async def turn_fortune(ctx: TickContext, act: Act) -> str | None:
    target = living(act.target) or act.user
    await span(ctx, Act(act.user, target, act.magnitude, act.power_id, act.span), E.TURN_FORTUNE)
    return f"turned fortune for {target.name}"


async def drain_life(ctx: TickContext, act: Act) -> str | None:
    struck = await harm(ctx, act, DamageType.PSYCHIC)
    if struck is None:
        return None
    await mend(ctx, act.user, healer_id=act.user.id)
    return f"drew life from {act.target.name if act.target is not None else 'its prey'}"


async def drain_power(ctx: TickContext, act: Act) -> str | None:
    target = living(act.target)
    if target is None:
        return None
    drained = 0
    for power in list(await ctx.session.scalars(select(PowerRow).where(PowerRow.holder_node_id == target.id))):
        if "strain" not in power.locked:
            power.strain = min(power.strain_cap * 2, power.strain + act.magnitude)
            drained += 1
    for own in list(await ctx.session.scalars(select(PowerRow).where(PowerRow.holder_node_id == act.user.id))):
        if "strain" not in own.locked:
            own.strain = max(0, own.strain - act.magnitude)
    return f"drained the powers of {target.name}" if drained else None


async def copy_power(ctx: TickContext, act: Act) -> str | None:
    target = living(act.target)
    if target is None:
        return None
    source = await ctx.session.scalar(
        select(PowerRow).where(PowerRow.holder_node_id == target.id, PowerRow.state == PowerState.ACTIVE).order_by(PowerRow.strength.desc()).limit(1)
    )
    if source is None:
        return None
    ctx.session.add(
        PowerRow(
            holder_node_id=act.user.id,
            system_id=source.system_id,
            source_id=source.source_id,
            technique=source.technique,
            form=source.form,
            range_km=source.range_km,
            duration_days=source.duration_days,
            on_others=source.on_others,
            strength=max(1, source.strength * ctx.rules.powers.copy_strength_pct // PERCENT),
            control=source.control // 2,
            origin=source.origin,
            state=PowerState.ACTIVE,
            visibility=source.visibility,
            strain=0,
            strain_cap=source.strain_cap,
            uses=0,
            gained_epoch=ctx.epoch,
            locked=[],
        )
    )
    return f"took on the power of {target.name}"


async def project_self(ctx: TickContext, act: Act) -> str | None:
    target = act.target
    if target is None:
        return None
    await gain_intel(ctx, act.user.id, target.id, act.magnitude)
    mind = await profile_of(ctx.session, ctx.rules, act.user.id, ctx.epoch)
    if "dormant" not in mind.locked:
        await span(ctx, act, E.PROJECT_SELF, prior=int(mind.dormant))
        mind.dormant = True
    return f"left its body to look upon {target.name}"


async def possess(ctx: TickContext, act: Act) -> str | None:
    host = living(act.target)
    if host is None or host.entity_type is not EntityType.MORTAL or host.id == act.user.id:
        return None
    mine = await profile_of(ctx.session, ctx.rules, act.user.id, ctx.epoch)
    theirs = await profile_of(ctx.session, ctx.rules, host.id, ctx.epoch)
    if "seat" in mine.locked or "dormant" in theirs.locked:
        return None
    await span(ctx, act, E.POSSESS, prior=int(theirs.dormant))
    mine.seat, mine.seat_node_id = MindSeat.HOST, host.id
    theirs.dormant = True
    await remember(ctx.session, ctx.rules, holder_id=host.id, subject_id=act.user.id, kind=MemoryKind.COMPELLED_ME, magnitude=-act.magnitude, epoch=ctx.epoch)
    await mind_crime(ctx, act.user.id, CrimeKind.MIND_COMPULSION)
    return f"took the body of {host.name}"


async def change_form(ctx: TickContext, act: Act) -> str | None:
    if held(act.user.id):
        return None
    might = stat_or(act.user, "might", 0)
    await span(ctx, act, E.CHANGE_FORM, prior=might)
    set_stats(act.user, might=clamp_int(might + act.magnitude, 0, PERCENT))
    return f"{act.user.name} took another shape"


async def conceal(ctx: TickContext, act: Act) -> str | None:
    target = living(act.target) or act.user
    await span(ctx, Act(act.user, target, act.magnitude, act.power_id, act.span), E.CONCEAL)
    return f"hid {target.name} from sight"


async def nullify(ctx: TickContext, act: Act) -> str | None:
    target = living(act.target)
    if target is None:
        return None
    stilled = 0
    for power in list(await ctx.session.scalars(select(PowerRow).where(PowerRow.holder_node_id == target.id, PowerRow.state == PowerState.ACTIVE))):
        if "state" not in power.locked:
            power.state = PowerState.SUPPRESSED
            stilled += 1
    if not stilled:
        return None
    await span(ctx, act, E.NULLIFY)
    return f"stilled the powers of {target.name}"


async def pace(ctx: TickContext, act: Act, effect: RiteEffectKind) -> str | None:
    target = living(act.target) or act.user
    mind = await profile_of(ctx.session, ctx.rules, target.id, ctx.epoch)
    if "speed_pct" in mind.locked:
        return None
    await span(ctx, Act(act.user, target, act.magnitude, act.power_id, act.span), effect, prior=mind.speed_pct)
    shift = act.magnitude * ctx.rules.powers.pace_per_strength
    mind.speed_pct = clamp_int(mind.speed_pct + (shift if effect is E.HASTEN else -shift), 1, PERCENT * 10)
    return f"{'quickened' if effect is E.HASTEN else 'slowed'} {target.name}"


async def years(ctx: TickContext, act: Act, sign: int) -> str | None:
    target = living(act.target) or act.user
    if target.entity_type is not EntityType.MORTAL:
        return None
    age = stat_or(target, "age", 0)
    set_stats(target, age=max(0, age + sign * round_half_up(act.magnitude * ctx.rules.powers.years_per_strength / PERCENT)))
    return f"{'aged' if sign > 0 else 'renewed'} {target.name}"


async def weather(ctx: TickContext, act: Act, form: SpellForm | None) -> str | None:
    atlas = await RegionAtlas.load(ctx.session)
    region = await ctx.session.get(EntityRow, atlas.top_region(act.target.id if act.target is not None else act.user.id) or 0)
    if region is None or region.entity_type is not EntityType.REGION or held(region.id):
        return None
    kind = FORM_WEATHER.get(form, WeatherKind.RAIN) if form is not None else WeatherKind.RAIN
    await force_weather(ctx.session, region, kind, from_epoch=ctx.epoch, epochs=1, season_position=None)
    return f"called {kind.value.replace('_', ' ')} over {region.name}"


async def future_for(ctx: TickContext, seer: EntityRow, subject: EntityRow | None) -> tuple[ProphecyPredicate, int, int]:
    futures = await likely_futures(ctx, seer.world_id)
    likely = [item for item in futures if item[2] >= ctx.rules.prescience.likely_at]
    if likely:
        return max(likely, key=lambda item: (item[2], -item[1]))
    watched = subject if subject is not None and subject.entity_type is EntityType.MORTAL else seer
    age, span = stat_or(watched, "age", 0), max(1, stat_or(watched, "lifespan", 0))
    return ProphecyPredicate.DIES, watched.id, clamp_int(age * PERCENT // span, 0, PERCENT)


async def seen_ahead(ctx: TickContext, seer: EntityRow, subject: EntityRow | None, sight: int, power_id: int | None) -> ForesightRow | None:
    row = await foresee(ctx, seer.id, ForesightSource.POWER, seer.world_id, sight=sight, chosen=await future_for(ctx, seer, subject))
    if row is None:
        return None
    in_world = select(EntityRow.id).where(EntityRow.world_id == seer.world_id, EntityRow.id != seer.id, EntityRow.status == EntityStatus.CANON)
    rivals = await ctx.session.scalar(
        select(func.count(func.distinct(PowerRow.holder_node_id))).where(
            PowerRow.holder_node_id.in_(in_world), PowerRow.form == SpellForm.TIME, PowerRow.state == PowerState.ACTIVE
        )
    )
    row.certainty = clamp_percent(row.certainty - ctx.rules.powers.foresight_blind * int(rivals or 0))
    row.power_id = power_id
    return row


async def foresight(ctx: TickContext, act: Act) -> str | None:
    row = await seen_ahead(ctx, act.user, act.target, act.magnitude, act.power_id)
    return f"{act.user.name} saw what may come" if row is not None else None


async def scar(ctx: TickContext, user: EntityRow, amount: int) -> None:
    if user.entity_type is not EntityType.MORTAL or held(user.id):
        return
    reason = "was scarred within by a power pushed too far"
    await apply_hits(ctx, user, Harm(amount, HarmCause.POWER, reason, damage_type=DamageType.PSYCHIC, kind=InjuryKind.MIND_SCAR), lethal=False)


HANDLERS: dict[RiteEffectKind, Callable[[TickContext, Act], Awaitable[str | None]]] = {
    E.MOVE_TARGET: move_target,
    E.MOVE_SELF: move_self,
    E.PUSH: push,
    E.SHAPE_MATTER: shape_matter,
    E.READ_RECORD: read_record,
    E.SEIZE_MACHINE: seize_machine,
    E.ALTER_RECORD: alter_record,
    E.SENSE_EMOTION: sense,
    E.SWAY_EMOTION: sway,
    E.TURN_FORTUNE: turn_fortune,
    E.DRAIN_LIFE: drain_life,
    E.DRAIN_POWER: drain_power,
    E.COPY_POWER: copy_power,
    E.PROJECT_SELF: project_self,
    E.POSSESS: possess,
    E.CHANGE_FORM: change_form,
    E.CONCEAL: conceal,
    E.NULLIFY: nullify,
    E.HASTEN: lambda ctx, act: pace(ctx, act, E.HASTEN),
    E.SLOW: lambda ctx, act: pace(ctx, act, E.SLOW),
    E.AGE: lambda ctx, act: years(ctx, act, 1),
    E.RENEW: lambda ctx, act: years(ctx, act, -1),
    E.FORESEE: foresight,
}
POWER_HANDLERS: dict[RiteEffectKind, Callable[[TickContext, Act], Awaitable[str | None]]] = {
    **HANDLERS,
    E.DAMAGE: harm,
    E.HEAL: heal,
    E.BLESS: bless,
    E.SCRY: read_mind,
    E.WARD: conceal,
}


async def apply(ctx: TickContext, effect: RiteEffectKind, act: Act, form: SpellForm | None = None) -> str | None:
    if effect is E.DAMAGE and form is not None:
        return await harm(ctx, act, HARM_TYPES.get(form, DamageType.BLUNT))
    if effect is E.WEATHER_CHANGE:
        return await weather(ctx, act, form)
    handler = POWER_HANDLERS.get(effect)
    return await handler(ctx, act) if handler is not None else None
