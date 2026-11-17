from aerona.catalog.kinds.definition import Defined
from aerona.core.total import total
from aerona.domain.enums.quests import QuestTargetKind

QUEST_TARGET_KIND = total(
    QuestTargetKind,
    {
        QuestTargetKind.STAR: Defined(
            "A star",
            checked_by=(
                "catalog.quests.LEGENDARY_AIMS",
                "engine.cosmos.quests.TARGET_FINDERS",
                "engine.cosmos.quests._completed",
                "engine.cosmos.quests._invalid_reason",
            ),
            used_by=("catalog.quests.LEGACY_LEGENDARY", "db.tables.lore.LegendaryQuestRow", "services.player.cosmic.LegendaryQuest"),
        ),
        QuestTargetKind.ROUTE: Defined(
            "A route",
            checked_by=(
                "catalog.quests.LEGENDARY_AIMS",
                "engine.cosmos.quests.TARGET_FINDERS",
                "engine.cosmos.quests._bound",
                "engine.cosmos.quests._completed",
                "engine.cosmos.quests._invalid_reason",
            ),
            used_by=("catalog.quests.LEGACY_LEGENDARY",),
        ),
        QuestTargetKind.KNOWLEDGE: Defined(
            "Knowledge",
            checked_by=(
                "catalog.quests.LEGENDARY_AIMS",
                "engine.cosmos.quests.TARGET_FINDERS",
                "engine.cosmos.quests._completed",
                "engine.cosmos.quests._invalid_reason",
            ),
            used_by=("catalog.quests.LEGACY_HERO", "catalog.quests.LEGACY_LEGENDARY", "engine.phases.society_support.quests.knowledge_options"),
        ),
        QuestTargetKind.OUTER_BEING: Defined(
            "A being from outside",
            checked_by=("catalog.quests.LEGENDARY_AIMS", "engine.cosmos.quests.TARGET_FINDERS"),
            used_by=("catalog.quests.LEGACY_LEGENDARY",),
        ),
        QuestTargetKind.SPECIES: Defined(
            "A kind of creature", checked_by=(), used_by=("catalog.quests.LEGACY_HERO", "engine.phases.society_support.quests.hunt_options")
        ),
        QuestTargetKind.ITEM: Defined(
            "An item",
            checked_by=(),
            used_by=("catalog.quests.LEGACY_HERO", "engine.phases.society_support.quests.relic_options", "engine.polity.houses.relic_quest"),
        ),
        QuestTargetKind.PERSON: Defined(
            "A person",
            checked_by=(),
            used_by=(
                "catalog.quests.LEGACY_HERO",
                "db.tables.warfare.HeroQuestRow",
                "engine.phases.mind.vengeance",
                "engine.phases.society_support.quests.vengeance_options",
            ),
        ),
        QuestTargetKind.PLACE: Defined(
            "A place", checked_by=("engine.phases.society_support.quest_claims.reach",), used_by=("engine.phases.society_support.quests.place_options",)
        ),
        QuestTargetKind.INCIDENT_ARC: Defined(
            "An incident arc", checked_by=(), used_by=("catalog.quests.LEGACY_HERO", "engine.phases.society_support.quests.thread_options")
        ),
    },
)
