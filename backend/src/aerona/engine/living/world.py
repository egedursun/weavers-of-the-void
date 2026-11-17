from collections import defaultdict

from sqlalchemy import func, select

from aerona.db.tables.bonds import BondRow
from aerona.db.tables.ecology import SpeciesRangeRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.environment import RegionEnvironmentRow
from aerona.db.tables.living import LivingLineRow, LivingLineTraitRow
from aerona.db.write_guard import held
from aerona.domain.enums.bond import BondKind, BondState
from aerona.domain.enums.entity import EntityFlag, EntityStatus, EntityType
from aerona.domain.enums.living import LineTrait
from aerona.domain.enums.modifier import IncidentRole
from aerona.domain.models.entity_stats import PeopleStats
from aerona.engine.context import TickContext
from aerona.engine.primitives.numbers import clamp_percent
from aerona.engine.primitives.queries import add_flag, connect
from aerona.engine.primitives.records import RecordSpec, create_record
from aerona.engine.recording.record import record

PEOPLE_POWER = 8
RISEN_SHARE = 10
SHAPING_TRAITS = frozenset({LineTrait.CLIMATE_TOLERANCE, LineTrait.HARDINESS, LineTrait.YIELD})


async def rise(ctx: TickContext, line: LivingLineRow, species: EntityRow) -> EntityRow:
    counted = await ctx.session.scalar(select(func.sum(SpeciesRangeRow.abundance)).where(SpeciesRangeRow.species_entity_id == species.id))
    people = await create_record(
        ctx,
        RecordSpec(
            entity_type=EntityType.PEOPLE,
            name=f"the folk risen from {species.name}",
            body=f"A people raised to thought from {species.name} by the line {line.name}, in epoch {ctx.epoch}.",
            stats=PeopleStats(population=max(ctx.rules.clones.people_at, int(counted or 0) // RISEN_SHARE)),
            power=PEOPLE_POWER,
            world_id=species.world_id,
            location_id=species.location_id,
        ),
    )
    await connect(ctx.session, people.id, species.id, BondKind.DESCENDS_FROM, ctx.epoch, description="raised to thought by design")
    if line.maker_node_id is not None:
        await connect(ctx.session, line.maker_node_id, people.id, BondKind.PRODUCED, ctx.epoch, description="raised this people to thought")
    await add_flag(ctx.session, species.id, EntityFlag.SPECIES_BECAME_PEOPLE, ctx.epoch)
    await add_flag(ctx.session, people.id, EntityFlag.DESIGNED_PEOPLE, ctx.epoch)
    await record(
        ctx,
        "living.sapience",
        roles={IncidentRole.PRODUCT: people.id, IncidentRole.ORIGIN: species.id, IncidentRole.MAKER: line.maker_node_id},
        facts={"line": line.name},
    )
    return people


async def designed_sapience(ctx: TickContext) -> int:
    risen = 0
    lines = await ctx.session.execute(
        select(LivingLineRow, LivingLineTraitRow)
        .join(LivingLineTraitRow, LivingLineTraitRow.line_id == LivingLineRow.id)
        .where(LivingLineTraitRow.trait == LineTrait.SAPIENCE, LivingLineTraitRow.strength >= ctx.rules.genome_design.sapience_at)
        .order_by(LivingLineRow.id)
    )
    for line, _ in lines.all():
        species = await ctx.session.get(EntityRow, line.species_entity_id) if line.species_entity_id is not None else None
        if species is None or species.status is not EntityStatus.CANON or held(species.id):
            continue
        descended = await ctx.session.scalar(
            select(BondRow.id).where(BondRow.target_node_id == species.id, BondRow.kind == BondKind.DESCENDS_FROM, BondRow.state == BondState.ACTIVE).limit(1)
        )
        if descended is not None:
            continue
        await rise(ctx, line, species)
        risen += 1
    return risen


async def clone_peoples(ctx: TickContext) -> int:
    formed = 0
    by_source: dict[int, list[int]] = defaultdict(list)
    for clone_id, source_id in (
        await ctx.session.execute(
            select(BondRow.source_node_id, BondRow.target_node_id).where(BondRow.kind == BondKind.CLONE_OF, BondRow.state == BondState.ACTIVE)
        )
    ).all():
        by_source[source_id].append(clone_id)
    joined = set(
        await ctx.session.scalars(select(BondRow.source_node_id).where(BondRow.kind == BondKind.MEMBER_OF, BondRow.description == "one of the clone folk"))
    )
    for source_id, clones in sorted(by_source.items()):
        free = [clone for clone in clones if clone not in joined]
        source = await ctx.session.get(EntityRow, source_id)
        if source is None or len(free) < ctx.rules.clones.people_at or held(source_id):
            continue
        people = await create_record(
            ctx,
            RecordSpec(
                entity_type=EntityType.PEOPLE,
                name=f"the folk of {source.name}'s body",
                body=f"The clones grown from {source.name}, become a people of their own.",
                stats=PeopleStats(population=len(free)),
                power=PEOPLE_POWER,
                world_id=source.world_id,
                location_id=source.location_id,
            ),
        )
        await add_flag(ctx.session, people.id, EntityFlag.DESIGNED_PEOPLE, ctx.epoch)
        for clone in free:
            await connect(ctx.session, clone, people.id, BondKind.MEMBER_OF, ctx.epoch, description="one of the clone folk")
        await record(
            ctx,
            "living.clone_people",
            roles={IncidentRole.PRODUCT: people.id, IncidentRole.ORIGIN: source_id, IncidentRole.MEMBER: list(free)},
            facts={"clones": len(free)},
        )
        formed += 1
    return formed


async def shape_lands(ctx: TickContext) -> int:
    shaped = 0
    escaped = await ctx.session.execute(
        select(LivingLineRow.species_entity_id)
        .join(LivingLineTraitRow, LivingLineTraitRow.line_id == LivingLineRow.id)
        .where(LivingLineRow.escaped.is_(True), LivingLineRow.species_entity_id.is_not(None), LivingLineTraitRow.trait.in_(list(SHAPING_TRAITS)))
        .distinct()
    )
    for (species_id,) in escaped.all():
        for region in list(await ctx.session.scalars(select(SpeciesRangeRow.region_entity_id).where(SpeciesRangeRow.species_entity_id == species_id))):
            land = await ctx.session.get(RegionEnvironmentRow, region)
            if land is None or held(region) or "soil_fertility" in (land.locked or []):
                continue
            land.soil_fertility = clamp_percent(land.soil_fertility + ctx.rules.living.decay_fertility)
            shaped += 1
    return shaped
