from aerona.domain.enums.genetics import Locus
from aerona.domain.enums.nature import SenseKind

SENSE_LOCI: dict[Locus, SenseKind] = {
    Locus.SIGHT: SenseKind.SIGHT,
    Locus.NIGHT_VISION: SenseKind.NIGHT_VISION,
    Locus.SMELL: SenseKind.SMELL,
    Locus.HEARING: SenseKind.HEARING,
}

LEANED_LOCUSS = (Locus.HEIGHT, Locus.GIANT_BLOOD, Locus.MUSCLE, Locus.BONE_DENSITY)
