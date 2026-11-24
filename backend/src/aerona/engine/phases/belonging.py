from aerona.engine.belonging.fugitives_w52 import keep_fugitives
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
    "table.deep_passages",
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
    "table.powers",
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
    "table.captives",
    "table.community_relations",
    "table.crime_cases",
    "table.cult_holdings",
    "table.culture_values",
    "table.defections",
    "table.entities",
    "table.favours",
    "table.fugitives",
    "table.law_jurisdictions",
    "table.law_profiles",
    "table.mind_facets",
    "table.node_births",
    "table.nodes",
    "table.offices",
    "table.outlaws",
    "table.personality_values",
    "table.polity_members",
    "table.prisoners",
    "table.registries",
    "table.relationships",
    "table.reputations",
    "table.sanctuaries",
    "table.social_norms",
    "table.structure_profiles",
    "table.thoughts",
    "table.traits",
)
@writes(
    "cult.influence",
    "table.chronicle",
    "table.chronicle_entities",
    "table.community_relations",
    "table.cult_doctrines",
    "table.entities",
    "table.favours",
    "table.incident_facts",
    "table.incident_participants",
    "table.incidents",
    "table.memories",
    "table.mortal_profiles",
    "table.sanctuaries",
    "table.thoughts",
)
async def sanctuary(ctx: TickContext) -> None:
    tally = SanctuaryTally()
    ctx.count("fugitives", await keep_fugitives(ctx))
    await keep_sanctuaries(ctx, tally)
    count(ctx, "sanctuary", tally)


@reads(
    "table.artwork_profiles",
    "table.entities",
    "table.media_outlets",
    "table.node_births",
    "table.nodes",
    "table.offices",
    "table.polity_members",
    "table.prisoners",
    "table.sanctuaries",
    "table.satires",
    "table.settlement_profiles",
    "table.social_norms",
    "table.structure_profiles",
)
@writes(
    "table.bias_weights",
    "table.chronicle",
    "table.chronicle_entities",
    "table.incident_facts",
    "table.incident_participants",
    "table.incidents",
    "table.mortal_profiles",
    "table.satires",
)
async def satire(ctx: TickContext) -> None:
    tally = SatireTally()
    await keep_satire(ctx, tally)
    count(ctx, "satire", tally)


PHASES = (
    Phase("belonging", belonging),
    Phase("sanctuary", sanctuary),
    Phase("satire", satire),
)
