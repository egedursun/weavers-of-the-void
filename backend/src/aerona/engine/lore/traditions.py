from dataclasses import dataclass

from sqlalchemy import select

from aerona.catalog.lore import TRADITIONS
from aerona.constants.units import PERCENT
from aerona.db.tables.bonds import BondRow
from aerona.db.tables.culture import TraditionParticipationRow, TraditionProfileRow
from aerona.db.tables.demography import PeopleCultureRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.environment import RegionEnvironmentRow
from aerona.db.tables.faith import SpiritProfileRow
from aerona.db.tables.settlement import SettlementProfileRow
from aerona.db.tables.society import CommunitySocietyRow
from aerona.domain.enums.body import HarmCause
from aerona.domain.enums.bond import BondKind, BondState
from aerona.domain.enums.culture import Technique, TraditionKind
from aerona.domain.enums.economy import CommodityKind, GoodsFlow
from aerona.domain.enums.entity import COMMUNITY_TYPES, EngineKind, EntityStatus, EntityType
from aerona.domain.enums.faith import SpiritAlignment
from aerona.domain.enums.mind import MemoryKind, ValueAxis, ValueHolder
from aerona.domain.enums.society import Commodity, SocialClass
from aerona.domain.models.entity_stats import TraditionStats
from aerona.engine.body.hits import Harm
from aerona.engine.context import TickContext
from aerona.engine.economy.stocks import holding
from aerona.engine.interconnect.flows import FlowCategory, flowing
from aerona.engine.lifecycle.wounds import apply_hits
from aerona.engine.lore.research import has_technique
from aerona.engine.mind.book import stored_values, values_for, write_values
from aerona.engine.mind.space import value_distance
from aerona.engine.primitives.distance import RegionAtlas
from aerona.engine.primitives.numbers import clamp_int, round_half_up
from aerona.engine.primitives.queries import connect
from aerona.engine.primitives.records import RecordSpec, create_record
from aerona.engine.primitives.society import shift_stock
from aerona.engine.primitives.stats import headcount, headcount_key, put_stat, set_stats, shift_stat, stat
from aerona.engine.services.community_relations import change_relation

K = TraditionKind
WORDS = (
    (("mourning", "lament", "wake"), K.MOURNING),
    (("funeral", "burial", "pyre"), K.FUNERAL_RITE),
    (("plague",), K.FAST),
    (("remembrance", "victory", "festival", "feast day", "carnival"), K.FESTIVAL),
    (("ancestor",), K.ANCESTOR_FEAST),
    (("harvest", "sowing"), K.HARVEST_RITE),
    (("fast", "lent"), K.FAST),
    (("initiation",), K.INITIATION),
    (("wedding", "marriage"), K.MARRIAGE_RITE),
    (("coming of age", "naming"), K.COMING_OF_AGE),
    (("taboo", "forbidden"), K.TABOO),
    (("offering", "sacrifice"), K.OFFERING),
    (("pilgrimage",), K.PILGRIMAGE),
    (("hospitality", "guest"), K.HOSPITALITY_LAW),
    (("duel", "honour"), K.DUEL_CUSTOM),
    (("war dance", "war-dance", "dance"), K.WAR_DANCE),
    (("scar",), K.SCAR_RITE),
    (("oath", "peace"), K.FESTIVAL),
)
FIT = 50
HUNGRY = 0
MATURITY = 16


@dataclass(frozen=True)
class Keeping:
    weight: float = 1.0
    relief: float = 0.0
    in_season: bool | None = None


def kind_of(tradition: EntityRow) -> TraditionKind:
    text = f"{tradition.name} {tradition.subtype or ''}".lower()
    for words, kind in WORDS:
        if any(word in text for word in words):
            return kind
    return K.FESTIVAL


FEASTS = frozenset({K.FESTIVAL, K.ANCESTOR_FEAST, K.HARVEST_RITE, K.MARRIAGE_RITE, K.COMING_OF_AGE})
GIFTS = frozenset({K.OFFERING, K.PILGRIMAGE, K.FUNERAL_RITE})


def cost_for(ctx: TickContext, kind: TraditionKind) -> dict[str, int]:
    table = ctx.rules.traditions
    if kind in FEASTS:
        return {"food": table.festival_food}
    if kind in GIFTS:
        return {"goods": table.offering_cost}
    return {}


async def profile_of(ctx: TickContext, tradition: EntityRow) -> TraditionProfileRow:
    row = await ctx.session.get(TraditionProfileRow, tradition.id)
    if row is not None:
        return row
    kind = kind_of(tradition)
    spec = TRADITIONS[kind]
    row = TraditionProfileRow(
        tradition_entity_id=tradition.id,
        kind=kind,
        calendar_slot=None,
        cost={**cost_for(ctx, kind), **spec.cost},
        effects=dict(spec.effects),
        taboo_target="livestock" if kind is K.TABOO else None,
        updated_epoch=ctx.epoch,
        locked=[],
    )
    ctx.session.add(row)
    return row


async def celebrants(ctx: TickContext, tradition_id: int) -> list[EntityRow]:
    statement = select(BondRow.source_node_id).where(
        BondRow.target_node_id == tradition_id, BondRow.kind == BondKind.CELEBRATES, BondRow.state == BondState.ACTIVE
    )
    ids = sorted(set(await ctx.session.scalars(statement)))
    rows = await ctx.session.scalars(
        select(EntityRow).where(EntityRow.id.in_(ids), EntityRow.status == EntityStatus.CANON, EntityRow.entity_type.in_(list(COMMUNITY_TYPES)))
    )
    return list(rows)


async def participate(ctx: TickContext, tradition: EntityRow, community: EntityRow) -> TraditionParticipationRow:
    row = await ctx.session.get(TraditionParticipationRow, (tradition.id, community.id))
    if row is None:
        row = TraditionParticipationRow(
            tradition_entity_id=tradition.id, community_entity_id=community.id, participation=PERCENT // 2, since_epoch=ctx.epoch, skipped=0
        )
        ctx.session.add(row)
    table = ctx.rules.traditions
    spec = TRADITIONS[(await profile_of(ctx, tradition)).kind]
    culture = await values_for(ctx.session, community.id)
    fit = value_distance({axis: value * 10 for axis, value in spec.values.items()}, culture) if spec.values and culture else FIT
    row.participation = clamp_int(row.participation + (table.participation_gain if fit < FIT else -table.participation_decay), 0, PERCENT)
    return row


async def cohere(ctx: TickContext, community: EntityRow, step: int) -> None:
    culture = await ctx.session.get(PeopleCultureRow, community.id)
    if culture is not None:
        culture.cohesion = clamp_int(culture.cohesion + step, 0, PERCENT)


async def push_values(ctx: TickContext, community: EntityRow, values: dict[ValueAxis, int], weight: float) -> None:
    stored = await stored_values(ctx.session, ValueHolder.CULTURE, community.id)
    if not stored:
        return
    for axis, value in values.items():
        stored[axis] = stored.get(axis, 0) + round_half_up(value * weight)
    await write_values(ctx.session, ValueHolder.CULTURE, community.id, stored)


async def feast(ctx: TickContext, community: EntityRow, row: TraditionProfileRow, share: float, relief: float = 0.0) -> bool:
    society = await ctx.session.get(CommunitySocietyRow, community.id)
    food = round_half_up(row.cost.get("food", 0) * max(0.0, 1 - relief))
    if food and society is not None and society.stock_food <= HUNGRY:
        await cohere(ctx, community, -ctx.rules.traditions.skipped_cohesion)
        return False
    if food:
        await shift_stock(ctx.session, ctx.rules, community.id, Commodity.FOOD, -round_half_up(food * share), epoch=ctx.epoch, flow=GoodsFlow.CONSUMPTION)
    goods = row.cost.get("goods", 0)
    if goods:
        await shift_stock(ctx.session, ctx.rules, community.id, Commodity.GOODS, -round_half_up(goods * share), epoch=ctx.epoch, flow=GoodsFlow.OFFERING)
    return True


async def scar_youths(ctx: TickContext, community: EntityRow, tradition: EntityRow) -> int:
    youths = await ctx.session.scalars(
        select(EntityRow)
        .where(EntityRow.entity_type == EntityType.MORTAL, EntityRow.status == EntityStatus.CANON, EntityRow.location_id == community.id)
        .order_by(EntityRow.id)
    )
    marked = 0
    for youth in youths:
        if (stat(youth, "age") or 0) != MATURITY:
            continue
        if ctx.rng(f"scar_rite.{tradition.id}.{youth.id}.{ctx.epoch}").chance(ctx.rules.traditions.scar_rite_chance):
            await apply_hits(ctx, youth, Harm(4, HarmCause.QUEST, f"marked by {tradition.name}", part="face"), lethal=False)
            marked += 1
    return marked


async def placate(ctx: TickContext, community: EntityRow) -> int:
    mortals = select(EntityRow.id).where(EntityRow.location_id == community.id, EntityRow.entity_type == EntityType.MORTAL)
    spirits = await ctx.session.scalars(select(SpiritProfileRow).where(SpiritProfileRow.origin_mortal_id.in_(mortals)))
    calmed = 0
    for profile in spirits:
        spirit = await ctx.session.get(EntityRow, profile.spirit_entity_id)
        if spirit is None or spirit.status is not EntityStatus.CANON:
            continue
        set_stats(spirit, unrest=clamp_int((stat(spirit, "unrest") or 0) - ctx.rules.traditions.ancestor_feast_placation, 0, PERCENT))
        profile.veneration = clamp_int(profile.veneration + ctx.rules.traditions.ancestor_feast_placation, 0, PERCENT)
        if profile.alignment is SpiritAlignment.VENGEFUL and (stat(spirit, "unrest") or 0) < ctx.rules.spirits.vengeful_unrest:
            profile.alignment = SpiritAlignment.NEUTRAL
        calmed += 1
    return calmed


async def welcome(ctx: TickContext, community: EntityRow, atlas: RegionAtlas) -> bool:
    region_id = atlas.top_region(community.id)
    region = await ctx.session.get(EntityRow, region_id) if region_id is not None else None
    if region is None:
        return False
    shift_stat(region, "danger", -ctx.rules.traditions.hospitality_danger)
    return True


async def bless_harvest(ctx: TickContext, community: EntityRow, atlas: RegionAtlas) -> bool:
    region_id = atlas.top_region(community.id)
    land = await ctx.session.get(RegionEnvironmentRow, region_id) if region_id is not None else None
    if land is None:
        return False
    land.harvest_pct = clamp_int(land.harvest_pct + ctx.rules.traditions.piety, 0, PERCENT * 2)
    return True


async def wed(ctx: TickContext, community: EntityRow) -> int:
    population = headcount(community)
    born = round_half_up(population * ctx.rules.traditions.marriage_fertility_pct / PERCENT / PERCENT)
    if born <= 0:
        return 0
    with flowing(FlowCategory.BIRTH):
        put_stat(ctx.rules, community, headcount_key(community), population + born)
    return born


async def gladden(ctx: TickContext, community: EntityRow) -> None:
    society = await ctx.session.get(CommunitySocietyRow, community.id)
    if society is None:
        return
    step = ctx.rules.traditions.festival_satisfaction
    for social_class in SocialClass:
        key = f"satisfaction_{social_class.value}"
        setattr(society, key, clamp_int(getattr(society, key) + step, 0, PERCENT))


async def rest(ctx: TickContext, community: EntityRow, share: float) -> None:
    table = ctx.rules.seasonal
    town = await ctx.session.get(SettlementProfileRow, community.id)
    if town is not None and "unrest" not in town.locked:
        town.unrest = clamp_int(town.unrest - round_half_up(table.siesta_unrest * share), 0, PERCENT)
    society = await ctx.session.get(CommunitySocietyRow, community.id)
    if society is not None:
        for social_class in SocialClass:
            key = f"satisfaction_{social_class.value}"
            setattr(society, key, clamp_int(getattr(society, key) + round_half_up(table.siesta_satisfaction * share), 0, PERCENT))
    shift_stat(community, "prosperity", -round_half_up(table.siesta_prosperity * share), 0)


async def keep_vigil(ctx: TickContext, community: EntityRow, share: float) -> None:
    table = ctx.rules.seasonal
    town = await ctx.session.get(SettlementProfileRow, community.id)
    if town is not None and "crime" not in town.locked:
        town.crime = clamp_int(town.crime - round_half_up(table.vigil_crime * share), 0, PERCENT)
    await push_values(ctx, community, {ValueAxis.PIETY: table.vigil_piety}, share)
    await placate(ctx, community)


async def observe(ctx: TickContext, kind: TraditionKind, tradition: EntityRow, community: EntityRow, atlas: RegionAtlas, *, share: float) -> None:
    table = ctx.rules.traditions
    if kind in {K.FESTIVAL, K.COMING_OF_AGE, K.MOURNING, K.HARVEST_RITE, K.INITIATION}:
        await cohere(ctx, community, round_half_up(table.festival_cohesion * share))
    if kind is K.FESTIVAL:
        await gladden(ctx, community)
    if kind is K.FAST:
        await shift_stock(ctx.session, ctx.rules, community.id, Commodity.FOOD, table.fast_food, epoch=ctx.epoch, flow=GoodsFlow.PRODUCTION)
    if kind in {K.INITIATION, K.SCAR_RITE}:
        await scar_youths(ctx, community, tradition)
    if kind is K.HOSPITALITY_LAW:
        await welcome(ctx, community, atlas)
    if kind is K.HARVEST_RITE:
        await bless_harvest(ctx, community, atlas)
    if kind is K.MARRIAGE_RITE:
        await wed(ctx, community)
    if kind is K.ANCESTOR_FEAST:
        await placate(ctx, community)
    if kind is K.WAR_DANCE:
        await push_values(ctx, community, {ValueAxis.MARTIAL: table.war_dance_martial}, share)
    if kind in {K.OFFERING, K.PILGRIMAGE, K.FAST}:
        await push_values(ctx, community, {ValueAxis.PIETY: table.piety}, share)
    if kind is K.SIESTA:
        await rest(ctx, community, share)
    if kind is K.NIGHT_VIGIL:
        await keep_vigil(ctx, community, share)


async def celebrate(ctx: TickContext, tradition: EntityRow, community: EntityRow, atlas: RegionAtlas, keeping: Keeping | None = None) -> str | None:
    row = await profile_of(ctx, tradition)
    part = await participate(ctx, tradition, community)
    keeping = keeping or Keeping()
    counted = 1 + ctx.rules.technique_effects.calendar_pct / PERCENT if await has_technique(ctx.session, community.id, Technique.CALENDAR) else 1.0
    share = min(1.0, part.participation / PERCENT * counted) * keeping.weight
    row.in_season = keeping.in_season
    if not await feast(ctx, community, row, share, keeping.relief):
        part.skipped += 1
        return "skipped"
    part.last_celebrated_epoch = ctx.epoch
    spec = TRADITIONS[row.kind]
    if spec.values:
        await push_values(ctx, community, spec.values, share)
    await observe(ctx, row.kind, tradition, community, atlas, share=share)
    return row.kind.value


async def taboos(ctx: TickContext, community_id: int) -> set[str]:
    traditions = select(BondRow.target_node_id).where(
        BondRow.source_node_id == community_id, BondRow.kind == BondKind.CELEBRATES, BondRow.state == BondState.ACTIVE
    )
    rows = await ctx.session.scalars(
        select(TraditionProfileRow.taboo_target).where(TraditionProfileRow.tradition_entity_id.in_(traditions), TraditionProfileRow.kind == K.TABOO)
    )
    return {row for row in rows if row}


async def resent_taboo(ctx: TickContext, community_id: int) -> int:
    held = {commodity for commodity in CommodityKind if commodity.value in await taboos(ctx, community_id)}
    if not held:
        return 0
    resented = 0
    roads = await ctx.session.scalars(
        select(BondRow).where(
            BondRow.kind == BondKind.TRADES_WITH,
            BondRow.state == BondState.ACTIVE,
            (BondRow.source_node_id == community_id) | (BondRow.target_node_id == community_id),
        )
    )
    for road in list(roads):
        partner = road.other_end(community_id)
        if any([await holding(ctx.session, partner, commodity) > 0 for commodity in held]):
            await change_relation(ctx, community_id, partner, -ctx.rules.traditions.taboo_infamy, MemoryKind.ILL_WILL, note="trades in what is taboo")
            resented += 1
    return resented


async def keeps(ctx: TickContext, community_id: int, kind: TraditionKind) -> bool:
    traditions = select(BondRow.target_node_id).where(
        BondRow.source_node_id == community_id, BondRow.kind == BondKind.CELEBRATES, BondRow.state == BondState.ACTIVE
    )
    found = await ctx.session.scalar(
        select(TraditionProfileRow.tradition_entity_id)
        .where(TraditionProfileRow.tradition_entity_id.in_(traditions), TraditionProfileRow.kind == kind)
        .limit(1)
    )
    return found is not None


MOURNED = frozenset({EngineKind.PLAGUE, EngineKind.FAMINE, EngineKind.FLOOD, EngineKind.EARTHQUAKE, EngineKind.SIEGE})
HAILED = frozenset({EngineKind.BATTLE, EngineKind.WAR})


async def commemorate(ctx: TickContext, event: EntityRow) -> EntityRow | None:
    if event.engine_kind not in MOURNED | HAILED or event.location_id is None:
        return None
    if (stat(event, "severity") or 0) < ctx.rules.deep_life.legend_event_min_severity:
        return None
    if not ctx.rng(f"commemoration.{event.id}").chance(ctx.rules.traditions.commemoration_chance):
        return None
    kind = K.MOURNING if event.engine_kind in MOURNED else K.FESTIVAL
    word = "Mourning" if kind is K.MOURNING else "Feast"
    tradition = await create_record(
        ctx,
        RecordSpec(
            name=f"The {word} of {event.name}",
            entity_type=EntityType.TRADITION,
            stats=TraditionStats(spread=PERCENT // 5, rigidity=PERCENT // 4),
            body=f"Kept each year in memory of {event.name}.",
            power=2,
            world_id=event.world_id,
            location_id=event.location_id,
        ),
    )
    row = await profile_of(ctx, tradition)
    row.kind, row.origin_entity_id = kind, event.id
    row.cost = {**cost_for(ctx, kind), **TRADITIONS[kind].cost}
    keepers = await ctx.session.scalars(
        select(EntityRow.id).where(EntityRow.id == event.location_id, EntityRow.entity_type.in_(list(COMMUNITY_TYPES)), EntityRow.status == EntityStatus.CANON)
    )
    for keeper in list(keepers):
        await connect(ctx.session, keeper, tradition.id, BondKind.CELEBRATES, ctx.epoch, description="in remembrance")
    await connect(ctx.session, tradition.id, event.id, BondKind.TELLS_OF, ctx.epoch, description="remembers")
    return tradition
