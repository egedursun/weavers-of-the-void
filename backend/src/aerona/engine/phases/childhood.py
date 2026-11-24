from aerona.engine.childhood.life import keep_childhood
from aerona.engine.childhood.seed import seed_childhood
from aerona.engine.context import TickContext
from aerona.engine.interconnect.annotations import reads, writes
from aerona.engine.phase import Phase


@reads(
    "cult.zeal",
    "mortal.age",
    "mortal.charisma",
    "mortal.lifespan",
    "mortal.strength",
    "settlement.population",
    "settlement.prosperity",
    "spirit.unrest",
    "table.age_sets",
    "table.biology_variants",
    "table.bonds",
    "table.child_standing",
    "table.creator",
    "table.crime_cases",
    "table.cult_offices",
    "table.culture_values",
    "table.deep_passages",
    "table.dimensions",
    "table.divine_wounds",
    "table.doctrine_sacraments",
    "table.entities",
    "table.entity_flags",
    "table.foreign_gods",
    "table.galaxies",
    "table.galaxy_clusters",
    "table.grave_goods",
    "table.griefs",
    "table.holder_levels",
    "table.incidents",
    "table.infant_care",
    "table.injuries",
    "table.insurance_policies",
    "table.insurers",
    "table.item_profiles",
    "table.kinship_systems",
    "table.law_jurisdictions",
    "table.law_profiles",
    "table.marriages",
    "table.memories",
    "table.mind_facets",
    "table.mortal_profiles",
    "table.name_registry",
    "table.node_births",
    "table.nodes",
    "table.outbreaks",
    "table.passions",
    "table.pedagogy",
    "table.personality_values",
    "table.polity_members",
    "table.routes",
    "table.sacraments",
    "table.socialization",
    "table.sons",
    "table.spirit_profiles",
    "table.stars",
    "table.structure_profiles",
    "table.thoughts",
    "table.tradition_profiles",
    "table.traits",
    "table.transform_prospects",
    "table.war_sides",
    "table.wars",
    "table.world_domain_hooks",
    "table.worlds",
)
@writes(
    "mortal.death_year",
    "settlement.prosperity",
    "table.bonds",
    "table.child_standing",
    "table.chronicle",
    "table.chronicle_entities",
    "table.community_societies",
    "table.community_stocks",
    "table.entities",
    "table.goods_flows",
    "table.grave_goods",
    "table.griefs",
    "table.incident_facts",
    "table.incident_participants",
    "table.incident_steps",
    "table.incidents",
    "table.infant_care",
    "table.memories",
    "table.mind_facets",
    "table.mortal_profiles",
    "table.name_registry",
    "table.node_births",
    "table.pedagogy",
    "table.personality_values",
    "table.sacraments",
    "table.socialization",
    "table.sons",
    "table.spirit_profiles",
    "table.thoughts",
    "table.transformations",
)
async def childhood(ctx: TickContext) -> None:
    seeded = await seed_childhood(ctx)
    ctx.count("childhood_seeded_care", seeded.infant_care)
    ctx.count("childhood_seeded_standing", seeded.standing)
    ctx.count("childhood_seeded_socialization", seeded.socialization)
    ctx.count("childhood_seeded_pedagogy", seeded.pedagogy)
    tally = await keep_childhood(ctx)
    ctx.count("childhood_infants_lost", tally.infants_lost)
    ctx.count("childhood_weaned", tally.weaned)
    ctx.count("childhood_named", tally.named)
    ctx.count("childhood_workers", tally.workers)
    ctx.count("childhood_shaped", tally.shaped)
    ctx.count("childhood_schooled", tally.schooled)


PHASES = (Phase("childhood", childhood),)
