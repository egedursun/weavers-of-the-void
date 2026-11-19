from sqlalchemy import select

from aerona.constants.units import PERCENT
from aerona.db.tables.crafts import NumberSystemRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.folk_knowledge import FolkKnowledgeRow
from aerona.db.write_guard import held
from aerona.domain.enums.culture import Technique
from aerona.domain.enums.entity import EntityStatus, EntityType
from aerona.domain.enums.folk_knowledge import FolkDomain, LoreHolders, LoreTransmission, NumberReading
from aerona.domain.enums.mind import ValueAxis, ValueHolder
from aerona.engine.context import TickContext
from aerona.engine.lore.research import has_technique
from aerona.engine.mind.book import Values, stored_values
from aerona.engine.primitives.naming import seed_of
from aerona.engine.primitives.numbers import clamp_int

LEANING = 50
READINGS_SPAN = 25
DOMAIN_AXES: dict[FolkDomain, ValueAxis] = {
    FolkDomain.WEATHER: ValueAxis.NATURE,
    FolkDomain.SKY: ValueAxis.KNOWLEDGE,
    FolkDomain.MATTER: ValueAxis.CRAFTSMANSHIP,
    FolkDomain.LAND: ValueAxis.NATURE,
    FolkDomain.WATERS: ValueAxis.NATURE,
    FolkDomain.PLANTS: ValueAxis.NATURE,
    FolkDomain.ANIMALS: ValueAxis.NATURE,
    FolkDomain.BODY: ValueAxis.MERCY,
    FolkDomain.ILLNESS: ValueAxis.MERCY,
    FolkDomain.MIND: ValueAxis.TRUTH,
    FolkDomain.SOCIETY: ValueAxis.LAW,
    FolkDomain.NUMBER: ValueAxis.KNOWLEDGE,
    FolkDomain.TIME: ValueAxis.TRADITION,
}


def half(value: int) -> int:
    return clamp_int(PERCENT // 2 + value // 2, 0, PERCENT)


def holders_of(values: Values) -> LoreHolders:
    tradition = values.get(ValueAxis.TRADITION, 0)
    craft = values.get(ValueAxis.CRAFTSMANSHIP, 0)
    if max(tradition, craft) < LEANING:
        return LoreHolders.EVERYONE
    return LoreHolders.ELDERS if tradition >= craft else LoreHolders.SPECIALISTS


async def transmission_of(ctx: TickContext, people_id: int, values: Values) -> LoreTransmission:
    if await has_technique(ctx.session, people_id, Technique.ALPHABET):
        return LoreTransmission.WRITTEN
    if values.get(ValueAxis.PIETY, 0) >= LEANING:
        return LoreTransmission.RITE
    if values.get(ValueAxis.CRAFTSMANSHIP, 0) >= LEANING:
        return LoreTransmission.APPRENTICESHIP
    return LoreTransmission.ORAL


def read_numbers(ctx: TickContext, people_id: int, system: NumberSystemRow, superstition: int) -> None:
    if system.numerology or "numerology" in (system.locked or []):
        return
    count = min(system.base - 1, max(0, superstition) // READINGS_SPAN)
    if count <= 0:
        return
    rng = ctx.rng(seed_of("numerology", people_id))
    readings = list(NumberReading)
    system.numerology = {str(number): rng.pick(readings).value for number in sorted(rng.sample(list(range(1, system.base)), count))}


async def seed_folk_knowledge(ctx: TickContext) -> int:
    known = set(await ctx.session.scalars(select(FolkKnowledgeRow.people_entity_id).distinct()))
    made = 0
    for folk in list(
        await ctx.session.scalars(
            select(EntityRow).where(EntityRow.entity_type == EntityType.PEOPLE, EntityRow.status == EntityStatus.CANON).order_by(EntityRow.id)
        )
    ):
        if held(folk.id):
            continue
        values = await stored_values(ctx.session, ValueHolder.CULTURE, folk.id)
        system = await ctx.session.get(NumberSystemRow, folk.id)
        if system is not None:
            read_numbers(ctx, folk.id, system, values.get(ValueAxis.SUPERSTITION, 0))
        if folk.id in known:
            continue
        accuracy = half((values.get(ValueAxis.KNOWLEDGE, 0) - values.get(ValueAxis.SUPERSTITION, 0)) // 2)
        holders = holders_of(values)
        transmission = await transmission_of(ctx, folk.id, values)
        for domain, axis in DOMAIN_AXES.items():
            depth = system.numeracy if domain is FolkDomain.NUMBER and system is not None else half(values.get(axis, 0))
            ctx.session.add(
                FolkKnowledgeRow(
                    people_entity_id=folk.id,
                    domain=domain,
                    depth=depth,
                    accuracy=accuracy,
                    holders=holders,
                    transmission=transmission,
                    locked=[],
                )
            )
        made += 1
    await ctx.session.flush()
    return made
