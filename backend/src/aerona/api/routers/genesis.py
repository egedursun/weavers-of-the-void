from typing import Any

from fastapi import APIRouter, status
from pydantic import Field

from aerona.api.background import submit
from aerona.api.dependencies import ServicesDep, reader
from aerona.api.schemas.common import ApiModel, JobAccepted, RequestModel
from aerona.constants.genesis import FIRST_SONS_CEILING
from aerona.db.repositories.cosmos import CosmosRepository
from aerona.domain.enums.job import JobKind
from aerona.domain.enums.rarity import Rarity
from aerona.domain.enums.world import LoreLanguage
from aerona.domain.models.genesis import GenesisSettings
from aerona.epoch.concurrency import WORLD_GROUP
from aerona.jobs.context import JobContext
from aerona.services.genesis_wizard import SEED_MAX_LENGTH, TONE_MAX_LENGTH, GenesisCommand, WizardInput, WizardOptions, options

router = APIRouter(tags=["genesis"])

CREATOR_NAME_MAX_LENGTH = 60


class GenesisRequest(RequestModel):
    creator_name: str = Field(max_length=CREATOR_NAME_MAX_LENGTH)
    seed: str = Field(max_length=SEED_MAX_LENGTH)
    tone: str | None = Field(default=None, max_length=TONE_MAX_LENGTH)
    lore_language: LoreLanguage = LoreLanguage.ENGLISH
    wizard: WizardInput | None = None
    first_sons: list[Rarity] | None = Field(default=None, max_length=FIRST_SONS_CEILING)


@router.get("/genesis/wizard", response_model=WizardOptions)
async def wizard_options(services: ServicesDep) -> WizardOptions:
    return options(services.rules.current)


@router.post("/genesis", response_model=JobAccepted, status_code=status.HTTP_202_ACCEPTED)
async def start_genesis(request: GenesisRequest, services: ServicesDep) -> JobAccepted:
    wizard = services.genesis()
    command = GenesisCommand(
        creator_name=request.creator_name,
        seed=request.seed,
        tone=request.tone,
        lore_language=request.lore_language,
        wizard=request.wizard,
        first_sons=tuple(request.first_sons) if request.first_sons is not None else None,
    )
    await wizard.validate(command)

    async def work(context: JobContext) -> dict[str, Any]:
        return await wizard.run(command, context)

    return await submit(services, JobKind.GENESIS, WORLD_GROUP, work, request.model_dump(mode="json"), label="genesis")


class SavedGenesis(ApiModel):
    lore_language: LoreLanguage
    seed_idea: str
    tone: str
    settings: GenesisSettings | None


@router.get("/genesis/settings", response_model=SavedGenesis)
async def saved_genesis(services: ServicesDep) -> SavedGenesis:
    async with reader(services) as session:
        cosmos = await CosmosRepository(session).require_cosmos()
    return SavedGenesis(lore_language=cosmos.lore_language, seed_idea=cosmos.seed_idea, tone=cosmos.tone, settings=cosmos.genesis_settings)
