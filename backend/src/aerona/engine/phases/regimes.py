from aerona.engine.context import TickContext
from aerona.engine.interconnect.annotations import reads, writes
from aerona.engine.phase import Phase
from aerona.engine.phases.dominion import count
from aerona.engine.regime.learning import LearningTally, keep_learning
from aerona.engine.regime.lineages import LineageTally, keep_lineages
from aerona.engine.regime.patronage import PatronageTally, keep_patronage
from aerona.engine.regime.rule import RegimeTally, keep_regimes


@reads(
    "faction.sway",
    "mortal.age",
    "mortal.charisma",
    "mortal.hp",
    "mortal.lifespan",
    "people.population",
    "people.prosperity",
    "settlement.population",
    "settlement.prosperity",
    "table.bonds",
    "table.coalition_members",
    "table.community_societies",
    "table.creator_taboos",
    "table.culture_ethics",
    "table.designated_heirs",
    "table.entity_flags",
    "table.epoch_year_cursors",
    "table.geasa",
    "table.gifts",
    "table.holder_techniques",
    "table.house_members",
    "table.legend_profiles",
    "table.memories",
    "table.minds",
    "table.miracle_records",
    "table.mortal_profiles",
    "table.natural_law_profiles",
    "table.nodes",
    "table.oaths",
    "table.offices",
    "table.polity_members",
    "table.polity_profiles",
    "table.polity_stress",
    "table.polity_territories",
    "table.power_bases",
    "table.regimes",
    "table.relationships",
    "table.secrets",
    "table.tradition_profiles",
    "table.vassalages",
    "table.wars",
)
@writes(
    "people.prosperity",
    "settlement.prosperity",
    "table.bonds",
    "table.chronicle",
    "table.chronicle_entities",
    "table.coalition_members",
    "table.community_societies",
    "table.entities",
    "table.entity_flags",
    "table.epoch_year_cursors",
    "table.incident_participants",
    "table.incidents",
    "table.memories",
    "table.mortal_profiles",
    "table.oaths",
    "table.office_history",
    "table.offices",
    "table.polity_members",
    "table.polity_profiles",
    "table.polity_treasury",
    "table.regimes",
    "table.secrets",
)
async def regimes(ctx: TickContext) -> None:
    tally = RegimeTally()
    await keep_regimes(ctx, tally)
    count(ctx, "regimes", tally)


@reads(
    "army.size",
    "law.justice",
    "mortal.age",
    "table.armies",
    "table.bonds",
    "table.coalition_members",
    "table.house_profiles",
    "table.law_jurisdictions",
    "table.law_profiles",
    "table.mortal_profiles",
    "table.oaths",
    "table.offices",
    "table.patronage_ties",
    "table.people_culture",
    "table.polity_members",
    "table.polity_profiles",
    "table.polity_territories",
    "table.power_bases",
    "table.regimes",
    "table.traits",
    "table.vassalages",
    "table.venal_offices",
)
@writes(
    "table.chronicle",
    "table.chronicle_entities",
    "table.coalition_members",
    "table.epoch_year_cursors",
    "table.incident_participants",
    "table.incidents",
    "table.mortal_profiles",
    "table.oaths",
    "table.office_history",
    "table.offices",
    "table.patronage_ties",
    "table.polity_profiles",
    "table.polity_treasury",
    "table.power_bases",
    "table.regimes",
    "table.venal_offices",
)
async def patronage(ctx: TickContext) -> None:
    tally = PatronageTally()
    await keep_patronage(ctx, tally)
    count(ctx, "patronage", tally)


@reads("table.feuds", "table.house_profiles", "table.lineage_segments", "table.polity_profiles")
@writes("table.lineage_segments")
async def kin_politics(ctx: TickContext) -> None:
    tally = LineageTally()
    await keep_lineages(ctx, tally)
    count(ctx, "kin_politics", tally)


@reads(
    "table.examinations",
    "table.holder_techniques",
    "table.offices",
    "table.polity_members",
    "table.polity_profiles",
    "table.polity_territories",
    "table.school_lineages",
    "table.school_members",
    "table.vassalages",
)
async def learning_institutions(ctx: TickContext) -> None:
    tally = LearningTally()
    await keep_learning(ctx, tally)
    count(ctx, "learning_institutions", tally)


PHASES = (
    Phase("regimes", regimes),
    Phase("patronage", patronage),
    Phase("kin_politics", kin_politics),
    Phase("learning_institutions", learning_institutions),
)
