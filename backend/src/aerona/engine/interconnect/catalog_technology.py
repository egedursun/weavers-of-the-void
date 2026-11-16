from aerona.db.tables.technology import TechnologyProfileRow
from aerona.engine.interconnect.registry import Coupling, EdgeKind, Exposure, Mechanic, Subsystem, Surface

S = Subsystem
E = EdgeKind

TECHNOLOGY_MECHANICS: tuple[Mechanic, ...] = (
    Mechanic(
        key="technology_families",
        spec_item="S47.2",
        title="Each people and world holds a level in every family of technology, and made works, networks and intrusions read their own family",
        subsystem=S.KNOWLEDGE,
        phases=("tech_eras",),
        surface=Surface(drawer="section-technology"),
        backfill="tech_eras: every world takes its families from its starting era and every people derives them from what it knows on the first epoch",
        templates=(),
        tables=(TechnologyProfileRow.__tablename__,),
        exposure=Exposure.NONE,
        tools=(),
        levers=("technology:set", "technology:release", "technology:delete"),
        targets=("people", "world", "polity", "settlement", "mortal"),
        couplings=(
            Coupling(S.KNOWLEDGE, "knowledge levels and techniques raise each family", E.FLOW, "tech_eras"),
            Coupling(S.COMMUNICATION, "networks and relics need the communication family to be kept", E.MODIFIER, "made_relics.wear"),
        ),
    ),
)
