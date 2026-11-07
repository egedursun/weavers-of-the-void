from aerona.catalog.genetics import LOCI
from aerona.core.random import SeededRandom
from aerona.db.tables.factions import FactionProfileRow
from aerona.db.tables.genetics import GenomeRow, HouseResemblanceRow
from aerona.db.tables.mind import CultureEthicRow
from aerona.db.tables.polity import HouseMemberRow, HouseProfileRow
from aerona.domain.enums.culture import MagicSchool
from aerona.domain.enums.entity import EntityType
from aerona.domain.enums.faction import FactionKind
from aerona.domain.enums.genetics import GiftStance, Locus
from aerona.domain.enums.mind import ActKind, EthicalStance, SkillKind
from aerona.domain.enums.polity import HouseTrait
from aerona.domain.models.entity_stats import FactionStats, HouseStats
from aerona.engine.genetics.genome import aptitude, colour_factor, consanguinity, gift_factors, inherited_genes, likeness, phenotype
from aerona.engine.genetics.life import bless_blood, express, fertility_factor, found_genome, madness_factor, refresh_genome
from aerona.engine.genetics.lineage import examine_children, seed_looks, tend_resemblance
from aerona.engine.genetics.pools import members_by_people, seed_pool, tend_pool
from aerona.engine.mortal.kinship import add_parent
from aerona.engine.polity.laws import LawBook
from aerona.engine.primitives.stats import stat
from aerona.rules.registry import Rules
from tests.engine.society.factories import Realm, context, make, mortal, people, settlement

RULES = Rules()


def genes(**pairs: tuple[str, str]) -> dict[str, list[str]]:
    found = {locus.value: [spec.alleles[0].key, spec.alleles[0].key] for locus, spec in LOCI.items()}
    found.update({key: list(value) for key, value in pairs.items()})
    return found


def test_the_stronger_allele_shows_and_graded_looks_blend() -> None:
    assert phenotype(genes(hair_colour=("golden", "black")), Locus.HAIR_COLOUR) == "black"
    assert phenotype(genes(eye_colour=("blue", "grey")), Locus.EYE_COLOUR) in {"blue", "grey"}
    assert phenotype(genes(height=("short", "tall")), Locus.HEIGHT) == "middling"
    assert phenotype(genes(skin=("pale", "brown")), Locus.SKIN) == "olive"


def test_the_gift_is_recessive_and_the_wild_allele_dominant() -> None:
    assert aptitude(RULES, genes(gift_storm=("dormant", "gifted")), MagicSchool.STORM) == RULES.gift.carrier_aptitude
    assert aptitude(RULES, genes(gift_storm=("gifted", "gifted")), MagicSchool.STORM) == RULES.gift.gifted_aptitude
    assert aptitude(RULES, genes(gift_storm=("dormant", "wild")), MagicSchool.STORM) == RULES.gift.wild_aptitude
    assert aptitude(RULES, genes(), MagicSchool.STORM) == 0


def test_children_take_one_allele_from_each_parent_and_inbreeding_doubles_harm() -> None:
    first = genes(hair_colour=("copper", "copper"), madness=("sound", "touched"))
    second = genes(hair_colour=("ash", "ash"), madness=("sound", "touched"))
    clean = inherited_genes(RULES, SeededRandom.for_epoch(1, 1, "a"), first, second, 0)
    assert sorted(clean[Locus.HAIR_COLOUR.value]) in (["ash", "copper"], ["copper", "ash"]) or set(clean[Locus.HAIR_COLOUR.value]) <= {"ash", "copper"}
    inbred = inherited_genes(RULES, SeededRandom.for_epoch(1, 1, "b"), first, second, 100)
    assert inbred[Locus.MADNESS.value] == ["touched", "touched"]
    assert madness_factor(RULES, GenomeRow(genes=inbred)) > 1


async def test_siblings_breed_inbred_children_and_genomes_follow_parents(realm: Realm) -> None:
    ctx = context(realm.session)
    mother = await mortal(realm, "Ama")
    father = await mortal(realm, "Ben")
    first = await mortal(realm, "Cai")
    second = await mortal(realm, "Dee")
    for child in (first, second):
        await add_parent(realm.session, mother.id, child.id, 1)
        await add_parent(realm.session, father.id, child.id, 1)
    await realm.session.flush()
    assert await consanguinity(realm.session, RULES, first.id, second.id) == RULES.genetics.sibling_blood_pct
    assert await consanguinity(realm.session, RULES, mother.id, father.id) == 0
    baby = await mortal(realm, "Eve", age=0)
    await add_parent(realm.session, first.id, baby.id, 2)
    await add_parent(realm.session, second.id, baby.id, 2)
    await realm.session.flush()
    genome = await found_genome(ctx, baby, (first, second))
    assert genome.inbreeding >= RULES.genetics.sibling_blood_pct
    assert set(genome.potential) and all(0 <= value <= 100 for value in genome.potential.values())
    await refresh_genome(ctx, baby, genome, None)
    assert {str(first.id), str(second.id)} == set(genome.likeness)


async def test_house_traits_write_their_alleles_and_express_them(realm: Realm) -> None:
    ctx = context(realm.session)
    child = await mortal(realm, "Fen", age=0, lifespan=60, strength=40)
    genome = await found_genome(ctx, child)
    bless_blood(RULES, child, genome, [HouseTrait.GIANT_BLOODED, HouseTrait.LONG_LIVED, HouseTrait.FERTILE])
    assert "giant" in genome.genes[Locus.GIANT_BLOOD.value]
    assert (stat(child, "strength") or 0) >= 40 + RULES.genetics.giant_strength
    assert (stat(child, "lifespan") or 0) > 60 or phenotype(genome.genes, Locus.LONGEVITY) != "enduring"
    assert fertility_factor(RULES, genome) >= 1.0


async def test_pools_seed_drift_and_persecution_thins_the_gift(realm: Realm) -> None:
    ctx = context(realm.session)
    folk = await people(realm, "Vale Folk")
    pool = await seed_pool(ctx, folk)
    assert all(abs(sum(found.values()) - 100) <= 1 for found in pool.frequencies.values())
    before = pool.frequencies[Locus.GIFT_STORM.value].get("gifted", 0)
    pool.gift_stance = GiftStance.PERSECUTED
    pool.locked = ["gift_stance"]
    await tend_pool(ctx, folk, pool, [], await LawBook.load(realm.session))
    assert pool.frequencies[Locus.GIFT_STORM.value].get("gifted", 0) <= before
    assert pool.gift_stance is GiftStance.PERSECUTED
    assert await seed_looks(ctx, folk, pool) > 0
    assert await seed_looks(ctx, folk, pool) == 0


async def test_the_gift_stance_follows_the_people_s_ethics(realm: Realm) -> None:
    ctx = context(realm.session)
    folk = await people(realm, "Fearful Folk")
    realm.session.add(CultureEthicRow(holder_entity_id=folk.id, act=ActKind.MAGIC_USE, stance=EthicalStance.SHAMEFUL, since_epoch=1, locked=[]))
    pool = await seed_pool(ctx, folk)
    await tend_pool(ctx, folk, pool, [], await LawBook.load(realm.session))
    assert pool.gift_stance in {GiftStance.FEARED, GiftStance.PERSECUTED}


async def test_a_house_is_known_by_its_shared_look_and_orders_take_gifted_children(realm: Realm) -> None:
    ctx = context(realm.session)
    house = await make(realm.session, "House Varn", EntityType.HOUSE, HouseStats(), world_id=realm.world.id)
    realm.session.add(HouseProfileRow(house_entity_id=house.id, traits=[], seats=[], locked=[]))
    kin = [await mortal(realm, f"Varn {index}") for index in range(4)]
    for member in kin:
        realm.session.add(HouseMemberRow(house_entity_id=house.id, mortal_entity_id=member.id, joined_epoch=1, by_marriage=False))
        genome = await found_genome(ctx, member)
        genome.genes = {**genome.genes, Locus.HAIR_COLOUR.value: ["copper", "copper"]}
    await realm.session.flush()
    assert await tend_resemblance(ctx, house, kin)
    row = await realm.session.get(HouseResemblanceRow, house.id)
    assert row is not None and row.share == 100
    town = await settlement(realm, "Towerton")
    order = await make(realm.session, "The Grey Order", EntityType.FACTION, FactionStats(strength=30), world_id=realm.world.id)
    realm.session.add(FactionProfileRow(faction_entity_id=order.id, kind=FactionKind.MAGE_ORDER, home_entity_id=town.id))
    child = await mortal(realm, "Wren", age=8, location_id=town.id)
    genome = await found_genome(ctx, child)
    genome.genes = {**genome.genes, Locus.GIFT_MIND.value: ["wild", "dormant"]}
    await realm.session.flush()
    taken = 0
    for epoch in range(3, 12):
        taken += await examine_children(context(realm.session, epoch=epoch))
        if taken:
            break
    assert taken == 1
    assert likeness(genome.genes, genome.genes) == 100
    assert (await members_by_people(ctx)) is not None
    express(RULES, child, genome.genes)


def test_colour_blindness_slows_crafts_of_colour_and_the_gift_steadies_and_strengthens_rites() -> None:
    blind = GenomeRow(genes=genes(colour_blindness=("blind", "blind")))
    seeing = GenomeRow(genes=genes())
    assert colour_factor(RULES, blind, SkillKind.WEAVING) < 1.0
    assert colour_factor(RULES, blind, SkillKind.SMITHING) == 1.0
    assert colour_factor(RULES, seeing, SkillKind.WEAVING) == 1.0
    gifted = GenomeRow(genes=genes(gift_storm=("gifted", "gifted")))
    steadiness, strength = gift_factors(RULES, gifted, MagicSchool.STORM)
    assert steadiness < 1.0 and strength > 1.0
    assert gift_factors(RULES, seeing, MagicSchool.STORM) == (1.0, 1.0)
