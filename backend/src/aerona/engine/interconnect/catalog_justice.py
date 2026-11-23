from aerona.db.tables.justice import CaseWitnessRow, CrimeCaseRow, LawProposalRow, ProposalStanceRow
from aerona.engine.interconnect.registry import Coupling, EdgeKind, Exposure, Mechanic, Subsystem, Surface

JUSTICE = "section-justice"
S = Subsystem
E = EdgeKind

JUSTICE_MECHANICS: tuple[Mechanic, ...] = (
    Mechanic(
        key="enactment",
        spec_item="S4.5/RP2",
        title="Laws pass as proposals that move by the weight of voices for and against them; estates and hooks stall or carry them",
        subsystem=S.LAW,
        phases=("legislature", "polity_cycles"),
        surface=Surface(drawer=JUSTICE),
        backfill="none: realms bring their laws forward from the next epoch",
        templates=("enactment.debate", "enactment.riot", "enactment.compromise", "enactment.obstruction", "enactment.failed"),
        fields=("progress", "support", "opposition", "stalled_epochs", "state", "params", "stance", "weight", "hooked"),
        tables=(LawProposalRow.__tablename__, ProposalStanceRow.__tablename__),
        exposure=Exposure.TOOL,
        tools=("propose_law", "enact_law"),
        targets=("polity", "mortal", "faction", "cult"),
        couplings=(
            Coupling(S.POLITY, "the realm's way of deciding sets whose voice weighs most", E.MODIFIER, "enactment.ruler_weight"),
            Coupling(S.INTRIGUE, "hooks over council members turn their votes, and a champion owes favours to those who carried the law", E.TRIGGER),
            Coupling(S.SOCIAL, "an estate with a council seat obstructs a law it opposes", E.MODIFIER, "enactment.estate_obstruct_pct"),
            Coupling(S.COMMUNICATION, "under an assembly the people's opinion of the champion sways the law", E.MODIFIER, "enactment.assembly_weight"),
            Coupling(S.SOCIAL, "riots over a disliked law raise the capital's unrest", E.FLOW, "enactment.riot_unrest"),
            Coupling(S.POLITY, "a proposal that stalls fails and costs its champion reputation", E.TRIGGER, "enactment.champion_cost"),
        ),
    ),
    Mechanic(
        key="trials",
        spec_item="S4.5/RP2",
        title="Crimes become cases with witnesses, an investigation that may torture or blame a scapegoat, and a trial by judge, jury, combat or ordeal",
        subsystem=S.LAW,
        phases=("settlement_life", "trials", "intrigue"),
        surface=Surface(drawer=JUSTICE),
        backfill="none: cases open from the next crimes",
        templates=("trials.condemned", "trials.acquitted"),
        fields=("evidence", "stage", "trial", "verdict", "wrongful", "tortured", "forged", "testimony", "reliability"),
        tables=(CrimeCaseRow.__tablename__, CaseWitnessRow.__tablename__),
        exposure=Exposure.TOOL,
        tools=(
            "accuse",
            "testify",
        ),
        targets=("mortal", "settlement", "polity"),
        couplings=(
            Coupling(S.BODY, "questioning under torture and trials by combat or ordeal wound the accused", E.FLOW, "trials.torture_hp"),
            Coupling(
                S.MIND, "an investigator questions under torture only where the law allows it and their ethics bear it", E.TRIGGER, "trials.torture_reading"
            ),
            Coupling(
                S.INTRIGUE,
                "known secrets strengthen a case, a framing scheme forges one, and hooks silence or turn witnesses",
                E.MODIFIER,
                "trials.secret_evidence",
            ),
            Coupling(S.POLITY, "wrongful convictions breed grievance toward the realm and unrest in the city", E.FLOW, "trials.injustice_grievance"),
            Coupling(
                S.SOCIAL,
                "the kin of the wrongly convicted hold it against the judge, and the wrongly executed become martyrs",
                E.TRIGGER,
                "trials.martyr_renown",
            ),
        ),
    ),
)
