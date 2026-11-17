from aerona.db.tables.law_grammar import LawExceptionRow, LawTheoryRow
from aerona.db.tables.outer_agency import OuterHeraldRow, OuterIncursionRow, OuterPactRow, OuterPlanRow, OuterRelationRow, OuterSealRow
from aerona.engine.interconnect.registry import Coupling, EdgeKind, Exposure, Mechanic, Subsystem, Surface

S = Subsystem
E = EdgeKind

LAW_OUTER_MECHANICS: tuple[Mechanic, ...] = (
    Mechanic(
        key="natural_law_grammar",
        spec_item="S47.5",
        title=(
            "Natural laws are written as a target, an operator, a value, a condition, exceptions and a span; "
            "they press on stats and on made things, contest by strength, and peoples hold theories of them"
        ),
        subsystem=S.COSMOS,
        phases=("natural_laws",),
        surface=Surface(drawer="section-law-grammar"),
        backfill="natural_laws: every law gains the grammar of its old kind on the first epoch",
        templates=("law.natural_set", "law.natural_suspended", "law.natural_ended", "law.natural_reshaped"),
        fields=("target", "operator", "key", "value", "condition", "until_epoch", "suspended"),
        tables=(LawExceptionRow.__tablename__, LawTheoryRow.__tablename__),
        exposure=Exposure.TOOL,
        tools=("set_natural_law",),
        targets=("natural_law", "people"),
        couplings=(
            Coupling(S.GODS, "the authors of contesting laws fall out", E.MODIFIER, "natural_laws.feud_relation"),
            Coupling(S.KNOWLEDGE, "a people's wrong theory of a law costs it craft", E.MODIFIER, "natural_laws.reliability_pct"),
            Coupling(S.MAGIC, "a law over powers, sources or made minds moves their values", E.MODIFIER),
        ),
    ),
    Mechanic(
        key="outer_agency",
        spec_item="S47.5",
        title=(
            "Outer beings pursue aims in stages with signs, bind heralds, press incursions through rifts, strike bargains that give bonded powers, "
            "feed on or thwart one another, and can be sealed, banished, starved or destroyed"
        ),
        subsystem=S.COSMOS,
        phases=("outer_hunger",),
        surface=Surface(drawer="section-outer-agency"),
        backfill="outer_hunger: every outer being takes up an aim from the first epoch",
        templates=("outer.sign", "outer.plan_achieved", "outer.incursion", "outer.incursion_ended", "outer.seal_broken", "outer.ended"),
        tables=(
            OuterPlanRow.__tablename__,
            OuterHeraldRow.__tablename__,
            OuterIncursionRow.__tablename__,
            OuterPactRow.__tablename__,
            OuterRelationRow.__tablename__,
            OuterSealRow.__tablename__,
        ),
        exposure=Exposure.NONE,
        tools=(),
        targets=("outer_being", "mortal", "region"),
        couplings=(
            Coupling(S.MIND, "an incursion drains the sanity of its land by its stage", E.MODIFIER, "outer_beings.incursion_sanity"),
            Coupling(S.MAGIC, "a bargain gives a bonded power", E.TRIGGER, "outer_beings.bargain_strength"),
            Coupling(S.GODS, "sons ward off a manifestation with essence", E.FLOW, "outer_beings.ward_essence"),
        ),
    ),
)
