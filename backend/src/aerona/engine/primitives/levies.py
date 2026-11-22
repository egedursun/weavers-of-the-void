from aerona.db.tables.entities import EntityRow
from aerona.domain.enums.entity import EntityStatus, EntityType
from aerona.engine.interconnect.flows import FlowCategory, flowing
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
    with flowing(FlowCategory.LEVY):
        put_stat(rules, community, headcount_key(community), current - taken)
    return taken


def levy_category(community: EntityRow) -> FlowCategory:
    return FlowCategory.LEVY if levies_from(community) else FlowCategory.CREATION


def stand_down(rules: Rules, army: EntityRow, owner: EntityRow | None) -> int:
    soldiers = stat(army, "size") or 0
    returned = demobilise(rules, owner, soldiers)
    discharge(army, soldiers, returned)
    return returned


def discharge(army: EntityRow, soldiers: int, returned: int) -> None:
    with flowing(FlowCategory.LEVY):
        set_stats(army, size=max(0, soldiers - returned))
    with flowing(FlowCategory.DEATH):
        set_stats(army, size=0)


def add_heads(rules: Rules, community: EntityRow, count: int, category: FlowCategory) -> int:
    before = headcount(community)
    with flowing(category):
        after = put_stat(rules, community, headcount_key(community), before + count)
    return min(count, max(0, (after or before) - before))


def demobilise(rules: Rules, owner: EntityRow | None, soldiers: int) -> int:
    if owner is None or owner.status is not EntityStatus.CANON or soldiers <= 0 or not levies_from(owner):
        return 0
    return add_heads(rules, owner, soldiers, FlowCategory.LEVY)
