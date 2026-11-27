from collections.abc import Mapping

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.catalog.death_causes import DEATH_CAUSES, LOOSE_CAUSES, death_cause_of
from aerona.constants.units import PERCENT
from aerona.db.fixups import fixup_due
from aerona.db.tables.body import InjuryRow
from aerona.db.tables.cosmos import AppliedFixupRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.mortal import DeathReadingRow, MortalProfileRow
from aerona.db.write_guard import held
from aerona.domain.enums.body import InjuryState
from aerona.domain.enums.entity import EntityStatus, EntityType
from aerona.domain.enums.mind import ValueAxis, ValueHolder
from aerona.domain.enums.mortal import DeathCause, DeathReading
from aerona.engine.body.customs import people_id_of
from aerona.engine.context import TickContext
from aerona.engine.mind.book import stored_values
from aerona.rules.registry import Rules

READINGS_FIXUP = "death_readings.w52"
QUIET_LEAN = 2


def reading_score(rules: Rules, values: Mapping[ValueAxis, int], cause: DeathCause) -> int:
    table = rules.death_readings
    spec = DEATH_CAUSES[cause]
    score = 0.0
    if spec.combat:
        score += values.get(ValueAxis.MARTIAL, 0) * table.martial_glory_pct / PERCENT * QUIET_LEAN
    if spec.offered:
        score += values.get(ValueAxis.PIETY, 0) * table.piety_offering_pct / PERCENT * QUIET_LEAN
    if spec.judged or spec.own_hand:
        score -= values.get(ValueAxis.HONOUR, 0) * table.honour_shame_pct / PERCENT * QUIET_LEAN
    if spec.uncanny:
        score -= values.get(ValueAxis.SUPERSTITION, 0) * table.dread_curse_pct / PERCENT * QUIET_LEAN
    if spec.natural or not (spec.combat or spec.offered or spec.judged or spec.own_hand or spec.uncanny):
        score += values.get(ValueAxis.DEATH, 0) * table.death_rest_pct / PERCENT
    return round(score)


def reading_of_score(rules: Rules, score: int, cause: DeathCause) -> DeathReading:
    table = rules.death_readings
    if score >= table.glorious_at:
        return DeathReading.GLORIOUS
    if score >= table.honourable_at:
        return DeathReading.HONOURABLE
    if score <= -table.cursed_at:
        return DeathReading.CURSED if DEATH_CAUSES[cause].uncanny or DEATH_CAUSES[cause].own_hand else DeathReading.SHAMEFUL
    if score <= -table.shameful_at:
        return DeathReading.SHAMEFUL
    return DeathReading.PLAIN


def derive_reading(rules: Rules, values: Mapping[ValueAxis, int], cause: DeathCause) -> DeathReading:
    reading = reading_of_score(rules, reading_score(rules, values, cause), cause)
    spec = DEATH_CAUSES[cause]
    harmless = not (spec.violent or spec.combat or spec.judged or spec.offered or spec.own_hand or spec.natural)
    if reading is DeathReading.PLAIN and harmless and values.get(ValueAxis.MERCY, 0) >= rules.death_readings.pity_mercy:
        return DeathReading.PITIED
    return reading


async def seed_people(ctx: TickContext, people_id: int) -> int:
    if held(people_id):
        return 0
    known = set(await ctx.session.scalars(select(DeathReadingRow.cause).where(DeathReadingRow.people_entity_id == people_id)))
    values = await stored_values(ctx.session, ValueHolder.CULTURE, people_id)
    made = 0
    for cause in DeathCause:
        if cause in known:
            continue
        ctx.session.add(DeathReadingRow(people_entity_id=people_id, cause=cause, reading=derive_reading(ctx.rules, values, cause), authored=False, locked=[]))
        made += 1
    return made


async def keep_readings(ctx: TickContext) -> int:
    peoples = await ctx.session.scalars(
        select(EntityRow.id).where(EntityRow.entity_type == EntityType.PEOPLE, EntityRow.status == EntityStatus.CANON).order_by(EntityRow.id)
    )
    made = 0
    for people_id in list(peoples):
        made += await seed_people(ctx, people_id)
        for row in await ctx.session.scalars(select(DeathReadingRow).where(DeathReadingRow.people_entity_id == people_id).order_by(DeathReadingRow.cause)):
            if row.authored or "reading" in row.locked:
                continue
            row.reading = derive_reading(ctx.rules, await stored_values(ctx.session, ValueHolder.CULTURE, people_id), row.cause)
    if await fixup_due(ctx.session, READINGS_FIXUP):
        ctx.session.add(AppliedFixupRow(key=READINGS_FIXUP, result={"readings": made}))
    await ctx.session.flush()
    return made


async def reading_for(session: AsyncSession, rules: Rules, mortal: EntityRow, cause: DeathCause) -> DeathReading:
    people_id = await people_id_of(session, mortal)
    if people_id is None:
        return DeathReading.PLAIN
    row = await session.get(DeathReadingRow, (people_id, cause))
    if row is not None:
        return row.reading
    return derive_reading(rules, await stored_values(session, ValueHolder.CULTURE, people_id), cause)


DROWNINGS_FIXUP = "death.w52"


async def last_wound(session: AsyncSession, mortal_id: int) -> InjuryRow | None:
    found: InjuryRow | None = await session.scalar(
        select(InjuryRow).where(InjuryRow.bearer_node_id == mortal_id, InjuryRow.state == InjuryState.LETHAL).order_by(InjuryRow.id.desc()).limit(1)
    )
    return found


def wound_cause(row: InjuryRow) -> DeathCause:
    return death_cause_of(row.cause_kind, row.damage_type)


async def mismatched_deaths(session: AsyncSession) -> list[int]:
    found: list[int] = []
    for profile in await session.scalars(
        select(MortalProfileRow).where(MortalProfileRow.cause_of_death.in_(sorted(LOOSE_CAUSES))).order_by(MortalProfileRow.entity_id)
    ):
        wound = await last_wound(session, profile.entity_id)
        if wound is not None and wound_cause(wound) is not profile.cause_of_death and DEATH_CAUSES[wound_cause(wound)].damage is not None:
            found.append(profile.entity_id)
    return found


async def mend_death_cause(session: AsyncSession, key: int) -> None:
    profile = await session.get(MortalProfileRow, key)
    wound = await last_wound(session, key)
    if profile is not None and wound is not None and "cause_of_death" not in (profile.locked or []):
        profile.cause_of_death = wound_cause(wound)


async def backfill_drownings(session: AsyncSession) -> int:
    if not await fixup_due(session, DROWNINGS_FIXUP):
        return 0
    moved = 0
    for key in await mismatched_deaths(session):
        if not held(key):
            await mend_death_cause(session, key)
            moved += 1
    session.add(AppliedFixupRow(key=DROWNINGS_FIXUP, result={"deaths": moved}))
    await session.flush()
    return moved
