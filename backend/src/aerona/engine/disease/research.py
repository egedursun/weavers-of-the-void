from dataclasses import dataclass

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.constants.units import PERCENT
from aerona.db.tables.disease import DiseaseCureRow, OutbreakRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.evolution import CureResearchRow
from aerona.db.tables.mind import SkillRow
from aerona.db.tables.structures import StructureProfileRow
from aerona.db.write_guard import held
from aerona.domain.enums.discovery import TheoryDomain
from aerona.domain.enums.disease import CureSource, OutbreakStatus
from aerona.domain.enums.entity import EntityStatus, EntityType
from aerona.domain.enums.mind import SkillKind
from aerona.domain.enums.structure import STANDING_STATES, StructureKind
from aerona.engine.context import TickContext
from aerona.engine.economy.purse import give_coin, take_coin
from aerona.engine.lore.research_depth import trade_partners
from aerona.engine.lore.truth import ruling_truths
from aerona.engine.notes import note
from aerona.engine.primitives.distance import RegionAtlas
from aerona.engine.primitives.folk import present_among
from aerona.engine.primitives.stats import shift_bounded

SEATS_OF_LEARNING = (StructureKind.HOSPITAL, StructureKind.ACADEMY, StructureKind.MONASTERY)
PRESTIGE = "prestige"


@dataclass
class ResearchTally:
    started: int = 0
    cured: int = 0
    passed: int = 0


async def institutions(session: AsyncSession) -> list[EntityRow]:
    return list(
        await session.scalars(
            select(EntityRow)
            .join(StructureProfileRow, StructureProfileRow.structure_entity_id == EntityRow.id)
            .where(
                EntityRow.status == EntityStatus.CANON,
                StructureProfileRow.kind.in_(list(SEATS_OF_LEARNING)),
                StructureProfileRow.construction_state.in_(list(STANDING_STATES)),
            )
            .order_by(EntityRow.id)
        )
    )


async def scholars_of(session: AsyncSession, community_id: int, skill: int) -> int:
    return int(
        await session.scalar(
            select(func.count())
            .select_from(SkillRow)
            .join(EntityRow, EntityRow.id == SkillRow.holder_node_id)
            .where(
                SkillRow.skill == SkillKind.MEDICINE,
                SkillRow.level >= skill,
                EntityRow.entity_type == EntityType.MORTAL,
                EntityRow.status == EntityStatus.CANON,
                await present_among(session, [community_id]),
            )
        )
        or 0
    )


async def found_cure(ctx: TickContext, row: CureResearchRow, institution: EntityRow) -> None:
    row.cured_epoch = ctx.epoch
    holder = await ctx.session.get(EntityRow, institution.location_id) if institution.location_id is not None else None
    disease = await ctx.session.get(EntityRow, row.disease_entity_id)
    if holder is None or disease is None:
        return
    if await ctx.session.get(DiseaseCureRow, (disease.id, holder.id)) is None:
        ctx.session.add(DiseaseCureRow(disease_entity_id=disease.id, community_entity_id=holder.id, source=CureSource.KNOWLEDGE, since_epoch=ctx.epoch))
    shift_bounded(ctx.rules, holder, PRESTIGE, ctx.rules.cure_research.prestige)
    await note(
        ctx, f"The learned of {institution.name} found a cure for {disease.name}.", key="disease.cure_found", ids=[institution.id, holder.id, disease.id]
    )


async def study(ctx: TickContext, tally: ResearchTally) -> None:
    table = ctx.rules.cure_research
    atlas = await RegionAtlas.load(ctx.session)
    truths = await ruling_truths(ctx.session, TheoryDomain.MEDICINE)
    sick: dict[int, set[int]] = {}
    for outbreak in await ctx.session.scalars(select(OutbreakRow).where(OutbreakRow.status != OutbreakStatus.ENDED)):
        sick.setdefault(outbreak.region_entity_id, set()).add(outbreak.disease_entity_id)
    for institution in await institutions(ctx.session):
        if held(institution.id) or institution.location_id is None:
            continue
        region = atlas.top_region(institution.id)
        for disease_id in sorted(sick.get(region or -1, set())):
            if await ctx.session.get(CureResearchRow, (institution.id, disease_id)) is None:
                ctx.session.add(
                    CureResearchRow(
                        institution_entity_id=institution.id, disease_entity_id=disease_id, points=0, specimens=0, started_epoch=ctx.epoch, locked=[]
                    )
                )
                tally.started += 1
        await ctx.session.flush()
        scholars = await scholars_of(ctx.session, institution.location_id, table.scholar_skill)
        theory = 1 + table.theory_pct / PERCENT if truths.get(institution.location_id, 0) >= ctx.rules.carriers.theory_truth else 1.0
        for row in list(await ctx.session.scalars(select(CureResearchRow).where(CureResearchRow.institution_entity_id == institution.id))):
            if row.cured_epoch is not None or held(row.disease_entity_id):
                continue
            specimen = row.disease_entity_id in sick.get(region or -1, set())
            if specimen and "specimens" not in row.locked:
                row.specimens += 1
            if "points" not in row.locked:
                row.points += round((scholars * table.per_scholar + (table.specimen if specimen else 0)) * theory)
            if row.points >= table.threshold:
                await found_cure(ctx, row, institution)
                tally.cured += 1


async def spread_cures(ctx: TickContext, tally: ResearchTally) -> None:
    table = ctx.rules.cure_research
    for cure in list(
        await ctx.session.scalars(
            select(DiseaseCureRow)
            .where(DiseaseCureRow.source == CureSource.KNOWLEDGE)
            .order_by(DiseaseCureRow.disease_entity_id, DiseaseCureRow.community_entity_id)
        )
    ):
        holder = await ctx.session.get(EntityRow, cure.community_entity_id)
        if holder is None or held(holder.id):
            continue
        for partner_id in sorted(await trade_partners(ctx.session, holder.id)):
            if held(partner_id) or await ctx.session.get(DiseaseCureRow, (cure.disease_entity_id, partner_id)) is not None:
                continue
            if not ctx.rng(f"cure_trade.{cure.disease_entity_id}.{holder.id}.{partner_id}").chance(table.diffusion_pct):
                continue
            buyer = await ctx.session.get(EntityRow, partner_id)
            if buyer is None or not await take_coin(ctx.session, ctx.rules, buyer, table.price):
                continue
            await give_coin(ctx.session, ctx.rules, holder, table.price)
            ctx.session.add(
                DiseaseCureRow(disease_entity_id=cure.disease_entity_id, community_entity_id=partner_id, source=CureSource.KNOWLEDGE, since_epoch=ctx.epoch)
            )
            tally.passed += 1
            await note(
                ctx, f"{buyer.name} bought the cure that {holder.name} holds.", key="disease.cure_sold", ids=[buyer.id, holder.id, cure.disease_entity_id]
            )
    await ctx.session.flush()


async def research_cures(ctx: TickContext, tally: ResearchTally) -> None:
    await study(ctx, tally)
    await ctx.session.flush()
    await spread_cures(ctx, tally)
