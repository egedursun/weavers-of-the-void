from sqlalchemy import select

from aerona.catalog.pacts import IDENTITY_REASONS
from aerona.constants.units import PERCENT
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.genetics import GenomeRow
from aerona.db.tables.intrigue import IdentityRow, SecretRow
from aerona.db.write_guard import held
from aerona.domain.enums.intrigue import IdentityReason
from aerona.domain.enums.mind import Facet
from aerona.domain.enums.modifier import IncidentRole
from aerona.engine.context import TickContext
from aerona.engine.intrigue.secrets import expose, keep_secret
from aerona.engine.mind.split import facets_of
from aerona.engine.primitives.numbers import clamp_int
from aerona.engine.recording.record import record

EXPOSURE = "exposure"
CAREFREE_AT = -10
TEN = 10


async def assume(
    ctx: TickContext, mortal: EntityRow, reason: IdentityReason, false_name: str, *, cover_role: str | None = None, community_id: int | None = None
) -> IdentityRow | None:
    if held(mortal.id) or await ctx.session.get(IdentityRow, mortal.id) is not None:
        return None
    row = IdentityRow(
        mortal_node_id=mortal.id,
        false_name=false_name,
        cover_role=cover_role,
        community_node_id=community_id,
        reason=reason,
        exposure=0,
        since_epoch=ctx.epoch,
        locked=[],
    )
    ctx.session.add(row)
    await keep_secret(ctx, mortal.id, IDENTITY_REASONS[reason].secret, source=f"identity.{reason.value}")
    await ctx.session.flush()
    return row


async def tend_identity(ctx: TickContext, row: IdentityRow) -> bool:
    if row.exposed_epoch is not None or EXPOSURE in (row.locked or []) or held(row.mortal_node_id):
        return False
    table = ctx.rules.intrigue
    facets = await facets_of(ctx.session, row.mortal_node_id)
    slip = table.identity_slip if facets.get(Facet.CAUTION, 0) < CAREFREE_AT else 0
    genome = await ctx.session.get(GenomeRow, row.mortal_node_id)
    look = (genome.recognisability // TEN) * table.identity_look if genome is not None else 0
    row.exposure = clamp_int(row.exposure + slip + look, 0, PERCENT)
    if row.exposure < PERCENT:
        return False
    row.exposed_epoch = ctx.epoch
    kind = IDENTITY_REASONS[row.reason].secret
    masks = await ctx.session.scalars(select(SecretRow).where(SecretRow.holder_node_id == row.mortal_node_id, SecretRow.kind == kind).order_by(SecretRow.id))
    for secret in list(masks):
        await expose(ctx, secret)
    await record(ctx, "identity.exposed", roles={IncidentRole.SUBJECT: row.mortal_node_id}, facts={"reason": row.reason, "false_name": row.false_name})
    return True
