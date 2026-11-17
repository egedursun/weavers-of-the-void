from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.constants.units import PERCENT
from aerona.db.tables.bonds import BondRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.faith import CultDoctrineRow, CultTenetRow
from aerona.db.tables.polity import PolityProfileRow
from aerona.domain.enums.bond import BondKind, BondState
from aerona.domain.enums.entity import EntityStatus, EntityType
from aerona.domain.enums.faith import TenetKind
from aerona.engine.context import TickContext
from aerona.engine.faith.book import patron_node
from aerona.engine.primitives.numbers import clamp_int, round_half_up
from aerona.engine.primitives.stats import shift_stat, stat
from aerona.rules.registry import Rules


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


def sway_of(rules: Rules, doctrine: CultDoctrineRow, zeal: int) -> int:
    table = rules.inquisition
    learned = doctrine.clergy_quality * table.sway_quality_pct / PERCENT
    fervent = zeal * table.sway_zeal_pct / PERCENT
    numerous = min(table.sway_numbers_cap, doctrine.clergy_count * table.sway_per_100_clergy / PERCENT)
    return clamp_int(round_half_up(learned + fervent + numerous), 0, PERCENT)


async def clergy_sway(session: AsyncSession, rules: Rules, polity_id: int) -> int:
    realm = await session.get(PolityProfileRow, polity_id)
    if realm is None or realm.state_religion_id is None:
        return 0
    doctrine = await session.get(CultDoctrineRow, realm.state_religion_id)
    cult = await session.get(EntityRow, realm.state_religion_id)
    if doctrine is None or cult is None or cult.status is not EntityStatus.CANON:
        return 0
    if await session.get(CultTenetRow, (cult.id, TenetKind.DIVINE_RULE)) is not None:
        return 0
    return sway_of(rules, doctrine, stat(cult, "zeal") or 0)
