from dataclasses import dataclass

from aerona.rules.groups import RuleGroup
from aerona.rules.model import rule

L = RuleGroup.LANGUAGE_AND_NAMES


@dataclass(frozen=True)
class SoundChangeRules:
    base_pct: int = rule(6, 0, 100, L, "Chance a living language takes a new sound change each epoch when it stands alone (%)")
    contact_pct: int = rule(4, 0, 100, L, "Extra chance for each other tongue its speakers also speak (%)")
    migration_pct: int = rule(8, 0, 100, L, "Extra chance when its speakers moved to a new land this epoch (%)")
    prestige_gap: int = rule(25, 0, 100, L, "Prestige by which a neighbouring tongue must outrank it before its sounds are copied")
    most: int = rule(24, 0, 200, L, "Sound changes a language holds at most before older ones fade into its proto-forms")
    per_epoch: int = rule(60, 0, 10000, L, "Languages that may take a new sound change each epoch at most")
    reconstruct_pct: int = rule(20, 0, 100, L, "Chance a scholar who knows two daughter tongues recovers a proto-word of their dead parent each epoch (%)")
    reconstruct_skill: int = rule(40, 0, 100, L, "Languages skill a scholar needs to reconstruct proto-words")


@dataclass(frozen=True)
class GrammarRules:
    misread_pct: int = rule(40, 0, 200, L, "Extra misreading between two tongues at the greatest grammatical distance (%)")
    loan_isolating_pct: int = rule(150, 0, 300, L, "Loanwords an isolating tongue takes compared with the usual (%)")
    loan_polysynthetic_pct: int = rule(50, 0, 300, L, "Loanwords a polysynthetic tongue takes compared with the usual (%)")
    convergence_pct: int = rule(10, 0, 100, L, "Chance each epoch a tongue takes the word order of a prestigious tongue its speakers also speak (%)")
    creole_cases: int = rule(0, 0, 20, L, "Cases a newborn creole or pidgin keeps")
    compound_pct: int = rule(60, 0, 100, L, "Chance an agglutinative or polysynthetic tongue composes a new name from two of its words (%)")


@dataclass(frozen=True)
class SemanticDriftRules:
    drift_pct: int = rule(3, 0, 100, L, "Chance each epoch that one word of a living language shifts its meaning (%)")
    taboo_terror: int = rule(70, 0, 100, L, "Terror a beast must hold before the folk who dread it stop saying its name")
    taboo_pct: int = rule(25, 0, 100, L, "Chance each epoch the folk replace the name of a dreaded or holy thing with a euphemism (%)")
    per_epoch: int = rule(40, 0, 10000, L, "Words that may shift or be replaced each epoch at most")


@dataclass(frozen=True)
class ScriptEvolutionRules:
    evolve_pct: int = rule(4, 0, 100, L, "Chance each epoch a written language moves its script one step along the chain (%)")
    merchant_share: int = rule(15, 0, 100, L, "Share of merchants among a language's speakers that wears its script simpler (%)")
    reform_standard: int = rule(60, 0, 100, L, "Standardisation past which a language may reform its script")
    borrow_pct: int = rule(10, 0, 100, L, "Chance each epoch an unwritten language borrows the script of a tongue its speakers also speak (%)")
    borrowed_signs: int = rule(3, 0, 100, L, "Signs a borrowed script gains for the borrower's own sounds")


@dataclass(frozen=True)
class DecipherRules:
    base: int = rule(2, 0, 100, L, "Progress a decipherment makes each epoch a scholar works on it")
    skill_pct: int = rule(8, 0, 100, L, "Progress for each full measure of the scholar's languages skill (%)")
    corpus_step: int = rule(5, 1, 1000, L, "Surviving texts that add one step of progress each epoch")
    bilingual: int = rule(10, 0, 100, L, "Progress a bilingual text adds each epoch")
    cognate: int = rule(4, 0, 100, L, "Progress a living daughter or sister tongue adds each epoch")
    error_pct: int = rule(15, 0, 100, L, "Chance each epoch a partial decipherment takes in a misreading (%)")
    legend_errors: int = rule(3, 0, 100, L, "Misreadings past which one becomes a legend among the scholar's people")
    bilingual_find_pct: int = rule(25, 0, 100, L, "Chance a book found in an excavation is a bilingual text of a dead tongue (%)")


@dataclass(frozen=True)
class PidginRules:
    contact_pct: int = rule(20, 0, 100, L, "Chance each epoch traders who share no tongue make a pidgin (%)")
    creole_after: int = rule(2, 0, 100, L, "Epochs after which children raised in a pidgin make it a creole")
    native_share: int = rule(30, 0, 100, L, "Share of a community that must speak a pidgin before its children take it as their own (%)")


@dataclass(frozen=True)
class LanguagePolicyRules:
    official_pct: int = rule(10, 0, 100, L, "Chance each epoch a realm without an official tongue makes its ruler's tongue official (%)")
    official_gain: int = rule(4, 0, 100, L, "Second-tongue share an official tongue gains among its subjects each epoch at full strength")
    suppress_loss: int = rule(5, 0, 100, L, "Speaker share a suppressed tongue loses each epoch at full strength")
    suppress_cohesion: int = rule(3, 0, 100, L, "Cohesion the speakers of a suppressed tongue lose each epoch at full strength")
    suppress_unrest: int = rule(4, 0, 100, L, "Unrest the speakers of a suppressed tongue gain each epoch at full strength")
    revival_gain: int = rule(4, 0, 100, L, "Speaker share a revived tongue gains each epoch at full strength")
    revival_pct: int = rule(20, 0, 100, L, "Chance each epoch a revival brings a dead tongue back to life (%)")


@dataclass(frozen=True)
class ModalityRules:
    scent_trace_pct: int = rule(20, 0, 100, L, "Extra chance a spy among scent speakers is found out by the traces it leaves (%)")
    unwritten_literacy_pct: int = rule(50, 0, 100, L, "Literacy a tongue that cannot be written keeps through other records (%)")


@dataclass(frozen=True)
class DivineTongueRules:
    rite_pct: int = rule(15, 0, 100, L, "Extra strength a rite gains when its caster speaks its god's tongue (%)")
    learn_pct: int = rule(30, 0, 100, L, "Chance a mortal its god speaks to in a dream learns some of the divine tongue (%)")
    words: int = rule(12, 0, 200, L, "Words a divine tongue holds when it is first spoken")
