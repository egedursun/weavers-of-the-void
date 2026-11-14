from collections.abc import Mapping
from dataclasses import dataclass

from aerona.constants.units import PERCENT
from aerona.core.errors import ValidationFailedError
from aerona.db.base import Base
from aerona.db.tables.celestial import WorldRow
from aerona.db.tables.climes import (
    COSMOPOLITAN_FIELDS,
    COSMOPOLITAN_MEMBER_FIELDS,
    MONSOON_FIELDS,
    OSCILLATION_FIELDS,
    WIND_FIELDS,
    WINDOW_FIELDS,
    ClimateOscillationRow,
    CosmopolitanCultureRow,
    CosmopolitanMemberRow,
    LaunchWindowRow,
    MonsoonSeasonRow,
    RegionWindRow,
)
from aerona.domain.enums.mind import ValueAxis
from aerona.engine.climes.crossings import CrossingTally, keep_cultures, keep_windows
from aerona.engine.climes.seasons import SeasonTally, keep_seasons
from aerona.engine.climes.winds import WindTally, keep_winds
from aerona.engine.collective.control import saved
from aerona.engine.context import TickContext
from aerona.engine.cycles.control import node_exists
from aerona.engine.divine.control import apply
from aerona.engine.gatherings.control import Values, allowed, found
from aerona.engine.primitives.numbers import clamp_int


@dataclass(frozen=True)
class Kind:
    table: type[Base]
    fields: tuple[str, ...]
    label: str
    keys: tuple[str, ...]


KINDS: Mapping[str, Kind] = {
    "region_wind": Kind(RegionWindRow, WIND_FIELDS, "prevailing wind", ("region_entity_id",)),
    "monsoon_season": Kind(MonsoonSeasonRow, MONSOON_FIELDS, "monsoon of a year", ("world_id", "epoch")),
    "climate_oscillation": Kind(ClimateOscillationRow, OSCILLATION_FIELDS, "climate oscillation", ("world_id",)),
    "launch_window": Kind(LaunchWindowRow, WINDOW_FIELDS, "launch window", ("from_world_id", "to_world_id")),
    "cosmopolitan_culture": Kind(CosmopolitanCultureRow, COSMOPOLITAN_FIELDS, "culture of a road", ("id",)),
    "cosmopolitan_member": Kind(CosmopolitanMemberRow, COSMOPOLITAN_MEMBER_FIELDS, "member of a culture of a road", ("culture_id", "community_entity_id")),
}
WORLD_KEYS = ("world_id", "from_world_id", "to_world_id")


async def checked(ctx: TickContext, values: Values) -> None:
    for name, value in values.items():
        if value is None or not isinstance(value, int):
            continue
        if name.endswith(("_node_id", "_entity_id")):
            await node_exists(ctx, value, name.removesuffix("_id").replace("_", " "))
        if name in WORLD_KEYS and await ctx.session.get(WorldRow, value) is None:
            raise ValidationFailedError("No such world.")
    culture = values.get("culture_id")
    if isinstance(culture, int) and await ctx.session.get(CosmopolitanCultureRow, culture) is None:
        raise ValidationFailedError("No such culture of a road.")
    if values.get("from_world_id") is not None and values.get("from_world_id") == values.get("to_world_id"):
        raise ValidationFailedError("A window opens between two different worlds.")


def key_of(kind: Kind, keys: Values) -> object:
    picked = tuple(keys[name] for name in kind.keys)
    return picked[0] if len(picked) == 1 else picked


def ordered(name: str, keys: Values) -> Values:
    if name != "launch_window":
        return keys
    first, second = sorted((int(str(keys["from_world_id"])), int(str(keys["to_world_id"]))))
    return {"from_world_id": first, "to_world_id": second}


def ordered_key(name: str, key: object) -> object:
    if name == "launch_window" and isinstance(key, tuple):
        return tuple(sorted(key))
    return key


async def set_record(ctx: TickContext, name: str, keys: Values, values: Values) -> Base:
    kind = KINDS[name]
    keys = ordered(name, keys)
    await checked(ctx, {**keys, **values})
    row = await ctx.session.get(kind.table, key_of(kind, keys)) if "id" not in kind.keys else None
    if row is None:
        row = await saved(ctx, kind.table(**keys, **values, locked=[]))
    else:
        apply(row, allowed(values, kind.fields, kind.label), [])
        await ctx.session.flush()
    return row


async def edit_record(ctx: TickContext, name: str, key: object, values: Values, release: list[str]) -> Base:
    kind = KINDS[name]
    await checked(ctx, values)
    row = apply(await found(ctx, kind.table, ordered_key(name, key), kind.label), allowed(values, kind.fields, kind.label), release)
    await ctx.session.flush()
    return row


async def delete_record(ctx: TickContext, name: str, key: object) -> None:
    kind = KINDS[name]
    await ctx.session.delete(await found(ctx, kind.table, ordered_key(name, key), kind.label))
    await ctx.session.flush()


async def set_value(ctx: TickContext, culture_id: int, axis: ValueAxis, value: int) -> CosmopolitanCultureRow:
    row = await found(ctx, CosmopolitanCultureRow, culture_id, "culture of a road")
    row.values = {**row.values, axis.value: clamp_int(value, -PERCENT, PERCENT)}
    row.locked = sorted({*row.locked, "values"})
    await ctx.session.flush()
    return row


@dataclass
class ClimesRun:
    winds: WindTally
    seasons: SeasonTally


async def run_climes(ctx: TickContext) -> ClimesRun:
    tally = ClimesRun(WindTally(), SeasonTally())
    await keep_winds(ctx, tally.winds)
    await keep_seasons(ctx, tally.seasons)
    return tally


async def run_crossings(ctx: TickContext) -> CrossingTally:
    tally = CrossingTally()
    await keep_windows(ctx, tally)
    await keep_cultures(ctx, tally)
    return tally
