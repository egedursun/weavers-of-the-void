from dataclasses import dataclass

from aerona.rules.groups import RuleGroup
from aerona.rules.model import Spanned, rule, span


@dataclass(frozen=True)
class LanguageContactRules(Spanned):
    event_cap: int = rule(6, 0, 1000, RuleGroup.RELIGION_AND_LANGUAGE, "Most language contact events (bilingualism, shift, creole) per epoch")
    conquest_bilingual_chance: int = rule(
        20, 0, 100, RuleGroup.RELIGION_AND_LANGUAGE, "Chance per epoch a ruled community also starts speaking its ruler's language (%)"
    )
    conquest_shift_chance: int = rule(
        8, 0, 100, RuleGroup.RELIGION_AND_LANGUAGE, "Chance per epoch a ruled community that speaks its ruler's language drops its own (%)"
    )
    migration_bilingual_chance: int = rule(
        30, 0, 100, RuleGroup.RELIGION_AND_LANGUAGE, "Chance newly settled migrants also start speaking their neighbours' language (%)"
    )
    migration_window_years: int = span(25, 0, 2500, RuleGroup.RELIGION_AND_LANGUAGE, "Migrants count as new for this many years after the migration")
    trade_loan_chance: int = rule(
        15, 0, 100, RuleGroup.RELIGION_AND_LANGUAGE, "Chance per epoch one trading partner of another tongue borrows words from the other (%)"
    )
    trade_bilingual_chance: int = rule(
        3, 0, 100, RuleGroup.RELIGION_AND_LANGUAGE, "Chance per epoch the smaller trading partner also starts speaking the larger's language (%)"
    )
    contact_words: int = rule(2, 0, 100, RuleGroup.RELIGION_AND_LANGUAGE, "Most words borrowed in one contact per epoch")
    loan_cap: int = rule(40, 0, 100000, RuleGroup.RELIGION_AND_LANGUAGE, "Most words borrowed per epoch across all contacts")
    plague_shift_chance: int = rule(
        35, 0, 100, RuleGroup.RELIGION_AND_LANGUAGE, "Chance a bilingual community struck by plague drops its minority language (%)"
    )
    plague_spread_loss: int = rule(5, 0, 100, RuleGroup.RELIGION_AND_LANGUAGE, "Spread lost by the only language of a community struck by plague")
    creole_epochs: int = rule(
        3, 0, 1000, RuleGroup.RELIGION_AND_LANGUAGE, "A community speaking two languages for at least this many epochs can give birth to a creole"
    )
    creole_chance: int = rule(
        6, 0, 100, RuleGroup.RELIGION_AND_LANGUAGE, "Chance per epoch a bilingual community gives birth to a creole of its two languages (%)"
    )
    creole_words: int = rule(12, 0, 1000, RuleGroup.RELIGION_AND_LANGUAGE, "Most words a creole takes from each parent language")
    creole_power: int = rule(2, 1, 12, RuleGroup.RELIGION_AND_LANGUAGE, "Power level of a creole language")
    creole_cap: int = rule(1, 0, 100, RuleGroup.RELIGION_AND_LANGUAGE, "Most creoles born per epoch")
    stat_step: int = rule(2, 0, 100, RuleGroup.RELIGION_AND_LANGUAGE, "Most a language stat drifts per epoch")
    spread_mult_pct: int = rule(150, 0, 10000, RuleGroup.RELIGION_AND_LANGUAGE, "Spread target: the speakers' share of the world's population times this (%)")
    complexity_base: int = rule(20, 0, 100, RuleGroup.RELIGION_AND_LANGUAGE, "Base of the complexity target")
    complexity_word_divisor: int = rule(4, 1, 10000, RuleGroup.RELIGION_AND_LANGUAGE, "Complexity target gains the word count divided by this")
    complexity_word_cap: int = rule(50, 0, 100, RuleGroup.RELIGION_AND_LANGUAGE, "Most the lexicon adds to the complexity target")
    complexity_writing: int = rule(20, 0, 100, RuleGroup.RELIGION_AND_LANGUAGE, "Complexity a written language (or one spoken by those who know writing) gains")
    sacredness_piety_pct: int = rule(60, 0, 100, RuleGroup.RELIGION_AND_LANGUAGE, "Share of the speakers' mean piety in the sacredness target (%)")
    sacredness_cult: int = rule(15, 0, 100, RuleGroup.RELIGION_AND_LANGUAGE, "Sacredness each cult speaking the language adds")
    sacredness_cult_cap: int = rule(40, 0, 100, RuleGroup.RELIGION_AND_LANGUAGE, "Most cults add to sacredness")
    default_piety: int = rule(40, 0, 100, RuleGroup.RELIGION_AND_LANGUAGE, "Piety counted for a speaker whose piety is unrecorded")

    @property
    def migration_window(self) -> int:
        return self.epochs(self.migration_window_years)
