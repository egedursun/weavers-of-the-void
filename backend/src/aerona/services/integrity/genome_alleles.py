from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.catalog.genetics import LOCI
from aerona.db.tables.genetics import GenomeRow
from aerona.domain.enums.genetics import Locus

KNOWN = {locus.value: set(spec.keys) for locus, spec in LOCI.items()}


def stray(genes: dict[str, list[str]]) -> bool:
    return any(key in KNOWN and any(allele not in KNOWN[key] for allele in pair) for key, pair in genes.items())


async def stray_alleles(session: AsyncSession) -> list[int]:
    rows = await session.execute(select(GenomeRow.holder_node_id, GenomeRow.genes).order_by(GenomeRow.holder_node_id))
    return [holder for holder, genes in rows.all() if stray(genes)]


async def mend_alleles(session: AsyncSession, holder_id: int) -> None:
    genome = await session.get(GenomeRow, holder_id)
    if genome is None:
        return
    mended: dict[str, list[str]] = {}
    for key, pair in genome.genes.items():
        if key not in KNOWN:
            mended[key] = list(pair)
            continue
        common = LOCI[Locus(key)].common.key
        mended[key] = [allele if allele in KNOWN[key] else common for allele in pair]
    genome.genes = mended
