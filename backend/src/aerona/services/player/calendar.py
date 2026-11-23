from pydantic import Field

from aerona.catalog.weather import WEATHER
from aerona.core.errors import NotFoundError, ValidationFailedError
from aerona.core.grammar import agree, several, spoken
from aerona.db.tables.celestial import WorldRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.environment import NotableYearRow
from aerona.domain.enums.action import ActionKind
from aerona.domain.enums.environment import NotableYearKind, SeasonOnset, WeatherKind
from aerona.domain.enums.modifier import IncidentRole
from aerona.engine.environment import time_control
from aerona.engine.lore.calendar_rites import found_fast, keepers_of
from aerona.engine.recording.record import record
from aerona.services.player.scope import Command, Effect, PlayerScope, player_action

NAME_MAX = 120
SEASON_NAME_MAX = 60


class AddSeason(Command):
    world_id: int
    name: str = Field(min_length=1, max_length=SEASON_NAME_MAX)
    position: int | None = Field(default=None, ge=0)
    temperature_shift: int = Field(default=0, ge=-100, le=100)
    rain_shift: int = Field(default=0, ge=-100, le=100)
    growth: int = Field(default=50, ge=0, le=100)
    travel: int = Field(default=50, ge=0, le=100)
    campaign: int = Field(default=50, ge=0, le=100)
    share_pct: int | None = Field(default=None, ge=1, le=100)


class SeasonTarget(Command):
    season_id: int


class SetOnset(Command):
    world_id: int
    year: int
    season_position: int = Field(ge=0)
    onset: SeasonOnset


class OnsetTarget(Command):
    onset_id: int


class SetMoons(Command):
    world_id: int
    moon_count: int | None = Field(default=None, ge=0, le=100)
    tidal_strength: int | None = Field(default=None, ge=0, le=100)


class ReleaseCalendar(Command):
    world_id: int
    fields: list[str] = Field(min_length=1)


class EditWeather(Command):
    forced_id: int
    kind: WeatherKind | None = None
    until_epoch: int | None = Field(default=None, ge=1)
    season_position: int | None = Field(default=None, ge=0)
    every_season: bool = False


class EditNotableYear(Command):
    notable_id: int
    name: str | None = Field(default=None, min_length=1, max_length=NAME_MAX)
    magnitude: int | None = Field(default=None, ge=0, le=100)
    kind: NotableYearKind | None = None
    weather: WeatherKind | None = None
    year: int | None = Field(default=None, ge=0)


class NotableTarget(Command):
    notable_id: int


class SetHolyDay(Command):
    knowledge_id: int
    index: int | None = Field(default=None, ge=0)
    name: str = Field(min_length=1, max_length=NAME_MAX)
    season_position: int | None = Field(default=None, ge=0)
    notable_year_id: int | None = None
    tradition_id: int | None = None
    found_tradition: bool = False


class HolyDayTarget(Command):
    knowledge_id: int
    index: int = Field(ge=0)


class SetAnchor(Command):
    knowledge_id: int
    anchor_year: int = Field(ge=0)


class LeyStrength(Command):
    line_id: int
    strength: int = Field(ge=0, le=100)


class LeyLineTarget(Command):
    line_id: int


class LeyWork(Command):
    structure_id: int
    values: dict[str, bool] = Field(default_factory=dict)
    release: list[str] = Field(default_factory=list)


async def _world(scope: PlayerScope, world_id: int) -> WorldRow:
    found = await scope.session.get(WorldRow, world_id)
    if found is None:
        raise NotFoundError("No such world.")
    return found


async def _name(scope: PlayerScope, entity_id: int) -> str:
    found = await scope.session.get(EntityRow, entity_id)
    return found.name if found is not None else "a lost land"


@player_action("seasons:add", ActionKind.OTHER)
async def add_season(scope: PlayerScope, command: AddSeason) -> Effect:
    values = command.model_dump(include={"temperature_shift", "rain_shift", "growth", "travel", "campaign"})
    season = await time_control.add_season(scope.session, command.world_id, command.name, values, command.position, share_pct=command.share_pct)
    world = await _world(scope, command.world_id)
    ctx = await scope.context("seasons:add")
    await record(ctx, "season.added", roles={IncidentRole.SUBJECT: world.id}, facts={"season": season.name, "share": season.share_pct}, world_id=world.id)
    return Effect(f"{season.name} now turns in the year of {world.name}, season {season.position + 1} of {world.season_count}.", target_node_id=world.id)


@player_action("seasons:remove", ActionKind.OTHER)
async def remove_season(scope: PlayerScope, command: SeasonTarget) -> Effect:
    season = await time_control.remove_season(scope.session, command.season_id)
    world = await _world(scope, season.world_id)
    ctx = await scope.context("seasons:remove")
    await record(ctx, "season.removed", roles={IncidentRole.SUBJECT: world.id}, facts={"season": season.name}, world_id=world.id)
    return Effect(
        f"{season.name} is gone from the year of {world.name}; "
        f"{several(world.season_count, 'season', 'seasons')} {agree(world.season_count, 'remains', 'remain')}.",
        target_node_id=world.id,
    )


@player_action("seasons:release", ActionKind.OTHER)
async def release_season(scope: PlayerScope, command: SeasonTarget) -> Effect:
    season = await time_control.release_season(scope.session, command.season_id)
    return Effect(f"{season.name} is no longer held; the world may reshape it when its year changes.", target_node_id=season.world_id)


@player_action("seasons:onset", ActionKind.OTHER)
async def set_onset(scope: PlayerScope, command: SetOnset) -> Effect:
    row = await time_control.set_onset(
        scope.session, command.world_id, command.year, command.season_position, command.onset, by_node_id=(await scope.creator()).id
    )
    world = await _world(scope, command.world_id)
    return Effect(
        f"In year {row.year} of {world.name}, season {row.season_position + 1} comes {spoken(row.onset)}; the onset is held.", target_node_id=world.id
    )


@player_action("seasons:onset_release", ActionKind.OTHER)
async def release_onset(scope: PlayerScope, command: OnsetTarget) -> Effect:
    row = await time_control.release_onset(scope.session, command.onset_id)
    return Effect(f"The onset of year {row.year} is no longer held; the engine draws it again.", target_node_id=row.world_id)


@player_action("seasons:onset_clear", ActionKind.OTHER)
async def clear_onset(scope: PlayerScope, command: OnsetTarget) -> Effect:
    row = await time_control.clear_onset(scope.session, command.onset_id)
    return Effect(f"Season {row.season_position + 1} comes on time in year {row.year}.", target_node_id=row.world_id)


@player_action("seasons:moons", ActionKind.OTHER)
async def set_moons(scope: PlayerScope, command: SetMoons) -> Effect:
    if command.moon_count is None and command.tidal_strength is None:
        raise ValidationFailedError("Set the moons or the tides.")
    world = await _world(scope, command.world_id)
    time_control.set_moons(world, scope.rules, moon_count=command.moon_count, tidal_strength=command.tidal_strength)
    await scope.session.flush()
    return Effect(
        f"{world.name} now has {several(world.moon_count, 'moon', 'moons')} and tides of {world.tidal_strength}; both are held.", target_node_id=world.id
    )


@player_action("seasons:calendar_release", ActionKind.OTHER)
async def release_calendar(scope: PlayerScope, command: ReleaseCalendar) -> Effect:
    world = await time_control.release_calendar(scope.session, command.world_id, command.fields)
    released = ", ".join(field.replace("_", " ") for field in command.fields)
    return Effect(f"The {released} of {world.name} follow the heavens again from the next epoch.", target_node_id=world.id)


@player_action("weather:edit", ActionKind.OTHER)
async def edit_weather(scope: PlayerScope, command: EditWeather) -> Effect:
    row = await time_control.edit_weather(
        scope.session,
        command.forced_id,
        kind=command.kind,
        until_epoch=command.until_epoch,
        season_position=command.season_position,
        every_season=command.every_season,
    )
    when = f"season {row.season_position + 1}" if row.season_position is not None else "every season"
    label = WEATHER[row.kind].label.lower()
    return Effect(f"{label.capitalize()} holds over {await _name(scope, row.region_entity_id)} in {when} until epoch {row.until_epoch}.", row.region_entity_id)


@player_action("year:edit", ActionKind.OTHER)
async def edit_notable_year(scope: PlayerScope, command: EditNotableYear) -> Effect:
    row = await time_control.edit_notable_year(
        scope.session, command.notable_id, name=command.name, magnitude=command.magnitude, kind=command.kind, weather=command.weather, year=command.year
    )
    return Effect(f"{row.name[:1].upper() + row.name[1:]} (the year {row.year}) is remembered at magnitude {row.magnitude}.", row.region_entity_id)


@player_action("year:delete", ActionKind.OTHER)
async def delete_notable_year(scope: PlayerScope, command: NotableTarget) -> Effect:
    row = await time_control.delete_notable_year(scope.session, command.notable_id)
    return Effect(f"{row.name[:1].upper() + row.name[1:]} is struck from memory.", row.region_entity_id)


@player_action("calendar:holy_day", ActionKind.OTHER)
async def set_holy_day(scope: PlayerScope, command: SetHolyDay) -> Effect:
    tradition_id = command.tradition_id
    if command.found_tradition and tradition_id is None:
        if command.notable_year_id is None:
            raise ValidationFailedError("A holy day founds its fast from a remembered year; pick one.")
        notable = await scope.session.get(NotableYearRow, command.notable_year_id)
        if notable is None:
            raise NotFoundError("No such notable year.")
        calendar = await time_control.calendar_of(scope.session, command.knowledge_id)
        row = await found_fast(await scope.context("calendar:holy_day"), calendar, notable, await keepers_of(scope.session, calendar.knowledge_entity_id))
        tradition_id = row.tradition_entity_id
    entry = time_control.holy_day_entry(
        command.name, season_position=command.season_position, notable_year_id=command.notable_year_id, tradition_id=tradition_id, year=None
    )
    calendar = await time_control.set_holy_day(scope.session, command.knowledge_id, command.index, entry)
    verb = "keeps" if command.index is None else "now keeps"
    return Effect(f"{await _name(scope, calendar.knowledge_entity_id)} {verb} the holy day of {command.name}.", calendar.knowledge_entity_id)


@player_action("calendar:holy_day_remove", ActionKind.OTHER)
async def remove_holy_day(scope: PlayerScope, command: HolyDayTarget) -> Effect:
    removed = await time_control.remove_holy_day(scope.session, command.knowledge_id, command.index)
    return Effect(f"{removed.get('name', 'The holy day')} is no longer kept by {await _name(scope, command.knowledge_id)}.", command.knowledge_id)


@player_action("calendar:anchor", ActionKind.OTHER)
async def set_anchor(scope: PlayerScope, command: SetAnchor) -> Effect:
    calendar = await time_control.set_anchor(scope.session, command.knowledge_id, command.anchor_year)
    return Effect(f"{await _name(scope, command.knowledge_id)} now counts its years from {calendar.anchor_year}.", command.knowledge_id)


@player_action("ley:strength", ActionKind.OTHER)
async def set_ley_strength(scope: PlayerScope, command: LeyStrength) -> Effect:
    line = await time_control.set_ley_strength(scope.session, command.line_id, command.strength)
    first, second = await _name(scope, line.region_a_id), await _name(scope, line.region_b_id)
    return Effect(f"The ley line between {first} and {second} flows at {line.strength} and is held there.", line.region_a_id)


@player_action("ley:dissolve", ActionKind.OTHER)
async def dissolve_ley(scope: PlayerScope, command: LeyLineTarget) -> Effect:
    line = await time_control.dissolve_ley(scope.session, command.line_id)
    first, second = await _name(scope, line.region_a_id), await _name(scope, line.region_b_id)
    return Effect(f"The ley line between {first} and {second} is unmade; the land may form it again if its magic runs strong.", line.region_a_id)


@player_action("ley:work", ActionKind.OTHER)
async def set_ley_work(scope: PlayerScope, command: LeyWork) -> Effect:
    row = await time_control.set_ley_work(scope.session, command.structure_id, command.values, command.release)
    ties = [
        label for key, label in (("attuned", "channels the ley"), ("on_ley_line", "stands on a line"), ("at_nexus", "stands at a nexus")) if getattr(row, key)
    ]
    name = await _name(scope, command.structure_id)
    return Effect(f"{name} {', '.join(ties) if ties else 'has no tie to the ley'}.", command.structure_id)
