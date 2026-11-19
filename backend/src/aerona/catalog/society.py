from dataclasses import dataclass

from aerona.domain.enums.society import CommunityRelationLabel, SocialClass
from aerona.domain.enums.son import SonRelationLabel
from aerona.rules.registry import Rules


@dataclass(frozen=True)
class SocialClassSpec:
    social_class: SocialClass
    singular: str
    plural: str


SOCIAL_CLASSES: dict[SocialClass, SocialClassSpec] = {
    spec.social_class: spec
    for spec in (
        SocialClassSpec(SocialClass.FARMER, "Farmer", "Farmers"),
        SocialClassSpec(SocialClass.ARTISAN, "Artisan", "Artisans"),
        SocialClassSpec(SocialClass.MERCHANT, "Merchant", "Merchants"),
        SocialClassSpec(SocialClass.PRIEST, "Priest", "Priests"),
        SocialClassSpec(SocialClass.WARRIOR, "Warrior", "Warriors"),
        SocialClassSpec(SocialClass.SCRIBE, "Clerk", "Clerks"),
        SocialClassSpec(SocialClass.NOBLE, "Noble", "Nobles"),
        SocialClassSpec(SocialClass.SERF_OR_SLAVE, "Bonded", "Bonded"),
        SocialClassSpec(SocialClass.OUTCAST, "Outcast", "Outcasts"),
        SocialClassSpec(SocialClass.MONASTIC, "Monastic", "Monastics"),
        SocialClassSpec(SocialClass.WORKER, "Worker", "Workers"),
        SocialClassSpec(SocialClass.PROFESSIONAL, "Professional", "Professionals"),
        SocialClassSpec(SocialClass.OFFICIAL, "Official", "Officials"),
        SocialClassSpec(SocialClass.CITIZEN, "Citizen", "Citizens"),
        SocialClassSpec(SocialClass.UNEMPLOYED, "Unemployed", "Unemployed"),
    )
}


def community_relation_label(rules: Rules, value: int) -> CommunityRelationLabel:
    core = rules.core_rules
    hostile = (
        (-core.relation_blood_enemy, CommunityRelationLabel.BLOOD_ENEMY),
        (-core.relation_enemy, CommunityRelationLabel.ENEMY),
        (-core.relation_cold, CommunityRelationLabel.COLD),
    )
    friendly = (
        (core.relation_friend, CommunityRelationLabel.NEUTRAL),
        (core.relation_close_friend, CommunityRelationLabel.FRIEND),
        (core.relation_sibling, CommunityRelationLabel.CLOSE_FRIEND),
    )
    for ceiling, label in hostile:
        if value <= ceiling:
            return label
    return next((label for ceiling, label in friendly if value < ceiling), CommunityRelationLabel.SIBLING)


def son_relation_label(rules: Rules, value: int) -> SonRelationLabel:
    thresholds = rules.son_relations
    if value >= thresholds.devotion:
        return SonRelationLabel.DEVOTION
    if value >= thresholds.friendship:
        return SonRelationLabel.FRIENDSHIP
    if value > -thresholds.hostility:
        return SonRelationLabel.DISTANCE
    if value > -thresholds.hatred:
        return SonRelationLabel.HOSTILITY
    return SonRelationLabel.HATRED
