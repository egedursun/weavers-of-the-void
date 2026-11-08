from types import MappingProxyType

from aerona.domain.enums.disease import ClimateAffinity, DiseaseTarget, DiseaseVector

VECTOR_NOUNS = MappingProxyType(
    {
        DiseaseVector.AIR: ("cough", "breathing sickness", "grey lung", "choking fever"),
        DiseaseVector.WATER: ("flux", "bloody flux", "river sickness", "marsh fever"),
        DiseaseVector.TOUCH: ("pox", "rot", "weeping sores", "blight of the skin"),
        DiseaseVector.BITE: ("ague", "shaking fever", "swamp fever", "bite sickness"),
        DiseaseVector.SPIRIT: ("dreaming sickness", "soul fever", "hollowing", "ghost cough"),
        DiseaseVector.VOID: ("void blight", "starless rot", "unmaking", "pale emptiness"),
        DiseaseVector.CURSE: ("curse sickness", "black sending", "god-blight", "withering doom"),
    }
)
CLIMATE_WORDS = MappingProxyType(
    {
        ClimateAffinity.WARM: ("red", "burning", "summer"),
        ClimateAffinity.WET: ("wet", "green", "marsh"),
        ClimateAffinity.COLD: ("white", "winter", "frost"),
        ClimateAffinity.DRY: ("dust", "yellow", "thirsting"),
        ClimateAffinity.ANY: ("great", "grey", "creeping"),
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
STRAIN_WORDS = ("new", "second", "black", "swift", "returning", "hidden")
TRADITION_NAMES = ("the Survivors' Feast", "the Bell of the Dead", "the Smoke Walk", "the Night of Masks", "the Pit Vigil", "the Mourners' Fast")
