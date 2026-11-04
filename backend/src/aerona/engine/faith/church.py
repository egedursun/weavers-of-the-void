from sqlalchemy import select

from aerona.db.tables.bonds import BondRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.faith import CultTenetRow
from aerona.domain.enums.bond import BondKind, BondState
from aerona.domain.enums.entity import EntityStatus, EntityType
from aerona.domain.enums.faith import TenetKind
from aerona.engine.context import TickContext
from aerona.engine.faith.book import patron_node
from aerona.engine.primitives.stats import shift_stat


async def holy_warriors(ctx: TickContext, god_id: int) -> list[EntityRow]:
    worshippers = select(BondRow.source_node_id).where(BondRow.target_node_id == god_id, BondRow.kind == BondKind.WORSHIPS, BondRow.state == BondState.ACTIVE)
    holy = select(CultTenetRow.cult_entity_id).where(CultTenetRow.tenet == TenetKind.HOLY_WAR)
    return list(
        await ctx.session.scalars(
            select(EntityRow).where(
                EntityRow.id.in_(worshippers), EntityRow.id.in_(holy), EntityRow.entity_type == EntityType.CULT, EntityRow.status == EntityStatus.CANON
            )
        )
    )


async def holy_peace(ctx: TickContext, first_id: int, second_id: int) -> int:
    gods = (await patron_node(ctx.session, first_id), await patron_node(ctx.session, second_id))
    if None in gods or gods[0] == gods[1]:
        return 0
    cooled = 0
    for god in gods:
        for cult in await holy_warriors(ctx, god or 0):
            shift_stat(cult, "zeal", -ctx.rules.doctrine.holy_peace_zeal)
            cooled += 1
    return cooled
