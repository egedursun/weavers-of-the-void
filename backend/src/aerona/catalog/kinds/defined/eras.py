from aerona.catalog.kinds.definition import Defined
from aerona.core.total import total
from aerona.domain.enums.eras import EraChannel

ERA_CHANNEL = total(
    EraChannel,
    {
        EraChannel.FARMING: Defined("Harvests", checked_by=(), used_by=("catalog.eras.ERA_EFFECTS", "engine.economy.extraction.craft_factor")),
        EraChannel.MINING: Defined("Mining", checked_by=(), used_by=("catalog.eras.ERA_EFFECTS", "engine.economy.extraction.craft_factor")),
        EraChannel.INDUSTRY: Defined("Industry", checked_by=(), used_by=("catalog.eras.ERA_EFFECTS", "engine.economy.refining.run_step")),
        EraChannel.DISEASE: Defined("Deaths from sickness spared", checked_by=(), used_by=("catalog.eras.ERA_EFFECTS", "engine.disease.book.DiseaseBook.load")),
        EraChannel.MESSAGES: Defined("Message reach", checked_by=(), used_by=("catalog.eras.ERA_EFFECTS", "engine.communication.post.delay")),
        EraChannel.MARCH: Defined("Army march", checked_by=(), used_by=("catalog.eras.ERA_EFFECTS", "engine.military.logistics.advance")),
        EraChannel.SEA_ROUTES: Defined("Sea routes", checked_by=(), used_by=("catalog.eras.ERA_EFFECTS", "engine.economy.routes.spoken_capacity")),
        EraChannel.WORLD_ROUTES: Defined("Routes between worlds", checked_by=(), used_by=("catalog.eras.ERA_EFFECTS", "engine.cosmos.commerce.carry")),
        EraChannel.FORTIFICATION: Defined("Walls", checked_by=(), used_by=("catalog.eras.ERA_EFFECTS", "engine.phases.warfare._powers")),
        EraChannel.POLLUTION: Defined("Pollution", checked_by=(), used_by=("catalog.eras.ERA_EFFECTS", "engine.industry.pollution.foul_from_runs")),
        EraChannel.OPINION: Defined("Speed of opinion", checked_by=(), used_by=("catalog.eras.ERA_EFFECTS", "engine.communication.opinion.tend_community")),
        EraChannel.RESEARCH: Defined("Research", checked_by=(), used_by=("catalog.eras.ERA_EFFECTS", "engine.lore.research.thought_factor")),
        EraChannel.SECULARISATION: Defined("Secularisation", checked_by=(), used_by=("catalog.eras.ERA_EFFECTS", "engine.sacred.rites.weigh_town")),
        EraChannel.FIREPOWER: Defined("Missile strength", checked_by=(), used_by=("catalog.eras.ERA_EFFECTS", "engine.military.clash.side_of")),
        EraChannel.RITES: Defined("Power rites lose", checked_by=(), used_by=("catalog.eras.ERA_EFFECTS", "engine.lore.rites.cast")),
        EraChannel.SPOILAGE: Defined("Spoilage spared", checked_by=(), used_by=("catalog.eras.ERA_EFFECTS", "engine.economy.routes.haul")),
        EraChannel.DOOM: Defined("Doom each epoch", checked_by=(), used_by=("catalog.eras.ERA_EFFECTS", "engine.eras.progress.era_doom")),
        EraChannel.LEARNING: Defined("Literacy reach", checked_by=(), used_by=("catalog.eras.ERA_EFFECTS", "engine.structures.functions.school")),
        EraChannel.HEALTH: Defined("Life span", checked_by=(), used_by=("catalog.eras.ERA_EFFECTS", "engine.lifecycle.aging.effective_lifespan")),
    },
)
