from collections.abc import Mapping
from dataclasses import dataclass, field

from aerona.core.errors import ValidationFailedError
from aerona.db.base import Base
from aerona.db.tables.ecology import SpeciesProfileRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.nature import (
    CULTURE_FIELDS,
    MICROBIOTA_FIELDS,
    RELATION_FIELDS,
    SENSE_FIELDS,
    FermentCultureRow,
    SenseProfileRow,
    SoilMicrobiotaRow,
    SpeciesRelationRow,
)
from aerona.domain.enums.entity import EntityType
from aerona.engine.collective.control import saved
from aerona.engine.context import TickContext
from aerona.engine.cycles.control import node_exists
from aerona.engine.divine.control import apply
from aerona.engine.gatherings.control import Values, allowed, found
from aerona.engine.nature.islands import IslandTally, keep_islands
from aerona.engine.nature.microbes import MicrobeTally, keep_microbes
from aerona.engine.nature.plants import PlantTally, keep_plant_defences
from aerona.engine.nature.senses import SenseTally, seed_senses
from aerona.engine.nature.sleepers import SleeperTally, keep_sleepers
from aerona.engine.nature.symbiosis import SymbiosisTally, keep_symbiosis


@dataclass(frozen=True)
class Kind:
    table: type[Base]
    fields: tuple[str, ...]
    label: str
    keys: tuple[str, ...]


KINDS: Mapping[str, Kind] = {
    "soil_microbiota": Kind(SoilMicrobiotaRow, MICROBIOTA_FIELDS, "life of a soil", ("region_entity_id",)),
    "ferment_culture": Kind(FermentCultureRow, CULTURE_FIELDS, "ferment culture", ("id",)),
    "species_relation": Kind(SpeciesRelationRow, RELATION_FIELDS, "bond between kinds", ("id",)),
    "sense": Kind(SenseProfileRow, SENSE_FIELDS, "sense", ("holder_entity_id", "sense")),
}
STAMPS = {"soil_microbiota": "updated_epoch", "ferment_culture": "since_epoch", "species_relation": "since_epoch"}


async def holds_senses(ctx: TickContext, holder_id: int) -> bool:
    entity = await ctx.session.get(EntityRow, holder_id)
    return entity is not None and (entity.entity_type is EntityType.PEOPLE or await ctx.session.get(SpeciesProfileRow, holder_id) is not None)


async def checked(ctx: TickContext, values: Values) -> None:
    for name, value in values.items():
        if value is not None and isinstance(value, int) and name.endswith(("_node_id", "_entity_id", "_species_id")):
            await node_exists(ctx, value, name.removesuffix("_id").replace("_", " "))
    for name in ("first_species_id", "second_species_id"):
        value = values.get(name)
        if isinstance(value, int) and await ctx.session.get(SpeciesProfileRow, value) is None:
            raise ValidationFailedError("A bond between kinds joins two living kinds.")
    if values.get("first_species_id") is not None and values.get("first_species_id") == values.get("second_species_id"):
        raise ValidationFailedError("A kind cannot be bonded to itself.")
    holder = values.get("holder_entity_id")
    if "sense" in values and isinstance(holder, int) and not await holds_senses(ctx, holder):
        raise ValidationFailedError("Only a kind of creature or a people holds senses.")


def key_of(kind: Kind, keys: Values) -> object:
    picked = tuple(keys[name] for name in kind.keys)
    return picked[0] if len(picked) == 1 else picked


async def set_record(ctx: TickContext, name: str, keys: Values, values: Values) -> Base:
    kind = KINDS[name]
    await checked(ctx, {**keys, **values})
    row = await ctx.session.get(kind.table, key_of(kind, keys)) if "id" not in kind.keys else None
    if row is None:
        stamp = {STAMPS[name]: ctx.epoch} if name in STAMPS else {}
        row = await saved(ctx, kind.table(**keys, **values, **stamp, locked=[]))
    else:
        apply(row, allowed(values, kind.fields, kind.label), [])
        await ctx.session.flush()
    return row


async def edit_record(ctx: TickContext, name: str, key: object, values: Values, release: list[str]) -> Base:
    kind = KINDS[name]
    await checked(ctx, values)
    row = apply(await found(ctx, kind.table, key, kind.label), allowed(values, kind.fields, kind.label), release)
    await ctx.session.flush()
    return row


async def delete_record(ctx: TickContext, name: str, key: object) -> None:
    kind = KINDS[name]
    await ctx.session.delete(await found(ctx, kind.table, key, kind.label))
    await ctx.session.flush()


@dataclass
class NatureRun:
    microbes: MicrobeTally = field(default_factory=MicrobeTally)
    symbiosis: SymbiosisTally = field(default_factory=SymbiosisTally)
    sleepers: SleeperTally = field(default_factory=SleeperTally)
    senses: SenseTally = field(default_factory=SenseTally)
    plants: PlantTally = field(default_factory=PlantTally)
    islands: IslandTally = field(default_factory=IslandTally)


async def keep_nature(ctx: TickContext, tally: NatureRun) -> None:
    await keep_microbes(ctx, tally.microbes)
    await seed_senses(ctx, tally.senses)
    await keep_symbiosis(ctx, tally.symbiosis)
    await keep_sleepers(ctx, tally.sleepers)
    await keep_plant_defences(ctx, tally.plants)
    await keep_islands(ctx, tally.islands)


async def run_nature(ctx: TickContext) -> NatureRun:
    tally = NatureRun()
    await keep_nature(ctx, tally)
    return tally
