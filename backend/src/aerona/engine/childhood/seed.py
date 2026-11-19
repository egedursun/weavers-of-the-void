from dataclasses import dataclass

from sqlalchemy import select

from aerona.constants.units import PERCENT
from aerona.db.tables.biology import BiologyRow
from aerona.db.tables.childhood import TECHNIQUE_WEIGHTS, ChildStandingRow, InfantCareRow, PedagogyRow, SocializationRow
from aerona.db.tables.customs import AgeSetRow
from aerona.db.tables.cycles import KinshipSystemRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.structures import StructureProfileRow
from aerona.db.write_guard import held
from aerona.domain.enums.childhood import InfantCarer, InfantFeeding, PedagogyTheory
from aerona.domain.enums.cycles import AdoptionKind
from aerona.domain.enums.entity import EntityStatus, EntityType
from aerona.domain.enums.mind import ValueAxis, ValueHolder
from aerona.engine.childhood.life import SCHOOLS
from aerona.engine.context import TickContext
from aerona.engine.mind.book import stored_values
from aerona.engine.primitives.numbers import clamp_int

LEANING = 60
BASE_WEIGHT = 10
TECHNIQUE_AXES: dict[str, ValueAxis] = {
    "example": ValueAxis.FAMILY,
    "instruction": ValueAxis.TRADITION,
    "praise": ValueAxis.MERCY,
    "shame": ValueAxis.HONOUR,
    "punishment": ValueAxis.HIERARCHY,
    "ritual_ordeal": ValueAxis.MARTIAL,
    "storytelling": ValueAxis.ARTWORK,
    "play": ValueAxis.LEISURE,
    "apprenticeship": ValueAxis.CRAFTSMANSHIP,
    "schooling": ValueAxis.KNOWLEDGE,
    "peer_group": ValueAxis.FRIENDSHIP,
    "age_set": ValueAxis.LOYALTY,
}
AIM_AXES: dict[str, ValueAxis] = {
    "aim_independence": ValueAxis.COMPETITION,
    "aim_obedience": ValueAxis.HIERARCHY,
    "aim_aggression": ValueAxis.MARTIAL,
    "aim_restraint": ValueAxis.LAW,
    "aim_cooperation": ValueAxis.FRIENDSHIP,
    "aim_piety": ValueAxis.PIETY,
    "aim_craft": ValueAxis.CRAFTSMANSHIP,
}


@dataclass
class ChildhoodSeedTally:
    infant_care: int = 0
    standing: int = 0
    socialization: int = 0
    pedagogy: int = 0


def half(value: int) -> int:
    return clamp_int(PERCENT // 2 + value // 2, 0, PERCENT)


def weights_for(values: dict[ValueAxis, int], age_sets: bool) -> dict[str, int]:
    raw = {name: max(0, BASE_WEIGHT + values.get(axis, 0) // 5) for name, axis in TECHNIQUE_AXES.items()}
    if not age_sets:
        raw["age_set"] = 0
    total = sum(raw.values()) or 1
    shares = {name: raw[name] * PERCENT // total for name in TECHNIQUE_WEIGHTS}
    shares["example"] += PERCENT - sum(shares.values())
    return shares


async def peoples(ctx: TickContext, owned: set[int]) -> list[EntityRow]:
    rows = await ctx.session.scalars(
        select(EntityRow).where(EntityRow.entity_type == EntityType.PEOPLE, EntityRow.status == EntityStatus.CANON).order_by(EntityRow.id)
    )
    return [row for row in rows if row.id not in owned and not held(row.id)]


async def seed_infant_care(ctx: TickContext, tally: ChildhoodSeedTally) -> None:
    for folk in await peoples(ctx, set(await ctx.session.scalars(select(InfantCareRow.people_entity_id)))):
        biology = await ctx.session.get(BiologyRow, folk.id)
        system = await ctx.session.get(KinshipSystemRow, folk.id)
        values = await stored_values(ctx.session, ValueHolder.CULTURE, folk.id)
        if biology is not None and biology.food_need_pct == 0:
            feeding = InfantFeeding.NONE_NEEDED
        elif system is not None and system.adoption is AdoptionKind.FOSTER:
            feeding = InfantFeeding.BY_OTHER_NURSE
        else:
            feeding = InfantFeeding.BY_BIRTH_PARENT
        carer = InfantCarer.COMMUNITY if values.get(ValueAxis.FRIENDSHIP, 0) >= LEANING else InfantCarer.KIN
        ctx.session.add(InfantCareRow(people_entity_id=folk.id, feeding=feeding, carer=carer, locked=[]))
        tally.infant_care += 1


async def seed_standing(ctx: TickContext, tally: ChildhoodSeedTally) -> None:
    for folk in await peoples(ctx, set(await ctx.session.scalars(select(ChildStandingRow.people_entity_id)))):
        values = await stored_values(ctx.session, ValueHolder.CULTURE, folk.id)
        labour = clamp_int(PERCENT // 5 + values.get(ValueAxis.WEALTH, 0) // 4 - values.get(ValueAxis.KNOWLEDGE, 0) // 4, 0, PERCENT)
        ctx.session.add(
            ChildStandingRow(
                people_entity_id=folk.id,
                labour_share=labour,
                protected=values.get(ValueAxis.MERCY, 0) >= LEANING,
                locked=[],
            )
        )
        tally.standing += 1


async def seed_socialization(ctx: TickContext, tally: ChildhoodSeedTally) -> None:
    for folk in await peoples(ctx, set(await ctx.session.scalars(select(SocializationRow.people_entity_id)))):
        values = await stored_values(ctx.session, ValueHolder.CULTURE, folk.id)
        age_sets = await ctx.session.scalar(select(AgeSetRow.id).where(AgeSetRow.people_entity_id == folk.id).limit(1)) is not None
        aims = {name: half(values.get(axis, 0)) for name, axis in AIM_AXES.items()}
        ctx.session.add(SocializationRow(people_entity_id=folk.id, **weights_for(values, age_sets), **aims, locked=[]))
        tally.socialization += 1


async def seed_pedagogy(ctx: TickContext, tally: ChildhoodSeedTally) -> None:
    taught = set(await ctx.session.scalars(select(PedagogyRow.holder_node_id)))
    rows = await ctx.session.execute(
        select(EntityRow, StructureProfileRow)
        .join(StructureProfileRow, StructureProfileRow.structure_entity_id == EntityRow.id)
        .where(StructureProfileRow.kind.in_(sorted(SCHOOLS)), EntityRow.status == EntityStatus.CANON)
        .order_by(EntityRow.id)
    )
    for school, _profile in list(rows):
        if school.id in taught or held(school.id):
            continue
        ctx.session.add(PedagogyRow(holder_node_id=school.id, theory=PedagogyTheory.ROTE, founded_epoch=ctx.epoch, locked=[]))
        tally.pedagogy += 1


async def seed_childhood(ctx: TickContext) -> ChildhoodSeedTally:
    tally = ChildhoodSeedTally()
    await seed_infant_care(ctx, tally)
    await seed_standing(ctx, tally)
    await seed_socialization(ctx, tally)
    await seed_pedagogy(ctx, tally)
    await ctx.session.flush()
    return tally
