from dataclasses import dataclass
from functools import partial

from aerona.catalog.collective import ACT_COLLECTION, FAITH_ACTS
from aerona.db.tables.entities import EntityRow
from aerona.domain.enums.collective import CollectiveActKind
from aerona.domain.enums.faction import FactionKind
from aerona.domain.enums.gathering import CollectionRole
from aerona.domain.enums.modifier import IncidentRole
from aerona.domain.enums.records import StepAction
from aerona.engine.collective.accounts import (
    HistoryTally,
    age_accounts,
    believe_myths,
    fade_struck,
    find_scandals,
    mark_anniversaries,
    press_lost_lands,
    relive,
    rewrite_reigns,
    write_accounts,
)
from aerona.engine.collective.crowds import CrowdTally, rage_mobs, ready_to_arm, stir_towns, tend_movements
from aerona.engine.collective.dating import DatingTally, keep_calendars
from aerona.engine.collective.demography import DemographyTally, keep_demography
from aerona.engine.collective.designs import DesignTally, refit
from aerona.engine.collective.generations import GenerationTally, keep_generations
from aerona.engine.collective.heraldry import HeraldryTally, keep_heraldry
from aerona.engine.collective.learning import LearningTally, learn_socially
from aerona.engine.collective.norm_drift import keep_norm_drift
from aerona.engine.collective.norms import NormTally, keep_norms
from aerona.engine.collective.roles import RoleTally, keep_roles
from aerona.engine.collective.storylets import StoryletTally, announce, open_storylets, settle_due
from aerona.engine.context import TickContext
from aerona.engine.history.collections import open_collection
from aerona.engine.interconnect.annotations import reads, writes
from aerona.engine.phase import Phase
from aerona.engine.phases.dominion import count
from aerona.engine.phases.factions import found_faction
from aerona.engine.recording.record import StepDraft, record
from aerona.engine.vehicles.fleet import newer_frame


@dataclass
class ArmedTally:
    armed: int = 0
    revolts: int = 0


@reads(
    "mortal.charisma",
    "settlement.population",
    "table.collection_members",
    "table.collection_places",
    "table.community_societies",
    "table.crowd_moods",
    "table.districts",
    "table.entities",
    "table.faction_profiles",
    "table.held_identities",
    "table.incident_participants",
    "table.incidents",
    "table.indentures",
    "table.mind_facets",
    "table.node_births",
    "table.nodes",
    "table.offices",
    "table.outbreaks",
    "table.polity_members",
    "table.polity_profiles",
    "table.polity_stress",
    "table.satires",
    "table.settlement_profiles",
    "table.sky_events",
)
@writes(
    "table.cascades",
    "table.chronicle",
    "table.chronicle_entities",
    "table.collection_members",
    "table.collection_places",
    "table.community_societies",
    "table.crowd_moods",
    "table.incident_collections",
    "table.incident_facts",
    "table.incident_participants",
    "table.incident_steps",
    "table.incidents",
    "table.mobs",
    "table.movements",
)
async def crowds(ctx: TickContext) -> None:
    tally = CrowdTally()
    await stir_towns(ctx, tally)
    count(ctx, "crowd", tally)


@reads("table.mobs", "table.polity_profiles", "table.settlement_profiles")
@writes("table.districts", "table.mobs", "table.polity_profiles", "table.settlement_profiles")
async def mobs(ctx: TickContext) -> None:
    tally = CrowdTally()
    await rage_mobs(ctx, tally)
    count(ctx, "mob", tally)


async def arm_movements(ctx: TickContext, tally: ArmedTally) -> None:
    for movement in await ready_to_arm(ctx):
        town = await ctx.session.get(EntityRow, movement.settlement_entity_id)
        if town is None:
            continue
        kind = FactionKind.MOVEMENT if movement.act in FAITH_ACTS else FactionKind.REBELS
        faction = await found_faction(ctx, town, kind)
        movement.faction_entity_id = faction.id
        tally.armed += 1
        if movement.act not in FAITH_ACTS:
            movement.act = CollectiveActKind.REVOLT
            tally.revolts += 1
            await open_collection(
                ctx,
                ACT_COLLECTION[CollectiveActKind.REVOLT],
                world_id=town.world_id,
                members={faction.id: CollectionRole.LEADER, town.id: CollectionRole.PLACE},
                places=[town.id],
            )
        await record(
            ctx,
            "collective.movement_armed",
            roles={IncidentRole.PLACE: town.id, IncidentRole.PRODUCT: faction.id},
            facts={"act": movement.act, "members": movement.members, "strength": movement.strength},
            steps=(StepDraft(StepAction.FOUND, target=faction.id),),
            place=town.id,
        )
    await ctx.session.flush()


@reads(
    "faction.wealth",
    "table.bonds",
    "table.collection_members",
    "table.collection_places",
    "table.crowd_moods",
    "table.entities",
    "table.incident_participants",
    "table.incidents",
    "table.movements",
    "table.name_registry",
    "table.node_births",
    "table.nodes",
)
@writes(
    "table.bonds",
    "table.chronicle",
    "table.chronicle_entities",
    "table.collection_members",
    "table.collection_places",
    "table.entities",
    "table.faction_profiles",
    "table.incident_collections",
    "table.incident_facts",
    "table.incident_participants",
    "table.incident_steps",
    "table.incidents",
    "table.movements",
    "table.name_registry",
    "table.node_births",
)
async def popular_movements(ctx: TickContext) -> None:
    tally = CrowdTally()
    await tend_movements(ctx, tally)
    count(ctx, "movement", tally)
    armed = ArmedTally()
    await arm_movements(ctx, armed)
    count(ctx, "movement_armed", armed)


@reads(
    "table.bonds",
    "table.community_relations",
    "table.culture_values",
    "table.entities",
    "table.law_jurisdictions",
    "table.law_profiles",
    "table.nodes",
    "table.polity_members",
    "table.social_norms",
)
@writes("table.norm_changes", "table.social_norms")
async def social_norms(ctx: TickContext) -> None:
    tally = NormTally()
    await keep_norms(ctx, tally)
    await keep_norm_drift(ctx, tally)
    count(ctx, "norm", tally)


@reads(
    "table.account_stances",
    "table.accounts",
    "table.artwork_profiles",
    "table.collection_incidents",
    "table.collection_members",
    "table.collection_places",
    "table.culture_values",
    "table.data_stores",
    "table.deed_claims",
    "table.deeds",
    "table.entities",
    "table.held_identities",
    "table.house_members",
    "table.incident_collections",
    "table.memory_strikes",
    "table.mortal_profiles",
    "table.nodes",
    "table.offices",
    "table.polity_members",
    "table.polity_profiles",
)
@writes(
    "table.account_stances",
    "table.accounts",
    "table.chronicle",
    "table.chronicle_entities",
    "table.entities",
    "table.incident_participants",
    "table.incidents",
    "table.memory_strikes",
    "table.mortal_profiles",
    "table.polity_profiles",
    "table.secrets",
)
async def historiography(ctx: TickContext) -> None:
    tally = HistoryTally()
    await write_accounts(ctx, tally)
    await age_accounts(ctx, tally)
    await rewrite_reigns(ctx, tally)
    await find_scandals(ctx, tally)
    await fade_struck(ctx, tally)
    count(ctx, "history", tally)


@reads(
    "table.accounts",
    "table.collection_members",
    "table.entities",
    "table.founding_myths",
    "table.incident_collections",
    "table.incident_participants",
    "table.incidents",
    "table.mortal_profiles",
    "table.node_births",
    "table.nodes",
    "table.polity_members",
    "table.polity_profiles",
    "table.settlement_profiles",
)
@writes(
    "table.account_stances",
    "table.accounts",
    "table.chronicle",
    "table.chronicle_entities",
    "table.founding_myths",
    "table.incident_facts",
    "table.incident_participants",
    "table.incident_terms",
    "table.incidents",
    "table.polity_profiles",
    "table.settlement_profiles",
)
async def founding_myths(ctx: TickContext) -> None:
    tally = HistoryTally()
    await believe_myths(ctx, tally)
    count(ctx, "founding_myth", tally)


@reads(
    "table.collection_members",
    "table.commemorations",
    "table.creator",
    "table.dimensions",
    "table.entities",
    "table.foreign_gods",
    "table.galaxies",
    "table.galaxy_clusters",
    "table.incident_collections",
    "table.mortal_profiles",
    "table.node_births",
    "table.nodes",
    "table.polity_members",
    "table.polity_profiles",
    "table.sons",
    "table.stars",
    "table.worlds",
)
@writes(
    "table.chronicle",
    "table.chronicle_entities",
    "table.commemorations",
    "table.incident_facts",
    "table.incident_participants",
    "table.incident_terms",
    "table.incidents",
    "table.settlement_profiles",
)
async def commemorations(ctx: TickContext) -> None:
    tally = HistoryTally()
    await mark_anniversaries(ctx, tally)
    await relive(ctx, tally)
    count(ctx, "commemoration", tally)


@reads("table.commemorations", "table.lost_lands", "table.polity_territories")
@writes("table.casus_belli", "table.lost_lands")
async def lost_lands(ctx: TickContext) -> None:
    tally = HistoryTally()
    await press_lost_lands(ctx, tally)
    count(ctx, "lost_land", tally)


@reads(
    "mortal.age",
    "mortal.lifespan",
    "settlement.population",
    "table.arcs",
    "table.bonds",
    "table.cascades",
    "table.collection_members",
    "table.collection_places",
    "table.community_societies",
    "table.entities",
    "table.incident_collections",
    "table.incident_participants",
    "table.incidents",
    "table.mortal_profiles",
    "table.node_births",
    "table.nodes",
    "table.offices",
    "table.polity_members",
    "table.polity_profiles",
    "table.settlement_profiles",
    "table.storylet_runs",
    "table.storytellers",
    "table.worlds",
)
@writes(
    "table.casus_belli",
    "table.chronicle",
    "table.chronicle_entities",
    "table.claims",
    "table.collection_members",
    "table.designated_heirs",
    "table.incident_collections",
    "table.incident_facts",
    "table.incident_participants",
    "table.incidents",
    "table.storylet_runs",
)
async def storylets(ctx: TickContext) -> None:
    tally = StoryletTally()
    await announce(ctx, tally)
    await settle_due(ctx, tally)
    await open_storylets(ctx, tally)
    count(ctx, "storylet", tally)


@reads(
    "table.crowd_moods",
    "table.entities",
    "table.learning_biases",
    "table.mortal_profiles",
    "table.nodes",
    "table.personality_values",
    "table.settlement_profiles",
)
@writes("table.learning_biases", "table.learning_events", "table.personality_values")
async def social_learning(ctx: TickContext) -> None:
    tally = LearningTally()
    await learn_socially(ctx, tally)
    count(ctx, "social_learning", tally)


@reads(
    "people.population",
    "settlement.population",
    "table.collection_members",
    "table.collection_places",
    "table.community_cohorts",
    "table.community_societies",
    "table.creator",
    "table.dimensions",
    "table.entities",
    "table.foreign_gods",
    "table.galaxies",
    "table.galaxy_clusters",
    "table.generations",
    "table.incident_collections",
    "table.node_births",
    "table.nodes",
    "table.settlement_profiles",
    "table.sons",
    "table.stars",
    "table.worlds",
)
@writes(
    "table.chronicle",
    "table.chronicle_entities",
    "table.culture_values",
    "table.generations",
    "table.incident_facts",
    "table.incident_participants",
    "table.incidents",
    "table.settlement_profiles",
)
async def generations(ctx: TickContext) -> None:
    tally = GenerationTally()
    await keep_generations(ctx, tally)
    count(ctx, "generation", tally)


@reads(
    "table.community_cohorts",
    "table.demographic_transitions",
    "table.diasporas",
    "table.entities",
    "table.nodes",
    "table.people_culture",
    "table.role_norms",
    "table.settlement_profiles",
    "table.sex_ratios",
)
@writes("table.demographic_transitions", "table.diasporas", "table.districts", "table.settlement_profiles", "table.sex_ratios")
async def demography_depth(ctx: TickContext) -> None:
    tally = DemographyTally()
    await keep_demography(ctx, tally)
    count(ctx, "demography_depth", tally)


@reads("table.culture_values", "table.entities", "table.nodes", "table.role_norms", "table.sex_ratios")
@writes("table.role_norms")
async def role_norms(ctx: TickContext) -> None:
    tally = RoleTally()
    await keep_roles(ctx, tally)
    count(ctx, "role_norm", tally)


@reads("table.calendars", "table.cosmos", "table.dating_systems", "table.entities", "table.holder_techniques", "table.nodes", "table.offices")
@writes("table.dating_systems")
async def dating_systems(ctx: TickContext) -> None:
    tally = DatingTally()
    await keep_calendars(ctx, tally)
    count(ctx, "dating", tally)


@reads(
    "table.armies",
    "table.arms",
    "table.company_profiles",
    "table.creator",
    "table.culture_values",
    "table.dimensions",
    "table.entities",
    "table.faction_profiles",
    "table.foreign_gods",
    "table.galaxies",
    "table.galaxy_clusters",
    "table.house_members",
    "table.house_profiles",
    "table.incident_participants",
    "table.incidents",
    "table.marriages",
    "table.node_births",
    "table.nodes",
    "table.polity_profiles",
    "table.sons",
    "table.stars",
    "table.title_profiles",
    "table.worlds",
)
@writes(
    "table.arms",
    "table.chronicle",
    "table.chronicle_entities",
    "table.house_profiles",
    "table.incident_facts",
    "table.incident_participants",
    "table.incidents",
    "table.polity_profiles",
    "table.title_profiles",
)
async def heraldry(ctx: TickContext) -> None:
    tally = HeraldryTally()
    await keep_heraldry(ctx, tally)
    count(ctx, "heraldry", tally)


@reads(
    "table.bonds",
    "table.cosmos",
    "table.design_components",
    "table.design_mounts",
    "table.design_sections",
    "table.designs",
    "table.entities",
    "table.equipment_models",
    "table.holder_levels",
    "table.incident_participants",
    "table.incidents",
    "table.language_profiles",
    "table.lexemes",
    "table.name_registry",
    "table.node_births",
    "table.nodes",
    "table.polity_profiles",
    "table.vessel_profiles",
    "table.world_materials",
)
@writes(
    "table.chronicle",
    "table.chronicle_entities",
    "table.design_components",
    "table.design_mounts",
    "table.design_sections",
    "table.design_techniques",
    "table.designs",
    "table.entities",
    "table.equipment_models",
    "table.incident_facts",
    "table.incident_participants",
    "table.incidents",
    "table.name_registry",
    "table.node_births",
    "table.vessel_profiles",
)
async def designs(ctx: TickContext) -> None:
    tally = DesignTally()
    await refit(ctx, tally, partial(newer_frame, ctx.rules))
    count(ctx, "design", tally)


PHASES = (
    Phase("crowds", crowds),
    Phase("mobs", mobs),
    Phase("popular_movements", popular_movements),
    Phase("social_norms", social_norms),
    Phase("historiography", historiography),
    Phase("founding_myths", founding_myths),
    Phase("commemorations", commemorations),
    Phase("lost_lands", lost_lands),
    Phase("storylets", storylets),
    Phase("social_learning", social_learning),
    Phase("generations", generations),
    Phase("demography_depth", demography_depth),
    Phase("role_norms", role_norms),
    Phase("dating_systems", dating_systems),
    Phase("heraldry", heraldry),
    Phase("designs", designs),
)
