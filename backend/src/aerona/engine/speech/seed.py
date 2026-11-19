from sqlalchemy import select

from aerona.constants.units import PERCENT
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.speech import HumourStyleRow
from aerona.db.write_guard import held
from aerona.domain.enums.entity import EntityStatus, EntityType
from aerona.domain.enums.mind import ValueAxis, ValueHolder
from aerona.domain.enums.speech import HumourForm
from aerona.engine.context import TickContext
from aerona.engine.mind.book import stored_values
from aerona.engine.primitives.numbers import clamp_int

LEANING = 50
FORM_AXES: dict[ValueAxis, HumourForm] = {
    ValueAxis.TRUTH: HumourForm.IRONY,
    ValueAxis.FRIENDSHIP: HumourForm.TEASING,
    ValueAxis.ARTWORK: HumourForm.STORYTELLING,
    ValueAxis.LEISURE: HumourForm.ABSURD,
    ValueAxis.COMPETITION: HumourForm.WORDPLAY,
    ValueAxis.SUPERSTITION: HumourForm.RITUAL_CLOWNING,
    ValueAxis.LAW: HumourForm.SATIRE,
}


def half(value: int) -> int:
    return clamp_int(PERCENT // 2 + value // 2, 0, PERCENT)


async def seed_humour(ctx: TickContext) -> int:
    owned = set(await ctx.session.scalars(select(HumourStyleRow.people_entity_id)))
    made = 0
    for folk in list(
        await ctx.session.scalars(
            select(EntityRow).where(EntityRow.entity_type == EntityType.PEOPLE, EntityRow.status == EntityStatus.CANON).order_by(EntityRow.id)
        )
    ):
        if folk.id in owned or held(folk.id):
            continue
        values = await stored_values(ctx.session, ValueHolder.CULTURE, folk.id)
        axis = max(sorted(FORM_AXES), key=lambda each: values.get(each, 0))
        hierarchy = values.get(ValueAxis.HIERARCHY, 0)
        piety = values.get(ValueAxis.PIETY, 0)
        ctx.session.add(
            HumourStyleRow(
                people_entity_id=folk.id,
                form=FORM_AXES[axis],
                mock_rulers=hierarchy < LEANING,
                mock_gods=piety < LEANING,
                mock_kin=values.get(ValueAxis.FAMILY, 0) < LEANING,
                mock_strangers=values.get(ValueAxis.XENOPHILIA, 0) < LEANING,
                offence_threshold=half(values.get(ValueAxis.HONOUR, 0)),
                directness=half(values.get(ValueAxis.TRUTH, 0)),
                silence=half(values.get(ValueAxis.TRADITION, 0)),
                locked=[],
            )
        )
        made += 1
    await ctx.session.flush()
    return made
