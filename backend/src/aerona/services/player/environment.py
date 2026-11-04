from pydantic import Field

from aerona.cartography.biomes import Biome
from aerona.catalog.weather import WEATHER
from aerona.core.errors import NotFoundError, ValidationFailedError
from aerona.db.tables.celestial import WorldRow
from aerona.db.tables.economy import WorldMaterialRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.environment import CalendarRow
from aerona.domain.enums.action import ActionKind
from aerona.domain.enums.bond import BondKind
from aerona.domain.enums.environment import NotableYearKind, ScarKind, WeatherKind
from aerona.domain.enums.material import MaterialKind
from aerona.engine.environment import control
from aerona.engine.phases.environment import adopt_calendar, write_seasons
from aerona.engine.primitives.queries import active_bonds
from aerona.services.player.scope import Command, Effect, PlayerScope, player_action

FIELD_PATTERN = r"^[a-z][a-z_]*$"
NAME_MAX = 60


class SetRegionEnvironment(Command):
    region_id: int
    field: str = Field(pattern=FIELD_PATTERN)
    value: int | str
    lock: bool = True


class UnlockRegionEnvironment(Command):
    region_id: int
    field: str = Field(pattern=FIELD_PATTERN)


class SetScar(Command):
    region_id: int
    kind: ScarKind
    depth: int = Field(ge=0, le=100)
    lock: bool = False


class SetMineral(Command):
    region_id: int
    material: MaterialKind | None = None
    world_material_id: int | None = None
    richness: int = Field(ge=0, le=100)
    lock: bool = False


class SetBiome(Command):
    region_id: int
    biome: int = Field(ge=0, le=9)
    share: int = Field(ge=0, le=100)
    lock: bool = True


class SetPlaceEnvironment(Command):
    place_id: int
    field: str = Field(pattern=FIELD_PATTERN)
    value: int | str | bool
    lock: bool = True


class ReorderSeasons(Command):
    world_id: int
    order: list[int] = Field(min_length=1)


class EditSeason(Command):
    season_id: int
    name: str | None = Field(default=None, min_length=1, max_length=NAME_MAX)
    temperature_shift: int | None = Field(default=None, ge=-100, le=100)
    rain_shift: int | None = Field(default=None, ge=-100, le=100)
    growth: int | None = Field(default=None, ge=0, le=100)
    travel: int | None = Field(default=None, ge=0, le=100)
    campaign: int | None = Field(default=None, ge=0, le=100)


class SetWorldCalendar(Command):
    world_id: int
    axial_tilt: int | None = Field(default=None, ge=0, le=90)
    year_length_days: int | None = Field(default=None, ge=1)
    day_length_hours: int | None = Field(default=None, ge=1)
    regenerate_seasons: bool = True


class CalendarTarget(Command):
    knowledge_id: int


class RenameMonths(Command):
    knowledge_id: int
    names: list[str] = Field(min_length=1)


async def _entity(scope: PlayerScope, entity_id: int) -> EntityRow:
    found = await scope.session.get(EntityRow, entity_id)
    if found is None:
        raise NotFoundError("No such record.")
    return found


async def _world(scope: PlayerScope, world_id: int) -> WorldRow:
    found = await scope.session.get(WorldRow, world_id)
    if found is None:
        raise NotFoundError("No such world.")
    return found


@player_action("environment:set", ActionKind.OTHER)
async def set_region_environment(scope: PlayerScope, command: SetRegionEnvironment) -> Effect:
    region = await _entity(scope, command.region_id)
    ground = await control.region_ground(scope.session, region.id)
    control.set_region_field(ground, command.field, command.value, lock=command.lock)
    held = " and held there" if command.lock and command.field in control.LOCKABLE else ""
    return Effect(f"{region.name}'s {command.field.replace('_', ' ')} is now {getattr(ground, command.field)}{held}.", target_node_id=region.id)


@player_action("environment:unlock", ActionKind.OTHER)
async def unlock_region_environment(scope: PlayerScope, command: UnlockRegionEnvironment) -> Effect:
    region = await _entity(scope, command.region_id)
    ground = await control.region_ground(scope.session, region.id)
    if not control.unlock_region_field(ground, command.field):
        raise ValidationFailedError(f"{region.name}'s {command.field.replace('_', ' ')} is not held.")
    return Effect(f"{region.name}'s {command.field.replace('_', ' ')} follows the world again.", target_node_id=region.id)


@player_action("environment:scar", ActionKind.OTHER)
async def set_region_scar(scope: PlayerScope, command: SetScar) -> Effect:
    region = await _entity(scope, command.region_id)
    ground = await control.region_ground(scope.session, region.id)
    control.set_scar(ground, command.kind, command.depth, lock=command.lock)
    label = command.kind.value.replace("_", " ")
    message = f"{region.name} bears {label} of depth {command.depth}" if command.depth else f"The {label} of {region.name} is healed"
    message += ", held against time." if command.lock and command.depth else "."
    return Effect(message, target_node_id=region.id)


@player_action("environment:mineral", ActionKind.OTHER)
async def set_region_mineral(scope: PlayerScope, command: SetMineral) -> Effect:
    region = await _entity(scope, command.region_id)
    ground = await control.region_ground(scope.session, region.id)
    if command.material is not None and command.world_material_id is None:
        key = command.material.value
        material = command.material.value.replace("_", " ")
    elif command.world_material_id is not None and command.material is None:
        world_material = await scope.session.get(WorldMaterialRow, command.world_material_id)
        if world_material is None or world_material.world_id != ground.world_id:
            raise NotFoundError("No such material in this region's world.")
        key = control.world_seam(world_material.id)
        material = world_material.name or (world_material.base_kind.value.replace("_", " ") if world_material.base_kind is not None else "strange stone")
    else:
        raise ValidationFailedError("Name either a material or a world material for the seam.")
    control.set_mineral(ground, key, command.richness, lock=command.lock)
    message = f"{region.name} holds {material} of richness {command.richness}." if command.richness else f"{region.name} holds no {material}."
    return Effect(message, target_node_id=region.id)


@player_action("environment:biome", ActionKind.OTHER)
async def set_region_biome(scope: PlayerScope, command: SetBiome) -> Effect:
    region = await _entity(scope, command.region_id)
    ground = await control.region_ground(scope.session, region.id)
    control.set_biome(ground, command.biome, command.share, lock=command.lock)
    label = Biome(command.biome).name.replace("_", " ").lower()
    return Effect(f"{label.capitalize()} now covers {command.share} of {region.name}.", target_node_id=region.id)


@player_action("environment:place", ActionKind.OTHER)
async def set_place_environment(scope: PlayerScope, command: SetPlaceEnvironment) -> Effect:
    place = await _entity(scope, command.place_id)
    ground = await control.place_ground(scope.session, place.id)
    control.set_place_field(ground, command.field, command.value, lock=command.lock)
    held = " and held there" if command.field in ground.locked else ""
    return Effect(f"{place.name}'s {command.field.replace('_', ' ')} is now {getattr(ground, command.field)}{held}.", target_node_id=place.id)


@player_action("seasons:reorder", ActionKind.OTHER)
async def reorder_world_seasons(scope: PlayerScope, command: ReorderSeasons) -> Effect:
    world = await _world(scope, command.world_id)
    seasons = await control.reorder_seasons(scope.session, world.id, command.order)
    return Effect(f"The year of {world.name} now runs: {', '.join(season.name for season in seasons)}.", target_node_id=world.id)


@player_action("seasons:edit", ActionKind.OTHER)
async def edit_world_season(scope: PlayerScope, command: EditSeason) -> Effect:
    values = command.model_dump(exclude={"season_id", "name"}, exclude_none=True)
    season = await control.edit_season(scope.session, command.season_id, values, command.name)
    return Effect(f"{season.name} was reshaped.", target_node_id=season.world_id)


@player_action("seasons:calendar", ActionKind.OTHER)
async def set_world_calendar(scope: PlayerScope, command: SetWorldCalendar) -> Effect:
    world = await _world(scope, command.world_id)
    control.set_world_calendar(
        scope.rules, world, axial_tilt=command.axial_tilt, year_length_days=command.year_length_days, day_length_hours=command.day_length_hours
    )
    if command.regenerate_seasons:
        await write_seasons(await scope.context("seasons:calendar"), world)
    return Effect(
        f"{world.name} turns with an axial tilt of {world.axial_tilt}, {world.year_length_days} days a year and {world.season_count} seasons.",
        target_node_id=world.id,
    )


@player_action("calendar:adopt", ActionKind.OTHER)
async def adopt_world_calendar(scope: PlayerScope, command: CalendarTarget) -> Effect:
    record = await control.astronomy_record(scope.session, command.knowledge_id)
    if await scope.session.get(CalendarRow, record.id) is not None:
        raise ValidationFailedError(f"{record.name} already keeps a calendar.")
    knowers = [bond.source_node_id for bond in await active_bonds(scope.session, [BondKind.KNOWS], targets=[record.id])]
    if not knowers:
        raise ValidationFailedError(f"No one knows {record.name}; a calendar needs keepers.")
    calendar = await adopt_calendar(await scope.context("calendar:adopt"), record, knowers[0])
    return Effect(f"{record.name} now keeps a calendar of {len(calendar.month_names)} months.", target_node_id=record.id)


@player_action("calendar:drop", ActionKind.OTHER)
async def drop_world_calendar(scope: PlayerScope, command: CalendarTarget) -> Effect:
    record = await control.astronomy_record(scope.session, command.knowledge_id)
    if not await control.drop_calendar(scope.session, record.id):
        raise ValidationFailedError(f"{record.name} keeps no calendar.")
    return Effect(f"{record.name} no longer keeps a calendar.", target_node_id=record.id)


@player_action("calendar:rename", ActionKind.OTHER)
async def rename_calendar_months(scope: PlayerScope, command: RenameMonths) -> Effect:
    record = await control.astronomy_record(scope.session, command.knowledge_id)
    calendar = await control.rename_months(scope.session, record.id, command.names)
    return Effect(f"The months of {record.name} are now {', '.join(calendar.month_names)}.", target_node_id=record.id)


class LeyTarget(Command):
    line_id: int


class SeverLey(Command):
    line_id: int
    epochs: int | None = Field(default=None, ge=1)


async def _line_name(scope: PlayerScope, first: int, second: int) -> str:
    one, two = await _entity(scope, first), await _entity(scope, second)
    return f"the ley line between {one.name} and {two.name}"


@player_action("ley:sever", ActionKind.OTHER)
async def sever_ley_line(scope: PlayerScope, command: SeverLey) -> Effect:
    epoch = await scope.epoch()
    epochs = command.epochs or scope.rules.environment.sever_ley_epochs
    line = await control.sever_ley(scope.session, command.line_id, until_epoch=epoch + epochs - 1)
    return Effect(f"{(await _line_name(scope, line.region_a_id, line.region_b_id)).capitalize()} is cut for {epochs} epochs.", target_node_id=line.region_a_id)


@player_action("ley:restore", ActionKind.OTHER)
async def restore_ley_line(scope: PlayerScope, command: LeyTarget) -> Effect:
    line = await control.restore_ley(scope.session, command.line_id)
    return Effect(f"{(await _line_name(scope, line.region_a_id, line.region_b_id)).capitalize()} flows again.", target_node_id=line.region_a_id)


class ForgeLey(Command):
    first_region_id: int
    second_region_id: int
    strength: int | None = Field(default=None, ge=0, le=100)


@player_action("ley:forge", ActionKind.OTHER)
async def forge_ley_line(scope: PlayerScope, command: ForgeLey) -> Effect:
    line = await control.forge_ley(
        scope.session, scope.rules, command.first_region_id, command.second_region_id, epoch=await scope.epoch(), strength=command.strength
    )
    name = await _line_name(scope, line.region_a_id, line.region_b_id)
    return Effect(f"{name.capitalize()} is forged at strength {line.strength}; it holds even where the land's magic is thin.", target_node_id=line.region_a_id)


@player_action("ley:unforge", ActionKind.OTHER)
async def unforge_ley_line(scope: PlayerScope, command: LeyTarget) -> Effect:
    line = await control.unforge_ley(scope.session, command.line_id)
    name = await _line_name(scope, line.region_a_id, line.region_b_id)
    return Effect(f"{name.capitalize()} is left to the land's own magic again.", target_node_id=line.region_a_id)


class ForceWeather(Command):
    region_id: int
    kind: WeatherKind
    epochs: int = Field(default=1, ge=1, le=1000)
    season_position: int | None = Field(default=None, ge=0)


class ForcedTarget(Command):
    forced_id: int


@player_action("weather:force", ActionKind.OTHER)
async def force_weather(scope: PlayerScope, command: ForceWeather) -> Effect:
    region = await _entity(scope, command.region_id)
    row = await control.force_weather(
        scope.session, region, command.kind, from_epoch=await scope.epoch(), epochs=command.epochs, season_position=command.season_position
    )
    when = f"season {row.season_position + 1}" if row.season_position is not None else "every season"
    label = WEATHER[row.kind].label.lower()
    return Effect(f"{label.capitalize()} will hold over {region.name} in {when} for {command.epochs} epochs.", target_node_id=region.id)


@player_action("weather:release", ActionKind.OTHER)
async def release_weather(scope: PlayerScope, command: ForcedTarget) -> Effect:
    row = await control.release_weather(scope.session, command.forced_id)
    region = await _entity(scope, row.region_entity_id)
    return Effect(f"The sky over {region.name} goes its own way again.", target_node_id=region.id)


class ForceNotableYear(Command):
    region_id: int
    kind: NotableYearKind
    magnitude: int = Field(ge=0, le=100)
    name: str | None = Field(default=None, min_length=1, max_length=120)
    weather: WeatherKind | None = None


@player_action("year:force_notable", ActionKind.OTHER)
async def force_notable_year(scope: PlayerScope, command: ForceNotableYear) -> Effect:
    region = await _entity(scope, command.region_id)
    row = await control.force_notable_year(
        scope.session,
        scope.rules,
        region,
        command.kind,
        epoch=await scope.epoch(),
        magnitude=command.magnitude,
        name=command.name,
        weather=command.weather,
    )
    return Effect(f"{row.name[:1].upper() + row.name[1:]} (the year {row.year}) is written into {region.name}'s memory.", target_node_id=region.id)
