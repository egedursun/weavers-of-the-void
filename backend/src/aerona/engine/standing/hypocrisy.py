from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.catalog.mind import ACT_READINGS
from aerona.constants.units import PERCENT
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.mortal import MortalProfileRow
from aerona.db.tables.standing import ProfessionOfValueRow
from aerona.db.write_guard import held
from aerona.domain.enums.entity import EntityType
from aerona.domain.enums.mind import ActKind
from aerona.domain.enums.modifier import IncidentRole
from aerona.engine.context import TickContext
from aerona.engine.mind.book import values_for
from aerona.engine.mortal.standing import add_infamy
from aerona.engine.primitives.naming import seed_of
from aerona.engine.primitives.numbers import clamp_int
from aerona.engine.primitives.stats import has_stat, scale_stat
from aerona.engine.recording.record import record
from aerona.engine.recording.terms import explaining_alone, term
from aerona.rules.registry import Rules


@dataclass
class HypocrisyTally:
    faded: int = 0
    exposed: int = 0
    forgiven: int = 0


async def professions_of(session: AsyncSession, rules: Rules, holder_id: int) -> list[ProfessionOfValueRow]:
    rows = list(await session.scalars(select(ProfessionOfValueRow).where(ProfessionOfValueRow.holder_node_id == holder_id).order_by(ProfessionOfValueRow.id)))
    if rows:
        return rows
    for axis, value in sorted((await values_for(session, holder_id)).items()):
        if value >= rules.standing.profess_from:
            row = ProfessionOfValueRow(holder_node_id=holder_id, axis=axis, strength=clamp_int(value, 0, PERCENT), locked=[])
            session.add(row)
            rows.append(row)
    return rows


async def professed_act(ctx: TickContext, actor_id: int, act: ActKind, witnesses: int) -> None:
    readings = ACT_READINGS.get(act)
    if readings is None or held(actor_id):
        return
    step = ctx.rules.standing.gap_per_act
    for row in await professions_of(ctx.session, ctx.rules, actor_id):
        if readings.get(row.axis, 0) >= 0 or "gap" in row.locked:
            continue
        with explaining_alone():
            term("standing.gap", step, source_node_id=actor_id)
            row.gap = clamp_int(row.gap + step, 0, PERCENT)
        row.acts_against += 1
        row.knowers += witnesses
        row.last_act_epoch = ctx.epoch


async def expose(ctx: TickContext, row: ProfessionOfValueRow, exposer_id: int | None) -> None:
    table = ctx.rules.standing
    row.exposed = True
    holder = await ctx.session.get(EntityRow, row.holder_node_id)
    if holder is not None and not held(holder.id):
        if holder.entity_type is EntityType.MORTAL:
            await add_infamy(ctx.session, holder.id, table.hypocrisy_trust_loss, ctx.epoch, rules=ctx.rules)
            profile = await ctx.session.get(MortalProfileRow, holder.id)
            if profile is not None and profile.legitimacy is not None and "legitimacy" not in (profile.locked or []):
                profile.legitimacy = clamp_int(profile.legitimacy - table.hypocrisy_trust_loss, 0, PERCENT)
        if has_stat(holder, "followers"):
            scale_stat(ctx.rules, holder, "followers", 1 - table.hypocrisy_follower_loss_pct / PERCENT, default=0)
    roles = {IncidentRole.SUBJECT: row.holder_node_id, IncidentRole.ACTOR: exposer_id}
    await record(ctx, "standing.hypocrisy_exposed", roles=roles, facts={"axis": row.axis, "gap": row.gap, "acts": row.acts_against})


async def keep_hypocrisy(ctx: TickContext, tally: HypocrisyTally) -> None:
    table = ctx.rules.standing
    for row in list(await ctx.session.scalars(select(ProfessionOfValueRow).order_by(ProfessionOfValueRow.id))):
        if held(row.holder_node_id):
            continue
        if row.last_act_epoch != ctx.epoch and row.gap > 0 and "gap" not in row.locked:
            row.gap = clamp_int(row.gap - table.gap_fade, 0, PERCENT)
            tally.faded += 1
        wide = row.gap >= table.hypocrisy_gap_threshold
        if wide and not row.exposed and row.knowers > 0 and ctx.rng(seed_of("hypocrisy", row.id, ctx.epoch)).chance(table.exposure_pct):
            tally.exposed += 1
            await expose(ctx, row, None)
        elif row.exposed and row.gap < table.hypocrisy_gap_threshold // 2 and "exposed" not in row.locked:
            row.exposed = False
            tally.forgiven += 1
            await record(ctx, "standing.hypocrisy_forgiven", roles={IncidentRole.SUBJECT: row.holder_node_id}, facts={"axis": row.axis, "gap": row.gap})
    await ctx.session.flush()
