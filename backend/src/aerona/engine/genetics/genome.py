from collections.abc import Mapping

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.catalog.effect_packages import PACKAGES
from aerona.catalog.genetic_effects import ATTRIBUTE_WORDS, EFFECT_POINTS, EFFECT_SCALES, GENETIC_EFFECT_LABELS, LOCUS_EFFECTS, STAT_WORDS
from aerona.catalog.genetics import GIFT_LOCI_ORDER, HARMFUL, LOCI, LOOKS_LOCI, SCHOOL_OF_LOCUS, VISIBLE_LOCI, LocusSpec
from aerona.catalog.mind import SKILLS
from aerona.constants.units import PERCENT
from aerona.core.random import SeededRandom
from aerona.db.tables.afflictions import AfflictionRow
from aerona.db.tables.body import InjuryRow
from aerona.db.tables.genetics import GenomeRow
from aerona.domain.enums.body import InjuryKind, InjuryState
from aerona.domain.enums.culture import MagicSchool
from aerona.domain.enums.genetics import GeneticEffect, Locus
from aerona.domain.enums.living import LineTrait
from aerona.domain.enums.mind import Attribute, SkillKind, TraitKind
from aerona.engine.body.marks import marked
from aerona.engine.mortal.kin import parents_of
from aerona.engine.primitives.numbers import clamp_int, round_half_up
from aerona.rules.registry import Rules

Genes = dict[str, list[str]]
Pool = Mapping[str, Mapping[str, int]]
MISSING_KINDS = frozenset({InjuryKind.SEVERED, InjuryKind.GOUGED, InjuryKind.DESTROYED})
PAIR = 2


def pair_of(genes: Mapping[str, list[str]], locus: Locus) -> tuple[str, str]:
    spec = LOCI[locus]
    found = genes.get(locus.value) or []
    first = found[0] if found and found[0] in spec.keys else spec.common.key
    second = found[1] if len(found) >= PAIR and found[1] in spec.keys else first
    return first, second


def phenotype(genes: Mapping[str, list[str]], locus: Locus) -> str:
    spec = LOCI[locus]
    first, second = pair_of(genes, locus)
    if spec.graded:
        mean = round_half_up((spec.allele(first).score + spec.allele(second).score) / PAIR)
        return min(spec.alleles, key=lambda allele: (abs(allele.score - mean), allele.score)).key
    return max((first, second), key=lambda key: (spec.allele(key).dominance, -spec.keys.index(key)))


def weights(spec: LocusSpec, pool: Pool | None) -> list[tuple[str, int]]:
    found = (pool or {}).get(spec.locus.value) or {}
    drawn = [(allele.key, int(found.get(allele.key, allele.weight))) for allele in spec.alleles]
    return drawn if sum(weight for _key, weight in drawn) > 0 else [(allele.key, max(1, allele.weight)) for allele in spec.alleles]


def draw(rng: SeededRandom, spec: LocusSpec, pool: Pool | None) -> str:
    options = weights(spec, pool)
    roll = rng.random() * sum(weight for _key, weight in options)
    for key, weight in options:
        roll -= weight
        if roll < 0:
            return key
    return options[-1][0]


def drawn_genes(rng: SeededRandom, pool: Pool | None) -> Genes:
    return {locus.value: [draw(rng, spec, pool), draw(rng, spec, pool)] for locus, spec in LOCI.items()}


def inherited_genes(rules: Rules, rng: SeededRandom, first: Mapping[str, list[str]], second: Mapping[str, list[str]], inbreeding: int) -> Genes:
    table = rules.genetics
    genes: Genes = {}
    for locus, spec in LOCI.items():
        mine = list(pair_of(first, locus))
        theirs = list(pair_of(second, locus))
        child = [mine[0] if rng.random() < 0.5 else mine[1], theirs[0] if rng.random() < 0.5 else theirs[1]]
        harmful = HARMFUL.get(locus)
        carried = harmful is not None and (harmful in mine or harmful in theirs)
        if carried and harmful is not None and rng.chance(inbreeding * table.condition_pct / PERCENT):
            child = [harmful, harmful]
        for index in range(PAIR):
            if rng.chance(table.mutation_pct):
                child[index] = rng.pick(list(spec.keys))
        genes[locus.value] = child
    return genes


def aptitude(rules: Rules, genes: Mapping[str, list[str]], school: MagicSchool) -> int:
    table = rules.gift
    first, second = pair_of(genes, next(locus for locus in GIFT_LOCI_ORDER if SCHOOL_OF_LOCUS[locus] is school))
    if "wild" in (first, second):
        return table.wild_aptitude
    if first == second == "gifted":
        return table.gifted_aptitude
    if "gifted" in (first, second):
        return table.carrier_aptitude
    return 0


def aptitudes(rules: Rules, genes: Mapping[str, list[str]]) -> dict[MagicSchool, int]:
    found = {school: aptitude(rules, genes, school) for school in MagicSchool}
    return {school: value for school, value in found.items() if value > 0}


def gifted_schools(rules: Rules, genes: Mapping[str, list[str]]) -> list[MagicSchool]:
    return [school for school, value in aptitudes(rules, genes).items() if value >= rules.gift.gifted_at]


def looks_labels(genes: Mapping[str, list[str]]) -> list[str]:
    return [LOCI[locus].allele(phenotype(genes, locus)).label for locus in LOOKS_LOCI]


def blood_labels(genes: Mapping[str, list[str]]) -> list[str]:
    shown: list[str] = []
    for locus in VISIBLE_LOCI:
        spec = LOCI[locus]
        if spec.locus in LOOKS_LOCI:
            continue
        allele = spec.allele(phenotype(genes, locus))
        if allele.score:
            shown.append(allele.label)
    return shown


def appearance_text(genes: Mapping[str, list[str]], marks: list[str]) -> str:
    parts = [*looks_labels(genes), *blood_labels(genes), *marks]
    return ", ".join(parts)


def score_of(genes: Mapping[str, list[str]], locus: Locus) -> int:
    return LOCI[locus].allele(phenotype(genes, locus)).score


async def genome_of(session: AsyncSession, holder_id: int | None) -> GenomeRow | None:
    return await session.get(GenomeRow, holder_id) if holder_id is not None else None


async def consanguinity(session: AsyncSession, rules: Rules, first_id: int, second_id: int) -> int:
    table = rules.genetics
    first_parents, second_parents = set(await parents_of(session, first_id)), set(await parents_of(session, second_id))
    shared = len(first_parents & second_parents)
    if shared >= PAIR:
        blood = table.sibling_blood_pct
    elif shared:
        blood = table.half_blood_pct
    else:
        first_grand = {grand for parent in first_parents for grand in await parents_of(session, parent)}
        second_grand = {grand for parent in second_parents for grand in await parents_of(session, parent)}
        blood = table.cousin_blood_pct if first_grand & second_grand else 0
    if first_id in second_parents or second_id in first_parents:
        blood = max(blood, table.sibling_blood_pct)
    owned = [genome.inbreeding for genome in (await genome_of(session, first_id), await genome_of(session, second_id)) if genome is not None]
    carried = round_half_up(sum(owned) / PAIR * table.inherited_inbreeding_pct / PERCENT) if owned else 0
    return clamp_int(blood + carried, 0, PERCENT)


def potential_of(rules: Rules, rng: SeededRandom, first: Mapping[str, int], second: Mapping[str, int], fallback: Mapping[str, int]) -> dict[str, int]:
    deviation = rules.genetics.potential_deviation
    middle = PERCENT // PAIR
    return {
        member.value: clamp_int(
            (first.get(member.value, fallback.get(member.value, middle)) + second.get(member.value, fallback.get(member.value, middle))) / PAIR
            + rng.integer(-deviation, deviation),
            0,
            PERCENT,
        )
        for member in Attribute
    }


async def body_marks(session: AsyncSession, holder_id: int) -> tuple[int, int]:
    rows = list(await session.scalars(select(InjuryRow).where(InjuryRow.bearer_node_id == holder_id, InjuryRow.visible.is_(True), marked())))
    missing = sum(1 for row in rows if row.kind in MISSING_KINDS)
    scars = sum(1 for row in rows if row.state is InjuryState.HEALED_SCAR and row.kind not in MISSING_KINDS)
    return scars, missing


async def affliction_marks(session: AsyncSession, holder_id: int) -> list[str]:
    marks: list[str] = []
    rows = await session.scalars(select(AfflictionRow).where(AfflictionRow.bearer_node_id == holder_id, AfflictionRow.cured_epoch.is_(None)))
    for row in rows:
        spec = PACKAGES[row.package]
        stage = spec.stages[min(row.stage, len(spec.stages) - 1)]
        if stage.appearance:
            marks.append(stage.appearance)
    return marks


def rare_visible(rules: Rules, genes: Mapping[str, list[str]], pool: Pool | None) -> int:
    rare = 0
    for locus in VISIBLE_LOCI:
        allele = phenotype(genes, locus)
        share = dict(weights(LOCI[locus], pool)).get(allele, 0)
        total = sum(weight for _key, weight in weights(LOCI[locus], pool)) or 1
        if share * PERCENT / total < rules.genetics.rare_allele_pct:
            rare += 1
    return rare


def likeness(genes: Mapping[str, list[str]], other: Mapping[str, list[str]]) -> int:
    same = sum(1 for locus in VISIBLE_LOCI if phenotype(genes, locus) == phenotype(other, locus))
    return round_half_up(same * PERCENT / max(1, len(VISIBLE_LOCI)))


def effect_steps(genes: Mapping[str, list[str]], channel: GeneticEffect) -> int:
    return sum(score_of(genes, locus) * spec.effects[channel] for locus, spec in LOCUS_EFFECTS.items() if channel in spec.effects)


def effect_pct(rules: Rules, genes: Mapping[str, list[str]], channel: GeneticEffect) -> int:
    return effect_steps(genes, channel) * EFFECT_SCALES[channel](rules)


def effect_factor(rules: Rules, genome: GenomeRow | None, channel: GeneticEffect) -> float:
    return 1.0 if genome is None else max(0.0, 1 + effect_pct(rules, genome.genes, channel) / PERCENT)


def learning_factor(rules: Rules, genome: GenomeRow | None, skill: SkillKind) -> float:
    if genome is None:
        return 1.0
    share = sum(score_of(genome.genes, locus) * spec.skills[skill] for locus, spec in LOCUS_EFFECTS.items() if skill in spec.skills)
    return max(0.0, 1 + share * rules.genetics.learning_pct / PERCENT / PERCENT)


def stat_shifts(rules: Rules, genes: Mapping[str, list[str]]) -> dict[str, int]:
    shifts: dict[str, int] = {}
    for locus, spec in LOCUS_EFFECTS.items():
        score = score_of(genes, locus)
        for key, points in spec.stats.items():
            shifts[key] = shifts.get(key, 0) + score * points
    return {key: round_half_up(value * rules.genetics.stat_step_pct / PERCENT) for key, value in shifts.items() if value}


def attribute_shifts(rules: Rules, genes: Mapping[str, list[str]]) -> dict[Attribute, int]:
    shifts: dict[Attribute, int] = {}
    for locus, spec in LOCUS_EFFECTS.items():
        score = score_of(genes, locus)
        for member, points in spec.attributes.items():
            shifts[member] = shifts.get(member, 0) + score * points
    return {member: round_half_up(value * rules.genetics.attribute_step_pct / PERCENT) for member, value in shifts.items() if value}


def tied_traits(genes: Mapping[str, list[str]]) -> list[tuple[Locus, TraitKind]]:
    return [(locus, trait) for locus, spec in LOCUS_EFFECTS.items() for allele, trait in spec.traits if phenotype(genes, locus) == allele]


def line_traits(rules: Rules, genes: Mapping[str, list[str]]) -> dict[LineTrait, int]:
    found: dict[LineTrait, int] = {}
    for locus, spec in LOCUS_EFFECTS.items():
        score = score_of(genes, locus)
        if spec.line_trait is not None and score:
            found[spec.line_trait] = found.get(spec.line_trait, 0) + score * rules.genetics.germline_trait
    return {trait: value for trait, value in found.items() if value}


def signed(value: int) -> str:
    return f"+{value}" if value > 0 else str(value)


def describe_effects(rules: Rules, locus: Locus, score: int) -> list[str]:
    if not score:
        return []
    spec = LOCUS_EFFECTS[locus]
    lines = [
        f"{STAT_WORDS[key]} {signed(round_half_up(score * points * rules.genetics.stat_step_pct / PERCENT))} at birth" for key, points in spec.stats.items()
    ]
    lines += [
        f"Inborn {ATTRIBUTE_WORDS[member]} {signed(round_half_up(score * points * rules.genetics.attribute_step_pct / PERCENT))}"
        for member, points in spec.attributes.items()
    ]
    for skill, share in spec.skills.items():
        pace = round_half_up(score * share * rules.genetics.learning_pct / PERCENT)
        lines.append(f"Learns {SKILLS[skill].label.lower()} {abs(pace)}% {'faster' if pace > 0 else 'slower'}")
    for channel, weight in spec.effects.items():
        amount = score * weight * EFFECT_SCALES[channel](rules)
        unit = " each epoch" if channel in EFFECT_POINTS else "%"
        lines.append(f"{GENETIC_EFFECT_LABELS[channel]} {signed(amount)}{unit}")
    return lines


def carried_alleles(genes: Mapping[str, list[str]]) -> list[tuple[Locus, str]]:
    hidden: list[tuple[Locus, str]] = []
    for locus in LOCI:
        shown = phenotype(genes, locus)
        hidden.extend((locus, key) for key in dict.fromkeys(pair_of(genes, locus)) if key != shown and not LOCI[locus].graded)
    return hidden


def gift_factors(rules: Rules, genome: GenomeRow | None, school: MagicSchool) -> tuple[float, float]:
    if genome is None:
        return 1.0, 1.0
    gift = aptitude(rules, genome.genes, school) / PERCENT
    return max(0.0, 1 - gift * rules.gift.backlash_pct / PERCENT), 1 + gift * rules.gift.power_pct / PERCENT
