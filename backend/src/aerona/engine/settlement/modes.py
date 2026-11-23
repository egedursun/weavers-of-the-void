from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.catalog.settle_modes import PREFERRED, SETTLE_MODES
from aerona.catalog.terrain import TERRAIN
from aerona.constants.units import PERCENT
from aerona.db.tables.cosmos import AppliedFixupRow
from aerona.db.tables.demography import PeopleBiologyRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.environment import RegionEnvironmentRow
from aerona.db.tables.settlement import SettlementProfileRow
from aerona.db.write_guard import held
from aerona.domain.enums.body import BodyPlan
from aerona.domain.enums.entity import EntityType
from aerona.domain.enums.environment import MovementMode, TerrainKind, WeatherEffect
from aerona.domain.enums.modifier import IncidentRole
from aerona.domain.enums.world_view import SettleMode
from aerona.engine.body.customs import people_of
from aerona.engine.body.variants import body_modes
from aerona.engine.context import TickContext
from aerona.engine.cosmos.world_views import view_of
from aerona.engine.environment.book import EnvironmentBook
from aerona.engine.interconnect.flows import FlowCategory, flowing
from aerona.engine.primitives.distance import RegionAtlas
from aerona.engine.primitives.numbers import clamp_int, round_half_up
from aerona.engine.primitives.queries import canon
from aerona.engine.primitives.stats import set_stats, shift_stat, stat_or
from aerona.engine.recording.record import record
from aerona.rules.model import keyed
from aerona.rules.registry import Rules

MODES_FIXUP = "settle_modes.w52"
MODE_KEY = "settle_mode"


@dataclass(frozen=True)
class SettleScene:
    plan: BodyPlan | None
    modes: frozenset[MovementMode]
    terrain: TerrainKind | None
    cover: int
    default: SettleMode


def fits(rules: Rules, mode: SettleMode, scene: SettleScene) -> bool:
    if mode is scene.default:
        return True
    spec = SETTLE_MODES[mode]
    traits = TERRAIN[scene.terrain].traits if scene.terrain is not None else frozenset()
    if spec.needs is not None and spec.needs not in scene.modes:
        return False
    if spec.terrains and not traits & spec.terrains:
        return False
    if spec.shuns & traits:
        return False
    return not spec.forest or scene.cover >= rules.settle_modes.canopy_cover


def chosen(rules: Rules, scene: SettleScene) -> SettleMode:
    for mode in PREFERRED:
        if scene.plan in SETTLE_MODES[mode].natural and fits(rules, mode, scene):
            return mode
    return scene.default


async def ground_of(session: AsyncSession, settlement: EntityRow) -> RegionEnvironmentRow | None:
    region = (await RegionAtlas.load(session)).top_region(settlement.id)
    return await session.get(RegionEnvironmentRow, region) if region is not None else None


async def scene_of(session: AsyncSession, rules: Rules, settlement: EntityRow, book: EnvironmentBook | None = None) -> SettleScene:
    people = await people_of(session, settlement)
    biology = await session.get(PeopleBiologyRow, people.id) if people is not None else None
    ground = book.region_of(settlement.id) if book is not None else await ground_of(session, settlement)
    view = await view_of(session, rules, settlement.world_id)
    return SettleScene(
        biology.body_plan if biology is not None else None,
        await body_modes(session, settlement),
        ground.dominant_terrain if ground is not None else None,
        ground.forest_cover if ground is not None else 0,
        view.settle,
    )


async def founding_scene(session: AsyncSession, rules: Rules, founder: EntityRow, region: EntityRow) -> SettleScene:
    people = await people_of(session, founder) if founder.entity_type is not EntityType.PEOPLE else founder
    biology = await session.get(PeopleBiologyRow, people.id) if people is not None else None
    ground = await session.get(RegionEnvironmentRow, region.id)
    view = await view_of(session, rules, region.world_id)
    return SettleScene(
        biology.body_plan if biology is not None else None,
        await body_modes(session, founder),
        ground.dominant_terrain if ground is not None else None,
        ground.forest_cover if ground is not None else 0,
        view.settle,
    )


async def choose_mode(session: AsyncSession, rules: Rules, settlement: EntityRow) -> SettleMode:
    return chosen(rules, await scene_of(session, rules, settlement))


def defence_pct(rules: Rules, mode: SettleMode) -> int:
    return keyed(rules.settle_modes, mode.value, "defence")


def exposure_pct(rules: Rules, mode: SettleMode) -> int:
    return keyed(rules.settle_modes, mode.value, "exposure")


@dataclass
class ModeTally:
    settled: int = 0
    weathered: int = 0
    fell: int = 0
    unfit: int = 0


async def backfill_modes(ctx: TickContext, tally: ModeTally) -> None:
    if await ctx.session.get(AppliedFixupRow, MODES_FIXUP) is not None:
        return
    for profile in list(
        await ctx.session.scalars(
            select(SettlementProfileRow).where(SettlementProfileRow.settle_mode == SettleMode.GROUND).order_by(SettlementProfileRow.settlement_entity_id)
        )
    ):
        town = await ctx.session.get(EntityRow, profile.settlement_entity_id)
        if town is None or MODE_KEY in profile.locked or held(town.id):
            continue
        mode = await choose_mode(ctx.session, ctx.rules, town)
        if mode is not profile.settle_mode:
            profile.settle_mode = mode
            tally.settled += 1
    ctx.session.add(AppliedFixupRow(key=MODES_FIXUP, result={"settled": tally.settled}))
    await ctx.session.flush()


async def weather_town(ctx: TickContext, book: EnvironmentBook, town: EntityRow, profile: SettlementProfileRow, tally: ModeTally) -> None:
    region = book.region_of(town.id)
    if region is None:
        return
    season = book.season_at(region.world_id, ctx.epoch)
    weather = book.weather(ctx.environment.world_seed, ctx.epoch, region, season, f"settle.{town.id}")
    harm = max(0, weather.effect(WeatherEffect.WIND)) + max(0, weather.effect(WeatherEffect.FLOOD))
    loss = round_half_up(harm / PERCENT * exposure_pct(ctx.rules, profile.settle_mode) / PERCENT * ctx.rules.settle_modes.exposure_prosperity)
    if loss > 0:
        shift_stat(town, "prosperity", -loss, ctx.rules.society.default_stat)
        tally.weathered += 1


async def canopy_falls(ctx: TickContext, town: EntityRow, profile: SettlementProfileRow, scene: SettleScene, tally: ModeTally) -> None:
    if profile.settle_mode is not SettleMode.CANOPY or MODE_KEY in profile.locked or scene.cover >= ctx.rules.settle_modes.canopy_cover:
        return
    people = stat_or(town, "population", 0)
    lost = round_half_up(people * ctx.rules.settle_modes.canopy_fall_pct / PERCENT)
    with flowing(FlowCategory.DEATH):
        set_stats(town, population=max(0, people - lost))
    profile.settle_mode = SettleMode.GROUND
    tally.fell += 1
    await record(ctx, "settle_modes.canopy_fell", roles={IncidentRole.SUBJECT: town.id}, facts={"lost": lost, "cover": scene.cover}, place=town.id)


async def unfit_town(ctx: TickContext, town: EntityRow, profile: SettlementProfileRow, scene: SettleScene, tally: ModeTally) -> None:
    if fits(ctx.rules, profile.settle_mode, scene):
        return
    if "unrest" not in profile.locked:
        profile.unrest = clamp_int(profile.unrest + ctx.rules.settle_modes.unfit_unrest, 0, PERCENT)
    tally.unfit += 1
    await record(ctx, "settle_modes.unfit", roles={IncidentRole.SUBJECT: town.id}, facts={"mode": profile.settle_mode}, place=town.id)


async def keep_modes(ctx: TickContext, tally: ModeTally) -> None:
    await backfill_modes(ctx, tally)
    book = await EnvironmentBook.load(ctx.session, ctx.rules, ctx.epoch)
    for town in await canon(ctx.session, [EntityType.SETTLEMENT]):
        profile = await ctx.session.get(SettlementProfileRow, town.id)
        if profile is None or held(town.id):
            continue
        scene = await scene_of(ctx.session, ctx.rules, town, book)
        await weather_town(ctx, book, town, profile, tally)
        await canopy_falls(ctx, town, profile, scene, tally)
        await unfit_town(ctx, town, profile, scene, tally)
    await ctx.session.flush()
