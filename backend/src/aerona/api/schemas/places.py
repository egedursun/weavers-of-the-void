from aerona.api.schemas.common import ApiModel
from aerona.domain.enums.culture import MagicSchool
from aerona.domain.enums.material import MaterialKind
from aerona.domain.enums.place import DiscoveryMode, PlaceKind, SacredClass, SecretKind, SecretOrigin
from aerona.domain.enums.society import KnowledgeBranch


class PlaceSecretView(ApiModel):
    id: int
    kind: SecretKind
    strength: int
    sealed: bool
    held: bool
    origin: SecretOrigin
    material: MaterialKind | None
    school: MagicSchool | None
    branch: KnowledgeBranch | None
    hidden_by_son_id: int | None
    created_epoch: int
    revealed_epoch: int | None
    revealed_by: DiscoveryMode | None
    revealed_by_entity_id: int | None
    revealed_by_name: str | None
    released_epoch: int | None
    result_entity_id: int | None
    result_name: str | None


class PlaceProfileView(ApiModel):
    place_id: int
    kind: PlaceKind
    sacred_class: SacredClass
    deep: bool
    sacredness: int
    sacred_target: int
    pilgrims: int
    holy_site: bool
    pilgrimage_site: bool
    nexus: bool
    mystery: int
    mystery_held: bool
    battles: int
    locked: list[str]
    secrets: list[PlaceSecretView]
