from sqlalchemy.ext.asyncio import AsyncSession

from aerona.catalog.intimacy_shapes import POSTNATAL_RECOVERY_PCT
from aerona.catalog.life.intimacy import SINGLE_COMPLICATIONS
from aerona.constants.units import PERCENT
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.intimacy import ReproductiveCourseRow
from aerona.db.tables.mortal import MortalProfileRow
from aerona.domain.enums.intimacy import BirthAttendant, BirthComplication, BirthPlace, CycleCustom, PostnatalCustom
from aerona.domain.enums.modifier import IncidentRole
from aerona.engine.body.customs import people_of
from aerona.engine.context import TickContext
from aerona.engine.primitives.numbers import clamp_int, round_half_up
from aerona.engine.recording.record import RoleValue, record
from aerona.engine.recording.terms import explaining, term

USUAL_RISK = 50
YEAR_MONTHS = 12
ATTENDANT_SHARE = {
    BirthAttendant.SPECIALIST: 1.0,
    BirthAttendant.HEALER: 1.0,
    BirthAttendant.MADE_MIND: 1.0,
    BirthAttendant.KIN: 0.5,
    BirthAttendant.NONE: 0.0,
}
PLACE_RISK = {
    BirthPlace.BIRTH_HOUSE: 0.8,
    BirthPlace.SACRED_SITE: 0.9,
    BirthPlace.HOME: 1.0,
    BirthPlace.ANYWHERE: 1.0,
    BirthPlace.APART: 1.2,
}
CYCLE_RISK = {CycleCustom.PURITY_RULES: 0.9, CycleCustom.SECLUSION: 0.95, CycleCustom.NONE: 1.0}


async def course_of(session: AsyncSession, bearer: EntityRow) -> ReproductiveCourseRow | None:
    folk = await people_of(session, bearer)
    return await session.get(ReproductiveCourseRow, folk.id) if folk is not None else None


def complication_risk(ctx: TickContext, course: ReproductiveCourseRow | None, health: int, attended: bool) -> float:
    table = ctx.rules.unions_and_birth
    risk = table.complication_base_pct * (1 + (PERCENT - health) / PERCENT)
    share = 1.0 if attended else 0.0
    if course is not None:
        risk *= course.risk / USUAL_RISK * PLACE_RISK[course.birth_place] * CYCLE_RISK[course.cycle_custom]
        share = max(share, ATTENDANT_SHARE[course.attendant])
    return min(float(PERCENT), risk * (1 - share * table.attendant_care_pct / PERCENT))


def complication_kind(ctx: TickContext, course: ReproductiveCourseRow | None, born: list[EntityRow], seed: str) -> BirthComplication:
    if len(born) > 1:
        return BirthComplication.MULTIPLE
    if course is not None and course.chief_complication is not BirthComplication.NONE:
        return course.chief_complication
    return ctx.rng(seed).pick(SINGLE_COMPLICATIONS)


async def birth_course(ctx: TickContext, bearer: EntityRow, born: list[EntityRow], attendant_id: int | None) -> None:
    profile = await ctx.session.get(MortalProfileRow, bearer.id)
    if profile is None or not born:
        return
    table = ctx.rules.unions_and_birth
    course = await course_of(ctx.session, bearer)
    risk = complication_risk(ctx, course, profile.health, attendant_id is not None)
    roles: dict[IncidentRole, RoleValue] = {
        IncidentRole.PATIENT: bearer.id,
        IncidentRole.CHILD: [child.id for child in born],
        IncidentRole.HEALER: attendant_id,
    }
    if ctx.rng(f"birth_course.{bearer.id}.{ctx.epoch}").chance(risk):
        kind = complication_kind(ctx, course, born, f"birth_complication.{bearer.id}.{ctx.epoch}")
        if "health" not in (profile.locked or []):
            with explaining():
                term("unions_and_birth.complication_harm", -table.complication_harm, source_node_id=bearer.id)
                profile.health = clamp_int(profile.health - table.complication_harm, 0, PERCENT)
        await record(ctx, "birth.complication", roles=roles, facts={"complication": kind, "risk": round_half_up(risk)}, place=bearer.location_id)
        ctx.count("birth_complications")
    if course is None or course.postnatal is PostnatalCustom.NONE or "health" in (profile.locked or []):
        return
    regained = max(
        1,
        round_half_up(table.recovery_health * min(max(course.rest_months, 1), YEAR_MONTHS) / YEAR_MONTHS * POSTNATAL_RECOVERY_PCT[course.postnatal] / PERCENT),
    )
    with explaining():
        term("unions_and_birth.recovery_health", regained, source_node_id=bearer.id)
        profile.health = clamp_int(profile.health + regained, 0, PERCENT)
    await record(
        ctx,
        "birth.recovered",
        roles={IncidentRole.PATIENT: bearer.id},
        facts={"postnatal": course.postnatal, "rest_months": course.rest_months},
        place=bearer.location_id,
    )
