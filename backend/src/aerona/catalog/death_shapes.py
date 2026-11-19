from aerona.domain.enums.death_work import RemainsTreatment
from aerona.domain.enums.demography import FuneralCustom
from aerona.domain.enums.mind import Profession, SkillKind

TREATMENT_COST_PCT: dict[RemainsTreatment, int] = {
    RemainsTreatment.BURIAL: 100,
    RemainsTreatment.CREMATION: 120,
    RemainsTreatment.EXPOSURE: 30,
    RemainsTreatment.PRESERVATION: 300,
    RemainsTreatment.WATER: 60,
    RemainsTreatment.CONSUMPTION: 40,
    RemainsTreatment.STORAGE: 150,
    RemainsTreatment.RETURN_TO_MAKER: 50,
    RemainsTreatment.RELEASE: 20,
    RemainsTreatment.NONE_NEEDED: 0,
}

TREATMENT_SANITATION: dict[RemainsTreatment, int] = {
    RemainsTreatment.BURIAL: 0,
    RemainsTreatment.CREMATION: 1,
    RemainsTreatment.EXPOSURE: -2,
    RemainsTreatment.PRESERVATION: 0,
    RemainsTreatment.WATER: -1,
    RemainsTreatment.CONSUMPTION: -1,
    RemainsTreatment.STORAGE: -1,
    RemainsTreatment.RETURN_TO_MAKER: 0,
    RemainsTreatment.RELEASE: 0,
    RemainsTreatment.NONE_NEEDED: 0,
}

TREATMENT_SPIRIT_PCT: dict[RemainsTreatment, int] = {
    RemainsTreatment.BURIAL: 100,
    RemainsTreatment.CREMATION: 70,
    RemainsTreatment.EXPOSURE: 120,
    RemainsTreatment.PRESERVATION: 130,
    RemainsTreatment.WATER: 90,
    RemainsTreatment.CONSUMPTION: 60,
    RemainsTreatment.STORAGE: 110,
    RemainsTreatment.RETURN_TO_MAKER: 0,
    RemainsTreatment.RELEASE: 0,
    RemainsTreatment.NONE_NEEDED: 0,
}

GROUND_REMAINS = frozenset({RemainsTreatment.BURIAL, RemainsTreatment.PRESERVATION, RemainsTreatment.STORAGE})

REACHABLE_REMAINS = frozenset({RemainsTreatment.BURIAL, RemainsTreatment.PRESERVATION, RemainsTreatment.STORAGE, RemainsTreatment.EXPOSURE})

RITE_TREATMENTS: dict[FuneralCustom, tuple[RemainsTreatment, ...]] = {
    FuneralCustom.BURIAL: (RemainsTreatment.BURIAL, RemainsTreatment.STORAGE),
    FuneralCustom.CREMATION: (RemainsTreatment.CREMATION,),
    FuneralCustom.SKY_BURIAL: (RemainsTreatment.EXPOSURE,),
    FuneralCustom.SEA_BURIAL: (RemainsTreatment.WATER,),
    FuneralCustom.ENTOMBMENT: (RemainsTreatment.PRESERVATION, RemainsTreatment.STORAGE, RemainsTreatment.BURIAL),
    FuneralCustom.ANCESTOR_SHRINE: (RemainsTreatment.PRESERVATION, RemainsTreatment.STORAGE),
    FuneralCustom.ENDOCANNIBALISM: (RemainsTreatment.CONSUMPTION,),
    FuneralCustom.REANIMATION: (RemainsTreatment.PRESERVATION, RemainsTreatment.BURIAL),
    FuneralCustom.SOUL_BINDING: (RemainsTreatment.RELEASE, RemainsTreatment.STORAGE),
    FuneralCustom.NAMELESS: (RemainsTreatment.BURIAL, RemainsTreatment.EXPOSURE, RemainsTreatment.WATER),
    FuneralCustom.NONE: (RemainsTreatment.NONE_NEEDED, RemainsTreatment.RELEASE, RemainsTreatment.BURIAL),
}

CALLED_PROFESSIONS = frozenset({Profession.DEATH_WORKER})

DEATH_SKILLS = (SkillKind.RITUAL, SkillKind.MEDICINE)
