from collections.abc import Awaitable, Callable, Mapping

from sqlalchemy import func, select

from aerona.constants.units import PERCENT
from aerona.db.tables.bonds import BondRow
from aerona.db.tables.concealment import PublicKnowledgeRow
from aerona.db.tables.culture import HolderTechniqueRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.living import LivingLineRow
from aerona.db.tables.polity import PolityMemberRow, PolityProfileRow
from aerona.db.tables.powers import PowerSourceRow
from aerona.domain.enums.bond import BondKind
from aerona.domain.enums.cycles import ChallengeKind
from aerona.engine.context import TickContext
from aerona.engine.primitives.numbers import clamp_int

Signal = Callable[[TickContext, PolityProfileRow, list[EntityRow]], Awaitable[int]]


def ids(towns: list[EntityRow]) -> list[int]:
    return [town.id for town in towns]


async def collapse(ctx: TickContext, profile: PolityProfileRow, _towns: list[EntityRow]) -> int:
    return clamp_int((ctx.rules.challenge_response.collapse_below - profile.stability) * 2, 0, PERCENT)


async def secession(ctx: TickContext, profile: PolityProfileRow, towns: list[EntityRow]) -> int:
    restless = await ctx.session.scalar(
        select(func.count())
        .select_from(PolityMemberRow)
        .where(PolityMemberRow.polity_entity_id == profile.polity_entity_id, PolityMemberRow.autonomy >= ctx.rules.revolts.secession_autonomy)
    )
    return clamp_int(int(restless or 0) * PERCENT // max(1, len(towns)), 0, PERCENT)


async def migration_wave(ctx: TickContext, _profile: PolityProfileRow, towns: list[EntityRow]) -> int:
    arrived = await ctx.session.scalar(
        select(func.count())
        .select_from(BondRow)
        .where(BondRow.kind == BondKind.MIGRATED_TO, BondRow.target_node_id.in_(ids(towns)), BondRow.epoch == ctx.epoch)
    )
    return clamp_int(int(arrived or 0) * ctx.rules.challenge_response.signal_step, 0, PERCENT)


async def revelation(ctx: TickContext, _profile: PolityProfileRow, towns: list[EntityRow]) -> int:
    known = await ctx.session.scalar(
        select(func.max(PublicKnowledgeRow.know_pct)).where(
            PublicKnowledgeRow.population_node_id.in_(ids(towns)), PublicKnowledgeRow.revealed_epoch == ctx.epoch
        )
    )
    return int(known or 0)


async def runaway(ctx: TickContext, profile: PolityProfileRow, towns: list[EntityRow]) -> int:
    owners = [profile.polity_entity_id, *ids(towns)]
    loose = await ctx.session.scalar(
        select(func.count()).select_from(LivingLineRow).where(LivingLineRow.escaped.is_(True), LivingLineRow.owner_node_id.in_(owners))
    )
    return clamp_int(int(loose or 0) * ctx.rules.challenge_response.signal_step * 2, 0, PERCENT)


async def source_depletion(ctx: TickContext, profile: PolityProfileRow, towns: list[EntityRow]) -> int:
    scopes = [profile.polity_entity_id, *ids(towns)]
    weakest = await ctx.session.scalar(select(func.min(PowerSourceRow.stability)).where(PowerSourceRow.scope_node_id.in_(scopes)))
    return clamp_int(ctx.rules.challenge_response.depleted_below - int(weakest), 0, PERCENT) * 2 if weakest is not None else 0


async def technological_shock(ctx: TickContext, profile: PolityProfileRow, towns: list[EntityRow]) -> int:
    learned = await ctx.session.scalar(
        select(func.count())
        .select_from(HolderTechniqueRow)
        .where(HolderTechniqueRow.holder_entity_id.in_([profile.polity_entity_id, *ids(towns)]), HolderTechniqueRow.since_epoch == ctx.epoch)
    )
    return clamp_int(int(learned or 0) * ctx.rules.challenge_response.signal_step, 0, PERCENT)


SIGNALS: Mapping[ChallengeKind, Signal] = {
    ChallengeKind.COLLAPSE: collapse,
    ChallengeKind.SECESSION: secession,
    ChallengeKind.MIGRATION_WAVE: migration_wave,
    ChallengeKind.REVELATION: revelation,
    ChallengeKind.RUNAWAY: runaway,
    ChallengeKind.SOURCE_DEPLETION: source_depletion,
    ChallengeKind.TECHNOLOGICAL_SHOCK: technological_shock,
}


async def signalled(ctx: TickContext, profile: PolityProfileRow, towns: list[EntityRow]) -> dict[ChallengeKind, int]:
    return {kind: severity for kind, find in SIGNALS.items() if (severity := await find(ctx, profile, towns)) > 0}
