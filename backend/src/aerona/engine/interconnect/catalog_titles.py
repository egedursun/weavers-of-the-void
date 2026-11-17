from aerona.db.tables.titles import DeJureLinkRow, TitleHolderRow, TitleProfileRow
from aerona.engine.interconnect.registry import Coupling, EdgeKind, Exposure, Mechanic, Subsystem, Surface

TITLES = "section-titles"
S = Subsystem
E = EdgeKind

TITLE_MECHANICS: tuple[Mechanic, ...] = (
    Mechanic(
        key="titles",
        spec_item="S4.11",
        title=(
            "Titles from local to imperial tiers rule their de jure lands by right; the ruler of a realm holds its primary title, lands held long "
            "under another title drift into it, and realms claim, usurp, create and restore titles"
        ),
        subsystem=S.POLITY,
        phases=("titles",),
        surface=Surface(drawer=TITLES, layer="map-layer-de-jure"),
        backfill="titles: every realm founds its primary title over its lands",
        templates=("titles.created", "titles.usurped", "titles.restored", "titles.partition"),
        fields=("rank", "holder_node_id", "de_jure_liege_entity_id", "prestige", "emblem", "drift", "destroyed_epoch"),
        tables=(TitleProfileRow.__tablename__, TitleHolderRow.__tablename__, DeJureLinkRow.__tablename__),
        exposure=Exposure.TOOL,
        tools=("seize_title",),
        targets=("polity", "mortal", "region"),
        couplings=(
            Coupling(
                S.POLITY,
                "the holder of a realm's primary title holds its throne, and a mortal holding two top titles rules both realms",
                E.TRIGGER,
                "titles.union_pct",
            ),
            Coupling(S.WAR, "a realm holding lands of another title presses a claim on it", E.TRIGGER, "titles.claim_strength"),
            Coupling(S.LAW, "an equal inheritance divides a late ruler's lesser titles and their lands among the heirs", E.TRIGGER),
            Coupling(S.POLITY, "usurping a title costs the usurper's realm legitimacy", E.MODIFIER, "titles.usurp_legitimacy"),
            Coupling(S.ENVIRONMENT, "lands held long under another title drift into it", E.FLOW, "titles.drift_epochs"),
        ),
    ),
    Mechanic(
        key="seats",
        spec_item="S4.11",
        title=(
            "Faiths raise local, high and foremost seats for their foremost cleric, and free companies and guilds raise "
            "military commands and guild headships for their leaders, who gain prestige by them"
        ),
        subsystem=S.POLITY,
        phases=("titles",),
        surface=Surface(drawer=TITLES),
        backfill="none: seats rise from the next epoch",
        templates=("titles.seat_founded",),
        fields=("rank", "holder_node_id", "prestige", "capital_entity_id"),
        tables=(TitleProfileRow.__tablename__, TitleHolderRow.__tablename__),
        exposure=Exposure.CONTEXT,
        targets=("cult", "faction", "mortal"),
        couplings=(
            Coupling(
                S.FAITH,
                "a faith with enough followers raises a local seat, then a high seat, and the largest of a world holds the foremost seat",
                E.TRIGGER,
                "titles.faith_local_followers",
            ),
            Coupling(S.SOCIAL, "the holder of a seat gains prestige each epoch by its rank", E.FLOW, "titles.seat_prestige"),
        ),
    ),
)
