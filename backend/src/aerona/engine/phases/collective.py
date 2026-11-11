from dataclasses import dataclass

from aerona.catalog.collective import ACT_COLLECTION, FAITH_ACTS
from aerona.db.tables.entities import EntityRow
from aerona.domain.enums.collective import CollectiveActKind
from aerona.domain.enums.faction import FactionKind
from aerona.domain.enums.gathering import CollectionRole
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
from aerona.engine.collective.norms import NormTally, keep_norms
from aerona.engine.collective.roles import RoleTally, keep_roles
from aerona.engine.collective.storylets import StoryletTally, announce, open_storylets, settle_due
from aerona.engine.context import TickContext
from aerona.engine.history.collections import open_collection
from aerona.engine.interconnect.annotations import reads, writes
from aerona.engine.notes import note
from aerona.engine.phase import Phase
from aerona.engine.phases.dominion import count
from aerona.engine.phases.factions import found_faction


@dataclass
class ArmedTally:
    armed: int = 0
    revolts: int = 0


@reads(
    "settlement.population",
    "table.crowd_moods",
    "table.districts",
    "table.faction_profiles",
    "table.incidents",
    "table.mind_facets",
    "table.outbreaks",
    "table.settlement_profiles",
    "table.sky_events",
)
@writes("table.cascades", "table.community_societies", "table.crowd_moods", "table.incident_collections", "table.mobs", "table.movements")
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
        await note(ctx, f"The movement in {town.name} became {faction.name}.", key="collective.movement_armed", ids=[faction.id, town.id])
    await ctx.session.flush()


@reads("table.crowd_moods", "table.movements")
@writes("table.entities", "table.faction_profiles", "table.movements")
async def popular_movements(ctx: TickContext) -> None:
    tally = CrowdTally()
    await tend_movements(ctx, tally)
    count(ctx, "movement", tally)
    armed = ArmedTally()
    await arm_movements(ctx, armed)
    count(ctx, "movement_armed", armed)


@reads("table.bonds", "table.culture_values", "table.law_jurisdictions", "table.law_profiles", "table.polity_members", "table.social_norms")
@writes("table.norm_changes", "table.social_norms")
async def social_norms(ctx: TickContext) -> None:
    tally = NormTally()
    await keep_norms(ctx, tally)
    count(ctx, "norm", tally)


@reads(
    "table.account_stances",
    "table.accounts",
    "table.artwork_profiles",
    "table.collection_members",
    "table.collection_places",
    "table.culture_values",
    "table.house_members",
    "table.incident_collections",
    "table.memory_strikes",
    "table.mortal_profiles",
    "table.offices",
    "table.polity_members",
    "table.polity_profiles",
)
@writes(
    "table.account_stances",
    "table.accounts",
    "table.chronicle",
    "table.chronicle_entities",
    "table.epoch_year_cursors",
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


@reads("table.accounts", "table.founding_myths", "table.polity_profiles")
@writes(
    "table.account_stances",
    "table.accounts",
    "table.chronicle",
    "table.chronicle_entities",
    "table.epoch_year_cursors",
    "table.founding_myths",
    "table.incident_participants",
    "table.incidents",
    "table.polity_profiles",
    "table.settlement_profiles",
)
async def founding_myths(ctx: TickContext) -> None:
    tally = HistoryTally()
    await believe_myths(ctx, tally)
    count(ctx, "founding_myth", tally)


@reads(
    "table.collection_members", "table.commemorations", "table.incident_collections", "table.mortal_profiles", "table.polity_members", "table.polity_profiles"
)
@writes("table.commemorations", "table.settlement_profiles")
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
    "table.bonds",
    "table.collection_members",
    "table.collection_places",
    "table.incident_collections",
    "table.offices",
    "table.polity_members",
    "table.polity_profiles",
    "table.storylet_runs",
    "table.storytellers",
)
@writes(
    "table.casus_belli",
    "table.chronicle",
    "table.chronicle_entities",
    "table.claims",
    "table.collection_members",
    "table.designated_heirs",
    "table.epoch_year_cursors",
    "table.incident_collections",
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


@reads("table.crowd_moods", "table.learning_biases", "table.personality_values")
@writes("table.learning_biases", "table.learning_events", "table.personality_values")
async def social_learning(ctx: TickContext) -> None:
    tally = LearningTally()
    await learn_socially(ctx, tally)
    count(ctx, "social_learning", tally)


@reads("table.community_cohorts", "table.generations", "table.incident_collections")
@writes("table.culture_values", "table.generations", "table.settlement_profiles")
async def generations(ctx: TickContext) -> None:
    tally = GenerationTally()
    await keep_generations(ctx, tally)
    count(ctx, "generation", tally)


@reads(
    "table.community_cohorts",
    "table.demographic_transitions",
    "table.diasporas",
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


@reads("table.culture_values", "table.role_norms", "table.sex_ratios")
@writes("table.role_norms")
async def role_norms(ctx: TickContext) -> None:
    tally = RoleTally()
    await keep_roles(ctx, tally)
    count(ctx, "role_norm", tally)


@reads("table.calendars", "table.dating_systems", "table.holder_techniques", "table.offices")
@writes("table.dating_systems")
async def dating_systems(ctx: TickContext) -> None:
    tally = DatingTally()
    await keep_calendars(ctx, tally)
    count(ctx, "dating", tally)


@reads(
    "table.armies",
    "table.arms",
    "table.faction_profiles",
    "table.house_members",
    "table.house_profiles",
    "table.marriages",
    "table.polity_profiles",
    "table.title_profiles",
)
@writes(
    "table.arms",
    "table.chronicle",
    "table.chronicle_entities",
    "table.epoch_year_cursors",
    "table.house_profiles",
    "table.incident_participants",
    "table.incidents",
    "table.polity_profiles",
    "table.title_profiles",
)
async def heraldry(ctx: TickContext) -> None:
    tally = HeraldryTally()
    await keep_heraldry(ctx, tally)
    count(ctx, "heraldry", tally)


@reads("table.design_components", "table.designs")
@writes("table.design_components", "table.designs", "table.vessel_profiles")
async def designs(ctx: TickContext) -> None:
    tally = DesignTally()
    await refit(ctx, tally)
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
