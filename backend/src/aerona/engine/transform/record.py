from sqlalchemy import select

from aerona.catalog.transformations import TRANSFORMS
from aerona.core.grammar import spoken
from aerona.db.tables.node import NodeRow
from aerona.db.tables.sons import SonRow
from aerona.db.tables.transform import TransformationRow, TransformProspectRow
from aerona.domain.enums.modifier import IncidentRole
from aerona.domain.enums.transform import ProspectStance, TransformKind, TransformTrigger
from aerona.engine.context import TickContext
from aerona.engine.recording.record import record
from aerona.engine.transform.ledger import Ledger


async def name_of(ctx: TickContext, node_id: int | None) -> str | None:
    node = await ctx.session.get(NodeRow, node_id) if node_id is not None else None
    return node.name if node is not None else None


async def blocked(ctx: TickContext, kind: TransformKind, subject_id: int) -> bool:
    stance = await ctx.session.scalar(
        select(TransformProspectRow.stance).where(TransformProspectRow.kind == kind, TransformProspectRow.subject_node_id == subject_id)
    )
    return stance is ProspectStance.BLOCKED


async def record_transformation(
    ctx: TickContext,
    kind: TransformKind,
    subject_id: int | None,
    result_id: int | None,
    *,
    trigger: TransformTrigger = TransformTrigger.ENGINE,
    ledger: Ledger | None = None,
) -> TransformationRow:
    subject = await name_of(ctx, subject_id) or ""
    result = await name_of(ctx, result_id)
    ids = [node for node in (subject_id, result_id) if node is not None]
    sons = [node for node in ids if await ctx.session.get(SonRow, node) is not None]
    write = await record(
        ctx,
        f"transform.{kind.value}",
        roles={IncidentRole.SUBJECT: subject_id, IncidentRole.PRODUCT: result_id},
        facts={"subject_name": subject or spoken(TRANSFORMS[kind].source), "result_name": result or spoken(TRANSFORMS[kind].target)},
        son_id=sons[0] if sons else None,
    )
    row = TransformationRow(
        kind=kind,
        epoch=ctx.epoch,
        trigger=trigger,
        subject_node_id=subject_id,
        result_node_id=result_id,
        subject_name=subject,
        result_name=result,
        incident_id=write.incident_id,
        undo=list(ledger.steps) if ledger is not None else [],
        locked=[],
    )
    ctx.session.add(row)
    ctx.count("transformations")
    await ctx.session.flush()
    return row
