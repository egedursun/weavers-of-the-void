from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.db.fixups import fixup_due
from aerona.db.tables.bonds import BondRow
from aerona.db.tables.cosmos import AppliedFixupRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.mortal import MortalProfileRow
from aerona.db.tables.polity import TreatyClauseRow
from aerona.db.tables.relations import RelationshipRow
from aerona.db.write_guard import held
from aerona.domain.enums.bond import BondKind, BondState
from aerona.domain.enums.entity import EntityStatus
from aerona.domain.enums.mind import ActKind, MemoryKind
from aerona.domain.enums.modifier import IncidentRole
from aerona.domain.enums.polity import ClauseKind
from aerona.domain.enums.relations import RelationType
from aerona.engine.context import TickContext
from aerona.engine.mind.ethics import conscience
from aerona.engine.mind.memories import remember
from aerona.engine.mortal.kin import fosterers_of
from aerona.engine.mortal.kinship import close_between, foster
from aerona.engine.mortal.life import young
from aerona.engine.primitives.queries import active_bonds
from aerona.engine.recording.record import record
from aerona.engine.relations.book import ensure_relation, relation, shift

R = RelationType


@dataclass
class TieTally:
    told: int = 0
    broken: int = 0
    oaths_broken: int = 0
    fostered: int = 0


async def tell_ties(ctx: TickContext, row: RelationshipRow, before: set[RelationType], after: set[RelationType], tally: TieTally) -> None:
    if row.holder_node_id > row.subject_node_id:
        return
    gained = after - before
    roles = {IncidentRole.ACTOR: row.holder_node_id, IncidentRole.TARGET: row.subject_node_id}
    if R.BETROTHED in gained:
        await record(ctx, "relation.betrothed", roles=roles)
        tally.told += 1
    if R.SWORN_KIN in gained:
        await record(ctx, "relation.sworn", roles=roles)
        tally.told += 1
    if R.FOSTER in gained:
        await record(ctx, "relation.fostered", roles=roles)
        tally.told += 1


async def grieve_houses(ctx: TickContext, first: int, second: int) -> None:
    loss = ctx.rules.relations.betrothal_break_grievance
    for holder, subject in ((first, second), (second, first)):
        row = await ensure_relation(ctx.session, holder, subject, ctx.epoch)
        if row is not None:
            shift(ctx.rules, row, ctx.epoch, friendship=-loss, rivalry=loss)
        await remember(ctx.session, ctx.rules, holder_id=holder, subject_id=subject, kind=MemoryKind.ILL_WILL, magnitude=-loss, epoch=ctx.epoch)


async def alive(ctx: TickContext, node_id: int) -> bool:
    entity = await ctx.session.get(EntityRow, node_id)
    return entity is not None and entity.status is EntityStatus.CANON


async def keep_promises(ctx: TickContext, tally: TieTally) -> None:
    at = ctx.rules.relations.betrothal_break_at
    promises = await ctx.session.scalars(select(BondRow).where(BondRow.kind == BondKind.BETROTHED_TO, BondRow.state == BondState.ACTIVE).order_by(BondRow.id))
    for bond in list(promises):
        first, second = bond.source_node_id, bond.target_node_id
        if held(first, second):
            continue
        living = await alive(ctx, first) and await alive(ctx, second)
        mine, theirs = await relation(ctx.session, first, second), await relation(ctx.session, second, first)
        soured = any(row is not None and row.friendship <= at for row in (mine, theirs))
        if living and not soured:
            continue
        await close_between(ctx.session, first, second, (BondKind.BETROTHED_TO,), epoch=ctx.epoch, reason="the promise was broken" if living else "death")
        if not living:
            continue
        await grieve_houses(ctx, first, second)
        await record(
            ctx,
            "relation.betrothal_broken",
            roles={IncidentRole.ACTOR: first, IncidentRole.TARGET: second},
            facts={"grievance": ctx.rules.relations.betrothal_break_grievance},
        )
        tally.broken += 1


async def keep_sworn_oaths(ctx: TickContext, tally: TieTally) -> None:
    oaths = await ctx.session.scalars(select(BondRow).where(BondRow.kind == BondKind.SWORN_KIN, BondRow.state == BondState.ACTIVE).order_by(BondRow.id))
    for bond in list(oaths):
        first, second = bond.source_node_id, bond.target_node_id
        if held(first, second):
            continue
        for breaker, wronged in ((first, second), (second, first)):
            row = await relation(ctx.session, breaker, wronged)
            if row is None or R.ENEMY.value not in row.kinds:
                continue
            await close_between(ctx.session, first, second, (BondKind.SWORN_KIN,), epoch=ctx.epoch, reason="the oath of kinship was broken")
            await conscience(ctx, breaker, ActKind.OATHBREAKING, wronged)
            await remember(
                ctx.session,
                ctx.rules,
                holder_id=wronged,
                subject_id=breaker,
                kind=MemoryKind.BROKE_OATH,
                magnitude=-ctx.rules.relations.sworn_kin_duty,
                epoch=ctx.epoch,
            )
            await record(ctx, "relation.sworn_broken", roles={IncidentRole.ACTOR: breaker, IncidentRole.TARGET: wronged})
            tally.oaths_broken += 1
            break


async def keep_ties(ctx: TickContext) -> TieTally:
    tally = TieTally()
    tally.fostered = await backfill_fosterage(ctx.session, ctx.epoch)
    await keep_promises(ctx, tally)
    await keep_sworn_oaths(ctx, tally)
    return tally


async def foster_hostage(session: AsyncSession, hostage: EntityRow, house_id: int, epoch: int) -> bool:
    profile = await session.get(MortalProfileRow, hostage.id)
    if profile is None or not young(profile.life_stage) or held(hostage.id):
        return False
    rulers = await active_bonds(session, [BondKind.RULES], targets=[house_id])
    fosterer = rulers[0].source_node_id if rulers else None
    if fosterer is None or fosterer == hostage.id or fosterer in await fosterers_of(session, hostage.id):
        return False
    await foster(session, hostage.id, fosterer, epoch, description="raised as a hostage in another house")
    return True


FOSTER_FIXUP = "relations.w52"


async def backfill_fosterage(session: AsyncSession, epoch: int) -> int:
    if not await fixup_due(session, FOSTER_FIXUP):
        return 0
    fostered = 0
    clauses = await session.scalars(select(TreatyClauseRow).where(TreatyClauseRow.kind == ClauseKind.HOSTAGE).order_by(TreatyClauseRow.id))
    for clause in clauses:
        key = clause.params.get("mortal_id", clause.params.get("hostage"))
        hostage = await session.get(EntityRow, int(key)) if key is not None else None
        if hostage is not None and clause.beneficiary_node_id is not None and hostage.location_id == clause.beneficiary_node_id:
            fostered += await foster_hostage(session, hostage, clause.beneficiary_node_id, epoch)
    session.add(AppliedFixupRow(key=FOSTER_FIXUP, result={"fostered": fostered}))
    await session.flush()
    return fostered
