from collections import defaultdict
from dataclasses import dataclass

from sqlalchemy import select

from aerona.catalog.evolution import NICHE_BAND, size_band
from aerona.constants.units import PERCENT
from aerona.db.tables.ecology import SpeciesProfileRow, SpeciesRangeRow
from aerona.db.tables.entities import EntityFlagRow, EntityRow
from aerona.db.tables.evolution import SpeciesTraitRow
from aerona.db.write_guard import held
from aerona.domain.enums.ecology import SIZE_ORDER, Diet
from aerona.domain.enums.entity import EntityFlag, EntityType
from aerona.domain.enums.evolution import EvolvedTrait
from aerona.domain.enums.modifier import IncidentRole
from aerona.engine.context import TickContext
from aerona.engine.primitives.distance import RegionAtlas
from aerona.engine.primitives.numbers import clamp_int
from aerona.engine.primitives.queries import canon
from aerona.engine.recording.record import record

NicheKey = tuple[Diet, bool, int, str]
ANY_HABITAT = ""


@dataclass
class NicheTally:
    excluded: int = 0
    displaced: int = 0
    radiated: int = 0


def size_mean(profile: SpeciesProfileRow, row: SpeciesTraitRow | None) -> int:
    if row is not None:
        return row.mean
    return round(SIZE_ORDER.index(profile.size_class) * PERCENT / (len(SIZE_ORDER) - 1))


def habitat_of(profile: SpeciesProfileRow) -> str:
    if not profile.habitat:
        return ANY_HABITAT
    return max(sorted(profile.habitat), key=lambda terrain: profile.habitat[terrain])


def niche_of(profile: SpeciesProfileRow, size: SpeciesTraitRow | None) -> NicheKey:
    return (profile.diet, profile.nocturnal, size_band(size_mean(profile, size)), habitat_of(profile))


@dataclass
class Occupant:
    range: SpeciesRangeRow
    profile: SpeciesProfileRow
    size: SpeciesTraitRow | None

    @property
    def strength(self) -> int:
        return self.range.abundance * self.range.fit


async def occupants(ctx: TickContext) -> dict[int, dict[NicheKey, list[Occupant]]]:
    profiles = {row.species_entity_id: row for row in await ctx.session.scalars(select(SpeciesProfileRow))}
    sizes = {
        (row.species_entity_id, row.region_entity_id): row
        for row in await ctx.session.scalars(select(SpeciesTraitRow).where(SpeciesTraitRow.trait == EvolvedTrait.SIZE))
    }
    living = {row.id for row in await canon(ctx.session, [EntityType.SPECIES])}
    found: dict[int, dict[NicheKey, list[Occupant]]] = defaultdict(lambda: defaultdict(list))
    for row in await ctx.session.scalars(
        select(SpeciesRangeRow).where(SpeciesRangeRow.abundance > 0).order_by(SpeciesRangeRow.region_entity_id, SpeciesRangeRow.species_entity_id)
    ):
        profile = profiles.get(row.species_entity_id)
        if profile is None or row.species_entity_id not in living:
            continue
        size = sizes.get((row.species_entity_id, row.region_entity_id))
        found[row.region_entity_id][niche_of(profile, size)].append(Occupant(row, profile, size))
    return found


async def ranges_of(ctx: TickContext, species_id: int) -> int:
    return len(list(await ctx.session.scalars(select(SpeciesRangeRow.region_entity_id).where(SpeciesRangeRow.species_entity_id == species_id))))


def displace(occupant: Occupant, winner: Occupant, epoch: int) -> bool:
    size = occupant.size
    if size is None or "mean" in size.locked:
        return False
    away = NICHE_BAND if size.mean >= size_mean(winner.profile, winner.size) else -NICHE_BAND
    before = size.mean
    size.mean = clamp_int(size.mean + away, 0, PERCENT)
    size.updated_epoch = epoch
    return size.mean != before


async def exclude(ctx: TickContext, occupant: Occupant, winner: Occupant, tally: NicheTally) -> None:
    table = ctx.rules.niches
    row = occupant.range
    if "abundance" in row.locked:
        return
    row.abundance = clamp_int(row.abundance - table.exclusion_loss, 0, PERCENT)
    row.updated_epoch = ctx.epoch
    if row.abundance >= table.excluded_at or await ranges_of(ctx, row.species_entity_id) <= 1:
        return
    loser = await ctx.session.get(EntityRow, row.species_entity_id)
    region = await ctx.session.get(EntityRow, row.region_entity_id)
    rival = await ctx.session.get(EntityRow, winner.range.species_entity_id)
    await ctx.session.delete(row)
    tally.excluded += 1
    if loser is not None and region is not None and rival is not None:
        await record(
            ctx,
            "ecology.niche_excluded",
            roles={IncidentRole.ACTOR: rival.id, IncidentRole.VICTIM: loser.id, IncidentRole.PLACE: region.id},
            facts={"abundance": row.abundance, "loss": table.exclusion_loss},
            place=region.id,
        )


async def compete(ctx: TickContext, tally: NicheTally) -> None:
    table = ctx.rules.niches
    for region_id, niches in sorted((await occupants(ctx)).items()):
        if held(region_id):
            continue
        for key, sharing in sorted(niches.items(), key=lambda item: (item[0][0].value, item[0][1], item[0][2], item[0][3])):
            if len(sharing) < 2:
                continue
            ranked = sorted(sharing, key=lambda item: (-item.strength, item.range.species_entity_id))
            winner = ranked[0]
            for occupant in ranked[1:]:
                if held(occupant.range.species_entity_id):
                    continue
                rng = ctx.rng(f"niche.{region_id}.{occupant.range.species_entity_id}.{key[2]}")
                if rng.chance(table.displacement_pct) and displace(occupant, winner, ctx.epoch):
                    tally.displaced += 1
                    continue
                await exclude(ctx, occupant, winner, tally)


async def lost_niches(ctx: TickContext) -> list[tuple[EntityRow, SpeciesProfileRow]]:
    since = ctx.epoch - ctx.rules.niches.vacated_window
    found: list[tuple[EntityRow, SpeciesProfileRow]] = []
    for flag in await ctx.session.scalars(
        select(EntityFlagRow).where(EntityFlagRow.flag == EntityFlag.EXTINCT, EntityFlagRow.epoch >= since).order_by(EntityFlagRow.entity_id)
    ):
        species = await ctx.session.get(EntityRow, flag.entity_id)
        profile = await ctx.session.get(SpeciesProfileRow, flag.entity_id)
        if species is not None and profile is not None and species.location_id is not None:
            found.append((species, profile))
    return found


async def radiate(ctx: TickContext, tally: NicheTally) -> None:
    table = ctx.rules.niches
    atlas = await RegionAtlas.load(ctx.session)
    filled = await occupants(ctx)
    for lost, profile in await lost_niches(ctx):
        region_id = atlas.top_region(lost.location_id)
        if region_id is None or held(region_id):
            continue
        key = niche_of(profile, None)
        if filled.get(region_id, {}).get(key):
            continue
        if not ctx.rng(f"radiation.{lost.id}.{region_id}").chance(table.radiation_pct):
            continue
        near = [region_id, *atlas.neighbour_regions(region_id)]
        heirs = sorted(
            (occupant for land in near for niche, rows in filled.get(land, {}).items() if niche[0] is key[0] for occupant in rows),
            key=lambda item: (-item.strength, item.range.species_entity_id, item.range.region_entity_id),
        )
        heir = next((item for item in heirs if not held(item.range.species_entity_id) and item.size is not None and "mean" not in item.size.locked), None)
        if heir is None or heir.size is None:
            continue
        heir.size.mean = clamp_int(key[2] * NICHE_BAND + NICHE_BAND // 2, 0, PERCENT)
        heir.size.updated_epoch = ctx.epoch
        if heir.range.region_entity_id != region_id and await ctx.session.get(SpeciesRangeRow, (heir.range.species_entity_id, region_id)) is None:
            ctx.session.add(
                SpeciesRangeRow(
                    species_entity_id=heir.range.species_entity_id,
                    region_entity_id=region_id,
                    abundance=table.excluded_at * 2,
                    fit=heir.range.fit,
                    since_epoch=ctx.epoch,
                    updated_epoch=ctx.epoch,
                    locked=[],
                )
            )
        species = await ctx.session.get(EntityRow, heir.range.species_entity_id)
        region = await ctx.session.get(EntityRow, region_id)
        tally.radiated += 1
        if species is not None and region is not None:
            await record(
                ctx,
                "ecology.niche_radiation",
                roles={IncidentRole.SUBJECT: species.id, IncidentRole.PREDECESSOR: lost.id, IncidentRole.PLACE: region.id},
                facts={"abundance": table.excluded_at * 2, "fit": heir.range.fit},
                place=region.id,
            )


async def keep_niches(ctx: TickContext, tally: NicheTally) -> None:
    await compete(ctx, tally)
    await ctx.session.flush()
    await radiate(ctx, tally)
