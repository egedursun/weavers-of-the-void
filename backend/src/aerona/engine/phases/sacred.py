from aerona.engine.context import TickContext
from aerona.engine.interconnect.annotations import reads, writes
from aerona.engine.phase import Phase
from aerona.engine.phases.dominion import count
from aerona.engine.sacred.bureau import BureauTally, keep_bureau
from aerona.engine.sacred.foresight import ForesightTally, keep_foresight
from aerona.engine.sacred.mysteries import MysteryTally, keep_mysteries
from aerona.engine.sacred.rites import RiteTally, keep_rites
from aerona.engine.sacred.spirits import SpiritTally, keep_place_spirits


@reads(
    "settlement.piety",
    "settlement.population",
    "settlement.prosperity",
    "table.bonds",
    "table.community_societies",
    "table.community_society",
    "table.divine_standing",
    "table.divine_wounds",
    "table.entities",
    "table.epoch_year_cursors",
    "table.foreign_gods",
    "table.genius_loci",
    "table.mind_facets",
    "table.minds",
    "table.mortal_profiles",
    "table.name_registry",
    "table.nodes",
    "table.personality_values",
    "table.petitions",
    "table.place_profiles",
    "table.region_environment",
    "table.region_pollution",
    "table.sons",
    "table.spirit_offices",
    "table.world_domain_hooks",
)
@writes(
    "settlement.population",
    "settlement.prosperity",
    "table.bonds",
    "table.chronicle",
    "table.chronicle_entities",
    "table.community_societies",
    "table.community_society",
    "table.community_stocks",
    "table.divine_standing",
    "table.entities",
    "table.epoch_year_cursors",
    "table.genius_loci",
    "table.goods_flows",
    "table.incident_participants",
    "table.incidents",
    "table.memories",
    "table.mind_facets",
    "table.mortal_profiles",
    "table.name_registry",
    "table.personality_values",
    "table.petitions",
    "table.spirit_offices",
    "table.thoughts",
)
async def folk_spirits(ctx: TickContext) -> None:
    spirits, bureau = SpiritTally(), BureauTally()
    await keep_place_spirits(ctx, spirits)
    await keep_bureau(ctx, bureau)
    count(ctx, "place_spirits", spirits)
    count(ctx, "spirit_offices", bureau)


@reads(
    "cult.zeal",
    "mortal.charisma",
    "mortal.intellect",
    "mortal.wisdom",
    "settlement.population",
    "settlement.wealth",
    "table.battles",
    "table.bonds",
    "table.community_societies",
    "table.community_society",
    "table.cosmos",
    "table.cult_doctrines",
    "table.cult_offices",
    "table.cult_tenets",
    "table.divine_standing",
    "table.divine_wounds",
    "table.entities",
    "table.epoch_year_cursors",
    "table.faith_climates",
    "table.holder_techniques",
    "table.millenarian_movements",
    "table.miracle_records",
    "table.mortal_profiles",
    "table.mystics",
    "table.outbreaks",
    "table.personality_values",
    "table.polity_members",
    "table.polity_profiles",
    "table.polity_stress",
    "table.prophecy_conditions",
    "table.sky_events",
    "table.storytellers",
    "table.theodicy_crises",
    "table.world_domain_hooks",
)
@writes(
    "settlement.piety",
    "settlement.population",
    "settlement.wealth",
    "table.bonds",
    "table.chronicle",
    "table.chronicle_entities",
    "table.community_societies",
    "table.community_society",
    "table.community_stocks",
    "table.cult_tenets",
    "table.divine_standing",
    "table.entities",
    "table.epoch_year_cursors",
    "table.faction_profiles",
    "table.goods_flows",
    "table.heresies",
    "table.holy_order_profiles",
    "table.incident_participants",
    "table.incidents",
    "table.millenarian_movements",
    "table.mortal_profiles",
    "table.movements",
    "table.mystics",
    "table.theodicy_crises",
    "table.thoughts",
    "table.visions",
)
async def mysteries(ctx: TickContext) -> None:
    tally = MysteryTally()
    await keep_mysteries(ctx, tally)
    count(ctx, "mysteries", tally)


@reads(
    "cult.zeal",
    "mortal.age",
    "settlement.piety",
    "settlement.population",
    "settlement.prosperity",
    "spirit.unrest",
    "table.afterlife_strata",
    "table.bonds",
    "table.cult_doctrines",
    "table.cult_offices",
    "table.cult_tenets",
    "table.divine_wounds",
    "table.doctrine_afterlives",
    "table.doctrine_sacraments",
    "table.dominions",
    "table.dreams",
    "table.entities",
    "table.entity_flags",
    "table.faith_climates",
    "table.holder_techniques",
    "table.mind_facets",
    "table.minds",
    "table.miracle_records",
    "table.outbreaks",
    "table.people_culture",
    "table.polity_members",
    "table.polity_profiles",
    "table.reincarnations",
    "table.sacraments",
    "table.soul_judgements",
    "table.spirit_profiles",
    "table.theory_profiles",
    "table.thoughts",
    "table.wars",
    "table.world_domain_hooks",
)
@writes(
    "settlement.piety",
    "spirit.unrest",
    "table.chronicle",
    "table.chronicle_entities",
    "table.cult_doctrines",
    "table.doctrine_afterlives",
    "table.doctrine_sacraments",
    "table.entities",
    "table.entity_flags",
    "table.faith_climates",
    "table.sacraments",
    "table.thoughts",
)
async def rites_of_passage(ctx: TickContext) -> None:
    tally = RiteTally()
    await keep_rites(ctx, tally)
    count(ctx, "rites", tally)


@reads(
    "mortal.age",
    "mortal.lifespan",
    "mortal.wisdom",
    "table.archive_holdings",
    "table.bonds",
    "table.climate_oscillations",
    "table.community_society",
    "table.divination_systems",
    "table.divinations",
    "table.divine_wounds",
    "table.entities",
    "table.epoch_year_cursors",
    "table.faction_profiles",
    "table.forecast_models",
    "table.foresights",
    "table.holder_techniques",
    "table.miracle_records",
    "table.mortal_profiles",
    "table.name_registry",
    "table.natural_law_profiles",
    "table.offices",
    "table.personality_values",
    "table.polity_members",
    "table.polity_stress",
    "table.prophecy_conditions",
    "table.son_powers",
    "table.sons",
    "table.wars",
    "table.world_domain_hooks",
)
@writes(
    "table.chronicle",
    "table.chronicle_entities",
    "table.community_society",
    "table.divination_systems",
    "table.divinations",
    "table.entities",
    "table.epoch_year_cursors",
    "table.forecast_models",
    "table.foresights",
    "table.goods_flows",
    "table.incident_participants",
    "table.incidents",
    "table.long_plans",
    "table.mortal_profiles",
    "table.name_registry",
    "table.prophecy_conditions",
)
async def foresight(ctx: TickContext) -> None:
    tally = ForesightTally()
    await keep_foresight(ctx, tally)
    count(ctx, "foresight", tally)


PHASES = (Phase("folk_spirits", folk_spirits), Phase("mysteries", mysteries), Phase("rites_of_passage", rites_of_passage), Phase("foresight", foresight))
