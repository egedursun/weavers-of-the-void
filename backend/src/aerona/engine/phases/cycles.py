from aerona.constants.units import PERCENT
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.factions import FactionMembershipRow
from aerona.db.tables.society import CommunitySocietyRow
from aerona.db.write_guard import held
from aerona.domain.enums.cycles import CyclePhase
from aerona.domain.enums.faction import FactionKind, FactionRank
from aerona.domain.enums.modifier import IncidentRole
from aerona.domain.enums.society import SocialClass
from aerona.engine.context import TickContext
from aerona.engine.cycles.asabiyya import AsabiyyaTally, keep_asabiyya
from aerona.engine.cycles.bondage import BondageTally, keep_bondage
from aerona.engine.cycles.book import realm_towns
from aerona.engine.cycles.challenge import ChallengeTally, meet_challenges
from aerona.engine.cycles.gifts import GiftTally, keep_gifts
from aerona.engine.cycles.kinship import KinshipTally, keep_kinship
from aerona.engine.cycles.legacy import LegacyTally, keep_legacies
from aerona.engine.cycles.nomads import NomadTally, keep_nomads
from aerona.engine.cycles.plans import PlanTally, advance_plans
from aerona.engine.cycles.reproduction import ReproductionTally, keep_reproduction
from aerona.engine.cycles.seeding import SeedTally, seed_peoples
from aerona.engine.cycles.stress import StressTally, aspirant_leader, read_stress
from aerona.engine.demography.bound import move_people, sync_bound_share
from aerona.engine.demography.cohorts import cohorts_of
from aerona.engine.interconnect.annotations import reads, writes
from aerona.engine.phase import Phase
from aerona.engine.phases.dominion import count
from aerona.engine.phases.factions import found_faction
from aerona.engine.primitives.queries import living_entity
from aerona.engine.primitives.stats import stat_or
from aerona.engine.recording.record import RoleValue, record
from aerona.engine.unions.keep import keep_unions


async def counter_elites(ctx: TickContext, polity: EntityRow, capital_id: int | None, overproduction: int, tally: StressTally) -> None:
    table = ctx.rules.structural_demography
    if overproduction < table.counter_elite_at or not ctx.rng(f"counter_elite.{polity.id}.{ctx.epoch}").chance(table.counter_elite_pct):
        return
    leader = await aspirant_leader(ctx, polity.id)
    capital = await living_entity(ctx.session, capital_id) if capital_id is not None else None
    if leader is None or capital is None or held(capital.id, leader.id):
        return
    faction = await found_faction(ctx, capital, FactionKind.NOBLE_COUNCIL)
    ctx.session.add(FactionMembershipRow(faction_entity_id=faction.id, mortal_entity_id=leader.id, rank=FactionRank.LEADER, joined_epoch=ctx.epoch, locked=[]))
    tally.counter_elites += 1
    roles: dict[IncidentRole, RoleValue] = {IncidentRole.LEADER: leader.id, IncidentRole.PRODUCT: faction.id, IncidentRole.OPPONENT: polity.id}
    await record(ctx, "stress.counter_elites", roles=roles, facts={"overproduction": overproduction}, place=capital.id)


def fall_from(society: CommunitySocietyRow | None, fall_pct: int) -> float:
    if society is None:
        return 0.0
    moved = round(society.share_noble * fall_pct / PERCENT, 2)
    society.share_noble = round(society.share_noble - moved, 2)
    society.share_outcast = round(min(PERCENT, society.share_outcast + moved), 2)
    return moved


async def thin_elites(ctx: TickContext, polity: EntityRow) -> int:
    table = ctx.rules.structural_demography
    fallen = 0
    for town in await realm_towns(ctx.session, polity.id):
        if held(town.id):
            continue
        rows = await cohorts_of(ctx.session, town.id)
        society = await ctx.session.get(CommunitySocietyRow, town.id)
        fallen += await move_people(ctx, town, rows, source=SocialClass.NOBLE, target=SocialClass.OUTCAST, share=table.elite_fall_pct / PERCENT)
        moved = fall_from(society, table.elite_fall_pct)
        fallen += round(stat_or(town, "population", 0) * moved / PERCENT) if not rows else 0
        sync_bound_share(society, rows)
    return fallen


@reads(
    "place.fertility",
    "region.breadth",
    "region.fertility",
    "settlement.population",
    "table.bonds",
    "table.cohorts",
    "table.community_cohorts",
    "table.community_societies",
    "table.cosmos",
    "table.creator",
    "table.dimensional_events",
    "table.dimensions",
    "table.entities",
    "table.exam_sittings",
    "table.foreign_gods",
    "table.galactic_structures",
    "table.galaxies",
    "table.galaxy_clusters",
    "table.holder_levels",
    "table.node_births",
    "table.nodes",
    "table.offices",
    "table.place_environment",
    "table.polity_members",
    "table.polity_profiles",
    "table.polity_stress",
    "table.region_environment",
    "table.settlement_profiles",
    "table.sons",
    "table.stars",
    "table.stress_readings",
    "table.title_profiles",
    "table.worlds",
)
@writes(
    "table.chronicle",
    "table.chronicle_entities",
    "table.cohorts",
    "table.community_cohorts",
    "table.community_societies",
    "table.entities",
    "table.faction_memberships",
    "table.faction_profiles",
    "table.incident_facts",
    "table.incident_participants",
    "table.incidents",
    "table.polity_stress",
    "table.stress_readings",
)
async def structural_demography(ctx: TickContext) -> None:
    tally = StressTally()
    for polity, profile, row in await read_stress(ctx, tally):
        await counter_elites(ctx, polity, profile.capital_entity_id, row.elite_overproduction, tally)
        if row.phase is CyclePhase.CRISIS:
            fallen = await thin_elites(ctx, polity)
            if fallen:
                await record(ctx, "stress.elites_fell", roles={IncidentRole.SUBJECT: polity.id}, facts={"fallen": fallen, "psi": row.psi})
    count(ctx, "stress", tally)


@reads(
    "table.asabiyya",
    "table.bonds",
    "table.community_societies",
    "table.culture_values",
    "table.entities",
    "table.nodes",
    "table.people_culture",
    "table.polity_members",
    "table.polity_profiles",
    "table.polity_stress",
    "table.war_sides",
    "table.wars",
)
@writes("table.asabiyya", "table.people_culture")
async def asabiyya(ctx: TickContext) -> None:
    tally = AsabiyyaTally()
    await keep_asabiyya(ctx, tally)
    count(ctx, "asabiyya", tally)


@reads(
    "place.fertility",
    "region.breadth",
    "region.fertility",
    "settlement.population",
    "table.asabiyya",
    "table.bias_weights",
    "table.bonds",
    "table.cosmos",
    "table.creator",
    "table.dimensional_events",
    "table.dimensions",
    "table.entities",
    "table.foreign_gods",
    "table.galactic_structures",
    "table.galaxies",
    "table.galaxy_clusters",
    "table.holder_levels",
    "table.holder_techniques",
    "table.incident_participants",
    "table.incidents",
    "table.living_lines",
    "table.node_births",
    "table.nodes",
    "table.offices",
    "table.personality_values",
    "table.place_environment",
    "table.polity_members",
    "table.polity_profiles",
    "table.polity_stress",
    "table.power_sources",
    "table.public_knowledge",
    "table.relationships",
    "table.research_focus",
    "table.research_progress",
    "table.skills",
    "table.sons",
    "table.stars",
    "table.worlds",
)
@writes(
    "table.asabiyya",
    "table.bias_weights",
    "table.challenges",
    "table.chronicle",
    "table.chronicle_entities",
    "table.incident_facts",
    "table.incident_participants",
    "table.incidents",
    "table.polity_profiles",
    "table.polity_stress",
    "table.research_progress",
)
async def challenge_response(ctx: TickContext) -> None:
    tally = ChallengeTally()
    await meet_challenges(ctx, tally)
    count(ctx, "challenge", tally)


@reads("table.house_profiles", "table.long_plans", "table.offices", "table.polity_profiles")
@writes("table.bonds", "table.constructions", "table.entities", "table.house_profiles", "table.long_plans", "table.region_environment")
async def long_plans(ctx: TickContext) -> None:
    tally = PlanTally()
    await advance_plans(ctx, tally)
    count(ctx, "plans", tally)


@reads(
    "faction.wealth",
    "house.wealth",
    "people.piety",
    "people.wealth",
    "settlement.piety",
    "settlement.wealth",
    "table.action_records",
    "table.bonds",
    "table.ceremonial_circuits",
    "table.community_relations",
    "table.creator",
    "table.creator_taboos",
    "table.cult_doctrines",
    "table.culture_ethics",
    "table.culture_values",
    "table.dimensions",
    "table.divine_debts",
    "table.divine_standing",
    "table.entities",
    "table.faction_profiles",
    "table.foreign_gods",
    "table.galaxies",
    "table.galaxy_clusters",
    "table.gathering_guests",
    "table.gatherings",
    "table.geasa",
    "table.gifts",
    "table.held_identities",
    "table.house_members",
    "table.house_profiles",
    "table.incident_participants",
    "table.kinship_systems",
    "table.language_profiles",
    "table.marriages",
    "table.memories",
    "table.messages",
    "table.mind_profiles",
    "table.minds",
    "table.mortal_profiles",
    "table.node_births",
    "table.nodes",
    "table.personality_values",
    "table.polity_members",
    "table.polity_profiles",
    "table.professions_of_value",
    "table.relation_components",
    "table.relationships",
    "table.reputations",
    "table.ruler_currencies",
    "table.skills",
    "table.social_norms",
    "table.sons",
    "table.speaker_cohorts",
    "table.stars",
    "table.tradition_profiles",
    "table.traits",
    "table.worlds",
)
@writes(
    "faction.wealth",
    "house.wealth",
    "people.wealth",
    "settlement.wealth",
    "table.ceremonial_circuits",
    "table.chronicle",
    "table.chronicle_entities",
    "table.community_relations",
    "table.cult_doctrines",
    "table.divine_debts",
    "table.divine_standing",
    "table.entities",
    "table.faction_profiles",
    "table.gifts",
    "table.house_profiles",
    "table.incident_facts",
    "table.incident_participants",
    "table.incident_steps",
    "table.incidents",
    "table.memories",
    "table.mortal_profiles",
    "table.polity_profiles",
    "table.professions_of_value",
    "table.settlement_profiles",
)
async def reciprocity(ctx: TickContext) -> None:
    tally = GiftTally()
    await keep_gifts(ctx, tally)
    count(ctx, "gifts", tally)


@reads(
    "mortal.age",
    "table.bonds",
    "table.community_relations",
    "table.entities",
    "table.held_identities",
    "table.house_members",
    "table.house_profiles",
    "table.kinship_systems",
    "table.marriage_alliances",
    "table.marriages",
    "table.memories",
    "table.minds",
    "table.nodes",
    "table.people_culture",
    "table.relation_components",
    "table.relationships",
    "table.reputations",
    "table.ruler_currencies",
    "table.speaker_cohorts",
    "table.traits",
    "table.union_customs",
)
@writes(
    "table.bonds",
    "table.community_relations",
    "table.entities",
    "table.house_profiles",
    "table.marriage_alliances",
    "table.marriages",
    "table.memories",
    "table.union_customs",
)
async def kinship_systems(ctx: TickContext) -> None:
    tally = KinshipTally()
    await keep_unions(ctx)
    await keep_kinship(ctx, tally)
    count(ctx, "kinship", tally)


@reads("table.entities", "table.mortal_profiles", "table.nodes", "table.people_reproduction")
@writes("table.entities", "table.mortal_castes")
async def reproduction_systems(ctx: TickContext) -> None:
    tally = ReproductionTally()
    await keep_reproduction(ctx, tally)
    count(ctx, "reproduction", tally)


@reads(
    "mortal.charisma",
    "settlement.population",
    "settlement.wealth",
    "table.asabiyya",
    "table.bonds",
    "table.camps",
    "table.community_labour",
    "table.community_relations",
    "table.confederations",
    "table.creator",
    "table.creator_taboos",
    "table.culture_values",
    "table.dimensions",
    "table.entities",
    "table.foreign_gods",
    "table.galaxies",
    "table.galaxy_clusters",
    "table.geasa",
    "table.held_identities",
    "table.incident_participants",
    "table.incidents",
    "table.labour",
    "table.language_registers",
    "table.mind_profiles",
    "table.minds",
    "table.name_registry",
    "table.node_births",
    "table.nodes",
    "table.personality_values",
    "table.polity_members",
    "table.polity_profiles",
    "table.professions_of_value",
    "table.region_environment",
    "table.relation_components",
    "table.relationships",
    "table.reputations",
    "table.ruler_currencies",
    "table.settlement_profiles",
    "table.sons",
    "table.speaker_cohorts",
    "table.stars",
    "table.tradition_profiles",
    "table.traits",
    "table.treaty_profiles",
    "table.tributes",
    "table.worlds",
)
@writes(
    "table.asabiyya",
    "table.bonds",
    "table.camps",
    "table.chronicle",
    "table.chronicle_entities",
    "table.community_relations",
    "table.confederations",
    "table.entities",
    "table.incident_facts",
    "table.incident_participants",
    "table.incident_steps",
    "table.incidents",
    "table.memories",
    "table.name_registry",
    "table.polity_profiles",
    "table.region_environment",
    "table.treaty_clauses",
    "table.treaty_parties",
    "table.treaty_profiles",
    "table.tributes",
)
async def nomadism(ctx: TickContext) -> None:
    tally = NomadTally()
    await keep_nomads(ctx, tally)
    count(ctx, "nomads", tally)


@reads("table.bonds", "table.culture_values", "table.entities", "table.founding_myths", "table.nodes", "table.people_culture")
@writes("table.account_stances", "table.culture_values", "table.legacy_traits", "table.people_culture")
async def legacy_traits(ctx: TickContext) -> None:
    tally = LegacyTally()
    await keep_legacies(ctx, tally)
    count(ctx, "legacy", tally)


@reads(
    "settlement.population",
    "table.bonds",
    "table.cohorts",
    "table.community_societies",
    "table.constructions",
    "table.corvee_levies",
    "table.creator",
    "table.diasporas",
    "table.dimensions",
    "table.entities",
    "table.faction_profiles",
    "table.foreign_gods",
    "table.galaxies",
    "table.galaxy_clusters",
    "table.incident_participants",
    "table.incidents",
    "table.indentures",
    "table.labour",
    "table.labour_reasons",
    "table.law_jurisdictions",
    "table.law_profiles",
    "table.manumissions",
    "table.node_births",
    "table.nodes",
    "table.people_culture",
    "table.polity_members",
    "table.polity_profiles",
    "table.settlement_profiles",
    "table.slave_markets",
    "table.sons",
    "table.stars",
    "table.worlds",
)
@writes(
    "settlement.population",
    "table.accounts",
    "table.chronicle",
    "table.chronicle_entities",
    "table.cohorts",
    "table.constructions",
    "table.corvee_levies",
    "table.incident_facts",
    "table.incident_participants",
    "table.incidents",
    "table.indentures",
    "table.manumissions",
    "table.slave_markets",
)
async def labour_regimes(ctx: TickContext) -> None:
    tally = BondageTally()
    await keep_bondage(ctx, tally)
    count(ctx, "labour_regimes", tally)


@reads(
    "table.biology",
    "table.entities",
    "table.kinship_systems",
    "table.nodes",
    "table.people_biology",
    "table.people_culture",
    "table.people_reproduction",
    "table.role_norms",
)
@writes("table.kinship_systems", "table.people_reproduction", "table.union_customs")
async def people_customs(ctx: TickContext) -> None:
    tally = SeedTally()
    await seed_peoples(ctx, tally)
    count(ctx, "people_customs", tally)


PHASES = (
    Phase("people_customs", people_customs),
    Phase("structural_demography", structural_demography),
    Phase("asabiyya", asabiyya),
    Phase("challenge_response", challenge_response),
    Phase("long_plans", long_plans),
    Phase("reciprocity", reciprocity),
    Phase("kinship_systems", kinship_systems),
    Phase("reproduction_systems", reproduction_systems),
    Phase("nomadism", nomadism),
    Phase("legacy_traits", legacy_traits),
    Phase("labour_regimes", labour_regimes),
)
