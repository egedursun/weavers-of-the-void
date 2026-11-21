from enum import StrEnum


class MarketForm(StrEnum):
    MANY_SELLERS = "many_sellers"
    FEW_SELLERS = "few_sellers"
    ONE_SELLER = "one_seller"
    ONE_BUYER = "one_buyer"
    FEW_BUYERS = "few_buyers"


class EntryBarrier(StrEnum):
    CAPITAL = "capital"
    LICENCE = "licence"
    GUILD_RIGHT = "guild_right"
    SECRET_TECHNIQUE = "secret_technique"
    ROUTE_CONTROL = "route_control"
    NETWORK_CONTROL = "network_control"
    DIVINE_FAVOUR = "divine_favour"


class CartelAim(StrEnum):
    PRICE = "price"
    QUOTA = "quota"
    TERRITORY = "territory"
    BID_RIGGING = "bid_rigging"


class PriceWarOutcome(StrEnum):
    ONGOING = "ongoing"
    WON = "won"
    LOST = "lost"
    CALLED_OFF = "called_off"


class CompetitionClause(StrEnum):
    MERGER_REVIEW = "merger_review"
    CARTEL_BAN = "cartel_ban"
    MONOPOLY_BREAK = "monopoly_break"
    PRICE_CAP = "price_cap"
    LICENCE_LIMIT = "licence_limit"
    INSIDER_BAN = "insider_ban"
