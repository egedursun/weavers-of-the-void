from aerona.db.tables.culture import LegendProfileRow, RumourRow
from aerona.engine.interconnect.registry import Coupling, EdgeKind, Exposure, Mechanic, Subsystem, Surface

S = Subsystem
RUMOURS = "section-rumours"

RUMOUR_MECHANICS = (
    Mechanic(
        key="rumours",
        spec_item="F11",
        title="Word of what happened travels along trade roads, pilgrimages, journeys and spy networks, garbled by distance, tongues and the unlettered",
        subsystem=S.COMMUNICATION,
        phases=("rumour_cycles",),
        surface=Surface(drawer=RUMOURS),
        backfill="lore.rumours_backfill: the happenings of the last epochs are remembered as rumour where they were witnessed",
        templates=("rumour.alarm", "rumour.legend"),
        fields=("fidelity", "channel", "hops", "lingered", "planted"),
        tables=(RumourRow.__tablename__, LegendProfileRow.__tablename__),
        exposure=Exposure.CONTEXT,
        targets=("settlement", "people", "polity", "cult", "faction", "mortal", "legend"),
        couplings=(
            Coupling(
                S.MIND, "a community hates the doer of an atrocity it heard of, as much as it believes the tale", EdgeKind.MODIFIER, "rumours.atrocity_hatred"
            ),
            Coupling(S.WAR, "word of an enemy host nearby sends a town to its walls", EdgeKind.TRIGGER, "rumours.alarm_defense"),
            Coupling(S.SOCIAL, "a frightened community calls on its allies against the coming army", EdgeKind.MODIFIER, "rumours.ally_call"),
            Coupling(S.CULTURE, "garbled word that lingers hardens into legend", EdgeKind.TRIGGER, "rumours.legend_fidelity"),
            Coupling(S.LANGUAGE, "word crossing a tongue nobody shares is garbled", EdgeKind.MODIFIER, "rumours.barrier_loss"),
        ),
    ),
)
