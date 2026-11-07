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
            "Titles from lordships to empires rule their de jure lands by right; the ruler of a realm holds its primary title, lands held long "
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
)
