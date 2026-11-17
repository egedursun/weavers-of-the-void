from dataclasses import dataclass

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.core.errors import ConflictError
from aerona.core.grammar import several, spoken
from aerona.db.repositories.sons import SonRepository
from aerona.db.tables.foreign_gods import GodConflictRow
from aerona.db.tables.sons import SonPowerRow, SonRow
from aerona.domain.enums.body import DamageType, HarmCause
from aerona.domain.enums.chronicle import ChronicleKind
from aerona.domain.enums.divine import WoundCause
from aerona.domain.enums.son import PowerEffect, SonStatus, Stat
from aerona.domain.enums.war import GodConflictOutcome
from aerona.engine.body.hits import Harm
from aerona.engine.context import TickContext
from aerona.engine.divine.decrees import truce_in_force
from aerona.engine.divine.wounds import name_exposure, strike
from aerona.engine.gods.progress import Progress, cap_gained_essence, grant_progress
from aerona.engine.lifecycle.wounds import apply_hits
from aerona.engine.primitives.numbers import round_half_up
from aerona.engine.primitives.transfers import move_amount

ARENA_STATS = (Stat.STRENGTH, Stat.WISDOM, Stat.CUNNING, Stat.CHARISMA, Stat.WILL)


@dataclass(frozen=True)
class DuelResult:
    winner_id: int
    loser_id: int
    challenger_score: int
    defender_score: int
    text: str
    progress: Progress


async def _power(session: AsyncSession, son_id: int, effect: PowerEffect, stat: Stat | None = None) -> bool:
    statement = select(SonPowerRow).where(SonPowerRow.son_id == son_id, SonPowerRow.effect == effect)
    return any(stat is None or row.param_stat is None or row.param_stat is stat for row in await session.scalars(statement))


async def _score(ctx: TickContext, son: SonRow, rival: SonRow, stat: Stat) -> int:
    tools = ctx.rules.son_tools
    bonus = tools.challenge_power_bonus if await _power(ctx.session, son.id, PowerEffect.DUEL_MASTER, stat) else 0
    bonus -= tools.challenge_untouchable if await _power(ctx.session, rival.id, PowerEffect.UNTOUCHABLE) else 0
    die = ctx.rng(f"duel.{son.id}.{rival.id}").die(tools.challenge_die)
    exposed = await name_exposure(ctx.session, son.id, ctx.rules.divine_wounds.name_exposure_pct)
    return round_half_up((son.stat(stat) + die * tools.challenge_die_mult + son.level * tools.challenge_strength_per_level + bonus) * exposed)


BODILY_STATS = frozenset({Stat.STRENGTH, Stat.ENDURANCE, Stat.AGILITY, Stat.MIGHT})


async def son_duel(ctx: TickContext, challenger: SonRow, defender: SonRow, stat: Stat, reason: str) -> DuelResult:
    if await truce_in_force(ctx):
        raise ConflictError("A cosmic truce of the council forbids duels between gods.")
    tools = ctx.rules.son_tools
    first, second = await _score(ctx, challenger, defender, stat), await _score(ctx, defender, challenger, stat)
    winner, loser = (challenger, defender) if first >= second else (defender, challenger)
    wound = tools.challenge_min_wound + round(abs(first - second) / tools.challenge_wound_diff_divisor)
    damage_type = None if stat in BODILY_STATS else DamageType.MAGIC
    await apply_hits(ctx, loser, Harm(wound, HarmCause.DUEL, "fell in a trial of the gods", damage_type=damage_type, source_node_id=winner.id))
    loser.fame = max(0, loser.fame - tools.challenge_loser_renown_loss)
    stolen = min(tools.challenge_max_steal, loser.essence)
    before = winner.essence
    if not move_amount(loser, winner, "essence", stolen):
        stolen = 0
    cap_gained_essence(ctx.rules, winner, before)
    outcome_text = f"{winner.name} won ({first}-{second}); {loser.name} lost {wound} HP and had {stolen} essence snatched."
    text = f'{challenger.name} challenged {defender.name} to a trial of {spoken(stat)} ("{reason}"). {outcome_text}'
    if loser.hp <= 0:
        loser.status = SonStatus.ASLEEP
        reviving = await _power(ctx.session, loser.id, PowerEffect.REVIVING)
        loser.sleep_epochs_left = tools.reviving_sleep_epochs if reviving else tools.challenge_sleep_epochs
        text += f" {loser.name} collapsed and fell into a sleep that will last {several(loser.sleep_epochs_left, 'epoch', 'epochs')}."
    outcome = GodConflictOutcome.ATTACKER_WON if winner.id == challenger.id else GodConflictOutcome.DEFENDER_WON
    ctx.session.add(
        GodConflictRow(
            epoch=ctx.epoch,
            attacker_node_id=challenger.id,
            defender_node_id=defender.id,
            outcome=outcome,
            attacker_score=first,
            defender_score=second,
            duel=True,
        )
    )
    await SonRepository(ctx.session).change_relation(challenger.id, defender.id, -tools.challenge_relation)
    await ctx.chronicle(ChronicleKind.CHALLENGE, text, template_key="pantheon.duel", son_id=challenger.id)
    progress = await grant_progress(ctx, winner, xp=tools.challenge_xp, fame=tools.challenge_renown)
    await strike(ctx, loser, winner.id, WoundCause.DUEL, abs(first - second))
    return DuelResult(winner.id, loser.id, first, second, text, progress)


async def duel_history(session: AsyncSession, first: int, second: int, limit: int) -> list[GodConflictRow]:
    statement = (
        select(GodConflictRow)
        .where(
            GodConflictRow.duel.is_(True),
            or_(
                (GodConflictRow.attacker_node_id == first) & (GodConflictRow.defender_node_id == second),
                (GodConflictRow.attacker_node_id == second) & (GodConflictRow.defender_node_id == first),
            ),
        )
        .order_by(GodConflictRow.id.desc())
        .limit(limit)
    )
    return list(await session.scalars(statement))


def duel_winner(row: GodConflictRow) -> int:
    return row.attacker_node_id if row.outcome is GodConflictOutcome.ATTACKER_WON else row.defender_node_id
