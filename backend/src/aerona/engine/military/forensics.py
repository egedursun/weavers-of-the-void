from sqlalchemy import select

from aerona.catalog.law_depth import MEDICINE_TECHNIQUES, METHOD_STEALTH
from aerona.constants.units import PERCENT
from aerona.db.tables.disease import DiseaseProfileRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.law_depth import KillingRow
from aerona.db.tables.military import SpyNetworkRow
from aerona.db.write_guard import held
from aerona.domain.enums.entity import EntityStatus, EntityType
from aerona.domain.enums.law_depth import KillMethod
from aerona.domain.enums.mind import SkillKind
from aerona.engine.context import TickContext
from aerona.engine.lore.civics import holders_know
from aerona.engine.mind.book import best_skill
from aerona.engine.primitives.folk import present_among
from aerona.engine.primitives.numbers import clamp_int, round_half_up

HEALING = (SkillKind.MEDICINE, SkillKind.SURGERY)


async def methods_for(ctx: TickContext, owner: EntityRow, network: SpyNetworkRow) -> list[KillMethod]:
    found = [KillMethod.BLADE, KillMethod.POISON]
    if network.depth >= 2 * ctx.rules.espionage.assassinate_depth:
        found.append(KillMethod.ACCIDENT)
    if await ctx.session.scalar(select(DiseaseProfileRow.disease_entity_id).limit(1)) is not None:
        found.append(KillMethod.DISEASE)
    if owner.entity_type is EntityType.CULT:
        found.append(KillMethod.CURSE)
    return found


async def choose_method(ctx: TickContext, owner: EntityRow, network: SpyNetworkRow, victim: EntityRow) -> KillMethod:
    return ctx.rng(f"espionage.method.{network.id}.{victim.id}").pick(await methods_for(ctx, owner, network))


async def examiner_in(ctx: TickContext, town_id: int | None, victim_id: int) -> tuple[EntityRow, int] | None:
    if town_id is None:
        return None
    folk = await ctx.session.scalars(
        select(EntityRow)
        .where(
            EntityRow.entity_type == EntityType.MORTAL,
            EntityRow.status == EntityStatus.CANON,
            EntityRow.id != victim_id,
            await present_among(ctx.session, [town_id]),
        )
        .order_by(EntityRow.id)
    )
    best: tuple[EntityRow, int] | None = None
    for mortal in list(folk):
        skill = await best_skill(ctx.session, mortal.id, HEALING)
        if skill > 0 and (best is None or skill > best[1]):
            best = (mortal, skill)
    return best


async def medicine_known(ctx: TickContext, town_id: int | None) -> bool:
    if town_id is None:
        return False
    for technique in MEDICINE_TECHNIQUES:
        if await holders_know(ctx.session, [town_id], technique):
            return True
    return False


async def examine(ctx: TickContext, victim: EntityRow, killer_id: int | None, method: KillMethod) -> KillingRow:
    table = ctx.rules.forensics
    found = await examiner_in(ctx, victim.location_id, victim.id)
    sight = round_half_up(found[1] * table.examiner_pct / PERCENT) if found is not None else 0
    theory = table.theory_bonus if await medicine_known(ctx, victim.location_id) else 0
    chance = clamp_int(PERCENT - int(getattr(table, METHOD_STEALTH[method])) + sight + theory, 0, PERCENT)
    row = KillingRow(
        victim_entity_id=victim.id,
        killer_entity_id=killer_id,
        method=method,
        recognised=ctx.rng(f"espionage.forensics.{victim.id}").chance(chance),
        examiner_entity_id=found[0].id if found is not None and not held(found[0].id) else None,
        epoch=ctx.epoch,
        locked=[],
    )
    ctx.session.add(row)
    await ctx.session.flush()
    return row
