from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field, replace
from types import MappingProxyType

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.cartography.model import ElevationClass
from aerona.catalog.interventions import DISASTERS
from aerona.constants.units import PERCENT
from aerona.core.errors import NotFoundError, ValidationFailedError
from aerona.core.grammar import an, several
from aerona.db.repositories.bonds import BondDraft, BondRepository
from aerona.db.repositories.entities import EntityRepository
from aerona.db.tables.celestial import WorldRow
from aerona.db.tables.disease import OutbreakRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.environment import RegionEnvironmentRow
from aerona.db.tables.happenings import RegionGeomorphRow
from aerona.db.tables.physics import WorldPhysicsRow
from aerona.db.tables.structures import StructureProfileRow
from aerona.db.write_guard import held, unheld
from aerona.domain.enums.agrarian import NutrientKind
from aerona.domain.enums.body import DamageType, HarmCause
from aerona.domain.enums.bond import BondKind
from aerona.domain.enums.disease import SpreadPath
from aerona.domain.enums.divine import DomainHook
from aerona.domain.enums.dominion import DivineScale
from aerona.domain.enums.entity import COMMUNITY_TYPES, LOCATION_TYPES, SOCIETY_TYPES, EngineKind, EntityFlag, EntityStatus, EntityType
from aerona.domain.enums.environment import RiverClass, ScarKind
from aerona.domain.enums.happening import EventPhase
from aerona.domain.enums.integrity import HarmForce
from aerona.domain.enums.intervention import Disaster
from aerona.domain.enums.loops import BalanceLoop
from aerona.domain.enums.modifier import IncidentRole
from aerona.domain.enums.mortal import DeathCause
from aerona.domain.enums.records import FactUnit, StepAction, StepLocus, StepOutcome
from aerona.domain.enums.settlement import DistrictHarm
from aerona.domain.enums.society import Commodity, KnowledgeBranch, NaturalLaw
from aerona.domain.enums.storyteller import SpontaneousKind
from aerona.domain.enums.structure import StructureKind
from aerona.domain.models.entity_stats import EventStats
from aerona.engine.agrarian.book import deposit, shield_of
from aerona.engine.body.hits import Harm
from aerona.engine.body.variants import folk_biology
from aerona.engine.context import TickContext
from aerona.engine.cosmos.climate import cold_snap
from aerona.engine.cosmos.world_views import WorldView, world_views
from aerona.engine.disease.book import DiseaseBook
from aerona.engine.disease.harm import disease_harm, lasting_illness
from aerona.engine.disease.outbreaks import STRIKING, disease_for, lethality_factor, open_outbreak, spread_factor, tally
from aerona.engine.dominion.blame import blame_rulers
from aerona.engine.dominion.book import DominionBook
from aerona.engine.economy.routes import trade_links
from aerona.engine.environment.book import EnvironmentBook, add_scar, region_environment
from aerona.engine.environment.geomorph import erupted, eruption_chance, quaked, river_after_flood, river_after_quake, shapes_by_region
from aerona.engine.environment.notable import remember_event_year
from aerona.engine.environment.profile import RIVER_RANK
from aerona.engine.folkways.shunning import corpse_exposure
from aerona.engine.happenings.profile import add_footprint, derive_footprint, flow_of, open_profile, record_casualties
from aerona.engine.households.homes import sickness_factor
from aerona.engine.interconnect.annotations import reads, writes
from aerona.engine.interconnect.flows import FlowCategory, flowing
from aerona.engine.lifecycle.wounds import WoundOutcome, apply_hits, fatal_injury
from aerona.engine.loops.delay import lagged
from aerona.engine.phase import Phase
from aerona.engine.phases.climate import plague_pct
from aerona.engine.phases.society_economy import population_bounds, society_of
from aerona.engine.primitives.distance import RegionAtlas
from aerona.engine.primitives.knowledge import KnowledgeMap, LawBook
from aerona.engine.primitives.numbers import clamp_int, fraction, round_half_up
from aerona.engine.primitives.queries import BondIndex, canon, top_region
from aerona.engine.primitives.records import RecordSpec, create_record
from aerona.engine.primitives.stats import FOLLOWERS_KEY, POPULATION_KEY, headcount_value, set_stats, stat, stat_or
from aerona.engine.primitives.thresholds import relative_threshold
from aerona.engine.recording.record import FactInput, RoleValue, StepDraft, record
from aerona.engine.recording.scope import recording
from aerona.engine.records import death_path
from aerona.engine.settlement.districts import damage_districts
from aerona.engine.storyteller.pace import paced
from aerona.engine.structures.damage import harm, quake_loss
from aerona.engine.structures.readers import strength_at
from aerona.engine.transform.anchors import world_harmed
from aerona.rules.registry import Rules

DISASTER_DAMAGE: dict[Disaster, DamageType] = {
    Disaster.EARTHQUAKE: DamageType.BLUNT,
    Disaster.FLOOD: DamageType.BLUNT,
    Disaster.PLAGUE: DamageType.VENOM,
    Disaster.DROUGHT: DamageType.VENOM,
    Disaster.STORM: DamageType.BLUNT,
    Disaster.ERUPTION: DamageType.FIRE,
    Disaster.VOLCANIC_QUAKE: DamageType.BLUNT,
}

DISASTER_KINDS: dict[Disaster, EngineKind] = {
    Disaster.EARTHQUAKE: EngineKind.EARTHQUAKE,
    Disaster.FLOOD: EngineKind.FLOOD,
    Disaster.PLAGUE: EngineKind.PLAGUE,
    Disaster.DROUGHT: EngineKind.DROUGHT,
    Disaster.STORM: EngineKind.STORM,
    Disaster.ERUPTION: EngineKind.ERUPTION,
    Disaster.VOLCANIC_QUAKE: EngineKind.EARTHQUAKE,
}
SHAKING = frozenset({Disaster.EARTHQUAKE, Disaster.VOLCANIC_QUAKE, Disaster.ERUPTION})
STRUCK_TYPES = frozenset({*COMMUNITY_TYPES, EntityType.STRUCTURE})
SPREAD_BOND_KINDS = (BondKind.PAYS_TRIBUTE, BondKind.RULES)
HIGHLANDS = frozenset({ElevationClass.MOUNTAINOUS, ElevationClass.HILLY})


@dataclass
class DisasterImpact:
    notes: list[str] = field(default_factory=list)
    losses: dict[int, int | None] = field(default_factory=dict)
    dead: list[EntityRow] = field(default_factory=list)
    destroyed: list[EntityRow] = field(default_factory=list)
    steps: list[StepDraft] = field(default_factory=list)
    sickness: int | None = None

    def lost(self) -> int:
        return sum(value or 0 for value in self.losses.values())

    def struck(self) -> list[int]:
        return sorted({*self.losses, *(row.id for row in self.dead), *(row.id for row in self.destroyed)})


DISTRICT_HARMS: Mapping[Disaster, DistrictHarm] = MappingProxyType(
    {
        Disaster.EARTHQUAKE: DistrictHarm.EARTHQUAKE,
        Disaster.VOLCANIC_QUAKE: DistrictHarm.EARTHQUAKE,
        Disaster.ERUPTION: DistrictHarm.EARTHQUAKE,
        Disaster.FLOOD: DistrictHarm.FLOOD,
        Disaster.STORM: DistrictHarm.STORM,
        Disaster.DROUGHT: DistrictHarm.DROUGHT,
    }
)


def joined_names(names: Sequence[str]) -> str:
    if len(names) <= 1:
        return "".join(names)
    return f"{', '.join(names[:-1])} and {names[-1]}"


async def affected_entities(session: AsyncSession, target: EntityRow) -> list[EntityRow]:
    found = [target]
    seen = {target.id}
    frontier = [target.id]
    while frontier:
        children = list(
            await session.scalars(select(EntityRow).where(EntityRow.location_id.in_(frontier), EntityRow.status == EntityStatus.CANON).order_by(EntityRow.id))
        )
        frontier = []
        for child in children:
            if child.id not in seen:
                seen.add(child.id)
                found.append(child)
                frontier.append(child.id)
    return found


def _reduce(rules: Rules, entity: EntityRow, key: str, loss: float) -> None:
    current = stat(entity, key)
    if current is None:
        return
    if key == FOLLOWERS_KEY:
        set_stats(entity, followers=clamp_int(current * (1 - loss), 1, rules.limits.cult_follower_cap))
        return
    floor, ceiling = population_bounds(rules, entity)
    set_stats(entity, population=clamp_int(current * (1 - loss), floor, ceiling))


def _drop(entity: EntityRow, key: str, amount: float) -> None:
    current = stat(entity, key)
    if current is not None:
        set_stats(entity, **{key: clamp_int(current - amount, 0, PERCENT)})


async def _strike_mortal(ctx: TickContext, mortal: EntityRow, disaster: Disaster, scale: float, knowledge: KnowledgeMap) -> bool:
    if held(mortal.id):
        return False
    effects = ctx.rules.intervention_effects
    death_chances = {
        Disaster.EARTHQUAKE: effects.earthquake_mortal_death_chance,
        Disaster.FLOOD: effects.flood_mortal_death_chance,
        Disaster.PLAGUE: effects.plague_mortal_death_chance,
        Disaster.DROUGHT: effects.drought_mortal_death_chance,
        Disaster.STORM: effects.storm_mortal_death_chance,
        Disaster.ERUPTION: ctx.rules.geomorphology.eruption_mortal_death_chance,
        Disaster.VOLCANIC_QUAKE: effects.earthquake_mortal_death_chance * ctx.rules.geomorphology.volcanic_quake_pct / PERCENT,
    }
    medicine = (
        knowledge.ratio(ctx.rules, mortal.id, KnowledgeBranch.MEDICINE, effects.medicine_plague_severity)
        * await lagged(ctx, BalanceLoop.SQUALOR_DISEASE, mortal.id, await sickness_factor(ctx.session, ctx.rules, mortal.id))
        if disaster is Disaster.PLAGUE
        else 1.0
    )
    rng = ctx.rng(f"disaster_mortal.{mortal.id}")
    phrase = DISASTERS[disaster].death_phrase
    label = DISASTERS[disaster].label.lower()
    hurt = Harm(
        round_half_up(effects.disaster_injury_hp * scale), HarmCause.DISASTER, f"died of wounds suffered in the {label}", damage_type=DISASTER_DAMAGE[disaster]
    )
    exposed = await corpse_exposure(ctx.session, ctx.rules, mortal.id) if disaster is Disaster.PLAGUE else 1.0
    if rng.chance(death_chances[disaster] * scale * medicine * exposed):
        if disaster is not Disaster.PLAGUE:
            await fatal_injury(ctx, mortal, replace(hurt, death_cause=phrase))
        return await death_path(ctx, mortal, phrase, manner=DeathCause.DISASTER)
    if not rng.chance(effects.disaster_injury_chance):
        return False
    profile = STRIKING.get() if disaster is Disaster.PLAGUE else None
    if profile is not None:
        hurt = await disease_harm(ctx, mortal, profile, hurt)
    wounding = await apply_hits(ctx, mortal, hurt)
    if disaster is Disaster.PLAGUE and wounding.outcome is WoundOutcome.WOUNDED:
        chronic = profile.chronic_rate / ctx.rules.epidemiology.neutral_chronic_rate if profile is not None else 1.0
        await lasting_illness(ctx, mortal, profile, chance=min(PERCENT, ctx.rules.conditions.plague_chronic_chance * chronic))
    return wounding.outcome is WoundOutcome.DIED


def shaking_loss(rules: Rules, disaster: Disaster) -> float:
    if disaster is Disaster.ERUPTION:
        return float(rules.geomorphology.eruption_durability_loss)
    strength = rules.geomorphology.volcanic_quake_pct / PERCENT if disaster is Disaster.VOLCANIC_QUAKE else 1.0
    return rules.intervention_effects.earthquake_durability_loss * strength


async def _quake_structure(ctx: TickContext, structure: EntityRow, scale: float, knowledge: KnowledgeMap, disaster: Disaster = Disaster.EARTHQUAKE) -> bool:
    effects = ctx.rules.intervention_effects
    sturdy = structure.maker_entity_id is not None and knowledge.knows(structure.maker_entity_id, KnowledgeBranch.ARCHITECTURE)
    label = DISASTERS[disaster].label.lower()
    loss = await quake_loss(ctx, structure, shaking_loss(ctx.rules, disaster) * (fraction(effects.architecture_quake_severity) if sturdy else 1.0) * scale)
    profile = await ctx.session.get(StructureProfileRow, structure.id)
    if profile is not None:
        if not await harm(
            ctx, structure, profile, loss, cause=f"the {label}", force=HarmForce.IMPACT if disaster is Disaster.ERUPTION else HarmForce.QUAKE, quiet=True
        ):
            return False
    else:
        durability = stat(structure, "durability")
        if durability is None:
            return False
        remaining = clamp_int(durability - loss, 0, PERCENT)
        set_stats(structure, durability=remaining)
        if remaining > 0:
            return False
    await EntityRepository(ctx.session).set_status(structure, EntityStatus.DESTROYED, ctx.epoch, f"Collapsed in the {label}.")
    return True


def _strike_stats(rules: Rules, entity: EntityRow, disaster: Disaster, scale: float, knowledge: KnowledgeMap) -> None:
    effects = rules.intervention_effects
    if disaster is Disaster.EARTHQUAKE:
        _reduce(rules, entity, POPULATION_KEY, fraction(effects.earthquake_population_loss) * scale)
    elif disaster is Disaster.VOLCANIC_QUAKE:
        _reduce(rules, entity, POPULATION_KEY, fraction(effects.earthquake_population_loss) * scale * rules.geomorphology.volcanic_quake_pct / PERCENT)
    elif disaster is Disaster.ERUPTION:
        _reduce(rules, entity, POPULATION_KEY, fraction(rules.geomorphology.eruption_population_loss) * scale)
        _drop(entity, "prosperity", rules.geomorphology.eruption_prosperity_loss * scale)
    elif disaster is Disaster.FLOOD:
        _drop(entity, "prosperity", effects.flood_prosperity_loss * scale)
        _reduce(rules, entity, POPULATION_KEY, fraction(effects.flood_population_loss) * scale)
        _drop(entity, "fertility", -effects.flood_fertility_after)
    elif disaster is Disaster.PLAGUE:
        medicine = knowledge.ratio(rules, entity.id, KnowledgeBranch.MEDICINE, effects.medicine_plague_severity)
        _reduce(rules, entity, POPULATION_KEY, fraction(effects.plague_population_loss) * scale * medicine)
        _reduce(rules, entity, FOLLOWERS_KEY, fraction(effects.plague_follower_loss) * scale * medicine)
    elif disaster is Disaster.DROUGHT:
        farming = knowledge.ratio(rules, entity.id, KnowledgeBranch.AGRICULTURE, effects.agriculture_drought_severity)
        _drop(entity, "fertility", effects.drought_fertility_loss * scale * farming)
        _reduce(rules, entity, POPULATION_KEY, fraction(effects.drought_population_loss) * scale * farming)
    else:
        _drop(entity, "defense", effects.storm_defense_loss * scale)
        _drop(entity, "prosperity", effects.storm_prosperity_loss * scale)


def disaster_phrase(disaster: Disaster) -> str:
    return an(DISASTERS[disaster].label.lower())


async def apply_disaster(ctx: TickContext, target: EntityRow, disaster: Disaster, severity: float) -> DisasterImpact:
    with flowing(FlowCategory.DISASTER):
        impact = await strike_disaster(ctx, target, disaster, severity)
    await world_harmed(ctx, target.world_id, severity)
    return impact


async def strike_disaster(ctx: TickContext, target: EntityRow, disaster: Disaster, severity: float) -> DisasterImpact:
    impact = DisasterImpact()
    knowledge = await KnowledgeMap.load(ctx.session)
    repository = EntityRepository(ctx.session)
    effects = ctx.rules.intervention_effects
    for entity in await affected_entities(ctx.session, target):
        if await repository.remove_flag(entity.id, EntityFlag.PROTECTED_FROM_DISASTER):
            impact.notes.append(f"{entity.name} was protected")
            impact.steps.append(StepDraft(StepAction.SPREAD, target=entity.id, outcome=StepOutcome.NO_EFFECT))
            continue
        scale = severity * knowledge.ratio(ctx.rules, entity.id, KnowledgeBranch.ASTRONOMY, effects.astronomy_disaster_severity)
        scale *= (await folk_biology(ctx.session, entity)).disaster(disaster)
        if entity.entity_type is EntityType.MORTAL:
            if entity.status is EntityStatus.CANON and await _strike_mortal(ctx, entity, disaster, scale, knowledge):
                impact.dead.append(entity)
            continue
        if disaster is Disaster.FLOOD:
            scale *= 1 - await strength_at(ctx.session, entity.id, [StructureKind.DAM]) * ctx.rules.structure_functions.dam_flood_cut_pct / PERCENT
        if entity.entity_type is EntityType.SETTLEMENT:
            shielded = await shield_of(ctx, entity, disaster)
            scale *= 1 - shielded
            if shielded > 0:
                impact.notes.append(f"the works of {entity.name} held back part of it")
                impact.steps.append(
                    StepDraft(StepAction.SPREAD, target=entity.id, outcome=StepOutcome.ABSORBED, amount=shielded * PERCENT, unit=FactUnit.PERCENT)
                )
        before = headcount_value(entity)
        if disaster in SHAKING and entity.entity_type is EntityType.STRUCTURE and await _quake_structure(ctx, entity, scale, knowledge, disaster):
            impact.destroyed.append(entity)
            continue
        _strike_stats(ctx.rules, entity, disaster, scale, knowledge)
        hurt = DISTRICT_HARMS.get(disaster)
        if hurt is not None and entity.entity_type is EntityType.SETTLEMENT:
            await damage_districts(ctx, entity, hurt, scale)
        after = headcount_value(entity)
        if entity.entity_type in STRUCK_TYPES:
            lost = max(0, before - after) if before is not None and after is not None else None
            impact.losses[entity.id] = lost
            impact.steps.append(
                StepDraft(StepAction.SPREAD, target=entity.id, outcome=StepOutcome.DAMAGED, amount=lost, unit=FactUnit.COUNT if lost is not None else None)
            )
    if impact.destroyed:
        impact.notes.append(f"{joined_names([item.name for item in impact.destroyed])} collapsed")
        impact.steps.extend(StepDraft(StepAction.COLLAPSE, target=item.id, outcome=StepOutcome.DESTROYED) for item in impact.destroyed)
    if impact.dead:
        impact.notes.append(f"{joined_names([item.name for item in impact.dead])} perished")
        impact.steps.extend(StepDraft(StepAction.SPREAD, target=item.id, outcome=StepOutcome.KILLED) for item in impact.dead)
    await ctx.session.flush()
    return impact


async def record_disaster_event(ctx: TickContext, target: EntityRow, disaster: Disaster, severity: int, impact: DisasterImpact | None = None) -> EntityRow:
    effects = ctx.rules.intervention_effects
    label = DISASTERS[disaster].label
    event = await create_record(
        ctx,
        RecordSpec(
            name=f"{target.name} {label} (Epoch {ctx.epoch})",
            entity_type=EntityType.EVENT,
            stats=EventStats(severity=clamp_int(severity, 0, PERCENT)),
            body=f"{label} over {target.name}.",
            power=clamp_int(severity / effects.disaster_event_power_divisor, effects.disaster_event_power_min, effects.disaster_event_power_max),
            world_id=target.world_id,
            location_id=target.id if target.entity_type in LOCATION_TYPES else target.location_id,
            subtype=label.lower(),
            engine_kind=DISASTER_KINDS[disaster],
            flags=(EntityFlag.DISASTER,),
        ),
    )
    bonds = BondRepository(ctx.session)
    await bonds.connect(BondDraft(event.id, target.id, BondKind.CAUSED, ctx.epoch))
    if impact is not None:
        for entity_id, loss in impact.losses.items():
            if entity_id != target.id:
                await bonds.connect(BondDraft(event.id, entity_id, BondKind.CAUSED, ctx.epoch, f"{several(loss, 'life', 'lives')} lost" if loss else "struck"))
        for mortal in impact.dead:
            mortal.death_event_entity_id = event.id
            await bonds.connect(BondDraft(event.id, mortal.id, BondKind.CAUSED, ctx.epoch, "died there"))
        for structure in impact.destroyed:
            await bonds.connect(BondDraft(event.id, structure.id, BondKind.CAUSED, ctx.epoch, "was destroyed"))
        await record_impact(ctx, event, impact)
    return event


async def record_impact(ctx: TickContext, event: EntityRow, impact: DisasterImpact) -> int:
    await blame_rulers(ctx, list(impact.losses))
    await open_profile(ctx, event)
    await derive_footprint(ctx.session, await RegionAtlas.load(ctx.session), event, ctx.epoch)
    dead = 0
    for entity_id, loss in sorted(impact.losses.items()):
        community = await ctx.session.get(EntityRow, entity_id)
        if community is not None and loss:
            dead += await record_casualties(ctx, event.id, community, loss, category=flow_of(event.engine_kind), phase=EventPhase.ONSET)
    return dead


@dataclass
class DisasterWorld:
    laws: LawBook
    climates: Mapping[int, int]
    struck: int = 0
    views: Mapping[int, WorldView] = field(default_factory=dict)
    bodies: Mapping[int, WorldPhysicsRow] = field(default_factory=dict)
    dominion: DominionBook = field(default_factory=DominionBook)

    def fortune_mult(self, rules: Rules, region_id: int) -> float:
        fortune = self.dominion.scale_at(rules, region_id, DivineScale.FORTUNE)
        return max(0.0, 1 - fortune * rules.dominion.fortune_per_step_pct / PERCENT)

    def nature_mult(self, rules: Rules, world_id: int | None, disaster: Disaster) -> float:
        view = self.views.get(world_id) if world_id is not None else None
        kind = fraction(view.disaster(disaster)) if view is not None else 1.0
        return kind * self.restless(rules, world_id, disaster)

    def restless(self, rules: Rules, world_id: int | None, disaster: Disaster) -> float:
        body = self.bodies.get(world_id) if world_id is not None else None
        if body is None or disaster not in SHAKING:
            return 1.0
        table = rules.planetary_climate
        if disaster is Disaster.ERUPTION:
            return body.volcanism / max(1, table.volcanism_reference)
        return body.tectonics / max(1, table.tectonics_reference)

    def law_mult(self, rules: Rules, world_id: int) -> float:
        return float(rules.disasters.law_mult) if self.laws.has(NaturalLaw.DISASTERS, world_id) else 1.0

    def climate_mult(self, world_id: int) -> float:
        return fraction(self.climates.get(world_id, PERCENT))

    def plague_mult(self, rules: Rules, world_id: int) -> float:
        return self.climate_mult(world_id) * self.law_mult(rules, world_id)


def severity_roll(ctx: TickContext, stream: str) -> int:
    settings = ctx.rules.disasters
    return settings.severity_base + ctx.rng(stream).die(settings.severity_die)


def flood_chance(rules: Rules, coastal: bool, ground: RegionEnvironmentRow | None, tidal: int) -> float:
    settings = rules.disasters
    if ground is None:
        return float(settings.flood_chance) if coastal else 0.0
    river = RIVER_RANK[ground.river_class]
    if not coastal and river < RIVER_RANK[RiverClass.RIVER]:
        return 0.0
    boost = (
        (tidal * settings.tide_flood_pct / PERCENT if coastal else 0) + river * settings.river_flood_pct + ground.erosion * settings.erosion_flood_pct / PERCENT
    )
    return settings.flood_chance * (1 + boost / PERCENT)


def region_candidates(
    ctx: TickContext,
    region: EntityRow,
    atlas: RegionAtlas,
    population: int,
    laws: LawBook,
    *,
    ground: RegionEnvironmentRow | None = None,
    tidal: int = 0,
    shape: RegionGeomorphRow | None = None,
) -> list[tuple[Disaster, float]]:
    settings = ctx.rules.disasters
    entry = atlas.record(region.id)
    if entry is None:
        return []
    candidates: list[tuple[Disaster, float]] = []
    volcanic = shape is not None and shape.volcanic
    if entry.elevation_class in HIGHLANDS or volcanic:
        candidates.append((Disaster.VOLCANIC_QUAKE if volcanic else Disaster.EARTHQUAKE, settings.earthquake_chance))
    eruption = eruption_chance(ctx.rules, shape)
    if eruption:
        candidates.append((Disaster.ERUPTION, eruption))
    flood = flood_chance(ctx.rules, entry.coastal, ground, tidal)
    if flood:
        candidates.append((Disaster.FLOOD, flood))
    if entry.coastal:
        candidates.append((Disaster.STORM, settings.storm_chance))
    barren = stat_or(region, "fertility", ctx.rules.world_effects.unknown_fertility) < settings.drought_fertility_threshold
    dry = ground is not None and ground.rainfall < settings.drought_rainfall_below
    if barren or dry or laws.has(NaturalLaw.DROUGHT, region.world_id):
        candidates.append((Disaster.DROUGHT, settings.drought_chance))
    if population >= settings.region_plague_population:
        crowding = min(float(settings.plague_crowd_max_pct), population / settings.plague_crowd_divisor * PERCENT)
        disease = ground.disease_load * settings.disease_plague_pct / PERCENT if ground is not None else 0
        candidates.append((Disaster.PLAGUE, settings.region_plague_chance + crowding + disease))
    return candidates


SCARRING: dict[Disaster, tuple[ScarKind, str]] = {
    Disaster.PLAGUE: (ScarKind.PLAGUE_GROUND, "plague_scar_pct"),
    Disaster.EARTHQUAKE: (ScarKind.CRATER, "quake_crater_pct"),
    Disaster.VOLCANIC_QUAKE: (ScarKind.CRATER, "quake_crater_pct"),
}


async def scar_land(ctx: TickContext, target: EntityRow, disaster: Disaster, severity: int) -> None:
    found = SCARRING.get(disaster)
    if found is None:
        return
    kind, key = found
    ground = await region_environment(ctx.session, target.id)
    if ground is not None:
        add_scar(ground, kind, round_half_up(severity * getattr(ctx.rules.disasters, key) / PERCENT))


async def strike_plague(
    ctx: TickContext,
    target: EntityRow,
    severity: int,
    *,
    disease: EntityRow | None = None,
    path: SpreadPath = SpreadPath.ORIGIN,
    source: OutbreakRow | None = None,
) -> tuple[EntityRow, DisasterImpact]:
    book = await DiseaseBook.load(ctx.session, ctx.rules, ctx.epoch)
    region_id = target.id if target.entity_type is EntityType.REGION else book.atlas.top_region(target.id)
    region = await ctx.session.get(EntityRow, region_id) if region_id is not None else None
    chosen = disease if disease is not None else await disease_for(ctx, book, region) if region is not None else None
    struck = [entity for entity in await affected_entities(ctx.session, target) if entity.entity_type in COMMUNITY_TYPES]
    factor = lethality_factor(book, chosen.id, struck, await KnowledgeMap.load(ctx.session)) if chosen is not None else 1.0
    if chosen is not None and book.active_of(chosen.id, region_id) is None:
        factor *= 1 - book.hidden_share(chosen.id) * ctx.rules.epidemiology.incubation_delay_pct / PERCENT
    factor *= await ctx.hook_easing(target.id, DomainHook.IMMUNITY)
    token = STRIKING.set(book.profiles.get(chosen.id) if chosen is not None else None)
    try:
        with flowing(FlowCategory.PLAGUE):
            impact = await apply_disaster(ctx, target, Disaster.PLAGUE, severity * factor / ctx.rules.disasters.scale_divisor)
    finally:
        STRIKING.reset(token)
    if chosen is not None:
        impact.notes.insert(0, f"the sickness was {chosen.name}")
        impact.sickness = chosen.id
    await scar_land(ctx, target, Disaster.PLAGUE, severity)
    event = await record_disaster_event(ctx, target, Disaster.PLAGUE, severity, impact)
    await remember_event_year(ctx, event, await RegionAtlas.load(ctx.session), epoch=ctx.epoch)
    if chosen is not None and region_id is not None:
        outbreak = await open_outbreak(ctx, book, chosen, region_id, path=path, severity=severity, event=event, source=source)
        record_toll(ctx, book, chosen, outbreak, struck=struck, impact=impact)
    return event, impact


def record_toll(ctx: TickContext, book: DiseaseBook, disease: EntityRow, outbreak: OutbreakRow, *, struck: list[EntityRow], impact: DisasterImpact) -> None:
    table = ctx.rules.epidemiology
    profile = book.profiles.get(disease.id)
    virulence = profile.virulence / table.neutral_virulence if profile is not None else 1.0
    dead = sum(value or 0 for key, value in impact.losses.items() if key in {entity.id for entity in struck})
    people = sum(stat_or(entity, POPULATION_KEY, 0) for entity in struck)
    infected = round_half_up(people * table.infected_pct / PERCENT * min(2.0, virulence))
    tally(disease, outbreak, infected=infected + dead, dead=dead)


async def strike(ctx: TickContext, target: EntityRow, disaster: Disaster, severity: int) -> tuple[EntityRow, DisasterImpact]:
    if disaster is Disaster.PLAGUE:
        return await strike_plague(ctx, target, severity)
    impact = await apply_disaster(ctx, target, disaster, severity / ctx.rules.disasters.scale_divisor)
    await scar_land(ctx, target, disaster, severity)
    event = await record_disaster_event(ctx, target, disaster, severity, impact)
    await after_strike(ctx, target, disaster, severity, event, impact=impact)
    return event, impact


async def after_strike(ctx: TickContext, target: EntityRow, disaster: Disaster, severity: int, event: EntityRow, *, impact: DisasterImpact) -> None:
    await silt_land(ctx, target, disaster, severity)
    if disaster is Disaster.FLOOD and await river_after_flood(ctx, target, severity, event) is not None:
        impact.notes.append("the river left its bed")
        impact.steps.append(StepDraft(StepAction.FLOOD_LAND, locus_kind=StepLocus.REGION, locus_node=target.id, outcome=StepOutcome.SUCCESS))
    elif disaster is Disaster.EARTHQUAKE and await river_after_quake(ctx, target, severity, event) is not None:
        impact.notes.append("the ground shook the river from its bed")
        impact.steps.append(StepDraft(StepAction.QUAKE, locus_kind=StepLocus.REGION, locus_node=target.id, outcome=StepOutcome.SUCCESS))
    elif disaster is Disaster.ERUPTION:
        await erupted(ctx, target, severity)
        impact.notes.append("ash buried the fields")
        impact.steps.append(StepDraft(StepAction.ERUPT, locus_kind=StepLocus.REGION, locus_node=target.id, outcome=StepOutcome.SUCCESS))
        cooled = await cold_snap(ctx, target.world_id, ctx.rules.world_life.volcano_cold) if target.world_id is not None else 0
        if cooled and target.world_id is not None:
            impact.notes.append("ash in the sky cooled the world")
            await record(
                ctx,
                "climate.ash_cold",
                roles={IncidentRole.PLACE: target.id, IncidentRole.SUBJECT: target.world_id},
                facts={"cold": ctx.rules.world_life.volcano_cold, "regions": cooled},
                place=target.id,
                world_id=target.world_id,
            )
    elif disaster is Disaster.VOLCANIC_QUAKE and await quaked(ctx, target):
        woken, _ = await strike(ctx, target, Disaster.ERUPTION, severity)
        impact.notes.append(f"the shaking woke {woken.name}")
        impact.steps.append(StepDraft(StepAction.APPEAR, target=woken.id, outcome=StepOutcome.SUCCESS))


async def silt_land(ctx: TickContext, target: EntityRow, disaster: Disaster, severity: int) -> None:
    table = ctx.rules.nutrients
    gift = {Disaster.FLOOD: table.flood_mineral, Disaster.ERUPTION: table.ash_mineral}.get(disaster, 0)
    region = await top_region(ctx.session, target) if gift else None
    if region is not None:
        await deposit(ctx, region.id, NutrientKind.MINERAL, round_half_up(gift * severity / PERCENT))


def disaster_steps(target: EntityRow, impact: DisasterImpact) -> tuple[StepDraft, ...]:
    begin = StepDraft(StepAction.BEGIN, locus_kind=StepLocus.REGION if target.entity_type is EntityType.REGION else StepLocus.SETTLEMENT, locus_node=target.id)
    return (begin, *impact.steps, StepDraft(StepAction.END, locus_node=target.id))


async def record_strike(
    ctx: TickContext,
    key: str,
    target: EntityRow,
    struck: tuple[Disaster, int, EntityRow, DisasterImpact],
    *,
    extra: Mapping[str, FactInput] | None = None,
    authority: int | None = None,
) -> None:
    disaster, severity, event, impact = struck
    roles: dict[IncidentRole, RoleValue] = {IncidentRole.PLACE: target.id, IncidentRole.VICTIM: impact.struck(), IncidentRole.SUBJECT: event.id}
    if authority is not None:
        roles[IncidentRole.AUTHORITY] = authority
    await record(
        ctx,
        key,
        roles=roles,
        facts={
            "disaster": disaster,
            "severity": severity,
            "lost": impact.lost(),
            "dead": len(impact.dead),
            "destroyed": len(impact.destroyed),
            "sickness": impact.sickness,
            **(extra or {}),
        },
        steps=disaster_steps(target, impact),
        place=target.id,
        world_id=target.world_id,
        magnitude=min(PERCENT, severity),
    )


async def _region_disasters(ctx: TickContext, world: DisasterWorld) -> None:
    atlas = await RegionAtlas.load(ctx.session)
    grounds = await EnvironmentBook.load(ctx.session, ctx.rules, ctx.epoch, atlas)
    shapes = await shapes_by_region(ctx.session)
    regional_population: dict[int, int] = {}
    for community in await canon(ctx.session, SOCIETY_TYPES):
        home = atlas.top_region(community.id)
        if home is not None:
            regional_population[home] = regional_population.get(home, 0) + stat_or(community, "population", 0)
    for region in unheld(await canon(ctx.session, [EntityType.REGION])):
        if world.struck >= ctx.rules.disasters.cap:
            return
        if atlas.is_water(region.id) or region.is_water:
            continue
        rng = ctx.rng(f"region_disaster.{region.id}")
        ground = grounds.regions.get(region.id)
        planet = grounds.worlds.get(region.world_id)
        tidal = (planet.tidal_strength or 0) if planet is not None else 0
        shape = shapes.get(region.id)
        candidates = region_candidates(ctx, region, atlas, regional_population.get(region.id, 0), world.laws, ground=ground, tidal=tidal, shape=shape)
        for disaster, base in candidates:
            chance = await paced(ctx, region.world_id, SpontaneousKind.PLAGUE, base) if disaster is Disaster.PLAGUE else base
            climate = world.climate_mult(region.world_id) if disaster is Disaster.PLAGUE else 1.0
            if not rng.chance(
                chance
                * world.law_mult(ctx.rules, region.world_id)
                * climate
                * world.nature_mult(ctx.rules, region.world_id, disaster)
                * world.fortune_mult(ctx.rules, region.id)
            ):
                continue
            severity = severity_roll(ctx, f"severity.{region.id}")
            key = f"disasters.{Disaster(disaster).value}"
            async with recording(ctx, key, place_id=region.id, world_id=region.world_id):
                event, impact = await strike(ctx, region, disaster, severity)
                world.struck += 1
                await record_strike(ctx, key, region, (disaster, severity, event, impact))
            break


async def _city_plagues(ctx: TickContext, world: DisasterWorld) -> None:
    settings = ctx.rules.disasters
    cities = await canon(ctx.session, [EntityType.SETTLEMENT])
    crowd = relative_threshold(
        cities, "population", fraction(settings.city_plague_top_pct), settings.city_plague_crowd_floor, settings.city_plague_always_population
    )
    hostility = (await BondIndex.load(ctx.session, [BondKind.ENEMY])).bonds
    at_war = {bond.source_node_id for bond in hostility} | {bond.target_node_id for bond in hostility}
    effects = ctx.rules.world_effects
    for city in cities:
        population = stat_or(city, "population", 0)
        if held(city.id) or population < settings.city_plague_min_population or world.struck >= settings.cap:
            continue
        crowded = population >= crowd(city)
        hungry = (await society_of(ctx.session, ctx.rules, city.id)).stocks[Commodity.FOOD] < effects.hungry_food
        war = city.id in at_war
        chance = (settings.city_plague_chance if crowded else 0) + (settings.hungry_plague_chance if hungry else 0) + (settings.war_plague_chance if war else 0)
        nature = world.nature_mult(ctx.rules, city.world_id, Disaster.PLAGUE)
        if not chance or not ctx.rng(f"city_plague.{city.id}").chance(chance * world.plague_mult(ctx.rules, city.world_id) * nature):
            continue
        severity = severity_roll(ctx, f"city_severity.{city.id}")
        async with recording(ctx, "disasters.city_plague", place_id=city.id, world_id=city.world_id):
            event, impact = await strike(ctx, city, Disaster.PLAGUE, severity)
            world.struck += 1
            await record_strike(ctx, "disasters.city_plague", city, (Disaster.PLAGUE, severity, event, impact), extra={"chance": chance})


def route_chance(rules: Rules, volume: int) -> float:
    table = rules.epidemiology
    busy = max(table.route_volume_floor_pct / PERCENT, min(table.route_volume_cap_pct / PERCENT, volume / max(1, table.route_busy_volume)))
    return table.route_spread_chance * busy


async def route_volumes(ctx: TickContext) -> dict[int, dict[int, int]]:
    volumes: dict[int, dict[int, int]] = {}
    for link in await trade_links(ctx):
        for here, there in ((link.first, link.second), (link.second, link.first)):
            volumes.setdefault(here, {})[there] = max(volumes.get(here, {}).get(there, 0), link.volume)
    return volumes


async def _plague_spread(ctx: TickContext) -> int:
    settings = ctx.rules.disasters
    session = ctx.session
    plagues = [
        event
        for event in await canon(session, [EntityType.EVENT])
        if event.engine_kind is EngineKind.PLAGUE and event.birth_epoch >= ctx.epoch - settings.plague_spread_epochs
    ]
    links = await BondIndex.load(session, [*SPREAD_BOND_KINDS, BondKind.CAUSED])
    roads = await route_volumes(ctx)
    knowledge = await KnowledgeMap.load(session)
    book = await DiseaseBook.load(session, ctx.rules, ctx.epoch)
    medicine_cut = settings.plague_spread_medicine_chance / max(1, settings.plague_spread_chance)
    spread = 0
    for plague in plagues:
        caused = links.outgoing(plague.id, BondKind.CAUSED)
        outbreak = book.of_event(plague.id)
        disease = book.diseases.get(outbreak.disease_entity_id) if outbreak is not None else None
        if not caused:
            continue
        source, struck = caused[0].target_node_id, {bond.target_node_id for bond in caused}
        bonded = {bond.other_end(source) for kind in SPREAD_BOND_KINDS for bond in links.touching(source, kind)}
        traffic = roads.get(source, {})
        partners = sorted((bonded | set(traffic)) - struck - {source})
        for partner_id in partners:
            partner = await session.get(EntityRow, partner_id)
            if partner is None or partner.status is not EntityStatus.CANON or partner.entity_type not in COMMUNITY_TYPES:
                continue
            on_route = partner.id in traffic
            chance = route_chance(ctx.rules, traffic[partner.id]) if on_route else float(settings.plague_spread_chance)
            if knowledge.knows(partner.id, KnowledgeBranch.MEDICINE):
                chance *= medicine_cut
            path = SpreadPath.ROUTE if on_route else SpreadPath.ORIGIN
            target_region = book.atlas.top_region(partner.id)
            ground = await session.get(RegionEnvironmentRow, target_region) if target_region is not None else None
            pressure = (
                spread_factor(
                    book,
                    disease.id,
                    partner,
                    ground,
                    source_region=book.atlas.top_region(source),
                    path=path,
                    hidden=book.unseen(outbreak),
                    sealed=outbreak is not None and outbreak.quarantined,
                )
                if disease is not None
                else 1.0
            )
            if not ctx.rng(f"plague_spread.{plague.id}.{partner.id}").chance(min(100, chance * pressure)):
                continue
            lethal = lethality_factor(book, disease.id, [partner], knowledge) if disease is not None else 1.0
            if disease is not None and book.active_of(disease.id, target_region) is None:
                lethal *= 1 - book.hidden_share(disease.id) * ctx.rules.epidemiology.incubation_delay_pct / PERCENT
            token = STRIKING.set(book.profiles.get(disease.id) if disease is not None else None)
            try:
                with flowing(FlowCategory.PLAGUE):
                    impact = await apply_disaster(ctx, partner, Disaster.PLAGUE, fraction(settings.plague_spread_severity_pct) * lethal)
            finally:
                STRIKING.reset(token)
            if disease is not None and outbreak is not None and target_region is not None:
                landed = await open_outbreak(
                    ctx, book, disease, target_region, path=path, severity=outbreak.severity * settings.plague_spread_severity_pct // PERCENT, source=outbreak
                )
                record_toll(ctx, book, disease, landed, struck=[partner], impact=impact)
            links.add(await BondRepository(session).connect(BondDraft(plague.id, partner.id, BondKind.CAUSED, ctx.epoch, "spread along the roads")))
            await add_footprint(session, plague.id, target_region, ctx.epoch)
            spread += 1
            await record(
                ctx,
                "disasters.plague_spread",
                roles={IncidentRole.SUBJECT: plague.id, IncidentRole.ORIGIN: source, IncidentRole.DESTINATION: partner.id},
                facts={
                    "disaster": Disaster.PLAGUE,
                    "severity": settings.plague_spread_severity_pct * lethal,
                    "lost": impact.lost(),
                    "dead": len(impact.dead),
                    "destroyed": len(impact.destroyed),
                    "sickness": disease.id if disease is not None else None,
                    "chance": min(100, chance * pressure),
                },
                steps=disaster_steps(partner, impact),
                place=partner.id,
                origin=source,
                destination=partner.id,
                world_id=partner.world_id,
            )
    return spread


async def climate_plague_multipliers(ctx: TickContext) -> dict[int, int]:
    rows = await ctx.session.execute(select(WorldRow.id, WorldRow.climate_era))
    return {world_id: plague_pct(ctx.rules, era) for world_id, era in rows if era is not None}


@reads(
    "cult.followers",
    "event.severity",
    "item.protection",
    "mortal.age",
    "mortal.agility",
    "mortal.charisma",
    "mortal.creativity",
    "mortal.endurance",
    "mortal.hp",
    "mortal.intellect",
    "mortal.lifespan",
    "mortal.perception",
    "mortal.strength",
    "mortal.willpower",
    "mortal.wisdom",
    "people.population",
    "people.prosperity",
    "place.fertility",
    "region.fertility",
    "settlement.defense",
    "settlement.population",
    "settlement.prosperity",
    "table.assistive_aids",
    "table.augment_effects",
    "table.augments",
    "table.avatars",
    "table.bodies",
    "table.body_customs",
    "table.bonds",
    "table.calendars",
    "table.charms",
    "table.community_cohorts",
    "table.community_societies",
    "table.conditions",
    "table.cosmos",
    "table.creature_anatomy",
    "table.cult_tenets",
    "table.culture_values",
    "table.designated_heirs",
    "table.dimensional_events",
    "table.dimensions",
    "table.disease_cures",
    "table.disease_profiles",
    "table.districts",
    "table.divine_standing",
    "table.divine_wounds",
    "table.dominions",
    "table.drink_kinds",
    "table.endemic_diseases",
    "table.entities",
    "table.entity_flags",
    "table.entity_tags",
    "table.entity_traits",
    "table.event_casualties",
    "table.event_footprints",
    "table.event_profiles",
    "table.forced_weather",
    "table.foreign_gods",
    "table.galactic_structures",
    "table.galaxies",
    "table.galaxy_clusters",
    "table.genomes",
    "table.god_designs",
    "table.god_scales",
    "table.griefs",
    "table.herds",
    "table.holder_levels",
    "table.holder_techniques",
    "table.immunities",
    "table.impurity_sources",
    "table.incident_participants",
    "table.incidents",
    "table.incorporeal_rights",
    "table.incubating_ideas",
    "table.injuries",
    "table.insurance_policies",
    "table.insurers",
    "table.item_profiles",
    "table.kind_holdings",
    "table.language_profiles",
    "table.law_jurisdictions",
    "table.lexemes",
    "table.ley_lines",
    "table.marriages",
    "table.memories",
    "table.mind_attributes",
    "table.mind_profiles",
    "table.minds",
    "table.mortal_equipment",
    "table.mortal_profiles",
    "table.name_registry",
    "table.natural_law_profiles",
    "table.node_births",
    "table.nodes",
    "table.outbreaks",
    "table.passions",
    "table.people_culture",
    "table.personality_values",
    "table.place_environment",
    "table.plague_responses",
    "table.polity_members",
    "table.polity_profiles",
    "table.preparedness",
    "table.prostheses",
    "table.quarantines",
    "table.reconstructions",
    "table.region_dominion",
    "table.region_environment",
    "table.region_geomorphology",
    "table.river_shifts",
    "table.role_norms",
    "table.routes",
    "table.settlement_profiles",
    "table.sieges",
    "table.sky_events",
    "table.soil_nutrients",
    "table.sons",
    "table.species_hosts",
    "table.species_profiles",
    "table.species_ranges",
    "table.spirit_profiles",
    "table.stars",
    "table.storytellers",
    "table.structure_profiles",
    "table.theory_adherents",
    "table.theory_profiles",
    "table.trade_flows",
    "table.trade_route_profiles",
    "table.trade_route_regions",
    "table.trade_route_tolls",
    "table.tradition_profiles",
    "table.traits",
    "table.transform_prospects",
    "table.world_domain_hooks",
    "table.world_maps",
    "table.world_physics",
    "table.world_seasons",
    "table.worlds",
    "trade_route.culture",
)
@writes(
    "cult.followers",
    "mortal.death_year",
    "mortal.hp",
    "mortal.lifespan",
    "people.population",
    "people.prosperity",
    "place.fertility",
    "region.fertility",
    "settlement.defense",
    "settlement.population",
    "settlement.prosperity",
    "table.bodies",
    "table.body_customs",
    "table.bonds",
    "table.chronicle",
    "table.chronicle_entities",
    "table.conditions",
    "table.districts",
    "table.divine_standing",
    "table.entities",
    "table.entity_flags",
    "table.event_casualties",
    "table.event_footprints",
    "table.event_profiles",
    "table.griefs",
    "table.incident_facts",
    "table.incident_participants",
    "table.incident_steps",
    "table.incident_terms",
    "table.incidents",
    "table.injuries",
    "table.item_history",
    "table.marriages",
    "table.memories",
    "table.mind_facets",
    "table.mortal_profiles",
    "table.name_registry",
    "table.notable_years",
    "table.personality_values",
    "table.place_environment",
    "table.reconstructions",
    "table.region_environment",
    "table.region_geomorphology",
    "table.river_shifts",
    "table.soil_nutrients",
    "table.sons",
    "table.spirit_profiles",
    "table.thoughts",
)
async def natural_disasters(ctx: TickContext) -> None:
    views = await world_views(ctx.session, ctx.rules)
    bodies = {row.world_id: row for row in await ctx.session.scalars(select(WorldPhysicsRow))}
    world = DisasterWorld(await ctx.laws(), await climate_plague_multipliers(ctx), views=views, bodies=bodies, dominion=await DominionBook.load(ctx.session))
    await _region_disasters(ctx, world)
    await _city_plagues(ctx, world)
    ctx.count("disasters", world.struck)
    ctx.count("plague_spread", await _plague_spread(ctx))


async def send_disaster(ctx: TickContext, target_id: int, disaster: Disaster, severity: int | None = None, by_id: int | None = None) -> EntityRow:
    target = await ctx.session.get(EntityRow, target_id)
    if target is None:
        raise NotFoundError("No such place.")
    if target.entity_type not in LOCATION_TYPES or target.status is not EntityStatus.CANON:
        raise ValidationFailedError("Disasters strike regions, places and settlements.")
    rolled = severity if severity is not None else severity_roll(ctx, f"manual_severity.{target.id}")
    key = f"disasters.manual_{disaster.value}"
    async with recording(ctx, key, place_id=target.id, world_id=target.world_id):
        event, impact = await strike(ctx, target, disaster, rolled)
        await record_strike(ctx, key, target, (disaster, rolled, event, impact), authority=by_id)
    return event


PHASES = (Phase("natural_disasters", natural_disasters),)
