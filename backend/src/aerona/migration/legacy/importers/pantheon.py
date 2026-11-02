from typing import Any

from aerona.db.tables.foreign_gods import ForeignGodPowerRow, ForeignGodRow
from aerona.db.tables.sons import SonPowerRow, SonRelationRow, SonRow
from aerona.domain.enums.domain import Domain
from aerona.domain.enums.entity import EntityType
from aerona.domain.enums.foreign_god import ForeignGodPowerEffect, ForeignGodStatus
from aerona.domain.enums.limits import MAX_STARS, MIN_STARS, PERCENT_MAX, PERCENT_MIN, POWER_SLOTS, RELATION_MAX, RELATION_MIN
from aerona.domain.enums.rarity import Rarity
from aerona.domain.enums.son import Passion, PowerEffect, ReputationLabel, SonDeathCause, SonStatus, Stat
from aerona.domain.models.profiles import Personality
from aerona.domain.models.stats import STAT_CEILING, STAT_FLOOR
from aerona.migration.legacy import blobs
from aerona.migration.legacy.context import MigrationContext
from aerona.migration.legacy.idmap import LegacyKind
from aerona.migration.legacy.importers.cosmos import DEFAULTED, UNKNOWN_VALUE, named
from aerona.migration.legacy.source import LegacyRow
from aerona.migration.legacy.values import as_dict, as_int, as_list, as_text, bounded, required_bounded

STAT_DEFAULT = 50
PASSION_DEFAULT = 50
DEATH_CAUSE_UNKNOWN = "death cause unknown"


def stat_block(context: MigrationContext, reference: str, payload: Any) -> dict[Stat, int]:
    data = as_dict(payload)
    values: dict[Stat, int] = {}
    for stat in Stat:
        legacy = context.vocabulary.encode("son_stat", stat.value)
        raw = as_int(data.get(legacy))
        if raw is None:
            context.report.warn(DEFAULTED, reference, f"stat {stat.value} set to {STAT_DEFAULT}")
            raw = STAT_DEFAULT
        values[stat] = required_bounded(context.report, reference, stat.value, raw, (STAT_FLOOR, STAT_CEILING), fallback=STAT_DEFAULT)
    return values


def passion_block(context: MigrationContext, reference: str, payload: Any) -> dict[Passion, int]:
    data = as_dict(payload)
    values: dict[Passion, int] = {}
    for passion in Passion:
        raw = as_int(data.get(context.vocabulary.encode("passion", passion.value)))
        values[passion] = required_bounded(context.report, reference, passion.value, raw, (PERCENT_MIN, PERCENT_MAX), fallback=PASSION_DEFAULT)
    return values


def domains(context: MigrationContext, reference: str, first: str | None, second: str | None) -> tuple[Domain | None, Domain | None]:
    primary = context.vocabulary.decode_as("domain", first, Domain)
    secondary = context.vocabulary.decode_as("domain", second, Domain)
    if first is not None and primary is None:
        context.report.warn(UNKNOWN_VALUE, reference, f"domain {first!r} is not one of the forty domains")
    if second is not None and secondary is None:
        context.report.warn(UNKNOWN_VALUE, reference, f"domain {second!r} is not one of the forty domains")
    return primary, secondary


def _reputation(context: MigrationContext, son: SonRow, row: LegacyRow) -> None:
    vocabulary = context.vocabulary
    data = as_dict(row.json("reputation"))
    if data:
        son.reputation_love = as_int(vocabulary.field("reputation", data, "love"))
        son.reputation_fear = as_int(vocabulary.field("reputation", data, "fear"))
        son.reputation_forgotten = as_int(vocabulary.field("reputation", data, "forgotten"))
        son.reputation_unanswered = as_int(vocabulary.field("reputation", data, "unanswered"))
        son.reputation_last_contact_epoch = as_int(vocabulary.field("reputation", data, "last_contact"))
        son.reputation_epoch = as_int(vocabulary.field("reputation", data, "epoch"))
        label = vocabulary.field("reputation", data, "label")
        son.reputation_label = vocabulary.decode_as("reputation_label", label, ReputationLabel)
        if label is not None and son.reputation_label is None:
            context.report.warn(UNKNOWN_VALUE, f"son:{row.integer('id')}", f"reputation label {label!r} dropped")
    manual = as_dict(row.json("reputation_manual"))
    son.manual_love = as_int(vocabulary.field("reputation", manual, "love")) or 0
    son.manual_fear = as_int(vocabulary.field("reputation", manual, "fear")) or 0
    son.manual_forgotten = as_int(vocabulary.field("reputation", manual, "forgotten")) or 0
    trace = as_dict(row.json("reputation_trace"))
    son.trace_love = as_int(vocabulary.field("reputation", trace, "love")) or 0
    son.trace_fear = as_int(vocabulary.field("reputation", trace, "fear")) or 0


def _son(context: MigrationContext, row: LegacyRow) -> SonRow | None:
    legacy_id = row.integer("id") or 0
    reference = f"son:{legacy_id}"
    rarity = context.vocabulary.decode_as("rarity", row.text("rarity"), Rarity)
    primary, secondary = domains(context, reference, row.text("domain_primary"), row.text("domain_secondary"))
    if rarity is None or primary is None or secondary is None:
        context.report.place_failed("son", reference, "rarity or domains could not be read")
        return None
    if primary is secondary:
        context.report.place_failed("son", reference, "both domains are the same")
        return None
    status = context.vocabulary.decode_as("son_status", row.text("status"), SonStatus) or SonStatus.ACTIVE
    death_epoch = row.integer("death_epoch")
    death_cause = None
    if status is SonStatus.DEAD:
        death_cause = SonDeathCause.OTHER
        context.report.warn(DEATH_CAUSE_UNKNOWN, reference, "the legacy data does not record how the son died")
        if death_epoch is None:
            death_epoch = context.epoch
            context.report.warn(DEFAULTED, reference, f"death epoch set to {death_epoch}")
    stats = stat_block(context, reference, row.json("stats"))
    passions = passion_block(context, reference, row.json("passions"))
    profile, raw_mode = blobs.existence(context.vocabulary, row.json("existence_profile"))
    if raw_mode is not None:
        context.report.warn(UNKNOWN_VALUE, reference, f"existence mode {raw_mode!r} dropped")
    son = SonRow(
        name=named(context, "son", legacy_id, row.text("name")),
        title=row.required_text("title"),
        rarity=rarity,
        stars=required_bounded(context.report, reference, "stars", row.integer("stars"), (MIN_STARS, MAX_STARS), fallback=MIN_STARS),
        domain_primary=primary,
        domain_secondary=secondary,
        **{stat.value: value for stat, value in stats.items()},
        **{passion.value: value for passion, value in passions.items()},
        personality=blobs.personality(context.vocabulary, row.json("personality")) or Personality(),
        existence_profile=profile,
        existence=required_bounded(context.report, reference, "existence", row.integer("existence"), (PERCENT_MIN, PERCENT_MAX), fallback=PERCENT_MIN),
        fading_epochs=max(0, row.integer("fading") or 0),
        hp=max(0, row.integer("hp") or 0),
        essence=max(0, row.integer("essence") or 0),
        faith=max(0, row.integer("faith") or 0),
        fame=max(0, row.integer("fame") or 0),
        xp=max(0, row.integer("xp") or 0),
        level=max(1, row.integer("level") or 1),
        status=status,
        sleep_epochs_left=max(0, row.integer("sleep_left") or 0),
        chained=row.flag("chained"),
        rebel=row.flag("rebel"),
        standing_order=row.text("standing_order"),
        order_absolute=row.flag("order_absolute"),
        plan=row.text("plan"),
        plan_epoch=row.integer("plan_epoch"),
        epic=blobs.epic(context.vocabulary, row.json("epic"), context.epoch),
        current_world_id=context.world(row.integer("current_world")) or context.primary_world_id,
        manually_assigned_epoch=row.integer("assigned_epoch"),
        birth_epoch=max(1, row.integer("birth_epoch") or 1),
        death_epoch=death_epoch,
        death_cause=death_cause,
        last_acted_epoch=max(0, row.integer("last_acted_epoch") or 0),
        image_prompt=row.text("image_prompt"),
    )
    _reputation(context, son, row)
    return son


def _powers(context: MigrationContext, son_id: int, row: LegacyRow) -> None:
    reference = f"son:{row.integer('id')}"
    for slot, item in enumerate(as_list(row.json("powers"))[:POWER_SLOTS]):
        raw_effect = context.vocabulary.field("power", item, "effect")
        effect = context.vocabulary.decode_as("power_effect", raw_effect, PowerEffect)
        name = as_text(context.vocabulary.field("power", item, "name"))
        if effect is None or name is None:
            context.report.place_failed("son power", reference, f"power {slot} with effect {raw_effect!r} could not be read")
            continue
        param = context.vocabulary.field("power", item, "param")
        param_type = context.vocabulary.decode_as("entity_type", param, EntityType) if effect is PowerEffect.CHEAP_CREATION else None
        param_stat = context.vocabulary.decode_as("son_stat", param, Stat) if effect is PowerEffect.DUEL_MASTER else None
        if param is not None and param_type is None and param_stat is None:
            context.report.warn(UNKNOWN_VALUE, reference, f"power parameter {param!r} dropped")
        context.add(
            SonPowerRow(
                son_id=son_id,
                slot=slot,
                name=name,
                description=as_text(context.vocabulary.field("power", item, "description")) or name,
                effect=effect,
                param_entity_type=param_type,
                param_stat=param_stat,
            )
        )


async def import_sons(context: MigrationContext) -> None:
    created: list[tuple[LegacyRow, SonRow]] = []
    for row in context.source.rows("sons", ("id",)):
        son = _son(context, row)
        if son is not None:
            created.append((row, son))
    context.session.add_all([son for _, son in created])
    await context.session.flush()
    for row, son in created:
        context.ids.put(LegacyKind.SON, row.integer("id") or 0, son.id)
        context.names.bind(son.id, son.name)
        _powers(context, son.id, row)
    context.session.add_all(context.names.drain())
    for row, son in created:
        parent = context.son(row.integer("parent_id"))
        son.parent_son_id = parent if parent != son.id else None
    await context.flush()
    _relations(context)
    await context.flush()


def _relations(context: MigrationContext) -> None:
    seen: set[tuple[int, int]] = set()
    for row in context.source.iterate("son_relations"):
        first, second = context.son(row.integer("son_a")), context.son(row.integer("son_b"))
        reference = f"son_relation:{row.integer('son_a')}-{row.integer('son_b')}"
        if first is None or second is None or first == second:
            context.report.place_failed("son relation", reference, "a son is missing")
            continue
        pair = (min(first, second), max(first, second))
        if pair in seen:
            continue
        seen.add(pair)
        value = required_bounded(context.report, reference, "relation", row.integer("value"), (RELATION_MIN, RELATION_MAX), fallback=0)
        context.add(SonRelationRow(son_a_id=pair[0], son_b_id=pair[1], value=value, note=row.text("note")))


async def link_son_entities(context: MigrationContext) -> None:
    for row in context.source.iterate("sons"):
        son_id = context.son(row.integer("id"))
        if son_id is None:
            continue
        son = await context.session.get(SonRow, son_id)
        if son is None:
            continue
        for column, attribute in (("anchor_id", "anchor_entity_id"), ("corpse_id", "corpse_entity_id")):
            legacy = row.integer(column)
            if legacy is None:
                continue
            target = context.entity(legacy)
            if target is None:
                context.report.place_failed("son link", f"son:{row.integer('id')}", f"{column} entity {legacy} is missing")
            setattr(son, attribute, target)
    await context.session.flush()


def _god_domains(context: MigrationContext, reference: str, raw: str | None) -> tuple[Domain | None, Domain | None]:
    parts = [part.strip() for part in (raw or "").split(context.vocabulary.texts.domain_separator) if part.strip()]
    decoded = [(part, context.vocabulary.decode_as("domain", part, Domain)) for part in parts]
    for part, domain in decoded:
        if domain is None:
            context.report.warn(UNKNOWN_VALUE, reference, f"domain {part!r} is not one of the forty domains")
    known = [domain for _, domain in decoded if domain is not None]
    primary = known[0] if known else None
    secondary = next((domain for domain in known[1:] if domain is not primary), None)
    return primary, secondary


def _foreign_god(context: MigrationContext, row: LegacyRow) -> ForeignGodRow | None:
    legacy_id = row.integer("id") or 0
    reference = f"foreign_god:{legacy_id}"
    primary, secondary = _god_domains(context, reference, row.text("domains"))
    world_id = context.world(row.integer("world_id"))
    if primary is None or world_id is None:
        context.report.place_failed("foreign god", reference, "no known domain or world")
        return None
    status = context.vocabulary.decode_as("foreign_god_status", row.text("status"), ForeignGodStatus) or ForeignGodStatus.AWAKE
    death_epoch = row.integer("death_epoch")
    if status is ForeignGodStatus.DEAD and death_epoch is None:
        death_epoch = context.epoch
        context.report.warn(DEFAULTED, reference, f"death epoch set to {death_epoch}")
    stats = stat_block(context, reference, row.json("stats"))
    profile, raw_mode = blobs.existence(context.vocabulary, row.json("existence_profile"))
    if raw_mode is not None:
        context.report.warn(UNKNOWN_VALUE, reference, f"existence mode {raw_mode!r} dropped")
    return ForeignGodRow(
        name=named(context, "foreign_god", legacy_id, row.text("name")),
        title=row.text("title"),
        domain_primary=primary,
        domain_secondary=secondary,
        world_id=world_id,
        power=required_bounded(context.report, reference, "power", row.integer("power"), (PERCENT_MIN, PERCENT_MAX), fallback=PERCENT_MIN),
        faith=max(0, row.integer("faith") or 0),
        stance=required_bounded(context.report, reference, "stance", row.integer("stance"), (RELATION_MIN, RELATION_MAX), fallback=0),
        status=status,
        contacted=row.flag("contacted"),
        description=row.text("description"),
        image_prompt=row.text("image_prompt"),
        **{stat.value: value for stat, value in stats.items()},
        personality=blobs.personality(context.vocabulary, row.json("personality")),
        existence_profile=profile,
        depth=blobs.god_depth(context.vocabulary, row.json("depth"), context.epoch),
        awakening_pressure=max(0, row.integer("awakening_pressure") or 0),
        awakening_average=row.number("awakening_average"),
        created_epoch=max(1, row.integer("created_epoch") or 1),
        defeated_epoch=bounded(context.report, reference, "defeated epoch", row.integer("defeated_epoch"), (0, None)),
        death_epoch=death_epoch,
    )


async def import_foreign_gods(context: MigrationContext) -> None:
    created: list[tuple[LegacyRow, ForeignGodRow]] = []
    for row in context.source.rows("foreign_gods", ("id",)):
        god = _foreign_god(context, row)
        if god is not None:
            created.append((row, god))
    context.session.add_all([god for _, god in created])
    await context.session.flush()
    for row, god in created:
        context.ids.put(LegacyKind.FOREIGN_GOD, row.integer("id") or 0, god.id)
        context.names.bind(god.id, god.name)
        for slot, item in enumerate(as_list(row.json("powers"))):
            raw_effect = context.vocabulary.field("power", item, "effect")
            effect = context.vocabulary.decode_as("foreign_god_power", raw_effect, ForeignGodPowerEffect)
            name = as_text(context.vocabulary.field("power", item, "name"))
            if effect is None or name is None:
                context.report.place_failed(
                    "foreign god power", f"foreign_god:{row.integer('id')}", f"power {slot} with effect {raw_effect!r} could not be read"
                )
                continue
            description = as_text(context.vocabulary.field("power", item, "description")) or name
            context.add(ForeignGodPowerRow(god_id=god.id, slot=slot, name=name, effect=effect, description=description))
    context.session.add_all(context.names.drain())
    await context.flush()
