from datetime import datetime

from pydantic import Field

from aerona.api.schemas.common import ApiModel, RequestModel
from aerona.constants.providers import (
    BASE_URL_MAX_LENGTH,
    CHAIN_MAX_ENTRIES,
    CONNECTION_LABEL_MAX_LENGTH,
    LOGIN_INPUT_MAX_LENGTH,
    MODEL_NAME_MAX_LENGTH,
    SECRET_MAX_LENGTH,
)
from aerona.domain.enums.providers import LoginState, ModelRole, ProviderFamily, ProviderKind


class ProviderKindView(ApiModel):
    kind: ProviderKind
    label: str
    family: ProviderFamily
    roles: list[ModelRole]
    asks_key: bool
    asks_address: bool
    key_page: str
    terms: str | None
    refusal: str | None


class ProviderConnectionView(ApiModel):
    id: int
    kind: ProviderKind
    label: str
    secret_hint: str
    base_url: str
    logged_in_at: datetime | None
    created_at: datetime
    unusable: str | None
    from_server: bool


class ChainEntryView(ApiModel):
    id: int
    connection_id: int
    model: str
    tools_work: bool | None
    sees_images: bool | None
    checked_at: datetime | None
    check_note: str


class ModelRoleView(ApiModel):
    role: ModelRole
    label: str
    description: str
    entries: list[ChainEntryView]
    server_entries: list[ChainEntryView]


class ProvidersView(ApiModel):
    workspace_id: int | None
    personal: bool
    editable: bool
    gateway_ready: bool
    kinds: list[ProviderKindView]
    connections: list[ProviderConnectionView]
    roles: list[ModelRoleView]


class ConnectionCreate(RequestModel):
    kind: ProviderKind
    label: str = Field(default="", max_length=CONNECTION_LABEL_MAX_LENGTH)
    secret: str = Field(default="", max_length=SECRET_MAX_LENGTH)
    base_url: str = Field(default="", max_length=BASE_URL_MAX_LENGTH)


class ConnectionEdit(RequestModel):
    label: str | None = Field(default=None, max_length=CONNECTION_LABEL_MAX_LENGTH)
    secret: str | None = Field(default=None, max_length=SECRET_MAX_LENGTH)
    base_url: str | None = Field(default=None, max_length=BASE_URL_MAX_LENGTH)


class ChainLinkBody(RequestModel):
    connection_id: int = Field(ge=1)
    model: str = Field(default="", max_length=MODEL_NAME_MAX_LENGTH)


class ChainPut(RequestModel):
    entries: list[ChainLinkBody] = Field(max_length=CHAIN_MAX_ENTRIES)


class ProviderModels(ApiModel):
    models: list[str]


class ProviderLoginView(ApiModel):
    state: LoginState
    output: str
    links: list[str]
    code: str
    note: str
    started_at: datetime
    ended_at: datetime | None


class LoginInput(RequestModel):
    text: str = Field(max_length=LOGIN_INPUT_MAX_LENGTH)
