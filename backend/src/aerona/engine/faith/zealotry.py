from sqlalchemy import select

from aerona.constants.units import PERCENT
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.faith import CultDoctrineRow, CultHoldingRow, CultOfficeRow, HeresyRow
from aerona.db.tables.polity import OfficeRow, PolityMemberRow, PolityProfileRow
from aerona.domain.enums.body import HarmCause
from aerona.domain.enums.entity import EngineKind, EntityStatus, EntityType
from aerona.domain.enums.faith import ClergyOffice, FanaticismKind, HoldingKind, TenetKind
from aerona.domain.enums.mind import SkillKind, ValueAxis
from aerona.domain.enums.polity import OfficeKind
from aerona.domain.enums.war import WarCause
from aerona.engine.body.hits import Harm
from aerona.engine.context import TickContext
from aerona.engine.faith.book import Church, FaithBook, patron_node
from aerona.engine.lifecycle.wounds import apply_hits
from aerona.engine.mind.book import skill_level, values_for
from aerona.engine.mind.space import value_distance
from aerona.engine.primitives.distance import RegionAtlas
from aerona.engine.primitives.numbers import clamp_int, round_half_up
from aerona.engine.primitives.records import retire_in
from aerona.engine.primitives.stats import shift_stat, stat
from aerona.engine.records import death_path
from aerona.engine.services.war import declare_war

CREATIVE_THEOLOGY = 60
STRONG_CLERGY = 50


async def infidel_neighbour(ctx: TickContext, church: Church, book: FaithBook, atlas: RegionAtlas) -> tuple[EntityRow, EntityRow] | None:
    god = church.god.id if church.god is not None else None
    for member in church.members:
        for other in book.communities.values():
            if other.id == member.id or other.world_id != member.world_id or book.faith.patron(other.id) in {god, None}:
                continue
            if atlas.adjacent(member.id, other.id):
                return member, other
    return None


async def crusade(ctx: TickContext, church: Church, book: FaithBook, atlas: RegionAtlas) -> str | None:
    pair = await infidel_neighbour(ctx, church, book, atlas)
    if pair is None:
        return None
    member, infidel = pair
    if not await declare_war(ctx, member.id, infidel.id, f"the holy war of {church.cult.name}", cause=WarCause.FOREIGN_GOD):
        return None
    doctrine = church.doctrine
    realm_id = await ctx.session.scalar(select(PolityMemberRow.polity_entity_id).where(PolityMemberRow.member_entity_id == member.id).limit(1))
    realm = await ctx.session.get(PolityProfileRow, realm_id) if realm_id is not None else None
    if doctrine is not None and realm is not None:
        gift = round_half_up(doctrine.treasury * ctx.rules.tithes.war_chest_pct / PERCENT)
        doctrine.treasury -= gift
        realm.war_chest += gift
    return f"{church.cult.name} preached a holy war; {member.name} took up arms against the unbelievers of {infidel.name}."


async def inquisition(ctx: TickContext, church: Church) -> str | None:
    table = ctx.rules.inquisition
    god = church.god.id if church.god is not None else None
    homes = [member.id for member in church.members]
    if not homes:
        return None
    mortals = await ctx.session.scalars(
        select(EntityRow)
        .where(EntityRow.entity_type == EntityType.MORTAL, EntityRow.status == EntityStatus.CANON, EntityRow.location_id.in_(homes))
        .order_by(EntityRow.id)
    )
    for mortal in mortals:
        faith = await patron_node(ctx.session, mortal.id)
        if faith is None or faith == god:
            continue
        rng = ctx.rng(f"inquisition.{church.cult.id}.{mortal.id}.{ctx.epoch}")
        if rng.chance(table.execution_chance):
            await death_path(ctx, mortal, f"burned as a heretic by {church.cult.name}", None, "the inquisition", forced=True, harm=HarmCause.PUNISHMENT)
            return f"The inquisitors of {church.cult.name} burned {mortal.name} as a heretic."
        await apply_hits(ctx, mortal, Harm(table.punish_hp, HarmCause.TORTURE, f"questioned by the inquisitors of {church.cult.name}"), lethal=False)
        return f"The inquisitors of {church.cult.name} put {mortal.name} to the question."
    return None


async def iconoclasm(ctx: TickContext, church: Church) -> str | None:
    homes = [member.id for member in church.members]
    if not homes:
        return None
    ours = select(CultHoldingRow.holding_entity_id).where(CultHoldingRow.cult_entity_id == church.cult.id)
    rival = await ctx.session.scalar(
        select(EntityRow)
        .where(EntityRow.engine_kind == EngineKind.TEMPLE, EntityRow.status == EntityStatus.CANON, EntityRow.location_id.in_(homes), EntityRow.id.not_in(ours))
        .order_by(EntityRow.id)
        .limit(1)
    )
    if rival is None:
        return None
    await retire_in(ctx, rival, f"torn down by the iconoclasts of {church.cult.name}", close_bonds=True)
    place = await ctx.session.get(EntityRow, rival.location_id) if rival.location_id is not None else None
    if place is not None:
        shift_stat(place, "prosperity", -ctx.rules.inquisition.iconoclasm_prosperity)
    return f"The iconoclasts of {church.cult.name} tore down {rival.name}."


async def fanaticism(ctx: TickContext, church: Church, book: FaithBook, atlas: RegionAtlas) -> str | None:
    table = ctx.rules.zeal
    doctrine = church.doctrine
    if doctrine is None or (stat(church.cult, "zeal") or 0) <= table.fanaticism:
        return None
    if not ctx.rng(f"fanatic.{church.cult.id}.{ctx.epoch}").chance(table.fanaticism_chance):
        return None
    order = [FanaticismKind.CRUSADE] if church.holds(TenetKind.HOLY_WAR) else []
    order += [FanaticismKind.INQUISITION] if doctrine.orthodoxy >= ctx.rules.inquisition.orthodoxy_suppress else []
    order += [FanaticismKind.ICONOCLASM, FanaticismKind.INQUISITION, FanaticismKind.CRUSADE]
    for kind in dict.fromkeys(order):
        if kind is FanaticismKind.CRUSADE and church.holds(TenetKind.PACIFISM):
            continue
        text = await (
            crusade(ctx, church, book, atlas)
            if kind is FanaticismKind.CRUSADE
            else inquisition(ctx, church)
            if kind is FanaticismKind.INQUISITION
            else iconoclasm(ctx, church)
        )
        if text is not None:
            doctrine.fanaticism, doctrine.fanaticism_epoch = kind, ctx.epoch
            return text
    return None


async def drift(ctx: TickContext, church: Church) -> int:
    doctrine = church.doctrine
    if doctrine is None or not church.members:
        return 0
    doctrine_values = await values_for(ctx.session, church.cult.id)
    distances = [value_distance(doctrine_values, await values_for(ctx.session, member.id)) for member in church.members]
    pressure = sum(distances) / len(distances)
    high = select(CultOfficeRow.holder_entity_id).where(CultOfficeRow.cult_entity_id == church.cult.id, CultOfficeRow.kind == ClergyOffice.HIGH_PRIEST)
    theologian = await ctx.session.scalar(high.limit(1))
    creative = theologian is not None and await skill_level(ctx.session, theologian, SkillKind.THEOLOGY) >= CREATIVE_THEOLOGY
    step = ctx.rules.inquisition.drift_rate * (2 if creative else 1)
    if "doctrinal_distance" not in doctrine.locked:
        doctrine.doctrinal_distance = clamp_int(
            max(doctrine.doctrinal_distance - step // 2, round_half_up(pressure / 2)) + (step if pressure > PERCENT // 4 else 0), 0, PERCENT
        )
    return doctrine.doctrinal_distance


async def record_heresy(ctx: TickContext, heresy: EntityRow, parent_id: int) -> HeresyRow:
    doctrine = await ctx.session.get(CultDoctrineRow, parent_id)
    distance = doctrine.doctrinal_distance if doctrine is not None else 0
    suppressed = doctrine is not None and doctrine.orthodoxy >= ctx.rules.inquisition.orthodoxy_suppress
    row = HeresyRow(
        heresy_entity_id=heresy.id, parent_entity_id=parent_id, distance=distance, declared_epoch=ctx.epoch, suppressed=suppressed, tolerated=not suppressed
    )
    ctx.session.add(row)
    if doctrine is not None:
        doctrine.doctrinal_distance = 0
    return row


async def drifted(ctx: TickContext, cult_id: int) -> bool:
    doctrine = await ctx.session.get(CultDoctrineRow, cult_id)
    return doctrine is not None and doctrine.doctrinal_distance >= ctx.rules.inquisition.drift_heresy


async def suppress(ctx: TickContext, church: Church) -> int:
    rows = list(await ctx.session.scalars(select(HeresyRow).where(HeresyRow.parent_entity_id == church.cult.id, HeresyRow.suppressed.is_(True))))
    struck = 0
    for row in rows:
        heresy = await ctx.session.get(EntityRow, row.heresy_entity_id)
        if heresy is None or heresy.status is not EntityStatus.CANON:
            continue
        shift_stat(heresy, "influence", -ctx.rules.inquisition.punish_hp // 4)
        shift_stat(heresy, "zeal", ctx.rules.zeal.persecution)
        struck += 1
    return struck


async def investiture(ctx: TickContext, church: Church) -> str | None:
    table = ctx.rules.inquisition
    doctrine = church.doctrine
    if doctrine is None or doctrine.clergy_quality < STRONG_CLERGY:
        return None
    realm = await ctx.session.scalar(
        select(PolityProfileRow).where(PolityProfileRow.state_religion_id == church.cult.id).order_by(PolityProfileRow.polity_entity_id).limit(1)
    )
    if realm is None or not ctx.rng(f"investiture.{church.cult.id}.{ctx.epoch}").chance(table.investiture_chance):
        return None
    ruler_id = await ctx.session.scalar(
        select(OfficeRow.holder_entity_id).where(OfficeRow.polity_entity_id == realm.polity_entity_id, OfficeRow.kind == OfficeKind.RULER)
    )
    ruler = await ctx.session.get(EntityRow, ruler_id) if ruler_id is not None else None
    if ruler is None:
        return None
    if (stat(church.cult, "zeal") or 0) > ctx.rules.zeal.fanaticism and ruler.id not in doctrine.excommunicated:
        doctrine.excommunicated = [*doctrine.excommunicated, ruler.id]
        return f"{church.cult.name} and {ruler.name} quarrelled over who appoints the priests; the high priest cast the ruler out of the faith."
    piety = (await values_for(ctx.session, ruler.id)).get(ValueAxis.PIETY, 0)
    return f"{church.cult.name} and {ruler.name} quarrelled over who appoints the priests" + ("; the ruler bowed." if piety > 0 else "; neither yielded.")


async def heresy_parents(ctx: TickContext) -> set[int]:
    return set(await ctx.session.scalars(select(HeresyRow.parent_entity_id)))


async def monastery_keeps(ctx: TickContext, community_id: int) -> bool:
    return (
        await ctx.session.scalar(
            select(CultHoldingRow.cult_entity_id).where(CultHoldingRow.holding_entity_id == community_id, CultHoldingRow.kind == HoldingKind.MONASTERY).limit(1)
        )
        is not None
    )
