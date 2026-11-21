from sqlalchemy import select

from aerona.db.tables.entities import EntityRow
from aerona.db.tables.mass_weapons import MassWeaponRow
from aerona.db.tables.polity import TreatyClauseRow, TreatyProfileRow
from aerona.db.write_guard import held
from aerona.domain.enums.mass_weapons import ARMED_STAGES
from aerona.domain.enums.polity import ClauseKind, PartyRole, TreatyKind, TreatyStatus
from aerona.engine.context import TickContext
from aerona.engine.mass_weapons.book import ArsenalTally, weapons_of
from aerona.engine.polity.accords import Clause, sign
from aerona.engine.primitives.queries import living_entity
from aerona.engine.services.war import current_war


async def bound_pair(ctx: TickContext, first: int, second: int) -> bool:
    found = await ctx.session.scalar(
        select(TreatyClauseRow.id)
        .join(TreatyProfileRow, TreatyProfileRow.treaty_entity_id == TreatyClauseRow.treaty_entity_id)
        .where(
            TreatyClauseRow.kind == ClauseKind.MASS_WEAPON_LIMIT,
            TreatyClauseRow.obligor_node_id == first,
            TreatyClauseRow.beneficiary_node_id == second,
            TreatyProfileRow.status == TreatyStatus.IN_FORCE,
        )
        .limit(1)
    )
    return found is not None


async def arsenal_size(ctx: TickContext, holder_id: int) -> int:
    return sum(weapon.count for weapon in await weapons_of(ctx.session, holder_id) if weapon.stage in ARMED_STAGES)


async def past_limit(ctx: TickContext, actors: set[int], clause: TreatyClauseRow) -> bool:
    cap = int(clause.params.get("count", 0))
    for actor in sorted(actors):
        weapons = await weapons_of(ctx.session, actor)
        if sum(weapon.count for weapon in weapons) > cap or any(weapon.tested_epoch == ctx.epoch for weapon in weapons):
            return True
    return False


async def bind_arsenals(ctx: TickContext, tally: ArsenalTally) -> None:
    holders: list[EntityRow] = []
    for holder_id in sorted(set(await ctx.session.scalars(select(MassWeaponRow.holder_entity_id).where(MassWeaponRow.count > 0)))):
        holder = await living_entity(ctx.session, holder_id)
        if holder is not None and not held(holder.id):
            holders.append(holder)
    for index, first in enumerate(holders):
        for second in holders[index + 1 :]:
            if (
                first.world_id != second.world_id
                or await bound_pair(ctx, first.id, second.id)
                or await current_war(ctx.session, first.id, second.id) is not None
            ):
                continue
            if not ctx.rng(f"arms_limit.{first.id}.{second.id}.{ctx.epoch}").chance(ctx.rules.mass_weapons.limit_treaty_chance_pct):
                continue
            await sign(
                ctx,
                TreatyKind.ARMS_LIMIT,
                [(first.id, PartyRole.SIGNATORY), (second.id, PartyRole.SIGNATORY)],
                clauses=[
                    Clause(ClauseKind.MASS_WEAPON_LIMIT, first.id, second.id, {"count": await arsenal_size(ctx, first.id)}),
                    Clause(ClauseKind.MASS_WEAPON_LIMIT, second.id, first.id, {"count": await arsenal_size(ctx, second.id)}),
                ],
            )
            tally.treaties += 1
