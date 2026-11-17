from aerona.core.random import SeededRandom
from aerona.db.tables.entities import EntityRow
from aerona.domain.enums.entity import EntityType
from aerona.domain.enums.society import SocialClass
from aerona.rules.registry import Rules

FALLBACK_ROLE = "heir"
BASE_ROLES: dict[EntityType, tuple[str, ...]] = {
    EntityType.SETTLEMENT: ("sovereign", "ruler"),
    EntityType.PEOPLE: ("chief", "head of the people"),
    EntityType.FACTION: ("leader", "captain"),
    EntityType.CULT: ("head of the faith",),
    EntityType.REGION: ("governor", "warden of the border"),
    EntityType.PLACE: ("warden",),
    EntityType.LAW: ("keeper of the law",),
    EntityType.ARMY: ("commander",),
}
CLASS_ROLES: dict[SocialClass, str] = {
    SocialClass.PRIEST: "priest-ruler",
    SocialClass.WARRIOR: "warrior-ruler",
    SocialClass.MERCHANT: "merchant-ruler",
    SocialClass.SCRIBE: "scholar-ruler",
    SocialClass.ARTISAN: "artisan-ruler",
    SocialClass.FARMER: "farmer-ruler",
    SocialClass.NOBLE: "high ruler",
    SocialClass.SERF_OR_SLAVE: "freed ruler",
    SocialClass.OUTCAST: "outcast ruler",
    SocialClass.MONASTIC: "ascetic-ruler",
    SocialClass.WORKER: "workers' leader",
    SocialClass.PROFESSIONAL: "expert ruler",
    SocialClass.OFFICIAL: "chief administrator",
    SocialClass.CITIZEN: "first citizen",
    SocialClass.UNEMPLOYED: "voice of the jobless",
}
CLASSED_TYPES = frozenset({EntityType.SETTLEMENT, EntityType.PEOPLE})


def dominant_class(rules: Rules, ruled: EntityRow, shares: dict[SocialClass, float]) -> SocialClass | None:
    if ruled.entity_type not in CLASSED_TYPES or not shares:
        return None
    social_class, share = max(shares.items(), key=lambda item: (item[1], item[0].value))
    return social_class if share >= rules.casualties.ruler_class_min_share else None


def ruler_role(rules: Rules, ruled: EntityRow | None, shares: dict[SocialClass, float], rng: SeededRandom | None = None) -> str:
    if ruled is None:
        return FALLBACK_ROLE
    base = BASE_ROLES.get(ruled.entity_type)
    if base is None:
        return FALLBACK_ROLE
    dominant = dominant_class(rules, ruled, shares)
    if dominant is not None and (rng is None or rng.chance(rules.casualties.ruler_class_chance)):
        return CLASS_ROLES[dominant]
    return rng.pick(base) if rng is not None else base[0]
