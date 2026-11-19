from aerona.catalog.kinds.definition import Defined
from aerona.core.total import total
from aerona.domain.enums.population import PopulationInstrument

POPULATION_INSTRUMENT = total(
    PopulationInstrument,
    {
        PopulationInstrument.BIRTH_REWARD: Defined("Birth reward", checked_by=("engine.numbers.book.birth_shift",), used_by=("engine.numbers.policies.adopt",)),
        PopulationInstrument.BIRTH_TAX: Defined("Birth tax", checked_by=("engine.numbers.book.birth_shift",), used_by=("engine.numbers.policies.adopt",)),
        PopulationInstrument.UNION_LAW: Defined("Union law", checked_by=("engine.numbers.book.birth_shift",), used_by=()),
        PopulationInstrument.CHILD_LIMIT: Defined(
            "Child limit", checked_by=("engine.numbers.book.PolicyBook.load",), used_by=("engine.numbers.policies.HARSH",)
        ),
        PopulationInstrument.CHILD_SUPPORT: Defined("Child support", checked_by=("engine.numbers.book.birth_shift",), used_by=()),
        PopulationInstrument.INHERITANCE_RULE: Defined("Inheritance rule", checked_by=("engine.numbers.book.birth_shift",), used_by=()),
        PopulationInstrument.SETTLEMENT_GRANT: Defined("Settlement grant", checked_by=(), used_by=("engine.numbers.policies.PULLS",)),
        PopulationInstrument.MIGRATION_PERMIT: Defined("Migration permit", checked_by=(), used_by=("engine.numbers.policies.PULLS",)),
        PopulationInstrument.MIGRATION_BAN: Defined("Migration ban", checked_by=("engine.numbers.policies.apply_instrument",), used_by=()),
        PopulationInstrument.EXPULSION: Defined(
            "Expulsion", checked_by=("engine.numbers.policies.apply_instrument",), used_by=("engine.numbers.policies.HARSH",)
        ),
        PopulationInstrument.RESETTLEMENT: Defined("Resettlement", checked_by=("engine.numbers.policies.apply_instrument",), used_by=()),
        PopulationInstrument.RECRUITMENT_ABROAD: Defined("Recruitment abroad", checked_by=(), used_by=("engine.numbers.policies.PULLS",)),
        PopulationInstrument.HEALTH_CAMPAIGN: Defined("Health campaign", checked_by=("engine.numbers.policies.apply_instrument",), used_by=()),
        PopulationInstrument.FAITH_TEACHING: Defined(
            "Faith teaching", checked_by=("engine.numbers.book.birth_shift", "engine.numbers.policies.keep_policy"), used_by=()
        ),
        PopulationInstrument.MADE_BIRTH: Defined("Made birth", checked_by=("engine.numbers.policies.apply_instrument",), used_by=()),
    },
)
