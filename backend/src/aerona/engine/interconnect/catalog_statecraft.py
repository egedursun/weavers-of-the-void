from aerona.db.tables.polity import VassalageRow
from aerona.db.tables.statecraft import CrisisBackerRow, CrisisRow, DiplomacyProfileRow, PolityRegardRow, SphereRow
from aerona.engine.interconnect.registry import Coupling, EdgeKind, Exposure, Mechanic, Subsystem, Surface

STATECRAFT = "section-statecraft"
S = Subsystem
E = EdgeKind

STATECRAFT_MECHANICS: tuple[Mechanic, ...] = (
    Mechanic(
        key="threat_and_coalitions",
        spec_item="S4.6/RP2",
        title="Conquest, wars without a claim and broken treaties raise threat; realms that fear the same aggressor band into a coalition",
        subsystem=S.POLITY,
        phases=("statecraft", "war_upkeep", "treaty_cycles", "polity_cycles"),
        surface=Surface(drawer=STATECRAFT),
        backfill="none: realms take each other's measure from the next epoch",
        templates=("statecraft.coalition",),
        fields=("threat", "trust", "capacity", "relations", "strain"),
        tables=(PolityRegardRow.__tablename__, DiplomacyProfileRow.__tablename__),
        tools=("declare_neutral",),
        exposure=Exposure.CONTEXT,
        targets=("polity",),
        couplings=(
            Coupling(
                S.WAR,
                "a conquest or a war without a claim raises threat, more in neighbours and realms of distant values",
                E.TRIGGER,
                "statecraft.conquest_threat",
            ),
            Coupling(S.WAR, "a coalition stronger than its foe goes to war", E.TRIGGER, "statecraft.coalition_war_pct"),
            Coupling(S.LAW, "a broken treaty costs trust and a kept one earns it", E.MODIFIER, "statecraft.breach_trust"),
            Coupling(S.HOUSEHOLD, "a marriage pact soothes threat between realms", E.MODIFIER, "statecraft.marriage_threat"),
            Coupling(S.COMMUNICATION, "relations past a realm's capacity sour with every partner", E.FLOW, "statecraft.strain_decay"),
        ),
    ),
    Mechanic(
        key="crises",
        spec_item="S4.6/RP2",
        title="A demand to cede land, release a vassal, convert or pay opens a crisis; backers weigh in until a side yields or it becomes war",
        subsystem=S.POLITY,
        phases=("statecraft",),
        surface=Surface(drawer=STATECRAFT),
        backfill="none: crises open from the next claims, holy wars and debts",
        templates=("statecraft.crisis", "statecraft.crisis_backed_down", "statecraft.crisis_conceded", "statecraft.crisis_war"),
        fields=("demand", "escalation", "state", "amount", "side", "promised", "swing"),
        tables=(CrisisRow.__tablename__, CrisisBackerRow.__tablename__),
        exposure=Exposure.TOOL,
        tools=("issue_demand", "back_crisis"),
        targets=("polity",),
        couplings=(
            Coupling(S.WAR, "a war over a claim, a faith or a debt may open as a crisis instead", E.TRIGGER, "statecraft.crisis_pct"),
            Coupling(S.INTRIGUE, "a demander owes a favour to swing parties who backed it", E.TRIGGER, "statecraft.swing_promise"),
            Coupling(S.POLITY, "the side that backs down loses legitimacy", E.MODIFIER, "statecraft.back_down_legitimacy"),
            Coupling(S.FAITH, "a realm that concedes takes up the demander's faith", E.TRIGGER),
        ),
    ),
    Mechanic(
        key="spheres",
        spec_item="S4.6/RP2",
        title="Great powers draw weaker neighbours into spheres, favour and protect their clients, contest each other's and meet in summits",
        subsystem=S.POLITY,
        phases=("statecraft",),
        surface=Surface(drawer=STATECRAFT),
        backfill="none: spheres form from the next epoch",
        templates=("statecraft.sphere", "statecraft.summit"),
        fields=("strength",),
        tables=(SphereRow.__tablename__,),
        exposure=Exposure.CONTEXT,
        targets=("polity",),
        couplings=(
            Coupling(S.WAR, "a power goes to war for a client that is attacked", E.TRIGGER),
            Coupling(S.ECONOMY, "a client is favoured in trade with its power", E.MODIFIER, "statecraft.sphere_regard"),
            Coupling(S.POLITY, "a contested client slips toward the stronger power", E.FLOW, "statecraft.sphere_contest"),
        ),
    ),
    Mechanic(
        key="subjects",
        spec_item="S4.6/RP2",
        title="Subjects of every kind owe typed duties, hold contract rights and wish for liberty",
        subsystem=S.POLITY,
        phases=("statecraft", "treaty_cycles", "titles"),
        surface=Surface(drawer=STATECRAFT),
        backfill="none: subjects take their kind as their next terms are set",
        templates=("statecraft.terms",),
        fields=("kind", "liberty", "private_war", "coinage", "confirm_succession", "confirmed_ruler_entity_id"),
        tables=(VassalageRow.__tablename__,),
        exposure=Exposure.CONTEXT,
        targets=("polity",),
        couplings=(
            Coupling(S.ECONOMY, "only vassals, tributaries and colonies pay tribute, and a subject without coinage rights mints no coin", E.MODIFIER),
            Coupling(S.WAR, "only vassals, marches and colonies send levies, and a subject without the right of private war makes none", E.MODIFIER),
            Coupling(S.POLITY, "a subject wishing hard for liberty demands better terms or rises", E.TRIGGER, "statecraft.liberty_revolt"),
            Coupling(
                S.POLITY,
                "a subject far from its overlord is a tributary, one in its sphere a client and a small unarmed neighbour a protectorate",
                E.TRIGGER,
                "statecraft.protectorate_tiers",
            ),
            Coupling(S.WAR, "an overlord joins the wars of its clients and protectorates", E.TRIGGER),
        ),
    ),
)
