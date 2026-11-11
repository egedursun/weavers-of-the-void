from aerona.engine.context import TickContext
from aerona.engine.divine.activity import tend_domain_economy
from aerona.engine.divine.avatars import avatar_cycles
from aerona.engine.divine.creator import tend_attention, type_taboos
from aerona.engine.divine.foreign import divine_pacts, god_opinions, old_god_doctrine, pantheon_leagues
from aerona.engine.divine.goals import pursue_goals
from aerona.engine.divine.laws import tend_laws
from aerona.engine.divine.outer import outer_feeding, void_rites
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
    "table.entities",
    "table.foreign_gods",
    "table.goods_flows",
    "table.journeys",
    "table.oaths",
    "table.schemes",
    "table.sons",
    "table.trade_flows",
    "table.trade_route_profiles",
    "table.world_domain_hooks",
)
@writes("table.domain_activity", "table.foreign_gods", "table.sons")
async def domain_economy(ctx: TickContext) -> None:
    ctx.count("activity_rows", await tend_domain_economy(ctx))


@reads(
    "table.bonds",
    "table.divine_wounds",
    "table.epoch_year_cursors",
    "table.foreign_gods",
    "table.house_members",
    "table.mantlings",
    "table.personality_values",
    "table.polity_members",
    "table.relics",
    "table.son_goals",
    "table.son_powers",
    "table.sons",
    "table.thrones",
    "table.war_sides",
    "table.wars",
    "table.world_domain_hooks",
    "table.worlds",
)
@writes(
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


@reads("table.bonds", "table.castings", "table.divine_wounds", "table.foreign_gods", "table.sons")
@writes("table.chronicle", "table.divine_wounds", "table.epoch_year_cursors", "table.incident_participants", "table.incidents")
async def divine_wounds(ctx: TickContext) -> None:
    ctx.count("healed", await heal_wounds(ctx))


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


@reads("table.action_records", "table.creator", "table.entities", "table.world_attention", "table.worlds")
@writes("table.world_attention")
async def creator_attention(ctx: TickContext) -> None:
    ctx.count("worlds", await tend_attention(ctx))


@reads("table.bonds", "table.foreign_gods", "table.relationships", "table.sons", "table.treaty_parties", "table.treaty_profiles")
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
    "table.relationships",
    "table.treaty_clauses",
    "table.treaty_parties",
    "table.treaty_profiles",
)
async def god_relations(ctx: TickContext) -> None:
    ctx.count("opinions", await god_opinions(ctx))
    ctx.count("leagues", await pantheon_leagues(ctx))
    ctx.count("pacts", await divine_pacts(ctx))
    ctx.count("old_faiths", await old_god_doctrine(ctx))


@reads("table.council_rulings", "table.sons", "table.worlds")
@writes("table.chronicle", "table.council_rulings", "table.epoch_year_cursors", "table.incident_participants", "table.incidents", "table.sons")
async def council_rulings(ctx: TickContext) -> None:
    ctx.count("rulings", await enforce_rulings(ctx))


@reads("table.creator", "table.entities", "table.natural_law_profiles", "table.sons", "table.worlds")
@writes(
    "table.chronicle",
    "table.creator",
    "table.entities",
    "table.epoch_year_cursors",
    "table.incident_participants",
    "table.incidents",
    "table.natural_law_profiles",
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
    "table.outer_being_profiles",
    "table.spirit_profiles",
    "table.stars",
    "table.worlds",
)
@writes(
    "table.breach_points",
    "table.chronicle",
    "table.entities",
    "table.epoch_year_cursors",
    "table.holder_levels",
    "table.incident_participants",
    "table.incidents",
    "table.legend_profiles",
    "table.lexemes",
    "table.outer_being_profiles",
    "table.stars",
    "table.worlds",
)
async def outer_hunger(ctx: TickContext) -> None:
    ctx.count("fed", await outer_feeding(ctx))
    ctx.count("void_rites", await void_rites(ctx))


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
