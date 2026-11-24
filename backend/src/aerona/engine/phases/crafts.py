from aerona.engine.context import TickContext
from aerona.engine.crafts.aids import AidTally, keep_aids
from aerona.engine.crafts.chemistry import ChemistryTally, keep_chemistry
from aerona.engine.crafts.clocks import ClockTally, keep_clocks
from aerona.engine.crafts.games import GameTally, keep_games
from aerona.engine.crafts.grounds import GroundTally, keep_grounds
from aerona.engine.crafts.insurance import InsuranceTally, keep_insurance
from aerona.engine.crafts.numbers import NumberTally, keep_numbers
from aerona.engine.crafts.rights import RightsTally, keep_rights
from aerona.engine.crafts.spirits import SpiritTally, keep_spirits
from aerona.engine.crafts.sympathy import SympathyTally, keep_sympathy
from aerona.engine.interconnect.annotations import reads, writes
from aerona.engine.phase import Phase
from aerona.engine.phases.dominion import count


@reads(
    "cult.zeal",
    "item.protection",
    "mortal.age",
    "mortal.agility",
    "mortal.charisma",
    "mortal.creativity",
    "mortal.endurance",
    "mortal.hp",
    "mortal.intellect",
    "mortal.lifespan",
    "mortal.perception",
    "mortal.strength",
    "mortal.willpower",
    "mortal.wisdom",
    "settlement.wealth",
    "spirit.unrest",
    "table.artwork_profiles",
    "table.augment_effects",
    "table.augments",
    "table.bonds",
    "table.catch_grounds",
    "table.charms",
    "table.chemical_works",
    "table.community_relations",
    "table.community_stocks",
    "table.conditions",
    "table.cooperatives",
    "table.creator",
    "table.crime_cases",
    "table.cult_offices",
    "table.cult_tenets",
    "table.culture_values",
    "table.custom_kinds",
    "table.deep_passages",
    "table.dimensions",
    "table.dishes",
    "table.divine_wounds",
    "table.doctrine_sacraments",
    "table.entities",
    "table.entity_flags",
    "table.entity_tags",
    "table.foreign_gods",
    "table.galaxies",
    "table.galaxy_clusters",
    "table.game_reserves",
    "table.goods_flows",
    "table.grave_goods",
    "table.held_identities",
    "table.holder_custom_techniques",
    "table.holder_levels",
    "table.holder_techniques",
    "table.house_members",
    "table.incidents",
    "table.incorporeal_rights",
    "table.incubating_ideas",
    "table.injuries",
    "table.insurance_policies",
    "table.insurers",
    "table.item_profiles",
    "table.lexemes",
    "table.marriages",
    "table.memories",
    "table.mind_attributes",
    "table.name_registry",
    "table.node_births",
    "table.nodes",
    "table.offices",
    "table.outbreaks",
    "table.passions",
    "table.personality_values",
    "table.prostheses",
    "table.public_clocks",
    "table.region_environment",
    "table.region_pollution",
    "table.relationships",
    "table.reputations",
    "table.resource_profiles",
    "table.resource_workers",
    "table.rite_profiles",
    "table.routes",
    "table.ruler_currencies",
    "table.sacraments",
    "table.sons",
    "table.species_ranges",
    "table.stars",
    "table.structure_profiles",
    "table.traits",
    "table.transform_prospects",
    "table.world_domain_hooks",
    "table.worlds",
)
@writes(
    "mortal.death_year",
    "mortal.hp",
    "settlement.wealth",
    "table.bodies",
    "table.body_customs",
    "table.bonds",
    "table.catch_grounds",
    "table.chemical_works",
    "table.chronicle",
    "table.chronicle_entities",
    "table.community_relations",
    "table.community_stocks",
    "table.conditions",
    "table.entities",
    "table.goods_flows",
    "table.incident_facts",
    "table.incident_participants",
    "table.incident_steps",
    "table.incidents",
    "table.incorporeal_rights",
    "table.injuries",
    "table.insurance_policies",
    "table.insurers",
    "table.marriages",
    "table.memories",
    "table.mortal_profiles",
    "table.name_registry",
    "table.node_births",
    "table.public_clocks",
    "table.region_environment",
    "table.region_pollution",
    "table.sacraments",
    "table.settlement_profiles",
    "table.sons",
    "table.spirit_profiles",
    "table.transformations",
)
async def trades(ctx: TickContext) -> None:
    grounds, chemistry, insurance, rights, clocks = GroundTally(), ChemistryTally(), InsuranceTally(), RightsTally(), ClockTally()
    await keep_grounds(ctx, grounds)
    await keep_chemistry(ctx, chemistry)
    await keep_insurance(ctx, insurance)
    await keep_rights(ctx, rights)
    await keep_clocks(ctx, clocks)
    count(ctx, "grounds", grounds)
    count(ctx, "chemistry", chemistry)
    count(ctx, "insurance", insurance)
    count(ctx, "incorporeal", rights)
    count(ctx, "clocks", clocks)


@reads(
    "settlement.prosperity",
    "table.assistive_aids",
    "table.bonds",
    "table.conditions",
    "table.creator",
    "table.dimensions",
    "table.entities",
    "table.foreign_gods",
    "table.galaxies",
    "table.galaxy_clusters",
    "table.games",
    "table.holder_techniques",
    "table.incident_participants",
    "table.incidents",
    "table.kind_holdings",
    "table.language_profiles",
    "table.lexemes",
    "table.minds",
    "table.name_registry",
    "table.node_births",
    "table.nodes",
    "table.number_systems",
    "table.offices",
    "table.settlement_profiles",
    "table.skills",
    "table.sons",
    "table.stars",
    "table.worlds",
)
@writes(
    "settlement.prosperity",
    "table.applied_fixups",
    "table.assistive_aids",
    "table.chronicle",
    "table.chronicle_entities",
    "table.entities",
    "table.games",
    "table.incident_facts",
    "table.incident_participants",
    "table.incident_steps",
    "table.incidents",
    "table.kind_holdings",
    "table.number_systems",
    "table.settlement_profiles",
    "table.skills",
)
async def learning_aids(ctx: TickContext) -> None:
    aids, games, numbers = AidTally(), GameTally(), NumberTally()
    await keep_aids(ctx, aids)
    await keep_games(ctx, games)
    await keep_numbers(ctx, numbers)
    count(ctx, "aids", aids)
    count(ctx, "games", games)
    count(ctx, "numeracy", numbers)


@reads(
    "region.magic",
    "table.accusations",
    "table.deep_passages",
    "table.emotion_spirits",
    "table.material_affinities",
    "table.node_births",
    "table.rite_effects",
    "table.sympathetic_links",
    "table.thoughts",
    "table.world_materials",
)
@writes(
    "table.chronicle",
    "table.chronicle_entities",
    "table.emotion_spirits",
    "table.entity_flags",
    "table.incident_facts",
    "table.incident_participants",
    "table.incidents",
)
async def sympathies(ctx: TickContext) -> None:
    sympathy, spirits = SympathyTally(), SpiritTally()
    await keep_sympathy(ctx, sympathy)
    await keep_spirits(ctx, spirits)
    count(ctx, "sympathy", sympathy)
    count(ctx, "emotion_spirits", spirits)


PHASES = (
    Phase("trades", trades),
    Phase("learning_aids", learning_aids),
    Phase("sympathies", sympathies),
)
