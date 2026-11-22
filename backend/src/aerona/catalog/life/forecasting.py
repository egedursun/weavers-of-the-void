from aerona.domain.enums.forecasting import WeatherWorkMethod
from aerona.domain.enums.society import KnowledgeBranch

NEEDS: dict[WeatherWorkMethod, KnowledgeBranch] = {
    WeatherWorkMethod.RITE: KnowledgeBranch.MAGIC,
    WeatherWorkMethod.POWER: KnowledgeBranch.MAGIC,
    WeatherWorkMethod.SEEDING: KnowledgeBranch.AGRICULTURE,
    WeatherWorkMethod.DIVERSION: KnowledgeBranch.ARCHITECTURE,
    WeatherWorkMethod.MADE_STRUCTURE: KnowledgeBranch.ARCHITECTURE,
    WeatherWorkMethod.LIVING_CRAFT: KnowledgeBranch.BIOMANCY,
}
