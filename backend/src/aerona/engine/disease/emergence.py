from sqlalchemy.ext.asyncio import AsyncSession

from aerona.catalog.diseases import CLIMATE_WORDS, STRAIN_WORDS, VECTOR_FUNCTIONS, VECTOR_NOUNS, VECTOR_STIGMA
from aerona.constants.units import PERCENT
from aerona.core.random import SeededRandom
from aerona.db.tables.disease import DiseaseProfileRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.environment import RegionEnvironmentRow
from aerona.domain.enums.bond import BondKind
from aerona.domain.enums.disease import ClimateAffinity, DiseaseVector, SpreadPath
from aerona.domain.enums.entity import EntityType
from aerona.domain.enums.environment import TemperatureBand
from aerona.domain.models.entity_stats import DiseaseStats
from aerona.engine.context import TickContext
from aerona.engine.disease.book import DiseaseBook
from aerona.engine.primitives.numbers import clamp_int
from aerona.engine.primitives.queries import connect
from aerona.engine.primitives.records import RecordSpec, create_record

WARM_BANDS = frozenset({TemperatureBand.WARM, TemperatureBand.HOT, TemperatureBand.SEARING})
COLD_BANDS = frozenset({TemperatureBand.FROZEN, TemperatureBand.COLD})
WET = 40
DRY = 20
MAGIC = 60
VOID_SCARS = ("void", "void_wound", "unmade")


def affinity_of(ground: RegionEnvironmentRow | None) -> ClimateAffinity:
    if ground is None:
        return ClimateAffinity.ANY
    if ground.wetland >= WET or ground.rainfall >= PERCENT - DRY:
        return ClimateAffinity.WET
    if ground.temperature_band in WARM_BANDS:
        return ClimateAffinity.WARM
    if ground.temperature_band in COLD_BANDS:
        return ClimateAffinity.COLD
    if ground.rainfall <= DRY:
        return ClimateAffinity.DRY
    return ClimateAffinity.ANY


def vector_of(rng: SeededRandom, ground: RegionEnvironmentRow | None, *, host: EntityRow | None, cursed: bool) -> DiseaseVector:
    if cursed:
        return DiseaseVector.CURSE
    if ground is not None and any(ground.scars.get(key, 0) for key in VOID_SCARS):
        return DiseaseVector.VOID
    if ground is not None and ground.magic_density >= MAGIC and rng.chance(40):
        return DiseaseVector.SPIRIT
    if host is not None:
        return DiseaseVector.BITE if rng.chance(60) else DiseaseVector.TOUCH
    if ground is not None and ground.wetland >= WET:
        return rng.pick([DiseaseVector.WATER, DiseaseVector.BITE])
    return rng.pick([DiseaseVector.AIR, DiseaseVector.AIR, DiseaseVector.TOUCH, DiseaseVector.WATER])


def name_of(rng: SeededRandom, vector: DiseaseVector, affinity: ClimateAffinity, region: EntityRow | None) -> str:
    noun = rng.pick(VECTOR_NOUNS[vector])
    word = rng.pick(CLIMATE_WORDS[affinity])
    place = f" of {region.name}" if region is not None and rng.chance(50) else ""
    return f"the {word} {noun}{place}"


def fresh_profile(ctx: TickContext, rng: SeededRandom, ground: RegionEnvironmentRow | None, *, host: EntityRow | None, cursed: bool) -> DiseaseProfileRow:
    vector = vector_of(rng, ground, host=host, cursed=cursed)
    affinity = affinity_of(ground)
    return DiseaseProfileRow(
        vector=vector,
        virulence=rng.integer(20, 70),
        lethality=rng.integer(10, 55),
        chronic_rate=rng.integer(0, 30),
        incubation=rng.integer(0, 3),
        target_functions=[item.value for item in VECTOR_FUNCTIONS[vector]],
        climate_affinity=affinity,
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
        vector=parent.vector,
        virulence=clamp_int(parent.virulence + rng.integer(-5, 15), 1, PERCENT),
        lethality=clamp_int(parent.lethality + rng.integer(-15, 10), 1, PERCENT),
        chronic_rate=parent.chronic_rate,
        incubation=parent.incubation,
        target_functions=list(parent.target_functions),
        climate_affinity=parent.climate_affinity,
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


async def birth_disease(
    ctx: TickContext, book: DiseaseBook, profile: DiseaseProfileRow, *, region: EntityRow, path: SpreadPath, name: str, son_id: int | None = None
) -> EntityRow:
    entity = await create_record(
        ctx,
        RecordSpec(
            entity_type=EntityType.DISEASE,
            name=name,
            body=f"A sickness that first showed itself in {region.name}, carried by {profile.vector.value}.",
            stats=DiseaseStats(virulence=profile.virulence, lethality=profile.lethality, infected=0, dead=0),
            power=max(1, profile.lethality // 10),
            location_id=region.id,
            world_id=region.world_id,
            subtype=profile.vector.value,
            creator_son_id=son_id,
            pending=False,
        ),
    )
    profile.disease_entity_id = entity.id
    profile.origin_region_id = region.id
    ctx.session.add(profile)
    if profile.parent_disease_id is not None:
        await connect(ctx.session, entity.id, profile.parent_disease_id, BondKind.DESCENDS_FROM, ctx.epoch, description="a new strain")
    await ctx.session.flush()
    book.diseases[entity.id] = entity
    book.profiles[entity.id] = profile
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
) -> EntityRow:
    ground = await ctx.session.get(RegionEnvironmentRow, region.id)
    rng = ctx.rng(f"disease.new.{region.id}.{path.value}.{len(book.diseases)}")
    profile = fresh_profile(ctx, rng, ground, host=host, cursed=cursed)
    return await birth_disease(ctx, book, profile, region=region, path=path, name=name_of(rng, profile.vector, profile.climate_affinity, region), son_id=son_id)


async def new_strain(ctx: TickContext, book: DiseaseBook, parent: EntityRow, region: EntityRow) -> EntityRow | None:
    profile = book.profiles.get(parent.id)
    if profile is None:
        return None
    rng = ctx.rng(f"disease.strain.{parent.id}.{ctx.epoch}")
    child = strain_profile(ctx, rng, profile)
    name = f"the {rng.pick(STRAIN_WORDS)} {plain(parent.name)}"
    return await birth_disease(ctx, book, child, region=region, path=SpreadPath.MUTATION, name=name, son_id=parent.creator_son_id)


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
