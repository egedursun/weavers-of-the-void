from dataclasses import dataclass
from types import MappingProxyType

from aerona.domain.enums.cosmography import PhenomenonKind
from aerona.domain.enums.divine import OuterHunger
from aerona.domain.enums.domain import Domain
from aerona.domain.enums.entity import EntityType
from aerona.domain.enums.node import NodeKind
from aerona.domain.enums.transform import TransformEnd, TransformKind
from aerona.domain.enums.world import WorldType

K = TransformKind
E = TransformEnd


@dataclass(frozen=True)
class TransformSpec:
    source: TransformEnd
    target: TransformEnd
    label: str
    existing: bool
    warned: bool = False
    watched: bool = False


TRANSFORMS = MappingProxyType(
    {
        K.DEIFICATION: TransformSpec(E.MORTAL, E.SON, "Deification", existing=True),
        K.MANTLING: TransformSpec(E.MORTAL, E.SON, "Mantling", existing=True),
        K.SPIRIT_RISING: TransformSpec(E.MORTAL, E.SPIRIT, "Rising as a spirit", existing=True),
        K.REINCARNATION: TransformSpec(E.SPIRIT, E.MORTAL, "Reincarnation", existing=True),
        K.POSSESSION: TransformSpec(E.SPIRIT, E.MORTAL, "Possession", existing=True),
        K.LOCAL_GOD: TransformSpec(E.SPIRIT, E.GOD, "A spirit raised to a local god", existing=False, watched=True),
        K.BEAST_CURSE: TransformSpec(E.MORTAL, E.BEAST, "Cursed into a beast", existing=False, watched=True),
        K.CURSE_LIFTED: TransformSpec(E.BEAST, E.MORTAL, "A beast's curse lifted", existing=False, watched=True),
        K.UPLIFT: TransformSpec(E.SPECIES, E.PEOPLE, "Uplift", existing=True),
        K.CITY_STATE: TransformSpec(E.SETTLEMENT, E.POLITY, "A city becomes a state", existing=True),
        K.SECESSION: TransformSpec(E.FACTION, E.POLITY, "Secession", existing=True),
        K.THEOCRACY: TransformSpec(E.CULT, E.POLITY, "Theocracy", existing=True),
        K.TITLE_RAISED: TransformSpec(E.POLITY, E.TITLE, "A realm raised to a title", existing=True),
        K.REALM_FROM_TITLE: TransformSpec(E.TITLE, E.POLITY, "A title made a realm", existing=False, watched=True),
        K.MANIFESTATION: TransformSpec(E.LEGEND, E.CREATION, "Manifestation", existing=True),
        K.LEGEND_FIXED: TransformSpec(E.LEGEND, E.ARTWORK, "A legend fixed into an artwork", existing=True),
        K.ARTWORK_REMEMBERED: TransformSpec(E.ARTWORK, E.LEGEND, "A lost artwork remembered as a legend", existing=False),
        K.EVENT_PHENOMENON: TransformSpec(E.EVENT, E.PHENOMENON, "An event becomes a phenomenon", existing=True),
        K.DEAD_GOD: TransformSpec(E.SON, E.PLACE, "The body of a dead god becomes a place", existing=True),
        K.CONSTRUCT: TransformSpec(E.MADE_THING, E.BEAST, "A made thing wakes as a construct", existing=True),
        K.BEAST_PROMOTION: TransformSpec(E.SPECIES, E.BEAST, "A creature raised to a beast", existing=True),
        K.LANGUAGE_DEATH: TransformSpec(E.LANGUAGE, E.LANGUAGE, "A language dies", existing=True),
        K.LANGUAGE_REVIVAL: TransformSpec(E.LANGUAGE, E.LANGUAGE, "A dead language revived", existing=True),
        K.THEORY_SETTLED: TransformSpec(E.THEORY, E.KNOWLEDGE, "A theory settled into knowledge", existing=False, watched=True),
        K.TRADITION_CODIFIED: TransformSpec(E.TRADITION, E.LAW, "A custom codified into law", existing=False, watched=True),
        K.FALL: TransformSpec(E.SON, E.MORTAL, "Fall from godhood", existing=False, warned=True, watched=True),
        K.RESTORATION: TransformSpec(E.MORTAL, E.SON, "A fallen god regains godhood", existing=False, watched=True),
        K.LOSS_OF_SAPIENCE: TransformSpec(E.PEOPLE, E.SPECIES, "Loss of sapience", existing=False, watched=True),
        K.ETHNORELIGIOUS: TransformSpec(E.CULT, E.PEOPLE, "A faith becomes a people", existing=False, watched=True),
        K.NATION_BUILDING: TransformSpec(E.POLITY, E.PEOPLE, "A realm forges a people", existing=False, watched=True),
        K.HOUSE_PEOPLE: TransformSpec(E.HOUSE, E.PEOPLE, "A house grows into a people", existing=False, watched=True),
        K.POCKET_WORLD: TransformSpec(E.PHENOMENON, E.WORLD, "A phenomenon grows into a world", existing=False, watched=True),
        K.WORLD_SOUL: TransformSpec(E.WORLD, E.GOD, "A world's soul ascends", existing=False, watched=True),
        K.STAR_GOD: TransformSpec(E.STAR, E.GOD, "A star raised to godhood", existing=False, watched=True),
        K.SACRALISATION: TransformSpec(E.IDEOLOGY, E.CULT, "Sacralisation", existing=False, watched=True),
        K.SECULARISATION: TransformSpec(E.CULT, E.IDEOLOGY, "Secularisation", existing=False, watched=True),
        K.PROGENITOR: TransformSpec(E.BEAST, E.SPECIES, "A beast founds a species", existing=False, watched=True),
        K.OUTER_ENTRY: TransformSpec(E.OUTER_BEING, E.GOD, "An outer being enters the cosmos", existing=False, watched=True),
        K.CORRUPTION: TransformSpec(E.SON, E.OUTER_BEING, "Corruption into an outer being", existing=False, warned=True, watched=True),
        K.COLOSSAL_CORPSE: TransformSpec(E.BEAST, E.PLACE, "A colossal corpse becomes a place", existing=False),
    }
)

ENGINE_KINDS = frozenset(kind for kind, spec in TRANSFORMS.items() if spec.watched)
WARNED_KINDS = frozenset(kind for kind, spec in TRANSFORMS.items() if spec.warned)

POCKET_WORLDS = MappingProxyType(
    {
        PhenomenonKind.OUTSIDE_OPENING: WorldType.VOID_POCKET,
        PhenomenonKind.BARREN_GROUND: WorldType.VOID_POCKET,
        PhenomenonKind.GRAVITY_ANOMALY: WorldType.VOID_POCKET,
        PhenomenonKind.TIME_DISTORTION: WorldType.VOID_POCKET,
        PhenomenonKind.MOVING_FOG: WorldType.DREAM,
        PhenomenonKind.DISTANT_VIEW: WorldType.DREAM,
    }
)

HUNGER_DOMAINS = MappingProxyType(
    {
        OuterHunger.SOULS: Domain.DEATH,
        OuterHunger.KNOWLEDGE: Domain.KNOWLEDGE,
        OuterHunger.LIGHT: Domain.SHADOW,
        OuterHunger.NAMES: Domain.OATH,
        OuterHunger.MEMORIES: Domain.MEMORY,
        OuterHunger.DREAMS: Domain.DREAM,
        OuterHunger.TIME: Domain.TIME,
    }
)

END_OF_TYPE = MappingProxyType(
    {
        EntityType.MORTAL: E.MORTAL,
        EntityType.SPIRIT: E.SPIRIT,
        EntityType.BEAST: E.BEAST,
        EntityType.SPECIES: E.SPECIES,
        EntityType.PEOPLE: E.PEOPLE,
        EntityType.CULT: E.CULT,
        EntityType.POLITY: E.POLITY,
        EntityType.HOUSE: E.HOUSE,
        EntityType.SETTLEMENT: E.SETTLEMENT,
        EntityType.FACTION: E.FACTION,
        EntityType.TITLE: E.TITLE,
        EntityType.LEGEND: E.LEGEND,
        EntityType.ARTWORK: E.ARTWORK,
        EntityType.EVENT: E.EVENT,
        EntityType.PHENOMENON: E.PHENOMENON,
        EntityType.IDEOLOGY: E.IDEOLOGY,
        EntityType.OUTER_BEING: E.OUTER_BEING,
        EntityType.PLACE: E.PLACE,
        EntityType.ITEM: E.MADE_THING,
        EntityType.STRUCTURE: E.MADE_THING,
        EntityType.LANGUAGE: E.LANGUAGE,
        EntityType.KNOWLEDGE: E.KNOWLEDGE,
        EntityType.THEORY: E.THEORY,
        EntityType.TRADITION: E.TRADITION,
        EntityType.LAW: E.LAW,
    }
)

END_OF_NODE = MappingProxyType({NodeKind.SON: E.SON, NodeKind.FOREIGN_GOD: E.GOD, NodeKind.WORLD: E.WORLD, NodeKind.STAR: E.STAR})
