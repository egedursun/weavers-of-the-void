from aerona.engine.context import TickContext
from aerona.engine.interconnect.annotations import reads, writes
from aerona.engine.phase import Phase
from aerona.engine.space_weather.weather import SpaceWeatherTally, keep_space_weather


@reads(
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
    "people.piety",
    "settlement.piety",
    "settlement.prosperity",
    "table.augment_effects",
    "table.augments",
    "table.bodies",
    "table.bonds",
    "table.conditions",
    "table.creator",
    "table.dimensions",
    "table.entities",
    "table.entity_flags",
    "table.entity_tags",
    "table.foreign_gods",
    "table.galaxies",
    "table.galaxy_clusters",
    "table.holder_levels",
    "table.incubating_ideas",
    "table.injuries",
    "table.item_profiles",
    "table.mind_attributes",
    "table.network_profiles",
    "table.node_births",
    "table.nodes",
    "table.prostheses",
    "table.sons",
    "table.space_weather_events",
    "table.star_activity",
    "table.stars",
    "table.traits",
    "table.world_fields",
    "table.worlds",
)
@writes(
    "mortal.hp",
    "people.piety",
    "settlement.piety",
    "settlement.prosperity",
    "table.bodies",
    "table.chronicle",
    "table.chronicle_entities",
    "table.entities",
    "table.incident_facts",
    "table.incident_participants",
    "table.incidents",
    "table.injuries",
    "table.mortal_profiles",
    "table.network_outages",
    "table.network_profiles",
    "table.space_weather_events",
    "table.star_activity",
    "table.world_fields",
)
async def space_weather(ctx: TickContext) -> None:
    tally = SpaceWeatherTally()
    await keep_space_weather(ctx, tally)
    ctx.count("space_weather_events", tally.events)
    ctx.count("space_weather_outages", tally.outages)
    ctx.count("space_weather_harmed", tally.harmed)
    ctx.count("space_weather_reversals", tally.reversals)
    ctx.count("space_weather_omens", tally.omens)


PHASES = (Phase("space_weather", space_weather),)
