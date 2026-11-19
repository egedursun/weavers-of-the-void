from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.catalog.ethics import HONOUR_MODELS, STANCE_ORDER, STANCE_READINGS
from aerona.catalog.mind import ACT_READINGS
from aerona.constants.units import PERCENT
from aerona.db.fast_session import rows_by_prefix
from aerona.db.tables.entities import EntityFlagRow, EntityRow
from aerona.db.tables.mind import CultureEthicRow, CultureHonourRow, MemoryRow, ThoughtRow
from aerona.db.tables.mortal import MortalProfileRow
from aerona.db.tables.warfare import WarRow, WarSideRow
from aerona.db.write_guard import write_blocked
from aerona.domain.enums.bond import BondKind
from aerona.domain.enums.entity import EntityFlag, EntityStatus, EntityType
from aerona.domain.enums.faction import FactionKind
from aerona.domain.enums.mind import ActKind, EthicalStance, HonourModel, MemoryKind, PressureKind, ThoughtKind, ValueAxis, ValueHolder
from aerona.domain.enums.modifier import IncidentRole
from aerona.domain.enums.mortal import DeathCause
from aerona.domain.enums.war import WarStatus
from aerona.engine.body.customs import people_of
from aerona.engine.context import TickContext
from aerona.engine.lifecycle.aging import is_notable
from aerona.engine.lore.taboos import guest_of
from aerona.engine.mind.book import Values, is_locked, mind_of, pressures_of, stored_values, write_values
from aerona.engine.mind.memories import remember
from aerona.engine.mind.space import value_reading
from aerona.engine.mind.thoughts import think
from aerona.engine.mortal.kin import close_kin_of
from aerona.engine.mortal.profile import is_held
from aerona.engine.mortal.standing import add_infamy, add_renown, add_stress, add_wealth
from aerona.engine.primitives.numbers import clamp_int
from aerona.engine.primitives.queries import active_bonds, living_entity
from aerona.engine.recording.record import record as record_incident
from aerona.rules.registry import Rules

ETHICS_LOCK = "ethics"
ETHICS_KEY = "ethics"
STANCE_FIELD = "stance"
MODEL_FIELD = "model"
ACTIVE_WAR_STATUSES = (WarStatus.MOBILIZING, WarStatus.ONGOING)
WAR_ACTS = frozenset({ActKind.KILLING_IN_WAR, ActKind.KILLING_OUTSIDER, ActKind.TAKING_CAPTIVES, ActKind.RAIDING, ActKind.CONQUEST})
FAMINE_ACTS = frozenset({ActKind.THEFT, ActKind.HOARDING_IN_FAMINE})
SHAME_KINDS = frozenset({ThoughtKind.WAS_SHAMED, ThoughtKind.WAS_INSULTED, ThoughtKind.DEFEATED, ThoughtKind.WAS_PUNISHED, ThoughtKind.LOST_DUEL})
GOOD = frozenset({EthicalStance.REQUIRED, EthicalStance.ADMIRABLE})
BAD = frozenset({EthicalStance.SHAMEFUL, EthicalStance.UNTHINKABLE})
CULTURE_TYPES = frozenset({EntityType.PEOPLE, EntityType.CULT})


async def at_war(session: AsyncSession, sides: list[int]) -> bool:
    found = await session.scalar(
        select(WarSideRow.war_id)
        .join(WarRow, WarRow.id == WarSideRow.war_id)
        .where(WarSideRow.entity_id.in_(sides), WarRow.status.in_(ACTIVE_WAR_STATUSES))
        .limit(1)
    )
    return found is not None


def stance_for(rules: Rules, reading: float) -> EthicalStance:
    table = rules.ethics
    if reading >= table.required_above:
        return EthicalStance.REQUIRED
    if reading >= table.admirable_above:
        return EthicalStance.ADMIRABLE
    if reading <= table.unthinkable_below:
        return EthicalStance.UNTHINKABLE
    if reading <= table.shameful_below:
        return EthicalStance.SHAMEFUL
    if reading <= table.frowned_below:
        return EthicalStance.FROWNED_UPON
    return EthicalStance.ACCEPTABLE


async def ethics_of(session: AsyncSession, holder_id: int | None) -> dict[ActKind, CultureEthicRow]:
    if holder_id is None:
        return {}
    return {row.act: row for row in await rows_by_prefix(session, CultureEthicRow, holder_id)}


async def culture_of(session: AsyncSession, node_id: int | None) -> EntityRow | None:
    node = await session.get(EntityRow, node_id) if node_id is not None else None
    if node is None:
        return None
    if node.entity_type in CULTURE_TYPES:
        return node
    return await people_of(session, node)


async def write_stance(session: AsyncSession, holder_id: int, act: ActKind, stance: EthicalStance, epoch: int) -> CultureEthicRow | None:
    if write_blocked(holder_id, ETHICS_KEY):
        return None
    row = await session.get(CultureEthicRow, (holder_id, act))
    if row is None:
        row = CultureEthicRow(holder_entity_id=holder_id, act=act, stance=stance, since_epoch=epoch, locked=[])
        session.add(row)
    elif STANCE_FIELD not in (row.locked or []) and row.stance is not stance:
        row.stance, row.since_epoch = stance, epoch
    await session.flush()
    return row


def holder_kind(entity: EntityRow) -> ValueHolder:
    return ValueHolder.DOCTRINE if entity.entity_type is EntityType.CULT else ValueHolder.CULTURE


async def church_of(session: AsyncSession, people: EntityRow) -> list[int]:
    gods = [bond.target_node_id for bond in await active_bonds(session, [BondKind.WORSHIPS], sources=[people.id])]
    if not gods:
        return []
    found: list[int] = []
    for bond in await active_bonds(session, [BondKind.WORSHIPS], targets=gods):
        cult = await session.get(EntityRow, bond.source_node_id)
        if cult is not None and cult.entity_type is EntityType.CULT and cult.status is EntityStatus.CANON:
            found.append(cult.id)
    return found


async def church_ethics(session: AsyncSession, culture: EntityRow) -> list[dict[ActKind, CultureEthicRow]]:
    if culture.entity_type is not EntityType.PEOPLE:
        return []
    return [await ethics_of(session, cult) for cult in await church_of(session, culture)]


def target_reading(rules: Rules, act: ActKind, values: Values, church: list[dict[ActKind, CultureEthicRow]]) -> float:
    reading: float = value_reading(values, act)
    stances = [row.stance for ethics in church if (row := ethics.get(act)) is not None]
    if stances:
        cult_reading = sum(STANCE_READINGS[stance] for stance in stances) / len(stances)
        reading += (cult_reading - reading) * rules.ethics.cult_pull_pct / PERCENT
    return reading


async def seed_ethics(ctx: TickContext, culture: EntityRow) -> int:
    if await ethics_of(ctx.session, culture.id):
        return 0
    values = await stored_values(ctx.session, holder_kind(culture), culture.id)
    if not values:
        return 0
    if write_blocked(culture.id, ETHICS_KEY):
        return 0
    ctx.session.add_all(
        CultureEthicRow(holder_entity_id=culture.id, act=act, stance=stance_for(ctx.rules, value_reading(values, act)), since_epoch=ctx.epoch, locked=[])
        for act in ActKind
    )
    await ctx.session.flush()
    return len(ActKind)


async def drift_ethics(ctx: TickContext, culture: EntityRow) -> int:
    if is_locked(await mind_of(ctx.session, culture.id), ETHICS_LOCK) or ctx.epoch % ctx.rules.ethics.drift_epochs:
        return 0
    values = await stored_values(ctx.session, holder_kind(culture), culture.id)
    if not values:
        return 0
    moved = 0
    held = await ethics_of(ctx.session, culture.id)
    church = await church_ethics(ctx.session, culture)
    for act in ActKind:
        if act not in held:
            await write_stance(ctx.session, culture.id, act, stance_for(ctx.rules, target_reading(ctx.rules, act, values, church)), ctx.epoch)
            moved += 1
    for act, row in held.items():
        if STANCE_FIELD in (row.locked or []):
            continue
        wanted = stance_for(ctx.rules, target_reading(ctx.rules, act, values, church))
        here, there = STANCE_ORDER.index(row.stance), STANCE_ORDER.index(wanted)
        if here == there:
            continue
        row.stance = STANCE_ORDER[here + (1 if there > here else -1)]
        row.since_epoch = ctx.epoch
        moved += 1
    await ctx.session.flush()
    return moved


async def ethic_reading(
    session: AsyncSession, rules: Rules, holder_id: int, act: ActKind, values: Values, *, actor_id: int | None = None, victim_id: int | None = None
) -> int:
    culture = await culture_of(session, holder_id)
    row = (await ethics_of(session, culture.id)).get(act) if culture is not None else None
    reading: float = STANCE_READINGS[row.stance] if row is not None else value_reading(values, act)
    if reading >= 0:
        return round(reading)
    table = rules.ethics
    holder = await session.get(EntityRow, holder_id)
    if act in WAR_ACTS and holder is not None and await at_war(session, [holder.id, *([holder.location_id] if holder.location_id is not None else [])]):
        reading = reading * PERCENT / table.war_pct
    if act in FAMINE_ACTS and (await pressures_of(session, holder_id)).get(PressureKind.HUNGER, 0) >= rules.needs.famine_aid_hunger:
        reading = reading * table.famine_pct / PERCENT
    if actor_id is not None and victim_id is not None and victim_id in await close_kin_of(session, actor_id):
        reading = reading * table.kin_pct / PERCENT
    return clamp_int(reading, -PERCENT, PERCENT)


async def shift_conviction(ctx: TickContext, actor_id: int, amount: int, act: ActKind) -> None:
    profile = await ctx.session.get(MortalProfileRow, actor_id)
    if profile is None or is_held(profile, "conviction"):
        return
    profile.conviction = clamp_int(profile.conviction + amount, 0, PERCENT)
    if amount >= 0 or profile.conviction > ctx.rules.aspirations.flip_below:
        return
    values = await stored_values(ctx.session, ValueHolder.PERSONAL, actor_id)
    if not values or is_locked(await mind_of(ctx.session, actor_id), "values"):
        return
    shift = ctx.rules.aspirations.flip_shift
    for axis, weight in ACT_READINGS[act].items():
        values[axis] = clamp_int(values.get(axis, 0) + shift * (1 if weight > 0 else -1), -PERCENT, PERCENT)
    await write_values(ctx.session, ValueHolder.PERSONAL, actor_id, values)
    profile.conviction = PERCENT // 2
    await think(ctx.session, ctx.rules, actor_id, ThoughtKind.DISILLUSIONED, ctx.epoch)
    await record_incident(ctx, "mind.disillusioned", roles={IncidentRole.SUBJECT: actor_id}, facts={"act": act})


async def conscience(ctx: TickContext, actor_id: int, act: ActKind, victim_id: int | None) -> EthicalStance | None:
    actor = await living_entity(ctx.session, actor_id)
    if actor is None or actor.entity_type is not EntityType.MORTAL:
        return None
    culture = await culture_of(ctx.session, actor.id)
    row = (await ethics_of(ctx.session, culture.id)).get(act) if culture is not None else None
    if row is None:
        return None
    table = ctx.rules.ethics
    if row.stance in GOOD:
        await shift_conviction(ctx, actor.id, ctx.rules.aspirations.conviction_gain, act)
        await add_renown(ctx.session, actor.id, table.renown_gain, ctx.epoch, rules=ctx.rules)
        await think(ctx.session, ctx.rules, actor.id, ThoughtKind.ACTED_ON_CONSCIENCE, ctx.epoch, subject_id=victim_id)
    elif row.stance in BAD:
        await shift_conviction(ctx, actor.id, -ctx.rules.aspirations.conviction_loss, act)
        await add_infamy(ctx.session, actor.id, table.infamy_gain, ctx.epoch, rules=ctx.rules)
        await add_stress(ctx.session, actor.id, table.guilt_stress * await guilt_scale(ctx.session, culture.id if culture else None) / PERCENT, ctx.epoch)
        await think(ctx.session, ctx.rules, actor.id, ThoughtKind.ACTED_AGAINST_CONSCIENCE, ctx.epoch, subject_id=victim_id)
        profile = await ctx.session.get(MortalProfileRow, actor.id)
        if profile is not None and profile.legitimacy is not None and not is_held(profile, "legitimacy"):
            profile.legitimacy = clamp_int(profile.legitimacy - table.legitimacy_loss, 0, PERCENT)
    return row.stance


async def honour_of(session: AsyncSession, culture_id: int | None) -> HonourModel:
    row = await session.get(CultureHonourRow, culture_id) if culture_id is not None else None
    return row.model if row is not None else HonourModel.DIGNITY


async def guilt_scale(session: AsyncSession, culture_id: int | None) -> int:
    return HONOUR_MODELS[await honour_of(session, culture_id)].guilt_pct


def model_for(values: Values) -> HonourModel:
    honour, hierarchy, law = values.get(ValueAxis.HONOUR, 0), values.get(ValueAxis.HIERARCHY, 0), values.get(ValueAxis.LAW, 0)
    if honour >= max(law, hierarchy) and honour > 0:
        return HonourModel.HONOUR
    if hierarchy > law and hierarchy > 0:
        return HonourModel.FACE
    return HonourModel.NONE if max(honour, hierarchy, law) < 0 else HonourModel.DIGNITY


async def seed_honour(ctx: TickContext, culture: EntityRow) -> bool:
    if culture.entity_type is not EntityType.PEOPLE or await ctx.session.get(CultureHonourRow, culture.id) is not None:
        return False
    values = await stored_values(ctx.session, ValueHolder.CULTURE, culture.id)
    if not values:
        return False
    ctx.session.add(CultureHonourRow(entity_id=culture.id, model=model_for(values), locked=[]))
    await ctx.session.flush()
    return True


async def spread_shame(ctx: TickContext, mortal: EntityRow) -> int:
    culture = await culture_of(ctx.session, mortal.id)
    spec = HONOUR_MODELS[await honour_of(ctx.session, culture.id if culture else None)]
    if not spec.shame_spread_pct:
        return 0
    shamed = list(
        await ctx.session.scalars(
            select(ThoughtRow).where(ThoughtRow.holder_node_id == mortal.id, ThoughtRow.epoch == ctx.epoch, ThoughtRow.kind.in_(list(SHAME_KINDS)))
        )
    )
    spread = 0
    for row in shamed:
        for kin in await close_kin_of(ctx.session, mortal.id):
            size = row.intensity * spec.shame_spread_pct / PERCENT
            if await think(ctx.session, ctx.rules, kin, ThoughtKind.KIN_SHAMED, ctx.epoch, subject_id=row.subject_node_id, intensity=size):
                spread += 1
            if row.subject_node_id is not None and row.subject_node_id != kin:
                await remember(
                    ctx.session,
                    ctx.rules,
                    holder_id=kin,
                    subject_id=row.subject_node_id,
                    kind=MemoryKind.HUMILIATED_ME,
                    magnitude=-size,
                    epoch=ctx.epoch,
                    note="a shame to the household",
                )
    return spread


async def restore(ctx: TickContext, mortal: EntityRow) -> int:
    culture = await culture_of(ctx.session, mortal.id)
    model = await honour_of(ctx.session, culture.id if culture else None)
    if not HONOUR_MODELS[model].restores:
        return 0
    table = ctx.rules.ethics
    grievances = list(
        await ctx.session.scalars(
            select(MemoryRow).where(MemoryRow.holder_node_id == mortal.id, MemoryRow.kind == MemoryKind.HUMILIATED_ME, MemoryRow.magnitude < 0)
        )
    )
    restored = 0
    for memory in grievances:
        offender = await living_entity(ctx.session, memory.subject_node_id)
        if offender is None or offender.entity_type is not EntityType.MORTAL:
            continue
        if not ctx.rng(f"restore.{memory.id}.{ctx.epoch}").chance(table.restoration_pct):
            continue
        await add_wealth(ctx.session, offender.id, -table.compensation_wealth, ctx.epoch)
        await add_wealth(ctx.session, mortal.id, table.compensation_wealth, ctx.epoch)
        memory.magnitude = memory.magnitude * HONOUR_MODELS[model].grievance_kept_pct // PERCENT
        await think(ctx.session, ctx.rules, mortal.id, ThoughtKind.SHAME_RESTORED, ctx.epoch, subject_id=offender.id)
        restored += 1
    await ctx.session.flush()
    return restored


async def belongs(session: AsyncSession, mortal: EntityRow, people_id: int) -> bool:
    found = await people_of(session, mortal)
    return found is not None and found.id == people_id


@dataclass
class SchismCall:
    act: ActKind
    dissent: int
    notables: int


async def schism(ctx: TickContext, people: EntityRow) -> SchismCall | None:
    table = ctx.rules.ethics
    mortals = list(
        await ctx.session.scalars(
            select(EntityRow).where(EntityRow.entity_type == EntityType.MORTAL, EntityRow.status == EntityStatus.CANON, EntityRow.world_id == people.world_id)
        )
    )
    flags: dict[int, set[EntityFlag]] = {mortal.id: set() for mortal in mortals}
    for holder_id, flag in await ctx.session.execute(select(EntityFlagRow.entity_id, EntityFlagRow.flag).where(EntityFlagRow.entity_id.in_(list(flags)))):
        flags[holder_id].add(flag)
    members = [mortal for mortal in mortals if is_notable(ctx.rules, mortal, flags[mortal.id]) and await belongs(ctx.session, mortal, people.id)]
    if len(members) < table.schism_min:
        return None
    ethics = await ethics_of(ctx.session, people.id)
    for act, row in ethics.items():
        if row.stance not in GOOD | BAD:
            continue
        opposite = BAD if row.stance in GOOD else GOOD
        dissent = 0
        for member in members:
            values = await stored_values(ctx.session, ValueHolder.PERSONAL, member.id)
            if values and stance_for(ctx.rules, value_reading(values, act)) in opposite:
                dissent += 1
        if dissent * PERCENT >= len(members) * table.schism_share_pct:
            return SchismCall(act, dissent, len(members))
    return None


SCHISM_FACTION = FactionKind.SECRET_SOCIETY


async def killing_act(session: AsyncSession, victim: EntityRow, killer_id: int | None, manner: DeathCause | None) -> ActKind | None:
    if killer_id is None:
        return ActKind.SUICIDE if manner is DeathCause.DESPAIR else None
    if killer_id == victim.id or manner in {DeathCause.EXECUTION, DeathCause.SACRIFICE}:
        return None
    grudge = await session.scalar(
        select(MemoryRow.id)
        .where(MemoryRow.holder_node_id == killer_id, MemoryRow.subject_node_id == victim.id, MemoryRow.kind == MemoryKind.KILLED_KIN)
        .limit(1)
    )
    checks = (
        (killer_id in await close_kin_of(session, victim.id), ActKind.KILLING_KIN),
        (await guest_of(session, victim), ActKind.GUEST_KILLING),
        (bool(await active_bonds(session, [BondKind.RULES], sources=[victim.id])), ActKind.REGICIDE),
        (manner is DeathCause.DUEL, ActKind.DUEL_TO_DEATH),
        (manner is DeathCause.BATTLE, ActKind.KILLING_IN_WAR),
        (bool(await active_bonds(session, [BondKind.HOLDS_CAPTIVE], targets=[victim.id])), ActKind.KILLING_CAPTIVE),
        (grudge is not None, ActKind.REVENGE_KILLING),
    )
    return next((act for hit, act in checks if hit), ActKind.KILLING_OUTSIDER)
