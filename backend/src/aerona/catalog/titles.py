from aerona.domain.enums.titles import TitleTenure, TitleTier

TIER_RANKS: tuple[TitleTier, ...] = (TitleTier.LOCAL, TitleTier.DISTRICT, TitleTier.REGIONAL, TitleTier.REALM, TitleTier.IMPERIAL)
FAITH_RANKS: tuple[TitleTier, ...] = (TitleTier.FAITH_LOCAL, TitleTier.FAITH_HIGH, TitleTier.FAITH_SUPREME)
SEAT_RANKS = frozenset({*FAITH_RANKS, TitleTier.MILITARY, TitleTier.GUILD})
RANK_WORDS: dict[TitleTier, str] = {
    TitleTier.LOCAL: "Lordship",
    TitleTier.DISTRICT: "County",
    TitleTier.REGIONAL: "Duchy",
    TitleTier.REALM: "Kingdom",
    TitleTier.IMPERIAL: "Empire",
    TitleTier.FAITH_LOCAL: "See",
    TitleTier.FAITH_HIGH: "Archsee",
    TitleTier.FAITH_SUPREME: "High Seat",
    TitleTier.MILITARY: "Captaincy",
    TitleTier.GUILD: "Guildmastership",
}
TENURE_LABELS: dict[TitleTenure, str] = {
    TitleTenure.FOUNDED: "Founded",
    TitleTenure.INHERITED: "Inherited",
    TitleTenure.CREATED: "Created",
    TitleTenure.USURPED: "Usurped",
    TitleTenure.GRANTED: "Granted",
    TitleTenure.RESTORED: "Restored",
}
TINCTURES: tuple[str, ...] = ("Or", "Argent", "Gules", "Azure", "Vert", "Sable", "Purpure", "Tenné", "Sanguine")
CHARGES: tuple[str, ...] = (
    "a tower",
    "a crescent",
    "a star",
    "a key",
    "a wheel",
    "a hand",
    "an eye",
    "a crown",
    "a tree",
    "a ship",
    "a sun",
    "a bird",
    "a beast",
    "a sword",
    "a book",
)
