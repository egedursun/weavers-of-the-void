import hashlib
from datetime import UTC, datetime

from aerona.cartography.terrain import default_terrain
from aerona.constants.migration import SEED_DIGEST_BITS
from aerona.constants.schema import SINGLETON_ID
from aerona.constants.units import PERCENT
from aerona.db.repositories.cosmos import snapshot_rules
from aerona.db.tables.celestial import StarRow, WorldRow
from aerona.db.tables.cosmos import CosmosRow, CreatorMoodInputRow, CreatorRow
from aerona.domain.enums.chronicle import NotificationCategory
from aerona.domain.enums.creator import CreatorMoodAxis
from aerona.domain.enums.limits import PERCENT_MAX, PERCENT_MIN
from aerona.domain.enums.world import Atmosphere, ClimateEra, Discovery, FateMode, Gravity, LoreLanguage, SonDistribution, StarType, WorldType
from aerona.migration.legacy import blobs
from aerona.migration.legacy.context import MigrationContext
from aerona.migration.legacy.idmap import LegacyKind
from aerona.migration.legacy.source import LegacyRow
from aerona.migration.legacy.values import as_dict, as_float, as_int, as_list, as_text, bounded, required_bounded

UNKNOWN_VALUE = "unknown value"
DEFAULTED = "defaulted value"
NOT_CARRIED = "not carried"
MOOD_DEFAULT = 50
FIRST_EPOCH = 1
FIRST_ORBIT = 1.0


def rng_seed(name: str, seed_idea: str) -> int:
    digest = hashlib.sha256(f"{name}\n{seed_idea}".encode()).digest()
    return int.from_bytes(digest[:8], "big") >> (64 - SEED_DIGEST_BITS)


def named(context: MigrationContext, kind: str, legacy_id: int | None, name: str | None) -> str:
    original = (name or "").strip() or f"{kind} {legacy_id}"
    display = context.names.reserve(original)
    if display != original:
        context.report.renamed(kind, legacy_id, original, display)
    return display


def star_type(context: MigrationContext, row: LegacyRow) -> StarType:
    raw = row.text("kind")
    decoded = context.vocabulary.decode_as("star_type", raw, StarType)
    if decoded is not None:
        return decoded
    folded = (raw or "").casefold()
    labels = sorted(context.vocabulary.enums["star_type"].items(), key=lambda item: -len(item[0]))
    found = next((StarType(english) for legacy, english in labels if legacy.casefold() in folded), None)
    if found is None:
        context.report.warn(UNKNOWN_VALUE, f"star:{row.integer('id')}", f"star kind {raw!r} set to {StarType.YELLOW_DWARF.value}")
        return StarType.YELLOW_DWARF
    context.report.warn(DEFAULTED, f"star:{row.integer('id')}", f"star kind {raw!r} read as {found.value}")
    return found


async def import_stars(context: MigrationContext) -> None:
    rows = context.source.rows("stars", ("id",))
    created: list[tuple[int, StarRow]] = []
    for row in rows:
        legacy_id = row.integer("id") or 0
        star = StarRow(
            name=named(context, "star", legacy_id, row.text("name")),
            star_type=star_type(context, row),
            brightness=required_bounded(context.report, f"star:{legacy_id}", "brightness", row.integer("brightness"), (PERCENT_MIN, PERCENT_MAX), fallback=0),
            x=row.number("x") or 0.0,
            y=row.number("y") or 0.0,
            description=row.text("description"),
            image_prompt=row.text("image_prompt"),
            created_epoch=max(FIRST_EPOCH, row.integer("created_epoch") or FIRST_EPOCH),
        )
        created.append((legacy_id, star))
    context.session.add_all([star for _, star in created])
    await context.session.flush()
    for legacy_id, star in created:
        context.ids.put(LegacyKind.STAR, legacy_id, star.id)
        context.names.bind(star.id, star.name)
    context.session.add_all(context.names.drain())


def _terrain(context: MigrationContext, row: LegacyRow, world_type: WorldType) -> tuple[float, float, float]:
    data = as_dict(row.json("terrain"))
    defaults = default_terrain(world_type, context.rules)
    sea = as_float(context.vocabulary.field("terrain", data, "sea"))
    mountains = as_float(context.vocabulary.field("terrain", data, "mountains"))
    humidity = as_float(context.vocabulary.field("terrain", data, "humidity"))
    if sea is None or mountains is None or humidity is None:
        context.report.warn(DEFAULTED, f"world:{row.integer('id')}", "terrain filled from the world type defaults")
    return (
        min(1.0, max(0.0, sea if sea is not None else (defaults.sea_pct or 0) / PERCENT)),
        max(0.0, mountains if mountains is not None else (defaults.mountains_pct or 0) / PERCENT),
        min(1.0, max(-1.0, humidity if humidity is not None else (defaults.moisture_pct or 0) / PERCENT)),
    )


def _decoded[E: (WorldType, Gravity, Atmosphere, Discovery)](context: MigrationContext, enum_name: str, row: LegacyRow, column: str, fallback: E) -> E:
    raw = row.text(column)
    decoded = context.vocabulary.decode_as(enum_name, raw, type(fallback))
    if decoded is None:
        if raw is not None:
            context.report.warn(UNKNOWN_VALUE, f"world:{row.integer('id')}", f"{column} {raw!r} set to {fallback.value}")
        return fallback
    return decoded


async def import_worlds(context: MigrationContext) -> None:
    rows = context.source.rows("worlds", ("id",))
    created: list[tuple[LegacyRow, WorldRow]] = []
    for row in rows:
        legacy_id = row.integer("id") or 0
        reference = f"world:{legacy_id}"
        world_type = _decoded(context, "world_type", row, "world_type", WorldType.ORDINARY)
        sea, mountains, humidity = _terrain(context, row, world_type)
        climate = as_dict(row.json("climate"))
        era = context.vocabulary.decode_as("climate_era", context.vocabulary.field("climate", climate, "era"), ClimateEra)
        orbit = row.number("orbit")
        time_factor = row.number("time_factor")
        world = WorldRow(
            name=named(context, "world", legacy_id, row.text("name")),
            world_type=world_type,
            star_id=context.ids.get(LegacyKind.STAR, row.integer("star_id")),
            orbit=orbit if orbit is not None and orbit > 0 else FIRST_ORBIT,
            gravity=_decoded(context, "gravity", row, "gravity", Gravity.NORMAL),
            atmosphere=_decoded(context, "atmosphere", row, "atmosphere", Atmosphere.NORMAL),
            time_factor=time_factor if time_factor is not None and time_factor > 0 else 1.0,
            terrain_seed=row.text("seed") or row.required_text("name", reference),
            terrain_sea=sea,
            terrain_mountains=mountains,
            terrain_humidity=humidity,
            discovery=_decoded(context, "discovery", row, "discovery", Discovery.KNOWN),
            danger=required_bounded(context.report, reference, "danger", row.integer("danger"), (PERCENT_MIN, PERCENT_MAX), fallback=PERCENT_MIN),
            leakage=required_bounded(context.report, reference, "leakage", row.integer("leakage"), (PERCENT_MIN, PERCENT_MAX), fallback=PERCENT_MIN),
            cosmology=row.text("cosmology"),
            description=row.text("description"),
            image_prompt=row.text("image_prompt"),
            patron_automatic=row.flag("patron_automatic"),
            mortal_agents=bounded(context.report, reference, "mortal agents", row.integer("mortal_agents"), (0, None)),
            climate_era=era,
            climate_epochs_left=max(0, as_int(context.vocabulary.field("climate", climate, "left")) or 0) if era is not None else None,
            climate_since_epoch=as_int(context.vocabulary.field("climate", climate, "since")) if era is not None else None,
            created_epoch=max(FIRST_EPOCH, row.integer("created_epoch") or FIRST_EPOCH),
        )
        if row.text("dialect") is not None:
            context.report.convert("world_naming_rules_replaced_by_phonology")
        created.append((row, world))
    context.session.add_all([world for _, world in created])
    await context.session.flush()
    for row, world in created:
        context.ids.put(LegacyKind.WORLD, row.integer("id") or 0, world.id)
        context.names.bind(world.id, world.name)
    context.session.add_all(context.names.drain())
    for row, world in created:
        world.parent_world_id = context.world(row.integer("parent_id"))
        twin = context.world(row.integer("mirror_twin"))
        world.mirror_twin_id = twin if twin != world.id else None
    if created:
        primary = context.world(1) or min(world.id for _, world in created)
        context.primary_world_id = primary
    await context.session.flush()


async def link_world_gods(context: MigrationContext) -> None:
    for row in context.source.iterate("worlds"):
        world_id = context.world(row.integer("id"))
        if world_id is None:
            continue
        world = await context.session.get(WorldRow, world_id)
        if world is None:
            continue
        world.creator_son_id = context.son(row.integer("creator_son_id"))
        world.patron_son_id = context.son(row.integer("patron_son_id"))
        climate = as_dict(row.json("climate"))
        world.climate_imposed_by_son_id = context.son(as_int(context.vocabulary.field("climate", climate, "imposed_by")))
    await context.session.flush()


async def link_world_stars(context: MigrationContext) -> None:
    for row in context.source.iterate("worlds"):
        world_id = context.world(row.integer("id"))
        if world_id is None:
            continue
        world = await context.session.get(WorldRow, world_id)
        legacy_star = row.integer("epoch_star")
        if world is None or legacy_star is None:
            continue
        world.epoch_star_entity_id = context.entity(legacy_star)
        if world.epoch_star_entity_id is None:
            context.report.place_failed("epoch star", f"world:{row.integer('id')}", f"entity {legacy_star} is missing")
    await context.session.flush()


def _fate_mode(context: MigrationContext, state: LegacyRow) -> FateMode:
    return context.vocabulary.decode_as("fate_mode", state.text("fate_mode"), FateMode) or FateMode.AUTO


def _notification_prefs(context: MigrationContext, state: LegacyRow) -> dict[NotificationCategory, bool]:
    prefs: dict[NotificationCategory, bool] = {}
    for key, value in as_dict(state.json("notification_prefs")).items():
        category = context.vocabulary.decode_as("notification_category", key, NotificationCategory)
        if category is None:
            context.report.warn(UNKNOWN_VALUE, "world_state", f"notification category {key!r} dropped")
            continue
        prefs[category] = bool(value)
    return prefs


async def import_cosmos(context: MigrationContext, state: LegacyRow) -> CosmosRow:
    name = state.required_text("name", "Cosmos")
    seed_idea = state.required_text("seed_idea", name)
    if state.text("genesis_settings") is not None:
        context.report.warn(NOT_CARRIED, "world_state", "genesis wizard settings are not carried; they only shape a new genesis")
    cosmos = CosmosRow(
        id=SINGLETON_ID,
        name=name,
        rng_seed=rng_seed(name, seed_idea),
        lore_language=LoreLanguage.TURKISH,
        seed_idea=seed_idea,
        cosmology=state.required_text("cosmology"),
        tone=state.required_text("tone"),
        epoch=context.epoch,
        epoch_start_year=max(0, state.integer("year") or 0),
        doom_clock=max(0, state.integer("doom_clock") or 0),
        fate_mode=_fate_mode(context, state),
        son_distribution=context.vocabulary.decode_as("son_distribution", state.text("son_distribution"), SonDistribution) or SonDistribution.AUTO,
        council_every_epochs=bounded(context.report, "world_state", "council interval", state.integer("council_every"), (0, None)),
        mortal_agents_per_epoch=bounded(context.report, "world_state", "mortal agents", state.integer("mortal_agents"), (0, None)),
        mortal_agent_parallelism=bounded(context.report, "world_state", "mortal parallelism", state.integer("mortal_parallelism"), (1, None)),
        fate_debt_epoch=state.integer("fate_debt"),
        alignment_until_epoch=state.integer("alignment_until"),
        primary_world_id=context.primary_world_id or None,
        travel_resource=blobs.travel_resource(context.vocabulary, state.json("travel_resource")),
        notification_prefs=_notification_prefs(context, state),
        rules_snapshot=snapshot_rules(context.rules),
        rules_snapshot_at=datetime.now(UTC),
    )
    context.session.add(cosmos)
    await context.session.flush()
    return cosmos


async def import_creator(context: MigrationContext, state: LegacyRow) -> CreatorRow:
    vocabulary = context.vocabulary
    mood = as_dict(state.json("creator_mood"))
    axes = vocabulary.enums["creator_mood_axis"]

    def mood_value(axis: CreatorMoodAxis) -> int:
        legacy = vocabulary.encode("creator_mood_axis", axis.value)
        value = as_int(mood.get(legacy))
        if value is None:
            context.report.warn(DEFAULTED, "creator", f"mood {axis.value} set to {MOOD_DEFAULT}")
            return MOOD_DEFAULT
        return max(PERCENT_MIN, min(PERCENT_MAX, value))

    passions, automatic, unknown = blobs.creator_passions(vocabulary, state.json("creator_passions"))
    for item in unknown:
        context.report.warn(UNKNOWN_VALUE, "creator", f"passion {item!r} dropped")
    name = named(context, "creator", None, state.text("creator_name"))
    creator = CreatorRow(
        name=name,
        title=state.text("creator_title"),
        appearance=state.text("creator_appearance"),
        temperament=state.text("creator_temperament"),
        image_prompt=state.text("creator_image_prompt"),
        note=state.text("creator_note"),
        essence=max(0, state.integer("creator_essence") or 0),
        mood_contentment=mood_value(CreatorMoodAxis.CONTENTMENT),
        mood_anger=mood_value(CreatorMoodAxis.ANGER),
        mood_interest=mood_value(CreatorMoodAxis.INTEREST),
        mood_loneliness=mood_value(CreatorMoodAxis.LONELINESS),
        passions=passions,
        passions_automatic=automatic,
        depth=blobs.god_depth(vocabulary, state.json("creator_depth"), context.epoch),
        epic=blobs.epic(vocabulary, state.json("creator_epic"), context.epoch),
    )
    context.session.add(creator)
    await context.session.flush()
    context.names.bind(creator.id, creator.name)
    context.session.add_all(context.names.drain())
    context.ids.set_creator(creator.id)
    inputs = as_dict(vocabulary.field("creator_mood", mood, "inputs"))
    last_epoch = max(FIRST_EPOCH, context.epoch - 1)
    for legacy_axis, items in inputs.items():
        axis = vocabulary.decode_as("creator_mood_axis", legacy_axis, CreatorMoodAxis)
        if axis is None or legacy_axis not in axes:
            continue
        for item in as_list(items):
            label = as_text(vocabulary.field("creator_mood", item, "item"))
            delta = as_float(vocabulary.field("creator_mood", item, "delta"))
            if label is not None and delta is not None:
                context.session.add(CreatorMoodInputRow(epoch=last_epoch, axis=axis, item=label, delta=delta))
    await context.session.flush()
    return creator
