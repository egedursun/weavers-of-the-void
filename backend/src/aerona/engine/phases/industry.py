from aerona.catalog.methods import ENERGY_LABELS
from aerona.db.write_guard import unheld
from aerona.domain.enums.chronicle import ChronicleKind
from aerona.domain.enums.industry import EnergyKind
from aerona.engine.context import TickContext
from aerona.engine.economy.book import EconomyBook
from aerona.engine.finance.access import gauge_access
from aerona.engine.industry.energy import gauge, industry_row, leys_by_region, unmet_pct
from aerona.engine.industry.methods import MethodTally, choose_methods
from aerona.engine.industry.owners import ProfitTally, magic_banned, tend_profits
from aerona.engine.industry.pollution import PollutionTally, tend_pollution
from aerona.engine.industry.stores import StoreTally, burn_fuel, kindle, noble_taste, pour_drink, preserve, spoil, wear_tools
from aerona.engine.interconnect.annotations import reads, writes
from aerona.engine.notes import note
from aerona.engine.phase import Phase

NOTE_CAP = 6


@reads(
    "people.population",
    "settlement.population",
    "table.army_profiles",
    "table.bonds",
    "table.calendars",
    "table.community_industry",
    "table.community_labour",
    "table.community_methods",
    "table.community_societies",
    "table.community_stocks",
    "table.culture_values",
    "table.epoch_year_cursors",
    "table.faction_goals",
    "table.faction_profiles",
    "table.forced_weather",
    "table.goods_flows",
    "table.holder_levels",
    "table.holder_techniques",
    "table.ideology_adherents",
    "table.ideology_tenets",
    "table.law_jurisdictions",
    "table.law_profiles",
    "table.ley_lines",
    "table.personality_values",
    "table.place_environment",
    "table.polity_members",
    "table.region_environment",
    "table.region_pollution",
    "table.resource_profiles",
    "table.resource_workers",
    "table.settlement_infrastructure",
    "table.skills",
    "table.sky_events",
    "table.trade_route_profiles",
    "table.treaty_parties",
    "table.workshop_designs",
    "table.workshops",
    "table.world_maps",
    "table.world_materials",
    "table.world_seasons",
    "trade_route.capacity",
    "trade_route.danger",
)
@writes(
    "table.chronicle",
    "table.chronicle_entities",
    "table.community_industry",
    "table.community_labour",
    "table.community_methods",
    "table.community_stocks",
    "table.epoch_year_cursors",
    "table.faction_goals",
    "table.goods_flows",
    "table.incident_participants",
    "table.incidents",
    "table.production_runs",
)
async def industry_methods(ctx: TickContext) -> None:
    book = await EconomyBook.load(ctx)
    leys = await leys_by_region(ctx)
    tally = MethodTally()
    banned = await magic_banned(ctx.session, book)
    ctx.count("access_gauged", await gauge_access(ctx, book))
    for community in unheld(book.communities):
        row = await gauge(ctx, book, community, leys)
        await choose_methods(ctx, book, community, tally, banned=community.id in banned)
        await kindle(ctx, book, community, row)
    await ctx.session.flush()
    ctx.count("methods_chosen", tally.chosen)
    ctx.count("methods_changed", tally.changed)
    ctx.count("artisans_displaced", tally.displaced)
    ctx.count("guilds_resisting", tally.resisted)


async def tell_shortfalls(ctx: TickContext, book: EconomyBook) -> int:
    told = 0
    for community in unheld(book.communities):
        row = book.industry.get(community.id)
        if row is None or told >= NOTE_CAP:
            continue
        worst = max(EnergyKind, key=lambda kind: (unmet_pct(row, kind), kind.value))
        if unmet_pct(row, worst) < ctx.rules.energy.shortfall_note_pct:
            continue
        told += 1
        await note(
            ctx,
            f"The works of {community.name} slowed for want of {ENERGY_LABELS[worst].lower()} power.",
            key="industry.energy_short",
            ids=[community.id],
            kind=ChronicleKind.PRODUCTION,
        )
    return told


@reads(
    "people.population",
    "settlement.population",
    "table.army_profiles",
    "table.bonds",
    "table.calendars",
    "table.community_industry",
    "table.community_labour",
    "table.community_methods",
    "table.community_relations",
    "table.community_societies",
    "table.community_stocks",
    "table.entity_traits",
    "table.epoch_year_cursors",
    "table.forced_weather",
    "table.goods_flows",
    "table.herds",
    "table.holder_levels",
    "table.holder_techniques",
    "table.ideology_adherents",
    "table.ideology_tenets",
    "table.place_environment",
    "table.production_runs",
    "table.region_environment",
    "table.region_pollution",
    "table.resource_profiles",
    "table.resource_workers",
    "table.settlement_profiles",
    "table.skills",
    "table.sky_events",
    "table.species_profiles",
    "table.species_ranges",
    "table.treaty_parties",
    "table.workshop_designs",
    "table.workshops",
    "table.world_maps",
    "table.world_materials",
    "table.world_seasons",
)
@writes(
    "table.chronicle",
    "table.chronicle_entities",
    "table.community_industry",
    "table.community_relations",
    "table.community_societies",
    "table.community_stocks",
    "table.epoch_year_cursors",
    "table.goods_flows",
    "table.incident_participants",
    "table.incidents",
    "table.memories",
    "table.production_runs",
    "table.region_environment",
    "table.region_pollution",
)
async def industry_aftermath(ctx: TickContext) -> None:
    book = await EconomyBook.load(ctx)
    stores = StoreTally()
    for community in unheld(book.communities):
        row = industry_row(ctx, book, community.id)
        await preserve(ctx, book, community, row, stores)
        await burn_fuel(ctx, book, community, row, stores)
        await wear_tools(ctx, book, community, row, stores)
        await spoil(ctx, book, community, row, stores)
        await noble_taste(ctx, book, community, stores)
        await pour_drink(ctx, community, row)
    await ctx.session.flush()
    fouled = PollutionTally()
    await tend_pollution(ctx, book, fouled)
    ctx.count("energy_notes", await tell_shortfalls(ctx, book))
    await ctx.session.flush()
    ctx.count("preserved", stores.preserved)
    ctx.count("spoiled", stores.spoiled)
    ctx.count("tools_worn", stores.worn)
    ctx.count("fuel_burned", stores.burned)
    ctx.count("nobles_wanting", stores.coarse)
    ctx.count("pollution_added", fouled.fouled)
    ctx.count("pollution_cleared", fouled.cleared)
    ctx.count("purification_rites", fouled.rites)
    ctx.count("blights", fouled.blighted)
    ctx.count("turned_against_polluters", fouled.turned)


@reads(
    "people.prosperity",
    "settlement.prosperity",
    "table.army_profiles",
    "table.bonds",
    "table.calendars",
    "table.community_industry",
    "table.community_labour",
    "table.community_methods",
    "table.community_societies",
    "table.cult_doctrines",
    "table.cult_holdings",
    "table.faction_goals",
    "table.faction_profiles",
    "table.forced_weather",
    "table.holder_levels",
    "table.holder_techniques",
    "table.house_profiles",
    "table.law_jurisdictions",
    "table.law_profiles",
    "table.mortal_profiles",
    "table.place_environment",
    "table.polity_members",
    "table.polity_profiles",
    "table.production_runs",
    "table.region_environment",
    "table.region_pollution",
    "table.resource_profiles",
    "table.resource_workers",
    "table.settlement_profiles",
    "table.skills",
    "table.sky_events",
    "table.trade_policies",
    "table.treaty_parties",
    "table.workshop_designs",
    "table.workshops",
    "table.world_maps",
    "table.world_materials",
    "table.world_seasons",
)
@writes(
    "people.prosperity",
    "settlement.prosperity",
    "table.cult_doctrines",
    "table.entities",
    "table.faction_goals",
    "table.faction_profiles",
    "table.house_profiles",
    "table.mortal_profiles",
    "table.polity_profiles",
    "table.settlement_profiles",
    "table.site_profits",
    "table.workshops",
)
async def site_profits(ctx: TickContext) -> None:
    book = await EconomyBook.load(ctx)
    tally = ProfitTally()
    await tend_profits(ctx, book, tally)
    await ctx.session.flush()
    ctx.count("sites_owned", tally.owned)
    ctx.count("sites_settled", tally.sites)
    ctx.count("profit", tally.profit)
    ctx.count("losses", tally.losses)
    ctx.count("invested", tally.invested)
    ctx.count("taxes", tally.taxes)
    ctx.count("owners_lobbying", tally.lobbied)


PHASES = (
    Phase("industry_methods", industry_methods),
    Phase("industry_aftermath", industry_aftermath),
    Phase("site_profits", site_profits),
)
