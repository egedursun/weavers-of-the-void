from aerona.catalog.kinds.definition import Defined
from aerona.core.total import total
from aerona.domain.enums.military import CaptiveFate, CasualtyFate, DuelContext, FeudParty, OutcomeClass, SabotageKind, SiegeWork, SpyOwnerKind, TargetClass

CAPTIVE_FATE = total(
    CaptiveFate,
    {
        CaptiveFate.HELD: Defined(
            "Held",
            checked_by=(
                "agents.context.society.war_lines",
                "engine.military.captivity.announce",
                "engine.military.captivity.cohort_fates",
                "engine.military.captivity.exchange_at_peace",
                "engine.military.control.settle_cohort",
                "engine.military.peace.release_all",
            ),
            used_by=(
                "db.tables.military.CaptiveCohortRow",
                "engine.military.captivity.decide",
                "engine.military.clash.captives_taken",
                "engine.military.siege_depth.mass_captives",
                "engine.tongues.pidgins.BOUND",
            ),
        ),
        CaptiveFate.RANSOMED: Defined("Ransomed", checked_by=("engine.military.control.settle_cohort",), used_by=("engine.military.captivity.decide",)),
        CaptiveFate.ENSLAVED: Defined(
            "Enslaved", checked_by=("engine.military.control.settle_cohort",), used_by=("engine.military.captivity.put_to_work", "engine.tongues.pidgins.BOUND")
        ),
        CaptiveFate.SACRIFICED: Defined("Sacrificed", checked_by=(), used_by=("engine.military.captivity.decide",)),
        CaptiveFate.LABOUR: Defined(
            "Labour", checked_by=("engine.military.control.settle_cohort",), used_by=("engine.military.captivity.put_to_work", "engine.tongues.pidgins.BOUND")
        ),
        CaptiveFate.EXCHANGED: Defined(
            "Exchanged", checked_by=("engine.military.control.settle_cohort",), used_by=("engine.military.captivity.exchange_at_peace",)
        ),
        CaptiveFate.RELEASED: Defined(
            "Released", checked_by=("engine.military.control.settle_cohort",), used_by=("engine.military.captivity.decide", "engine.military.peace.release_all")
        ),
    },
)

CASUALTY_FATE = total(
    CasualtyFate,
    {
        CasualtyFate.KILLED: Defined("Killed", checked_by=(), used_by=("engine.phases.warfare.DUEL_FATES", "engine.phases.warfare.duel")),
        CasualtyFate.WOUNDED: Defined("Wounded", checked_by=(), used_by=("engine.phases.warfare.DUEL_FATES",)),
        CasualtyFate.MAIMED: Defined("Maimed", checked_by=(), used_by=("engine.phases.warfare.DUEL_FATES",)),
        CasualtyFate.CAPTURED: Defined("Captured", checked_by=(), used_by=("engine.phases.warfare._heroics",)),
    },
)

DUEL_CONTEXT = total(
    DuelContext,
    {
        DuelContext.WAR: Defined("War", checked_by=(), used_by=("engine.phases.warfare.duel", "services.player.military_depth.DUEL_CONTEXTS")),
        DuelContext.HONOUR: Defined(
            "Honour",
            checked_by=(),
            used_by=("engine.phases.vendettas.honour_duels", "services.player.military_depth.DUEL_CONTEXTS", "services.player.military_depth.Ordeal"),
        ),
        DuelContext.TRIAL: Defined(
            "Trial",
            checked_by=("engine.military.duels.Duel.downed", "engine.military.duels.Duel.ended"),
            used_by=("engine.phases.warfare.ordeals", "services.player.military_depth.DUEL_CONTEXTS"),
        ),
        DuelContext.CHAMPION: Defined("Champion", checked_by=(), used_by=("engine.polity.wars.champions", "services.player.military_depth.DUEL_CONTEXTS")),
        DuelContext.GOD: Defined("God", checked_by=(), used_by=("engine.phases.warfare.ordeals", "services.player.military_depth.DUEL_CONTEXTS")),
    },
)

FEUD_PARTY = total(
    FeudParty,
    {
        FeudParty.HOUSE: Defined(
            "House", checked_by=("engine.regime.lineages.align",), used_by=("engine.military.feuds.house_feud", "engine.phases.vendettas.assassinate")
        ),
        FeudParty.COMMUNITY: Defined(
            "Community", checked_by=("engine.phases.vendettas.feuds",), used_by=("db.tables.military.FeudRow", "engine.services.community_relations.party_of")
        ),
        FeudParty.PEOPLE: Defined("People", checked_by=(), used_by=("engine.services.community_relations.party_of",)),
    },
)

OUTCOME_CLASS = total(
    OutcomeClass,
    {
        OutcomeClass.DECISIVE: Defined(
            "Decisive", checked_by=("engine.military.clash.wanted_traits",), used_by=("engine.military.battle.classify", "engine.phases.warfare.GREAT_CLASSES")
        ),
        OutcomeClass.VICTORY: Defined("Victory", checked_by=("engine.military.clash.wanted_traits",), used_by=("engine.military.battle.classify",)),
        OutcomeClass.PYRRHIC: Defined("Pyrrhic", checked_by=(), used_by=("engine.military.battle.classify",)),
        OutcomeClass.STALEMATE: Defined(
            "Stalemate", checked_by=("engine.military.clash.learn_tactic", "engine.phases.warfare._battle_score"), used_by=("engine.military.battle.classify",)
        ),
        OutcomeClass.ROUT: Defined(
            "Rout", checked_by=(), used_by=("engine.military.battle.classify", "engine.military.standards.BROKEN_FIELDS", "engine.phases.warfare.GREAT_CLASSES")
        ),
        OutcomeClass.MASSACRE: Defined(
            "Massacre",
            checked_by=(
                "engine.environment.memory._battle",
                "engine.happenings.emergence.massacres",
                "engine.military.clash.wanted_traits",
                "engine.phases.warfare._honours",
            ),
            used_by=("engine.military.battle.classify", "engine.military.standards.BROKEN_FIELDS", "engine.phases.warfare.GREAT_CLASSES"),
        ),
        OutcomeClass.REFUSED: Defined("Refused", checked_by=(), used_by=("engine.military.battle.resolve",)),
    },
)

SABOTAGE_KIND = total(
    SabotageKind,
    {
        SabotageKind.GRANARY_FIRE: Defined(
            "Granary fire", checked_by=("engine.phases.espionage.sabotage",), used_by=("engine.phases.espionage.sabotage_kind",)
        ),
        SabotageKind.WALL_WEAKENING: Defined(
            "Wall weakening", checked_by=("engine.phases.espionage.sabotage",), used_by=("engine.phases.espionage.sabotage_kind",)
        ),
        SabotageKind.POISON_WELLS: Defined(
            "Poison wells", checked_by=("engine.phases.espionage.sabotage",), used_by=("engine.phases.espionage.sabotage_kind",)
        ),
        SabotageKind.ARSON: Defined("Arson", checked_by=(), used_by=("engine.phases.espionage.sabotage_kind",)),
        SabotageKind.NETWORK_ATTACK: Defined("Network attack", checked_by=("engine.military.sabotage.WIDER_SABOTAGE",), used_by=()),
        SabotageKind.BRIDGE_DESTRUCTION: Defined("Bridge destruction", checked_by=("engine.military.sabotage.WIDER_SABOTAGE",), used_by=()),
        SabotageKind.BLIGHT_RELEASE: Defined("Blight release", checked_by=("engine.military.sabotage.WIDER_SABOTAGE",), used_by=()),
        SabotageKind.SUPPLY_THEFT: Defined("Supply theft", checked_by=("engine.military.sabotage.WIDER_SABOTAGE",), used_by=()),
        SabotageKind.MUTINY_INCITEMENT: Defined("Mutiny incitement", checked_by=("engine.military.sabotage.WIDER_SABOTAGE",), used_by=()),
        SabotageKind.RITE_DISRUPTION: Defined("Rite disruption", checked_by=("engine.military.sabotage.WIDER_SABOTAGE",), used_by=()),
        SabotageKind.SOURCE_POISONING: Defined("Source poisoning", checked_by=("engine.military.sabotage.WIDER_SABOTAGE",), used_by=()),
        SabotageKind.MACHINE_SEIZURE: Defined("Machine seizure", checked_by=("engine.military.sabotage.WIDER_SABOTAGE",), used_by=()),
    },
)

SIEGE_WORK = total(
    SiegeWork,
    {
        SiegeWork.CIRCUMVALLATION: Defined(
            "Circumvallation",
            checked_by=(),
            used_by=("engine.military.siege.season_steps", "engine.military.siege_depth.ACTION_WORKS", "engine.military.siege_depth.encircled"),
        ),
        SiegeWork.TOWERS: Defined("Towers", checked_by=(), used_by=("engine.military.siege_depth.ACTION_WORKS",)),
        SiegeWork.RAMS: Defined("Rams", checked_by=(), used_by=("engine.military.siege_depth.ACTION_WORKS",)),
        SiegeWork.MINES: Defined("Mines", checked_by=(), used_by=("engine.military.siege_depth.ACTION_WORKS", "engine.military.siege_depth.countermine")),
        SiegeWork.COUNTERMINES: Defined(
            "Countermines", checked_by=("engine.military.siege_depth.finished_works",), used_by=("engine.military.siege_depth.countermine",)
        ),
        SiegeWork.LADDERS: Defined("Ladders", checked_by=(), used_by=("engine.military.siege_depth.ACTION_WORKS",)),
    },
)

SPY_OWNER_KIND = total(
    SpyOwnerKind,
    {
        SpyOwnerKind.POLITY: Defined(
            "Polity",
            checked_by=("engine.military.spycraft.OWNER_COVERS", "engine.military.spycraft.side_for"),
            used_by=("engine.military.spycraft.OWNER_KINDS",),
        ),
        SpyOwnerKind.FACTION: Defined(
            "Faction",
            checked_by=("engine.military.spycraft.OWNER_COVERS", "engine.military.spycraft.side_for"),
            used_by=("engine.military.spycraft.OWNER_KINDS",),
        ),
        SpyOwnerKind.CULT: Defined("Cult", checked_by=("engine.military.spycraft.OWNER_COVERS",), used_by=("engine.military.spycraft.OWNER_KINDS",)),
        SpyOwnerKind.COMMUNITY: Defined("Community", checked_by=(), used_by=("db.tables.military.SpyNetworkRow", "engine.military.spycraft.owner_kind")),
        SpyOwnerKind.COMPANY: Defined(
            "Company",
            checked_by=("engine.military.spycraft.OWNER_COVERS", "engine.military.spycraft.side_for"),
            used_by=("engine.military.spycraft.owner_kind",),
        ),
        SpyOwnerKind.MADE_MIND: Defined("Made mind", checked_by=("engine.military.spycraft.OWNER_COVERS",), used_by=("engine.military.spycraft.owner_kind",)),
    },
)

TARGET_CLASS = total(
    TargetClass,
    {
        TargetClass.SOFT: Defined("Soft", checked_by=("engine.military.battle.hard_guard",), used_by=("engine.military.battle.class_of",)),
        TargetClass.HARD: Defined("Hard", checked_by=(), used_by=("engine.military.battle.class_of",)),
    },
)
