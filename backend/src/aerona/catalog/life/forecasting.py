from aerona.domain.enums.forecasting import WeatherWorkMethod
from aerona.domain.enums.society import KnowledgeBranch

NEEDS: dict[WeatherWorkMethod, KnowledgeBranch] = {
    WeatherWorkMethod.RITE: KnowledgeBranch.MAGIC,
    WeatherWorkMethod.POWER: KnowledgeBranch.MAGIC,
    WeatherWorkMethod.SEEDING: KnowledgeBranch.AGRICULTURE,
    WeatherWorkMethod.DIVERSION: KnowledgeBranch.ARCHITECTURE,
    WeatherWorkMethod.MADE_STRUCTURE: KnowledgeBranch.ARCHITECTURE,
    WeatherWorkMethod.LIVING_CRAFT: KnowledgeBranch.BIOMANCY,
    WeatherWorkMethod.BARGAIN: KnowledgeBranch.MAGIC,
    WeatherWorkMethod.MADE_MIND: KnowledgeBranch.ASTRONOMY,
}
METHOD_STRENGTH_PCT: dict[WeatherWorkMethod, int] = {
    WeatherWorkMethod.RITE: 100,
    WeatherWorkMethod.POWER: 130,
    WeatherWorkMethod.SEEDING: 80,
    WeatherWorkMethod.DIVERSION: 70,
    WeatherWorkMethod.MADE_STRUCTURE: 110,
    WeatherWorkMethod.LIVING_CRAFT: 90,
    WeatherWorkMethod.BARGAIN: 150,
    WeatherWorkMethod.MADE_MIND: 120,
}
METHOD_COST_PCT: dict[WeatherWorkMethod, int] = {
    WeatherWorkMethod.RITE: 100,
    WeatherWorkMethod.POWER: 80,
    WeatherWorkMethod.SEEDING: 120,
    WeatherWorkMethod.DIVERSION: 150,
    WeatherWorkMethod.MADE_STRUCTURE: 200,
    WeatherWorkMethod.LIVING_CRAFT: 110,
    WeatherWorkMethod.BARGAIN: 60,
    WeatherWorkMethod.MADE_MIND: 160,
}
