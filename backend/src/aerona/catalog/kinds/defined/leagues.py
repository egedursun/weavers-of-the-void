from aerona.catalog.kinds.definition import Defined
from aerona.core.total import total
from aerona.domain.enums.leagues import LeagueDecisionKind, LeagueOrgan, LeagueVoteBasis

LEAGUE_DECISION_KIND = total(
    LeagueDecisionKind,
    {
        LeagueDecisionKind.ADMIT: Defined(
            "Admit", checked_by=("engine.leagues.decisions.carry",), used_by=("engine.leagues.life.grow", "tools.mortal.leagues.join_league_tool")
        ),
        LeagueDecisionKind.EXPEL: Defined(
            "Expel", checked_by=("engine.leagues.decisions.carry",), used_by=("engine.leagues.decisions.AGAINST_SUBJECT", "engine.leagues.life.discipline")
        ),
        LeagueDecisionKind.SANCTION: Defined(
            "Sanction", checked_by=("engine.leagues.decisions.carry",), used_by=("engine.leagues.decisions.AGAINST_SUBJECT", "engine.leagues.life.discipline")
        ),
        LeagueDecisionKind.COMMON_TARIFF: Defined("Common tariff", checked_by=("engine.leagues.decisions.carry",), used_by=()),
        LeagueDecisionKind.COMMON_FORCE: Defined(
            "Common force", checked_by=("engine.leagues.decisions.carry",), used_by=("engine.leagues.decisions.AGAINST_SUBJECT", "engine.leagues.life.guard")
        ),
        LeagueDecisionKind.RULING: Defined("Ruling", checked_by=("engine.leagues.decisions.carry",), used_by=("engine.leagues.decisions.AGAINST_SUBJECT",)),
        LeagueDecisionKind.BUDGET: Defined("Budget", checked_by=("engine.leagues.decisions.carry",), used_by=("db.tables.leagues.LeagueDecisionRow",)),
        LeagueDecisionKind.MEDIATION: Defined("Mediation", checked_by=("engine.leagues.decisions.carry",), used_by=("engine.leagues.life.strife",)),
    },
)

LEAGUE_ORGAN = total(
    LeagueOrgan,
    {
        LeagueOrgan.ASSEMBLY: Defined(
            "Assembly",
            checked_by=(),
            used_by=(
                "db.tables.leagues.LeagueDecisionRow",
                "engine.leagues.decisions.organ_for",
                "engine.leagues.founding.organs_for",
                "engine.leagues.life.discipline",
                "engine.leagues.life.grow",
                "services.integrity.league_links.give_organ",
                "tools.mortal.leagues.join_league_tool",
            ),
        ),
        LeagueOrgan.COUNCIL: Defined(
            "Council", checked_by=(), used_by=("engine.leagues.founding.ORGANS_OF_AIMS", "engine.leagues.founding.organs_for", "engine.leagues.life.discipline")
        ),
        LeagueOrgan.COURT: Defined("Court", checked_by=(), used_by=("engine.leagues.founding.ORGANS_OF_AIMS", "engine.leagues.life.strife")),
        LeagueOrgan.SECRETARIAT: Defined("Secretariat", checked_by=(), used_by=("engine.leagues.founding.ORGANS_OF_AIMS",)),
        LeagueOrgan.FORCE: Defined("Force", checked_by=(), used_by=("engine.leagues.founding.ORGANS_OF_AIMS", "engine.leagues.life.guard")),
    },
)

LEAGUE_VOTE_BASIS = total(
    LeagueVoteBasis,
    {
        LeagueVoteBasis.ONE_MEMBER_ONE_VOTE: Defined(
            "One realm, one vote",
            checked_by=(),
            used_by=("db.tables.leagues.PolityLeagueRow", "engine.leagues.rise.from_treaty", "services.player.leagues.FoundLeague"),
        ),
        LeagueVoteBasis.BY_POPULATION: Defined("By population", checked_by=("engine.leagues.decisions.weight",), used_by=()),
        LeagueVoteBasis.BY_DUES: Defined("By dues paid", checked_by=("engine.leagues.decisions.weight",), used_by=()),
        LeagueVoteBasis.BY_VETO_HOLDERS: Defined(
            "By the veto holders", checked_by=("engine.leagues.decisions.weight", "engine.leagues.founding.found_league"), used_by=()
        ),
    },
)
