from collections.abc import Mapping

from sqlalchemy import select

from aerona.catalog.genetics import LOCI
from aerona.db.tables.cosmos import AppliedFixupRow
from aerona.db.tables.demography import PeopleBiologyRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.genetics import AllelePoolRow, GenomeRow
from aerona.db.tables.nature import SenseProfileRow
from aerona.db.write_guard import held
from aerona.domain.enums.entity import EntityStatus, EntityType
from aerona.domain.enums.genetics import Locus
from aerona.engine.body.customs import people_of
from aerona.engine.context import TickContext
from aerona.engine.genetics.genome import draw, pair_of
from aerona.engine.genetics.pools import leaned
from aerona.engine.mortal.kin import parents_of

WIDEN_FIXUP = "genetics.loci_widened"
GENES = "genes"
FREQUENCIES = "frequencies"


def missing_loci(found: Mapping[str, object]) -> list[Locus]:
    return [locus for locus in LOCI if locus.value not in found]


async def widen_pool(ctx: TickContext, people_id: int, pool: AllelePoolRow) -> bool:
    missing = missing_loci(pool.frequencies)
    if not missing or FREQUENCIES in (pool.locked or []) or held(people_id):
        return False
    biology = await ctx.session.get(PeopleBiologyRow, people_id)
    senses = {row.sense: row.acuity for row in await ctx.session.scalars(select(SenseProfileRow).where(SenseProfileRow.holder_entity_id == people_id))}
    rng = ctx.rng(f"genetics.widen_pool.{people_id}")
    pool.frequencies = {**pool.frequencies, **{locus.value: leaned(LOCI[locus], rng, biology, senses) for locus in missing}}
    return True


async def widen_genome(ctx: TickContext, mortal: EntityRow, genome: GenomeRow) -> bool:
    missing = missing_loci(genome.genes)
    if not missing or GENES in (genome.locked or []) or held(mortal.id):
        return False
    rng = ctx.rng(f"genetics.widen_genome.{mortal.id}")
    parents = [found for parent_id in await parents_of(ctx.session, mortal.id) if (found := await ctx.session.get(GenomeRow, parent_id)) is not None]
    people = await people_of(ctx.session, mortal)
    pool = await ctx.session.get(AllelePoolRow, people.id) if people is not None else None
    genes = {key: list(value) for key, value in genome.genes.items()}
    for locus in missing:
        spec = LOCI[locus]
        sources = [parent for parent in parents[:2] if locus.value in parent.genes]
        if len(sources) == 2:
            genes[locus.value] = [rng.pick(list(pair_of(sources[0].genes, locus))), rng.pick(list(pair_of(sources[1].genes, locus)))]
        else:
            frequencies = pool.frequencies if pool is not None else None
            genes[locus.value] = [draw(rng, spec, frequencies), draw(rng, spec, frequencies)]
    genome.genes = genes
    return True


async def widen_loci(ctx: TickContext) -> tuple[int, int]:
    if await ctx.session.get(AppliedFixupRow, WIDEN_FIXUP) is not None:
        return 0, 0
    pools = 0
    for pool in list(await ctx.session.scalars(select(AllelePoolRow).order_by(AllelePoolRow.people_node_id))):
        pools += await widen_pool(ctx, pool.people_node_id, pool)
    genomes = 0
    statement = (
        select(EntityRow, GenomeRow)
        .join(GenomeRow, GenomeRow.holder_node_id == EntityRow.id)
        .where(EntityRow.entity_type == EntityType.MORTAL, EntityRow.status == EntityStatus.CANON)
        .order_by(EntityRow.id)
    )
    for mortal, genome in list(await ctx.session.execute(statement)):
        genomes += await widen_genome(ctx, mortal, genome)
    ctx.session.add(AppliedFixupRow(key=WIDEN_FIXUP, result={"pools": pools, "genomes": genomes}))
    await ctx.session.flush()
    return pools, genomes
