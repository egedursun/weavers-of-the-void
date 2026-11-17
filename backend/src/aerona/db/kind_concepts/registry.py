from collections.abc import Mapping

from aerona.db.kind_concepts import crafts, cuisines, culture, dishes, drinks, dwellings, goods, nature, society
from aerona.db.kind_concepts.spec import ConceptSpec
from aerona.domain.enums.kinds import KindConcept

CONCEPTS: Mapping[KindConcept, ConceptSpec] = {
    spec.concept: spec
    for spec in (
        goods.SPEC,
        dishes.SPEC,
        drinks.SPEC,
        cuisines.SPEC,
        *crafts.SPECS,
        *society.SPECS,
        dwellings.SPEC,
        *nature.SPECS,
        *culture.SPECS,
    )
}
