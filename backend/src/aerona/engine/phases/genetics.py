from sqlalchemy import select

from aerona.db.tables.entities import EntityRow
from aerona.db.tables.genetics import AllelePoolRow, GenomeRow
from aerona.db.tables.polity import HouseMemberRow
from aerona.db.write_guard import held
from aerona.domain.enums.entity import EntityStatus, EntityType
from aerona.engine.context import TickContext
from aerona.engine.genetics.genome import genome_of
from aerona.engine.genetics.life import found_genome, refresh_genome
from aerona.engine.genetics.lineage import examine_children, seed_looks, stance_effects, tend_resemblance
from aerona.engine.genetics.pools import members_by_people, seed_pool, tend_pool
from aerona.engine.genetics.widen import W52_FIXUP, widen_loci
from aerona.engine.interconnect.annotations import reads, writes
from aerona.engine.mortal.kin import parents_of
from aerona.engine.phase import Phase
from aerona.engine.polity.laws import LawBook


async def canon(ctx: TickContext, kind: EntityType) -> list[EntityRow]:
    statement = select(EntityRow).where(EntityRow.entity_type == kind, EntityRow.status == EntityStatus.CANON).order_by(EntityRow.id)
    return list(await ctx.session.scalars(statement))


async def ensure_genome(ctx: TickContext, mortal: EntityRow) -> bool:
    if held(mortal.id) or await genome_of(ctx.session, mortal.id) is not None:
        return False
    parents = [parent for parent_id in await parents_of(ctx.session, mortal.id) if (parent := await ctx.session.get(EntityRow, parent_id)) is not None]
    await found_genome(ctx, mortal, parents[:2] if len(parents) >= 2 else ())
    return True


@reads(
    "mortal.beauty",
    "mortal.creativity",
    "mortal.endurance",
    "mortal.perception",
    "mortal.willpower",
    "mortal.wisdom",
    "table.allele_pools",
    "table.applied_fixups",
    "table.bonds",
    "table.entities",
    "table.entity_flags",
    "table.genomes",
    "table.nodes",
    "table.people_biology",
    "table.preferences",
    "table.sense_profiles",
)
@writes("table.allele_pools", "table.applied_fixups", "table.genomes", "table.preferences")
async def genetics_survey(ctx: TickContext) -> None:
    for people in await canon(ctx, EntityType.PEOPLE):
        if held(people.id):
            continue
        pool = await ctx.session.get(AllelePoolRow, people.id)
        if pool is None:
            pool = await seed_pool(ctx, people)
            ctx.count("pools_seeded")
        ctx.count("looks_tastes", await seed_looks(ctx, people, pool))
    for mortal in await canon(ctx, EntityType.MORTAL):
        if await ensure_genome(ctx, mortal):
            ctx.count("genomes_founded")
    pools, genomes = await widen_loci(ctx)
    later_pools, later_genomes = await widen_loci(ctx, W52_FIXUP)
    pools, genomes = pools + later_pools, genomes + later_genomes
    ctx.count("pools_widened", pools)
    ctx.count("genomes_widened", genomes)


@reads(
    "table.afflictions",
    "table.allele_pools",
    "table.bonds",
    "table.cosmos",
    "table.culture_ethics",
    "table.culture_values",
    "table.dimensional_events",
    "table.dimensions",
    "table.divine_wounds",
    "table.entities",
    "table.faction_profiles",
    "table.foreign_gods",
    "table.galactic_structures",
    "table.galaxies",
    "table.galaxy_clusters",
    "table.genomes",
    "table.house_members",
    "table.house_resemblances",
    "table.injuries",
    "table.law_jurisdictions",
    "table.law_profiles",
    "table.mortal_profiles",
    "table.natural_law_profiles",
    "table.natural_laws",
    "table.nodes",
    "table.personality_values",
    "table.polity_members",
    "table.preferences",
    "table.settlement_profiles",
    "table.sons",
    "table.stars",
    "table.world_domain_hooks",
    "table.worlds",
)
@writes(
    "table.allele_pools",
    "table.bonds",
    "table.chronicle",
    "table.chronicle_entities",
    "table.entities",
    "table.genomes",
    "table.house_resemblances",
    "table.incident_facts",
    "table.incident_participants",
    "table.incidents",
    "table.mortal_profiles",
    "table.settlement_profiles",
)
async def bloodlines(ctx: TickContext) -> None:
    laws = await LawBook.load(ctx.session)
    members = await members_by_people(ctx)
    for people in await canon(ctx, EntityType.PEOPLE):
        pool = await ctx.session.get(AllelePoolRow, people.id)
        if pool is None:
            continue
        await tend_pool(ctx, people, pool, members.get(people.id, []), laws)
        ctx.count("gift_stance_felt", await stance_effects(ctx, pool, members.get(people.id, [])))
    pools = {row.people_node_id: row for row in await ctx.session.scalars(select(AllelePoolRow))}
    people_of_mortal = {mortal.id: people_id for people_id, found in members.items() for mortal, _genome in found}
    refreshed = 0
    for mortal, genome in await ctx.session.execute(
        select(EntityRow, GenomeRow)
        .join(GenomeRow, GenomeRow.holder_node_id == EntityRow.id)
        .where(EntityRow.status == EntityStatus.CANON)
        .order_by(EntityRow.id)
    ):
        people_id = people_of_mortal.get(mortal.id)
        await refresh_genome(ctx, mortal, genome, pools.get(people_id) if people_id is not None else None)
        refreshed += 1
    ctx.count("genomes_refreshed", refreshed)
    houses = await canon(ctx, EntityType.HOUSE)
    for house in houses:
        blood: list[EntityRow] = []
        for mortal_id in await ctx.session.scalars(
            select(HouseMemberRow.mortal_entity_id).where(HouseMemberRow.house_entity_id == house.id, HouseMemberRow.by_marriage.is_(False))
        ):
            kin = await ctx.session.get(EntityRow, mortal_id)
            if kin is not None and kin.status is EntityStatus.CANON:
                blood.append(kin)
        if await tend_resemblance(ctx, house, blood):
            ctx.count("house_resemblances")
    ctx.count("gifted_children_taken", await examine_children(ctx))


PHASES = (Phase("genetics_survey", genetics_survey), Phase("bloodlines", bloodlines))
