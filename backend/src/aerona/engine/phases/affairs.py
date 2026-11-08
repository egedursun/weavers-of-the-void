from aerona.engine.context import TickContext
from aerona.engine.interconnect.annotations import reads, writes
from aerona.engine.phase import Phase
from aerona.engine.polity.assembly import AssemblyTally, tend_assemblies
from aerona.engine.polity.council import CouncilTally, tend_council
from aerona.engine.polity.court import CourtTally, tend_courts
from aerona.engine.polity.elections import ElectionTally, tend_elections
from aerona.engine.polity.mandates import MandateTally, tend_mandates
from aerona.engine.polity.policy import PolicyTally, tend_policy
from aerona.engine.polity.revenue import RevenueTally, tend_revenue


@reads(
    "law.justice",
    "mortal.charisma",
    "mortal.hp",
    "mortal.intellect",
    "mortal.strength",
    "mortal.wisdom",
    "people.piety",
    "people.population",
    "people.prosperity",
    "settlement.piety",
    "settlement.population",
    "settlement.prosperity",
    "table.bonds",
    "table.community_relations",
    "table.community_societies",
    "table.community_society",
    "table.community_stocks",
    "table.cosmos",
    "table.council_seats",
    "table.court_positions",
    "table.courts",
    "table.culture_values",
    "table.districts",
    "table.dwellings",
    "table.elections",
    "table.estate_profiles",
    "table.faction_memberships",
    "table.faction_profiles",
    "table.holder_techniques",
    "table.household_members",
    "table.ideology_tenets",
    "table.law_jurisdictions",
    "table.law_profiles",
    "table.mandates",
    "table.memories",
    "table.minds",
    "table.mortal_profiles",
    "table.movement_profiles",
    "table.movement_support",
    "table.noble_demands",
    "table.nodes",
    "table.offices",
    "table.personality_values",
    "table.policy_approval",
    "table.polity_members",
    "table.polity_profiles",
    "table.polity_regard",
    "table.polity_territories",
    "table.pressures",
    "table.relationships",
    "table.reputations",
    "table.resolution_votes",
    "table.resolutions",
    "table.ruler_currencies",
    "table.schemes",
    "table.secrets",
    "table.settlement_profiles",
    "table.skills",
    "table.speaker_cohorts",
    "table.tax_policies",
    "table.trade_policies",
    "table.traits",
    "table.vassalages",
    "table.war_sides",
    "table.wars",
    "table.world_maps",
)
@writes(
    "mortal.hp",
    "settlement.piety",
    "table.army_profiles",
    "table.chronicle",
    "table.chronicle_entities",
    "table.community_relations",
    "table.community_societies",
    "table.community_society",
    "table.community_stocks",
    "table.council_seats",
    "table.court_positions",
    "table.courts",
    "table.elections",
    "table.entities",
    "table.goods_flows",
    "table.law_profiles",
    "table.mandates",
    "table.memories",
    "table.mortal_profiles",
    "table.noble_demands",
    "table.offices",
    "table.policy_approval",
    "table.polity_profiles",
    "table.polity_regard",
    "table.polity_treasury",
    "table.resolution_votes",
    "table.resolutions",
    "table.schemes",
    "table.secrets",
    "table.settlement_profiles",
    "table.tax_policies",
    "table.trade_policies",
)
async def affairs(ctx: TickContext) -> None:
    council, election, revenue, mandate, policy = CouncilTally(), ElectionTally(), RevenueTally(), MandateTally(), PolicyTally()
    assembly, court = AssemblyTally(), CourtTally()
    await tend_council(ctx, council)
    await tend_elections(ctx, election)
    await tend_revenue(ctx, revenue)
    await tend_mandates(ctx, mandate)
    await tend_policy(ctx, policy)
    await tend_assemblies(ctx, assembly)
    await tend_courts(ctx, court)
    tallies: dict[str, object] = {
        "council": council,
        "election": election,
        "revenue": revenue,
        "mandate": mandate,
        "policy": policy,
        "assembly": assembly,
        "court": court,
    }
    for prefix, tally in tallies.items():
        for key, value in vars(tally).items():
            ctx.count(f"affairs_{prefix}_{key}", value)


PHASES = (Phase("affairs", affairs),)
