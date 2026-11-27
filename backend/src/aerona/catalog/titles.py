from aerona.domain.enums.titles import TitleTenure, TitleTier

TIER_RANKS: tuple[TitleTier, ...] = (TitleTier.LOCAL, TitleTier.DISTRICT, TitleTier.REGIONAL, TitleTier.REALM, TitleTier.IMPERIAL)
FAITH_RANKS: tuple[TitleTier, ...] = (TitleTier.FAITH_LOCAL, TitleTier.FAITH_HIGH, TitleTier.FAITH_SUPREME)
SEAT_RANKS = frozenset({*FAITH_RANKS, TitleTier.MILITARY, TitleTier.GUILD})
RANK_WORDS: dict[TitleTier, str] = {
    TitleTier.LOCAL: "Local title",
    TitleTier.DISTRICT: "District title",
    TitleTier.REGIONAL: "Regional title",
    TitleTier.REALM: "Realm title",
    TitleTier.IMPERIAL: "Imperial title",
    TitleTier.FAITH_LOCAL: "Local seat of a faith",
    TitleTier.FAITH_HIGH: "High seat of a faith",
    TitleTier.FAITH_SUPREME: "Foremost seat of a faith",
    TitleTier.MILITARY: "Military command",
    TitleTier.GUILD: "Headship of an association",
    TitleTier.LEAGUE: "Headship of a league",
}
TITLE_NAMES: dict[TitleTier, str] = {
    TitleTier.LOCAL: "local title",
    TitleTier.DISTRICT: "district title",
    TitleTier.REGIONAL: "regional title",
    TitleTier.REALM: "title",
    TitleTier.IMPERIAL: "imperial title",
    TitleTier.FAITH_LOCAL: "local seat",
    TitleTier.FAITH_HIGH: "high seat",
    TitleTier.FAITH_SUPREME: "foremost seat",
    TitleTier.MILITARY: "command",
    TitleTier.GUILD: "headship",
    TitleTier.LEAGUE: "headship",
}


def title_name(rank: TitleTier, holder: str) -> str:
    return f"the {TITLE_NAMES[rank]} of {holder}"


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
