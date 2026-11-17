from collections import Counter

from sqlalchemy import delete, select

from aerona.catalog.cosmography import PHENOMENON_KINDS, PHENOMENON_MODEL, PHENOMENON_REAGENTS, PHENOMENON_WEATHER, SCOPE_SPREAD
from aerona.constants.units import PERCENT
from aerona.core.errors import NotFoundError
from aerona.db.tables.cosmography import PhenomenonFootprintRow, PhenomenonProfileRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.environment import ForcedWeatherRow, RegionEnvironmentRow
from aerona.db.write_guard import held
from aerona.domain.enums.cosmography import PhenomenonCause, PhenomenonKind, PhenomenonPersistence
from aerona.domain.enums.entity import COMMUNITY_TYPES, EngineKind, EntityStatus, EntityType
from aerona.domain.enums.environment import WeatherKind
from aerona.domain.enums.modifier import IncidentRole
from aerona.domain.enums.records import StepAction, StepLocus, StepOutcome
from aerona.domain.models.entity_stats import PhenomenonStats
from aerona.engine.context import TickContext
from aerona.engine.cosmos.kinds import PHENOMENON_MECHANICS
from aerona.engine.environment.control import force_weather
from aerona.engine.interconnect.annotations import reads
from aerona.engine.primitives.distance import RegionAtlas
from aerona.engine.primitives.numbers import clamp_int, clamp_percent
from aerona.engine.primitives.queries import canon
from aerona.engine.primitives.records import RecordSpec, create_record, retire_in
from aerona.engine.primitives.stats import shift_bounded
from aerona.engine.recording.record import StepDraft, record

WARD_KINDS = frozenset({EngineKind.TEMPLE, EngineKind.WALL})


async def form_phenomenon(
    ctx: TickContext,
    kind: PhenomenonKind,
    region: EntityRow,
    cause: PhenomenonCause,
    *,
    cause_node_id: int | None = None,
    intensity: int | None = None,
) -> EntityRow | None:
    if held(region.id, region.world_id):
        return None
    existing = await ctx.session.scalar(
        select(PhenomenonFootprintRow.phenomenon_entity_id)
        .join(PhenomenonProfileRow, PhenomenonProfileRow.entity_id == PhenomenonFootprintRow.phenomenon_entity_id)
        .join(EntityRow, EntityRow.id == PhenomenonProfileRow.entity_id)
        .where(PhenomenonFootprintRow.region_entity_id == region.id, PhenomenonProfileRow.kind == kind, EntityRow.status == EntityStatus.CANON)
        .limit(1)
    )
    if existing is not None:
        return await ctx.session.get(EntityRow, existing)
    spec = PHENOMENON_KINDS[kind]
    mechanics = PHENOMENON_MECHANICS[kind]
    strength = clamp_percent(intensity if intensity is not None else ctx.rules.phenomena.spread_intensity * 2)
    entity = await create_record(
        ctx,
        RecordSpec(
            entity_type=EntityType.PHENOMENON,
            name=f"{spec.label} of {region.name}",
            body=spec.description,
            stats=PhenomenonStats(danger=clamp_percent(mechanics.danger(ctx.rules)), renown=strength // 2),
            power=max(1, strength // 20),
            world_id=region.world_id,
            location_id=region.id,
        ),
    )
    ctx.session.add(
        PhenomenonProfileRow(
            entity_id=entity.id,
            kind=kind,
            intensity=strength,
            growth=mechanics.growth(ctx.rules),
            containment=0,
            cause=cause,
            cause_node_id=cause_node_id,
            formed_epoch=ctx.epoch,
            locked=[],
        )
    )
    ctx.session.add(PhenomenonFootprintRow(phenomenon_entity_id=entity.id, region_entity_id=region.id, intensity=strength))
    await ctx.session.flush()
    await record(
        ctx,
        f"phenomenon.formed.{kind.value}",
        roles={IncidentRole.SUBJECT: entity.id, IncidentRole.PLACE: region.id, IncidentRole.ACTOR: cause_node_id},
        facts={"phenomenon": kind, "cause": cause, "intensity": strength, "danger": clamp_percent(mechanics.danger(ctx.rules))},
        steps=(StepDraft(StepAction.APPEAR, actor=entity.id, locus_kind=StepLocus.REGION, locus_node=region.id),),
        place=region.id,
        world_id=region.world_id,
    )
    ctx.count("phenomena_formed")
    return entity


async def wards_in(ctx: TickContext, region_ids: set[int]) -> int:
    statement = select(EntityRow.id).where(
        EntityRow.status == EntityStatus.CANON, EntityRow.engine_kind.in_(list(WARD_KINDS)), EntityRow.location_id.in_(list(region_ids))
    )
    return len(list(await ctx.session.scalars(statement)))


async def footprints_of(ctx: TickContext, entity_id: int) -> list[PhenomenonFootprintRow]:
    statement = select(PhenomenonFootprintRow).where(PhenomenonFootprintRow.phenomenon_entity_id == entity_id).order_by(PhenomenonFootprintRow.region_entity_id)
    return list(await ctx.session.scalars(statement))


async def spread(ctx: TickContext, atlas: RegionAtlas, entity: EntityRow, profile: PhenomenonProfileRow, prints: list[PhenomenonFootprintRow]) -> int:
    table = ctx.rules.phenomena
    cap = table.spread_cap * SCOPE_SPREAD[PHENOMENON_MODEL[profile.kind].scope]
    if profile.intensity < table.spread_at or len(prints) >= cap:
        return 0
    covered = {row.region_entity_id for row in prints}
    candidates = sorted({other for row in prints for other in atlas.neighbour_regions(row.region_entity_id)} - covered)
    candidates = [region for region in candidates if not held(region)]
    if not candidates:
        return 0
    target = ctx.rng(f"phenomenon_spread.{entity.id}").pick(candidates)
    ctx.session.add(PhenomenonFootprintRow(phenomenon_entity_id=entity.id, region_entity_id=target, intensity=table.spread_intensity))
    return 1


async def fade(ctx: TickContext, entity: EntityRow, profile: PhenomenonProfileRow, regions: int) -> None:
    await ctx.session.execute(delete(PhenomenonFootprintRow).where(PhenomenonFootprintRow.phenomenon_entity_id == entity.id))
    await retire_in(ctx, entity, "faded away", status=EntityStatus.DESTROYED)
    await record(
        ctx,
        "phenomenon.faded",
        roles={IncidentRole.SUBJECT: entity.id},
        facts={"regions": regions, "intensity": profile.intensity},
        steps=(StepDraft(StepAction.WANE, actor=entity.id), StepDraft(StepAction.END, actor=entity.id)),
        world_id=entity.world_id,
    )


async def effects(ctx: TickContext, profile: PhenomenonProfileRow, prints: list[PhenomenonFootprintRow]) -> None:
    mechanics = PHENOMENON_MECHANICS[profile.kind]
    weather = PHENOMENON_WEATHER.get(profile.kind)
    reagent = PHENOMENON_REAGENTS.get(profile.kind)
    for row in prints:
        if held(row.region_entity_id):
            continue
        share = row.intensity / PERCENT
        ground = await ctx.session.get(RegionEnvironmentRow, row.region_entity_id)
        region = await ctx.session.get(EntityRow, row.region_entity_id)
        if ground is not None and reagent is not None and "mineral_layers" not in ground.locked:
            layers = dict(ground.mineral_layers)
            layers[reagent.value] = clamp_int(layers.get(reagent.value, 0) + round(ctx.rules.phenomena.harvest * share), 0, PERCENT)
            ground.mineral_layers = layers
        if region is not None and weather is not None and not await weather_forced(ctx, region.id, weather):
            await force_weather(ctx.session, region, weather, from_epoch=ctx.epoch, epochs=ctx.rules.phenomena.weather_epochs, season_position=None)
        piety = round(mechanics.piety(ctx.rules) * share)
        if piety and region is not None:
            for community in await canon(ctx.session, COMMUNITY_TYPES, region.world_id):
                if community.location_id == region.id and not held(community.id):
                    shift_bounded(ctx.rules, community, "piety", piety)


async def weather_forced(ctx: TickContext, region_id: int, weather: WeatherKind) -> bool:
    statement = select(ForcedWeatherRow.id).where(
        ForcedWeatherRow.region_entity_id == region_id, ForcedWeatherRow.kind == weather, ForcedWeatherRow.until_epoch >= ctx.epoch
    )
    return await ctx.session.scalar(statement.limit(1)) is not None


@reads("table.phenomenon_profiles")
async def phenomena_cycles(ctx: TickContext) -> None:
    table = ctx.rules.phenomena
    atlas = await RegionAtlas.load(ctx.session)
    for profile in list(await ctx.session.scalars(select(PhenomenonProfileRow).order_by(PhenomenonProfileRow.entity_id))):
        entity = await ctx.session.get(EntityRow, profile.entity_id)
        if entity is None or entity.status is not EntityStatus.CANON or held(entity.id):
            continue
        prints = await footprints_of(ctx, entity.id)
        regions = {row.region_entity_id for row in prints}
        if "containment" not in profile.locked:
            profile.containment = clamp_percent(profile.containment + await wards_in(ctx, regions) * table.ward_containment)
        held_back = profile.containment * table.contain_pct / PERCENT / PERCENT
        growth = profile.growth * (1 - held_back) if profile.growth > 0 else profile.growth - profile.containment // 10
        persistence = PHENOMENON_MODEL[profile.kind].persistence
        if persistence is PhenomenonPersistence.PASSING:
            growth -= table.passing_fade
        if "intensity" not in profile.locked:
            profile.intensity = clamp_percent(round(profile.intensity + growth))
        for row in prints:
            row.intensity = clamp_percent(min(profile.intensity, row.intensity + max(0, round(growth))))
        if profile.intensity <= table.fade_at and (persistence is not PhenomenonPersistence.PERMANENT or profile.containment >= PERCENT):
            await fade(ctx, entity, profile, len(prints))
            continue
        ctx.count("phenomena_spread", await spread(ctx, atlas, entity, profile, prints))
        await effects(ctx, profile, prints)
    await ctx.session.flush()


async def contain(ctx: TickContext, entity_id: int, amount: int, by_id: int) -> PhenomenonProfileRow:
    profile = await ctx.session.get(PhenomenonProfileRow, entity_id)
    entity = await ctx.session.get(EntityRow, entity_id)
    if profile is None or entity is None:
        raise NotFoundError("No such phenomenon.")
    profile.containment = clamp_percent(profile.containment + amount)
    if profile.containment >= PERCENT:
        profile.intensity = clamp_percent(profile.intensity - amount)
    await record(
        ctx,
        "phenomenon.contained",
        roles={IncidentRole.ACTOR: by_id, IncidentRole.SUBJECT: entity.id},
        facts={"containment": profile.containment, "amount": amount},
        steps=(StepDraft(StepAction.BIND, actor=by_id, target=entity.id, outcome=StepOutcome.SUCCESS),),
        world_id=entity.world_id,
    )
    await ctx.session.flush()
    return profile


async def phenomenon_passability(ctx: TickContext) -> Counter[int]:
    shifts: Counter[int] = Counter()
    statement = (
        select(PhenomenonFootprintRow.region_entity_id, PhenomenonFootprintRow.intensity, PhenomenonProfileRow.kind)
        .join(PhenomenonProfileRow, PhenomenonProfileRow.entity_id == PhenomenonFootprintRow.phenomenon_entity_id)
        .join(EntityRow, EntityRow.id == PhenomenonProfileRow.entity_id)
        .where(EntityRow.status == EntityStatus.CANON)
    )
    for region_id, intensity, kind in await ctx.session.execute(statement):
        shifts[region_id] += round(PHENOMENON_MECHANICS[kind].passability(ctx.rules) * intensity / PERCENT)
    return shifts


async def phenomenon_sanity(ctx: TickContext) -> dict[int, int]:
    found: Counter[int] = Counter()
    statement = (
        select(PhenomenonFootprintRow.region_entity_id, PhenomenonFootprintRow.intensity, PhenomenonProfileRow.kind)
        .join(PhenomenonProfileRow, PhenomenonProfileRow.entity_id == PhenomenonFootprintRow.phenomenon_entity_id)
        .join(EntityRow, EntityRow.id == PhenomenonProfileRow.entity_id)
        .where(EntityRow.status == EntityStatus.CANON)
    )
    for region_id, intensity, kind in await ctx.session.execute(statement):
        found[region_id] += round(PHENOMENON_MECHANICS[kind].sanity(ctx.rules) * intensity / PERCENT)
    return dict(found)
