from sqlalchemy import select

from aerona.db.tables.intrigue import IdentityRow, SchemeRow
from aerona.engine.context import TickContext
from aerona.engine.interconnect.annotations import reads, writes
from aerona.engine.intrigue.belief_depth import keep_belief_depth
from aerona.engine.intrigue.beliefs import fade_beliefs
from aerona.engine.intrigue.decay import DecayTally, keep_decays
from aerona.engine.intrigue.far_sources import far_sources
from aerona.engine.intrigue.identities import tend_identity
from aerona.engine.intrigue.names import confide_names, renew_names, research_names, seed_true_names
from aerona.engine.intrigue.schemes import OPEN, SchemeTally, plotters, tend_scheme
from aerona.engine.intrigue.sources import (
    SourceTally,
    hidden_conditions,
    hidden_memberships,
    likeness_noticed,
    masked_lives,
    neighbours_seen,
    noble_debts,
    scout_reports,
    spy_reports,
)
from aerona.engine.phase import Phase
from aerona.engine.primitives.distance import RegionAtlas
from aerona.engine.primitives.naming import Namer


@reads(
    "table.afflictions",
    "table.bonds",
    "table.entities",
    "table.entity_flags",
    "table.faction_memberships",
    "table.foreign_gods",
    "table.households",
    "table.identities",
    "table.language_profiles",
    "table.lexemes",
    "table.name_registry",
    "table.nodes",
    "table.sons",
    "table.spy_agents",
    "table.true_names",
)
@writes("table.identities", "table.language_profiles", "table.secrets", "table.true_names")
async def intrigue_survey(ctx: TickContext) -> None:
    namer = Namer(ctx.session, ctx.rules)
    tally = SourceTally()
    ctx.count("true_names_given", await seed_true_names(ctx, namer))
    await hidden_conditions(ctx, tally)
    await noble_debts(ctx, tally)
    await hidden_memberships(ctx, tally)
    await masked_lives(ctx, namer, tally)
    ctx.count("secrets_kept", tally.secrets)
    ctx.count("identities_assumed", tally.identities)


@reads(
    "faction.wealth",
    "mortal.creativity",
    "people.population",
    "people.prosperity",
    "people.wealth",
    "settlement.defense",
    "settlement.population",
    "settlement.prosperity",
    "settlement.wealth",
    "table.arc_figures",
    "table.arcs",
    "table.armies",
    "table.army_profiles",
    "table.army_units",
    "table.artwork_profiles",
    "table.beliefs",
    "table.bias_weights",
    "table.bonds",
    "table.community_relations",
    "table.entities",
    "table.favours",
    "table.forced_weather",
    "table.foresights",
    "table.hooks",
    "table.identities",
    "table.intrusions",
    "table.mind_profiles",
    "table.mortal_profiles",
    "table.network_nodes",
    "table.nodes",
    "table.offices",
    "table.outbreaks",
    "table.people_culture",
    "table.personality_values",
    "table.polity_members",
    "table.powers",
    "table.region_environment",
    "table.relationships",
    "table.relics",
    "table.schemes",
    "table.secrets",
    "table.settlement_treasury",
    "table.sieges",
    "table.skills",
    "table.sky_events",
    "table.source_trust",
    "table.spy_networks",
    "table.surveillance_profiles",
    "table.traits",
    "table.true_names",
    "table.world_maps",
    "table.world_seasons",
    "table.worlds",
)
@writes(
    "table.beliefs",
    "table.bias_weights",
    "table.bonds",
    "table.chronicle",
    "table.claims",
    "table.community_relations",
    "table.favours",
    "table.hooks",
    "table.identities",
    "table.messages",
    "table.relationships",
    "table.schemes",
    "table.secrets",
    "table.source_trust",
    "table.true_names",
)
async def intrigue(ctx: TickContext) -> None:
    atlas = await RegionAtlas.load(ctx.session)
    sources = SourceTally()
    ctx.count("beliefs_faded", await fade_beliefs(ctx))
    await neighbours_seen(ctx, atlas, sources)
    await spy_reports(ctx, sources)
    await scout_reports(ctx, sources)
    await far_sources(ctx, sources)
    await keep_belief_depth(ctx, sources)
    await likeness_noticed(ctx, sources)
    ctx.count("true_names_learned", await research_names(ctx))
    ctx.count("true_names_confided", await confide_names(ctx))
    ctx.count("true_names_renewed", await renew_names(ctx, Namer(ctx.session, ctx.rules)))
    unmasked = 0
    for row in list(await ctx.session.scalars(select(IdentityRow).order_by(IdentityRow.mortal_node_id))):
        unmasked += await tend_identity(ctx, row)
    decays = DecayTally()
    await keep_decays(ctx, decays)
    for name, value in vars(decays).items():
        ctx.count(name, value)
    schemes = SchemeTally()
    await plotters(ctx, schemes)
    for scheme in list(await ctx.session.scalars(select(SchemeRow).where(SchemeRow.phase.in_(list(OPEN))).order_by(SchemeRow.id))):
        await tend_scheme(ctx, scheme, schemes, atlas)
    for key, value in (
        ("beliefs_formed", sources.beliefs),
        ("secrets_learned", sources.learned),
        ("secrets_exposed", sources.exposed),
        ("identities_unmasked", unmasked),
        ("schemes_begun", schemes.begun),
        ("schemes_succeeded", schemes.succeeded),
        ("schemes_failed", schemes.failed),
        ("schemes_exposed", schemes.exposed),
    ):
        ctx.count(key, value)


PHASES = (Phase("intrigue_survey", intrigue_survey), Phase("intrigue", intrigue))
