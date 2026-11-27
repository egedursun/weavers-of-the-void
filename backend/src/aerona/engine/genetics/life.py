from collections.abc import Mapping, Sequence

from sqlalchemy import select

from aerona.catalog.genetic_effects import HOUSE_TRAIT_ALLELES, LOCUS_EFFECTS
from aerona.catalog.genetics import APTITUDE_LOCI, LOOKS_LOCI
from aerona.constants.units import PERCENT
from aerona.db.repositories.entities import EntityRepository
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.genetics import AllelePoolRow, GenomeRow
from aerona.db.tables.households import DwellingRow, HouseholdMemberRow, HouseholdRow
from aerona.db.tables.mortal import MortalProfileRow
from aerona.db.write_guard import held
from aerona.domain.enums.entity import EntityFlag
from aerona.domain.enums.environment import TemperatureBand
from aerona.domain.enums.genetics import GeneticEffect, Locus
from aerona.domain.enums.mind import Attribute, PreferenceKind
from aerona.domain.enums.mortal import LifeStage
from aerona.domain.enums.polity import HouseTrait
from aerona.engine.body.customs import people_of
from aerona.engine.context import TickContext
from aerona.engine.genetics.genome import (
    affliction_marks,
    attribute_shifts,
    body_marks,
    consanguinity,
    drawn_genes,
    effect_factor,
    effect_pct,
    genome_of,
    inherited_genes,
    likeness,
    phenotype,
    potential_of,
    rare_visible,
    score_of,
    stat_shifts,
)
from aerona.engine.genetics.pools import seed_pool
from aerona.engine.mind.preferences import fit, prefs_of
from aerona.engine.mind.split import attributes_of, store_attributes, stored_attribute
from aerona.engine.mortal.kin import parents_of
from aerona.engine.primitives.numbers import clamp_int, round_half_up
from aerona.engine.primitives.stats import set_stats, stat
from aerona.rules.registry import Rules

BEAUTY = "beauty"
RECOGNISABILITY = "recognisability"
GENES = "genes"
MARKS = "marks"
LIKENESS = "likeness"
TRAIT_ALLELES = HOUSE_TRAIT_ALLELES
COLD_BANDS = frozenset({TemperatureBand.FROZEN, TemperatureBand.COLD})
HOT_BANDS = frozenset({TemperatureBand.HOT, TemperatureBand.SEARING})


async def people_pool(ctx: TickContext, mortal: EntityRow) -> AllelePoolRow | None:
    people = await people_of(ctx.session, mortal)
    if people is None:
        return None
    return await ctx.session.get(AllelePoolRow, people.id) or await seed_pool(ctx, people)


async def attribute_levels(ctx: TickContext, mortal: EntityRow) -> dict[str, int]:
    return {member.value: await stored_attribute(ctx.session, mortal, member) for member in Attribute}


def marked(genes: dict[str, list[str]], locus: Locus, allele: str) -> None:
    pair = list(genes.get(locus.value) or [allele, allele])
    if allele not in pair:
        pair[0] = allele
    genes[locus.value] = pair[:2]


async def found_genome(ctx: TickContext, mortal: EntityRow, parents: Sequence[EntityRow] = ()) -> GenomeRow:
    existing = await genome_of(ctx.session, mortal.id)
    if existing is not None:
        return existing
    rng = ctx.rng(f"genetics.genome.{mortal.id}")
    parent_genomes = [genome for parent in parents if (genome := await found_genome(ctx, parent)) is not None]
    inbreeding = await consanguinity(ctx.session, ctx.rules, parents[0].id, parents[1].id) if len(parents) >= 2 else 0
    if len(parent_genomes) >= 2:
        genes = inherited_genes(ctx.rules, rng, parent_genomes[0].genes, parent_genomes[1].genes, inbreeding)
        potential = potential_of(ctx.rules, rng, parent_genomes[0].potential, parent_genomes[1].potential, await attribute_levels(ctx, mortal))
        divine = parent_genomes[0].divine_son_id or parent_genomes[1].divine_son_id
    else:
        pool = await people_pool(ctx, mortal)
        genes = drawn_genes(rng, pool.frequencies if pool is not None else None)
        potential = await attribute_levels(ctx, mortal)
        divine = mortal.creator_son_id
    if divine is not None:
        marked(genes, Locus.DIVINE_BLOOD, "divine")
    if EntityFlag.BLOODLINE_CURSE in await EntityRepository(ctx.session).flags(mortal.id):
        marked(genes, Locus.CURSE_MARKER, "marked")
    row = GenomeRow(
        holder_node_id=mortal.id,
        genes=genes,
        potential=potential,
        divine_son_id=divine,
        inbreeding=inbreeding,
        beauty=ctx.rules.genetics.beauty_base,
        recognisability=ctx.rules.genetics.recognisable_base,
        likeness={},
        marks=[],
        epoch=ctx.epoch,
        locked=[],
    )
    ctx.session.add(row)
    await ctx.session.flush()
    return row


def bless_blood(rules: Rules, mortal: EntityRow, genome: GenomeRow, traits: Sequence[HouseTrait]) -> None:
    if GENES in (genome.locked or []) or held(mortal.id):
        return
    before = {key: list(value) for key, value in genome.genes.items()}
    genes = {key: list(value) for key, value in genome.genes.items()}
    for trait in traits:
        locus, allele = TRAIT_ALLELES[trait]
        marked(genes, locus, allele)
    genome.genes = genes
    express(rules, mortal, genes, before)


async def upbringing_pct(ctx: TickContext, child_id: int, parents: Sequence[EntityRow]) -> int:
    for parent in parents:
        member = await ctx.session.get(HouseholdMemberRow, parent.id)
        household = await ctx.session.get(HouseholdRow, member.household_id) if member is not None else None
        if household is None:
            continue
        home = await ctx.session.scalar(select(DwellingRow).where(DwellingRow.household_id == household.id))
        quality = home.quality if home is not None else 0
        wealth = min(PERCENT, household.wealth)
        return round_half_up((wealth + quality) / 2 * ctx.rules.genetics.upbringing_pct / PERCENT)
    return 0


def express(rules: Rules, mortal: EntityRow, genes: dict[str, list[str]], before: dict[str, list[str]] | None = None) -> None:
    table = rules.genetics

    def delta(locus: Locus) -> int:
        return score_of(genes, locus) - (score_of(before, locus) if before is not None else 0)

    lifespan = stat(mortal, "lifespan")
    span_shift = effect_pct(rules, genes, GeneticEffect.LIFESPAN) - (effect_pct(rules, before, GeneticEffect.LIFESPAN) if before is not None else 0)
    if lifespan is not None and span_shift:
        set_stats(mortal, lifespan=max(1, round_half_up(lifespan * (PERCENT + span_shift) / PERCENT)))
    earlier = stat_shifts(rules, before) if before is not None else {}
    for key, points in stat_shifts(rules, genes).items():
        moved = points - earlier.get(key, 0)
        current = stat(mortal, key)
        if moved and current is not None:
            set_stats(mortal, **{key: clamp_int(current + moved, 0, PERCENT)})
    if delta(Locus.GIANT_BLOOD):
        set_stats(mortal, strength=clamp_int((stat(mortal, "strength") or 0) + delta(Locus.GIANT_BLOOD) * table.giant_strength, 0, PERCENT))
    if delta(Locus.DIVINE_BLOOD):
        set_stats(mortal, charisma=clamp_int((stat(mortal, "charisma") or 0) + delta(Locus.DIVINE_BLOOD) * table.divine_charisma, 0, PERCENT))


def aptitude_pace(rules: Rules, genes: Mapping[str, list[str]]) -> dict[Attribute, float]:
    weight = rules.genetics.general_aptitude_weight_pct / PERCENT
    pace: dict[Attribute, float] = {}
    for locus in APTITUDE_LOCI:
        score = score_of(genes, locus)
        for member in LOCUS_EFFECTS[locus].attributes:
            pace[member] = pace.get(member, 1.0) * max(0.0, 1 + score * weight)
    return pace


def twinning_chance(rules: Rules, base: float, genomes: Sequence[GenomeRow | None]) -> float:
    carried = sum(max(0, score_of(genome.genes, Locus.TWINNING)) for genome in genomes if genome is not None)
    return base + carried * rules.genetics.twinning_pct


async def raise_child(ctx: TickContext, child: EntityRow, genome: GenomeRow, upbringing: int) -> None:
    inborn = attribute_shifts(ctx.rules, genome.genes)
    pace = aptitude_pace(ctx.rules, genome.genes)
    grown = {
        Attribute(key): clamp_int(value + round_half_up(upbringing * pace.get(Attribute(key), 1.0)) + inborn.get(Attribute(key), 0), 0, PERCENT)
        for key, value in genome.potential.items()
        if key in Attribute
    }
    if grown:
        await store_attributes(ctx.session, child, {**await attributes_of(ctx.session, child.id), **grown})
    express(ctx.rules, child, genome.genes)


def fertility_factor(rules: Rules, genome: GenomeRow | None) -> float:
    return effect_factor(rules, genome, GeneticEffect.FERTILITY)


def disease_factor(rules: Rules, genome: GenomeRow | None) -> float:
    return effect_factor(rules, genome, GeneticEffect.DISEASE)


def madness_factor(rules: Rules, genome: GenomeRow | None) -> float:
    return effect_factor(rules, genome, GeneticEffect.MADNESS)


def healing_factor(rules: Rules, genome: GenomeRow | None) -> float:
    return effect_factor(rules, genome, GeneticEffect.HEALING)


def stress_factor(rules: Rules, genome: GenomeRow | None) -> float:
    return effect_factor(rules, genome, GeneticEffect.STRESS)


def climate_health(rules: Rules, genome: GenomeRow | None, band: TemperatureBand | None) -> int:
    if genome is None or band is None:
        return 0
    if band in COLD_BANDS:
        return effect_pct(rules, genome.genes, GeneticEffect.COLD)
    if band in HOT_BANDS:
        return effect_pct(rules, genome.genes, GeneticEffect.HEAT)
    return 0


async def refresh_genome(ctx: TickContext, mortal: EntityRow, genome: GenomeRow, pool: AllelePoolRow | None) -> None:
    if held(mortal.id):
        return
    table = ctx.rules.genetics
    locked = set(genome.locked or [])
    scars, missing = await body_marks(ctx.session, mortal.id)
    afflicted = await affliction_marks(ctx.session, mortal.id)
    if MARKS not in locked:
        genome.marks = [*(["scarred"] if scars else []), *(["missing a part of the body"] if missing else []), *afflicted]
    people = await people_of(ctx.session, mortal)
    prefs = await prefs_of(ctx.session, people.id if people is not None else None)
    if BEAUTY not in locked:
        beauty: float = table.beauty_base
        for locus in LOOKS_LOCI:
            beauty += fit(prefs, PreferenceKind.LOOKS, f"{locus.value}:{phenotype(genome.genes, locus)}") * table.beauty_taste_pct / PERCENT
        beauty -= scars * table.beauty_scar + missing * table.beauty_missing + len(afflicted) * table.beauty_mark
        profile = await ctx.session.get(MortalProfileRow, mortal.id)
        if profile is not None and profile.life_stage is LifeStage.ELDER:
            beauty -= beauty * table.beauty_age_pct / PERCENT
        genome.beauty = clamp_int(beauty, 0, PERCENT)
    if RECOGNISABILITY not in locked:
        rare = rare_visible(ctx.rules, genome.genes, pool.frequencies if pool is not None else None)
        genome.recognisability = clamp_int(table.recognisable_base + rare * table.recognisable_rare + (scars + missing) * table.recognisable_scar, 0, PERCENT)
    if LIKENESS not in locked:
        resemblance: dict[str, int] = {}
        for parent_id in await parents_of(ctx.session, mortal.id):
            other = await genome_of(ctx.session, parent_id)
            if other is not None:
                resemblance[str(parent_id)] = likeness(genome.genes, other.genes)
        genome.likeness = resemblance
    genome.epoch = ctx.epoch
