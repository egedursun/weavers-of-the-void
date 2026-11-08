from sqlalchemy import select

from aerona.constants.units import PERCENT
from aerona.db.tables.entities import EntityRow
from aerona.db.write_guard import held
from aerona.domain.enums.bond import BondKind
from aerona.domain.enums.chronicle import ChronicleKind
from aerona.domain.enums.entity import EntityStatus, EntityType
from aerona.domain.enums.mind import ValueAxis
from aerona.domain.enums.society import KnowledgeBranch
from aerona.domain.enums.structure import StructureKind
from aerona.domain.models.entity_stats import SettlementStats
from aerona.engine.body.customs import culture_of, people_of
from aerona.engine.context import TickContext
from aerona.engine.disease.book import COLONY, DiseaseBook
from aerona.engine.disease.course import region_communities
from aerona.engine.interconnect.flows import FlowCategory, flowing
from aerona.engine.notes import note
from aerona.engine.primitives.knowledge import KnowledgeMap
from aerona.engine.primitives.numbers import round_half_up
from aerona.engine.primitives.queries import connect
from aerona.engine.primitives.records import RecordSpec, create_record
from aerona.engine.primitives.stats import headcount_bounds, set_stats, stat
from aerona.engine.structures.construction import Commission, begin

STIGMATISED = 50


async def values_for(ctx: TickContext, community: EntityRow) -> dict[ValueAxis, int]:
    people = await people_of(ctx.session, community)
    return await culture_of(ctx.session, people.id) if people is not None else {}


async def colony_in(ctx: TickContext, region: EntityRow, disease: EntityRow, founder: EntityRow) -> EntityRow:
    found = await ctx.session.scalar(
        select(EntityRow)
        .where(
            EntityRow.entity_type == EntityType.SETTLEMENT,
            EntityRow.status == EntityStatus.CANON,
            EntityRow.subtype == COLONY,
            EntityRow.location_id == region.id,
        )
        .order_by(EntityRow.id)
        .limit(1)
    )
    if found is not None:
        return found
    colony = await create_record(
        ctx,
        RecordSpec(
            entity_type=EntityType.SETTLEMENT,
            name=f"the colony of the sick at {region.name}",
            body=f"Where {founder.name} sent those who caught {disease.name}.",
            stats=SettlementStats(population=0, prosperity=5, defense=0, piety=50),
            power=1,
            location_id=region.id,
            world_id=region.world_id,
            subtype=COLONY,
            pending=False,
        ),
    )
    await connect(ctx.session, colony.id, founder.id, BondKind.DESCENDS_FROM, ctx.epoch, description="cast out of it")
    return colony


async def expel_sick(ctx: TickContext, book: DiseaseBook) -> int:
    table = ctx.rules.epidemiology
    moved = 0
    for outbreak in list(book.outbreaks):
        disease = book.diseases.get(outbreak.disease_entity_id)
        profile = book.profiles.get(outbreak.disease_entity_id)
        region = await ctx.session.get(EntityRow, outbreak.region_entity_id)
        if disease is None or profile is None or region is None or profile.stigma < STIGMATISED:
            continue
        for community in await region_communities(ctx, book, region.id):
            if community.subtype == COLONY or community.entity_type is not EntityType.SETTLEMENT or held(community.id):
                continue
            if (await values_for(ctx, community)).get(ValueAxis.PURITY, 0) < table.stigma_purity:
                continue
            population = stat(community, "population") or 0
            reach = min(1.0, outbreak.infected / max(1, population))
            expelled = round_half_up(population * reach * table.expel_pct / PERCENT)
            floor, _ = headcount_bounds(ctx.rules, community)
            expelled = min(expelled, max(0, population - floor))
            if expelled < table.colony_min:
                continue
            colony = await colony_in(ctx, region, disease, community)
            with flowing(FlowCategory.MIGRATION):
                set_stats(community, population=population - expelled)
                set_stats(colony, population=(stat(colony, "population") or 0) + expelled)
            moved += expelled
            await note(
                ctx,
                f"{community.name} sent {expelled} of its sick away to {colony.name} for fear of {disease.name}.",
                key="disease.expelled",
                ids=[community.id, colony.id, disease.id],
                kind=ChronicleKind.WORLD,
            )
    return moved


async def build_hospitals(ctx: TickContext, book: DiseaseBook) -> int:
    table = ctx.rules.epidemiology
    knowledge = await KnowledgeMap.load(ctx.session)
    built = 0
    for region_id in sorted({outbreak.region_entity_id for outbreak in book.outbreaks} | set(book.endemic)):
        if book.hospitals.get(region_id):
            continue
        for community in await region_communities(ctx, book, region_id):
            if community.entity_type is not EntityType.SETTLEMENT or not knowledge.knows(community.id, KnowledgeBranch.MEDICINE):
                continue
            if (await values_for(ctx, community)).get(ValueAxis.MERCY, 0) < table.hospital_mercy:
                continue
            hospital, _ = await begin(ctx, Commission(site=community, kind=StructureKind.HOSPITAL, name=f"the house of healing of {community.name}"))
            book.hospitals.setdefault(region_id, []).append(hospital)
            built += 1
            await note(
                ctx,
                f"Merciful {community.name} began to build {hospital.name}.",
                key="disease.hospital",
                ids=[community.id, hospital.id],
                kind=ChronicleKind.WORLD,
            )
            break
    return built
