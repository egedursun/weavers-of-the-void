from aerona.domain.enums.titles import TitleRank, TitleTenure

TIER_RANKS: tuple[TitleRank, ...] = (TitleRank.LORDSHIP, TitleRank.COUNTY, TitleRank.DUCHY, TitleRank.KINGDOM, TitleRank.EMPIRE)
FAITH_RANKS: tuple[TitleRank, ...] = (TitleRank.SEE, TitleRank.ARCHSEE, TitleRank.HIGH_SEAT)
SEAT_RANKS = frozenset({*FAITH_RANKS, TitleRank.CAPTAINCY, TitleRank.GUILDMASTERSHIP})
RANK_WORDS: dict[TitleRank, str] = {
    TitleRank.LORDSHIP: "Lordship",
    TitleRank.COUNTY: "County",
    TitleRank.DUCHY: "Duchy",
    TitleRank.KINGDOM: "Kingdom",
    TitleRank.EMPIRE: "Empire",
    TitleRank.SEE: "See",
    TitleRank.ARCHSEE: "Archsee",
    TitleRank.HIGH_SEAT: "High Seat",
    TitleRank.CAPTAINCY: "Captaincy",
    TitleRank.GUILDMASTERSHIP: "Guildmastership",
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
