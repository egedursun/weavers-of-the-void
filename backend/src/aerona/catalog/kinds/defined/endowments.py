from aerona.catalog.kinds.definition import Defined
from aerona.core.total import total
from aerona.domain.enums.endowments import EndowmentPurpose, EndowmentTerms

ENDOWMENT_PURPOSE = total(
    EndowmentPurpose,
    {
        EndowmentPurpose.RELIEF: Defined(
            "Relief",
            checked_by=("catalog.life.endowments.TOWN_EFFECTS",),
            used_by=("db.tables.endowments.EndowmentRow", "engine.endowments.seed.seed_endowments"),
        ),
        EndowmentPurpose.LEARNING: Defined("Learning", checked_by=("engine.endowments.trust.serve",), used_by=()),
        EndowmentPurpose.WORSHIP: Defined("Worship", checked_by=("catalog.life.endowments.TOWN_EFFECTS",), used_by=()),
        EndowmentPurpose.HEALTH: Defined("Health", checked_by=("catalog.life.endowments.TOWN_EFFECTS",), used_by=()),
        EndowmentPurpose.WORKS: Defined("Works", checked_by=("catalog.life.endowments.TOWN_EFFECTS",), used_by=()),
        EndowmentPurpose.ART: Defined("Art", checked_by=("engine.endowments.trust.serve",), used_by=()),
        EndowmentPurpose.KIN: Defined("Kin", checked_by=("engine.endowments.trust.serve",), used_by=()),
        EndowmentPurpose.MEMORY: Defined("Memory", checked_by=("engine.endowments.trust.serve",), used_by=()),
        EndowmentPurpose.RESEARCH: Defined("Research", checked_by=("engine.endowments.trust.serve",), used_by=()),
        EndowmentPurpose.HOSPITALITY: Defined("Hospitality", checked_by=("catalog.life.endowments.TOWN_EFFECTS",), used_by=()),
        EndowmentPurpose.RANSOM: Defined("Ransom", checked_by=("engine.endowments.trust.serve",), used_by=()),
    },
)

ENDOWMENT_TERMS = total(
    EndowmentTerms,
    {
        EndowmentTerms.PERPETUAL: Defined("Perpetual", checked_by=(), used_by=("db.tables.endowments.EndowmentRow",)),
        EndowmentTerms.FOR_A_TERM: Defined("For a term", checked_by=("engine.endowments.trust.end_by_terms",), used_by=()),
        EndowmentTerms.CONDITIONAL: Defined("Conditional", checked_by=("engine.endowments.trust.end_by_terms",), used_by=()),
    },
)
