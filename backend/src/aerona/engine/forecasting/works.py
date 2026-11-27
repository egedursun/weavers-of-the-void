from dataclasses import dataclass

from sqlalchemy import select

from aerona.catalog.life.forecasting import METHOD_COST_PCT, METHOD_STRENGTH_PCT, NEEDS
from aerona.catalog.life_traits import OBSERVATION_METHOD_TRAITS, having
from aerona.constants.units import PERCENT
from aerona.db.tables.climes import MonsoonSeasonRow
from aerona.db.tables.culture import HolderLevelRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.environment import ForcedWeatherRow, RegionEnvironmentRow
from aerona.db.tables.folk_knowledge import FolkKnowledgeRow
from aerona.db.tables.forecasting import ObservationMethodRow, WeatherWorkRow
from aerona.db.tables.minds import MindProfileRow
from aerona.db.tables.sacred import GeniusLocusRow
from aerona.db.tables.settlement import SettlementInfrastructureRow, SettlementProfileRow
from aerona.db.tables.water import RegionCryosphereRow
from aerona.db.write_guard import held
from aerona.domain.enums.entity import EntityStatus, EntityType
from aerona.domain.enums.environment import WeatherKind
from aerona.domain.enums.folk_knowledge import FolkDomain
from aerona.domain.enums.forecasting import ObservationMethod, WeatherAim, WeatherWorkMethod
from aerona.domain.enums.life_traits import ObservationMethodTrait
from aerona.domain.enums.loops import BalanceLoop
from aerona.domain.enums.mind import MemoryKind
from aerona.domain.enums.minds import MindOrigin
from aerona.domain.enums.modifier import IncidentRole
from aerona.domain.enums.records import InstrumentKind, StepAction
from aerona.domain.enums.society import KnowledgeBranch
from aerona.engine.context import TickContext
from aerona.engine.economy.purse import take_coin
from aerona.engine.forecasting.reading import sky_marks
from aerona.engine.loops.delay import lagged
from aerona.engine.primitives.distance import RegionAtlas
from aerona.engine.primitives.knowledge import knows
from aerona.engine.primitives.stats import shift_stat, stat_or
from aerona.engine.recording.record import FactInput, StepDraft, record
from aerona.engine.recording.terms import explaining_alone, term
from aerona.engine.services.community_relations import change_relation
from aerona.rules.registry import Rules

TRUSTED_BY_FAITH = having(OBSERVATION_METHOD_TRAITS, ObservationMethodTrait.TRUSTED_BY_FAITH)
AIM_WEATHER: dict[WeatherAim, WeatherKind] = {
    WeatherAim.RAIN: WeatherKind.RAIN,
    WeatherAim.DRY: WeatherKind.DROUGHT_WIND,
    WeatherAim.CALM: WeatherKind.CLEAR,
    WeatherAim.COLD: WeatherKind.SNOW,
    WeatherAim.WARM: WeatherKind.HEAT_WAVE,
    WeatherAim.WIND: WeatherKind.STORM,
    WeatherAim.SNOW: WeatherKind.SNOW,
}
OPPOSITE: dict[WeatherAim, WeatherAim] = {
    WeatherAim.RAIN: WeatherAim.DRY,
    WeatherAim.DRY: WeatherAim.RAIN,
    WeatherAim.CALM: WeatherAim.CALM,
    WeatherAim.COLD: WeatherAim.WARM,
    WeatherAim.WARM: WeatherAim.COLD,
    WeatherAim.WIND: WeatherAim.CALM,
    WeatherAim.SNOW: WeatherAim.WARM,
}
LORE_DEPTH = 30
LEVELS: tuple[tuple[ObservationMethod, KnowledgeBranch, int], ...] = (
    (ObservationMethod.ALMANAC, KnowledgeBranch.ASTRONOMY, 2),
    (ObservationMethod.INSTRUMENT, KnowledgeBranch.ASTRONOMY, 4),
    (ObservationMethod.NETWORK_OF_OBSERVERS, KnowledgeBranch.WRITING, 5),
    (ObservationMethod.MODEL, KnowledgeBranch.ASTRONOMY, 7),
)


EPOCH_STRENGTH = 25


@dataclass
class ForecastTally:
    methods: int = 0
    kept: int = 0
    failed: int = 0
    ignored: int = 0
    worked: int = 0
    side_effects: int = 0
    banned: int = 0
    raised: int = 0


def accuracy_of(rules: Rules, method: ObservationMethod) -> int:
    table = rules.forecasting
    return {
        ObservationMethod.SIGHT: table.accuracy_sight,
        ObservationMethod.LORE: table.accuracy_lore,
        ObservationMethod.ALMANAC: table.accuracy_almanac,
        ObservationMethod.INSTRUMENT: table.accuracy_instrument,
        ObservationMethod.NETWORK_OF_OBSERVERS: table.accuracy_network_of_observers,
        ObservationMethod.MODEL: table.accuracy_model,
        ObservationMethod.NETWORK: table.accuracy_network,
        ObservationMethod.POWER: table.accuracy_power,
        ObservationMethod.DIVINATION: table.accuracy_divination,
        ObservationMethod.ANIMAL_SIGNS: table.accuracy_animal_signs,
        ObservationMethod.DREAM: table.accuracy_dream,
    }[method]


async def methods_of(ctx: TickContext, people: EntityRow, tally: ForecastTally) -> list[ObservationMethodRow]:
    rows = list(
        await ctx.session.scalars(select(ObservationMethodRow).where(ObservationMethodRow.people_entity_id == people.id).order_by(ObservationMethodRow.id))
    )
    if rows:
        return rows
    known = {ObservationMethod.SIGHT}
    lore = await ctx.session.scalar(
        select(FolkKnowledgeRow.depth).where(FolkKnowledgeRow.people_entity_id == people.id, FolkKnowledgeRow.domain == FolkDomain.WEATHER)
    )
    if lore is not None and lore >= LORE_DEPTH:
        known.add(ObservationMethod.LORE)
    beasts = await ctx.session.scalar(
        select(FolkKnowledgeRow.depth).where(FolkKnowledgeRow.people_entity_id == people.id, FolkKnowledgeRow.domain == FolkDomain.ANIMALS)
    )
    if beasts is not None and beasts >= LORE_DEPTH:
        known.add(ObservationMethod.ANIMAL_SIGNS)
    mind = await ctx.session.scalar(
        select(FolkKnowledgeRow.depth).where(FolkKnowledgeRow.people_entity_id == people.id, FolkKnowledgeRow.domain == FolkDomain.MIND)
    )
    if mind is not None and mind >= LORE_DEPTH:
        known.add(ObservationMethod.DREAM)
    for method, branch, level in LEVELS:
        reached = await ctx.session.get(HolderLevelRow, (people.id, branch))
        if reached is not None and reached.level >= level:
            known.add(method)
    for method in sorted(known):
        row = ObservationMethodRow(people_entity_id=people.id, domain=FolkDomain.WEATHER, method=method, accuracy=accuracy_of(ctx.rules, method), locked=[])
        ctx.session.add(row)
        rows.append(row)
    tally.methods += len(known)
    return rows


async def foresee(ctx: TickContext, people: EntityRow, rows: list[ObservationMethodRow], towns: list[EntityRow], tally: ForecastTally) -> None:
    table = ctx.rules.forecasting
    best = max(rows, key=lambda row: (row.accuracy, row.id), default=None)
    if best is None:
        return
    roles = {IncidentRole.SUBJECT: people.id}
    if best.accuracy + await sky_marks(ctx.session, ctx.rules, people.id) < table.kept_accuracy:
        tally.failed += 1
        await record(ctx, "weather.forecast_failed", roles=roles, facts={"method": best.method, "accuracy": best.accuracy})
        return
    if stat_or(people, "piety", 0) >= table.ignore_piety and best.method not in TRUSTED_BY_FAITH:
        tally.ignored += 1
        await record(ctx, "weather.forecast_ignored", roles=roles, facts={"method": best.method, "accuracy": best.accuracy})
        return
    tally.kept += 1
    for town in towns:
        if not held(town.id):
            with explaining_alone():
                term("forecasting.foresight", table.kept_refund, source_node_id=people.id)
                shift_stat(town, "prosperity", table.kept_refund, low=0, high=PERCENT)
    await record(ctx, "weather.forecast_kept", roles=roles, facts={"method": best.method, "accuracy": best.accuracy})


def aimed_weather(rules: Rules, aim: WeatherAim, ground: RegionEnvironmentRow | None) -> WeatherKind:
    if aim is not WeatherAim.COLD or ground is None:
        return AIM_WEATHER[aim]
    settings = rules.weather
    near = abs(ground.temperature - settings.cold_threshold) <= settings.glaze_band
    if near and ground.rainfall >= settings.wet_pivot:
        return WeatherKind.ICE_STORM
    if ground.rainfall < settings.dry_threshold or ground.temperature <= settings.cold_threshold + settings.frost_band:
        return WeatherKind.FROST
    return AIM_WEATHER[aim]


async def force(ctx: TickContext, region: EntityRow, aim: WeatherAim) -> None:
    if region.world_id is None:
        return
    kind = aimed_weather(ctx.rules, aim, await ctx.session.get(RegionEnvironmentRow, region.id))
    ctx.session.add(
        ForcedWeatherRow(region_entity_id=region.id, world_id=region.world_id, from_epoch=max(1, ctx.epoch), until_epoch=max(1, ctx.epoch), kind=kind)
    )


async def work(ctx: TickContext, row: WeatherWorkRow, atlas: RegionAtlas, tally: ForecastTally) -> None:
    table = ctx.rules.forecasting
    region = await ctx.session.get(EntityRow, row.region_entity_id)
    if region is None or held(region.id):
        return
    await force(ctx, region, row.aim)
    tally.worked += 1
    await record(
        ctx,
        "weather.worked",
        roles={IncidentRole.ACTOR: row.holder_node_id, IncidentRole.PLACE: region.id},
        facts={"aim": row.aim, "strength": row.strength},
        place=region.id,
        steps=(StepDraft(StepAction.PERFORM_RITE, actor=row.holder_node_id, instrument_kind=InstrumentKind.WEATHER_WORK, instrument_key=row.method.value),),
    )
    if "epochs_left" not in row.locked:
        row.epochs_left = max(0, row.epochs_left - 1)
    downwind = await ctx.session.get(EntityRow, row.downwind_region_id) if row.downwind_region_id is not None else None
    side = row.strength * table.side_effect_share_pct // PERCENT
    if downwind is None or held(downwind.id) or side <= 0 or OPPOSITE[row.aim] is row.aim:
        return
    await force(ctx, downwind, OPPOSITE[row.aim])
    tally.side_effects += 1
    await record(
        ctx,
        "weather.side_effect",
        roles={IncidentRole.ACTOR: row.holder_node_id, IncidentRole.PLACE: downwind.id},
        facts={"aim": OPPOSITE[row.aim], "strength": side},
        place=downwind.id,
    )
    worker = row.holder_node_id
    for harmed in atlas.communities_in(downwind.id):
        if harmed == worker or held(harmed):
            continue
        standing = await change_relation(
            ctx,
            harmed,
            worker,
            -table.grievance,
            MemoryKind.HARMED_ME,
            note="a weather work elsewhere brought harmful weather on us",
            reverse_note="blamed us for a weather work",
        )
        felt = await lagged(ctx, BalanceLoop.WEATHER_GRIEVANCE, harmed, standing, subject=row.id)
        if felt < table.ban_relation and "epochs_left" not in row.locked:
            row.epochs_left = 0
            tally.banned += 1
            await record(
                ctx,
                "weather.work_banned",
                roles={IncidentRole.ACTOR: harmed, IncidentRole.TARGET: worker, IncidentRole.PLACE: region.id},
                facts={"relation": standing},
                place=region.id,
            )
            return


async def town_pays(ctx: TickContext, town: EntityRow, cost: int) -> bool:
    profile = await ctx.session.get(SettlementProfileRow, town.id)
    if profile is not None and "treasury" not in (profile.locked or []) and profile.treasury >= cost:
        profile.treasury -= cost
        return True
    return await take_coin(ctx.session, ctx.rules, town, cost)


async def method_known(ctx: TickContext, holder_id: int) -> WeatherWorkMethod | None:
    spirit = await ctx.session.scalar(select(GeniusLocusRow.spirit_entity_id).where(GeniusLocusRow.place_entity_id == holder_id).limit(1))
    if spirit is not None and await knows(ctx.session, holder_id, NEEDS[WeatherWorkMethod.BARGAIN]):
        return WeatherWorkMethod.BARGAIN
    made = await ctx.session.scalar(
        select(MindProfileRow.node_id)
        .join(EntityRow, EntityRow.id == MindProfileRow.node_id)
        .where(EntityRow.location_id == holder_id, EntityRow.status == EntityStatus.CANON, MindProfileRow.origin != MindOrigin.BORN)
        .limit(1)
    )
    if made is not None:
        return WeatherWorkMethod.MADE_MIND
    for method, branch in NEEDS.items():
        if await knows(ctx.session, holder_id, branch):
            return method
    return None


def aim_for(ctx: TickContext, shift: int, parched: bool, *, snowless: bool = False, harbour: bool = False) -> WeatherAim | None:
    limit = ctx.rules.forecasting.weather_work_shift
    if parched or shift <= -limit:
        return WeatherAim.SNOW if snowless else WeatherAim.RAIN
    if shift >= limit:
        return WeatherAim.DRY
    return WeatherAim.WIND if harbour else None


async def raise_works(ctx: TickContext, atlas: RegionAtlas, hard: set[int], tally: ForecastTally) -> None:
    table = ctx.rules.forecasting
    working = set(await ctx.session.scalars(select(WeatherWorkRow.region_entity_id).where(WeatherWorkRow.epochs_left > 0)))
    towns = select(EntityRow).where(EntityRow.entity_type == EntityType.SETTLEMENT, EntityRow.status == EntityStatus.CANON).order_by(EntityRow.id)
    for town in list(await ctx.session.scalars(towns)):
        region_id = atlas.top_region(town.id)
        land = await ctx.session.get(RegionEnvironmentRow, region_id) if region_id is not None else None
        if region_id is None or land is None or region_id in working or held(town.id) or held(region_id):
            continue
        ice = await ctx.session.get(RegionCryosphereRow, region_id)
        snowless = ice is not None and ice.glacier_extent > 0 and ice.snowpack < table.snow_work_snowpack
        harbour = (
            await ctx.session.get(SettlementInfrastructureRow, town.id) or SettlementInfrastructureRow(harbour_capacity=0)
        ).harbour_capacity >= table.wind_work_harbour
        aim = aim_for(ctx, land.rainfall_shift, town.world_id in hard, snowless=snowless, harbour=harbour)
        method = await method_known(ctx, town.id)
        if aim is None or method is None:
            continue
        cost = table.weather_work_cost * METHOD_COST_PCT[method] // PERCENT
        if not await town_pays(ctx, town, cost):
            continue
        strength = min(PERCENT, table.weather_work_strength * METHOD_STRENGTH_PCT[method] // PERCENT)
        downwind = next(iter(sorted(atlas.neighbours(region_id))), None)
        ctx.session.add(
            WeatherWorkRow(
                holder_node_id=town.id,
                region_entity_id=region_id,
                downwind_region_id=downwind,
                method=method,
                aim=aim,
                strength=strength,
                cost=cost,
                epochs_left=1 + strength // EPOCH_STRENGTH,
                since_epoch=ctx.epoch,
                locked=[],
            )
        )
        working.add(region_id)
        facts: dict[str, FactInput] = {"aim": aim, "method": method, "strength": strength}
        await record(ctx, "weather.work_raised", roles={IncidentRole.ACTOR: town.id, IncidentRole.PLACE: region_id}, facts=facts, place=region_id)
        tally.raised += 1


async def keep_forecasting(ctx: TickContext, tally: ForecastTally) -> None:
    atlas = await RegionAtlas.load(ctx.session)
    hard = set(await ctx.session.scalars(select(MonsoonSeasonRow.world_id).where(MonsoonSeasonRow.epoch == ctx.epoch, MonsoonSeasonRow.failed.is_(True))))
    folk = await ctx.session.scalars(
        select(EntityRow).where(EntityRow.entity_type == EntityType.PEOPLE, EntityRow.status == EntityStatus.CANON).order_by(EntityRow.id)
    )
    for people in list(folk):
        if held(people.id):
            continue
        rows = await methods_of(ctx, people, tally)
        if people.world_id in hard:
            towns = [
                town
                for town in [await ctx.session.get(EntityRow, place) for place in atlas.communities_in(people.location_id or 0)]
                if town is not None and town.entity_type is EntityType.SETTLEMENT
            ]
            await foresee(ctx, people, rows, towns, tally)
    await raise_works(ctx, atlas, hard, tally)
    for row in list(await ctx.session.scalars(select(WeatherWorkRow).where(WeatherWorkRow.epochs_left > 0).order_by(WeatherWorkRow.id))):
        await work(ctx, row, atlas, tally)
    await ctx.session.flush()
