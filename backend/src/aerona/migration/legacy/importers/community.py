from typing import Any

from aerona.constants.schema import KEY_MAX_LENGTH
from aerona.db.tables.society import CommunityRelationEventRow, CommunityRelationRow
from aerona.domain.enums.entity import SOCIETY_TYPES
from aerona.domain.enums.limits import PERCENT_MAX, PERCENT_MIN, RELATION_MAX, RELATION_MIN
from aerona.domain.enums.society import Commodity, SocialClass
from aerona.engine.phases.society_economy import Society, default_society, save_society
from aerona.migration.legacy.context import MigrationContext
from aerona.migration.legacy.values import as_dict, as_float, as_int, as_list, as_text, required_bounded

SHARE_CEILING = float(PERCENT_MAX)


async def import_community_relations(context: MigrationContext) -> None:
    seen: set[tuple[int, int]] = set()
    for row in context.source.iterate("community_relations"):
        first, second = context.entity(row.integer("entity_a")), context.entity(row.integer("entity_b"))
        reference = f"community_relation:{row.integer('entity_a')}-{row.integer('entity_b')}"
        if first is None or second is None or first == second:
            context.report.place_failed("community relation", reference, "a community is missing")
            continue
        low, high = min(first, second), max(first, second)
        if (low, high) in seen:
            continue
        seen.add((low, high))
        if row.flag("closed"):
            context.report.convert("community_relations_closed_by_ended_party")
        context.add(
            CommunityRelationRow(
                entity_a_id=low,
                entity_b_id=high,
                value=required_bounded(context.report, reference, "relation", row.integer("value"), (RELATION_MIN, RELATION_MAX), fallback=0),
                blood_feud_since_epoch=row.integer("blood_feud_since"),
            )
        )
        for item in as_list(row.json("history")):
            event = as_text(context.vocabulary.field("relation_history", item, "event"))
            epoch = as_int(context.vocabulary.field("relation_history", item, "epoch"))
            delta = as_int(context.vocabulary.field("relation_history", item, "delta"))
            if event is None or epoch is None or delta is None:
                continue
            context.add(CommunityRelationEventRow(entity_a_id=low, entity_b_id=high, epoch=epoch, event=event[:KEY_MAX_LENGTH], delta=delta))
            context.report.convert("community_relation_events")
        await context.flush_if_full()
    await context.flush()


def _merged(context: MigrationContext, payload: dict[str, Any]) -> Society:
    vocabulary = context.vocabulary
    society = default_society(context.rules)
    shares = as_dict(vocabulary.field("society", payload, "shares"))
    satisfaction = as_dict(vocabulary.field("society", payload, "satisfaction"))
    stocks = as_dict(vocabulary.field("society", payload, "stocks"))
    prices = as_dict(vocabulary.field("society", payload, "prices"))
    for social_class in SocialClass:
        legacy = vocabulary.encode("social_class", social_class.value)
        share = as_float(shares.get(legacy))
        if share is not None:
            society.shares[social_class] = max(0.0, min(SHARE_CEILING, share))
        content = as_int(satisfaction.get(legacy))
        if content is not None:
            society.satisfaction[social_class] = max(PERCENT_MIN, min(PERCENT_MAX, content))
    for commodity in Commodity:
        legacy = vocabulary.encode("commodity", commodity.value)
        stock = as_int(stocks.get(legacy))
        if stock is not None:
            society.stocks[commodity] = max(0, stock)
        price = as_int(prices.get(legacy))
        if price is not None:
            society.prices[commodity] = max(0, price)
    return society


async def import_societies(context: MigrationContext) -> None:
    await context.flush()
    reverse = context.ids.reverse_entities()
    for entity in sorted(context.rows.values(), key=lambda item: item.id):
        legacy_id = reverse.get(entity.id)
        if legacy_id is None:
            continue
        payload = context.society_payloads.get(legacy_id)
        if payload is None:
            continue
        if entity.entity_type not in SOCIETY_TYPES:
            context.report.place_failed("society", f"entity:{legacy_id}", f"a {entity.entity_type.value} cannot hold a society")
            continue
        await save_society(context.session, entity.id, _merged(context, payload))
        context.report.convert("societies")
