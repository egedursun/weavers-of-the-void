from aerona.catalog.kinds.definition import Defined
from aerona.core.total import total
from aerona.domain.enums.military import FeudParty, OutcomeClass, SabotageKind, SpyOwnerKind, TargetClass

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
        SabotageKind.RECORD_TAMPERING: Defined("Record tampering", checked_by=("engine.military.sabotage.WIDER_SABOTAGE",), used_by=()),
        SabotageKind.ROUTE_BLOCKING: Defined("Route blocking", checked_by=("engine.military.sabotage.WIDER_SABOTAGE",), used_by=()),
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
