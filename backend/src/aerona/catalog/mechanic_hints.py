import re

from aerona.domain.enums.society import NaturalLaw, ResourceMechanic

M = ResourceMechanic
L = NaturalLaw

RESOURCE_HINTS: tuple[tuple[ResourceMechanic, re.Pattern[str]], ...] = (
    (M.DECAYING, re.compile(r"\b(?:rot|rots|rotting|spoil|spoils|decay|decays|perish|fresh|fungus|fruit|milk|blood|resin|honey|pollen|nectar|mould|mold)\b")),
    (M.ADDICTIVE, re.compile(r"\b(?:addict\w*|intoxicat\w*|drunk\w*|ecstasy|craving|crave|incense|smoke|elixir|withdrawal|indispensable)\b")),
    (M.SENTIENT, re.compile(r"\b(?:sentient|whisper\w*|speaks|thinks|awake|chooses|wills|desires|its own will|breathes|dreams|ensouled)\b")),
    (M.DEPLETION_PRICE, re.compile(r"\b(?:last drop|when it runs out|if it runs dry|price is heavy|curse falls|cursed ground|doom|last grain|forbidden)\b")),
    (
        M.FIXED,
        re.compile(r"\b(?:never renew\w*|finite|limited|never forms again|single vein|unique|fallen from the sky|star dust|meteor\w*|previous creation)\b"),
    ),
    (M.SACRED, re.compile(r"\b(?:sacred|holy|hallowed|consecrat\w*|offering|divine|shrine|altar|temple)\b")),
)
SUBTYPE_LEANINGS: tuple[tuple[re.Pattern[str], ResourceMechanic], ...] = (
    (re.compile(r"\b(?:herb|plant|fungus|fruit|flower|root)\b"), M.DECAYING),
    (re.compile(r"\b(?:crystal|vein|ore|mine|ash|salt|glass)\b"), M.FIXED),
    (re.compile(r"\b(?:spring|well|water)\b"), M.SACRED),
    (re.compile(r"\b(?:magic|essence|light|dust)\b"), M.ADDICTIVE),
    (re.compile(r"\b(?:bone|blood|soul)\b"), M.DEPLETION_PRICE),
)
LAW_HINTS: tuple[tuple[NaturalLaw, re.Pattern[str]], ...] = (
    (L.DEAD_RETURN, re.compile(r"\b(?:the dead return|the dead rise|return as ghosts|come back|rise again)\b")),
    (L.IMMORTALITY, re.compile(r"\b(?:immortal\w*|never age|do not age|cannot die|death stops)\b")),
    (L.SHORT_LIFE, re.compile(r"\b(?:short li\w*|age quickly|die young|swift ageing|shortened lives)\b")),
    (L.MAGIC_PRICE, re.compile(r"\b(?:price of magic|magic demands|magic costs|blood for magic)\b")),
    (L.WAR_BAN, re.compile(r"\b(?:war is forbidden|no blood is shed|blades are not drawn|oath of peace)\b")),
    (L.BOUNTY, re.compile(r"\b(?:bounty|plenty|harvest|abundance|seed time)\b")),
    (L.DROUGHT, re.compile(r"\b(?:drought|famine|the soil dries|no rain|desert\w*)\b")),
    (L.SEA_BAN, re.compile(r"\b(?:seas cannot be crossed|no ship|sea is forbidden|beyond the shore)\b")),
    (L.ONE_LANGUAGE, re.compile(r"\b(?:one tongue|one language|all tongues|common tongue|languages merge)\b")),
    (L.DISASTERS, re.compile(r"\b(?:disaster\w*|earthquake\w*|storm\w*|calamit\w*|deluge)\b")),
)
