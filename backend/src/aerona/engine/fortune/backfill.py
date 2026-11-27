from sqlalchemy import select

from aerona.db.fixups import fixup_due
from aerona.db.tables.bonds import BondRow
from aerona.db.tables.cosmos import AppliedFixupRow
from aerona.db.tables.fortune import FortuneSourceRow
from aerona.db.write_guard import held
from aerona.domain.enums.bond import BondKind, BondState
from aerona.domain.enums.fortune import FortuneSourceKind
from aerona.engine.context import TickContext

LEGACY_FIXUP = "fortune.legacy_backfill"
JUDGEMENTS = ((BondKind.BLESSED, FortuneSourceKind.BLESSING, 1), (BondKind.CURSED, FortuneSourceKind.CURSE, -1))


async def divine_judgements(ctx: TickContext) -> int:
    made = 0
    rows = await ctx.session.execute(select(FortuneSourceRow.holder_node_id, FortuneSourceRow.giver_node_id, FortuneSourceRow.kind))
    given: set[tuple[int, int | None, FortuneSourceKind]] = {(holder, giver, kind) for holder, giver, kind in rows.all()}
    for bond_kind, source_kind, sign in JUDGEMENTS:
        bonds = await ctx.session.execute(
            select(BondRow.source_node_id, BondRow.target_node_id).where(BondRow.kind == bond_kind, BondRow.state == BondState.ACTIVE).order_by(BondRow.id)
        )
        for giver, holder in bonds.all():
            if held(holder) or (holder, giver, source_kind) in given:
                continue
            ctx.session.add(
                FortuneSourceRow(
                    holder_node_id=holder,
                    kind=source_kind,
                    strength=sign * ctx.rules.fortune.blessing_strength,
                    giver_node_id=giver,
                    until_epoch=None,
                    since_epoch=ctx.epoch,
                    locked=[],
                )
            )
            given.add((holder, giver, source_kind))
            made += 1
    return made


async def keep_judgements(ctx: TickContext) -> int:
    return await divine_judgements(ctx)


async def legacy_backfill(ctx: TickContext) -> int:
    if not await fixup_due(ctx.session, LEGACY_FIXUP):
        return 0
    result = {"judgements": await divine_judgements(ctx)}
    ctx.session.add(AppliedFixupRow(key=LEGACY_FIXUP, result=result))
    await ctx.session.flush()
    return sum(result.values())
