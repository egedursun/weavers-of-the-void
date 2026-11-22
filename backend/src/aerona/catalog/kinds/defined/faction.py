from aerona.catalog.kinds.definition import Defined
from aerona.core.total import total
from aerona.domain.enums.faction import FactionGoalKind, FactionScale

FACTION_GOAL_KIND = total(
    FactionGoalKind,
    {
        FactionGoalKind.LOWER_TAXES: Defined(
            "Lower taxes",
            checked_by=(),
            used_by=(
                "catalog.life.factions.CHOOSE_FACTION_GOAL_KINDS",
                "catalog.life.factions.GOAL_PLANS",
                "catalog.life.factions.GOAL_TARGET_FACTION_GOAL_KINDS",
                "catalog.life.factions.PETITION_TERMS_FACTION_GOAL_KINDS",
                "engine.industry.owners.lobby",
            ),
        ),
        FactionGoalKind.MONOPOLY_ON: Defined(
            "Monopoly on",
            checked_by=(
                "engine.factions.agenda.bribe",
                "engine.factions.agenda.choose",
                "engine.factions.agenda.goal_target",
                "engine.factions.agenda.petition_terms",
            ),
            used_by=("catalog.life.factions.GOAL_PLANS",),
        ),
        FactionGoalKind.INSTALL_CLAIMANT: Defined(
            "Install claimant",
            checked_by=("engine.factions.agenda.assassinate", "engine.factions.agenda.choose", "engine.factions.agenda.realm_goal"),
            used_by=("catalog.life.factions.GOAL_PLANS",),
        ),
        FactionGoalKind.ABOLISH_LAW: Defined(
            "Abolish law",
            checked_by=(
                "catalog.life.factions.CHOICES",
                "engine.factions.agenda.goal_target",
                "engine.factions.agenda.petition_terms",
                "engine.polity.enactment.faction_reading",
            ),
            used_by=(
                "catalog.life.factions.CHECKED_KEY_FACTION_GOAL_KINDS",
                "catalog.life.factions.CHOOSE_FACTION_GOAL_KINDS_2",
                "catalog.life.factions.GOALS",
                "catalog.life.factions.GOAL_PLANS",
                "engine.industry.owners.lobby",
            ),
        ),
        FactionGoalKind.ENACT_LAW: Defined(
            "Enact law",
            checked_by=(
                "catalog.life.factions.CHOICES",
                "engine.factions.agenda.goal_target",
                "engine.factions.agenda.petition_terms",
                "engine.polity.enactment.faction_reading",
            ),
            used_by=(
                "catalog.life.factions.CHECKED_KEY_FACTION_GOAL_KINDS",
                "catalog.life.factions.CHOOSE_FACTION_GOAL_KINDS_2",
                "catalog.life.factions.GOALS",
                "catalog.life.factions.GOAL_PLANS",
            ),
        ),
        FactionGoalKind.WAR_ON: Defined(
            "War on",
            checked_by=("catalog.life.factions.CHOICES",),
            used_by=("catalog.life.factions.GOAL_PLANS", "catalog.life.factions.REALM_GOAL_FACTION_GOAL_KINDS"),
        ),
        FactionGoalKind.PEACE_WITH: Defined(
            "Peace with",
            checked_by=("catalog.life.factions.CHOICES",),
            used_by=("catalog.life.factions.GOALS", "catalog.life.factions.GOAL_PLANS", "catalog.life.factions.REALM_GOAL_FACTION_GOAL_KINDS"),
        ),
        FactionGoalKind.PROTECT_CRAFT: Defined(
            "Protect craft",
            checked_by=("engine.industry.methods.resist",),
            used_by=(
                "catalog.life.factions.CHOOSE_FACTION_GOAL_KINDS",
                "catalog.life.factions.GOAL_PLANS",
                "catalog.life.factions.GOAL_TARGET_FACTION_GOAL_KINDS",
                "catalog.life.factions.PETITION_TERMS_FACTION_GOAL_KINDS",
                "engine.industry.methods.resist",
            ),
        ),
        FactionGoalKind.CONVERT_REALM: Defined(
            "Convert realm",
            checked_by=("catalog.life.factions.CHOICES", "engine.factions.agenda.petition_terms", "engine.factions.agenda.realm_goal"),
            used_by=("catalog.life.factions.CHOOSE_FACTION_GOAL_KINDS_2", "catalog.life.factions.GOALS", "catalog.life.factions.GOAL_PLANS"),
        ),
        FactionGoalKind.INDEPENDENCE: Defined(
            "Independence",
            checked_by=("catalog.life.factions.CHOICES", "engine.factions.agenda.realm_goal"),
            used_by=("catalog.life.factions.GOALS", "catalog.life.factions.GOAL_PLANS"),
        ),
        FactionGoalKind.LOOT: Defined(
            "Loot",
            checked_by=("engine.factions.agenda.choose", "engine.factions.agenda.goal_target", "engine.factions.agenda.realm_goal"),
            used_by=("catalog.life.factions.GOAL_PLANS",),
        ),
    },
)

FACTION_SCALE = total(
    FactionScale,
    {
        FactionScale.BAND: Defined(
            "Band",
            checked_by=(),
            used_by=(
                "db.kind_concepts.society.BUILT_IN_ORGANISATIONS",
                "db.tables.factions.FactionProfileRow",
                "engine.factions.agenda.dues",
                "engine.factions.book.new_profile",
                "engine.factions.offshoots.found_offshoot",
            ),
        ),
        FactionScale.COMPANY: Defined(
            "Company",
            checked_by=(),
            used_by=("db.kind_concepts.society.BUILT_IN_ORGANISATIONS", "db.tables.society_kinds.OrganisationKindRow", "engine.factions.agenda.dues"),
        ),
        FactionScale.ORGANISATION: Defined(
            "Organisation", checked_by=(), used_by=("db.kind_concepts.society.BUILT_IN_ORGANISATIONS", "engine.factions.agenda.dues")
        ),
        FactionScale.NETWORK: Defined("Network", checked_by=(), used_by=("db.kind_concepts.society.BUILT_IN_ORGANISATIONS", "engine.factions.agenda.dues")),
    },
)
