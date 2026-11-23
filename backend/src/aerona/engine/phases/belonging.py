from aerona.engine.belonging.identities import IdentityTally, backfill_layers, keep_identities
from aerona.engine.belonging.peers import PeerTally, keep_peers
from aerona.engine.belonging.sanctuary import SanctuaryTally, keep_sanctuaries
from aerona.engine.belonging.satire import SatireTally, keep_satire
from aerona.engine.context import TickContext
from aerona.engine.interconnect.annotations import reads, writes
from aerona.engine.phase import Phase
from aerona.engine.phases.dominion import count


@reads(
    "mortal.agility",
    "mortal.charisma",
    "mortal.creativity",
    "mortal.endurance",
    "mortal.intellect",
    "mortal.perception",
    "mortal.strength",
    "mortal.willpower",
    "mortal.wisdom",
    "table.age_set_members",
    "table.age_sets",
    "table.army_profiles",
    "table.augment_effects",
    "table.augments",
    "table.bonds",
    "table.charms",
    "table.coalition_members",
    "table.commemorations",
    "table.community_cohorts",
    "table.districts",
    "table.entities",
    "table.faction_memberships",
    "table.faction_profiles",
    "table.genomes",
    "table.held_identities",
    "table.house_members",
    "table.incubating_ideas",
    "table.kind_holdings",
    "table.language_policies",
    "table.law_jurisdictions",
    "table.law_profiles",
    "table.marriages",
    "table.matches",
    "table.mind_attributes",
    "table.mind_facets",
    "table.mind_profiles",
    "table.mortal_profiles",
    "table.movement_profiles",
    "table.movement_support",
    "table.movements",
    "table.node_births",
    "table.nodes",
    "table.notable_years",
    "table.peer_groups",
    "table.peer_members",
    "table.polity_members",
    "table.polity_profiles",
    "table.purity_ranks",
    "table.referendums",
    "table.skills",
    "table.war_sides",
    "table.wars",
)
@writes(
    "table.applied_fixups",
    "table.bonds",
    "table.chronicle",
    "table.chronicle_entities",
    "table.held_identities",
    "table.incident_facts",
    "table.incident_participants",
    "table.incidents",
    "table.mind_facets",
    "table.peer_groups",
    "table.peer_members",
    "table.relationships",
    "table.skills",
)
async def belonging(ctx: TickContext) -> None:
    identities, peers = IdentityTally(), PeerTally()
    ctx.count("identity_layers_backfilled", await backfill_layers(ctx))
    await keep_identities(ctx, identities)
    await keep_peers(ctx, peers)
    count(ctx, "identities", identities)
    count(ctx, "peers", peers)


@reads(
    "cult.influence",
    "table.bonds",
    "table.community_relations",
    "table.crime_cases",
    "table.cult_holdings",
    "table.culture_values",
    "table.defections",
    "table.entities",
    "table.nodes",
    "table.outlaws",
    "table.personality_values",
    "table.polity_members",
    "table.relationships",
    "table.reputations",
    "table.sanctuaries",
    "table.social_norms",
    "table.structure_profiles",
    "table.traits",
)
@writes("cult.influence", "table.community_relations", "table.cult_doctrines", "table.entities", "table.memories", "table.mortal_profiles", "table.sanctuaries")
async def sanctuary(ctx: TickContext) -> None:
    tally = SanctuaryTally()
    await keep_sanctuaries(ctx, tally)
    count(ctx, "sanctuary", tally)


@reads("table.artwork_profiles", "table.entities", "table.nodes", "table.offices", "table.satires")
@writes("table.bias_weights", "table.mortal_profiles", "table.satires")
async def satire(ctx: TickContext) -> None:
    tally = SatireTally()
    await keep_satire(ctx, tally)
    count(ctx, "satire", tally)


PHASES = (
    Phase("belonging", belonging),
    Phase("sanctuary", sanctuary),
    Phase("satire", satire),
)
