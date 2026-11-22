from aerona.domain.enums.discovery import TheoryDomain
from aerona.domain.enums.folk_knowledge import FolkDomain

THEORY_DOMAINS: dict[TheoryDomain, tuple[FolkDomain, ...]] = {
    TheoryDomain.MEDICINE: (FolkDomain.BODY, FolkDomain.ILLNESS),
    TheoryDomain.COSMOLOGY: (FolkDomain.SKY, FolkDomain.TIME),
    TheoryDomain.MATTER: (FolkDomain.MATTER,),
    TheoryDomain.LIFE: (FolkDomain.PLANTS, FolkDomain.ANIMALS),
    TheoryDomain.MIND: (FolkDomain.MIND,),
    TheoryDomain.SOCIETY: (FolkDomain.SOCIETY,),
}
