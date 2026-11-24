from collections.abc import Awaitable, Callable
from dataclasses import dataclass

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.catalog.calendar_slots import SLOTS
from aerona.catalog.lore import ABSORBABLE, FUNCTIONS, SLOT_NAMED, TRADITIONS, slot_fit, tradition_spec
from aerona.catalog.named_years import NAMED_YEARS
from aerona.constants.units import PERCENT
from aerona.core.dispatch import Handlers
from aerona.db.read_memo import memo_of, memoized, table_names
from aerona.db.tables.bonds import BondRow
from aerona.db.tables.collective import CommemorationRow
from aerona.db.tables.cosmos import AppliedFixupRow
from aerona.db.tables.culture import TraditionEffectRow, TraditionParticipationRow, TraditionProfileRow
from aerona.db.tables.demography import PeopleCultureRow
from aerona.db.tables.ecology import SpeciesRangeRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.environment import NotableYearRow, RegionEnvironmentRow
from aerona.db.tables.faith import SpiritProfileRow
from aerona.db.tables.interconnect import IncidentParticipantRow, IncidentRow
from aerona.db.tables.lore import ChronicleEntityRow, ChronicleRow
from aerona.db.tables.mortal import MortalProfileRow
from aerona.db.tables.settlement import SettlementProfileRow
from aerona.db.tables.society import CommunitySocietyRow
from aerona.db.write_guard import held
from aerona.domain.enums.body import HarmCause
from aerona.domain.enums.bond import BondKind, BondState
from aerona.domain.enums.chronicle import ChronicleKind
from aerona.domain.enums.culture import CalendarSlot, CustomCatalog, Technique, TraditionEffectKind, TraditionFunction
from aerona.domain.enums.economy import CommodityKind, GoodsFlow
from aerona.domain.enums.entity import COMMUNITY_TYPES, EngineKind, EntityStatus, EntityType
from aerona.domain.enums.faith import SpiritAlignment
from aerona.domain.enums.mind import ActKind, MemoryKind, ThoughtKind, ValueAxis, ValueHolder
from aerona.domain.enums.modifier import IncidentRole
from aerona.domain.enums.region import DangerSource
from aerona.domain.enums.society import Commodity, SocialClass
from aerona.domain.models.entity_stats import TraditionStats
from aerona.engine.body.hits import Harm
from aerona.engine.context import TickContext
from aerona.engine.economy.stocks import holding, holdings
from aerona.engine.environment.dangers import ease_danger
from aerona.engine.environment.harvest_harm import shift_harvest
from aerona.engine.interconnect.flows import FlowCategory, flowing
from aerona.engine.lifecycle.wounds import apply_hits
from aerona.engine.lore.calendar_slots import slot_open
from aerona.engine.lore.kinds import TraditionKindParams, kind_of, params_of
from aerona.engine.lore.research import has_technique
from aerona.engine.mind.book import stored_values, values_for, write_values
from aerona.engine.mind.hooks import judged
from aerona.engine.mind.space import value_distance
from aerona.engine.mind.thoughts import think
from aerona.engine.primitives.distance import RegionAtlas
from aerona.engine.primitives.folk import folk_of
from aerona.engine.primitives.numbers import clamp_int, round_half_up
from aerona.engine.primitives.queries import connect
from aerona.engine.primitives.records import RecordSpec, create_record
from aerona.engine.primitives.society import shift_stock
from aerona.engine.primitives.stats import headcount, headcount_key, put_stat, set_stats, shift_stat, stat
from aerona.engine.recording.record import record
from aerona.engine.services.community_relations import change_relation

K = TraditionFunction
E = TraditionEffectKind
FIT = 50
HUNGRY = 0
MATURITY = 16
VALUE_SCALE = 10


TABOO_TABLES = table_names((BondRow, TraditionProfileRow))


@dataclass(frozen=True)
class Keeping:
    weight: float = 1.0
    relief: float = 0.0
    in_season: bool | None = None


SCARRING = frozenset({K.BODY_MARKING})
AXES = frozenset(axis.value for axis in ValueAxis)
CLASSES = frozenset(item.value for item in SocialClass)
SPEC_EFFECTS = {
    "cohesion": E.COHESION,
    "satisfaction": E.SATISFACTION,
    "piety": E.PIETY,
    "food_saved": E.FOOD_SAVED,
    "fertility": E.FERTILITY,
    "harvest": E.HARVEST,
    "martial": E.MARTIAL,
    "placation": E.PLACATION,
    "hospitality": E.SAFETY,
    "rest": E.REST,
    "vigil": E.VIGIL,
    "healing": E.HEALING,
    "bonding": E.BONDING,
}

CLOSED_SLOTS = "closed_slots"


def cost_for(ctx: TickContext, kind: TraditionFunction) -> dict[str, int]:
    amount = FUNCTIONS[kind].cost(ctx.rules)
    return {resource: amount for resource in TRADITIONS[kind].cost} if amount else {}


def default_magnitude(ctx: TickContext, effect: TraditionEffectKind) -> int:
    table = ctx.rules.traditions
    return {
        E.COHESION: table.festival_cohesion,
        E.SATISFACTION: table.festival_satisfaction,
        E.PIETY: table.piety,
        E.FOOD_SAVED: table.fast_food,
        E.FERTILITY: table.marriage_fertility_pct,
        E.HARVEST: table.harvest_blessing,
        E.MARTIAL: table.martial_display_martial,
        E.PLACATION: table.ancestral_rite_placation,
        E.SAFETY: table.hospitality_danger,
        E.VALUE: table.value_push,
        E.REST: table.rest_pct,
        E.VIGIL: table.vigil_pct,
        E.TRADE: table.fair_trade_pct,
        E.FORAGE: table.forage_food_pct,
        E.HEALING: table.healing_effect,
        E.BONDING: table.bonding_effect,
    }[effect]


async def seed_effects(ctx: TickContext, row: TraditionProfileRow, *, replace: bool = False) -> int:
    existing = list(await ctx.session.scalars(select(TraditionEffectRow).where(TraditionEffectRow.tradition_entity_id == row.tradition_entity_id)))
    if existing and not replace:
        return 0
    for item in existing:
        await ctx.session.delete(item)
    custom = await kind_of(ctx.session, row.custom_kind_id, CustomCatalog.TRADITION_KIND)
    planned: dict[tuple[TraditionEffectKind, str], int] = {}
    if custom is not None:
        params = params_of(custom, TraditionKindParams)
        for effect, magnitude in params.effects.items():
            planned[(TraditionEffectKind(effect), "")] = magnitude
        for axis, value in params.values.items():
            planned[(E.VALUE, ValueAxis(axis).value)] = value
    if not planned:
        spec = tradition_spec(row.kind, row.stage)
        for found in (SPEC_EFFECTS[key] for key in spec.effects if key in SPEC_EFFECTS):
            planned[(found, "")] = default_magnitude(ctx, found)
        for axis, value in spec.values.items():
            planned[(E.VALUE, axis.value)] = value
    for (effect, target), magnitude in planned.items():
        ctx.session.add(TraditionEffectRow(tradition_entity_id=row.tradition_entity_id, effect=effect, target=target, magnitude=magnitude))
    await ctx.session.flush()
    return len(planned)


async def apply_custom_kind(ctx: TickContext, row: TraditionProfileRow) -> None:
    custom = await kind_of(ctx.session, row.custom_kind_id, CustomCatalog.TRADITION_KIND)
    if custom is None:
        return
    if "kind" not in row.locked:
        row.kind = TraditionFunction(custom.base)
    params = params_of(custom, TraditionKindParams)
    if params.cost and "cost" not in row.locked:
        row.cost = {Commodity(key).value: value for key, value in params.cost.items()}


async def taboo_good(ctx: TickContext, tradition: EntityRow) -> str | None:
    stores = await holdings(ctx.session, tradition.location_id) if tradition.location_id is not None else {}
    goods = sorted(commodity.value for commodity, amount in stores.items() if amount > 0)
    return ctx.rng(f"taboo.{tradition.id}").pick(goods) if goods else None


async def profile_of(ctx: TickContext, tradition: EntityRow, kind: TraditionFunction = K.FESTIVAL) -> TraditionProfileRow:
    row = await ctx.session.get(TraditionProfileRow, tradition.id)
    if row is not None:
        return row
    spec = TRADITIONS[kind]
    row = TraditionProfileRow(
        tradition_entity_id=tradition.id,
        kind=kind,
        calendar_slot=slot_fit(kind, None),
        cost=cost_for(ctx, kind),
        effects=dict(spec.effects),
        taboo_target=await taboo_good(ctx, tradition) if kind is K.TABOO else None,
        updated_epoch=ctx.epoch,
        locked=[],
    )
    ctx.session.add(row)
    await ctx.session.flush()
    await seed_effects(ctx, row)
    return row


async def effects_of(ctx: TickContext, row: TraditionProfileRow) -> list[TraditionEffectRow]:
    await seed_effects(ctx, row)
    statement = select(TraditionEffectRow).where(TraditionEffectRow.tradition_entity_id == row.tradition_entity_id)
    return list(await ctx.session.scalars(statement.order_by(TraditionEffectRow.effect, TraditionEffectRow.target)))


async def celebrants(ctx: TickContext, tradition_id: int) -> list[EntityRow]:
    statement = select(BondRow.source_node_id).where(
        BondRow.target_node_id == tradition_id, BondRow.kind == BondKind.CELEBRATES, BondRow.state == BondState.ACTIVE
    )
    ids = sorted(set(await ctx.session.scalars(statement)))
    rows = await ctx.session.scalars(
        select(EntityRow).where(EntityRow.id.in_(ids), EntityRow.status == EntityStatus.CANON, EntityRow.entity_type.in_(list(COMMUNITY_TYPES)))
    )
    return list(rows)


async def fit_of(ctx: TickContext, tradition_id: int, community_id: int) -> int:
    row = await ctx.session.get(TraditionProfileRow, tradition_id)
    if row is None:
        return FIT
    pushed = {
        ValueAxis(effect.target): effect.magnitude * VALUE_SCALE for effect in await effects_of(ctx, row) if effect.effect is E.VALUE and effect.target in AXES
    }
    culture = await values_for(ctx.session, community_id)
    return value_distance(pushed, culture) if pushed and culture else FIT


async def participate(ctx: TickContext, tradition: EntityRow, community: EntityRow) -> TraditionParticipationRow:
    row = await ctx.session.get(TraditionParticipationRow, (tradition.id, community.id))
    if row is None:
        row = TraditionParticipationRow(
            tradition_entity_id=tradition.id, community_entity_id=community.id, participation=PERCENT // 2, since_epoch=ctx.epoch, skipped=0, locked=[]
        )
        ctx.session.add(row)
        await ctx.session.flush()
    table = ctx.rules.traditions
    await profile_of(ctx, tradition)
    fit = await fit_of(ctx, tradition.id, community.id)
    if "participation" not in row.locked:
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
        .where(EntityRow.entity_type == EntityType.MORTAL, EntityRow.status == EntityStatus.CANON, await folk_of(ctx.session, community))
        .order_by(EntityRow.id)
    )
    marked = 0
    for youth in youths:
        if (stat(youth, "age") or 0) != MATURITY:
            continue
        if ctx.rng(f"scar_rite.{tradition.id}.{youth.id}.{ctx.epoch}").chance(ctx.rules.traditions.body_marking_chance):
            harm = Harm(ctx.rules.traditions.scar_harm, HarmCause.RITUAL, f"marked by {tradition.name}", part="face")
            await apply_hits(ctx, youth, harm, lethal=False)
            await judged(ctx, community.id, youth.id, ActKind.RITUAL_SCARRING, note=tradition.name)
            marked += 1
    if marked:
        ctx.count("ritual_scars")
    return marked


async def placate(ctx: TickContext, community: EntityRow, amount: int) -> int:
    mortals = select(EntityRow.id).where(await folk_of(ctx.session, community), EntityRow.entity_type == EntityType.MORTAL)
    spirits = await ctx.session.scalars(select(SpiritProfileRow).where(SpiritProfileRow.origin_mortal_id.in_(mortals)))
    calmed = 0
    for profile in spirits:
        spirit = await ctx.session.get(EntityRow, profile.spirit_entity_id)
        if spirit is None or spirit.status is not EntityStatus.CANON:
            continue
        set_stats(spirit, unrest=clamp_int((stat(spirit, "unrest") or 0) - amount, 0, PERCENT))
        profile.veneration = clamp_int(profile.veneration + amount, 0, PERCENT)
        if profile.alignment is SpiritAlignment.VENGEFUL and (stat(spirit, "unrest") or 0) < ctx.rules.spirits.vengeful_unrest:
            profile.alignment = SpiritAlignment.NEUTRAL
        calmed += 1
    return calmed


async def welcome(ctx: TickContext, community: EntityRow, atlas: RegionAtlas, amount: int) -> bool:
    region_id = atlas.top_region(community.id)
    if region_id is None:
        return False
    await ease_danger(ctx.session, ctx.rules, region_id, DangerSource.BANDITS, amount)
    return True


async def bless_harvest(ctx: TickContext, community: EntityRow, atlas: RegionAtlas, amount: int) -> bool:
    region_id = atlas.top_region(community.id)
    land = await ctx.session.get(RegionEnvironmentRow, region_id) if region_id is not None else None
    if land is None:
        return False
    shift_harvest(land, amount)
    return True


async def hold_fair(ctx: TickContext, community: EntityRow, amount: int) -> None:
    if amount <= 0 or held(community.id):
        return
    shift_stat(community, "prosperity", amount, 0)
    town = await ctx.session.get(SettlementProfileRow, community.id)
    if town is not None and "treasury" not in town.locked:
        town.treasury = max(0, town.treasury + town.treasury * amount // PERCENT)
    await record(ctx, "tradition.fair_held", roles={IncidentRole.SUBJECT: community.id}, facts={"lift": amount}, place=community.id)


async def forage(ctx: TickContext, community: EntityRow, atlas: RegionAtlas, amount: int) -> None:
    region_id = atlas.top_region(community.id)
    if region_id is None or amount <= 0:
        return
    ranges = list(
        await ctx.session.scalars(select(SpeciesRangeRow).where(SpeciesRangeRow.region_entity_id == region_id).order_by(SpeciesRangeRow.species_entity_id))
    )
    wild = max((row.abundance for row in ranges), default=0)
    food = round_half_up(amount * min(PERCENT, wild) / PERCENT)
    if food <= 0:
        return
    await shift_stock(ctx.session, ctx.rules, community.id, Commodity.FOOD, food, epoch=ctx.epoch, flow=GoodsFlow.HARVEST)
    pressure = ctx.rules.traditions.forage_pressure
    for row in ranges:
        if "hunted" not in row.locked and not held(row.species_entity_id):
            row.hunted = row.hunted + pressure
    await record(
        ctx, "tradition.forage_taken", roles={IncidentRole.SUBJECT: community.id, IncidentRole.PLACE: region_id}, facts={"food": food}, place=region_id
    )


async def wed(ctx: TickContext, community: EntityRow, pct: float) -> int:
    population = headcount(community)
    born = round_half_up(population * pct / PERCENT / PERCENT)
    if born <= 0:
        return 0
    with flowing(FlowCategory.BIRTH):
        put_stat(ctx.rules, community, headcount_key(community), population + born)
    return born


async def keepers_of(ctx: TickContext, community: EntityRow) -> list[EntityRow]:
    statement = select(EntityRow).where(
        EntityRow.entity_type == EntityType.MORTAL, EntityRow.status == EntityStatus.CANON, await folk_of(ctx.session, community)
    )
    return list(await ctx.session.scalars(statement.order_by(EntityRow.id)))


async def heal_keepers(ctx: TickContext, community: EntityRow, step: int) -> bool:
    healed = False
    for mortal in await keepers_of(ctx, community):
        profile = await ctx.session.get(MortalProfileRow, mortal.id)
        if profile is None or held(mortal.id) or "health" in (profile.locked or []):
            continue
        profile.health = clamp_int(profile.health + step, 0, PERCENT)
        healed = True
    return healed


async def bond_keepers(ctx: TickContext, community: EntityRow, step: int) -> bool:
    await cohere(ctx, community, step)
    for mortal in await keepers_of(ctx, community):
        if not held(mortal.id):
            await think(ctx.session, ctx.rules, mortal.id, ThoughtKind.BELONGED, ctx.epoch, subject_id=community.id)
    return True


async def gladden(ctx: TickContext, community: EntityRow, step: int, target: str) -> None:
    society = await ctx.session.get(CommunitySocietyRow, community.id)
    if society is None:
        return
    classes = [SocialClass(target)] if target in CLASSES else list(SocialClass)
    for social_class in classes:
        key = f"satisfaction_{social_class.value}"
        setattr(society, key, clamp_int(getattr(society, key) + step, 0, PERCENT))


async def rest(ctx: TickContext, community: EntityRow, share: float) -> None:
    table = ctx.rules.seasonal
    town = await ctx.session.get(SettlementProfileRow, community.id)
    if town is not None and "unrest" not in town.locked:
        town.unrest = clamp_int(town.unrest - round_half_up(table.rest_custom_unrest * share), 0, PERCENT)
    society = await ctx.session.get(CommunitySocietyRow, community.id)
    if society is not None:
        for social_class in SocialClass:
            key = f"satisfaction_{social_class.value}"
            setattr(society, key, clamp_int(getattr(society, key) + round_half_up(table.rest_custom_satisfaction * share), 0, PERCENT))
    shift_stat(community, "prosperity", -round_half_up(table.rest_custom_prosperity * share), 0)


async def keep_vigil(ctx: TickContext, community: EntityRow, share: float) -> None:
    table = ctx.rules.seasonal
    town = await ctx.session.get(SettlementProfileRow, community.id)
    if town is not None and "crime" not in town.locked:
        town.crime = clamp_int(town.crime - round_half_up(table.vigil_crime * share), 0, PERCENT)
    await push_values(ctx, community, {ValueAxis.PIETY: table.vigil_piety}, share)
    await placate(ctx, community, round_half_up(ctx.rules.traditions.ancestral_rite_placation * share))


async def synchronised(ctx: TickContext, row: TraditionProfileRow) -> int:
    if row.calendar_slot is None:
        return 0
    keepers = await ctx.session.scalar(
        select(func.count(BondRow.id)).where(
            BondRow.target_node_id == row.tradition_entity_id, BondRow.kind == BondKind.CELEBRATES, BondRow.state == BondState.ACTIVE
        )
    )
    return min(ctx.rules.traditions.sync_max, max(0, int(keepers or 0) - 1))


async def note_closed(ctx: TickContext, row: TraditionProfileRow, community: EntityRow, reason: str | None) -> None:
    noted: set[tuple[int, int]] = ctx.session.sync_session.info.setdefault(CLOSED_SLOTS, set())
    key = (row.tradition_entity_id, community.id)
    if key in noted:
        return
    noted.add(key)
    await record(
        ctx,
        "tradition.slot_closed",
        roles={IncidentRole.SUBJECT: row.tradition_entity_id, IncidentRole.ACTOR: community.id},
        facts={"reason": reason or "its time does not come"},
        place=community.id,
    )


async def slot_weight(ctx: TickContext, row: TraditionProfileRow, community: EntityRow, effect: TraditionEffectKind) -> float:
    if row.calendar_slot is None:
        return 1.0
    table = ctx.rules.traditions
    state = await slot_open(ctx, community.world_id, row.calendar_slot, community.id, row)
    if not state.open:
        await note_closed(ctx, row, community, state.reason)
        return table.calendar_misfit_pct / PERCENT
    strength = SLOTS[row.calendar_slot].strength(ctx.rules) / PERCENT
    return 1 + table.calendar_slot_pct / PERCENT * strength if effect in SLOTS[row.calendar_slot].effects else 1.0


@dataclass(frozen=True)
class Keep:
    ctx: TickContext
    community: EntityRow
    effect: TraditionEffectRow
    share: float
    atlas: RegionAtlas

    @property
    def amount(self) -> int:
        return round_half_up(self.effect.magnitude * self.share)


async def keep_value(keep: Keep) -> object:
    if keep.effect.target not in AXES:
        return False
    await push_values(keep.ctx, keep.community, {ValueAxis(keep.effect.target): keep.effect.magnitude}, keep.share)
    return True


async def keep_food(keep: Keep) -> object:
    return await shift_stock(keep.ctx.session, keep.ctx.rules, keep.community.id, Commodity.FOOD, keep.amount, epoch=keep.ctx.epoch, flow=GoodsFlow.PRODUCTION)


EFFECT_KEEPERS: Handlers[TraditionEffectKind, Callable[[Keep], Awaitable[object]]] = Handlers(TraditionEffectKind)
EFFECT_KEEPERS.update(
    {
        E.REST: lambda keep: rest(keep.ctx, keep.community, keep.share * keep.effect.magnitude / PERCENT),
        E.VIGIL: lambda keep: keep_vigil(keep.ctx, keep.community, keep.share * keep.effect.magnitude / PERCENT),
        E.COHESION: lambda keep: cohere(keep.ctx, keep.community, keep.amount),
        E.SATISFACTION: lambda keep: gladden(keep.ctx, keep.community, keep.amount, keep.effect.target),
        E.PIETY: lambda keep: push_values(keep.ctx, keep.community, {ValueAxis.PIETY: keep.effect.magnitude}, keep.share),
        E.MARTIAL: lambda keep: push_values(keep.ctx, keep.community, {ValueAxis.MARTIAL: keep.effect.magnitude}, keep.share),
        E.VALUE: keep_value,
        E.FOOD_SAVED: keep_food,
        E.FERTILITY: lambda keep: wed(keep.ctx, keep.community, keep.effect.magnitude * keep.share),
        E.PLACATION: lambda keep: placate(keep.ctx, keep.community, keep.amount),
        E.HARVEST: lambda keep: bless_harvest(keep.ctx, keep.community, keep.atlas, keep.amount),
        E.SAFETY: lambda keep: welcome(keep.ctx, keep.community, keep.atlas, keep.amount),
        E.TRADE: lambda keep: hold_fair(keep.ctx, keep.community, keep.amount),
        E.FORAGE: lambda keep: forage(keep.ctx, keep.community, keep.atlas, keep.amount),
        E.HEALING: lambda keep: heal_keepers(keep.ctx, keep.community, keep.amount),
        E.BONDING: lambda keep: bond_keepers(keep.ctx, keep.community, keep.amount),
    }
)
EFFECT_KEEPERS.seal()


async def apply_effect(ctx: TickContext, community: EntityRow, effect: TraditionEffectRow, share: float, atlas: RegionAtlas) -> bool:
    return await EFFECT_KEEPERS[effect.effect](Keep(ctx, community, effect, share, atlas)) is not False


async def celebrate(ctx: TickContext, tradition: EntityRow, community: EntityRow, atlas: RegionAtlas, keeping: Keeping | None = None) -> str | None:
    row = await profile_of(ctx, tradition)
    await apply_custom_kind(ctx, row)
    part = await participate(ctx, tradition, community)
    keeping = keeping or Keeping()
    counted = 1 + ctx.rules.technique_effects.calendar_pct / PERCENT if await has_technique(ctx.session, community.id, Technique.CALENDAR) else 1.0
    share = min(1.0, part.participation / PERCENT * counted) * keeping.weight
    row.in_season = keeping.in_season
    if not await feast(ctx, community, row, share, keeping.relief):
        part.skipped += 1
        return "skipped"
    part.last_celebrated_epoch = ctx.epoch
    for effect in await effects_of(ctx, row):
        if await apply_effect(ctx, community, effect, share * await slot_weight(ctx, row, community, effect.effect), atlas):
            ctx.count(f"tradition_effect_{effect.effect.value}")
    together = await synchronised(ctx, row)
    if together and row.calendar_slot is not None and (await slot_open(ctx, community.world_id, row.calendar_slot, community.id, row)).open:
        await cohere(ctx, community, round_half_up(together * ctx.rules.traditions.sync_cohesion * share))
        ctx.count("festivals_synchronised")
    if row.kind in SCARRING:
        await scar_youths(ctx, community, tradition)
    if row.kind is K.COMMEMORATION:
        await observe_commemorations(ctx, community)
    await record(
        ctx,
        "tradition.kept",
        roles={IncidentRole.PRODUCT: tradition.id, IncidentRole.PLACE: community.id},
        facts={"function": row.kind, "share": round_half_up(share * PERCENT)},
        place=community.id,
    )
    return row.kind.value


async def observe_commemorations(ctx: TickContext, community: EntityRow) -> None:
    for row in await ctx.session.scalars(
        select(CommemorationRow).where(CommemorationRow.holder_entity_id == community.id).order_by(CommemorationRow.collection_id)
    ):
        if "last_observed_epoch" not in row.locked:
            row.last_observed_epoch = ctx.epoch


FUNCTIONS_FIXUP = "traditions.w52_functions"


def kind_slot(kind: TraditionFunction) -> CalendarSlot | None:
    return FUNCTIONS[kind].slot


async def backfill_functions(ctx: TickContext) -> int:
    if await ctx.session.get(AppliedFixupRow, FUNCTIONS_FIXUP) is not None:
        return 0
    moved = 0
    for row in list(await ctx.session.scalars(select(TraditionProfileRow).order_by(TraditionProfileRow.tradition_entity_id))):
        if held(row.tradition_entity_id) or "kind" in row.locked:
            continue
        named = next((kind for kind in SLOT_NAMED if FUNCTIONS[kind].slot is row.calendar_slot and FUNCTIONS[row.kind].slot is not kind_slot(kind)), None)
        if named is not None:
            row.kind = named
            moved += 1
        if row.calendar_slot is None and "calendar_slot" not in row.locked:
            row.calendar_slot = slot_fit(row.kind, row.stage)
    ctx.session.add(AppliedFixupRow(key=FUNCTIONS_FIXUP, result={"traditions": moved}))
    await ctx.session.flush()
    return moved


async def taboos(ctx: TickContext, community_id: int) -> set[str]:
    memo = memo_of(ctx.session, "taboos", TABOO_TABLES)
    known: frozenset[str] | None = memo.get(community_id) if memo is not None else None
    if known is None:
        known = frozenset(await _taboos(ctx, community_id))
        after = memo_of(ctx.session, "taboos", TABOO_TABLES)
        if after is not None:
            after[community_id] = known
    return set(known)


@memoized(BondRow, TraditionProfileRow)
async def taboo_keepers(session: AsyncSession) -> frozenset[int]:
    taboo = select(TraditionProfileRow.tradition_entity_id).where(TraditionProfileRow.kind == K.TABOO, TraditionProfileRow.taboo_target.is_not(None))
    statement = select(BondRow.source_node_id).where(BondRow.kind == BondKind.CELEBRATES, BondRow.state == BondState.ACTIVE, BondRow.target_node_id.in_(taboo))
    return frozenset(await session.scalars(statement.distinct()))


async def _taboos(ctx: TickContext, community_id: int) -> set[str]:
    if community_id not in await taboo_keepers(ctx.session):
        return set()
    traditions = select(BondRow.target_node_id).where(
        BondRow.source_node_id == community_id, BondRow.kind == BondKind.CELEBRATES, BondRow.state == BondState.ACTIVE
    )
    rows = await ctx.session.scalars(
        select(TraditionProfileRow.taboo_target).where(TraditionProfileRow.tradition_entity_id.in_(traditions), TraditionProfileRow.kind == K.TABOO)
    )
    return {row for row in rows if row}


async def resent_taboo(ctx: TickContext, community_id: int) -> int:
    forbidden = {commodity for commodity in CommodityKind if commodity.value in await taboos(ctx, community_id)}
    if not forbidden:
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
        if any([await holding(ctx.session, partner, commodity) > 0 for commodity in forbidden]):
            await change_relation(ctx, community_id, partner, -ctx.rules.traditions.taboo_infamy, MemoryKind.ILL_WILL, note="trades in what is taboo")
            resented += 1
    return resented


async def keeps(ctx: TickContext, community_id: int, kind: TraditionFunction) -> bool:
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


async def founding_incident(ctx: TickContext, node_id: int) -> int | None:
    statement = select(IncidentParticipantRow.incident_id).where(IncidentParticipantRow.node_id == node_id).order_by(IncidentParticipantRow.incident_id)
    return await ctx.session.scalar(statement.limit(1))


async def commemorated(ctx: TickContext, incident_id: int | None) -> bool:
    if incident_id is None:
        return False
    found = await ctx.session.scalar(select(TraditionProfileRow.tradition_entity_id).where(TraditionProfileRow.origin_incident_id == incident_id).limit(1))
    return found is not None


async def found_commemoration(
    ctx: TickContext,
    *,
    name: str,
    kind: TraditionFunction,
    world_id: int | None,
    place_id: int | None,
    keepers: list[int],
    origin: int | None,
    incident: int | None,
) -> EntityRow:
    tradition = await create_record(
        ctx,
        RecordSpec(
            name=name,
            entity_type=EntityType.TRADITION,
            stats=TraditionStats(spread=PERCENT // 5, rigidity=PERCENT // 4),
            body=f"Kept each year so that {name.removeprefix('The ')} is not forgotten.",
            power=2,
            world_id=world_id,
            location_id=place_id,
        ),
    )
    row = await profile_of(ctx, tradition, kind)
    row.origin_entity_id, row.origin_incident_id = origin, incident
    for keeper in keepers:
        await connect(ctx.session, keeper, tradition.id, BondKind.CELEBRATES, ctx.epoch, description="in remembrance")
    if origin is not None:
        await connect(ctx.session, tradition.id, origin, BondKind.TELLS_OF, ctx.epoch, description="remembers")
    return tradition


async def commemorate(ctx: TickContext, event: EntityRow) -> EntityRow | None:
    if event.engine_kind not in MOURNED | HAILED or event.location_id is None:
        return None
    if (stat(event, "severity") or 0) < ctx.rules.deep_life.legend_event_min_severity:
        return None
    incident = await founding_incident(ctx, event.id)
    if await commemorated(ctx, incident) or not ctx.rng(f"commemoration.{event.id}").chance(ctx.rules.traditions.commemoration_chance):
        return None
    kind = K.MOURNING if event.engine_kind in MOURNED else K.FESTIVAL
    word = "Mourning" if kind is K.MOURNING else "Festival"
    keepers = list(
        await ctx.session.scalars(
            select(EntityRow.id).where(
                EntityRow.id == event.location_id, EntityRow.entity_type.in_(list(COMMUNITY_TYPES)), EntityRow.status == EntityStatus.CANON
            )
        )
    )
    return await found_commemoration(
        ctx,
        name=f"The {word} of {event.name}",
        kind=kind,
        world_id=event.world_id,
        place_id=event.location_id,
        keepers=keepers,
        origin=event.id,
        incident=incident,
    )


async def communities_in(ctx: TickContext, atlas: RegionAtlas, world_id: int, region_id: int | None) -> list[int]:
    rows = await ctx.session.scalars(
        select(EntityRow.id)
        .where(EntityRow.world_id == world_id, EntityRow.entity_type.in_([EntityType.SETTLEMENT, EntityType.PEOPLE]), EntityRow.status == EntityStatus.CANON)
        .order_by(EntityRow.id)
    )
    return [community for community in rows if region_id is None or atlas.top_region(community) == region_id]


async def remember_years(ctx: TickContext, atlas: RegionAtlas) -> list[EntityRow]:
    founded: list[EntityRow] = []
    years = await ctx.session.scalars(select(NotableYearRow).where(NotableYearRow.epoch == ctx.epoch).order_by(NotableYearRow.id))
    for year in list(years):
        if year.magnitude < NAMED_YEARS[year.kind].remembered(ctx.rules) or await commemorated(ctx, year.incident_id):
            continue
        if not ctx.rng(f"commemoration.year.{year.id}").chance(ctx.rules.traditions.commemoration_chance):
            continue
        land = await communities_in(ctx, atlas, year.world_id, year.region_entity_id)
        keepers = ctx.rng(f"commemoration.keepers.{year.id}").shuffled(land)[: -(-len(land) * ctx.rules.traditions.commemoration_keepers // PERCENT)]
        if not keepers:
            continue
        tradition = await found_commemoration(
            ctx,
            name=f"The Remembrance of {year.name}",
            kind=K.COMMEMORATION,
            world_id=year.world_id,
            place_id=keepers[0],
            keepers=keepers,
            origin=None,
            incident=year.incident_id,
        )
        profile = await profile_of(ctx, tradition, K.COMMEMORATION)
        profile.calendar_slot, profile.notable_year_id = CalendarSlot.REMEMBRANCE, year.id
        founded.append(tradition)
    return founded


async def remember_miracles(ctx: TickContext) -> list[EntityRow]:
    founded: list[EntityRow] = []
    rows = await ctx.session.execute(
        select(IncidentRow.id, ChronicleEntityRow.entity_id)
        .join(ChronicleRow, ChronicleRow.id == IncidentRow.chronicle_id)
        .join(ChronicleEntityRow, ChronicleEntityRow.chronicle_id == ChronicleRow.id)
        .where(ChronicleRow.kind == ChronicleKind.MIRACLE, ChronicleRow.epoch >= ctx.epoch - 1)
        .order_by(IncidentRow.id)
    )
    for incident_id, entity_id in rows.all():
        target = await ctx.session.get(EntityRow, entity_id)
        if target is None or target.status is not EntityStatus.CANON or target.entity_type not in COMMUNITY_TYPES:
            continue
        if await commemorated(ctx, incident_id) or not ctx.rng(f"commemoration.miracle.{incident_id}").chance(ctx.rules.traditions.commemoration_chance):
            continue
        founded.append(
            await found_commemoration(
                ctx,
                name=f"The Festival of the Wonder at {target.name}",
                kind=K.FESTIVAL,
                world_id=target.world_id,
                place_id=target.id,
                keepers=[target.id],
                origin=target.id,
                incident=incident_id,
            )
        )
    return founded


async def best_fit(ctx: TickContext, offered: list[EntityRow], community_id: int) -> tuple[EntityRow, int] | None:
    scored = [(await fit_of(ctx, tradition.id, community_id), tradition.id, tradition) for tradition in offered]
    if not scored:
        return None
    fit, _, tradition = min(scored, key=lambda item: (item[0], item[1]))
    return tradition, fit


async def absorb_festivals(ctx: TickContext, community: EntityRow, converter_id: int | None) -> list[EntityRow]:
    converter = await ctx.session.get(EntityRow, converter_id) if converter_id is not None else None
    if converter is None or converter.status is not EntityStatus.CANON or converter.id == community.id:
        return []
    absorbed: list[EntityRow] = []
    kept_by = select(BondRow.target_node_id).where(
        BondRow.source_node_id == community.id, BondRow.kind == BondKind.CELEBRATES, BondRow.state == BondState.ACTIVE
    )
    rows = await ctx.session.scalars(
        select(TraditionProfileRow).where(TraditionProfileRow.tradition_entity_id.in_(kept_by), TraditionProfileRow.kind.in_(list(ABSORBABLE)))
    )
    for row in list(rows):
        tradition = await ctx.session.get(EntityRow, row.tradition_entity_id)
        if tradition is None or tradition.status is not EntityStatus.CANON:
            continue
        if (stat(tradition, "rigidity") or 0) < ctx.rules.traditions.syncretism_rigidity:
            continue
        already = await ctx.session.scalar(
            select(BondRow.id).where(
                BondRow.source_node_id == converter.id,
                BondRow.target_node_id == tradition.id,
                BondRow.kind == BondKind.CELEBRATES,
                BondRow.state == BondState.ACTIVE,
            )
        )
        if already is not None:
            continue
        await connect(ctx.session, converter.id, tradition.id, BondKind.CELEBRATES, ctx.epoch, description="absorbed at the conversion")
        absorbed.append(tradition)
    return absorbed
