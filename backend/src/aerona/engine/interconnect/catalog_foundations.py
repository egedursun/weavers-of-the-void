from aerona.db.tables.society import CommunitySocietyRow
from aerona.db.tables.warfare import WarRow
from aerona.engine.interconnect.registry import Coupling, EdgeKind, Exposure, Mechanic, Subsystem, Surface

FOUNDATION_MECHANICS = (
    Mechanic(
        key="war_incitement",
        spec_item="W0",
        title="A god who incites a war reaps its fame and its losers' hatred",
        subsystem=Subsystem.GODS,
        phases=("war_upkeep", "campaigns", "diplomacy"),
        surface=Surface(drawer="WarIncitement"),
        backfill="none: wars incited before the wave keep their instigator, and the toll falls when they end",
        templates=("war.incitement_reaped",),
        fields=("incited_by_son_id",),
        tables=(WarRow.__tablename__,),
        exposure=Exposure.CONTEXT,
        targets=("war", "son"),
        couplings=(
            Coupling(
                Subsystem.GODS,
                "the instigator gains fame for every battle, existence when their worshippers win",
                EdgeKind.TRIGGER,
                "incitement.fame_per_battle",
            ),
            Coupling(Subsystem.MIND, "the losers keep a grievance against the god who set the war upon them", EdgeKind.TRIGGER, "incitement.loser_grievance"),
            Coupling(Subsystem.WAR, "a held incitement is inherited by the next war between the same sides"),
        ),
    ),
    Mechanic(
        key="golden_age_course",
        spec_item="W0",
        title="A golden age deepens with its length, then makes its peoples soft",
        subsystem=Subsystem.CULTURE,
        phases=("doom_clock",),
        surface=Surface(drawer="GoldenAge"),
        backfill="doom_clock: communities already in a golden age keep the epoch it began",
        templates=("world_age.golden_age", "world_age.golden_age_ended"),
        fields=("golden_age_since_epoch",),
        tables=(CommunitySocietyRow.__tablename__,),
        exposure=Exposure.CONTEXT,
        targets=("world", "people", "settlement"),
        couplings=(
            Coupling(Subsystem.ECONOMY, "prosperity grows faster the longer the age lasts", EdgeKind.MODIFIER, "deep_life.golden_age_deepening_gain"),
            Coupling(Subsystem.WAR, "a long age of ease wears down martiality and walls", EdgeKind.MODIFIER, "deep_life.golden_age_decadence_loss"),
            Coupling(Subsystem.GODS, "each world in a golden age pushes the doomsday clock back"),
        ),
    ),
    Mechanic(
        key="dedicated_anchor",
        spec_item="W0",
        title="Works dedicated to a god feed them and can anchor their existence",
        subsystem=Subsystem.GODS,
        phases=("sons_renewal", "works_remember_gods"),
        surface=Surface(drawer="SonAnchorage", chart="StructureDedication"),
        backfill="none: structures already dedicated count from the next epoch",
        fields=("anchor_entity_id",),
        exposure=Exposure.TOOL,
        tools=("choose_anchor",),
        targets=("son", "structure"),
        couplings=(
            Coupling(Subsystem.CULTURE, "a dedicated structure that falls leaves its anchored god fading"),
            Coupling(Subsystem.FAITH, "dedicated works add fame and existence every age", EdgeKind.MODIFIER, "world_epoch_transition.dedicated_work_existence"),
        ),
    ),
)
