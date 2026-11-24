from aerona.catalog.kinds.definition import Defined
from aerona.core.total import total
from aerona.domain.enums.ages import GiantMigration, PayoffKind, SeasonSource, SeasonSpell, SetupKind

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
                "engine.storyteller.drama.inheritance_paid",
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
                "engine.storyteller.drama.inheritance_paid",
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

SEASON_SOURCE = total(
    SeasonSource,
    {
        SeasonSource.IMPACT: Defined("Impact", checked_by=("engine.storyteller.control.source_belongs",), used_by=("catalog.long_seasons.CAUSES",)),
        SeasonSource.REGION: Defined("Region", checked_by=("engine.storyteller.control.source_belongs",), used_by=("catalog.long_seasons.CAUSES",)),
        SeasonSource.STAR: Defined("Star", checked_by=("engine.storyteller.control.source_belongs",), used_by=("catalog.long_seasons.CAUSES",)),
        SeasonSource.INCIDENT: Defined("Incident", checked_by=("engine.storyteller.control.source_belongs",), used_by=("catalog.long_seasons.CAUSES",)),
    },
)

SEASON_SPELL = total(
    SeasonSpell,
    {
        SeasonSpell.SUMMER: Defined(
            "Long summer",
            checked_by=("engine.environment.long_seasons.summer_drought", "engine.environment.long_seasons.turn", "engine.environment.spells.pull_of"),
            used_by=(
                "db.tables.ages.IrregularSeasonRow",
                "engine.environment.long_seasons.begin",
                "engine.environment.long_seasons.current_spell",
                "engine.environment.long_seasons.made_spell",
                "engine.environment.long_seasons.stellar_spells",
                "engine.environment.long_seasons.turn",
                "engine.storyteller.control.SpellDraft",
                "services.player.ages.SeasonDraft",
                "tools.son.ages.UnsettleSeasonsInput",
            ),
        ),
        SeasonSpell.WINTER: Defined(
            "Long winter",
            checked_by=(
                "engine.environment.long_seasons.bite",
                "engine.environment.long_seasons.lost_cause",
                "engine.environment.long_seasons.stellar_spells",
                "engine.environment.long_seasons.supernova_winter",
                "engine.environment.long_seasons.turn",
                "engine.environment.spells.pull_of",
                "engine.folkways.nutrition.light_of",
                "tools.son.ages.lengthen_winter",
            ),
            used_by=(
                "engine.environment.long_seasons.begin",
                "engine.environment.long_seasons.current_spell",
                "engine.environment.long_seasons.made_spell",
                "engine.environment.long_seasons.single_winter",
                "engine.environment.long_seasons.stellar_spells",
                "engine.environment.long_seasons.turn",
                "services.integrity.season_shares.impact_winters",
            ),
        ),
    },
)

SETUP_KIND = total(
    SetupKind,
    {
        SetupKind.PROPHECY: Defined("Prophecy", checked_by=(), used_by=("engine.storyteller.drama.log_setups", "engine.storyteller.drama.prophecy_paid")),
        SetupKind.OMEN: Defined("Omen", checked_by=(), used_by=("engine.storyteller.drama.log_setups", "engine.storyteller.drama.omen_paid")),
        SetupKind.DREAM: Defined("Dream", checked_by=(), used_by=("engine.storyteller.drama.dream_paid", "engine.storyteller.drama.log_setups")),
        SetupKind.FORESIGHT: Defined("Foresight", checked_by=(), used_by=("engine.storyteller.drama.foresight_paid", "engine.storyteller.drama.log_setups")),
        SetupKind.INCIDENT_ARC: Defined(
            "Open incident arc", checked_by=(), used_by=("engine.storyteller.drama.log_setups", "engine.storyteller.drama.thread_paid")
        ),
        SetupKind.PORTENT: Defined(
            "Portent of a god", checked_by=(), used_by=("engine.storyteller.drama.portent_paid", "services.player.ages.SetupDraft", "tools.son.ages.foreshadow")
        ),
        SetupKind.INHERITANCE: Defined(
            "Inheritance", checked_by=(), used_by=("engine.storyteller.drama.inheritance_paid", "engine.storyteller.drama.log_setups")
        ),
    },
)
