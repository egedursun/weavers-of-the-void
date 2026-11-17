from aerona.catalog.kinds.definition import Defined
from aerona.core.total import total
from aerona.domain.enums.faction import FactionActionKind, FactionGoalKind, FactionScale

FACTION_ACTION_KIND = total(
    FactionActionKind,
    {
        FactionActionKind.LOBBY: Defined(
            "Lobby",
            checked_by=("engine.factions.agenda.act",),
            used_by=("engine.factions.agenda.CHOICES", "engine.factions.agenda.choose", "engine.factions.agenda.lobby"),
        ),
        FactionActionKind.BRIBE: Defined(
            "Bribe", checked_by=("engine.factions.agenda.act",), used_by=("engine.factions.agenda.bribe", "engine.factions.agenda.choose")
        ),
        FactionActionKind.PETITION: Defined(
            "Petition", checked_by=("engine.factions.agenda.act",), used_by=("engine.factions.agenda.choose", "engine.factions.agenda.petition")
        ),
        FactionActionKind.STRIKE: Defined(
            "Strike",
            checked_by=("engine.factions.agenda.act",),
            used_by=("engine.factions.agenda.DEFIANT", "engine.factions.agenda.choose", "engine.factions.agenda.strike"),
        ),
        FactionActionKind.RIOT: Defined(
            "Riot",
            checked_by=("engine.factions.agenda.act",),
            used_by=("engine.factions.agenda.CHOICES", "engine.factions.agenda.DEFIANT", "engine.factions.agenda.choose", "engine.factions.agenda.riot"),
        ),
        FactionActionKind.COUP: Defined(
            "Coup",
            checked_by=("engine.factions.agenda.act",),
            used_by=("engine.factions.agenda.DEFIANT", "engine.factions.agenda.choose", "engine.factions.agenda.coup"),
        ),
        FactionActionKind.ASSASSINATE: Defined(
            "Assassinate",
            checked_by=("engine.factions.agenda.act",),
            used_by=("engine.factions.agenda.DEFIANT", "engine.factions.agenda.assassinate", "engine.factions.agenda.choose"),
        ),
        FactionActionKind.SMUGGLE: Defined(
            "Smuggle", checked_by=("engine.factions.agenda.act",), used_by=("engine.factions.agenda.choose", "engine.factions.agenda.smuggle")
        ),
        FactionActionKind.RAID: Defined(
            "Raid",
            checked_by=("engine.factions.agenda.act",),
            used_by=("engine.factions.agenda.choose", "engine.factions.agenda.raid", "engine.factions.outlaws.privateers"),
        ),
        FactionActionKind.FUND_WAR: Defined(
            "Fund war", checked_by=("engine.factions.agenda.act",), used_by=("engine.factions.agenda.CHOICES", "engine.factions.agenda.fund_war")
        ),
        FactionActionKind.RECRUIT: Defined(
            "Recruit", checked_by=("engine.factions.agenda.act",), used_by=("engine.factions.agenda.choose", "engine.factions.agenda.recruit")
        ),
        FactionActionKind.SCHISM: Defined("Schism", checked_by=(), used_by=("engine.factions.agenda.schisms",)),
        FactionActionKind.SUPPRESSED: Defined("Suppressed", checked_by=(), used_by=("engine.factions.outlaws.suppress",)),
        FactionActionKind.HIRED: Defined("Hired", checked_by=(), used_by=("engine.factions.outlaws.contract",)),
        FactionActionKind.DEFECTED: Defined("Defected", checked_by=(), used_by=("engine.factions.outlaws.defect",)),
    },
)

FACTION_GOAL_KIND = total(
    FactionGoalKind,
    {
        FactionGoalKind.LOWER_TAXES: Defined(
            "Lower taxes",
            checked_by=("engine.factions.agenda.choose", "engine.factions.agenda.goal_target", "engine.factions.agenda.petition_terms"),
            used_by=("engine.factions.agenda.GOAL_PLANS", "engine.industry.owners.lobby"),
        ),
        FactionGoalKind.MONOPOLY_ON: Defined(
            "Monopoly on",
            checked_by=(
                "engine.factions.agenda.bribe",
                "engine.factions.agenda.choose",
                "engine.factions.agenda.goal_target",
                "engine.factions.agenda.petition_terms",
            ),
            used_by=("engine.factions.agenda.GOAL_PLANS",),
        ),
        FactionGoalKind.INSTALL_CLAIMANT: Defined(
            "Install claimant",
            checked_by=("engine.factions.agenda.assassinate", "engine.factions.agenda.choose", "engine.factions.agenda.realm_goal"),
            used_by=("engine.factions.agenda.GOAL_PLANS",),
        ),
        FactionGoalKind.ABOLISH_LAW: Defined(
            "Abolish law",
            checked_by=(
                "engine.factions.agenda.CHOICES",
                "engine.factions.agenda.choose",
                "engine.factions.agenda.goal_target",
                "engine.factions.agenda.petition_terms",
                "engine.factions.control.checked_key",
                "engine.polity.enactment.faction_reading",
            ),
            used_by=("engine.factions.agenda.GOAL_PLANS", "engine.factions.movements.GOALS", "engine.industry.owners.lobby"),
        ),
        FactionGoalKind.ENACT_LAW: Defined(
            "Enact law",
            checked_by=(
                "engine.factions.agenda.CHOICES",
                "engine.factions.agenda.choose",
                "engine.factions.agenda.goal_target",
                "engine.factions.agenda.petition_terms",
                "engine.factions.control.checked_key",
                "engine.polity.enactment.faction_reading",
            ),
            used_by=("engine.factions.agenda.GOAL_PLANS", "engine.factions.movements.GOALS"),
        ),
        FactionGoalKind.WAR_ON: Defined(
            "War on", checked_by=("engine.factions.agenda.CHOICES", "engine.factions.agenda.realm_goal"), used_by=("engine.factions.agenda.GOAL_PLANS",)
        ),
        FactionGoalKind.PEACE_WITH: Defined(
            "Peace with",
            checked_by=("engine.factions.agenda.CHOICES", "engine.factions.agenda.realm_goal"),
            used_by=("engine.factions.agenda.GOAL_PLANS", "engine.factions.movements.GOALS"),
        ),
        FactionGoalKind.PROTECT_CRAFT: Defined(
            "Protect craft",
            checked_by=(
                "engine.factions.agenda.choose",
                "engine.factions.agenda.goal_target",
                "engine.factions.agenda.petition_terms",
                "engine.industry.methods.resist",
            ),
            used_by=("engine.factions.agenda.GOAL_PLANS", "engine.industry.methods.resist"),
        ),
        FactionGoalKind.CONVERT_REALM: Defined(
            "Convert realm",
            checked_by=(
                "engine.factions.agenda.CHOICES",
                "engine.factions.agenda.choose",
                "engine.factions.agenda.petition_terms",
                "engine.factions.agenda.realm_goal",
            ),
            used_by=("engine.factions.agenda.GOAL_PLANS", "engine.factions.movements.GOALS"),
        ),
        FactionGoalKind.INDEPENDENCE: Defined(
            "Independence",
            checked_by=("engine.factions.agenda.CHOICES", "engine.factions.agenda.realm_goal"),
            used_by=("engine.factions.agenda.GOAL_PLANS", "engine.factions.movements.GOALS"),
        ),
        FactionGoalKind.LOOT: Defined(
            "Loot",
            checked_by=("engine.factions.agenda.choose", "engine.factions.agenda.goal_target", "engine.factions.agenda.realm_goal"),
            used_by=("engine.factions.agenda.GOAL_PLANS",),
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
                "engine.factions.agenda.schisms",
                "engine.factions.book.new_profile",
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
