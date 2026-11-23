from collections.abc import Mapping

from aerona.core.grammar import spoken
from aerona.core.total import total
from aerona.domain.enums.quests import QuestAim, QuestObstacle, QuestReward, QuestTargetKind

LEGENDARY_AIMS: Mapping[QuestTargetKind, tuple[QuestAim, ...]] = {
    QuestTargetKind.STAR: (QuestAim.RESTORE,),
    QuestTargetKind.ROUTE: (QuestAim.FREE, QuestAim.BIND),
    QuestTargetKind.KNOWLEDGE: (QuestAim.FIND, QuestAim.LEARN),
    QuestTargetKind.OUTER_BEING: (QuestAim.DESTROY, QuestAim.BIND),
}
LEGACY_LEGENDARY: Mapping[str, tuple[QuestAim, QuestTargetKind]] = {
    "dead_star": (QuestAim.RESTORE, QuestTargetKind.STAR),
    "sealed_gate": (QuestAim.FREE, QuestTargetKind.ROUTE),
    "archive": (QuestAim.FIND, QuestTargetKind.KNOWLEDGE),
    "expel_outer": (QuestAim.DESTROY, QuestTargetKind.OUTER_BEING),
}
LEGACY_HERO: Mapping[str, tuple[QuestAim, QuestTargetKind]] = {
    "hunt": (QuestAim.HUNT, QuestTargetKind.SPECIES),
    "thread": (QuestAim.RESOLVE, QuestTargetKind.INCIDENT_ARC),
    "relic": (QuestAim.FIND, QuestTargetKind.ITEM),
    "knowledge": (QuestAim.LEARN, QuestTargetKind.KNOWLEDGE),
    "vengeance": (QuestAim.AVENGE, QuestTargetKind.PERSON),
}
OBSTACLE_PENALTY: Mapping[QuestObstacle, int] = total(
    QuestObstacle,
    {
        QuestObstacle.DISTANCE: 0,
        QuestObstacle.GUARDIAN: 10,
        QuestObstacle.RIDDLE: 5,
        QuestObstacle.RIVAL: 10,
        QuestObstacle.LAW: 5,
        QuestObstacle.CONCEALMENT: 10,
        QuestObstacle.DANGER_OF_PLACE: 15,
        QuestObstacle.COST: 5,
    },
)
OBSTACLE_EPOCHS: Mapping[QuestObstacle, int] = total(
    QuestObstacle,
    {
        QuestObstacle.DISTANCE: 2,
        QuestObstacle.GUARDIAN: 1,
        QuestObstacle.RIDDLE: 1,
        QuestObstacle.RIVAL: 1,
        QuestObstacle.LAW: 1,
        QuestObstacle.CONCEALMENT: 2,
        QuestObstacle.DANGER_OF_PLACE: 1,
        QuestObstacle.COST: 0,
    },
)
AIM_DEFAULTS: Mapping[QuestAim, tuple[QuestObstacle, QuestReward]] = total(
    QuestAim,
    {
        QuestAim.FIND: (QuestObstacle.CONCEALMENT, QuestReward.ITEM),
        QuestAim.RESTORE: (QuestObstacle.COST, QuestReward.STANDING),
        QuestAim.DESTROY: (QuestObstacle.GUARDIAN, QuestReward.RENOWN),
        QuestAim.FREE: (QuestObstacle.GUARDIAN, QuestReward.STANDING),
        QuestAim.BIND: (QuestObstacle.RIDDLE, QuestReward.POWER),
        QuestAim.REACH: (QuestObstacle.DISTANCE, QuestReward.RENOWN),
        QuestAim.LEARN: (QuestObstacle.RIDDLE, QuestReward.KNOWLEDGE),
        QuestAim.RETURN: (QuestObstacle.DISTANCE, QuestReward.STANDING),
        QuestAim.PROTECT: (QuestObstacle.RIVAL, QuestReward.STANDING),
        QuestAim.AVENGE: (QuestObstacle.RIVAL, QuestReward.RENOWN),
        QuestAim.HUNT: (QuestObstacle.DANGER_OF_PLACE, QuestReward.RENOWN),
        QuestAim.DELIVER: (QuestObstacle.DISTANCE, QuestReward.OFFICE),
        QuestAim.RECONCILE: (QuestObstacle.LAW, QuestReward.PEACE),
        QuestAim.PROVE: (QuestObstacle.RIVAL, QuestReward.RENOWN),
        QuestAim.RESOLVE: (QuestObstacle.CONCEALMENT, QuestReward.KNOWLEDGE),
    },
)
REWARD_WORDS: Mapping[QuestReward, str] = total(
    QuestReward,
    {
        QuestReward.RENOWN: "renown",
        QuestReward.POWER: "power",
        QuestReward.KNOWLEDGE: "knowledge",
        QuestReward.ITEM: "a prize",
        QuestReward.STANDING: "standing",
        QuestReward.OFFICE: "an office",
        QuestReward.CURE: "healing",
        QuestReward.PEACE: "peace",
    },
)


def quest_name(aim: QuestAim, target: QuestTargetKind) -> str:
    return f"{spoken(aim).capitalize()} the {spoken(target)}"
