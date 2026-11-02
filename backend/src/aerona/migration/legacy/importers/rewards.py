from typing import Any

from aerona.db.tables.agency import CreationRewardRow
from aerona.migration.legacy.context import MigrationContext
from aerona.migration.legacy.idmap import LegacyKind
from aerona.migration.legacy.values import as_int

SHAPE = "reward"
PERCENT_MAX = 100
FULL_FADE = 100


def _number(context: MigrationContext, payload: Any, key: str) -> int:
    return max(0, as_int(context.vocabulary.field(SHAPE, payload, key)) or 0)


async def import_rewards(context: MigrationContext) -> None:
    for row in context.source.iterate("entities", ("id",)):
        payload = row.json("reward")
        if not isinstance(payload, dict):
            continue
        entity_id = context.entity(row.integer("id"))
        son_id = context.son(as_int(context.vocabulary.field(SHAPE, payload, "son_id")))
        if entity_id is None or son_id is None:
            continue
        partner = context.vocabulary.field(SHAPE, payload, "partner")
        partner_id = context.son(as_int(context.vocabulary.field(SHAPE, partner, "partner_id"))) if isinstance(partner, dict) else None
        thread = as_int(context.vocabulary.field(SHAPE, payload, "thread"))
        context.add(
            CreationRewardRow(
                entity_id=entity_id,
                son_id=son_id,
                epoch=_number(context, payload, "epoch"),
                xp=_number(context, payload, "xp"),
                renown=_number(context, payload, "renown"),
                essence=_number(context, payload, "essence"),
                cost=_number(context, payload, "cost"),
                land=bool(context.vocabulary.field(SHAPE, payload, "land")),
                thread_id=context.ids.get(LegacyKind.THREAD, thread) if thread is not None else None,
                thread_reverted=bool(context.vocabulary.field(SHAPE, payload, "thread_reverted")),
                fade_pct=min(FULL_FADE, as_int(context.vocabulary.field(SHAPE, payload, "fade")) or FULL_FADE),
                repeats=_number(context, payload, "repeats"),
                partner_son_id=partner_id,
                partner_xp=_number(context, partner, "partner_xp") if partner_id is not None else 0,
                partner_renown=_number(context, partner, "partner_renown") if partner_id is not None else 0,
                partner_cost=_number(context, partner, "partner_cost") if partner_id is not None else 0,
                taken_back_pct=min(PERCENT_MAX, _number(context, payload, "taken_back")),
            )
        )
        context.report.convert("creation_rewards")
    await context.flush()
