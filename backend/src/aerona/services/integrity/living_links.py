from sqlalchemy import delete, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.db.tables.bonds import BondRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.genetics import GenomeRow
from aerona.db.tables.living import LivingLineRow, LivingLineTraitRow, LivingProfileRow, SymbiontRow
from aerona.domain.enums.bond import BondKind, BondState
from aerona.domain.enums.economy import CommodityKind
from aerona.domain.enums.entity import EntityType
from aerona.domain.enums.living import GrowthStage, Metabolism
from aerona.rules.registry import Rules
from aerona.services.integrity.minds_links import run

BODILESS = (EntityType.REGION, EntityType.SETTLEMENT, EntityType.POLITY, EntityType.FACTION, EntityType.CULT, EntityType.LANGUAGE, EntityType.KNOWLEDGE)


async def cap_traits(session: AsyncSession, rules: Rules) -> int:
    cap = rules.genome_design.trait_cap
    mended = 0
    over = await session.execute(
        select(LivingLineTraitRow.line_id).where(LivingLineTraitRow.side_effect.is_(False)).group_by(LivingLineTraitRow.line_id).having(func.count() > cap)
    )
    for (line_id,) in over.all():
        rows = list(
            await session.scalars(
                select(LivingLineTraitRow)
                .where(LivingLineTraitRow.line_id == line_id, LivingLineTraitRow.side_effect.is_(False))
                .order_by(func.abs(LivingLineTraitRow.strength).desc(), LivingLineTraitRow.id)
            )
        )
        for row in rows[cap:]:
            if not row.locked:
                await session.delete(row)
                mended += 1
    return mended


async def copy_source_genomes(session: AsyncSession, epoch: int) -> int:
    mended = 0
    pairs = await session.execute(
        select(BondRow.source_node_id, BondRow.target_node_id).where(BondRow.kind == BondKind.CLONE_OF, BondRow.state == BondState.ACTIVE)
    )
    for clone_id, source_id in pairs.all():
        source = await session.get(GenomeRow, source_id)
        if source is None or await session.get(GenomeRow, clone_id) is not None:
            continue
        session.add(GenomeRow(holder_node_id=clone_id, genes=dict(source.genes), potential=dict(source.potential), beauty=source.beauty, epoch=epoch))
        mended += 1
    return mended


async def mend_living_links(session: AsyncSession, rules: Rules, epoch: int) -> int:
    bodiless = select(EntityRow.id).where(EntityRow.entity_type.in_(BODILESS))
    lines = select(LivingLineRow.id)
    return (
        await run(
            session,
            [
                update(LivingProfileRow)
                .where(LivingProfileRow.health <= 0, LivingProfileRow.growth_stage != GrowthStage.DEAD)
                .values(growth_stage=GrowthStage.DEAD),
                update(LivingProfileRow).where(LivingProfileRow.growth_stage == GrowthStage.DEAD, LivingProfileRow.health > 0).values(health=0),
                update(LivingProfileRow)
                .where(LivingProfileRow.metabolism == Metabolism.FEEDING, LivingProfileRow.feed_commodity.is_(None))
                .values(feed_commodity=CommodityKind.FODDER),
                update(LivingProfileRow).where(LivingProfileRow.line_id.is_not(None), LivingProfileRow.line_id.not_in(lines)).values(line_id=None),
                delete(SymbiontRow).where(SymbiontRow.host_node_id.in_(bodiless)),
            ],
        )
        + await cap_traits(session, rules)
        + await copy_source_genomes(session, epoch)
    )
