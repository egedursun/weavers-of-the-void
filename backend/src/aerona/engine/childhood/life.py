from dataclasses import dataclass

from sqlalchemy import select

from aerona.catalog.life.childhood import HARSH, SOCIABLE, THEORY_SPEED, YOUNG_ONES_LIFE_STAGES
from aerona.catalog.life_traits import LIFE_STAGE_TRAITS, having
from aerona.constants.units import PERCENT
from aerona.db.tables.childhood import InfantCareRow, PedagogyRow, SocializationRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.mortal import MortalProfileRow
from aerona.db.tables.structures import StructureProfileRow
from aerona.db.write_guard import held
from aerona.domain.enums.childhood import CarryWay, InfantCarer, InfantFeeding, SleepArrangement
from aerona.domain.enums.entity import EntityStatus, EntityType
from aerona.domain.enums.life_traits import LifeStageTrait
from aerona.domain.enums.mind import ValueAxis, ValueHolder
from aerona.domain.enums.modifier import IncidentRole
from aerona.domain.enums.mortal import DeathCause, LifeStage
from aerona.domain.enums.structure import StructureKind
from aerona.domain.models.calendar import epoch_end_year, epoch_start_year
from aerona.domain.models.moment import Moment
from aerona.engine.body.customs import people_of
from aerona.engine.childhood.standing import age_of, crossed, standing_of
from aerona.engine.context import TickContext
from aerona.engine.lifecycle.mortal_death import die
from aerona.engine.mind.book import stored_values, write_values
from aerona.engine.primitives.numbers import clamp_int, round_half_up
from aerona.engine.primitives.stats import shift_stat
from aerona.engine.recording.births import birth_year
from aerona.engine.recording.record import record
from aerona.engine.recording.terms import explaining, term

TEN = 10
GROWING = having(LIFE_STAGE_TRAITS, LifeStageTrait.YOUNG)
FEEDING_STEPS = {
    InfantFeeding.NONE_NEEDED: 2,
    InfantFeeding.MADE_FOOD: 1,
    InfantFeeding.BY_BIRTH_PARENT: 0,
    InfantFeeding.BY_OTHER_NURSE: 0,
    InfantFeeding.ANIMAL_MILK: -1,
    InfantFeeding.PREPARED_FOOD: -1,
}
CARER_STEPS = {InfantCarer.SPECIALIST: 1, InfantCarer.MADE_MIND: 1, InfantCarer.KIN: 0, InfantCarer.COMMUNITY: 0}
CARRY_STEPS = {CarryWay.CARRIED: 1, CarryWay.CRADLED: 0, CarryWay.LEFT_TENDED: -1}
SLEEP_STEPS = {SleepArrangement.WITH_PARENT: 1, SleepArrangement.WITH_SIBLINGS: 0, SleepArrangement.COMMUNAL: 0, SleepArrangement.APART: -1}
AIM_AXES: tuple[tuple[str, ValueAxis, int], ...] = (
    ("aim_obedience", ValueAxis.HIERARCHY, 1),
    ("aim_obedience", ValueAxis.LOYALTY, 1),
    ("aim_independence", ValueAxis.TRADITION, -1),
    ("aim_aggression", ValueAxis.MARTIAL, 1),
    ("aim_restraint", ValueAxis.LAW, 1),
    ("aim_cooperation", ValueAxis.FRIENDSHIP, 1),
    ("aim_piety", ValueAxis.PIETY, 1),
    ("aim_craft", ValueAxis.CRAFTSMANSHIP, 1),
)
SCHOOLS = frozenset({StructureKind.SCHOOL, StructureKind.ACADEMY, StructureKind.UNIVERSITY})


@dataclass
class ChildhoodTally:
    infants_lost: int = 0
    weaned: int = 0
    named: int = 0
    workers: int = 0
    shaped: int = 0
    schooled: int = 0


async def young_ones(ctx: TickContext) -> list[tuple[EntityRow, MortalProfileRow]]:
    rows = await ctx.session.execute(
        select(EntityRow, MortalProfileRow)
        .join(MortalProfileRow, MortalProfileRow.entity_id == EntityRow.id)
        .where(
            EntityRow.entity_type == EntityType.MORTAL,
            EntityRow.status == EntityStatus.CANON,
            MortalProfileRow.life_stage.in_(YOUNG_ONES_LIFE_STAGES),
        )
        .order_by(EntityRow.id)
    )
    return [(entity, profile) for entity, profile in rows if not held(entity.id)]


def survival_of(ctx: TickContext, care: InfantCareRow | None) -> int:
    table = ctx.rules.childhood
    if care is None:
        return table.infant_survival_pct
    steps = FEEDING_STEPS[care.feeding] + CARER_STEPS[care.carer] + CARRY_STEPS[care.carry] + SLEEP_STEPS[care.sleeping]
    return clamp_int(table.infant_survival_pct + steps * table.feeding_survival_shift, 0, PERCENT)


async def at_age(ctx: TickContext, child: EntityRow, age: int) -> Moment | None:
    born = await birth_year(ctx.session, child.id)
    if born is None:
        return None
    years = ctx.rules.time.years_per_epoch
    start = epoch_start_year(ctx.epoch, years)
    return Moment(min(max(born + age, start, born), epoch_end_year(ctx.epoch, years) - 1))


async def keep_infants(ctx: TickContext, child: EntityRow, folk_id: int | None, tally: ChildhoodTally) -> None:
    care = await ctx.session.get(InfantCareRow, folk_id) if folk_id is not None else None
    survival = survival_of(ctx, care)
    if ctx.rng(f"infant.{child.id}").chance(PERCENT - survival):
        await die(ctx, child, cause="did not live through infancy", manner=DeathCause.DISEASE, natural=True)
        tally.infants_lost += 1
        return
    if care is not None and crossed(child, care.weaning_age, ctx.rules.time.years_per_epoch):
        await record(
            ctx,
            "childhood.weaned",
            roles={IncidentRole.SUBJECT: child.id},
            facts={"feeding": care.feeding, "age": care.weaning_age},
            at_moment=await at_age(ctx, child, care.weaning_age),
        )
        tally.weaned += 1


async def keep_standing(ctx: TickContext, child: EntityRow, profile: MortalProfileRow, tally: ChildhoodTally) -> None:
    standing = await standing_of(ctx.session, child)
    if standing is None:
        return
    span = ctx.rules.time.years_per_epoch
    if crossed(child, standing.naming_age, span):
        await record(
            ctx,
            "childhood.named",
            roles={IncidentRole.SUBJECT: child.id},
            facts={"name": child.name, "age": standing.naming_age},
            at_moment=await at_age(ctx, child, standing.naming_age),
        )
        tally.named += 1
    if profile.life_stage not in GROWING or standing.labour_share <= 0 or age_of(child) < standing.work_age:
        return
    if crossed(child, standing.work_age, span):
        await record(
            ctx,
            "childhood.put_to_work",
            roles={IncidentRole.SUBJECT: child.id},
            facts={"age": standing.work_age},
            at_moment=await at_age(ctx, child, standing.work_age),
        )
    table = ctx.rules.childhood
    loss = round_half_up(table.labour_schooling_loss_pct * standing.labour_share / (PERCENT * TEN))
    if loss and "education" not in (profile.locked or []):
        with explaining():
            term("childhood.labour_schooling_loss_pct", -loss)
            profile.education = clamp_int(profile.education - loss, 0, PERCENT)
    town = await ctx.session.get(EntityRow, child.location_id) if child.location_id is not None else None
    if town is not None and town.entity_type is EntityType.SETTLEMENT and not held(town.id):
        with explaining():
            term("childhood.labour_output", table.labour_output / TEN, source_node_id=child.id)
            shift_stat(town, "prosperity", table.labour_output / TEN, low=0, high=PERCENT)
    tally.workers += 1


async def shape(ctx: TickContext, child: EntityRow, profile: MortalProfileRow, folk_id: int | None, tally: ChildhoodTally) -> None:
    upbringing = await ctx.session.get(SocializationRow, folk_id) if folk_id is not None else None
    if upbringing is None or profile.life_stage not in GROWING:
        return
    table = ctx.rules.childhood
    values = dict(await stored_values(ctx.session, ValueHolder.PERSONAL, child.id))
    for aim, axis, sign in AIM_AXES:
        target = sign * (getattr(upbringing, aim) * 2 - PERCENT)
        current = values.get(axis, 0)
        values[axis] = current + max(-table.socialize_step, min(table.socialize_step, target - current))
    harsh = sum(getattr(upbringing, technique.value) for technique in HARSH)
    sociable = sum(getattr(upbringing, technique.value) for technique in SOCIABLE)
    values[ValueAxis.TRADITION] = values.get(ValueAxis.TRADITION, 0) + round_half_up(harsh * table.socialize_step / PERCENT)
    values[ValueAxis.FRIENDSHIP] = values.get(ValueAxis.FRIENDSHIP, 0) + round_half_up(sociable * table.play_cooperation_pct / (PERCENT * TEN))
    with explaining():
        term("childhood.socialize_step", table.socialize_step, source_node_id=folk_id)
        await write_values(ctx.session, ValueHolder.PERSONAL, child.id, values)
    strain = round_half_up(harsh * table.harsh_stress_pct / (PERCENT * TEN))
    if strain and "stress" not in (profile.locked or []):
        with explaining():
            term("childhood.harsh_stress_pct", strain, source_node_id=folk_id)
            profile.stress = clamp_int(profile.stress + strain, 0, PERCENT)
    tally.shaped += 1


async def teacher_of(ctx: TickContext, child: EntityRow, folk_id: int | None) -> PedagogyRow | None:
    if child.location_id is not None:
        schools = select(StructureProfileRow.structure_entity_id).where(
            StructureProfileRow.host_entity_id == child.location_id, StructureProfileRow.kind.in_(sorted(SCHOOLS))
        )
        found = await ctx.session.scalar(select(PedagogyRow).where(PedagogyRow.holder_node_id.in_(schools)).order_by(PedagogyRow.id).limit(1))
        if found is not None:
            return found
    if folk_id is None:
        return None
    return await ctx.session.scalar(select(PedagogyRow).where(PedagogyRow.holder_node_id == folk_id).order_by(PedagogyRow.id).limit(1))


async def school(ctx: TickContext, child: EntityRow, profile: MortalProfileRow, folk_id: int | None, tally: ChildhoodTally) -> None:
    if profile.life_stage not in GROWING or "education" in (profile.locked or []):
        return
    pedagogy = await teacher_of(ctx, child, folk_id)
    if pedagogy is None:
        return
    gain = round_half_up(ctx.rules.childhood.pedagogy_speed_pct * THEORY_SPEED[pedagogy.theory] / (PERCENT * TEN))
    if not gain:
        return
    first = profile.education == 0
    with explaining():
        term("childhood.pedagogy_speed_pct", gain, source_node_id=pedagogy.holder_node_id)
        profile.education = clamp_int(profile.education + gain, 0, PERCENT)
    if first:
        await record(
            ctx,
            "childhood.school_entered",
            roles={IncidentRole.SUBJECT: child.id, **({IncidentRole.TEACHER: pedagogy.founder_node_id} if pedagogy.founder_node_id is not None else {})},
            facts={"theory": pedagogy.theory},
            place=child.location_id,
        )
    tally.schooled += 1


async def keep_childhood(ctx: TickContext) -> ChildhoodTally:
    tally = ChildhoodTally()
    for child, profile in await young_ones(ctx):
        folk = await people_of(ctx.session, child)
        folk_id = folk.id if folk is not None else None
        if profile.life_stage is LifeStage.INFANT:
            await keep_infants(ctx, child, folk_id, tally)
            if child.status is not EntityStatus.CANON:
                continue
        await keep_standing(ctx, child, profile, tally)
        await shape(ctx, child, profile, folk_id, tally)
        await school(ctx, child, profile, folk_id, tally)
    await ctx.session.flush()
    return tally
