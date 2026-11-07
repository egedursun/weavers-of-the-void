from aerona.db.tables.estates import (
    CompanyProfileRow,
    CompanyShareRow,
    EstatePrivilegeRow,
    EstateProfileRow,
    GuildSecretRow,
    HolyOrderProfileRow,
    MovementProfileRow,
    MovementSupportRow,
)
from aerona.engine.interconnect.registry import Coupling, EdgeKind, Exposure, Mechanic, Subsystem, Surface

ESTATES = "section-estates"
S = Subsystem
E = EdgeKind

ESTATE_MECHANICS: tuple[Mechanic, ...] = (
    Mechanic(
        key="estates",
        spec_item="S4.3/RP2",
        title="The classes of a realm gather as estates with a loyalty and a share of its power; privileges buy loyalty at a cost in taxes, justice or power",
        subsystem=S.POLITY,
        phases=("estates", "settlement_life", "polity_cycles"),
        surface=Surface(drawer=ESTATES),
        backfill="none: estates gather from the next epoch",
        templates=("estates.granted", "estates.revoked"),
        fields=("loyalty", "influence", "privilege"),
        tables=(EstateProfileRow.__tablename__, EstatePrivilegeRow.__tablename__),
        exposure=Exposure.TOOL,
        tools=("bargain_with_estate",),
        targets=("polity", "faction"),
        couplings=(
            Coupling(S.ECONOMY, "a class free of taxes is not taxed in any town of its realm", E.MODIFIER),
            Coupling(S.LAW, "a class immune from the courts is not sentenced", E.TRIGGER),
            Coupling(S.WAR, "a class with the right to bear arms swells the militia", E.MODIFIER, "estates.militia_pct"),
            Coupling(S.POLITY, "an estate's influence is its share of the realm's power balance", E.FLOW, "estates.share_influence_pct"),
            Coupling(S.SOCIAL, "privileges raise an estate's loyalty and taking one back sours it", E.MODIFIER, "estates.privilege_loyalty"),
        ),
    ),
    Mechanic(
        key="movements",
        spec_item="S4.3/RP2",
        title=(
            "Movements for abolition, independence, revival, land reform or a wider franchise grow from pressures, protest, "
            "become parties where there is a council or assembly and rise where there is none"
        ),
        subsystem=S.POLITY,
        phases=("estates",),
        surface=Surface(drawer=ESTATES),
        backfill="none: movements gather from the next epoch",
        templates=("movements.revolt",),
        fields=("cause", "support", "is_party", "share"),
        tables=(MovementProfileRow.__tablename__, MovementSupportRow.__tablename__),
        exposure=Exposure.CONTEXT,
        targets=("polity", "settlement", "people"),
        couplings=(
            Coupling(S.SOCIAL, "protests raise a town's unrest", E.MODIFIER, "movements.protest_pct"),
            Coupling(S.WAR, "a movement past its threshold rises; an independence movement breaks its town away", E.TRIGGER, "movements.revolt_at"),
            Coupling(S.LAW, "movements lobby to abolish slavery and serfdom", E.TRIGGER),
            Coupling(
                S.CULTURE,
                "a distinct, cohesive people with grievances wishes to break away; autonomy and privileges soothe it",
                E.MODIFIER,
                "affairs.separatism_cohesion_pct",
            ),
        ),
    ),
    Mechanic(
        key="chartered_companies",
        spec_item="S4.3/RP2",
        title=(
            "Rich merchant guilds charter companies that hold the trade of a route abroad, pay their shareholders, "
            "may seize land at the far end and may collapse"
        ),
        subsystem=S.ECONOMY,
        phases=("estates",),
        surface=Surface(drawer=ESTATES),
        backfill="none: companies are chartered from the next epoch",
        templates=("companies.collapsed", "companies.conquest"),
        fields=("dividend_pct", "value", "share", "route_entity_id", "region_entity_id"),
        tables=(CompanyProfileRow.__tablename__, CompanyShareRow.__tablename__),
        exposure=Exposure.CONTEXT,
        targets=("faction", "polity", "mortal"),
        couplings=(
            Coupling(S.ECONOMY, "a company draws wealth from its route and pays dividends to its shareholders", E.FLOW, "companies.route_profit"),
            Coupling(S.WAR, "a strong company seizes the land at its route's far end", E.TRIGGER, "companies.conquest_strength"),
            Coupling(S.ECONOMY, "a collapsing company costs every shareholder", E.FLOW, "companies.collapse_loss"),
        ),
    ),
    Mechanic(
        key="holy_orders",
        spec_item="S4.3/RP2",
        title="Faiths with warriors among their faithful found holy orders fed by their tithes and holding border towns",
        subsystem=S.FAITH,
        phases=("estates",),
        surface=Surface(drawer=ESTATES),
        backfill="none: holy orders rise from the next epoch",
        fields=("cult_entity_id", "fortress_entity_id", "tithe_share"),
        tables=(HolyOrderProfileRow.__tablename__,),
        exposure=Exposure.CONTEXT,
        targets=("cult", "faction", "settlement"),
        couplings=(
            Coupling(S.ECONOMY, "a holy order draws on its faith's tithes", E.FLOW, "holy_orders.tithe_wealth"),
            Coupling(S.WAR, "a holy order strengthens the defences of its border town", E.MODIFIER, "holy_orders.fortress_defense"),
        ),
    ),
    Mechanic(
        key="guild_ranks",
        spec_item="S4.3/RP2",
        title=(
            "Guild members rise from apprentice to grandmaster by their craft; guilds keep craft secrets, take in apprentices "
            "and raise the quality of their town's works"
        ),
        subsystem=S.ECONOMY,
        phases=("estates", "households", "refining"),
        surface=Surface(drawer=ESTATES),
        backfill="none: ranks and secrets are reckoned from the next epoch",
        fields=("rank", "technique"),
        tables=(GuildSecretRow.__tablename__,),
        exposure=Exposure.CONTEXT,
        targets=("faction", "mortal", "settlement"),
        couplings=(
            Coupling(S.KNOWLEDGE, "a guild's secret technique does not spread to other towns", E.TRIGGER, "guild_ranks.secret_pct"),
            Coupling(S.ECONOMY, "a craft guild's standards raise the quality of its town's works", E.MODIFIER, "guild_ranks.quality_bonus"),
            Coupling(S.HOUSEHOLD, "a child apprenticed in a guild town joins the guild", E.TRIGGER),
        ),
    ),
)
