from aerona.engine.context import TickContext
from aerona.engine.divine.activity import tend_domain_economy
from aerona.engine.divine.avatars import avatar_cycles
from aerona.engine.divine.council_order import keep_council_order
from aerona.engine.divine.creator import tend_attention, type_taboos
from aerona.engine.divine.creator_bonds import keep_creator_bonds
from aerona.engine.divine.foreign import divine_pacts, god_opinions, old_god_doctrine, pantheon_leagues
from aerona.engine.divine.goals import pursue_goals
from aerona.engine.divine.grammar import keep_powers
from aerona.engine.divine.laws import tend_laws
from aerona.engine.divine.outer import outer_feeding, void_rites
from aerona.engine.divine.outer_agency import outer_agency
from aerona.engine.divine.pantheon import keep_pantheons
from aerona.engine.divine.rulings import enforce_rulings
from aerona.engine.divine.standing import tend_standing
from aerona.engine.divine.wounds import heal_wounds
from aerona.engine.interconnect.annotations import reads, writes
from aerona.engine.phase import Phase


@reads(
    "table.bonds",
    "table.castings",
    "table.divine_wounds",
    "table.dreams",
    "table.emotion_spirits",
    "table.entities",
    "table.foreign_gods",
    "table.god_feedings",
    "table.goods_flows",
    "table.journeys",
    "table.oaths",
    "table.schemes",
    "table.sons",
    "table.thoughts",
    "table.trade_flows",
    "table.trade_route_profiles",
    "table.world_domain_hooks",
)
@writes("table.domain_activity", "table.emotion_harvests", "table.foreign_gods", "table.god_feedings", "table.sons")
async def domain_economy(ctx: TickContext) -> None:
    ctx.count("activity_rows", await tend_domain_economy(ctx))


@reads(
    "table.bias_weights",
    "table.bonds",
    "table.divine_wounds",
    "table.epoch_year_cursors",
    "table.foreign_gods",
    "table.god_designs",
    "table.house_members",
    "table.mantlings",
    "table.network_nodes",
    "table.personality_values",
    "table.polity_members",
    "table.relationships",
    "table.relics",
    "table.skills",
    "table.son_goals",
    "table.son_powers",
    "table.sons",
    "table.spy_networks",
    "table.thrones",
    "table.war_sides",
    "table.wars",
    "table.world_domain_hooks",
    "table.worlds",
)
@writes(
    "table.bias_weights",
    "table.chronicle",
    "table.epoch_year_cursors",
    "table.foreign_gods",
    "table.god_designs",
    "table.incident_participants",
    "table.incidents",
    "table.son_goals",
    "table.sons",
)
async def god_goals(ctx: TickContext) -> None:
    ctx.count("attention_moved", await pursue_goals(ctx))


@reads("table.action_records", "table.bonds", "table.creator", "table.divine_standing", "table.entities", "table.messages", "table.nodes", "table.sons")
@writes("table.divine_standing")
async def divine_standing(ctx: TickContext) -> None:
    ctx.count("standings", await tend_standing(ctx))


@reads(
    "table.bonds",
    "table.castings",
    "table.divine_powers",
    "table.divine_wounds",
    "table.foreign_god_powers",
    "table.foreign_gods",
    "table.pressures",
    "table.son_powers",
    "table.sons",
)
@writes(
    "table.chronicle",
    "table.community_stocks",
    "table.culture_values",
    "table.divine_powers",
    "table.divine_wounds",
    "table.entities",
    "table.epoch_year_cursors",
    "table.goods_flows",
    "table.hidden_truths",
    "table.incident_participants",
    "table.incidents",
    "table.living_lines",
    "table.memories",
    "table.mind_profiles",
    "table.power_sources",
    "table.pressures",
    "table.region_environment",
    "table.skills",
    "table.structure_profiles",
    "table.world_attention",
)
async def divine_wounds(ctx: TickContext) -> None:
    ctx.count("healed", await heal_wounds(ctx))
    await keep_powers(ctx)


@reads("table.avatars", "table.bonds", "table.divine_standing", "table.entities", "table.foreign_gods", "table.sons")
@writes(
    "table.avatars", "table.bonds", "table.chronicle", "table.divine_standing", "table.epoch_year_cursors", "table.incident_participants", "table.incidents"
)
async def avatars(ctx: TickContext) -> None:
    ctx.count("converted", await avatar_cycles(ctx))


@reads("table.applied_fixups", "table.creator")
@writes("table.applied_fixups", "table.creator_taboos")
async def creator_taboos(ctx: TickContext) -> None:
    ctx.count("taboos", await type_taboos(ctx))


@reads(
    "table.action_records",
    "table.bonds",
    "table.covenants",
    "table.creator",
    "table.creator_chosen",
    "table.creator_depictions",
    "table.creator_standing",
    "table.culture_values",
    "table.entities",
    "table.language_profiles",
    "table.lexemes",
    "table.name_registry",
    "table.nodes",
    "table.world_attention",
    "table.worlds",
)
@writes(
    "table.chronicle",
    "table.cosmos",
    "table.covenants",
    "table.creator",
    "table.creator_chosen",
    "table.creator_depictions",
    "table.creator_standing",
    "table.entities",
    "table.epoch_year_cursors",
    "table.incident_participants",
    "table.incidents",
    "table.memories",
    "table.world_attention",
)
async def creator_attention(ctx: TickContext) -> None:
    ctx.count("worlds", await tend_attention(ctx))
    await keep_creator_bonds(ctx)


@reads(
    "table.bonds",
    "table.entities",
    "table.foreign_gods",
    "table.pantheon_structures",
    "table.pantheon_ties",
    "table.relationships",
    "table.sons",
    "table.syncretisms",
    "table.treaty_parties",
    "table.treaty_profiles",
)
@writes(
    "table.bonds",
    "table.chronicle",
    "table.cult_doctrines",
    "table.cult_tenets",
    "table.entities",
    "table.epoch_year_cursors",
    "table.foreign_gods",
    "table.incident_participants",
    "table.incidents",
    "table.pantheon_structures",
    "table.pantheon_ties",
    "table.relationships",
    "table.syncretisms",
    "table.treaty_clauses",
    "table.treaty_parties",
    "table.treaty_profiles",
)
async def god_relations(ctx: TickContext) -> None:
    ctx.count("opinions", await god_opinions(ctx))
    ctx.count("leagues", await pantheon_leagues(ctx))
    await keep_pantheons(ctx)
    ctx.count("pacts", await divine_pacts(ctx))
    ctx.count("old_faiths", await old_god_doctrine(ctx))


@reads(
    "table.council_procedures",
    "table.council_rulings",
    "table.council_violations",
    "table.divine_council_seats",
    "table.divine_powers",
    "table.foreign_gods",
    "table.god_conflicts",
    "table.living_lines",
    "table.mind_profiles",
    "table.power_sources",
    "table.sons",
    "table.treaty_parties",
    "table.treaty_profiles",
    "table.worlds",
)
@writes(
    "table.chronicle",
    "table.council_procedures",
    "table.council_rulings",
    "table.council_violations",
    "table.divine_council_seats",
    "table.epoch_year_cursors",
    "table.foreign_gods",
    "table.incident_participants",
    "table.incidents",
    "table.living_lines",
    "table.mind_profiles",
    "table.power_sources",
    "table.relationships",
    "table.sons",
)
async def council_rulings(ctx: TickContext) -> None:
    ctx.count("rulings", await enforce_rulings(ctx))
    await keep_council_order(ctx)


@reads(
    "table.bonds",
    "table.cosmos",
    "table.creator",
    "table.entities",
    "table.hidden_truths",
    "table.law_theories",
    "table.living_lines",
    "table.made_realm_profiles",
    "table.mind_profiles",
    "table.mind_states",
    "table.modifiers",
    "table.natural_law_exceptions",
    "table.natural_law_profiles",
    "table.power_sources",
    "table.powers",
    "table.sons",
    "table.wars",
    "table.worlds",
)
@writes(
    "table.chronicle",
    "table.creator",
    "table.entities",
    "table.epoch_year_cursors",
    "table.hidden_truths",
    "table.incident_participants",
    "table.incidents",
    "table.law_theories",
    "table.living_lines",
    "table.made_realm_profiles",
    "table.mind_profiles",
    "table.mind_states",
    "table.modifiers",
    "table.natural_law_profiles",
    "table.power_sources",
    "table.powers",
    "table.relationships",
    "table.sons",
    "table.worlds",
)
async def natural_laws(ctx: TickContext) -> None:
    ctx.count("laws", await tend_laws(ctx))


@reads(
    "table.bonds",
    "table.breach_points",
    "table.cult_tenets",
    "table.entities",
    "table.entity_flags",
    "table.holder_levels",
    "table.legend_profiles",
    "table.lexemes",
    "table.lifecycle_states",
    "table.natural_law_profiles",
    "table.outer_being_profiles",
    "table.outer_heralds",
    "table.outer_incursions",
    "table.outer_pacts",
    "table.outer_plans",
    "table.outer_relations",
    "table.outer_seals",
    "table.rifts",
    "table.sons",
    "table.spirit_profiles",
    "table.stars",
    "table.worlds",
)
@writes(
    "table.bonds",
    "table.breach_points",
    "table.chronicle",
    "table.entities",
    "table.epoch_year_cursors",
    "table.holder_levels",
    "table.incident_participants",
    "table.incidents",
    "table.legend_profiles",
    "table.lexemes",
    "table.natural_law_profiles",
    "table.outer_being_profiles",
    "table.outer_heralds",
    "table.outer_incursions",
    "table.outer_pacts",
    "table.outer_plans",
    "table.outer_relations",
    "table.outer_seals",
    "table.powers",
    "table.rifts",
    "table.sons",
    "table.stars",
    "table.worlds",
)
async def outer_hunger(ctx: TickContext) -> None:
    ctx.count("fed", await outer_feeding(ctx))
    ctx.count("void_rites", await void_rites(ctx))
    ctx.count("outer_aims", await outer_agency(ctx))


PHASES = (
    Phase("domain_economy", domain_economy),
    Phase("god_goals", god_goals),
    Phase("divine_standing", divine_standing),
    Phase("divine_wounds", divine_wounds),
    Phase("avatars", avatars),
    Phase("creator_taboos", creator_taboos),
    Phase("creator_attention", creator_attention),
    Phase("god_relations", god_relations),
    Phase("council_rulings", council_rulings),
    Phase("natural_laws", natural_laws),
    Phase("outer_hunger", outer_hunger),
)
