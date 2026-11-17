from aerona.catalog.kinds.definition import Defined
from aerona.core.total import total
from aerona.domain.enums.ages import ArcTemplate, GiantMigration, PayoffKind, SeasonSpell

ARC_TEMPLATE = total(
    ArcTemplate,
    {
        ArcTemplate.RISE_AND_FALL: Defined(
            "Rise and fall",
            checked_by=(),
            used_by=("engine.storyteller.arcs.ENDS_IN_DEATH", "engine.storyteller.arcs.deposed", "engine.storyteller.drama.ADVANCED_BY"),
        ),
        ArcTemplate.RAGS_TO_RICHES: Defined(
            "From poverty to wealth", checked_by=(), used_by=("engine.storyteller.arcs.rulers", "engine.storyteller.drama.ADVANCED_BY")
        ),
        ArcTemplate.REVENGE: Defined(
            "Revenge",
            checked_by=("engine.storyteller.arcs.outcome_on_death", "tools.mortal.ages.swear_vengeance"),
            used_by=(
                "engine.storyteller.arcs.betrayals",
                "engine.storyteller.arcs.revenge",
                "engine.storyteller.drama.ADVANCED_BY",
                "engine.storyteller.drama.CONFRONTING",
                "tools.mortal.ages.swear_vengeance",
            ),
        ),
        ArcTemplate.REDEMPTION: Defined("Redemption", checked_by=(), used_by=("engine.storyteller.arcs.redemption", "engine.storyteller.drama.ADVANCED_BY")),
        ArcTemplate.QUEST: Defined(
            "Quest",
            checked_by=("engine.storyteller.arcs.stages_of",),
            used_by=(
                "engine.storyteller.arcs.quests",
                "engine.storyteller.drama.ADVANCED_BY",
                "services.player.ages.ArcDraft",
                "services.player.ages.EchoDraft",
            ),
        ),
        ArcTemplate.TRAGEDY: Defined(
            "Tragedy",
            checked_by=(),
            used_by=("engine.storyteller.arcs.ENDS_IN_DEATH", "engine.storyteller.arcs.rulers", "engine.storyteller.drama.ADVANCED_BY"),
        ),
        ArcTemplate.FORBIDDEN_LOVE: Defined(
            "Forbidden love", checked_by=(), used_by=("engine.storyteller.arcs.forbidden_love", "engine.storyteller.drama.ADVANCED_BY")
        ),
        ArcTemplate.RIVALRY: Defined(
            "Rivalry",
            checked_by=(),
            used_by=("engine.storyteller.arcs.rivalry", "engine.storyteller.drama.ADVANCED_BY", "engine.storyteller.drama.CONFRONTING"),
        ),
        ArcTemplate.MENTOR_AND_HEIR: Defined(
            "Mentor and heir", checked_by=(), used_by=("engine.storyteller.arcs.apprenticeship", "engine.storyteller.drama.ADVANCED_BY")
        ),
        ArcTemplate.EXILE_AND_RETURN: Defined(
            "Exile and return", checked_by=(), used_by=("engine.storyteller.arcs.exile", "engine.storyteller.drama.ADVANCED_BY")
        ),
        ArcTemplate.CORRUPTION: Defined("Corruption", checked_by=(), used_by=("engine.storyteller.arcs.corruption", "engine.storyteller.drama.ADVANCED_BY")),
        ArcTemplate.COMING_OF_AGE: Defined(
            "Coming of age", checked_by=(), used_by=("engine.storyteller.arcs.apprenticeship", "engine.storyteller.drama.ADVANCED_BY")
        ),
        ArcTemplate.FALL_OF_A_HOUSE: Defined(
            "Fall of a house",
            checked_by=(),
            used_by=("engine.storyteller.arcs.ENDS_IN_DEATH", "engine.storyteller.arcs.houses", "engine.storyteller.drama.ADVANCED_BY"),
        ),
        ArcTemplate.FOUNDING: Defined("Founding", checked_by=(), used_by=("engine.storyteller.arcs.houses", "engine.storyteller.drama.ADVANCED_BY")),
        ArcTemplate.APOTHEOSIS: Defined("Apotheosis", checked_by=(), used_by=("engine.storyteller.arcs.apotheosis", "engine.storyteller.drama.ADVANCED_BY")),
    },
)

GIANT_MIGRATION = total(
    GiantMigration,
    {
        GiantMigration.NONE: Defined(
            "The giants stayed", checked_by=(), used_by=("db.tables.ages.FormationHistoryRow", "engine.cosmos.formation.migration_for")
        ),
        GiantMigration.INWARD: Defined(
            "The giants moved inward", checked_by=("engine.cosmos.formation.water_of",), used_by=("engine.cosmos.formation.migration_for",)
        ),
        GiantMigration.OUTWARD: Defined(
            "The giants moved outward", checked_by=("engine.cosmos.formation.water_of",), used_by=("engine.cosmos.formation.migration_for",)
        ),
    },
)

PAYOFF_KIND = total(
    PayoffKind,
    {
        PayoffKind.OPEN: Defined(
            "Waiting",
            checked_by=(
                "agents.context.ages_lines.son_ages_lines",
                "engine.storyteller.drama.pay_setups",
                "engine.storyteller.drama.press_stalled",
                "services.integrity.ages_links.mend_ages_links",
            ),
            used_by=("db.tables.ages.SetupRow",),
        ),
        PayoffKind.FULFILLED: Defined(
            "Fulfilled",
            checked_by=(),
            used_by=(
                "engine.storyteller.drama.dream_paid",
                "engine.storyteller.drama.foresight_paid",
                "engine.storyteller.drama.omen_paid",
                "engine.storyteller.drama.portent_paid",
                "engine.storyteller.drama.prophecy_paid",
                "engine.storyteller.drama.thread_paid",
            ),
        ),
        PayoffKind.SUBVERTED: Defined(
            "Subverted",
            checked_by=(),
            used_by=(
                "engine.storyteller.drama.dream_paid",
                "engine.storyteller.drama.foresight_paid",
                "engine.storyteller.drama.omen_paid",
                "engine.storyteller.drama.prophecy_paid",
            ),
        ),
        PayoffKind.LAPSED: Defined(
            "Lapsed",
            checked_by=("agents.context.chronicle_facts.payoff_facts", "engine.storyteller.drama.pay_setups"),
            used_by=("engine.storyteller.drama.resolution_of", "services.integrity.ages_links.mend_ages_links"),
        ),
    },
)

SEASON_SPELL = total(
    SeasonSpell,
    {
        SeasonSpell.SUMMER: Defined(
            "Long summer",
            checked_by=("engine.environment.long_seasons.turn",),
            used_by=("db.tables.ages.IrregularSeasonRow", "engine.environment.long_seasons.begin", "engine.environment.long_seasons.turn"),
        ),
        SeasonSpell.WINTER: Defined(
            "Long winter",
            checked_by=(
                "agents.context.ages_lines.season_lines",
                "agents.context.ages_lines.son_ages_lines",
                "engine.environment.long_seasons.keep_seasons",
                "engine.environment.long_seasons.lost_cause",
                "engine.environment.long_seasons.turn",
                "engine.environment.long_seasons.winter_share",
                "engine.folkways.nutrition.light_of",
                "tools.son.ages.lengthen_winter",
            ),
            used_by=("engine.environment.long_seasons.turn",),
        ),
    },
)
