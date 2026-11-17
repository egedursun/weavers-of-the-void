from aerona.db.tables.changes import StateChangeRow, StateChangeTermRow, StateCheckpointRow
from aerona.db.tables.culture import LegendProfileRow, RumourRow
from aerona.db.tables.records import IncidentFactRow, IncidentStepRow, IncidentStepStateRow, IncidentTermRow
from aerona.db.tables.tellings import IncidentNameRow, RumourDistortionRow
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
    Mechanic(
        key="witnesses_and_tellings",
        spec_item="F58.9",
        title="Those present at a happening witness it; retellings change its parts, truer tellings set them right and contrary ones cost trust",
        subsystem=S.COMMUNICATION,
        phases=("rumour_cycles",),
        surface=Surface(drawer=RUMOURS),
        backfill="none: witnesses and distortions are recorded from the upgrade on",
        templates=("rumour.corrected", "information.contradicted", "event.retold", "event.recounted"),
        fields=("witness_mode", "fidelity", "distortion"),
        tables=(RumourDistortionRow.__tablename__,),
        exposure=Exposure.TOOL,
        tools=("recall_event", "retell_event", "recount"),
        levers=(
            "rumour_distortion:create",
            "rumour_distortion:edit",
            "rumour_distortion:delete",
            "incident_witness:create",
            "incident_witness:edit",
            "incident_witness:delete",
        ),
        targets=("settlement", "people", "polity", "cult", "faction", "mortal", "son", "creator"),
        couplings=(
            Coupling(
                S.KNOWLEDGE, "rumours, memories and the chronicler tell a happening from its facts and steps", EdgeKind.FLOW, "records.distortion_per_hop_pct"
            ),
            Coupling(S.SOCIAL, "word of a renowned doer's deed travels further", EdgeKind.MODIFIER, "rumours.renown_spread_pct"),
            Coupling(
                S.SOCIAL,
                "a happening told otherwise than a community knew it wears its trust in what is told",
                EdgeKind.MODIFIER,
                "rumours.contradiction_trust_loss",
            ),
            Coupling(S.MIND, "those near a happening see or hear it, as true as their place let them", EdgeKind.FLOW, "records.witness_radius"),
        ),
    ),
    Mechanic(
        key="record_of_events",
        spec_item="F58.5",
        title="Every value any hand changes is kept with its before, after, cause and terms; any record can be read as it was at an earlier moment",
        subsystem=S.KNOWLEDGE,
        phases=("record_checkpoints",),
        surface=Surface(drawer="EventPage", layer="AtlasAtMoment", chart="HistorySection"),
        backfill="records_first_checkpoint: the state of the world at the upgrade is the first checkpoint; engine history starts there",
        tables=(
            StateChangeRow.__tablename__,
            StateChangeTermRow.__tablename__,
            StateCheckpointRow.__tablename__,
            IncidentFactRow.__tablename__,
            IncidentStepRow.__tablename__,
            IncidentStepStateRow.__tablename__,
            IncidentTermRow.__tablename__,
        ),
        exposure=Exposure.TOOL,
        tools=("recall_event",),
        levers=(
            "state_change:revert",
            "state_change:delete",
            "incident_fact:create",
            "incident_fact:edit",
            "incident_fact:delete",
            "incident_step:create",
            "incident_step:edit",
            "incident_step:delete",
        ),
        targets=("settlement", "people", "polity", "mortal", "son", "creator", "foreign_god", "world", "star"),
        couplings=(
            Coupling(
                S.KNOWLEDGE,
                "kept changes rebuild any record as it was at an earlier moment, and a god's revert is itself kept",
                EdgeKind.FLOW,
                "records.checkpoint_epochs",
            ),
            Coupling(S.MIND, "the terms kept with every number explain each value on every screen that shows it", EdgeKind.FLOW),
        ),
    ),
    Mechanic(
        key="happening_names",
        spec_item="F58.10",
        title="A happening of great weight is given a name in the tongue of those it befell",
        subsystem=S.LANGUAGE,
        phases=("rumour_cycles",),
        surface=Surface(drawer=RUMOURS),
        backfill="none: happenings are named from the upgrade on",
        tables=(IncidentNameRow.__tablename__,),
        exposure=Exposure.CONTEXT,
        levers=("incident_name:set", "incident_name:delete"),
        targets=("settlement", "people", "polity", "mortal"),
        couplings=(Coupling(S.CULTURE, "a weighty happening carries a name of its own in the world's tongues", EdgeKind.TRIGGER, "records.naming_magnitude"),),
    ),
)
