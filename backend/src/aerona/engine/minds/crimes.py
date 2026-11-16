from aerona.db.tables.entities import EntityRow
from aerona.db.tables.minds import MindProfileRow
from aerona.domain.enums.constructs import MindWill
from aerona.domain.enums.minds import MindSeat
from aerona.domain.enums.mortal import CrimeKind
from aerona.domain.enums.polity import LawKind
from aerona.engine.context import TickContext
from aerona.engine.minds.continuity import law_for
from aerona.engine.minds.profiles import is_made
from aerona.engine.polity.trials import report_crime
from aerona.engine.sacred.places import town_of

WILLED = frozenset({MindWill.FULL, MindWill.EXCEEDING})
ERASURE_CRIMES = {"regulated": CrimeKind.ERASURE, "destruction": CrimeKind.ERASURE, "killing": CrimeKind.MURDER}


async def mind_crime(ctx: TickContext, culprit_id: int, crime: CrimeKind) -> bool:
    culprit = await ctx.session.get(EntityRow, culprit_id)
    town = await town_of(ctx.session, culprit) if culprit is not None else None
    if town is None:
        return False
    case = await report_crime(ctx, town.id, culprit_id, crime)
    ctx.count(f"mind_crime.{crime.value}")
    return case is not None


async def copying_crime(ctx: TickContext, copier: EntityRow, source: MindProfileRow, seat: MindSeat) -> CrimeKind | None:
    own = copier.id in {source.node_id, source.made_by_node_id}
    if not own and seat is MindSeat.BODY:
        return CrimeKind.IMPERSONATION
    level = await law_for(ctx, copier, LawKind.COPY_LAW, "level")
    if level == "banned" or (level == "licensed" and not own):
        return CrimeKind.UNLICENSED_COPYING
    return None if own else CrimeKind.MIND_THEFT


async def binding_crime(copier: EntityRow, mind: MindProfileRow | None) -> CrimeKind | None:
    if mind is None:
        return None
    if mind.will in WILLED:
        return CrimeKind.FORCED_EDIT
    return None if mind.made_by_node_id == copier.id else CrimeKind.MACHINE_SEIZURE


async def erasure_crime(ctx: TickContext, slayer: EntityRow, victim_id: int) -> CrimeKind | None:
    mind = await ctx.session.get(MindProfileRow, victim_id)
    if mind is None or not is_made(mind) or mind.will is MindWill.NONE:
        return None
    level = await law_for(ctx, slayer, LawKind.ERASURE_LAW, "level") or "regulated"
    if level == "regulated" and mind.made_by_node_id == slayer.id:
        return None
    return ERASURE_CRIMES.get(level)
