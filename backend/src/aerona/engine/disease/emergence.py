from collections.abc import Callable

from sqlalchemy.ext.asyncio import AsyncSession

from aerona.catalog.diseases import VECTOR_FUNCTIONS, VECTOR_LABELS, VECTOR_STIGMA
from aerona.constants.units import PERCENT
from aerona.core.grammar import spoken
from aerona.core.random import SeededRandom
from aerona.db.tables.disease import DiseaseProfileRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.environment import RegionEnvironmentRow
from aerona.domain.enums.affliction import Transmission
from aerona.domain.enums.bond import BondKind
from aerona.domain.enums.disease import ClimateMoisture, ClimateWarmth, SpreadPath
from aerona.domain.enums.entity import EntityType
from aerona.domain.enums.environment import TemperatureBand
from aerona.domain.enums.modifier import IncidentRole
from aerona.domain.models.entity_stats import DiseaseStats
from aerona.engine.context import TickContext
from aerona.engine.disease.book import DiseaseBook
from aerona.engine.disease.routes import seed_routes
from aerona.engine.ecology.hosts import link_hosts
from aerona.engine.primitives.numbers import clamp_int
from aerona.engine.primitives.queries import connect
from aerona.engine.primitives.records import RecordSpec, create_record
from aerona.engine.recording.record import FactInput, RoleValue, record

WARM_BANDS = frozenset({TemperatureBand.WARM, TemperatureBand.HOT, TemperatureBand.SEARING})
COLD_BANDS = frozenset({TemperatureBand.FROZEN, TemperatureBand.COLD})
WET = 40
DRY = 20
MAGIC = 60
VOID_SCARS = ("void", "void_wound", "unmade")


def affinity_of(ground: RegionEnvironmentRow | None) -> tuple[ClimateWarmth, ClimateMoisture]:
    if ground is None:
        return ClimateWarmth.ANY, ClimateMoisture.ANY
    warmth = ClimateWarmth.WARM if ground.temperature_band in WARM_BANDS else ClimateWarmth.COLD if ground.temperature_band in COLD_BANDS else ClimateWarmth.ANY
    moisture = ClimateMoisture.WET if ground.wetland >= WET else ClimateMoisture.DRY if ground.rainfall <= DRY else ClimateMoisture.ANY
    return warmth, moisture


def vector_of(rng: SeededRandom, ground: RegionEnvironmentRow | None, *, host: EntityRow | None, cursed: bool) -> Transmission:
    if cursed:
        return Transmission.CURSE
    if ground is not None and any(ground.scars.get(key, 0) for key in VOID_SCARS):
        return Transmission.VOID
    if ground is not None and ground.magic_density >= MAGIC and rng.chance(40):
        return Transmission.SPIRIT
    if host is not None:
        return Transmission.BITE if rng.chance(60) else Transmission.CONTACT
    if ground is not None and ground.wetland >= WET:
        return rng.pick([Transmission.WATER, Transmission.BITE])
    return rng.pick([Transmission.INHALATION, Transmission.INHALATION, Transmission.CONTACT, Transmission.WATER])


def name_of(vector: Transmission, region: EntityRow | None) -> str:
    place = f" of {region.name}" if region is not None else ""
    return f"the {VECTOR_LABELS[vector]} sickness{place}"


def fresh_profile(ctx: TickContext, rng: SeededRandom, ground: RegionEnvironmentRow | None, *, host: EntityRow | None, cursed: bool) -> DiseaseProfileRow:
    vector = vector_of(rng, ground, host=host, cursed=cursed)
    warmth, moisture = affinity_of(ground)
    return DiseaseProfileRow(
        primary_route=vector,
        virulence=rng.integer(20, 70),
        lethality=rng.integer(10, 55),
        chronic_rate=rng.integer(0, 30),
        incubation=rng.integer(0, 3),
        target_functions=[item.value for item in VECTOR_FUNCTIONS[vector]],
        affinity_warmth=warmth,
        affinity_moisture=moisture,
        host_species_id=host.id if host is not None else None,
        immunity_epochs=rng.integer(2, 12),
        mutation_rate=rng.integer(2, 20),
        stigma=clamp_int(VECTOR_STIGMA[vector] + rng.integer(-15, 15), 0, PERCENT),
        cure_level=rng.integer(2, 6),
        emerged_epoch=ctx.epoch,
        locked=[],
    )


def strain_profile(ctx: TickContext, rng: SeededRandom, parent: DiseaseProfileRow) -> DiseaseProfileRow:
    return DiseaseProfileRow(
        primary_route=parent.primary_route,
        virulence=clamp_int(parent.virulence + rng.integer(-5, 15), 1, PERCENT),
        lethality=clamp_int(parent.lethality + rng.integer(-15, 10), 1, PERCENT),
        chronic_rate=parent.chronic_rate,
        incubation=parent.incubation,
        target_functions=list(parent.target_functions),
        affinity_warmth=parent.affinity_warmth,
        affinity_moisture=parent.affinity_moisture,
        host_species_id=parent.host_species_id,
        immunity_epochs=parent.immunity_epochs,
        mutation_rate=parent.mutation_rate,
        parent_disease_id=parent.disease_entity_id,
        generation=parent.generation + 1,
        stigma=parent.stigma,
        cure_level=parent.cure_level + (1 if rng.chance(50) else 0),
        emerged_epoch=ctx.epoch,
        locked=[],
    )


ORIGIN_KEYS = {
    (True, False): "disease.loosed",
    (True, True): "disease.loosed_host",
    (False, False): "disease.emerged",
    (False, True): "disease.emerged_host",
}


async def mark_origin(ctx: TickContext, profile: DiseaseProfileRow, entity: EntityRow, region: EntityRow, *, path: SpreadPath, son_id: int | None) -> None:
    host = await ctx.session.get(EntityRow, profile.host_species_id) if profile.host_species_id is not None else None
    key = ORIGIN_KEYS[(path is SpreadPath.LOOSED, host is not None)]
    roles: dict[IncidentRole, RoleValue] = {
        IncidentRole.SUBJECT: entity.id,
        IncidentRole.PLACE: region.id,
        IncidentRole.ORIGIN: host.id if host else None,
        IncidentRole.PATRON: son_id,
    }
    facts: dict[str, FactInput] = {"route": profile.primary_route, "path": path, "lethality": profile.lethality}
    write = await record(ctx, key, roles=roles, facts=facts, place=region.id, son_id=son_id, world_id=region.world_id)
    profile.origin_incident_id = write.incident_id


async def birth_disease(
    ctx: TickContext,
    book: DiseaseBook,
    profile: DiseaseProfileRow,
    *,
    region: EntityRow,
    path: SpreadPath,
    name: str,
    son_id: int | None = None,
    quiet: bool = False,
) -> EntityRow:
    entity = await create_record(
        ctx,
        RecordSpec(
            entity_type=EntityType.DISEASE,
            name=name,
            body=f"A sickness that first showed itself in {region.name}, carried by {spoken(profile.primary_route)}.",
            stats=DiseaseStats(virulence=profile.virulence, lethality=profile.lethality, infected=0, dead=0),
            power=max(1, profile.lethality // 10),
            location_id=region.id,
            world_id=region.world_id,
            subtype=profile.primary_route.value,
            creator_son_id=son_id,
            pending=False,
        ),
    )
    profile.disease_entity_id = entity.id
    profile.origin_region_id = region.id
    ctx.session.add(profile)
    seed_routes(ctx, book, entity, profile)
    if profile.parent_disease_id is not None:
        await connect(ctx.session, entity.id, profile.parent_disease_id, BondKind.DESCENDS_FROM, ctx.epoch, description="a new strain")
    await ctx.session.flush()
    book.diseases[entity.id] = entity
    book.profiles[entity.id] = profile
    if profile.host_species_id is not None:
        book.hosts.setdefault(entity.id, set()).add(profile.host_species_id)
    if not quiet:
        await mark_origin(ctx, profile, entity, region, path=path, son_id=son_id)
    ctx.count(f"disease.born.{path.value}")
    return entity


async def new_disease(
    ctx: TickContext,
    book: DiseaseBook,
    region: EntityRow,
    *,
    path: SpreadPath,
    host: EntityRow | None = None,
    son_id: int | None = None,
    cursed: bool = False,
    shape: Callable[[DiseaseProfileRow], None] | None = None,
    name: str | None = None,
    quiet: bool = False,
) -> EntityRow:
    ground = await ctx.session.get(RegionEnvironmentRow, region.id)
    rng = ctx.rng(f"disease.new.{region.id}.{path.value}.{len(book.diseases)}")
    profile = fresh_profile(ctx, rng, ground, host=host, cursed=cursed)
    if shape is not None:
        shape(profile)
    title = name or name_of(profile.primary_route, region)
    disease = await birth_disease(ctx, book, profile, region=region, path=path, name=title, son_id=son_id, quiet=quiet)
    ctx.count("disease_hosts", await link_hosts(ctx, disease, region.id, host))
    return disease


async def new_strain(ctx: TickContext, book: DiseaseBook, parent: EntityRow, region: EntityRow) -> EntityRow | None:
    profile = book.profiles.get(parent.id)
    if profile is None:
        return None
    rng = ctx.rng(f"disease.strain.{parent.id}.{ctx.epoch}")
    child = strain_profile(ctx, rng, profile)
    kin = sum(1 for row in book.profiles.values() if row.parent_disease_id == parent.id)
    name = f"{plain(parent.name)}, strain {kin + 2}"
    return await birth_disease(ctx, book, child, region=region, path=SpreadPath.MUTATION, name=name, son_id=parent.creator_son_id, quiet=True)


def plain(name: str) -> str:
    return name[4:] if name.lower().startswith("the ") else name


async def ensure_profile(session: AsyncSession, ctx: TickContext, disease: EntityRow) -> DiseaseProfileRow:
    found = await session.get(DiseaseProfileRow, disease.id)
    if found is not None:
        return found
    region = await session.get(RegionEnvironmentRow, disease.location_id) if disease.location_id is not None else None
    profile = fresh_profile(ctx, ctx.rng(f"disease.profile.{disease.id}"), region, host=None, cursed=False)
    profile.disease_entity_id = disease.id
    profile.origin_region_id = disease.location_id
    session.add(profile)
    await session.flush()
    return profile
