from dataclasses import dataclass

from aerona.domain.enums.environment import SeasonDating, WorldLink

SEASON_NAME = r"^(?:\w+_)?season(?:_index|_position)?$"
RATE_WORD = "per_season"


@dataclass(frozen=True)
class SeasonPosition:
    table: str
    column: str
    nullable: bool
    link: WorldLink
    through: str
    dating: SeasonDating
    writers: tuple[str, ...]


@dataclass(frozen=True)
class SeasonStep:
    table: str
    column: str


SEASON_POSITIONS: tuple[SeasonPosition, ...] = (
    SeasonPosition(
        "season_onsets",
        "season_position",
        False,
        WorldLink.WORLD,
        "world_id",
        SeasonDating.POSITION,
        ("engine/environment/onsets.py", "engine/environment/time_control.py"),
    ),
    SeasonPosition(
        "tradition_profiles",
        "season_position",
        True,
        WorldLink.ENTITY,
        "tradition_entity_id",
        SeasonDating.POSITION,
        ("engine/lore/calendar_rites.py", "engine/environment/time_control.py", "engine/environment/control.py"),
    ),
    SeasonPosition(
        "forced_weather",
        "season_position",
        True,
        WorldLink.WORLD,
        "world_id",
        SeasonDating.POSITION,
        ("engine/environment/time_control.py", "engine/environment/control.py", "engine/powers/effects.py", "engine/cosmos/phenomena.py"),
    ),
    SeasonPosition("gatherings", "season", True, WorldLink.WORLD, "world_id", SeasonDating.POSITION, ("engine/gatherings/hold.py",)),
    SeasonPosition("birth_signs", "season", False, WorldLink.ENTITY, "mortal_entity_id", SeasonDating.POSITION, ("engine/sacred/astrology.py",)),
    SeasonPosition(
        "event_profiles",
        "start_season",
        True,
        WorldLink.WORLD,
        "world_id",
        SeasonDating.POSITION,
        ("engine/happenings/profile.py", "engine/happenings/control.py", "engine/happenings/progression.py"),
    ),
    SeasonPosition(
        "event_profiles",
        "end_season",
        True,
        WorldLink.WORLD,
        "world_id",
        SeasonDating.POSITION,
        ("engine/happenings/profile.py", "engine/happenings/control.py", "engine/happenings/progression.py"),
    ),
    SeasonPosition(
        "incidents",
        "season",
        True,
        WorldLink.WORLD,
        "world_id",
        SeasonDating.DAY,
        ("engine/recording/record.py", "db/repositories/chronicle.py", "services/player/incidents.py", "services/player/record_levers.py"),
    ),
    SeasonPosition("incident_steps", "season", True, WorldLink.INCIDENT, "incident_id", SeasonDating.DAY, ("engine/recording/record.py",)),
    SeasonPosition("state_changes", "season", True, WorldLink.INCIDENT, "incident_id", SeasonDating.DAY, ("db/ledger_capture.py",)),
    SeasonPosition(
        "node_births", "season", True, WorldLink.ENTITY, "node_id", SeasonDating.DAY, ("engine/recording/births.py", "services/integrity/record_links.py")
    ),
)

SEASON_STEPS: tuple[SeasonStep, ...] = (
    SeasonStep("army_movements", "season"),
    SeasonStep("convoys", "season"),
    SeasonStep("supply_flows", "season"),
    SeasonStep("camps", "season_index"),
)
