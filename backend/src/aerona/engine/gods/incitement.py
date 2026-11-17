from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import aliased

from aerona.constants.units import PERCENT
from aerona.db.tables.sons import SonRow
from aerona.db.tables.warfare import WarRow, WarSideRow
from aerona.domain.enums.mind import MemoryKind
from aerona.domain.enums.modifier import IncidentRole
from aerona.domain.enums.son import SonStatus
from aerona.engine.context import TickContext
from aerona.engine.mind.memories import remember
from aerona.engine.primitives.faith import living_patron
from aerona.engine.primitives.holds import INCITEMENT_KEY, is_held
from aerona.engine.primitives.queries import living_entity
from aerona.engine.recording.record import record
from aerona.rules.registry.incitement import IncitementRules

INCITED_NOTE = "set the war upon us"


@dataclass(frozen=True)
class IncitementToll:
    fame: int
    existence: int
    grieved: bool


def incitement_toll(rules: IncitementRules, battles: int, victor_worships: bool, loser_worships: bool, has_loser: bool) -> IncitementToll:
    fame = min(rules.fame_cap, max(0, battles) * rules.fame_per_battle)
    existence = (rules.patron_victory_existence if victor_worships else 0) - (rules.patron_defeat_existence if loser_worships else 0)
    return IncitementToll(fame=fame, existence=existence, grieved=has_loser and not loser_worships and rules.loser_grievance > 0)


async def held_incitement(session: AsyncSession, epoch: int, first_id: int, second_id: int) -> tuple[bool, int | None]:
    one, other = aliased(WarSideRow), aliased(WarSideRow)
    war = await session.scalar(
        select(WarRow)
        .join(one, one.war_id == WarRow.id)
        .join(other, other.war_id == WarRow.id)
        .where(one.entity_id == first_id, other.entity_id == second_id)
        .order_by(WarRow.id.desc())
        .limit(1)
    )
    if war is None or not await is_held(session, war.event_entity_id, INCITEMENT_KEY, epoch):
        return False, None
    return True, war.incited_by_son_id


async def answer_incitement(ctx: TickContext, war: WarRow, victor_id: int | None, loser_id: int | None) -> IncitementToll | None:
    if war.incited_by_son_id is None:
        return None
    son = await ctx.session.get(SonRow, war.incited_by_son_id)
    if son is None or son.status is SonStatus.DEAD:
        return None
    rules = ctx.rules.incitement
    victor = await living_entity(ctx.session, victor_id)
    loser = await living_entity(ctx.session, loser_id)
    victor_patron = await living_patron(ctx.session, victor) if victor is not None else None
    loser_patron = await living_patron(ctx.session, loser) if loser is not None else None
    toll = incitement_toll(
        rules,
        war.battles,
        victor_patron is not None and victor_patron.id == son.id,
        loser_patron is not None and loser_patron.id == son.id,
        loser is not None,
    )
    son.fame += toll.fame
    son.existence = max(0, min(PERCENT, son.existence + toll.existence))
    if toll.grieved and loser is not None:
        await remember(
            ctx.session,
            ctx.rules,
            holder_id=loser.id,
            subject_id=son.id,
            kind=MemoryKind.HARMED_ME,
            magnitude=-rules.loser_grievance,
            epoch=ctx.epoch,
            note=INCITED_NOTE,
        )
    roles = {IncidentRole.ACTOR: son.id, **({IncidentRole.TARGET: loser.id} if toll.grieved and loser is not None else {})}
    await record(
        ctx,
        "war.incitement_reaped",
        roles=roles,
        facts={"war": war.event_entity_id, "battles": war.battles},
        son_id=son.id,
    )
    ctx.count("incitements_reaped")
    return toll
