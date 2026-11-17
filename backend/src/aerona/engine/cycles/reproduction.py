from dataclasses import dataclass

from sqlalchemy import select

from aerona.constants.units import PERCENT
from aerona.db.tables.cycles import MortalCasteRow, PeopleReproductionRow
from aerona.db.tables.entities import EntityRow
from aerona.db.write_guard import held
from aerona.domain.enums.cycles import ReproductiveSystem
from aerona.domain.enums.demography import Sex
from aerona.domain.enums.entity import EntityStatus, EntityType
from aerona.domain.models.entity_stats import MortalStats
from aerona.engine.context import TickContext
from aerona.engine.cycles.breeding import caste_for
from aerona.engine.mortal.profile import ensure_profile
from aerona.engine.notes import note
from aerona.engine.phases.births import bear_child
from aerona.engine.primitives.folk import folk_among
from aerona.engine.primitives.stats import stat_or

FLIPPED = {Sex.FEMALE.value: Sex.MALE.value, Sex.MALE.value: Sex.FEMALE.value}


@dataclass
class ReproductionTally:
    changed: int = 0
    castes: int = 0
    budded: int = 0


async def peoples_with(ctx: TickContext) -> list[tuple[EntityRow, PeopleReproductionRow]]:
    rows = await ctx.session.execute(
        select(EntityRow, PeopleReproductionRow)
        .join(PeopleReproductionRow, PeopleReproductionRow.people_entity_id == EntityRow.id)
        .where(EntityRow.status == EntityStatus.CANON, PeopleReproductionRow.system != ReproductiveSystem.TWO_SEX)
        .order_by(EntityRow.id)
    )
    return [(people, row) for people, row in rows.all()]


async def members(ctx: TickContext, people: EntityRow) -> list[EntityRow]:
    rows = await ctx.session.scalars(
        select(EntityRow)
        .where(EntityRow.entity_type == EntityType.MORTAL, EntityRow.status == EntityStatus.CANON, await folk_among(ctx.session, [people.id]))
        .order_by(EntityRow.id)
    )
    return [row for row in rows if not held(row.id)]


async def change_sex(ctx: TickContext, mortal: EntityRow, row: PeopleReproductionRow, tally: ReproductionTally) -> None:
    if not isinstance(mortal.stats, MortalStats) or mortal.stats.sex not in FLIPPED:
        return
    age = stat_or(mortal, "age", 0)
    if not age >= row.change_age > age - ctx.rules.time.years_per_epoch:
        return
    mortal.stats = mortal.stats.model_copy(update={"sex": FLIPPED[mortal.stats.sex]})
    tally.changed += 1
    await note(ctx, f"{mortal.name} came of the age when their people change, and took the other sex.", key="reproduction.changed", ids=[mortal.id])


async def keep_castes(ctx: TickContext, mortal: EntityRow, row: PeopleReproductionRow, tally: ReproductionTally) -> None:
    if await ctx.session.get(MortalCasteRow, mortal.id) is not None:
        return
    caste = caste_for(row, ctx.rng(f"caste.{mortal.id}"))
    ctx.session.add(MortalCasteRow(mortal_entity_id=mortal.id, caste=caste, since_epoch=ctx.epoch, locked=[]))
    tally.castes += 1


async def bud(ctx: TickContext, mortal: EntityRow, tally: ReproductionTally) -> None:
    table = ctx.rules.reproduction_systems
    profile, _ = await ensure_profile(ctx.session, mortal.id, ctx.epoch)
    chance = table.budding_pct * profile.fertility / PERCENT
    if not ctx.rng(f"bud.{mortal.id}.{ctx.epoch}").chance(chance):
        return
    child = await bear_child(ctx, mortal, mortal)
    tally.budded += 1
    await note(ctx, f"{mortal.name} budded and {child.name} grew from them.", key="reproduction.budded", ids=[mortal.id, child.id])


async def keep_reproduction(ctx: TickContext, tally: ReproductionTally) -> None:
    for people, row in await peoples_with(ctx):
        if held(people.id):
            continue
        for mortal in await members(ctx, people):
            if row.system is ReproductiveSystem.SEQUENTIAL:
                await change_sex(ctx, mortal, row, tally)
            elif row.system is ReproductiveSystem.CASTE:
                await keep_castes(ctx, mortal, row, tally)
            elif row.system is ReproductiveSystem.ASEXUAL:
                await bud(ctx, mortal, tally)
    await ctx.session.flush()
