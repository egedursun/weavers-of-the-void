import os
from functools import lru_cache
from pathlib import Path

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

from aerona.constants.accounts import (
    DEFAULT_LOCKOUT_ATTEMPTS,
    DEFAULT_LOCKOUT_MINUTES,
    DEFAULT_PASSWORD_MIN_LENGTH,
    DEFAULT_PRESENCE_TTL_SECONDS,
    DEFAULT_REASON_MAX_LENGTH,
    DEFAULT_SESSION_IDLE_DAYS,
    DEFAULT_SESSION_MAX_DAYS,
)
from aerona.constants.library import (
    DEFAULT_IDLE_MINUTES,
    DEFAULT_IMPORT_MAX_MB,
    DEFAULT_OPEN_UNIVERSES,
    DEFAULT_PARALLEL_EPOCHS,
    DEFAULT_TRASH_DAYS,
)
from aerona.constants.llm import EMBED_THREADS_RESERVED, ClaudeAuth
from aerona.constants.media import DEFAULT_MEDIA_BUCKET, DEFAULT_MEDIA_ENDPOINT, DEFAULT_MEDIA_REGION, MediaBackend
from aerona.paths import ProcessPaths, UniversePaths


def embedding_threads() -> int:
    return max(1, (os.process_cpu_count() or EMBED_THREADS_RESERVED + 1) - EMBED_THREADS_RESERVED)


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
    embed_threads: int = Field(default_factory=embedding_threads)
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
    media_prefix: str = ""
    library_open_universes: int = Field(default=DEFAULT_OPEN_UNIVERSES, ge=1)
    library_idle_minutes: float = Field(default=DEFAULT_IDLE_MINUTES, gt=0)
    library_parallel_epochs: int = Field(default=DEFAULT_PARALLEL_EPOCHS, ge=1)
    library_import_max_mb: int = Field(default=DEFAULT_IMPORT_MAX_MB, ge=1)
    library_trash_days: int = Field(default=DEFAULT_TRASH_DAYS, ge=0)
    library_root: Path | None = None
    cookie_secure: bool = False
    accounts_lockout_attempts: int = Field(default=DEFAULT_LOCKOUT_ATTEMPTS, ge=1)
    accounts_lockout_minutes: float = Field(default=DEFAULT_LOCKOUT_MINUTES, gt=0)
    accounts_password_min_length: int = Field(default=DEFAULT_PASSWORD_MIN_LENGTH, ge=8)
    accounts_session_idle_days: float = Field(default=DEFAULT_SESSION_IDLE_DAYS, gt=0)
    accounts_session_max_days: float = Field(default=DEFAULT_SESSION_MAX_DAYS, gt=0)
    team_presence_ttl_seconds: float = Field(default=DEFAULT_PRESENCE_TTL_SECONDS, gt=0)
    team_reason_max_length: int = Field(default=DEFAULT_REASON_MAX_LENGTH, ge=1)
    universe_id: str = ""

    @property
    def claude_auth(self) -> ClaudeAuth:
        return ClaudeAuth.TOKEN if self.claude_code_oauth_token.get_secret_value() else ClaudeAuth.LOGIN

    @property
    def paths(self) -> UniversePaths:
        return UniversePaths(self.data_dir)

    @property
    def process(self) -> ProcessPaths:
        return ProcessPaths(self.library_root or self.data_dir)

    @property
    def database_path(self) -> Path:
        return self.paths.database

    @property
    def database_url(self) -> str:
        return f"sqlite+aiosqlite:///{self.database_path}"

    @property
    def media_dir(self) -> Path:
        return self.paths.media

    @property
    def backups_dir(self) -> Path:
        return self.paths.backups

    @property
    def exports_dir(self) -> Path:
        return self.paths.exports

    @property
    def log_file(self) -> Path:
        return self.process.log_file

    def ensure_directories(self) -> None:
        for directory in (self.data_dir, self.backups_dir, self.exports_dir, self.log_file.parent):
            directory.mkdir(parents=True, exist_ok=True)

    def ensure_process_directories(self) -> None:
        for directory in (self.process.root, self.process.logs, self.process.universes):
            directory.mkdir(parents=True, exist_ok=True)

    def for_universe(self, universe_id: str, media_prefix: str) -> "Settings":
        process = self.process
        secondary = self.secondary_backup_dir / universe_id if self.secondary_backup_dir is not None else None
        return self.model_copy(
            update={
                "data_dir": process.universe(universe_id).root,
                "library_root": process.root,
                "universe_id": universe_id,
                "media_prefix": media_prefix,
                "secondary_backup_dir": secondary,
            }
        )


@lru_cache
def get_settings() -> Settings:
    return Settings()
