from sqlalchemy import select

from aerona.constants.units import PERCENT
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.genetics import GenomeRow
from aerona.db.tables.intrigue import IdentityRow, SecretRow
from aerona.db.write_guard import held
from aerona.domain.enums.intrigue import IdentityReason, IntrigueSecret
from aerona.domain.enums.mind import Facet
from aerona.engine.context import TickContext
from aerona.engine.intrigue.secrets import expose, keep_secret
from aerona.engine.mind.split import facets_of
from aerona.engine.primitives.numbers import clamp_int

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
    await keep_secret(ctx, mortal.id, IntrigueSecret.FALSE_IDENTITY, source=f"identity.{reason.value}")
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
    masks = await ctx.session.scalars(select(SecretRow).where(SecretRow.holder_node_id == row.mortal_node_id, SecretRow.kind == IntrigueSecret.FALSE_IDENTITY))
    for secret in masks:
        await expose(ctx, secret)
    return True
