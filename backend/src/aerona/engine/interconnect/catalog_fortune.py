from aerona.db.tables.fortune import CohortMishapRateRow, FortuneLawRow, FortuneProfileRow, FortuneSourceRow
from aerona.engine.interconnect.registry import Coupling, EdgeKind, Exposure, Mechanic, Subsystem, Surface

S = Subsystem
E = EdgeKind
FORTUNE = "section-fortune"
EVERY_NODE = ("mortal", "beast", "spirit", "son", "foreign_god", "creator", "world", "star", "people", "polity", "cult", "house", "region", "settlement")

FORTUNE_MECHANICS: tuple[Mechanic, ...] = (
    Mechanic(
        key="fortune",
        spec_item="S47.10",
        title="Fortune is reckoned from blessings, curses, charms, oaths, powers over fate and a streak of its own, and moves the mishaps and draws of a life",
        subsystem=S.FAITH,
        phases=("fortune",),
        surface=Surface(drawer=FORTUNE),
        backfill="fortune.legacy_backfill: every blessing and curse of a god becomes a source of fortune",
        templates=("folkways.mishap",),
        tables=(FortuneProfileRow.__tablename__, FortuneSourceRow.__tablename__, FortuneLawRow.__tablename__, CohortMishapRateRow.__tablename__),
        exposure=Exposure.TOOL,
        tools=("take_care", "bless_fortune", "curse_fortune", "make_charm", "consult_diviner"),
        levers=("fortune:edit", "fortune_source:create", "fortune_source:edit", "fortune_source:delete", "fortune_law:set", "mishap:trigger"),
        targets=EVERY_NODE,
        couplings=(
            Coupling(S.WAR, "a commander's fortune moves the luck of a battle", E.MODIFIER, "fortune.draw_cap_pct"),
            Coupling(S.BODY, "everyday mishaps wound by their kind and drawn severity", E.TRIGGER, "everyday_mishaps.small_per_epoch"),
            Coupling(S.DEMOGRAPHY, "towns lose folk to accidents by crowding and season", E.FLOW, "everyday_mishaps.cohort_rate_per_mil"),
            Coupling(S.FAITH, "a god's blessing turns fortune", E.FLOW, "fortune.blessing_strength"),
        ),
    ),
)
