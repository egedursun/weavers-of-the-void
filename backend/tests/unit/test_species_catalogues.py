from aerona.catalog.diets import DIETS, FLESH_SEEKERS, GRAZERS, HUNTERS, INEDIBLE, MEAT_EATERS, MEATLESS
from aerona.catalog.domestication import CHARGED_BIOCHEMISTRY, HOUSED_STAGES, KEPT_STAGES, SOCIALITIES, UNBOUND_BIOCHEMISTRY, WILDISH_STAGES
from aerona.catalog.senses import PURPOSES, SENSE_PURPOSES, SENSES
from aerona.domain.enums.ecology import Biochemistry, Diet, DomesticationStage, Sociality
from aerona.domain.enums.nature import SenseKind
from aerona.domain.enums.society import CreatureTrait


def test_diet_traits_keep_their_memberships() -> None:
    assert {Diet.CARNIVORE, Diet.OMNIVORE, Diet.SOUL, Diet.INSECTIVORE} == HUNTERS
    assert {Diet.HERBIVORE, Diet.OMNIVORE, Diet.FILTER} == GRAZERS
    assert {Diet.CARNIVORE, Diet.OMNIVORE, Diet.INSECTIVORE} == MEAT_EATERS
    assert {Diet.CARNIVORE, Diet.OMNIVORE, Diet.SCAVENGER} == FLESH_SEEKERS
    assert {Diet.VOID, Diet.MINERAL, Diet.ENERGY} == INEDIBLE
    assert {Diet.MINERAL, Diet.VOID, Diet.PHOTOSYNTHETIC, Diet.CHEMOSYNTHETIC, Diet.DECOMPOSER, Diet.ENERGY} == MEATLESS
    assert all(spec.needs and spec.text for spec in DIETS.values())


def test_stages_socialities_and_biochemistries_keep_their_memberships() -> None:
    assert {DomesticationStage.HERDED, DomesticationStage.DOMESTICATED, DomesticationStage.BREED, DomesticationStage.CAPTIVE} == KEPT_STAGES
    assert {DomesticationStage.DOMESTICATED, DomesticationStage.BREED, DomesticationStage.CAPTIVE} == HOUSED_STAGES
    assert {
        DomesticationStage.WILD,
        DomesticationStage.TAMED,
        DomesticationStage.HERDED,
        DomesticationStage.COMMENSAL,
        DomesticationStage.FERAL,
    } == WILDISH_STAGES
    assert {kind for kind, spec in SOCIALITIES.items() if spec.keeps_numbers} == {
        Sociality.HERD,
        Sociality.HIVE,
        Sociality.COLONY,
        Sociality.SWARM,
        Sociality.FAMILY_GROUP,
    }
    assert SOCIALITIES[Sociality.PACK].trait is CreatureTrait.PACK_HUNTER
    assert {Biochemistry.VOID, Biochemistry.SPIRIT, Biochemistry.PLASMA} == UNBOUND_BIOCHEMISTRY
    assert {Biochemistry.CRYSTAL, Biochemistry.SILICON, Biochemistry.PLASMA, Biochemistry.METAL} == CHARGED_BIOCHEMISTRY


def test_every_purpose_weighs_its_senses_to_one() -> None:
    assert set(PURPOSES) == set(SENSE_PURPOSES)
    assert all(abs(sum(weights.values()) - 1.0) < 1e-9 for weights in PURPOSES.values())
    assert set(SENSES) == set(SenseKind)
