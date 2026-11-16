from aerona.db.tables.council_order import CouncilProcedureRow, CouncilViolationRow, DivineSeatRow
from aerona.engine.interconnect.registry import Coupling, EdgeKind, Exposure, Mechanic, Subsystem, Surface

S = Subsystem
E = EdgeKind

COUNCIL_ORDER_MECHANICS: tuple[Mechanic, ...] = (
    Mechanic(
        key="council_order",
        spec_item="S47.5",
        title="How the council decides, which gods sit on it, the Creator's veto and the ladder of penalties for breaking its rulings",
        subsystem=S.GODS,
        phases=("council_rulings",),
        surface=Surface(drawer="section-god-council"),
        backfill="council_rulings: the council is given its procedure and every son a seat by right on the first epoch",
        templates=("council.violation", "council.engine_held"),
        tables=(CouncilProcedureRow.__tablename__, DivineSeatRow.__tablename__, CouncilViolationRow.__tablename__),
        exposure=Exposure.NONE,
        tools=(),
        targets=("son", "foreign_god"),
        couplings=(
            Coupling(S.GODS, "a god that breaks a ruling climbs the ladder from censure to a war of gods", E.TRIGGER, "council.sanction_essence"),
            Coupling(S.COSMOS, "a tithe the council levies slows the doom clock", E.MODIFIER, "council.tithe_doom"),
            Coupling(S.MIND, "a regulation of made minds binds them closer to their makers", E.MODIFIER, "council.regulation_step"),
        ),
    ),
)
