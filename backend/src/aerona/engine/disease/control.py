from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field

from sqlalchemy import select

from aerona.catalog.transmission import ROUTES
from aerona.constants.units import PERCENT
from aerona.core.errors import NotFoundError, ValidationFailedError
from aerona.db.tables.disease import DiseaseCureRow, DiseaseProfileRow, DiseaseRouteRow, EndemicDiseaseRow, ImmunityRow, OutbreakRow, QuarantineRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.interconnect import IncidentRow
from aerona.db.tables.living import LivingLineRow
from aerona.db.tables.node import NodeRow
from aerona.domain.enums.affliction import Transmission
from aerona.domain.enums.demography import AgeBand
from aerona.domain.enums.disease import ClimateMoisture, ClimateWarmth, CureSource, DiseaseTarget, OutbreakStatus, SpreadPath
from aerona.domain.enums.entity import COMMUNITY_TYPES, EntityStatus, EntityType
from aerona.engine.context import TickContext
from aerona.engine.disease.book import DiseaseBook
from aerona.engine.disease.emergence import ensure_profile, new_disease
from aerona.engine.disease.outbreaks import OUTBREAK_LOCKS
from aerona.engine.ecology.hosts import link_hosts
from aerona.engine.phases.disasters import strike_plague
from aerona.engine.primitives.stats import set_stats

PROFILE_NUMBERS = {
    "virulence": (1, PERCENT),
    "lethality": (1, PERCENT),
    "chronic_rate": (0, PERCENT),
    "incubation": (0, 20),
    "immunity_epochs": (1, 1000),
    "mutation_rate": (0, PERCENT),
    "stigma": (0, PERCENT),
    "cure_level": (0, 20),
    "cold_tolerance": (0, PERCENT),
    "heat_tolerance": (0, PERCENT),
    "resistance": (0, PERCENT),
}
ROUTE_KEY = "primary_route"
PROFILE_CHOICES = {ROUTE_KEY: Transmission, "affinity_warmth": ClimateWarmth, "affinity_moisture": ClimateMoisture}
PROFILE_LINKS = ("host_species_id", "origin_incident_id", "origin_region_id", "designed_line_id", "target_node_id")
TARGETS_KEY = "target_functions"
PROFILE_FIELDS = (*PROFILE_NUMBERS, *PROFILE_CHOICES, TARGETS_KEY, *PROFILE_LINKS)
OUTBREAK_NUMBERS = {"severity": (0, PERCENT), "infected": (0, 10**9), "dead": (0, 10**9)}
ProfileValue = int | str | list[str] | None


@dataclass(frozen=True)
class DiseaseDesign:
    name: str | None = None
    values: Mapping[str, ProfileValue] = field(default_factory=dict)
    hold: bool = True


async def living(ctx: TickContext, entity_id: int, types: frozenset[EntityType], label: str) -> EntityRow:
    entity = await ctx.session.get(EntityRow, entity_id)
    if entity is None or entity.entity_type not in types or entity.status is not EntityStatus.CANON:
        raise NotFoundError(f"No such {label}.")
    return entity


def lock(profile: DiseaseProfileRow, key: str) -> None:
    if key not in profile.locked:
        profile.locked = [*profile.locked, key]


def number(key: str, value: ProfileValue, bounds: tuple[int, int]) -> int:
    low, high = bounds
    if not isinstance(value, int) or isinstance(value, bool) or not low <= value <= high:
        raise ValidationFailedError(f"{key.replace('_', ' ').capitalize()} runs from {low} to {high}.")
    return value


def targets(value: ProfileValue) -> list[str]:
    if not isinstance(value, list) or not value:
        raise ValidationFailedError("A disease must strike at least one body function.")
    try:
        return sorted({DiseaseTarget(str(item)).value for item in value})
    except ValueError as error:
        raise ValidationFailedError(f"{error.args[0] if error.args else value} is not a body function a disease can strike.") from error


async def link(ctx: TickContext, key: str, value: ProfileValue) -> int | None:
    if value is None:
        return None
    if not isinstance(value, int) or isinstance(value, bool):
        raise ValidationFailedError(f"{key.replace('_', ' ').capitalize()} must be a record.")
    if key == "origin_incident_id":
        if await ctx.session.get(IncidentRow, value) is None:
            raise NotFoundError("No such incident.")
        return value
    if key == "designed_line_id":
        if await ctx.session.get(LivingLineRow, value) is None:
            raise NotFoundError("No such living line.")
        return value
    if key == "target_node_id":
        if await ctx.session.get(NodeRow, value) is None:
            raise NotFoundError("No such thing to aim at.")
        return value
    kind = EntityType.SPECIES if key == "host_species_id" else EntityType.REGION
    await living(ctx, value, frozenset({kind}), "species" if kind is EntityType.SPECIES else "land")
    return value


async def apply_value(ctx: TickContext, profile: DiseaseProfileRow, key: str, value: ProfileValue) -> None:
    if key in PROFILE_NUMBERS:
        setattr(profile, key, number(key, value, PROFILE_NUMBERS[key]))
    elif key in PROFILE_CHOICES:
        try:
            setattr(profile, key, PROFILE_CHOICES[key](str(value)))
        except ValueError as error:
            raise ValidationFailedError(f"{value} is not a known {key.replace('_', ' ')}.") from error
        if key == ROUTE_KEY and not ROUTES[profile.primary_route].disease:
            raise ValidationFailedError(f"A sickness cannot pass by {ROUTES[profile.primary_route].label}; that route belongs to afflictions.")
    elif key == TARGETS_KEY:
        profile.target_functions = targets(value)
    elif key in PROFILE_LINKS:
        setattr(profile, key, await link(ctx, key, value))
    else:
        raise ValidationFailedError(f"Unknown disease field: {key}.")


async def shape_profile(ctx: TickContext, profile: DiseaseProfileRow, values: Mapping[str, ProfileValue], *, hold: bool) -> None:
    for key, value in values.items():
        await apply_value(ctx, profile, key, value)
        if hold:
            lock(profile, key)


async def land_of(ctx: TickContext, book: DiseaseBook, target: EntityRow) -> EntityRow:
    region_id = target.id if target.entity_type is EntityType.REGION else book.atlas.top_region(target.id)
    region = await ctx.session.get(EntityRow, region_id) if region_id is not None else None
    if region is None:
        raise ValidationFailedError("A disease needs a land to rise in.")
    return region


async def create_disease(ctx: TickContext, region_id: int, design: DiseaseDesign, *, son_id: int | None) -> EntityRow:
    region = await living(ctx, region_id, frozenset({EntityType.REGION}), "land")
    book = await DiseaseBook.load(ctx.session, ctx.rules, ctx.epoch)
    staged = DiseaseProfileRow(locked=[])
    await shape_profile(ctx, staged, design.values, hold=False)
    host_id = staged.host_species_id
    host = await ctx.session.get(EntityRow, host_id) if host_id is not None else None
    chosen = dict(design.values)

    def shape(profile: DiseaseProfileRow) -> None:
        for key in chosen:
            setattr(profile, key, getattr(staged, key))
        profile.locked = sorted(chosen) if design.hold else []

    disease = await new_disease(ctx, book, region, path=SpreadPath.LOOSED, host=host, son_id=son_id, shape=shape, name=design.name)
    set_stats(disease, virulence=book.profiles[disease.id].virulence, lethality=book.profiles[disease.id].lethality)
    await ctx.session.flush()
    return disease


async def loose(
    ctx: TickContext, target_id: int, *, disease_id: int | None, severity: int, son_id: int | None, design: DiseaseDesign | None = None
) -> tuple[EntityRow, EntityRow]:
    target = await living(ctx, target_id, frozenset({EntityType.REGION, *COMMUNITY_TYPES}), "land or community")
    book = await DiseaseBook.load(ctx.session, ctx.rules, ctx.epoch)
    if disease_id is not None:
        disease = await living(ctx, disease_id, frozenset({EntityType.DISEASE}), "disease")
    elif design is not None:
        disease = await create_disease(ctx, (await land_of(ctx, book, target)).id, design, son_id=son_id)
    else:
        disease = await new_disease(ctx, book, await land_of(ctx, book, target), path=SpreadPath.LOOSED, son_id=son_id, cursed=son_id is not None)
    event, _ = await strike_plague(ctx, target, max(1, min(PERCENT, severity)), disease=disease, path=SpreadPath.LOOSED)
    return disease, event


async def edit_disease(
    ctx: TickContext, disease_id: int, values: Mapping[str, ProfileValue], *, release: Sequence[str] = (), hold: bool = True
) -> DiseaseProfileRow:
    disease = await living(ctx, disease_id, frozenset({EntityType.DISEASE}), "disease")
    profile = await ensure_profile(ctx.session, ctx, disease)
    await shape_profile(ctx, profile, values, hold=hold)
    unknown = [key for key in release if key not in PROFILE_FIELDS]
    if unknown:
        raise ValidationFailedError(f"Unknown disease field: {unknown[0]}.")
    profile.locked = [key for key in profile.locked if key not in release]
    if "host_species_id" in values and profile.host_species_id is not None:
        host = await ctx.session.get(EntityRow, profile.host_species_id)
        await link_hosts(ctx, disease, profile.origin_region_id or disease.location_id or 0, host)
    set_stats(disease, virulence=profile.virulence, lethality=profile.lethality)
    await ctx.session.flush()
    return profile


async def cure(ctx: TickContext, disease_id: int, community_id: int) -> DiseaseCureRow:
    await living(ctx, disease_id, frozenset({EntityType.DISEASE}), "disease")
    await living(ctx, community_id, frozenset(COMMUNITY_TYPES), "community")
    row = await ctx.session.get(DiseaseCureRow, (disease_id, community_id))
    if row is None:
        row = DiseaseCureRow(disease_entity_id=disease_id, community_entity_id=community_id, source=CureSource.GRANTED, since_epoch=ctx.epoch)
        ctx.session.add(row)
    await ctx.session.flush()
    return row


async def revoke_cure(ctx: TickContext, disease_id: int, community_id: int) -> bool:
    row = await ctx.session.get(DiseaseCureRow, (disease_id, community_id))
    if row is None:
        return False
    await ctx.session.delete(row)
    await ctx.session.flush()
    return True


async def quarantine(ctx: TickContext, region_id: int, *, epochs: int | None, son_id: int | None) -> QuarantineRow | None:
    await living(ctx, region_id, frozenset({EntityType.REGION}), "region")
    row = await ctx.session.get(QuarantineRow, region_id)
    if epochs == 0:
        if row is not None:
            await ctx.session.delete(row)
            await ctx.session.flush()
        return None
    span = epochs if epochs is not None else ctx.rules.epidemiology.quarantine_epochs
    if row is None:
        row = QuarantineRow(region_entity_id=region_id, started_epoch=ctx.epoch, until_epoch=ctx.epoch + span, ordered_by_son_id=son_id)
        ctx.session.add(row)
    else:
        row.until_epoch = ctx.epoch + span
    await ctx.session.flush()
    return row


async def grant_immunity(
    ctx: TickContext, community_id: int, disease_id: int, immune_pct: int, *, band: AgeBand | None = None, hold: bool | None = None
) -> int:
    await living(ctx, disease_id, frozenset({EntityType.DISEASE}), "disease")
    await living(ctx, community_id, frozenset(COMMUNITY_TYPES), "community")
    if not 0 <= immune_pct <= PERCENT:
        raise ValidationFailedError(f"Immunity runs from 0 to {PERCENT}.")
    for item in [band] if band is not None else list(AgeBand):
        row = await ctx.session.get(ImmunityRow, (community_id, disease_id, item))
        if row is None:
            row = ImmunityRow(community_entity_id=community_id, disease_entity_id=disease_id, age_band=item, immune_pct=0, since_epoch=ctx.epoch, locked=False)
            ctx.session.add(row)
        row.immune_pct = immune_pct
        row.since_epoch = ctx.epoch
        if hold is not None:
            row.locked = hold
    await ctx.session.flush()
    return immune_pct


async def forget_immunity(ctx: TickContext, community_id: int, disease_id: int, band: AgeBand | None) -> int:
    rows = await ctx.session.scalars(select(ImmunityRow).where(ImmunityRow.community_entity_id == community_id, ImmunityRow.disease_entity_id == disease_id))
    removed = 0
    for row in list(rows):
        if band is None or row.age_band is band:
            await ctx.session.delete(row)
            removed += 1
    await ctx.session.flush()
    return removed


async def end_outbreak(ctx: TickContext, outbreak_id: int) -> OutbreakRow:
    row = await ctx.session.get(OutbreakRow, outbreak_id)
    if row is None:
        raise NotFoundError("No such outbreak.")
    row.status = OutbreakStatus.ENDED
    row.ended_epoch = ctx.epoch
    await ctx.session.flush()
    return row


async def edit_outbreak(
    ctx: TickContext, outbreak_id: int, values: Mapping[str, int | str | bool], *, release: Sequence[str] = (), hold: bool = True
) -> OutbreakRow:
    row = await ctx.session.get(OutbreakRow, outbreak_id)
    if row is None:
        raise NotFoundError("No such outbreak.")
    for key, value in values.items():
        if key in OUTBREAK_NUMBERS:
            setattr(row, key, number(key, value if isinstance(value, int) else None, OUTBREAK_NUMBERS[key]))
        elif key == "status":
            try:
                row.status = OutbreakStatus(str(value))
            except ValueError as error:
                raise ValidationFailedError(f"{value} is not an outbreak state.") from error
            row.ended_epoch = ctx.epoch if row.status is OutbreakStatus.ENDED else None
        elif key == "quarantined":
            row.quarantined = bool(value)
        else:
            raise ValidationFailedError(f"Unknown outbreak field: {key}.")
        if hold and key not in row.locked:
            row.locked = [*row.locked, key]
    unknown = [key for key in release if key not in OUTBREAK_LOCKS]
    if unknown:
        raise ValidationFailedError(f"Unknown outbreak field: {unknown[0]}.")
    row.locked = [key for key in row.locked if key not in release]
    disease = await ctx.session.get(EntityRow, row.disease_entity_id)
    if disease is not None and ("infected" in values or "dead" in values):
        rows = list(await ctx.session.scalars(select(OutbreakRow).where(OutbreakRow.disease_entity_id == disease.id)))
        set_stats(disease, infected=sum(item.infected for item in rows), dead=sum(item.dead for item in rows))
    await ctx.session.flush()
    return row


async def set_endemic(ctx: TickContext, region_id: int, disease_id: int, load: int, *, hold: bool | None) -> EndemicDiseaseRow:
    await living(ctx, region_id, frozenset({EntityType.REGION}), "land")
    await living(ctx, disease_id, frozenset({EntityType.DISEASE}), "disease")
    if not 1 <= load <= PERCENT:
        raise ValidationFailedError(f"An endemic load runs from 1 to {PERCENT}.")
    row = await ctx.session.get(EndemicDiseaseRow, (region_id, disease_id))
    if row is None:
        row = EndemicDiseaseRow(region_entity_id=region_id, disease_entity_id=disease_id, load=load, since_epoch=ctx.epoch, locked=False)
        ctx.session.add(row)
    row.load = load
    if hold is not None:
        row.locked = hold
    await ctx.session.flush()
    return row


async def remove_endemic(ctx: TickContext, region_id: int, disease_id: int) -> bool:
    row = await ctx.session.get(EndemicDiseaseRow, (region_id, disease_id))
    if row is None:
        return False
    await ctx.session.delete(row)
    await ctx.session.flush()
    return True


async def set_route(ctx: TickContext, disease_id: int, route: Transmission, share: int, *, hold: bool | None) -> DiseaseRouteRow:
    await living(ctx, disease_id, frozenset({EntityType.DISEASE}), "disease")
    if not ROUTES[route].disease:
        raise ValidationFailedError(f"A sickness cannot pass by {ROUTES[route].label}; that route belongs to afflictions.")
    if not 1 <= share < PERCENT:
        raise ValidationFailedError(f"A further route carries 1 to {PERCENT - 1} of the spread.")
    profile = await ctx.session.get(DiseaseProfileRow, disease_id)
    if profile is not None and profile.primary_route is route:
        raise ValidationFailedError("That is already the sickness's main route.")
    row = await ctx.session.get(DiseaseRouteRow, (disease_id, route))
    if row is None:
        row = DiseaseRouteRow(disease_entity_id=disease_id, route=route, share=share, locked=[])
        ctx.session.add(row)
    row.share = share
    if hold is not None:
        row.locked = ["share"] if hold else []
    await ctx.session.flush()
    return row


async def remove_route(ctx: TickContext, disease_id: int, route: Transmission) -> bool:
    row = await ctx.session.get(DiseaseRouteRow, (disease_id, route))
    if row is None:
        return False
    await ctx.session.delete(row)
    await ctx.session.flush()
    return True
