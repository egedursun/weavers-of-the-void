from sqlalchemy import select

from aerona.catalog.genetic_effects import HOUSE_TRAIT_ALLELES, LOCUS_EFFECTS
from aerona.catalog.genetics import LOCI
from aerona.catalog.mind import TRAITS
from aerona.core.random import SeededRandom
from aerona.db.tables.cosmos import AppliedFixupRow
from aerona.db.tables.genetics import AllelePoolRow, GenomeRow
from aerona.db.tables.living import LivingLineTraitRow
from aerona.domain.enums.environment import TemperatureBand
from aerona.domain.enums.genetics import GeneticEffect, Locus, LocusGroup
from aerona.domain.enums.living import CultivationMethod, LineTrait
from aerona.domain.enums.mind import Attribute, SkillKind, TraitKind
from aerona.domain.enums.polity import HouseTrait
from aerona.engine.genetics.genome import (
    attribute_shifts,
    carried_alleles,
    describe_effects,
    effect_pct,
    inherited_genes,
    learning_factor,
    line_traits,
    phenotype,
    stat_shifts,
    tied_traits,
)
from aerona.engine.genetics.life import (
    bless_blood,
    climate_health,
    disease_factor,
    express,
    fertility_factor,
    found_genome,
    healing_factor,
    madness_factor,
    raise_child,
    stress_factor,
)
from aerona.engine.genetics.pools import seed_pool
from aerona.engine.genetics.widen import WIDEN_FIXUP, widen_loci
from aerona.engine.living.lines import LineDraft, make_line
from aerona.engine.mind.book import traits_of
from aerona.engine.mind.split import attributes_of
from aerona.engine.mind.traits import seed_traits
from aerona.engine.mortal.kinship import add_parent
from aerona.engine.primitives.stats import stat
from aerona.rules.registry import Rules
from tests.engine.society.factories import Realm, context, mortal, people, tuned

RULES = Rules()


def blood(holder_id: int, found: dict[str, list[str]]) -> GenomeRow:
    return GenomeRow(holder_node_id=holder_id, genes=found, potential={}, likeness={}, marks=[], locked=[])


def genes(**pairs: tuple[str, str]) -> dict[str, list[str]]:
    found = {locus.value: [spec.common.key, spec.common.key] for locus, spec in LOCI.items()}
    found.update({key: list(value) for key, value in pairs.items()})
    return found


def test_every_locus_has_a_spec_an_effect_and_a_common_allele_that_moves_nothing() -> None:
    assert set(LOCI) == set(Locus) == set(LOCUS_EFFECTS)
    assert {spec.group for spec in LOCI.values()} == set(LocusGroup)
    plain = genes()
    assert stat_shifts(RULES, plain) == {}
    assert attribute_shifts(RULES, plain) == {}
    assert all(effect_pct(RULES, plain, channel) == 0 for channel in GeneticEffect)
    assert all(learning_factor(RULES, GenomeRow(genes=plain), skill) == 1.0 for skill in SkillKind)


def test_every_tied_trait_is_heritable_and_every_house_trait_names_a_real_allele() -> None:
    for locus, spec in LOCUS_EFFECTS.items():
        for allele, trait in spec.traits:
            assert allele in LOCI[locus].keys
            assert TRAITS[trait].heritable
    for locus, allele in HOUSE_TRAIT_ALLELES.values():
        assert allele in LOCI[locus].keys


def test_the_body_senses_and_aptitudes_move_stats_abilities_and_learning() -> None:
    strong = genes(muscle=("high", "high"), sight=("high", "high"), number_sense=("high", "high"))
    assert stat_shifts(RULES, strong)["strength"] == 5
    assert attribute_shifts(RULES, strong)[Attribute.ANALYTICAL_ABILITY] == 6
    assert learning_factor(RULES, GenomeRow(genes=strong), SkillKind.BOW) > 1.0
    assert learning_factor(RULES, GenomeRow(genes=strong), SkillKind.ACCOUNTING) > 1.0
    dim = GenomeRow(genes=genes(sight=("low", "low")))
    assert learning_factor(RULES, dim, SkillKind.BOW) < 1.0
    assert learning_factor(RULES, GenomeRow(genes=genes(colour_blindness=("blind", "blind"))), SkillKind.WEAVING) == 0.7
    assert learning_factor(RULES, GenomeRow(genes=genes(colour_blindness=("keen", "keen"))), SkillKind.WEAVING) > 1.0
    assert phenotype(genes(muscle=("low", "high")), Locus.MUSCLE) == "common"


def test_health_strain_climate_and_old_loci_read_through_one_catalogue() -> None:
    assert healing_factor(RULES, GenomeRow(genes=genes(wound_healing=("high", "high")))) > 1.0
    assert healing_factor(RULES, GenomeRow(genes=genes(wound_healing=("low", "low")))) < 1.0
    assert stress_factor(RULES, GenomeRow(genes=genes(stress_response=("high", "high")))) > 1.0
    assert madness_factor(RULES, GenomeRow(genes=genes(stress_response=("high", "high")))) > 1.0
    assert disease_factor(RULES, GenomeRow(genes=genes(disease_resistance=("hardy", "hardy")))) == 1 - RULES.genetics.disease_pct / 100
    assert fertility_factor(RULES, GenomeRow(genes=genes(fertility=("fruitful", "fruitful")))) == 1 + RULES.genetics.fertility_pct / 100
    cold = GenomeRow(genes=genes(cold_tolerance=("high", "high")))
    assert climate_health(RULES, cold, TemperatureBand.FROZEN) == RULES.genetics.climate_health
    assert climate_health(RULES, cold, TemperatureBand.TEMPERATE) == 0
    assert climate_health(RULES, GenomeRow(genes=genes(heat_tolerance=("low", "low"))), TemperatureBand.SEARING) == -RULES.genetics.climate_health
    assert effect_pct(RULES, genes(ageing_pace=("high", "high")), GeneticEffect.LIFESPAN) < 0


def test_children_inherit_every_new_locus_and_mutations_stay_within_its_alleles() -> None:
    first = genes(muscle=("high", "high"), memory=("low", "low"))
    second = genes(muscle=("high", "high"), memory=("low", "low"))
    child = inherited_genes(tuned(RULES, genetics={"mutation_pct": 0}), SeededRandom.for_epoch(1, 1, "w48"), first, second, 0)
    assert set(child) == {locus.value for locus in Locus}
    assert child[Locus.MUSCLE.value] == ["high", "high"]
    assert child[Locus.MEMORY.value] == ["low", "low"]
    mutated = inherited_genes(tuned(RULES, genetics={"mutation_pct": 100}), SeededRandom.for_epoch(1, 1, "m"), first, second, 0)
    assert all(set(pair) <= set(LOCI[Locus(key)].keys) for key, pair in mutated.items())


def test_effects_are_told_plainly_and_hidden_alleles_are_found() -> None:
    assert "Strength +5 at birth" in describe_effects(RULES, Locus.MUSCLE, 1)
    assert any("slower" in line for line in describe_effects(RULES, Locus.COLOUR_BLINDNESS, 1))
    assert describe_effects(RULES, Locus.MUSCLE, 0) == []
    assert (Locus.MADNESS, "touched") in carried_alleles(genes(madness=("sound", "touched")))
    assert tied_traits(genes(sociability=("high", "high"), attention=("low", "low"))) == [
        (Locus.SOCIABILITY, TraitKind.GREGARIOUS),
        (Locus.ATTENTION, TraitKind.SCATTERBRAINED),
    ]
    assert line_traits(RULES, genes(muscle=("high", "high")))[LineTrait.STRENGTH] == RULES.genetics.germline_trait


async def test_a_newborn_grows_into_its_blood_and_takes_its_tied_traits(realm: Realm) -> None:
    rules = tuned(RULES, genetics={"gene_trait_pct": 100})
    ctx = context(realm.session, rules)
    child = await mortal(realm, "Ira", age=0, strength=40)
    genome = await found_genome(ctx, child)
    genome.genes = genes(muscle=("high", "high"), memory=("high", "high"), sociability=("high", "high"))
    genome.potential = {member.value: 40 for member in Attribute}
    await raise_child(ctx, child, genome, 0)
    assert (stat(child, "strength") or 0) >= 45
    assert (await attributes_of(realm.session, child.id))[Attribute.MEMORY] == 46
    await seed_traits(realm.session, rules, child.id, {}, rng=ctx.rng("traits"), epoch=ctx.epoch, divine=False)
    owned = await traits_of(realm.session, child.id)
    assert TraitKind.RETENTIVE in owned or TraitKind.GREGARIOUS in owned


async def test_a_house_breeds_toward_its_new_blood_traits(realm: Realm) -> None:
    ctx = context(realm.session)
    child = await mortal(realm, "Ora", age=0, strength=40)
    genome = await found_genome(ctx, child)
    bless_blood(RULES, child, genome, [HouseTrait.STRONG_BLOODED, HouseTrait.STEADY])
    assert "high" in genome.genes[Locus.MUSCLE.value]
    assert "low" in genome.genes[Locus.STRESS_RESPONSE.value]
    express(RULES, child, genome.genes)


async def test_old_genomes_and_pools_gain_the_new_loci_once_from_parents_or_their_people(realm: Realm) -> None:
    ctx = context(realm.session)
    folk = await people(realm, "Old Folk")
    pool = await seed_pool(ctx, folk)
    pool.frequencies = {key: value for key, value in pool.frequencies.items() if key != Locus.SIGHT.value}
    mother = await mortal(realm, "Mona")
    father = await mortal(realm, "Faro")
    child = await mortal(realm, "Kit", age=4)
    for parent in (mother, father):
        await add_parent(realm.session, parent.id, child.id, 1)
    old = {key: value for key, value in genes().items() if key not in {Locus.MUSCLE.value, Locus.SIGHT.value}}
    for being in (mother, father):
        realm.session.add(
            GenomeRow(holder_node_id=being.id, genes={**old, Locus.MUSCLE.value: ["high", "high"]}, potential={}, likeness={}, marks=[], locked=[])
        )
    realm.session.add(blood(child.id, dict(old)))
    await realm.session.flush()
    await widen_loci(ctx)
    widened = await realm.session.get(GenomeRow, child.id)
    assert widened is not None and widened.genes[Locus.MUSCLE.value] == ["high", "high"]
    assert Locus.SIGHT.value in widened.genes
    refreshed = await realm.session.get(AllelePoolRow, folk.id)
    assert refreshed is not None and Locus.SIGHT.value in refreshed.frequencies
    assert await realm.session.get(AppliedFixupRow, WIDEN_FIXUP) is not None
    assert await widen_loci(ctx) == (0, 0)


async def test_a_living_line_carries_the_leanings_of_its_sources_blood(realm: Realm) -> None:
    ctx = context(realm.session)
    maker = await mortal(realm, "Sela")
    source = await mortal(realm, "Brann")
    realm.session.add(
        GenomeRow(
            holder_node_id=source.id, genes=genes(muscle=("high", "high"), wound_healing=("high", "high")), potential={}, likeness={}, marks=[], locked=[]
        )
    )
    await realm.session.flush()
    line = await make_line(ctx, LineDraft("Strong line", CultivationMethod.SELECTIVE_BREEDING, maker.id, maker.id, (source.id,), ()), forced=True)
    carried = {row.trait: row.strength for row in await realm.session.scalars(select(LivingLineTraitRow).where(LivingLineTraitRow.line_id == line.id))}
    assert carried[LineTrait.STRENGTH] == RULES.genetics.germline_trait
    assert carried[LineTrait.REGENERATION] == RULES.genetics.germline_trait
