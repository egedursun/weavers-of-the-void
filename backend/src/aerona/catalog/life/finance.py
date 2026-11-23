from aerona.catalog.life.domain import CRIME_KINDS
from aerona.domain.enums.faction import FactionKind
from aerona.domain.enums.finance import CreditState
from aerona.domain.enums.polity import TreatyKind
from aerona.domain.enums.society import KnowledgeBranch

OUTLAWS = (FactionKind.BANDITS, FactionKind.PIRATES, FactionKind.ROUTE_RAIDERS, *sorted(CRIME_KINDS))


FORBIDDEN_LORE = (KnowledgeBranch.FORBIDDEN, KnowledgeBranch.MAGIC)


OUTLAW_KINDS = (FactionKind.BANDITS, FactionKind.PIRATES, FactionKind.ROUTE_RAIDERS, *sorted(CRIME_KINDS))


MERCHANT_GUILDS = (FactionKind.MERCHANT_GUILD, FactionKind.WANDERING_MARKET)


ALLIANCES = (TreatyKind.ALLIANCE_DEFENSIVE, TreatyKind.ALLIANCE_OFFENSIVE)


SPECULATION_MERCHANT_GUILDS = (FactionKind.MERCHANT_GUILD, FactionKind.WANDERING_MARKET)

REFUSES_CREDIT_STATES = (CreditState.DEFAULT, CreditState.RESTRUCTURING, CreditState.RESCUED, CreditState.REPUDIATED)
BURDENED_STATES = (CreditState.STRAINED, CreditState.DEFAULT)
