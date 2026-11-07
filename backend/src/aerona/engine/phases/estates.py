from aerona.engine.context import TickContext
from aerona.engine.factions.companies import CompanyTally, tend_companies
from aerona.engine.factions.estates import EstateTally, monopoly_rent, tend_estates
from aerona.engine.factions.guilds import GuildTally, tend_guilds
from aerona.engine.factions.movements import MovementTally, tend_movements
from aerona.engine.factions.orders import OrderTally, tend_orders
from aerona.engine.interconnect.annotations import reads, writes
from aerona.engine.phase import Phase


@reads(
    "faction.strength",
    "faction.wealth",
    "people.piety",
    "settlement.defense",
    "settlement.piety",
    "table.bonds",
    "table.community_societies",
    "table.company_profiles",
    "table.culture_values",
    "table.epoch_year_cursors",
    "table.estate_privileges",
    "table.estate_profiles",
    "table.faction_memberships",
    "table.faction_profiles",
    "table.holder_techniques",
    "table.holy_order_profiles",
    "table.law_jurisdictions",
    "table.law_profiles",
    "table.law_proposals",
    "table.movement_profiles",
    "table.movement_support",
    "table.name_registry",
    "table.nodes",
    "table.offices",
    "table.policy_approval",
    "table.polity_members",
    "table.polity_profiles",
    "table.polity_territories",
    "table.settlement_profiles",
    "table.vassalages",
    "table.war_sides",
    "table.wars",
    "table.world_maps",
)
@writes(
    "faction.wealth",
    "settlement.defense",
    "table.bonds",
    "table.chronicle",
    "table.chronicle_entities",
    "table.company_profiles",
    "table.company_shares",
    "table.entities",
    "table.epoch_year_cursors",
    "table.estate_privileges",
    "table.estate_profiles",
    "table.faction_goals",
    "table.faction_memberships",
    "table.faction_profiles",
    "table.guild_secrets",
    "table.holder_techniques",
    "table.holy_order_profiles",
    "table.incident_participants",
    "table.incidents",
    "table.law_proposals",
    "table.movement_profiles",
    "table.movement_support",
    "table.name_registry",
    "table.occupations",
    "table.settlement_profiles",
)
async def estates(ctx: TickContext) -> None:
    tallies = (EstateTally(), MovementTally(), CompanyTally(), OrderTally(), GuildTally())
    estate, movement, company, order, guild = tallies
    await tend_estates(ctx, estate)
    await monopoly_rent(ctx, estate)
    await tend_movements(ctx, movement)
    await tend_companies(ctx, company)
    await tend_orders(ctx, order)
    await tend_guilds(ctx, guild)
    for prefix, tally in zip(("estates", "movements", "companies", "holy_orders", "guilds"), tallies, strict=True):
        for key, value in vars(tally).items():
            ctx.count(f"{prefix}_{key}", value)


PHASES = (Phase("estates", estates),)
