from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.catalog.ethics import STANCE_ORDER, STANCE_READINGS
from aerona.catalog.norms import BEHAVIOUR_READINGS, SITUATION_SHIFTS
from aerona.constants.units import PERCENT
from aerona.db.tables.collective import NormChangeRow, SocialNormRow
from aerona.db.tables.entities import EntityRow
from aerona.db.write_guard import held
from aerona.domain.enums.collective import NormBehaviour, NormSituation
from aerona.domain.enums.entity import EntityStatus, EntityType
from aerona.domain.enums.mind import EthicalStance
from aerona.domain.enums.polity import LawKind
from aerona.engine.context import TickContext
from aerona.engine.mind.book import Values, stored_values
from aerona.engine.mind.ethics import church_of, holder_kind, stance_for
from aerona.engine.polity.laws import law_param
from aerona.engine.primitives.folk import homes_for
from aerona.engine.primitives.numbers import clamp_int
from aerona.rules.registry import Rules

Norms = dict[tuple[NormSituation, NormBehaviour], EthicalStance]
STANCE = "stance"
LOOSE_LUXURY = 30
STRICT = frozenset({EthicalStance.SHAMEFUL, EthicalStance.UNTHINKABLE})


@dataclass
class NormTally:
    seeded: int = 0
    drifted: int = 0
    doctrine: int = 0
    law: int = 0


def norm_reading(values: Values, situation: NormSituation, behaviour: NormBehaviour) -> int:
    base = sum(values.get(axis, 0) * weight for axis, weight in BEHAVIOUR_READINGS[behaviour].items()) / PERCENT
    shifts, axis = SITUATION_SHIFTS[situation]
    lean = shifts.get(behaviour, 0) * (1 + values.get(axis, 0) / PERCENT)
    return clamp_int(base + lean, -PERCENT, PERCENT)


def wanted_norms(rules: Rules, values: Values) -> Norms:
    return {(situation, behaviour): stance_for(rules, norm_reading(values, situation, behaviour)) for situation in NormSituation for behaviour in NormBehaviour}


async def norms_of(session: AsyncSession, holder_id: int | None) -> Norms:
    if holder_id is None:
        return {}
    rows = await session.scalars(select(SocialNormRow).where(SocialNormRow.holder_entity_id == holder_id))
    return {(row.situation, row.behaviour): row.stance for row in rows}


def stance_in(norms: Norms, situation: NormSituation, behaviour: NormBehaviour) -> EthicalStance:
    return norms.get((situation, behaviour), EthicalStance.ACCEPTABLE)


async def write_norm(
    ctx: TickContext, holder_id: int, situation: NormSituation, behaviour: NormBehaviour, stance: EthicalStance, *, cause: str
) -> SocialNormRow | None:
    row = await ctx.session.get(SocialNormRow, (holder_id, situation, behaviour))
    before = row.stance if row is not None else EthicalStance.ACCEPTABLE
    if before is stance or (row is not None and STANCE in row.locked):
        return row
    if row is None:
        row = SocialNormRow(holder_entity_id=holder_id, situation=situation, behaviour=behaviour, stance=stance, since_epoch=ctx.epoch, locked=[])
        ctx.session.add(row)
    else:
        row.stance, row.since_epoch = stance, ctx.epoch
    ctx.session.add(
        NormChangeRow(holder_entity_id=holder_id, situation=situation, behaviour=behaviour, before=before, after=stance, cause=cause, epoch=ctx.epoch)
    )
    await ctx.session.flush()
    return row


def step_toward(here: EthicalStance, there: EthicalStance) -> EthicalStance:
    first, second = STANCE_ORDER.index(here), STANCE_ORDER.index(there)
    if first == second:
        return here
    return STANCE_ORDER[first + (1 if second > first else -1)]


async def cultures(ctx: TickContext) -> list[EntityRow]:
    rows = await ctx.session.scalars(
        select(EntityRow).where(EntityRow.entity_type.in_([EntityType.PEOPLE, EntityType.CULT]), EntityRow.status == EntityStatus.CANON).order_by(EntityRow.id)
    )
    return [row for row in rows if not held(row.id)]


async def seed_norms(ctx: TickContext, culture: EntityRow, tally: NormTally) -> None:
    if await ctx.session.scalar(select(SocialNormRow.holder_entity_id).where(SocialNormRow.holder_entity_id == culture.id).limit(1)) is not None:
        return
    values = await stored_values(ctx.session, holder_kind(culture), culture.id)
    if not values:
        return
    for (situation, behaviour), stance in wanted_norms(ctx.rules, values).items():
        if stance is not EthicalStance.ACCEPTABLE:
            ctx.session.add(
                SocialNormRow(holder_entity_id=culture.id, situation=situation, behaviour=behaviour, stance=stance, since_epoch=ctx.epoch, locked=[])
            )
            tally.seeded += 1
    await ctx.session.flush()


async def drift_norms(ctx: TickContext, culture: EntityRow, tally: NormTally) -> None:
    if not ctx.rng(f"norm_drift.{culture.id}.{ctx.epoch}").chance(ctx.rules.norms.drift_pct):
        return
    values = await stored_values(ctx.session, holder_kind(culture), culture.id)
    if not values:
        return
    held_norms = await norms_of(ctx.session, culture.id)
    for key, wanted in sorted(wanted_norms(ctx.rules, values).items()):
        here = stance_in(held_norms, *key)
        moved = step_toward(here, wanted)
        if moved is not here and await write_norm(ctx, culture.id, *key, moved, cause="values") is not None:
            tally.drifted += 1


async def follow_doctrine(ctx: TickContext, people: EntityRow, tally: NormTally) -> None:
    own = await norms_of(ctx.session, people.id)
    for cult_id in await church_of(ctx.session, people):
        for key, stance in sorted((await norms_of(ctx.session, cult_id)).items()):
            if stance not in STRICT or stance_in(own, *key) in STRICT:
                continue
            roll = ctx.rng(f"norm_doctrine.{people.id}.{cult_id}.{key[0].value}.{key[1].value}.{ctx.epoch}")
            if roll.chance(ctx.rules.norms.doctrine_pct) and await write_norm(ctx, people.id, *key, stance, cause="doctrine") is not None:
                own[key] = stance
                tally.doctrine += 1


async def follow_sumptuary(ctx: TickContext, people: EntityRow, tally: NormTally) -> None:
    homes = sorted(await homes_for(ctx.session, [people.id]))
    if not homes:
        return
    luxury = await law_param(ctx.session, homes[0], LawKind.SUMPTUARY, "merchant_luxury")
    if not isinstance(luxury, int) or luxury > LOOSE_LUXURY:
        return
    if not ctx.rng(f"norm_law.{people.id}.{ctx.epoch}").chance(ctx.rules.norms.law_pct):
        return
    own = await norms_of(ctx.session, people.id)
    stance = EthicalStance.SHAMEFUL if luxury <= LOOSE_LUXURY // 2 else EthicalStance.FROWNED_UPON
    for situation in (NormSituation.MARKET, NormSituation.COURT, NormSituation.TEMPLE):
        loose = stance_in(own, situation, NormBehaviour.FINE_DRESS) not in STRICT
        if loose and await write_norm(ctx, people.id, situation, NormBehaviour.FINE_DRESS, stance, cause="sumptuary law") is not None:
            tally.law += 1


async def keep_norms(ctx: TickContext, tally: NormTally) -> None:
    for culture in await cultures(ctx):
        await seed_norms(ctx, culture, tally)
        await drift_norms(ctx, culture, tally)
        if culture.entity_type is EntityType.PEOPLE:
            await follow_doctrine(ctx, culture, tally)
            await follow_sumptuary(ctx, culture, tally)
    await ctx.session.flush()


def norm_pull(stance: EthicalStance) -> float:
    return STANCE_READINGS[stance] / abs(STANCE_READINGS[EthicalStance.UNTHINKABLE])


def volition(rules: Rules, stance: EthicalStance, *, conformity: float, rebel: float) -> float:
    table = rules.volition
    pull = norm_pull(stance)
    conform = (1 + conformity) / 2
    if pull >= 0:
        return 1 + pull * table.norm_draw / PERCENT * conform
    return 1 + pull * table.norm_cost / PERCENT * (0.5 + conform) - pull * table.rebel_appeal / PERCENT * rebel


def breach(stance: EthicalStance) -> bool:
    return stance in STRICT
