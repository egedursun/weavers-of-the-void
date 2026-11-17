from aerona.catalog.kinds.definition import Defined
from aerona.core.total import total
from aerona.domain.enums.culture_kinds import TenetScope

TENET_SCOPE = total(
    TenetScope,
    {
        TenetScope.DOCTRINE: Defined("Doctrine", checked_by=(), used_by=("db.kind_concepts.culture.built_in_tenets",)),
        TenetScope.IDEOLOGY: Defined("Ideology", checked_by=(), used_by=("db.kind_concepts.culture.built_in_tenets",)),
        TenetScope.IDEA: Defined("Idea", checked_by=(), used_by=("db.kind_concepts.culture.built_in_tenets",)),
    },
)
