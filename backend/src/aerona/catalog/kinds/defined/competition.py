from aerona.catalog.kinds.definition import Defined
from aerona.core.total import total
from aerona.domain.enums.competition import CompetitionClause, EntryBarrier

COMPETITION_CLAUSE = total(
    CompetitionClause,
    {
        CompetitionClause.MERGER_REVIEW: Defined("Merger review", checked_by=(), used_by=("engine.competition.law.merger_barred",)),
        CompetitionClause.CARTEL_BAN: Defined(
            "Cartel ban", checked_by=(), used_by=("engine.competition.cartels.tend_cartel", "tools.mortal.competition.report_cartel_tool")
        ),
        CompetitionClause.MONOPOLY_BREAK: Defined("Monopoly break", checked_by=(), used_by=("engine.competition.law.break_monopoly",)),
        CompetitionClause.PRICE_CAP: Defined("Price cap", checked_by=(), used_by=("engine.competition.pricing.market_factors",)),
        CompetitionClause.LICENCE_LIMIT: Defined("Licence limit", checked_by=(), used_by=("engine.competition.structure.derived_barriers",)),
        CompetitionClause.INSIDER_BAN: Defined("Insider ban", checked_by=(), used_by=("engine.securities.pricing.insiders",)),
    },
)

ENTRY_BARRIER = total(
    EntryBarrier,
    {
        EntryBarrier.CAPITAL: Defined("Capital", checked_by=(), used_by=("engine.competition.structure.derived_barriers",)),
        EntryBarrier.LICENCE: Defined("Licence", checked_by=(), used_by=("engine.competition.structure.derived_barriers",)),
        EntryBarrier.GUILD_RIGHT: Defined("Guild right", checked_by=(), used_by=("engine.competition.structure.derived_barriers",)),
        EntryBarrier.SECRET_TECHNIQUE: Defined("Secret technique", checked_by=(), used_by=("engine.competition.structure.derived_barriers",)),
        EntryBarrier.ROUTE_CONTROL: Defined("Route control", checked_by=(), used_by=("engine.competition.structure.derived_barriers",)),
        EntryBarrier.NETWORK_CONTROL: Defined("Network control", checked_by=(), used_by=("engine.competition.structure.derived_barriers",)),
        EntryBarrier.DIVINE_FAVOUR: Defined("Divine favour", checked_by=(), used_by=("engine.competition.structure.derived_barriers",)),
    },
)
