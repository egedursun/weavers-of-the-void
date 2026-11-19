from collections import defaultdict

from sqlalchemy import func, select

from aerona.constants.units import PERCENT
from aerona.db.tables.bonds import BondRow
from aerona.db.tables.cosmography import PhenomenonFootprintRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.minds import MindProfileRow
from aerona.db.tables.mortal import MortalProfileRow
from aerona.db.tables.powers import PowerRow, PowerSpanRow, PowerTriggerRow, SourceDensityRow
from aerona.db.write_guard import held
from aerona.domain.enums.arcana import SpellForm, SpellTechnique
from aerona.domain.enums.bond import BondKind, BondState
from aerona.domain.enums.constructs import MindWill
from aerona.domain.enums.culture import RiteEffectKind
from aerona.domain.enums.entity import EntityStatus, EntityType
from aerona.domain.enums.minds import MindOrigin, MindSeat
from aerona.domain.enums.modifier import IncidentRole
from aerona.domain.enums.mortal import LifeStage
from aerona.domain.enums.powers import PowerDeviceEffect, PowerOrigin, PowerState, PowerTrigger, PowerVisibility
from aerona.domain.enums.records import InstrumentKind, StepAction, StepOutcome
from aerona.domain.enums.society import CreatureTrait
from aerona.engine.body.book import species_of, species_traits
from aerona.engine.context import TickContext
from aerona.engine.interconnect.annotations import reads, writes
from aerona.engine.minds.profiles import profile_of
from aerona.engine.powers.backfill import keep_power_kinds, legacy_backfill
from aerona.engine.powers.devices import devices_of
from aerona.engine.powers.kinds import triggered
from aerona.engine.powers.sources import keep_density, keep_knowledge
from aerona.engine.powers.use import Outcome, use
from aerona.engine.primitives.distance import RegionAtlas
from aerona.engine.primitives.folk import present_among
from aerona.engine.primitives.numbers import clamp_int, clamp_percent
from aerona.engine.primitives.stats import set_stats, stat_or
from aerona.engine.recording.record import StepDraft, record

E = RiteEffectKind
QUIET = frozenset({PowerState.LATENT, PowerState.EXHAUSTED, PowerState.SUPPRESSED, PowerState.LOST})
GROWN = frozenset({LifeStage.ADULT, LifeStage.ELDER, LifeStage.ANCIENT})


async def grown(ctx: TickContext, holder: EntityRow) -> bool:
    profile = await ctx.session.get(MortalProfileRow, holder.id)
    return profile is None or profile.life_stage in GROWN


async def trigger_present(ctx: TickContext, power: PowerRow, holder: EntityRow) -> bool:
    triggers = set(await ctx.session.scalars(select(PowerTriggerRow.trigger).where(PowerTriggerRow.power_id == power.id)))
    if not triggers:
        triggers = {PowerTrigger.STRESS}
    profile = await ctx.session.get(MortalProfileRow, holder.id)
    stress = profile.stress if profile is not None else 0
    if PowerTrigger.STRESS in triggers and stress >= PERCENT // 2:
        return True
    if PowerTrigger.DANGER in triggers and stat_or(holder, "hp", PERCENT) < PERCENT // 3:
        return True
    if await triggered(ctx, holder, triggers):
        return True
    if PowerTrigger.PLACE in triggers and holder.location_id is not None:
        dense = await ctx.session.scalar(
            select(SourceDensityRow.id).where(SourceDensityRow.region_entity_id == holder.location_id, SourceDensityRow.density >= PERCENT * 3 // 4).limit(1)
        )
        return dense is not None
    if PowerTrigger.CONTACT in triggers:
        near = select(EntityRow.id).where(EntityRow.location_id == holder.location_id, EntityRow.id != holder.id)
        other = await ctx.session.scalar(select(PowerRow.id).where(PowerRow.holder_node_id.in_(near), PowerRow.state == PowerState.ACTIVE).limit(1))
        return other is not None
    return PowerTrigger.TIME in triggers and await grown(ctx, holder)


async def awaken(ctx: TickContext, power: PowerRow, holder: EntityRow) -> None:
    table = ctx.rules.powers
    woken = PowerDeviceEffect.AWAKEN in await devices_of(ctx.session, [holder.id])
    present = woken or await trigger_present(ctx, power, holder)
    if power.state is PowerState.LATENT and present and ctx.rng(f"power.emerge.{power.id}.{ctx.epoch}").chance(table.emerge_chance * (2 if woken else 1)):
        power.state = PowerState.EMERGING
        await record(ctx, "power.emerged", roles={IncidentRole.OWNER: holder.id})
        return
    if power.state is not PowerState.EMERGING:
        return
    rng = ctx.rng(f"power.wild.{power.id}.{ctx.epoch}")
    if power.control < table.misfire_below and rng.chance(table.wild_chance):
        near = await ctx.session.scalar(
            select(EntityRow)
            .where(await present_among(ctx.session, [holder.location_id]), EntityRow.id != holder.id, EntityRow.entity_type == EntityType.MORTAL)
            .limit(1)
        )
        outcome = await use(ctx, power, holder, near)
        if outcome.done is not None:
            await record(ctx, "power.wild", roles={IncidentRole.OWNER: holder.id}, facts={"done": outcome.done})
            ctx.count("wild_manifestations")
    if rng.chance(table.settle_chance):
        power.state = PowerState.ACTIVE


async def recover(ctx: TickContext, power: PowerRow) -> None:
    table = ctx.rules.powers
    if "strain" not in power.locked and power.last_used_epoch != ctx.epoch:
        power.strain = max(0, power.strain - table.rest_recovery)
    if power.state is PowerState.STRAINED and power.strain < power.strain_cap:
        power.state = PowerState.ACTIVE
    if power.state is PowerState.EXHAUSTED and ctx.rng(f"power.return.{power.id}.{ctx.epoch}").chance(table.burnout_recovery_chance):
        power.state, power.strain = PowerState.ACTIVE, 0


async def fade(ctx: TickContext, power: PowerRow, holder: EntityRow) -> None:
    span = stat_or(holder, "lifespan", 0)
    if not span or power.origin in {PowerOrigin.MADE, PowerOrigin.GROWN, PowerOrigin.HELD}:
        return
    if stat_or(holder, "age", 0) * PERCENT >= span * ctx.rules.powers.fade_age_pct and "strength" not in power.locked and power.strength > 1:
        power.strength -= 1


async def live_with(ctx: TickContext, power: PowerRow, holder: EntityRow) -> None:
    if power.state is not PowerState.ACTIVE or not ctx.rng(f"power.life.{power.id}.{ctx.epoch}").chance(ctx.rules.powers.use_chance):
        return
    target = None
    if power.on_others:
        target = await ctx.session.scalar(
            select(EntityRow)
            .where(EntityRow.location_id == holder.location_id, EntityRow.id != holder.id, EntityRow.status == EntityStatus.CANON)
            .order_by(EntityRow.id)
            .limit(1)
        )
    outcome = await use(ctx, power, holder, target)
    if outcome.done is not None:
        ctx.count("powers_used")
        if power.visibility is PowerVisibility.OVERT:
            await record(
                ctx,
                "power.used",
                roles={IncidentRole.OWNER: holder.id, IncidentRole.TARGET: target.id if target is not None else None},
                facts={"done": outcome.done},
                steps=power_steps(power, holder, target, outcome),
            )


def power_steps(power: PowerRow, holder: EntityRow, target: EntityRow | None, outcome: Outcome) -> tuple[StepDraft, ...]:
    used = StepDraft(
        StepAction.USE_POWER,
        actor=holder.id,
        target=target.id if target is not None else None,
        instrument_kind=InstrumentKind.POWER,
        instrument_key=power.technique.value,
        record_table=PowerRow.__tablename__,
        record_key=str(power.id),
        outcome=StepOutcome.FAILURE if outcome.resisted else StepOutcome.SUCCESS,
    )
    if not outcome.misfired:
        return (used,)
    return (
        used,
        StepDraft(StepAction.BACKLASH, actor=holder.id, target=holder.id, instrument_kind=InstrumentKind.POWER, instrument_key=power.form.value, parent=0),
    )


async def end_span(ctx: TickContext, row: PowerSpanRow) -> None:
    target_id = row.target_node_id or row.user_node_id
    if row.effect is E.POSSESS:
        mine = await ctx.session.get(MindProfileRow, row.user_node_id)
        theirs = await ctx.session.get(MindProfileRow, target_id)
        if mine is not None and "seat" not in mine.locked and mine.seat is MindSeat.HOST:
            mine.seat, mine.seat_node_id = MindSeat.BODY, row.user_node_id
        if theirs is not None and "dormant" not in theirs.locked:
            theirs.dormant = bool(row.prior)
    elif row.effect is E.PROJECT_SELF:
        mind = await ctx.session.get(MindProfileRow, row.user_node_id)
        if mind is not None and "dormant" not in mind.locked:
            mind.dormant = bool(row.prior)
    elif row.effect is E.NULLIFY:
        for power in await ctx.session.scalars(select(PowerRow).where(PowerRow.holder_node_id == target_id, PowerRow.state == PowerState.SUPPRESSED)):
            if "state" not in power.locked:
                power.state = PowerState.ACTIVE
    elif row.effect in {E.HASTEN, E.SLOW}:
        mind = await ctx.session.get(MindProfileRow, target_id)
        if mind is not None and "speed_pct" not in mind.locked:
            mind.speed_pct = row.prior
    elif row.effect is E.CHANGE_FORM:
        user = await ctx.session.get(EntityRow, row.user_node_id)
        if user is not None and not held(user.id):
            set_stats(user, might=row.prior)
    await ctx.session.delete(row)


async def end_spans(ctx: TickContext) -> int:
    ended = 0
    for row in list(await ctx.session.scalars(select(PowerSpanRow).where(PowerSpanRow.until_epoch <= ctx.epoch).order_by(PowerSpanRow.id))):
        if row.locked or held(row.user_node_id) or (row.target_node_id is not None and held(row.target_node_id)):
            continue
        await end_span(ctx, row)
        ended += 1
    return ended


async def exposed(ctx: TickContext) -> int:
    table = ctx.rules.powers
    atlas = await RegionAtlas.load(ctx.session)
    marked = set(await ctx.session.scalars(select(PhenomenonFootprintRow.region_entity_id)))
    marked |= set(await ctx.session.scalars(select(SourceDensityRow.region_entity_id).where(SourceDensityRow.density >= PERCENT * 9 // 10)))
    if not marked:
        return 0
    gained = 0
    powered = select(PowerRow.holder_node_id)
    mortals = await ctx.session.scalars(
        select(EntityRow)
        .where(EntityRow.entity_type == EntityType.MORTAL, EntityRow.status == EntityStatus.CANON, EntityRow.id.not_in(powered))
        .order_by(EntityRow.id)
    )
    for mortal in list(mortals):
        if held(mortal.id) or atlas.top_region(mortal.id) not in marked:
            continue
        rng = ctx.rng(f"power.exposure.{mortal.id}.{ctx.epoch}")
        if not rng.chance(table.exposure_chance):
            continue
        ctx.session.add(
            PowerRow(
                holder_node_id=mortal.id,
                technique=rng.pick(list(SpellTechnique)),
                form=rng.pick(list(SpellForm)),
                strength=1 + rng.die(3),
                control=rng.die(40),
                origin=PowerOrigin.EXPOSURE,
                state=PowerState.LATENT,
                visibility=PowerVisibility.SUBTLE,
                strain=0,
                strain_cap=30,
                uses=0,
                gained_epoch=ctx.epoch,
                locked=[],
            )
        )
        gained += 1
    return gained


async def gestalts(ctx: TickContext) -> int:
    table = ctx.rules.powers
    links: dict[int, set[int]] = defaultdict(set)
    rows = await ctx.session.execute(
        select(BondRow.source_node_id, BondRow.target_node_id).where(BondRow.kind == BondKind.LINKED_WITH, BondRow.state == BondState.ACTIVE)
    )
    for first, second in rows.all():
        links[first].add(second)
        links[second].add(first)
    formed = 0
    seen: set[int] = set()
    for start in sorted(links):
        if start in seen:
            continue
        group, frontier = {start}, [start]
        while frontier:
            for other in links[frontier.pop()]:
                if other not in group:
                    group.add(other)
                    frontier.append(other)
        seen |= group
        powered = await ctx.session.scalar(select(func.count(func.distinct(PowerRow.holder_node_id))).where(PowerRow.holder_node_id.in_(group)))
        if int(powered or 0) < table.gestalt_members or any(held(member) for member in group):
            continue
        anchor = min(group)
        mind = await profile_of(ctx.session, ctx.rules, anchor, ctx.epoch)
        if mind.seat is MindSeat.BODIES or "seat" in mind.locked:
            continue
        mind.seat, mind.seat_node_id, mind.origin = MindSeat.BODIES, anchor, MindOrigin.MERGED
        mind.capacity = clamp_percent(mind.capacity + len(group) * 2)
        mind.will = MindWill.FULL
        await record(ctx, "power.gestalt", roles={IncidentRole.SUBJECT: [*sorted(group)]})
        formed += 1
    return formed


async def hive_minds(ctx: TickContext) -> int:
    formed = 0
    peoples = await ctx.session.scalars(
        select(EntityRow).where(EntityRow.entity_type == EntityType.PEOPLE, EntityRow.status == EntityStatus.CANON).order_by(EntityRow.id)
    )
    for people in list(peoples):
        if held(people.id) or await ctx.session.get(MindProfileRow, people.id) is not None:
            continue
        species = await species_of(ctx.session, people)
        if species is None or CreatureTrait.HIVE_MIND not in await species_traits(ctx.session, species.id):
            continue
        mind = await profile_of(ctx.session, ctx.rules, people.id, ctx.epoch)
        mind.seat, mind.seat_node_id, mind.origin, mind.will = MindSeat.BODIES, people.id, MindOrigin.BORN, MindWill.FULL
        await record(ctx, "power.hive_mind", roles={IncidentRole.SUBJECT: people.id}, facts={"people": people.name})
        formed += 1
    return formed


async def train(ctx: TickContext, power: PowerRow) -> None:
    if power.origin is not PowerOrigin.DISCIPLINE or power.state not in {PowerState.ACTIVE, PowerState.LATENT}:
        return
    if "control" not in power.locked:
        power.control = clamp_int(power.control + ctx.rules.powers.control_gain, 0, PERCENT)
    gain = ctx.rules.powers.discipline_gain
    if "strength" not in power.locked and ctx.rng(f"power.discipline.{power.id}.{ctx.epoch}").chance(gain * 10):
        power.strength = min(10, power.strength + 1)
    if power.state is PowerState.LATENT:
        power.state = PowerState.ACTIVE


@reads(
    "mortal.age",
    "mortal.lifespan",
    "table.bonds",
    "table.creator",
    "table.dimensions",
    "table.entities",
    "table.entity_traits",
    "table.equipment_models",
    "table.equipment_stores",
    "table.foreign_gods",
    "table.galaxies",
    "table.galaxy_clusters",
    "table.genomes",
    "table.hidden_truths",
    "table.ley_lines",
    "table.magic_system_links",
    "table.magic_systems",
    "table.memories",
    "table.mind_profiles",
    "table.mortal_profiles",
    "table.node_births",
    "table.nodes",
    "table.phenomenon_footprints",
    "table.power_restrictions",
    "table.power_source_costs",
    "table.power_source_hazards",
    "table.power_source_interactions",
    "table.power_source_knowledge",
    "table.power_source_resistances",
    "table.power_sources",
    "table.power_spans",
    "table.power_triggers",
    "table.powers",
    "table.secrets",
    "table.sons",
    "table.source_density",
    "table.source_laws",
    "table.source_tides",
    "table.stars",
    "table.worlds",
)
@writes(
    "table.applied_fixups",
    "table.chronicle",
    "table.chronicle_entities",
    "table.entities",
    "table.incident_participants",
    "table.incidents",
    "table.magic_system_sources",
    "table.magic_systems",
    "table.mind_profiles",
    "table.mortal_profiles",
    "table.power_source_costs",
    "table.power_source_hazards",
    "table.power_source_knowledge",
    "table.power_source_resistances",
    "table.power_sources",
    "table.power_spans",
    "table.powers",
    "table.source_density",
)
async def keep_powers(ctx: TickContext) -> None:
    ctx.count("powers_backfilled", await legacy_backfill(ctx))
    ctx.count("power_kinds_kept", await keep_power_kinds(ctx))
    ctx.count("source_lands_kept", await keep_density(ctx))
    ctx.count("source_knowledge_changed", await keep_knowledge(ctx))
    ctx.count("power_spans_ended", await end_spans(ctx))
    for power in list(await ctx.session.scalars(select(PowerRow).where(PowerRow.state != PowerState.LOST).order_by(PowerRow.id))):
        holder = await ctx.session.get(EntityRow, power.holder_node_id)
        if holder is None or holder.status is not EntityStatus.CANON or held(holder.id):
            continue
        await recover(ctx, power)
        await awaken(ctx, power, holder)
        await train(ctx, power)
        await fade(ctx, power, holder)
        if power.state not in QUIET:
            await live_with(ctx, power, holder)
        ctx.count("powers_kept")
    ctx.count("powers_by_exposure", await exposed(ctx))
    ctx.count("gestalts_formed", await gestalts(ctx))
    ctx.count("hive_minds_formed", await hive_minds(ctx))
    await ctx.session.flush()
