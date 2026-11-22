from sqlalchemy import delete, select, update

from aerona.catalog.life_traits import PUNISHMENT_KIND_TRAITS, having
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.minds import MindProfileRow, MindStateRow, MindWillChangeRow
from aerona.db.tables.networks import NetworkNodeRow
from aerona.domain.enums.constructs import MindWill
from aerona.domain.enums.life_traits import PunishmentKindTrait
from aerona.domain.enums.minds import WillCause
from aerona.domain.enums.mortal import PunishmentKind
from aerona.domain.enums.polity import LawKind
from aerona.engine.context import TickContext
from aerona.engine.minds.continuity import law_for
from aerona.engine.minds.profiles import WILL_ORDER, is_made, will_rank
from aerona.engine.primitives.numbers import clamp_percent
from aerona.engine.primitives.records import retire_in

MIND_PUNISHMENTS = having(PUNISHMENT_KIND_TRAITS, PunishmentKindTrait.MIND_PUNISHMENTS)


async def forced_edit(ctx: TickContext, mind: MindProfileRow) -> None:
    table = ctx.rules.mind_law
    if "drift_pct" not in mind.locked:
        mind.drift_pct = clamp_percent(mind.drift_pct + table.edit_drift)
    if "stability" not in mind.locked:
        mind.stability = clamp_percent(mind.stability - table.edit_stability)
    if "will" not in mind.locked and will_rank(mind.will) > will_rank(MindWill.INSTRUCTED):
        lower = WILL_ORDER[will_rank(mind.will) - 1]
        ctx.session.add(MindWillChangeRow(mind_node_id=mind.node_id, from_will=mind.will, to_will=lower, cause=WillCause.DAMAGE, epoch=ctx.epoch))
        mind.will = lower


async def suffer_in_mind(ctx: TickContext, culprit: EntityRow, punishment: PunishmentKind, judge_id: int | None) -> PunishmentKind:
    mind = await ctx.session.get(MindProfileRow, culprit.id)
    made = mind is not None and is_made(mind)
    if mind is None or (not made and punishment is not PunishmentKind.SEAT_CONFINEMENT):
        return PunishmentKind.IMPRISONMENT
    if punishment is PunishmentKind.FORCED_DORMANCY:
        if "dormant" in mind.locked:
            return PunishmentKind.IMPRISONMENT
        mind.dormant = True
    elif punishment is PunishmentKind.FORCED_EDIT:
        await forced_edit(ctx, mind)
    elif punishment is PunishmentKind.SEAT_CONFINEMENT:
        if "transferable" not in mind.locked:
            mind.transferable = False
        await ctx.session.execute(delete(NetworkNodeRow).where(NetworkNodeRow.member_node_id == culprit.id))
    elif punishment is PunishmentKind.STATE_SEIZURE:
        owned = select(MindStateRow.id).where(MindStateRow.owner_node_id == culprit.id)
        if await ctx.session.scalar(owned.limit(1)) is None:
            return PunishmentKind.FINE
        await ctx.session.execute(update(MindStateRow).where(MindStateRow.owner_node_id == culprit.id).values(owner_node_id=judge_id))
    elif punishment is PunishmentKind.ERASURE:
        if await law_for(ctx, culprit, LawKind.ERASURE_LAW, "level") not in {"permitted", "regulated"}:
            return PunishmentKind.IMPRISONMENT
        await retire_in(ctx, culprit, "erased by the law")
    return punishment
