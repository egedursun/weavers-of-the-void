from collections.abc import Mapping
from types import MappingProxyType

from aerona.core.total import total
from aerona.domain.enums.economy import CommodityKind
from aerona.domain.enums.faction import FactionActionKind, FactionGoalKind, FactionKind
from aerona.domain.enums.polity import LawKind
from aerona.domain.enums.society import SocialClass

GOAL_PLANS: dict[FactionKind, tuple[FactionGoalKind, ...]] = {
    FactionKind.MERCHANT_GUILD: (FactionGoalKind.LOWER_TAXES, FactionGoalKind.MONOPOLY_ON, FactionGoalKind.PEACE_WITH, FactionGoalKind.GAIN_PRIVILEGE),
    FactionKind.CRAFT_GUILD: (FactionGoalKind.PROTECT_CRAFT, FactionGoalKind.MONOPOLY_ON, FactionGoalKind.LOWER_TAXES, FactionGoalKind.RUIN_RIVAL),
    FactionKind.PRIESTHOOD: (FactionGoalKind.CONVERT_REALM, FactionGoalKind.ENACT_LAW, FactionGoalKind.GAIN_PRIVILEGE),
    FactionKind.WARRIOR_ORDER: (FactionGoalKind.WAR_ON, FactionGoalKind.ENACT_LAW),
    FactionKind.NOBLE_COUNCIL: (FactionGoalKind.INSTALL_CLAIMANT, FactionGoalKind.ABOLISH_LAW, FactionGoalKind.LOWER_TAXES, FactionGoalKind.WIN_OFFICE),
    FactionKind.PEASANT_LEAGUE: (FactionGoalKind.LOWER_TAXES, FactionGoalKind.ABOLISH_LAW),
    FactionKind.REBELS: (FactionGoalKind.INDEPENDENCE, FactionGoalKind.INSTALL_CLAIMANT),
    FactionKind.BANDITS: (FactionGoalKind.LOOT,),
    FactionKind.PIRATES: (FactionGoalKind.LOOT,),
    FactionKind.ROUTE_RAIDERS: (FactionGoalKind.LOOT,),
    FactionKind.SOCIAL_CIRCLE: (),
    FactionKind.ASSASSINS: (FactionGoalKind.INSTALL_CLAIMANT, FactionGoalKind.LOOT),
    FactionKind.SCHOLARS_ACADEMY: (FactionGoalKind.ENACT_LAW, FactionGoalKind.PROTECT_CRAFT),
    FactionKind.SECRET_SOCIETY: (FactionGoalKind.INSTALL_CLAIMANT, FactionGoalKind.CONVERT_REALM),
    FactionKind.MERCENARY_COMPANY: (FactionGoalKind.LOOT, FactionGoalKind.WAR_ON),
    FactionKind.INTERWORLD_FEDERATION: (FactionGoalKind.PEACE_WITH, FactionGoalKind.LOWER_TAXES),
    FactionKind.WANDERING_MARKET: (FactionGoalKind.LOWER_TAXES, FactionGoalKind.MONOPOLY_ON),
    FactionKind.CRIME_FAMILY: (FactionGoalKind.LOOT, FactionGoalKind.MONOPOLY_ON, FactionGoalKind.RUIN_RIVAL),
    FactionKind.THIEVES_GUILD: (FactionGoalKind.LOOT,),
    FactionKind.SMUGGLING_RING: (FactionGoalKind.LOOT, FactionGoalKind.LOWER_TAXES),
    FactionKind.PIRATE_CONFEDERACY: (FactionGoalKind.LOOT,),
    FactionKind.WORKERS_UNION: (FactionGoalKind.LOWER_TAXES, FactionGoalKind.ABOLISH_LAW),
    FactionKind.ENGINEERS_SOCIETY: (FactionGoalKind.PROTECT_CRAFT, FactionGoalKind.ENACT_LAW),
    FactionKind.FINANCIERS: (FactionGoalKind.MONOPOLY_ON, FactionGoalKind.LOWER_TAXES, FactionGoalKind.PEACE_WITH),
    FactionKind.VETERANS: (FactionGoalKind.ENACT_LAW, FactionGoalKind.INSTALL_CLAIMANT, FactionGoalKind.WAR_ON),
    FactionKind.WORKER_BODY: (FactionGoalKind.ENACT_LAW, FactionGoalKind.ABOLISH_LAW, FactionGoalKind.LOWER_TAXES),
    FactionKind.ESTATE: (FactionGoalKind.GAIN_PRIVILEGE, FactionGoalKind.WIN_OFFICE),
    FactionKind.PARTY: (FactionGoalKind.WIN_OFFICE, FactionGoalKind.RUIN_RIVAL, FactionGoalKind.ENACT_LAW),
}


LAW_WISHES: dict[FactionKind, tuple[LawKind, dict[str, int | str | bool]]] = {
    FactionKind.PRIESTHOOD: (LawKind.TITHE, {"rate": 10, "enforced": True}),
    FactionKind.WARRIOR_ORDER: (LawKind.VETERAN_PENSION, {"amount": 30}),
    FactionKind.VETERANS: (LawKind.VETERAN_PENSION, {"amount": 30}),
    FactionKind.WORKER_BODY: (LawKind.LABOUR_LAW, {"max_hours": 48, "unions": True, "bodies": "recognised"}),
    FactionKind.SCHOLARS_ACADEMY: (LawKind.LICENSED_MAGIC, {"fee": 10}),
    FactionKind.CRAFT_GUILD: (LawKind.GUILD_CHARTER, {"monopoly": True}),
    FactionKind.MERCHANT_GUILD: (LawKind.GUILD_CHARTER, {"monopoly": True}),
}


LAW_GRIEVANCES: dict[FactionKind, LawKind] = {
    FactionKind.PEASANT_LEAGUE: LawKind.SERFDOM,
    FactionKind.NOBLE_COUNCIL: LawKind.TAX_RATE,
    FactionKind.MERCHANT_GUILD: LawKind.TOLLS,
}


MONOPOLY_GOODS: dict[FactionKind, CommodityKind] = {
    FactionKind.MERCHANT_GUILD: CommodityKind.LUXURIES,
    FactionKind.CRAFT_GUILD: CommodityKind.TOOLS,
    FactionKind.WANDERING_MARKET: CommodityKind.LUXURIES,
}


CHOICES: dict[FactionGoalKind, FactionActionKind] = {
    FactionGoalKind.ENACT_LAW: FactionActionKind.LOBBY,
    FactionGoalKind.ABOLISH_LAW: FactionActionKind.LOBBY,
    FactionGoalKind.CONVERT_REALM: FactionActionKind.LOBBY,
    FactionGoalKind.WAR_ON: FactionActionKind.FUND_WAR,
    FactionGoalKind.INDEPENDENCE: FactionActionKind.RIOT,
    FactionGoalKind.PEACE_WITH: FactionActionKind.LOBBY,
    FactionGoalKind.GAIN_PRIVILEGE: FactionActionKind.LOBBY,
    FactionGoalKind.WIN_OFFICE: FactionActionKind.PROPAGANDA,
    FactionGoalKind.RUIN_RIVAL: FactionActionKind.BOYCOTT,
}


CLASS_OF_KIND = MappingProxyType(
    {
        FactionKind.MERCHANT_GUILD: SocialClass.MERCHANT,
        FactionKind.CRAFT_GUILD: SocialClass.ARTISAN,
        FactionKind.PRIESTHOOD: SocialClass.PRIEST,
        FactionKind.WARRIOR_ORDER: SocialClass.WARRIOR,
        FactionKind.NOBLE_COUNCIL: SocialClass.NOBLE,
        FactionKind.PEASANT_LEAGUE: SocialClass.FARMER,
        FactionKind.SCHOLARS_ACADEMY: SocialClass.SCRIBE,
        FactionKind.BANDITS: SocialClass.OUTCAST,
        FactionKind.PIRATES: SocialClass.OUTCAST,
        FactionKind.ASSASSINS: SocialClass.OUTCAST,
        FactionKind.MERCENARY_COMPANY: SocialClass.WARRIOR,
        FactionKind.REBELS: SocialClass.FARMER,
        FactionKind.CRIME_FAMILY: SocialClass.OUTCAST,
        FactionKind.THIEVES_GUILD: SocialClass.OUTCAST,
        FactionKind.SMUGGLING_RING: SocialClass.OUTCAST,
        FactionKind.PIRATE_CONFEDERACY: SocialClass.OUTCAST,
        FactionKind.WORKERS_UNION: SocialClass.ARTISAN,
        FactionKind.WORKER_BODY: SocialClass.WORKER,
        FactionKind.ENGINEERS_SOCIETY: SocialClass.PROFESSIONAL,
        FactionKind.FINANCIERS: SocialClass.MERCHANT,
        FactionKind.VETERANS: SocialClass.WARRIOR,
    }
)


GUILDS = (FactionKind.CRAFT_GUILD, FactionKind.MERCHANT_GUILD)


GOAL_TARGET_FACTION_GOAL_KINDS = frozenset({FactionGoalKind.LOWER_TAXES, FactionGoalKind.PROTECT_CRAFT})
REALM_GOAL_FACTION_GOAL_KINDS = frozenset({FactionGoalKind.WAR_ON, FactionGoalKind.PEACE_WITH})
CHOOSE_FACTION_GOAL_KINDS = frozenset({FactionGoalKind.LOWER_TAXES, FactionGoalKind.PROTECT_CRAFT})
CHOOSE_FACTION_GOAL_KINDS_2 = frozenset({FactionGoalKind.ENACT_LAW, FactionGoalKind.ABOLISH_LAW, FactionGoalKind.CONVERT_REALM})
PETITION_TERMS_FACTION_GOAL_KINDS = frozenset({FactionGoalKind.LOWER_TAXES, FactionGoalKind.PROTECT_CRAFT})
CHECKED_KEY_FACTION_GOAL_KINDS = frozenset({FactionGoalKind.ENACT_LAW, FactionGoalKind.ABOLISH_LAW})
SUPPRESS_FACTION_KINDS = frozenset({FactionKind.BANDITS, FactionKind.PIRATES})


GOAL_WEIGHTS: Mapping[FactionGoalKind, str] = total(
    FactionGoalKind,
    {
        FactionGoalKind.LOWER_TAXES: "lower_taxes_weight",
        FactionGoalKind.MONOPOLY_ON: "monopoly_on_weight",
        FactionGoalKind.INSTALL_CLAIMANT: "install_claimant_weight",
        FactionGoalKind.ABOLISH_LAW: "abolish_law_weight",
        FactionGoalKind.ENACT_LAW: "enact_law_weight",
        FactionGoalKind.WAR_ON: "war_on_weight",
        FactionGoalKind.PEACE_WITH: "peace_with_weight",
        FactionGoalKind.PROTECT_CRAFT: "protect_craft_weight",
        FactionGoalKind.CONVERT_REALM: "convert_realm_weight",
        FactionGoalKind.INDEPENDENCE: "independence_weight",
        FactionGoalKind.LOOT: "loot_weight",
        FactionGoalKind.GAIN_PRIVILEGE: "gain_privilege_weight",
        FactionGoalKind.WIN_OFFICE: "win_office_weight",
        FactionGoalKind.RUIN_RIVAL: "ruin_rival_weight",
        FactionGoalKind.PROTECT_MEMBERS: "protect_members_weight",
        FactionGoalKind.FOUND_SETTLEMENT: "found_settlement_weight",
    },
)
