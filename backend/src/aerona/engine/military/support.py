from sqlalchemy import func, select

from aerona.constants.units import PERCENT
from aerona.db.tables.communication import APPROVAL_MAX, PublicOpinionRow
from aerona.db.tables.culture import ArtworkProfileRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.polity import OfficeRow, PolityMemberRow, PolityProfileRow
from aerona.db.tables.settlement import SettlementProfileRow
from aerona.db.tables.warfare import CasusBelliRow, WarRow, WarSideRow
from aerona.domain.enums.communication import OpinionSubject
from aerona.domain.enums.mind import ValueAxis
from aerona.domain.enums.polity import DecisionRule, OfficeKind
from aerona.domain.enums.war import WarSide
from aerona.engine.context import TickContext
from aerona.engine.mind.book import values_for
from aerona.engine.primitives.numbers import clamp_int, round_half_up
from aerona.engine.primitives.stats import stat

ASSEMBLIES = frozenset({DecisionRule.ASSEMBLY, DecisionRule.COUNCIL})


async def tax_burden(ctx: TickContext, entity_id: int) -> int:
    town = await ctx.session.get(SettlementProfileRow, entity_id)
    rate = town.tax_rate if town is not None else 0
    return round_half_up(ctx.rules.war_finance.war_tax_weariness * rate / max(1, PERCENT // 10))


async def realm_of(ctx: TickContext, entity_id: int) -> int | None:
    if await ctx.session.get(PolityProfileRow, entity_id) is not None:
        return entity_id
    return await ctx.session.scalar(select(PolityMemberRow.polity_entity_id).where(PolityMemberRow.member_entity_id == entity_id).limit(1))


async def propaganda(ctx: TickContext, entity_id: int) -> int:
    table = ctx.rules.war_conduct
    works = await ctx.session.scalar(
        select(func.count()).select_from(ArtworkProfileRow).where(ArtworkProfileRow.propaganda.is_(True), ArtworkProfileRow.patron_entity_id == entity_id)
    )
    realm = await realm_of(ctx, entity_id)
    heralds = 0
    if realm is not None:
        heralds = int(
            await ctx.session.scalar(
                select(func.count())
                .select_from(OfficeRow)
                .where(OfficeRow.polity_entity_id == realm, OfficeRow.kind == OfficeKind.HERALD, OfficeRow.holder_entity_id.is_not(None))
            )
            or 0
        )
    return min(table.propaganda_cap, (int(works or 0) + heralds) * table.propaganda_support)


async def war_opinion(ctx: TickContext, entity_id: int) -> float:
    found = await ctx.session.scalar(
        select(func.avg(PublicOpinionRow.approval)).where(PublicOpinionRow.community_node_id == entity_id, PublicOpinionRow.subject == OpinionSubject.WAR)
    )
    return float(found or 0) / APPROVAL_MAX


async def justification(ctx: TickContext, war: WarRow, side: WarSideRow) -> int:
    table = ctx.rules.war_conduct
    if side.side is not WarSide.ATTACKER:
        return 0
    if not war.justified:
        return -table.unjustified_support
    cause = await ctx.session.get(CasusBelliRow, war.casus_belli_id) if war.casus_belli_id is not None else None
    return round_half_up((cause.justification if cause is not None else PERCENT) * table.justification_support_pct / PERCENT)


async def support_aim(ctx: TickContext, war: WarRow, side: WarSideRow, *, dead: int, maimed: int, occupied: int) -> int:
    table = ctx.rules.war_conduct
    entity = await ctx.session.get(EntityRow, side.entity_id)
    population = (stat(entity, "population") or 0) if entity is not None else 0
    kinship = max(0, (await values_for(ctx.session, side.entity_id)).get(ValueAxis.KINSHIP, 0)) / PERCENT
    losses = dead / max(1, population) * PERCENT * table.casualty_support_pct / PERCENT * (1 + kinship)
    aim = (
        table.support_start
        + (table.defence_support if side.side is WarSide.DEFENDER else 0)
        + await justification(ctx, war, side)
        + await war_opinion(ctx, side.entity_id) * table.opinion_support_pct
        + await propaganda(ctx, side.entity_id)
        - losses
        - await tax_burden(ctx, side.entity_id) * table.tax_support_pct / PERCENT
        - maimed // 100 * table.maimed_support
        - occupied * table.occupation_support
    )
    return clamp_int(round_half_up(aim), 0, PERCENT)


async def rally_support(ctx: TickContext, war: WarRow, side: WarSideRow, *, dead: int, maimed: int, occupied: int) -> int:
    if "support" in side.locked:
        return side.support
    aim = await support_aim(ctx, war, side, dead=dead, maimed=maimed, occupied=occupied)
    side.support = clamp_int(side.support + round_half_up((aim - side.support) * ctx.rules.war_conduct.support_drift_pct / PERCENT), 0, PERCENT)
    return side.support


async def peace_pressure(ctx: TickContext, side: WarSideRow) -> int:
    table = ctx.rules.war_conduct
    gap = max(0, table.support_neutral - side.support)
    pressure = gap * table.support_peace_pct / PERCENT
    realm = await realm_of(ctx, side.entity_id)
    profile = await ctx.session.get(PolityProfileRow, realm) if realm is not None else None
    if profile is not None and profile.decision_rule in ASSEMBLIES:
        pressure *= table.assembly_peace_pct / PERCENT
    return round_half_up(pressure)


async def support_of(ctx: TickContext, war_id: int | None, entity_id: int) -> int | None:
    if war_id is None:
        return None
    side = await ctx.session.get(WarSideRow, (war_id, entity_id))
    return side.support if side is not None else None


def reluctance(rules_pct: int, support: int | None, neutral: int) -> float:
    if support is None or neutral <= 0:
        return 0.0
    return rules_pct / PERCENT * max(0, neutral - support) / neutral


def new_side(ctx: TickContext, war_id: int, entity_id: int, side: WarSide) -> WarSideRow:
    return WarSideRow(war_id=war_id, entity_id=entity_id, side=side, joined_epoch=ctx.epoch, support=ctx.rules.war_conduct.support_start, locked=[])
