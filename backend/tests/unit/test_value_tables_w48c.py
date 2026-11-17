from aerona.catalog.kinds.belief_stances import BELIEF_STANCES
from aerona.catalog.kinds.fanaticisms import FANATICISMS
from aerona.catalog.kinds.foe_natures import FOE_BANES
from aerona.catalog.kinds.gathering_outcomes import GATHERING_RESULTS
from aerona.catalog.kinds.line_outcomes import LINE_OUTCOMES
from aerona.catalog.kinds.making_outcomes import MAKING_WEIGHTS
from aerona.catalog.kinds.selectorates import SELECTORATE_BASES
from aerona.catalog.medicine import MEDICINE, infection_cut, threshold
from aerona.domain.enums.body import MedicineTier
from aerona.domain.enums.economy import FoeNature
from aerona.domain.enums.faith import FanaticismKind
from aerona.domain.enums.gathering import GatheringOutcome
from aerona.domain.enums.living import LineOutcome
from aerona.domain.enums.mind import ActKind, ThoughtKind
from aerona.domain.enums.regime import SelectorateKind
from aerona.engine.economy.materials import holy_edge
from aerona.rules.registry import Rules


def test_every_rule_a_value_table_names_exists() -> None:
    rules = Rules()
    named = [
        *((rules.selectorate, basis.share_rule) for basis in SELECTORATE_BASES.values()),
        *((rules.materials, bane.sanctity_rule) for bane in FOE_BANES.values()),
        *((rules.materials, bane.corruption_rule) for bane in FOE_BANES.values()),
        *((rules.god_images, stance.pull_rule) for stance in BELIEF_STANCES.values()),
        *((rules.god_images, stance.fame_rule) for stance in BELIEF_STANCES.values()),
        *((rules.living_methods, result.weight_rule) for result in LINE_OUTCOMES.values()),
        *((rules.living_methods, result.stability_rule) for result in LINE_OUTCOMES.values()),
        *((rules.living_methods, result.drift_rule) for result in LINE_OUTCOMES.values()),
        *((rules.mind_making, weight) for weight in MAKING_WEIGHTS.values()),
        *((rules.healing, spec.level_rule) for spec in MEDICINE.values()),
        *((rules.healing, spec.infection_rule) for spec in MEDICINE.values()),
    ]
    missing = [name for table, name in named if name is not None and not isinstance(getattr(table, name, None), int)]
    assert missing == []


def test_the_tables_keep_the_old_behaviour() -> None:
    rules = Rules()
    assert SELECTORATE_BASES[SelectorateKind.TRIBE].share_rule == "adult_pct" and not SELECTORATE_BASES[SelectorateKind.TRIBE].by_class
    assert SELECTORATE_BASES[SelectorateKind.COUNCIL].by_class and SELECTORATE_BASES[SelectorateKind.NOBLES].share_rule is None
    assert infection_cut(rules.healing, MedicineTier.NONE) == 0
    assert infection_cut(rules.healing, MedicineTier.HERBS) == rules.healing.herbs_infection_cut_pct
    assert infection_cut(rules.healing, MedicineTier.ANTISEPSIS) == rules.healing.surgery_infection_cut_pct
    assert threshold(rules.healing, MedicineTier.SURGERY) == rules.healing.surgery_level
    assert threshold(rules.healing, MedicineTier.IMMUNISATION) == MEDICINE[MedicineTier.IMMUNISATION].level
    assert FANATICISMS[FanaticismKind.ICONOCLASM].act is ActKind.ICONOCLASM and FANATICISMS[FanaticismKind.CRUSADE].act is ActKind.CONVERSION_BY_FORCE
    assert GATHERING_RESULTS[GatheringOutcome.MASSACRE].thought is ThoughtKind.WITNESSED_ATROCITY and GATHERING_RESULTS[GatheringOutcome.VIOLENT].disrupts
    assert not GATHERING_RESULTS[GatheringOutcome.QUARRELSOME].disrupts
    assert LINE_OUTCOMES[LineOutcome.STERILE].sterile and LINE_OUTCOMES[LineOutcome.UNSTABLE].stability_rule == "unstable_stability"
    assert rules.living_methods.unstable_stability == 30
    assert holy_edge(rules, None, frozenset({FoeNature.VOID})) == 1.0
