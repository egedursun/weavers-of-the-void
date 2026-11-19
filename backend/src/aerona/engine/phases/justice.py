from aerona.engine.context import TickContext
from aerona.engine.interconnect.annotations import reads, writes
from aerona.engine.phase import Phase
from aerona.engine.polity.enactment import EnactmentTally, tend_proposals
from aerona.engine.polity.trials import TrialTally, tend_cases


@reads(
    "law.rigidity",
    "table.council_seats",
    "table.creator",
    "table.culture_values",
    "table.dimensions",
    "table.entities",
    "table.estate_privileges",
    "table.estate_profiles",
    "table.faction_goals",
    "table.faction_profiles",
    "table.foreign_gods",
    "table.galaxies",
    "table.galaxy_clusters",
    "table.hooks",
    "table.incident_participants",
    "table.incidents",
    "table.law_profiles",
    "table.law_proposals",
    "table.name_registry",
    "table.node_births",
    "table.nodes",
    "table.offices",
    "table.personality_values",
    "table.polity_members",
    "table.polity_profiles",
    "table.polity_territories",
    "table.proposal_stances",
    "table.public_opinion",
    "table.settlement_profiles",
    "table.sons",
    "table.stars",
    "table.vassalages",
    "table.world_maps",
    "table.worlds",
)
@writes(
    "table.chronicle",
    "table.chronicle_entities",
    "table.entities",
    "table.favours",
    "table.hooks",
    "table.incident_facts",
    "table.incident_participants",
    "table.incident_steps",
    "table.incidents",
    "table.law_jurisdictions",
    "table.law_profiles",
    "table.law_proposals",
    "table.mortal_profiles",
    "table.name_registry",
    "table.proposal_stances",
    "table.settlement_profiles",
)
async def legislature(ctx: TickContext) -> None:
    tally = EnactmentTally()
    await tend_proposals(ctx, tally)
    for key, value in vars(tally).items():
        ctx.count(f"enactment_{key}", value)


@reads(
    "mortal.age",
    "mortal.intellect",
    "table.appeals",
    "table.bonds",
    "table.case_witnesses",
    "table.creator",
    "table.crime_cases",
    "table.dimensions",
    "table.entities",
    "table.estate_privileges",
    "table.estate_profiles",
    "table.foreign_gods",
    "table.galaxies",
    "table.galaxy_clusters",
    "table.incident_participants",
    "table.incidents",
    "table.jurisdictions",
    "table.law_jurisdictions",
    "table.law_profiles",
    "table.memberships",
    "table.node_births",
    "table.nodes",
    "table.offices",
    "table.polity_members",
    "table.relationships",
    "table.sanctuaries",
    "table.skills",
    "table.sons",
    "table.stars",
    "table.traits",
    "table.worlds",
)
@writes(
    "table.chronicle",
    "table.chronicle_entities",
    "table.crime_cases",
    "table.entities",
    "table.entity_flags",
    "table.incident_facts",
    "table.incident_participants",
    "table.incident_steps",
    "table.incidents",
    "table.memories",
    "table.mortal_profiles",
    "table.polity_profiles",
    "table.sentences",
    "table.settlement_profiles",
    "table.settlement_treasury",
    "table.thoughts",
)
async def trials(ctx: TickContext) -> None:
    tally = TrialTally()
    await tend_cases(ctx, tally)
    for key, value in vars(tally).items():
        ctx.count(f"trials_{key}", value)


PHASES = (Phase("legislature", legislature), Phase("trials", trials))
