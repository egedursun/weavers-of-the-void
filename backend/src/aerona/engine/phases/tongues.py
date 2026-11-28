from aerona.engine.context import TickContext
from aerona.engine.interconnect.annotations import reads, writes
from aerona.engine.phase import Phase
from aerona.engine.phases.dominion import count
from aerona.engine.tongues.decipher import DecipherTally, decipher_world
from aerona.engine.tongues.divine import TongueTally, give_tongues
from aerona.engine.tongues.grammar import GrammarTally, describe_grammars
from aerona.engine.tongues.meaning import DriftTally, drift_meanings
from aerona.engine.tongues.modality import settle_modalities
from aerona.engine.tongues.pidgins import PidginTally, pidgin_world
from aerona.engine.tongues.policy import PolicyTally, keep_policies
from aerona.engine.tongues.scripts import ScriptTally, evolve_scripts
from aerona.engine.tongues.sounds import SoundTally, shift_sounds


@reads(
    "table.bonds",
    "table.entities",
    "table.entity_flags",
    "table.language_policies",
    "table.language_profiles",
    "table.language_standing",
    "table.lexemes",
    "table.name_meanings",
    "table.network_nodes",
    "table.nodes",
    "table.sociolects",
    "table.sound_changes",
)
@writes("table.lexemes", "table.sound_changes")
async def sound_changes(ctx: TickContext) -> None:
    tally = SoundTally()
    await shift_sounds(ctx, tally)
    count(ctx, "sound", tally)


@reads(
    "language.complexity",
    "table.bonds",
    "table.entities",
    "table.language_grammar",
    "table.language_profiles",
    "table.language_standing",
    "table.network_nodes",
    "table.nodes",
    "table.people_biology",
    "table.people_substrates",
    "table.sense_profiles",
    "table.speaker_cohorts",
)
@writes("table.language_grammar")
async def grammar(ctx: TickContext) -> None:
    tally = GrammarTally()
    await describe_grammars(ctx, tally)
    count(ctx, "grammar", tally)
    ctx.count("modalities_settled", await settle_modalities(ctx))


@reads(
    "beast.terror",
    "table.bonds",
    "table.creator",
    "table.deep_passages",
    "table.dimensions",
    "table.entities",
    "table.foreign_gods",
    "table.galaxies",
    "table.galaxy_clusters",
    "table.incident_participants",
    "table.incidents",
    "table.language_grammar",
    "table.language_policies",
    "table.lexemes",
    "table.meaning_shifts",
    "table.name_exonyms",
    "table.node_births",
    "table.nodes",
    "table.sociolects",
    "table.sons",
    "table.stars",
    "table.tradition_profiles",
    "table.worlds",
)
@writes(
    "table.chronicle",
    "table.chronicle_entities",
    "table.incident_facts",
    "table.incident_participants",
    "table.incidents",
    "table.lexemes",
    "table.meaning_shifts",
    "table.name_exonyms",
)
async def semantic_drift(ctx: TickContext) -> None:
    tally = DriftTally()
    await drift_meanings(ctx, tally)
    count(ctx, "drift", tally)


@reads(
    "table.bonds",
    "table.community_societies",
    "table.divine_tongues",
    "table.entities",
    "table.entity_flags",
    "table.language_policies",
    "table.language_profiles",
    "table.language_standing",
    "table.node_births",
    "table.nodes",
    "table.polity_members",
    "table.scripts",
)
@writes(
    "table.chronicle",
    "table.chronicle_entities",
    "table.incident_facts",
    "table.incident_participants",
    "table.incidents",
    "table.language_profiles",
    "table.language_standing",
    "table.scripts",
)
async def script_evolution(ctx: TickContext) -> None:
    tally = ScriptTally()
    await evolve_scripts(ctx, tally)
    count(ctx, "script", tally)


@reads("table.entities", "table.entity_flags", "table.excavation_stages", "table.excavations", "table.nodes")
async def decipherment(ctx: TickContext) -> None:
    tally = DecipherTally()
    await decipher_world(ctx, tally)
    count(ctx, "decipher", tally)


@reads(
    "table.captive_cohorts",
    "table.language_profiles",
    "table.mercenary_contracts",
    "table.trade_flows",
    "table.trade_route_profiles",
    "table.trade_route_regions",
    "table.trade_route_tolls",
    "trade_route.culture",
)
async def pidgins(ctx: TickContext) -> None:
    tally = PidginTally()
    await pidgin_world(ctx, tally)
    count(ctx, "pidgin", tally)


@reads(
    "table.creator",
    "table.dimensions",
    "table.entities",
    "table.foreign_gods",
    "table.galaxies",
    "table.galaxy_clusters",
    "table.incident_participants",
    "table.incidents",
    "table.language_policies",
    "table.node_births",
    "table.nodes",
    "table.polity_members",
    "table.polity_memberstable.creator",
    "table.settlement_profiles",
    "table.sons",
    "table.speaker_cohorts",
    "table.stars",
    "table.state_changes",
    "table.worlds",
)
@writes(
    "table.chronicle",
    "table.chronicle_entities",
    "table.incident_facts",
    "table.incident_participants",
    "table.incidents",
    "table.language_policies",
    "table.node_births",
    "table.settlement_profiles",
    "table.speaker_cohorts",
)
async def language_policy(ctx: TickContext) -> None:
    tally = PolicyTally()
    await keep_policies(ctx, tally)
    count(ctx, "policy", tally)


@reads(
    "table.bonds",
    "table.divine_tongues",
    "table.entities",
    "table.language_profiles",
    "table.lexemes",
    "table.name_registry",
    "table.nodes",
    "table.son_powers",
    "table.sons",
    "table.true_names",
)
@writes("table.divine_tongues", "table.entities", "table.language_profiles", "table.lexemes", "table.name_registry", "table.true_names")
async def divine_tongues(ctx: TickContext) -> None:
    tally = TongueTally()
    await give_tongues(ctx, tally)
    count(ctx, "tongue", tally)


PHASES = (
    Phase("sound_changes", sound_changes),
    Phase("grammar", grammar),
    Phase("semantic_drift", semantic_drift),
    Phase("script_evolution", script_evolution),
    Phase("decipherment", decipherment),
    Phase("pidgins", pidgins),
    Phase("language_policy", language_policy),
    Phase("divine_tongues", divine_tongues),
)
