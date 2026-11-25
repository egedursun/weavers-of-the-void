from functools import lru_cache
from pathlib import Path

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

from aerona.constants.llm import ClaudeAuth
from aerona.constants.media import DEFAULT_MEDIA_BUCKET, DEFAULT_MEDIA_ENDPOINT, DEFAULT_MEDIA_REGION, MediaBackend
from aerona.constants.paths import (
    BACKUPS_DIRNAME,
    DATABASE_FILENAME,
    EXPORTS_DIRNAME,
    LOG_FILENAME,
    LOGS_DIRNAME,
    MEDIA_DIRNAME,
)


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="AERONA_", env_file=("../.env", ".env"), extra="ignore")

    data_dir: Path = Field(default=Path("data"))
    host: str = "127.0.0.1"
    port: int = 8000
    log_level: str = "INFO"
    llm_enabled: bool = True
    claude_code_oauth_token: SecretStr = Field(default=SecretStr(""), validation_alias="CLAUDE_CODE_OAUTH_TOKEN")
    image_worker_url: str = ""
    divine_will_upload_max_mb: int = 50
    divine_will_upload_max_files: int = 10
    embed_threads: int = 2
    embed_model_dir: Path | None = None
    secondary_backup_dir: Path | None = None
    static_dir: Path | None = None
    allowed_origins: list[str] = Field(default_factory=lambda: ["http://localhost:5173", "http://127.0.0.1:5173"])
    media_backend: MediaBackend = MediaBackend.FILE
    media_endpoint: str = DEFAULT_MEDIA_ENDPOINT
    media_bucket: str = DEFAULT_MEDIA_BUCKET
    media_access_key: str = ""
    media_secret_key: SecretStr = SecretStr("")
    media_region: str = DEFAULT_MEDIA_REGION
    media_secure: bool = False

    @property
    def claude_auth(self) -> ClaudeAuth:
        return ClaudeAuth.TOKEN if self.claude_code_oauth_token.get_secret_value() else ClaudeAuth.LOGIN

    @property
    def database_path(self) -> Path:
        return self.data_dir / DATABASE_FILENAME

    @property
    def database_url(self) -> str:
        return f"sqlite+aiosqlite:///{self.database_path}"

    @property
    def media_dir(self) -> Path:
        return self.data_dir / MEDIA_DIRNAME

    @property
    def backups_dir(self) -> Path:
        return self.data_dir / BACKUPS_DIRNAME

    @property
    def exports_dir(self) -> Path:
        return self.data_dir / EXPORTS_DIRNAME

    @property
    def log_file(self) -> Path:
        return self.data_dir / LOGS_DIRNAME / LOG_FILENAME

    def ensure_directories(self) -> None:
        for directory in (self.data_dir, self.backups_dir, self.exports_dir, self.log_file.parent):
            directory.mkdir(parents=True, exist_ok=True)


@lru_cache
def get_settings() -> Settings:
    return Settings()
