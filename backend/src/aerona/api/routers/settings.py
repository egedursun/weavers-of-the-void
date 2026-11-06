from fastapi import APIRouter

from aerona.api.actions import Alias, mount_all
from aerona.api.dependencies import ServicesDep, reader
from aerona.api.schemas.common import ApiModel
from aerona.db.repositories.cosmos import CosmosRepository
from aerona.domain.enums.world import FateMode, ImageStyle, SonDistribution

router = APIRouter(tags=["settings"])

ALIASES = (Alias("PATCH", "/settings", "settings"),)


class WorldSettingsView(ApiModel):
    fate_mode: FateMode
    son_distribution: SonDistribution
    mortal_agents_per_epoch: int | None
    council_every_epochs: int | None
    mortal_agent_parallelism: int | None
    llm_enabled: bool
    image_generation: bool
    image_style: ImageStyle
    image_style_custom: str


@router.get("/settings", response_model=WorldSettingsView)
async def read_settings(services: ServicesDep) -> WorldSettingsView:
    async with reader(services) as session:
        cosmos = await CosmosRepository(session).require_cosmos()
    return WorldSettingsView(
        fate_mode=cosmos.fate_mode,
        son_distribution=cosmos.son_distribution,
        mortal_agents_per_epoch=cosmos.mortal_agents_per_epoch,
        council_every_epochs=cosmos.council_every_epochs,
        mortal_agent_parallelism=cosmos.mortal_agent_parallelism,
        llm_enabled=services.agents.llm_enabled,
        image_generation=services.application.images.available,
        image_style=cosmos.image_style,
        image_style_custom=cosmos.image_style_custom,
    )


mount_all(router, ALIASES, tag="settings")
