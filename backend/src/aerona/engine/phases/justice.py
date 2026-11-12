from aerona.engine.context import TickContext
from aerona.engine.interconnect.annotations import reads, writes
from aerona.engine.phase import Phase
from aerona.engine.polity.enactment import EnactmentTally, tend_proposals
from aerona.engine.polity.trials import TrialTally, tend_cases


@reads(
    "law.rigidity",
    "table.council_seats",
    "table.culture_values",
    "table.epoch_year_cursors",
    "table.estate_privileges",
    "table.estate_profiles",
    "table.faction_goals",
    "table.faction_profiles",
    "table.hooks",
    "table.law_profiles",
    "table.law_proposals",
    "table.name_registry",
    "table.offices",
    "table.personality_values",
    "table.polity_members",
    "table.polity_profiles",
    "table.polity_territories",
    "table.proposal_stances",
    "table.public_opinion",
    "table.settlement_profiles",
    "table.vassalages",
    "table.world_maps",
)
@writes(
    "table.chronicle",
    "table.chronicle_entities",
    "table.entities",
    "table.epoch_year_cursors",
    "table.favours",
    "table.hooks",
    "table.incident_participants",
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
    "table.bonds",
    "table.case_witnesses",
    "table.crime_cases",
    "table.law_jurisdictions",
    "table.law_profiles",
    "table.polity_members",
    "table.relationships",
    "table.traits",
)
@writes(
    "table.chronicle",
    "table.chronicle_entities",
    "table.crime_cases",
    "table.memories",
    "table.mortal_profiles",
    "table.sentences",
    "table.settlement_profiles",
    "table.settlement_treasury",
)
async def trials(ctx: TickContext) -> None:
    tally = TrialTally()
    await tend_cases(ctx, tally)
    for key, value in vars(tally).items():
        ctx.count(f"trials_{key}", value)


PHASES = (Phase("legislature", legislature), Phase("trials", trials))
