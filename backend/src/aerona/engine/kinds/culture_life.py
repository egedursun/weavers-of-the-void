from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.constants.units import PERCENT
from aerona.db.kind_concepts.culture import BUILT_INS
from aerona.db.tables.culture_kinds import AimKindRow, FearKindRow, ReadingKindRow, TenetKindRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.kinds import KindHoldingRow
from aerona.db.write_guard import held
from aerona.domain.enums.entity import EntityType
from aerona.domain.enums.kinds import CARRIED_STANCES, KindConcept
from aerona.domain.enums.mind import DreamReading, LifeGoal, ValueHolder
from aerona.engine.body.customs import people_of
from aerona.engine.context import TickContext
from aerona.engine.mind.book import clamp_value, stored_values, write_values


@dataclass
class CultureKindTally:
    built_in: int = 0
    tenets: int = 0


async def ensure_culture_built_ins(session: AsyncSession) -> int:
    added = 0
    for table, rows in BUILT_INS:
        known = set(await session.scalars(select(table.built_in_key).where(table.built_in_key.is_not(None))))
        for row in rows:
            if row.key in known:
                continue
            session.add(table(name=row.name, built_in=True, built_in_key=row.key, category=row.category, locked=[], **row.values))
            added += 1
    if added:
        await session.flush()
    return added


async def folk_of(session: AsyncSession, mortal: EntityRow) -> EntityRow | None:
    return mortal if mortal.entity_type is EntityType.PEOPLE else await people_of(session, mortal)


async def held_of[T: (TenetKindRow, FearKindRow, ReadingKindRow, AimKindRow)](
    session: AsyncSession, holder_id: int, concept: KindConcept, table: type[T]
) -> list[tuple[KindHoldingRow, T]]:
    rows = await session.execute(
        select(KindHoldingRow, table)
        .join(table, table.id == KindHoldingRow.kind_id)
        .where(
            KindHoldingRow.holder_node_id == holder_id,
            KindHoldingRow.concept == concept,
            KindHoldingRow.stance.in_(sorted(CARRIED_STANCES)),
            table.retired.is_(False),
        )
        .order_by(KindHoldingRow.strength.desc(), KindHoldingRow.id)
    )
    return [(holding, kind) for holding, kind in rows.all()]


async def fears_held(session: AsyncSession, mortal: EntityRow) -> list[tuple[KindHoldingRow, FearKindRow]]:
    folk = await folk_of(session, mortal)
    return await held_of(session, folk.id, KindConcept.FEAR, FearKindRow) if folk is not None else []


async def reading_kind_for(session: AsyncSession, mortal: EntityRow, reading: DreamReading) -> ReadingKindRow | None:
    folk = await folk_of(session, mortal)
    held_rows = await held_of(session, folk.id, KindConcept.DREAM_READING, ReadingKindRow) if folk is not None else []
    return next((row for _, row in held_rows if row.category is reading), None)


async def aims_held(session: AsyncSession, mortal: EntityRow) -> dict[LifeGoal, tuple[int, AimKindRow]]:
    folk = await folk_of(session, mortal)
    found: dict[LifeGoal, tuple[int, AimKindRow]] = {}
    for holding, row in await held_of(session, folk.id, KindConcept.AIM, AimKindRow) if folk is not None else []:
        if row.category not in found:
            found[row.category] = (holding.strength, row)
    return found


async def hold_tenets(ctx: TickContext, people: EntityRow, tally: CultureKindTally) -> None:
    pull = ctx.rules.kinds.tenet_pull_pct
    values = await stored_values(ctx.session, ValueHolder.CULTURE, people.id)
    moved = False
    for holding, tenet in await held_of(ctx.session, people.id, KindConcept.TENET, TenetKindRow):
        for axis, delta in ((tenet.value_axis, tenet.value_delta), (tenet.second_axis, tenet.second_delta)):
            if axis is None or delta == 0:
                continue
            shift = delta * holding.strength * pull / PERCENT / PERCENT
            values[axis] = clamp_value(values.get(axis, 0) + shift)
            moved = True
        tally.tenets += 1
    if moved:
        await write_values(ctx.session, ValueHolder.CULTURE, people.id, values)


async def keep_culture_kinds(ctx: TickContext) -> CultureKindTally:
    tally = CultureKindTally(built_in=await ensure_culture_built_ins(ctx.session))
    holders = set(
        await ctx.session.scalars(
            select(KindHoldingRow.holder_node_id).where(KindHoldingRow.concept == KindConcept.TENET).order_by(KindHoldingRow.holder_node_id)
        )
    )
    for holder in sorted(holders):
        people = await ctx.session.get(EntityRow, holder)
        if people is None or held(people.id) or await stored_values(ctx.session, ValueHolder.CULTURE, people.id) == {}:
            continue
        await hold_tenets(ctx, people, tally)
    await ctx.session.flush()
    return tally
