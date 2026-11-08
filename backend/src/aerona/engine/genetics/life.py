from collections.abc import Sequence

from sqlalchemy import select

from aerona.constants.units import PERCENT
from aerona.db.repositories.entities import EntityRepository
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.genetics import AllelePoolRow, GenomeRow
from aerona.db.tables.households import DwellingRow, HouseholdMemberRow, HouseholdRow
from aerona.db.tables.mortal import MortalProfileRow
from aerona.db.write_guard import held
from aerona.domain.enums.entity import EntityFlag
from aerona.domain.enums.genetics import Locus
from aerona.domain.enums.mind import PreferenceKind
from aerona.domain.enums.mortal import Ability, LifeStage
from aerona.domain.enums.polity import HouseTrait
from aerona.engine.body.customs import people_of
from aerona.engine.context import TickContext
from aerona.engine.genetics.genome import (
    affliction_marks,
    body_marks,
    consanguinity,
    drawn_genes,
    genome_of,
    inherited_genes,
    likeness,
    phenotype,
    potential_of,
    rare_visible,
    score_of,
)
from aerona.engine.genetics.pools import seed_pool
from aerona.engine.mind.preferences import fit, prefs_of
from aerona.engine.mortal.kin import parents_of
from aerona.engine.primitives.numbers import clamp_int, round_half_up
from aerona.engine.primitives.stats import set_stats, stat
from aerona.rules.registry import Rules

BEAUTY = "beauty"
RECOGNISABILITY = "recognisability"
GENES = "genes"
MARKS = "marks"
TRAIT_ALLELES: dict[HouseTrait, tuple[Locus, str]] = {
    HouseTrait.LONG_LIVED: (Locus.LONGEVITY, "enduring"),
    HouseTrait.GIANT_BLOODED: (Locus.GIANT_BLOOD, "giant"),
    HouseTrait.GOD_BLOODED: (Locus.DIVINE_BLOOD, "divine"),
    HouseTrait.CURSED: (Locus.CURSE_MARKER, "marked"),
    HouseTrait.FERTILE: (Locus.FERTILITY, "fruitful"),
    HouseTrait.SEER_GIFT: (Locus.GIFT_DIVINATION, "gifted"),
}
DEFAULT_ABILITY = 50


async def people_pool(ctx: TickContext, mortal: EntityRow) -> AllelePoolRow | None:
    people = await people_of(ctx.session, mortal)
    if people is None:
        return None
    return await ctx.session.get(AllelePoolRow, people.id) or await seed_pool(ctx, people)


def abilities_of(mortal: EntityRow) -> dict[str, int]:
    return {ability.value: int(stat(mortal, ability.value) or DEFAULT_ABILITY) for ability in Ability}


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
        potential = potential_of(ctx.rules, rng, parent_genomes[0].potential, parent_genomes[1].potential, abilities_of(mortal))
        divine = parent_genomes[0].divine_son_id or parent_genomes[1].divine_son_id
    else:
        pool = await people_pool(ctx, mortal)
        genes = drawn_genes(rng, pool.frequencies if pool is not None else None)
        potential = abilities_of(mortal)
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
    span_shift = delta(Locus.LONGEVITY) - delta(Locus.CURSE_MARKER)
    if lifespan is not None and span_shift:
        set_stats(mortal, lifespan=max(1, round_half_up(lifespan * (PERCENT + span_shift * table.longevity_pct) / PERCENT)))
    if delta(Locus.GIANT_BLOOD):
        set_stats(mortal, strength=clamp_int((stat(mortal, "strength") or 0) + delta(Locus.GIANT_BLOOD) * table.giant_strength, 0, PERCENT))
    if delta(Locus.DIVINE_BLOOD):
        set_stats(mortal, charisma=clamp_int((stat(mortal, "charisma") or 0) + delta(Locus.DIVINE_BLOOD) * table.divine_charisma, 0, PERCENT))


def raise_child(rules: Rules, child: EntityRow, genome: GenomeRow, upbringing: int) -> None:
    abilities = {key: clamp_int(value + upbringing, 0, PERCENT) for key, value in genome.potential.items()}
    set_stats(child, **abilities)
    express(rules, child, genome.genes)


def fertility_factor(rules: Rules, genome: GenomeRow | None) -> float:
    return 1.0 if genome is None else max(0.0, 1 + score_of(genome.genes, Locus.FERTILITY) * rules.genetics.fertility_pct / PERCENT)


def disease_factor(rules: Rules, genome: GenomeRow | None) -> float:
    return 1.0 if genome is None else max(0.0, 1 - score_of(genome.genes, Locus.DISEASE_RESISTANCE) * rules.genetics.disease_pct / PERCENT)


def madness_factor(rules: Rules, genome: GenomeRow | None) -> float:
    return 1.0 if genome is None else 1 + score_of(genome.genes, Locus.MADNESS) * rules.genetics.madness_pct / PERCENT


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
        for locus in (Locus.HEIGHT, Locus.BUILD, Locus.SKIN, Locus.HAIR_COLOUR, Locus.HAIR_TEXTURE, Locus.EYE_COLOUR, Locus.FACE, Locus.VOICE):
            beauty += fit(prefs, PreferenceKind.LOOKS, f"{locus.value}:{phenotype(genome.genes, locus)}") * table.beauty_taste_pct / PERCENT
        beauty -= scars * table.beauty_scar + missing * table.beauty_missing + len(afflicted) * table.beauty_mark
        profile = await ctx.session.get(MortalProfileRow, mortal.id)
        if profile is not None and profile.life_stage is LifeStage.ELDER:
            beauty -= beauty * table.beauty_age_pct / PERCENT
        genome.beauty = clamp_int(beauty, 0, PERCENT)
    if RECOGNISABILITY not in locked:
        rare = rare_visible(ctx.rules, genome.genes, pool.frequencies if pool is not None else None)
        genome.recognisability = clamp_int(table.recognisable_base + rare * table.recognisable_rare + (scars + missing) * table.recognisable_scar, 0, PERCENT)
    resemblance: dict[str, int] = {}
    for parent_id in await parents_of(ctx.session, mortal.id):
        other = await genome_of(ctx.session, parent_id)
        if other is not None:
            resemblance[str(parent_id)] = likeness(genome.genes, other.genes)
    genome.likeness = resemblance
    genome.epoch = ctx.epoch
