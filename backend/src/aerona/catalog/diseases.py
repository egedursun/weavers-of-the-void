from types import MappingProxyType

from aerona.domain.enums.disease import DiseaseTarget, DiseaseVector

VECTOR_LABELS = MappingProxyType(
    {
        DiseaseVector.AIR: "airborne",
        DiseaseVector.WATER: "waterborne",
        DiseaseVector.TOUCH: "contact",
        DiseaseVector.BITE: "bite-borne",
        DiseaseVector.SPIRIT: "spirit-borne",
        DiseaseVector.VOID: "void-borne",
        DiseaseVector.CURSE: "cursed",
    }
)
VECTOR_FUNCTIONS = MappingProxyType(
    {
        DiseaseVector.AIR: (DiseaseTarget.BREATH, DiseaseTarget.VITAL),
        DiseaseVector.WATER: (DiseaseTarget.VITAL,),
        DiseaseVector.TOUCH: (DiseaseTarget.SKIN, DiseaseTarget.SIGHT),
        DiseaseVector.BITE: (DiseaseTarget.VITAL, DiseaseTarget.COGNITION),
        DiseaseVector.SPIRIT: (DiseaseTarget.COGNITION,),
        DiseaseVector.VOID: (DiseaseTarget.COGNITION, DiseaseTarget.VITAL),
        DiseaseVector.CURSE: (DiseaseTarget.VITAL, DiseaseTarget.SKIN),
    }
)
VECTOR_STIGMA = MappingProxyType(
    {
        DiseaseVector.AIR: 20,
        DiseaseVector.WATER: 15,
        DiseaseVector.TOUCH: 70,
        DiseaseVector.BITE: 10,
        DiseaseVector.SPIRIT: 50,
        DiseaseVector.VOID: 80,
        DiseaseVector.CURSE: 90,
    }
)
