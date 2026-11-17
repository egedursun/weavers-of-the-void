from collections.abc import Mapping
from typing import Any

from aerona.catalog.genetics import LOCI, LOCUS_GROUP_LABELS
from aerona.domain.enums.genetics import LocusGroup
from aerona.engine.genetics.genome import pair_of, phenotype


def genome_text(value: Mapping[str, Any]) -> str:
    genes = {key: list(items) for key, items in value.items() if isinstance(items, list)}
    groups: dict[LocusGroup, list[str]] = {}
    for locus, spec in LOCI.items():
        if locus.value not in genes:
            continue
        first, second = pair_of(genes, locus)
        shown = spec.allele(phenotype(genes, locus)).label
        carried = ", ".join(spec.allele(key).label for key in dict.fromkeys((first, second)) if spec.allele(key).label != shown)
        groups.setdefault(spec.group, []).append(f"{spec.label}: {shown}" + (f" (carries {carried})" if carried else ""))
    return " | ".join(f"{LOCUS_GROUP_LABELS[group]}: {'; '.join(lines)}" for group, lines in groups.items())
