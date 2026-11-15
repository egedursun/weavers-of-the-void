from collections import defaultdict
from typing import Any

from aerona.catalog.chronicle import NOTIFICATION_SEVERITY_MAX, NOTIFICATION_SEVERITY_MIN
from aerona.catalog.scenarios import SCENARIOS
from aerona.constants.schema import MAP_NOTE_COLOR_MAX_LENGTH, MAP_NOTE_MAX_LENGTH, NOTIFICATION_BODY_MAX_LENGTH, NOTIFICATION_TITLE_MAX_LENGTH
from aerona.db.tables.epochs import EpochStatsRow
from aerona.db.tables.meta import AchievementRow, MapNoteRow, MapSnapshotRow, NotificationRow, ScenarioRow, ScoreRow
from aerona.domain.enums.chronicle import NotificationCategory
from aerona.domain.enums.entity import EntityType
from aerona.domain.enums.meta import AchievementKey, ScenarioKey, ScenarioStatus
from aerona.domain.models.records import EpochStatsData, MapSnapshotData, RegionControl, SonEpochStats
from aerona.engine.gods.goals import preset_points
from aerona.migration.legacy import blobs
from aerona.migration.legacy.context import MigrationContext
from aerona.migration.legacy.idmap import LegacyKind
from aerona.migration.legacy.importers.cosmos import DEFAULTED, UNKNOWN_VALUE
from aerona.migration.legacy.timestamps import legacy_time
from aerona.migration.legacy.values import as_dict, as_float, as_int, as_list, as_text, truncated


async def import_scores(context: MigrationContext) -> None:
    for row in context.source.iterate("scores", ("epoch",)):
        epoch = row.integer("epoch")
        if epoch is None:
            continue
        breakdown, unknown = blobs.score_breakdown(context.vocabulary, row.json("breakdown"))
        for part in unknown:
            context.report.warn(UNKNOWN_VALUE, f"score:{epoch}", f"score part {part!r} dropped")
        context.add(ScoreRow(epoch=epoch, total=row.integer("total") or breakdown.total, breakdown=breakdown))
    for row in context.source.iterate("achievements"):
        achievement_key = context.vocabulary.decode_as("achievement_key", row.text("key"), AchievementKey)
        if achievement_key is None:
            context.report.place_failed("achievement", f"achievement:{row.text('key')}", "unknown achievement")
            continue
        achievement = AchievementRow(key=achievement_key, epoch=row.integer("epoch") or context.epoch)
        stamp = legacy_time(row.raw("achieved_at"))
        if stamp is not None:
            achievement.created_at = stamp
        context.add(achievement)
    running: set[ScenarioKey] = set()
    for row in context.source.iterate("scenarios", ("id",)):
        reference = f"scenario:{row.integer('id')}"
        scenario_key = context.vocabulary.decode_as("scenario_key", row.text("key"), ScenarioKey)
        status = context.vocabulary.decode_as("scenario_status", row.text("status"), ScenarioStatus) or ScenarioStatus.RUNNING
        if scenario_key is None:
            context.report.place_failed("scenario", reference, f"unknown scenario {row.text('key')!r}")
            continue
        if status is ScenarioStatus.RUNNING:
            if scenario_key in running:
                context.report.place_failed("scenario", reference, "a second running copy of the scenario")
                continue
            running.add(scenario_key)
            context.report.warn("scenario baseline", reference, "the running scenario restarts its progress baseline in the new engine")
        end = row.integer("end_epoch")
        if status is not ScenarioStatus.RUNNING and end is None:
            end = context.epoch
            context.report.warn(DEFAULTED, reference, f"end epoch set to {end}")
        target = SCENARIOS[scenario_key].default_target(context.rules)
        points = preset_points(context.rules, scenario_key, target, None)
        context.add(
            ScenarioRow(
                key=scenario_key,
                status=status,
                start_epoch=max(0, row.integer("start_epoch") or 0),
                end_epoch=end,
                target=target,
                points=points,
                awarded_points=points if status is ScenarioStatus.COMPLETED else 0,
                result=row.text("result"),
            )
        )
    await context.flush()


async def import_notifications(context: MigrationContext) -> None:
    for row in context.source.iterate("notifications", ("id",)):
        reference = f"notification:{row.integer('id')}"
        category = context.vocabulary.decode_as("notification_category", row.text("category"), NotificationCategory)
        title = truncated(context.report, reference, "title", row.text("title"), NOTIFICATION_TITLE_MAX_LENGTH)
        if category is None or title is None:
            context.report.place_failed("notification", reference, f"category {row.text('category')!r} or title missing")
            continue
        severity = max(NOTIFICATION_SEVERITY_MIN, min(NOTIFICATION_SEVERITY_MAX, row.integer("severity") or NOTIFICATION_SEVERITY_MIN))
        notification = NotificationRow(
            epoch=row.integer("epoch"),
            category=category,
            severity=severity,
            title=title,
            body=truncated(context.report, reference, "body", row.text("body"), NOTIFICATION_BODY_MAX_LENGTH),
            target_node_id=context.node(row.text("target_kind"), row.integer("target_id")),
            chronicle_id=context.ids.get(LegacyKind.CHRONICLE, row.integer("chronicle_id")),
            is_read=row.flag("read"),
        )
        stamp = legacy_time(row.raw("created_at"))
        if stamp is not None:
            notification.created_at = stamp
        context.add(notification)
        await context.flush_if_full()
    await context.flush()


async def import_map_notes(context: MigrationContext) -> None:
    for row in context.source.iterate("map_notes", ("id",)):
        reference = f"map_note:{row.integer('id')}"
        text = truncated(context.report, reference, "text", row.text("text"), MAP_NOTE_MAX_LENGTH)
        if text is None:
            continue
        note = MapNoteRow(
            world_id=context.world_or_primary(row.integer("world_id")),
            x=row.number("x") or 0.0,
            y=row.number("y") or 0.0,
            text=text,
            color=truncated(context.report, reference, "color", row.text("color"), MAP_NOTE_COLOR_MAX_LENGTH),
        )
        context.add(note)
    await context.flush()


def _region_control(context: MigrationContext, payload: Any) -> RegionControl | None:
    vocabulary = context.vocabulary
    ruler = context.entity(as_int(vocabulary.field("map_snapshot", payload, "ruler_id")))
    facts = context.facts(ruler)
    if ruler is None or facts is None:
        return None
    share = as_float(vocabulary.field("map_snapshot", payload, "share")) or 0.0
    return RegionControl(
        ruler_id=ruler,
        ruler_name=as_text(vocabulary.field("map_snapshot", payload, "ruler_name")) or "",
        ruler_type=facts.entity_type,
        share=max(0.0, share),
        contested=bool(vocabulary.field("map_snapshot", payload, "contested")),
    )


async def import_map_snapshots(context: MigrationContext) -> None:
    vocabulary = context.vocabulary
    for row in context.source.iterate("map_snapshots", ("epoch",)):
        epoch = row.integer("epoch")
        data = as_dict(row.json("data"))
        if epoch is None or not data:
            continue
        living: dict[int, list[int]] = defaultdict(list)
        population: dict[int, dict[int, int]] = defaultdict(dict)
        political: dict[int, dict[int, RegionControl]] = defaultdict(dict)
        wars: dict[int, list[int]] = defaultdict(list)
        for value in as_list(vocabulary.field("map_snapshot", data, "living")):
            facts = context.facts(context.entity(as_int(value)))
            new_id = context.entity(as_int(value))
            if facts is not None and new_id is not None:
                living[facts.world_id].append(new_id)
        for key, value in as_dict(vocabulary.field("map_snapshot", data, "population")).items():
            new_id = context.entity(as_int(key))
            facts = context.facts(new_id)
            amount = as_int(value)
            if new_id is not None and facts is not None and amount is not None:
                population[facts.world_id][new_id] = amount
        for key, value in as_dict(vocabulary.field("map_snapshot", data, "political")).items():
            region = context.entity(as_int(key))
            facts = context.facts(region)
            control = _region_control(context, value)
            if region is not None and facts is not None and facts.entity_type is EntityType.REGION and control is not None:
                political[facts.world_id][region] = control
        for value in as_list(vocabulary.field("map_snapshot", data, "wars")):
            new_id = context.entity(as_int(value))
            facts = context.facts(new_id)
            if new_id is not None and facts is not None:
                wars[facts.world_id].append(new_id)
        for world_id in sorted(set(living) | set(population) | set(political) | set(wars)):
            snapshot = MapSnapshotData(
                living_ids=tuple(living[world_id]),
                population=population[world_id],
                political=political[world_id],
                ongoing_war_ids=tuple(wars[world_id]),
            )
            context.add(MapSnapshotRow(epoch=epoch, world_id=world_id, data=snapshot))
            context.report.convert("map_snapshots_split_by_world")
    await context.flush()


async def import_epoch_stats(context: MigrationContext) -> None:
    vocabulary = context.vocabulary
    simple = (
        "population",
        "followers",
        "entities",
        "words",
        "knowledge",
        "languages",
        "wars",
        "trade_routes",
        "alliances",
        "structures",
        "items",
        "dead",
        "godless",
        "doom",
    )
    for row in context.source.iterate("epoch_stats", ("epoch",)):
        epoch = row.integer("epoch")
        data = as_dict(row.json("data"))
        if epoch is None or not data:
            continue
        values = {field: max(0, as_int(vocabulary.field("epoch_stats", data, field)) or 0) for field in simple}
        sons: dict[int, SonEpochStats] = {}
        for key, value in as_dict(vocabulary.field("epoch_stats", data, "sons")).items():
            son = context.son(as_int(key))
            if son is None:
                continue
            sons[son] = SonEpochStats(
                faith=as_int(vocabulary.field("epoch_stats", value, "son_faith")) or 0,
                fame=as_int(vocabulary.field("epoch_stats", value, "son_fame")) or 0,
                existence=as_int(vocabulary.field("epoch_stats", value, "son_existence")) or 0,
                level=as_int(vocabulary.field("epoch_stats", value, "son_level")) or 1,
            )
        context.add(EpochStatsRow(epoch=epoch, data=EpochStatsData(**values, sons=sons)))
        context.report.convert("epoch_stats")
    context.report.not_migrated["epoch_stat_item_breakdowns"] = context.source.count("epoch_stats")
    await context.flush()
