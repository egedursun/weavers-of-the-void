from aerona.api.schemas.common import ApiModel
from aerona.api.schemas.records import NodeRef
from aerona.domain.enums.culture import MagicSchool
from aerona.domain.enums.domain import Domain
from aerona.domain.enums.dominion import BeliefStance, CreatureDeed, CreatureLesson, DivineScale, MagicSiteKind, Manifestation, PerceivedAlignment


class DominionClaimView(ApiModel):
    god: NodeRef | None
    region: NodeRef | None
    strength: int
    temples: int
    holy_sites: int
    prophets: int
    miracles: int
    worship: int
    spread: int
    epoch: int
    ruling: bool
    locked: list[str]


class ScaleView(ApiModel):
    scale: DivineScale
    value: int
    stored: bool
    locked: list[str]


class GodDesignView(ApiModel):
    budget: int
    spent: int
    dominion_strength: int
    magic_aptitude: int
    manifestation_strength: int
    stats_pct: int
    rank: int
    checked_epoch: int
    locked: list[str]


class ImageView(ApiModel):
    believed_alignment: PerceivedAlignment
    believed_wrath: int
    believed_mercy: int
    believed_domain: Domain | None
    manifestation: Manifestation
    intensity: int
    worship_share: int
    crisis: int
    malleability: int
    pull: int
    domain_pressure: int
    stance: BeliefStance
    epoch: int
    locked: list[str]


class MiracleView(ApiModel):
    id: int
    god: NodeRef | None
    kind: str
    epoch: int
    target: NodeRef | None
    region: NodeRef | None
    magnitude: int
    witnesses: int
    need: int
    novelty: int
    legibility: int
    belief: int
    credited: NodeRef | None
    locked: list[str]


class DeedWeightView(ApiModel):
    deed: CreatureDeed
    weight: int


class LessonView(ApiModel):
    id: int
    deed: CreatureDeed
    lesson: CreatureLesson
    strength: int
    epoch: int


class CreatureView(ApiModel):
    creature: NodeRef | None
    god: NodeRef | None
    weights: list[DeedWeightView]
    hunger: int
    neglect_epochs: int
    last_deed: CreatureDeed | None
    deeds: int
    since_epoch: int
    lessons: list[LessonView]
    locked: list[str]


class ThroneView(ApiModel):
    id: int
    world: NodeRef | None
    place: NodeRef | None
    power: int
    holder: NodeRef | None
    since_epoch: int | None
    locked: list[str]


class MagicSiteView(ApiModel):
    id: int
    place: NodeRef | None
    kind: MagicSiteKind
    school: MagicSchool
    strength: int
    found_epoch: int | None
    found_by: NodeRef | None
    holder: NodeRef | None
    output: int
    target_world: NodeRef | None
    locked: list[str]


class GodDominionView(ApiModel):
    node: NodeRef
    claims: list[DominionClaimView]
    scales: list[ScaleView]
    design: GodDesignView | None
    image: ImageView | None
    miracles: list[MiracleView]
    credited: list[MiracleView]
    creatures: list[CreatureView]
    thrones: list[ThroneView]
    sites: list[MagicSiteView]


class RegionRuleView(ApiModel):
    region: NodeRef | None
    god: NodeRef | None
    share: int
    rivals: int
    epoch: int


class PlaceDominionView(ApiModel):
    place: NodeRef
    rule: RegionRuleView | None
    claims: list[DominionClaimView]
    thrones: list[ThroneView]
    sites: list[MagicSiteView]
    creatures: list[CreatureView]


class WorldDominionView(ApiModel):
    world: NodeRef
    rules: list[RegionRuleView]
    thrones: list[ThroneView]
    sites: list[MagicSiteView]
