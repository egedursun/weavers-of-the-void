from collections.abc import Awaitable, Callable, Mapping

from sqlalchemy import select

from aerona.catalog.kinds.fanaticisms import FANATICISMS, fanaticism_order
from aerona.constants.units import PERCENT
from aerona.core.total import total
from aerona.db.tables.bonds import BondRow
from aerona.db.tables.collective import DemographicTransitionRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.faith import CultDoctrineRow, CultHoldingRow, CultOfficeRow, HeresyRow
from aerona.db.tables.means import WrittenWorkRow
from aerona.db.tables.polity import OfficeRow, PolityMemberRow, PolityProfileRow
from aerona.db.tables.settlement import SettlementProfileRow
from aerona.db.write_guard import held, unheld
from aerona.domain.enums.body import HarmCause
from aerona.domain.enums.bond import BondKind, BondState
from aerona.domain.enums.economy import GoodsFlow
from aerona.domain.enums.entity import EngineKind, EntityStatus, EntityType
from aerona.domain.enums.faith import ClergyFunction, FanaticismKind, HoldingKind, TenetKind
from aerona.domain.enums.mind import SkillKind, ValueAxis
from aerona.domain.enums.modifier import IncidentRole
from aerona.domain.enums.polity import OfficeKind
from aerona.domain.enums.society import Commodity
from aerona.domain.enums.war import WarCause
from aerona.engine.body.hits import Harm
from aerona.engine.context import TickContext
from aerona.engine.faith.book import Church, FaithBook, FaithLine, patron_node
from aerona.engine.faith.church import clergy_sway
from aerona.engine.faith.works import credit, spend_devotion
from aerona.engine.law.sentences import banish
from aerona.engine.lifecycle.wounds import apply_hits
from aerona.engine.lore.art import smash
from aerona.engine.mind.book import skill_level, values_for
from aerona.engine.mind.hooks import judged
from aerona.engine.mind.space import value_distance
from aerona.engine.primitives.distance import RegionAtlas
from aerona.engine.primitives.folk import present_among
from aerona.engine.primitives.numbers import clamp_int, round_half_up
from aerona.engine.primitives.queries import active_bonds, close, connect
from aerona.engine.primitives.records import retire_in
from aerona.engine.primitives.society import shift_stock
from aerona.engine.primitives.stats import put_stat, set_stats, shift_stat, stat, stat_or
from aerona.engine.records import death_path
from aerona.engine.services.war import declare_war


async def infidel_neighbour(ctx: TickContext, church: Church, book: FaithBook, atlas: RegionAtlas) -> tuple[EntityRow, EntityRow] | None:
    god = church.god.id if church.god is not None else None
    for member in church.members:
        for other in book.communities.values():
            if other.id == member.id or other.world_id != member.world_id or book.faith.patron(other.id) in {god, None}:
                continue
            if atlas.adjacent(member.id, other.id):
                return member, other
    return None


async def crusade(ctx: TickContext, church: Church, book: FaithBook, atlas: RegionAtlas) -> FaithLine | None:
    pair = await infidel_neighbour(ctx, church, book, atlas)
    if pair is None:
        return None
    member, infidel = pair
    if not await declare_war(ctx, member.id, infidel.id, f"the holy war of {church.cult.name}", cause=WarCause.HOLY_WAR):
        return None
    doctrine = church.doctrine
    realm_id = await ctx.session.scalar(select(PolityMemberRow.polity_entity_id).where(PolityMemberRow.member_entity_id == member.id).limit(1))
    realm = await ctx.session.get(PolityProfileRow, realm_id) if realm_id is not None else None
    if doctrine is not None and realm is not None:
        gift = -credit(doctrine, -round_half_up(doctrine.treasury * ctx.rules.tithes.war_chest_pct / PERCENT))
        realm.war_chest += gift
    return FaithLine("faith.crusade", {IncidentRole.AUTHORITY: church.cult.id, IncidentRole.ACTOR: member.id, IncidentRole.TARGET: infidel.id})


async def heretics(ctx: TickContext, church: Church) -> list[EntityRow]:
    homes = [member.id for member in church.members]
    hunted = list(await ctx.session.scalars(select(HeresyRow).where(HeresyRow.parent_entity_id == church.cult.id, HeresyRow.suppressed.is_(True))))
    sects = [row.heresy_entity_id for row in hunted]
    if not homes or not sects:
        return []
    members = select(BondRow.source_node_id).where(BondRow.target_node_id.in_(sects), BondRow.kind == BondKind.MEMBER_OF, BondRow.state == BondState.ACTIVE)
    return list(
        await ctx.session.scalars(
            select(EntityRow)
            .where(
                EntityRow.entity_type == EntityType.MORTAL,
                EntityRow.status == EntityStatus.CANON,
                await present_among(ctx.session, homes),
                EntityRow.id.in_(members),
            )
            .order_by(EntityRow.id)
        )
    )


async def unbelievers(ctx: TickContext, church: Church) -> list[EntityRow]:
    god = church.god.id if church.god is not None else None
    homes = [member.id for member in church.members]
    if not homes:
        return []
    mortals = await ctx.session.scalars(
        select(EntityRow)
        .where(EntityRow.entity_type == EntityType.MORTAL, EntityRow.status == EntityStatus.CANON, await present_among(ctx.session, homes))
        .order_by(EntityRow.id)
    )
    found = []
    for mortal in mortals:
        faith = await patron_node(ctx.session, mortal.id)
        if faith is not None and faith != god:
            found.append(mortal)
    return found


async def inquisition(ctx: TickContext, church: Church) -> FaithLine | None:
    table = ctx.rules.inquisition
    for mortal in [*await heretics(ctx, church), *await unbelievers(ctx, church)]:
        rng = ctx.rng(f"inquisition.{church.cult.id}.{mortal.id}.{ctx.epoch}")
        if rng.chance(table.execution_chance):
            await death_path(ctx, mortal, f"put to death as a heretic by {church.cult.name}", None, "the inquisition", forced=True, harm=HarmCause.PUNISHMENT)
            return FaithLine("faith.inquisition_execution", {IncidentRole.JUDGE: church.cult.id, IncidentRole.ACCUSED: mortal.id})
        await apply_hits(ctx, mortal, Harm(table.punish_hp, HarmCause.TORTURE, f"questioned by the guardians of doctrine of {church.cult.name}"), lethal=False)
        return FaithLine("faith.inquisition_question", {IncidentRole.JUDGE: church.cult.id, IncidentRole.ACCUSED: mortal.id}, {"harm": table.punish_hp})
    return None


async def iconoclasm(ctx: TickContext, church: Church) -> FaithLine | None:
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
    broken = [work for home in homes for work in await smash(ctx, home, ctx.rules.art.iconoclasm_chance, f"smashed by the iconoclasts of {church.cult.name}")]
    if rival is None:
        return (
            FaithLine("faith.iconoclasm", {IncidentRole.ACTOR: church.cult.id, IncidentRole.TARGET: tuple(work.id for work in broken)}, {"images": len(broken)})
            if broken
            else None
        )
    await retire_in(ctx, rival, f"torn down by the iconoclasts of {church.cult.name}", close_bonds=True)
    place = await ctx.session.get(EntityRow, rival.location_id) if rival.location_id is not None else None
    if place is not None:
        shift_stat(place, "prosperity", -ctx.rules.inquisition.iconoclasm_prosperity)
    return FaithLine(
        "faith.iconoclasm",
        {IncidentRole.ACTOR: church.cult.id, IncidentRole.TARGET: (rival.id, *(work.id for work in broken))},
        {"images": len(broken), "temple": rival.name},
    )


async def followers(ctx: TickContext, church: Church) -> list[EntityRow]:
    god = church.god.id if church.god is not None else None
    homes = [member.id for member in church.members]
    if god is None or not homes:
        return []
    worshippers = select(BondRow.source_node_id).where(BondRow.target_node_id == god, BondRow.kind == BondKind.WORSHIPS, BondRow.state == BondState.ACTIVE)
    found = await ctx.session.scalars(
        select(EntityRow)
        .where(
            EntityRow.entity_type == EntityType.MORTAL,
            EntityRow.status == EntityStatus.CANON,
            await present_among(ctx.session, homes),
            EntityRow.id.in_(worshippers),
        )
        .order_by(EntityRow.id)
    )
    return unheld(list(found))


def reach(ctx: TickContext, people: list[EntityRow]) -> list[EntityRow]:
    free = ctx.rng(f"fanatic_reach.{ctx.epoch}").shuffled(unheld(people))
    return free[: max(1, -(-len(free) * ctx.rules.zeal.fanatic_reach // PERCENT))] if free else []


async def purge(ctx: TickContext, church: Church) -> FaithLine | None:
    expelled = reach(ctx, await heretics(ctx, church))
    for heretic in expelled:
        await banish(ctx, heretic, None)
    if not expelled:
        return None
    return FaithLine(
        "faith.purge", {IncidentRole.AUTHORITY: church.cult.id, IncidentRole.VICTIM: tuple(row.id for row in expelled)}, {"expelled": len(expelled)}
    )


async def forced_conversion(ctx: TickContext, church: Church) -> FaithLine | None:
    if church.god is None:
        return None
    converted = reach(ctx, await unbelievers(ctx, church))
    for mortal in converted:
        for bond in await active_bonds(ctx.session, [BondKind.WORSHIPS], sources=[mortal.id]):
            await close(ctx.session, bond, ctx.epoch, f"forced from their faith by {church.cult.name}")
        await connect(ctx.session, mortal.id, church.god.id, BondKind.WORSHIPS, ctx.epoch, description=f"converted by force by {church.cult.name}")
    if not converted:
        return None
    return FaithLine(
        "faith.forced_conversion",
        {IncidentRole.AUTHORITY: church.cult.id, IncidentRole.PATRON: church.god.id, IncidentRole.VICTIM: tuple(row.id for row in converted)},
        {"converted": len(converted)},
    )


async def martyrdom(ctx: TickContext, church: Church) -> FaithLine | None:
    devout = await followers(ctx, church)
    if not devout:
        return None
    martyr = devout[0]
    await death_path(ctx, martyr, f"gave their life for the faith of {church.cult.name}", None, "martyrdom", forced=True, harm=HarmCause.SACRIFICE)
    table = ctx.rules.zeal
    shift_stat(church.cult, "zeal", table.martyrdom)
    if church.doctrine is None or "devotion" not in church.doctrine.locked:
        set_stats(church.cult, devotion=(stat(church.cult, "devotion") or 0) + table.martyr_devotion)
    return FaithLine("faith.martyrdom", {IncidentRole.SUBJECT: martyr.id, IncidentRole.BENEFICIARY: church.cult.id}, {"zeal": table.martyrdom})


async def mortification(ctx: TickContext, church: Church) -> FaithLine | None:
    table = ctx.rules.zeal
    penitents = reach(ctx, await followers(ctx, church))
    for penitent in penitents:
        await apply_hits(ctx, penitent, Harm(table.mortification_hp, HarmCause.RITUAL, f"mortified the body for the faith of {church.cult.name}"), lethal=False)
    if not penitents:
        return None
    if church.doctrine is None or "devotion" not in church.doctrine.locked:
        set_stats(church.cult, devotion=(stat(church.cult, "devotion") or 0) + table.mortification_devotion * len(penitents))
    return FaithLine(
        "faith.mortification",
        {IncidentRole.AUTHORITY: church.cult.id, IncidentRole.MEMBER: tuple(row.id for row in penitents)},
        {"penitents": len(penitents), "harm": table.mortification_hp},
    )


async def book_burning(ctx: TickContext, church: Church) -> FaithLine | None:
    homes = [member.id for member in unheld(church.members)]
    if not homes:
        return None
    works = list(
        await ctx.session.scalars(
            select(EntityRow)
            .join(WrittenWorkRow, WrittenWorkRow.work_entity_id == EntityRow.id)
            .where(EntityRow.status == EntityStatus.CANON, EntityRow.location_id.in_(homes))
            .order_by(EntityRow.id)
        )
    )
    burned = unheld(works)
    for work in burned:
        await retire_in(ctx, work, f"burned by the fanatics of {church.cult.name}", EntityStatus.DESTROYED)
    if not burned:
        return None
    for home in {work.location_id for work in burned if work.location_id is not None}:
        transition = await ctx.session.get(DemographicTransitionRow, home)
        if transition is not None and "literacy" not in transition.locked:
            transition.literacy = clamp_int(transition.literacy - ctx.rules.zeal.book_burning_literacy, 0, PERCENT)
    return FaithLine(
        "faith.book_burning",
        {IncidentRole.ACTOR: church.cult.id, IncidentRole.TARGET: tuple(work.id for work in burned)},
        {"works": len(burned), "literacy_lost": ctx.rules.zeal.book_burning_literacy},
    )


async def persecution(ctx: TickContext, church: Church) -> FaithLine | None:
    table = ctx.rules.zeal
    harried = reach(ctx, await unbelievers(ctx, church))
    for mortal in harried:
        await apply_hits(ctx, mortal, Harm(table.persecution_hp, HarmCause.TORTURE, f"harried by the fanatics of {church.cult.name}"), lethal=False)
    if not harried:
        return None
    for home_id in {mortal.location_id for mortal in harried if mortal.location_id is not None}:
        town = await ctx.session.get(EntityRow, home_id)
        if town is None or held(town.id):
            continue
        shift_stat(town, "prosperity", -table.persecution_prosperity)
        profile = await ctx.session.get(SettlementProfileRow, town.id)
        if profile is not None and "unrest" not in profile.locked:
            profile.unrest = clamp_int(profile.unrest + table.persecution_unrest, 0, PERCENT)
    return FaithLine(
        "faith.persecution",
        {IncidentRole.ACTOR: church.cult.id, IncidentRole.VICTIM: tuple(row.id for row in harried)},
        {"harried": len(harried), "harm": table.persecution_hp},
    )


async def holy_place(ctx: TickContext, church: Church) -> EntityRow | None:
    target = await ctx.session.scalar(
        select(CultHoldingRow.holding_entity_id)
        .where(CultHoldingRow.cult_entity_id == church.cult.id, CultHoldingRow.kind == HoldingKind.HOLY_PLACE)
        .order_by(CultHoldingRow.holding_entity_id)
        .limit(1)
    )
    place = await ctx.session.get(EntityRow, target) if target is not None else None
    if place is None or place.status is not EntityStatus.CANON:
        return None
    if place.entity_type is EntityType.SETTLEMENT or place.location_id is None:
        return place
    return await ctx.session.get(EntityRow, place.location_id)


async def millenarian_flight(ctx: TickContext, church: Church) -> FaithLine | None:
    leaving = reach(ctx, await followers(ctx, church))
    if not leaving:
        return None
    goal = await holy_place(ctx, church)
    homes = {mortal.location_id for mortal in leaving if mortal.location_id is not None}
    for mortal in leaving:
        if goal is not None and goal.id != mortal.location_id:
            mortal.location_id, mortal.world_id = goal.id, goal.world_id
        else:
            await banish(ctx, mortal, None)
    for home_id in homes:
        town = await ctx.session.get(EntityRow, home_id)
        if town is not None and not held(town.id):
            shift_stat(town, "prosperity", -ctx.rules.zeal.flight_prosperity)
    return FaithLine(
        "faith.millenarian_flight",
        {
            IncidentRole.AUTHORITY: church.cult.id,
            IncidentRole.MEMBER: tuple(row.id for row in leaving),
            **({IncidentRole.DESTINATION: goal.id} if goal is not None else {}),
        },
        {"followers": len(leaving)},
    )


async def charity(ctx: TickContext, church: Church) -> FaithLine | None:
    table = ctx.rules.zeal
    givers = [mortal for mortal in reach(ctx, await followers(ctx, church)) if stat_or(mortal, "wealth", 0) > 0]
    if not givers:
        return None
    given = 0
    for mortal in givers:
        gift = stat_or(mortal, "wealth", 0) * table.charity_share_pct // PERCENT
        put_stat(ctx.rules, mortal, "wealth", stat_or(mortal, "wealth", 0) - gift)
        given += gift
    for home_id in {mortal.location_id for mortal in givers if mortal.location_id is not None}:
        if not held(home_id):
            await shift_stock(ctx.session, ctx.rules, home_id, Commodity.FOOD, table.charity_food, epoch=ctx.epoch, flow=GoodsFlow.AID)
    return FaithLine(
        "faith.charity",
        {IncidentRole.ACTOR: church.cult.id, IncidentRole.MEMBER: tuple(row.id for row in givers)},
        {"givers": len(givers), "given": given},
    )


async def pilgrim_zeal(ctx: TickContext, church: Church) -> FaithLine | None:
    goal = await holy_place(ctx, church)
    leaving = [mortal for mortal in reach(ctx, await followers(ctx, church)) if goal is None or mortal.location_id != goal.id]
    if not leaving:
        return None
    homes = {mortal.location_id for mortal in leaving if mortal.location_id is not None}
    for mortal in leaving:
        put_stat(ctx.rules, mortal, "wealth", 0)
        if goal is not None:
            mortal.location_id, mortal.world_id = goal.id, goal.world_id
    for home_id in homes:
        town = await ctx.session.get(EntityRow, home_id)
        if town is not None and not held(town.id):
            shift_stat(town, "prosperity", -ctx.rules.zeal.pilgrim_prosperity)
    if goal is not None and not held(goal.id):
        shift_stat(goal, "piety", ctx.rules.zeal.pilgrim_piety)
    return FaithLine(
        "faith.pilgrim_zeal",
        {
            IncidentRole.AUTHORITY: church.cult.id,
            IncidentRole.MEMBER: tuple(row.id for row in leaving),
            **({IncidentRole.DESTINATION: goal.id} if goal is not None else {}),
        },
        {"pilgrims": len(leaving)},
    )


FanaticPath = Callable[[TickContext, Church, FaithBook, RegionAtlas], Awaitable[FaithLine | None]]


FANATIC_PATHS: Mapping[FanaticismKind, FanaticPath] = total(
    FanaticismKind,
    {
        FanaticismKind.CRUSADE: crusade,
        FanaticismKind.INQUISITION: lambda ctx, church, _book, _atlas: inquisition(ctx, church),
        FanaticismKind.ICONOCLASM: lambda ctx, church, _book, _atlas: iconoclasm(ctx, church),
        FanaticismKind.PURGE: lambda ctx, church, _book, _atlas: purge(ctx, church),
        FanaticismKind.FORCED_CONVERSION: lambda ctx, church, _book, _atlas: forced_conversion(ctx, church),
        FanaticismKind.MARTYRDOM: lambda ctx, church, _book, _atlas: martyrdom(ctx, church),
        FanaticismKind.CHARITY: lambda ctx, church, _book, _atlas: charity(ctx, church),
        FanaticismKind.PILGRIM_ZEAL: lambda ctx, church, _book, _atlas: pilgrim_zeal(ctx, church),
        FanaticismKind.MORTIFICATION: lambda ctx, church, _book, _atlas: mortification(ctx, church),
        FanaticismKind.BOOK_BURNING: lambda ctx, church, _book, _atlas: book_burning(ctx, church),
        FanaticismKind.PERSECUTION: lambda ctx, church, _book, _atlas: persecution(ctx, church),
        FanaticismKind.MILLENARIAN_FLIGHT: lambda ctx, church, _book, _atlas: millenarian_flight(ctx, church),
    },
)


async def fanaticism(ctx: TickContext, church: Church, book: FaithBook, atlas: RegionAtlas) -> FaithLine | None:
    table = ctx.rules.zeal
    doctrine = church.doctrine
    if doctrine is None or (stat(church.cult, "zeal") or 0) <= table.fanaticism:
        return None
    if not ctx.rng(f"fanatic.{church.cult.id}.{ctx.epoch}").chance(table.fanaticism_chance):
        return None
    if (stat(church.cult, "devotion") or 0) < ctx.rules.doctrine.fanaticism_devotion:
        return None
    order = fanaticism_order(frozenset(church.tenets), doctrine.orthodoxy >= ctx.rules.inquisition.orthodoxy_suppress)
    for kind in order:
        line = await FANATIC_PATHS[kind](ctx, church, book, atlas)
        if line is not None:
            act = FANATICISMS[kind].act
            if act is not None:
                await judged(ctx, church.cult.id, church.cult.id, act)
            spend_devotion(church, ctx.rules.doctrine.fanaticism_devotion)
            if "fanaticism" not in doctrine.locked:
                doctrine.fanaticism, doctrine.fanaticism_epoch = kind, ctx.epoch
            return line
    return None


async def drift(ctx: TickContext, church: Church) -> int:
    doctrine = church.doctrine
    if doctrine is None or not church.members:
        return 0
    doctrine_values = await values_for(ctx.session, church.cult.id)
    distances = [value_distance(doctrine_values, await values_for(ctx.session, member.id)) for member in church.members]
    pressure = sum(distances) / len(distances)
    high = select(CultOfficeRow.holder_entity_id).where(CultOfficeRow.cult_entity_id == church.cult.id, CultOfficeRow.kind == ClergyFunction.LEADER)
    theologian = await ctx.session.scalar(high.limit(1))
    creative = theologian is not None and await skill_level(ctx.session, theologian, SkillKind.THEOLOGY) >= ctx.rules.inquisition.creative_theology
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
    if doctrine is not None and "doctrinal_distance" not in doctrine.locked:
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
        shift_stat(heresy, "influence", -ctx.rules.inquisition.heresy_influence)
        shift_stat(heresy, "zeal", ctx.rules.zeal.persecution)
        struck += 1
    return struck


async def investiture(ctx: TickContext, church: Church) -> FaithLine | None:
    table = ctx.rules.inquisition
    doctrine = church.doctrine
    if doctrine is None or doctrine.clergy_quality < table.strong_clergy or church.holds(TenetKind.DIVINE_RULE):
        return None
    realm = await ctx.session.scalar(
        select(PolityProfileRow).where(PolityProfileRow.state_religion_id == church.cult.id).order_by(PolityProfileRow.polity_entity_id).limit(1)
    )
    if realm is None:
        return None
    sway = await clergy_sway(ctx.session, ctx.rules, realm.polity_entity_id)
    chance = round_half_up(table.investiture_chance * (PERCENT + sway * table.sway_investiture_pct / PERCENT) / PERCENT)
    if not ctx.rng(f"investiture.{church.cult.id}.{ctx.epoch}").chance(chance):
        return None
    ruler_id = await ctx.session.scalar(
        select(OfficeRow.holder_entity_id).where(OfficeRow.polity_entity_id == realm.polity_entity_id, OfficeRow.kind == OfficeKind.RULER)
    )
    ruler = await ctx.session.get(EntityRow, ruler_id) if ruler_id is not None else None
    return await quarrel_with(ctx, church, doctrine, ruler, realm.polity_entity_id) if ruler is not None else None


async def quarrel_with(ctx: TickContext, church: Church, doctrine: CultDoctrineRow, ruler: EntityRow, polity_id: int) -> FaithLine:
    roles: dict[IncidentRole, int | tuple[int, ...]] = {IncidentRole.ACTOR: church.cult.id, IncidentRole.OPPONENT: ruler.id, IncidentRole.TARGET: polity_id}
    zealous = (stat(church.cult, "zeal") or 0) > ctx.rules.zeal.fanaticism
    if zealous and ruler.id not in doctrine.excommunicated and "excommunicated" not in doctrine.locked:
        doctrine.excommunicated = [*doctrine.excommunicated, ruler.id]
        return FaithLine("faith.investiture_excommunication", roles)
    piety = (await values_for(ctx.session, ruler.id)).get(ValueAxis.PIETY, 0)
    if piety > 0:
        return FaithLine("faith.investiture_yielded", roles, {"piety": piety})
    return FaithLine("faith.investiture_standoff", roles, {"piety": piety})


async def monastery_keeps(ctx: TickContext, community_id: int) -> bool:
    return (
        await ctx.session.scalar(
            select(CultHoldingRow.cult_entity_id).where(CultHoldingRow.holding_entity_id == community_id, CultHoldingRow.kind == HoldingKind.MONASTERY).limit(1)
        )
        is not None
    )
