from sqlalchemy import select

from aerona.catalog.death_shapes import RITE_TREATMENTS
from aerona.constants.units import PERCENT
from aerona.db.tables.death_work import DeathWorkRow
from aerona.db.tables.demography import PeopleCultureRow
from aerona.db.tables.entities import EntityRow
from aerona.db.write_guard import held
from aerona.domain.enums.death_work import DeathRole
from aerona.domain.enums.entity import EntityStatus, EntityType
from aerona.domain.enums.mind import ValueAxis, ValueHolder
from aerona.engine.context import TickContext
from aerona.engine.mind.book import stored_values
from aerona.engine.primitives.numbers import clamp_int

HANDLING = frozenset({DeathRole.WASHER, DeathRole.PREPARER, DeathRole.CARRIER})
SACRED = frozenset({DeathRole.OFFICIANT, DeathRole.KEEPER_OF_REMAINS})
FIRST_WORKERS = 2


def half(value: int) -> int:
    return clamp_int(PERCENT // 2 + value // 2, 0, PERCENT)


def purity_of(role: DeathRole, values: dict[ValueAxis, int]) -> int:
    if role in HANDLING:
        return clamp_int(PERCENT - half(values.get(ValueAxis.PURITY, 0)) + values.get(ValueAxis.DEATH, 0) // 4, 0, PERCENT)
    if role in SACRED:
        return half(values.get(ValueAxis.PIETY, 0))
    return half(values.get(ValueAxis.DEATH, 0) if role is DeathRole.MOURNER else values.get(ValueAxis.TRADITION, 0))


def fit_remains(culture: PeopleCultureRow) -> None:
    allowed = RITE_TREATMENTS[culture.funeral_rite]
    if culture.remains_treatment not in allowed and "remains_treatment" not in (culture.locked or []):
        culture.remains_treatment = allowed[0]


async def seed_death_work(ctx: TickContext) -> int:
    staffed = set(await ctx.session.scalars(select(DeathWorkRow.people_entity_id).distinct()))
    made = 0
    for folk in list(
        await ctx.session.scalars(
            select(EntityRow).where(EntityRow.entity_type == EntityType.PEOPLE, EntityRow.status == EntityStatus.CANON).order_by(EntityRow.id)
        )
    ):
        if held(folk.id):
            continue
        culture = await ctx.session.get(PeopleCultureRow, folk.id)
        if culture is not None:
            fit_remains(culture)
        if folk.id in staffed:
            continue
        values = await stored_values(ctx.session, ValueHolder.CULTURE, folk.id)
        ctx.session.add_all(
            DeathWorkRow(people_entity_id=folk.id, role=role, purity=purity_of(role, values), workers=FIRST_WORKERS, locked=[]) for role in DeathRole
        )
        made += 1
    await ctx.session.flush()
    return made
