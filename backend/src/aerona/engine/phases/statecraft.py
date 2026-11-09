from aerona.engine.context import TickContext
from aerona.engine.interconnect.annotations import reads, writes
from aerona.engine.phase import Phase
from aerona.engine.polity.coalitions import CoalitionTally, tend_coalitions
from aerona.engine.polity.crises import CrisisTally
from aerona.engine.polity.crisis_outcomes import tend_crises
from aerona.engine.polity.regard import RegardTally, tend_regard
from aerona.engine.polity.spheres import SphereTally, tend_spheres
from aerona.engine.polity.subjects import SubjectTally, tend_subjects


@reads(
    "people.martiality",
    "settlement.defense",
    "table.bonds",
    "table.community_relations",
    "table.community_societies",
    "table.cosmos",
    "table.crises",
    "table.crisis_backers",
    "table.culture_ethics",
    "table.culture_values",
    "table.dimensional_events",
    "table.diplomacy_profiles",
    "table.districts",
    "table.epoch_year_cursors",
    "table.galactic_structures",
    "table.holder_levels",
    "table.memories",
    "table.minds",
    "table.nodes",
    "table.offices",
    "table.personality_values",
    "table.polity_members",
    "table.polity_profiles",
    "table.polity_regard",
    "table.polity_territories",
    "table.relationships",
    "table.reputations",
    "table.ruler_currencies",
    "table.skills",
    "table.speaker_cohorts",
    "table.spheres",
    "table.tradition_profiles",
    "table.traits",
    "table.treaty_parties",
    "table.treaty_profiles",
    "table.vassalages",
    "table.world_maps",
)
@writes(
    "table.bonds",
    "table.chronicle",
    "table.chronicle_entities",
    "table.community_relations",
    "table.crises",
    "table.crisis_backers",
    "table.diplomacy_profiles",
    "table.entities",
    "table.epoch_year_cursors",
    "table.favours",
    "table.incident_participants",
    "table.incidents",
    "table.memories",
    "table.polity_profiles",
    "table.polity_regard",
    "table.polity_territories",
    "table.spheres",
    "table.treaty_clauses",
    "table.treaty_parties",
    "table.treaty_profiles",
    "table.vassalages",
)
async def statecraft(ctx: TickContext) -> None:
    regard, coalition, crisis, sphere, subject = RegardTally(), CoalitionTally(), CrisisTally(), SphereTally(), SubjectTally()
    await tend_regard(ctx, regard)
    await tend_coalitions(ctx, coalition)
    await tend_crises(ctx, crisis)
    await tend_spheres(ctx, sphere)
    await tend_subjects(ctx, subject)
    tallies: dict[str, object] = {"regard": regard, "coalition": coalition, "crisis": crisis, "sphere": sphere, "subject": subject}
    for prefix, tally in tallies.items():
        for key, value in vars(tally).items():
            ctx.count(f"statecraft_{prefix}_{key}", value)


PHASES = (Phase("statecraft", statecraft),)
