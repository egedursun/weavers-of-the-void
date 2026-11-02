from aerona.db.tables.entities import EntityRow
from aerona.domain.enums.entity import EntityStatus, EntityType
from aerona.engine.primitives.stats import headcount, headcount_bounds, headcount_key, headcount_value, put_stat, set_stats, stat
from aerona.rules.registry import Rules

LEVY_TYPES = frozenset({EntityType.PEOPLE, EntityType.SETTLEMENT, EntityType.CULT})


def levies_from(community: EntityRow) -> bool:
    return community.entity_type in LEVY_TYPES and headcount_value(community) is not None


def levy(rules: Rules, community: EntityRow, wanted: int) -> int:
    if not levies_from(community):
        return wanted
    floor, _ = headcount_bounds(rules, community)
    current = headcount(community)
    taken = max(0, min(wanted, current - floor))
    put_stat(rules, community, headcount_key(community), current - taken)
    return taken


def stand_down(rules: Rules, army: EntityRow, owner: EntityRow | None) -> int:
    soldiers = stat(army, "size") or 0
    set_stats(army, size=0)
    return demobilise(rules, owner, soldiers)


def demobilise(rules: Rules, owner: EntityRow | None, soldiers: int) -> int:
    if owner is None or owner.status is not EntityStatus.CANON or soldiers <= 0 or not levies_from(owner):
        return 0
    before = headcount(owner)
    after = put_stat(rules, owner, headcount_key(owner), before + soldiers)
    return (after or before) - before
