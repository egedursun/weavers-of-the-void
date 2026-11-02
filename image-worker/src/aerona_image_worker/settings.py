from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

from aerona_image_worker.constants.defaults import (
    DEFAULT_HOST,
    DEFAULT_IDLE_UNLOAD_SECONDS,
    DEFAULT_IMAGE_TIMEOUT_SECONDS,
    DEFAULT_LOAD_TIMEOUT_SECONDS,
    DEFAULT_LOG_LEVEL,
    DEFAULT_PORT,
    DEFAULT_RETAINED_JOBS,
    ENV_FILES,
    ENV_PREFIX,
)
from aerona_image_worker.constants.models import DEFAULT_MODEL_IDS
from aerona_image_worker.domain.enums import BackendName, Isolation


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix=ENV_PREFIX, env_file=ENV_FILES, extra="ignore")

    backend: BackendName
    model_id: str = ""
    host: str = DEFAULT_HOST
    port: int = DEFAULT_PORT
    log_level: str = DEFAULT_LOG_LEVEL
    isolation: Isolation = Isolation.PROCESS
    load_timeout_seconds: float = Field(default=DEFAULT_LOAD_TIMEOUT_SECONDS, gt=0)
    image_timeout_seconds: float = Field(default=DEFAULT_IMAGE_TIMEOUT_SECONDS, gt=0)
    idle_unload_seconds: float = Field(default=DEFAULT_IDLE_UNLOAD_SECONDS, ge=0)
    retained_jobs: int = Field(default=DEFAULT_RETAINED_JOBS, ge=1)
    fake_load_seconds: float = Field(default=0.0, ge=0)
    fake_step_seconds: float = Field(default=0.0, ge=0)
    fake_failure_prompt: str = ""

    @property
    def resolved_model_id(self) -> str:
        return self.model_id or DEFAULT_MODEL_IDS[self.backend]


@lru_cache
def get_settings() -> Settings:
    return Settings()
