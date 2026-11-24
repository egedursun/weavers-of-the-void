from aerona.domain.enums.childhood import PedagogyTheory, SocializationTechnique
from aerona.domain.enums.mortal import LifeStage

THEORY_SPEED = {
    PedagogyTheory.ROTE: 60,
    PedagogyTheory.DIALECTIC: 80,
    PedagogyTheory.APPRENTICESHIP: 70,
    PedagogyTheory.DISCOVERY: 90,
    PedagogyTheory.RITUAL_TRANSMISSION: 50,
    PedagogyTheory.EXAMINATION: 70,
    PedagogyTheory.NETWORK_LEARNING: 100,
    PedagogyTheory.MIND_TRANSFER: 120,
    PedagogyTheory.PEER_TEACHING: 75,
}


HARSH = (SocializationTechnique.SHAME, SocializationTechnique.PUNISHMENT, SocializationTechnique.RITUAL_ORDEAL)


SOCIABLE = (SocializationTechnique.PLAY, SocializationTechnique.PEER_GROUP)

YOUNG_ONES_LIFE_STAGES = (LifeStage.INFANT, LifeStage.CHILD, LifeStage.YOUTH)
