from aerona.domain.enums.entity import EntityType
from aerona.domain.enums.node import NodeKind
from aerona.services.player.catalog import ACTIONS_BY_ID

LORE = "lore:create"
SHAPED = "record:shape"

CREATORS: dict[str, str] = {
    EntityType.REGION: "region:shape",
    EntityType.PLACE: "place:create",
    EntityType.RESOURCE: "resource:create",
    EntityType.SETTLEMENT: "people:village",
    EntityType.SPECIES: "species:create",
    EntityType.PEOPLE: "people:found",
    EntityType.MORTAL: "mortal:shape",
    EntityType.ITEM: LORE,
    EntityType.STRUCTURE: "structure:commission",
    EntityType.LANGUAGE: LORE,
    EntityType.LEGEND: LORE,
    EntityType.TRADITION: LORE,
    EntityType.CULT: SHAPED,
    EntityType.FACTION: "faction:found",
    EntityType.CELESTIAL: SHAPED,
    EntityType.ARTWORK: LORE,
    EntityType.LAW: "law:enact",
    EntityType.SPIRIT: SHAPED,
    EntityType.KNOWLEDGE: LORE,
    EntityType.PROPHECY: LORE,
    EntityType.EVENT: "event:create",
    EntityType.VESSEL: "vessel:create",
    EntityType.OUTER_BEING: "horror:outer_being",
    EntityType.ARMY: "army:raise",
    EntityType.NATURAL_LAW: SHAPED,
    EntityType.TRADE_ROUTE: "trade_route:found",
    EntityType.DISEASE: "disease:create",
    EntityType.POLITY: "polity:found",
    EntityType.HOUSE: "house:found",
    EntityType.TREATY: "treaty:sign",
    EntityType.TITLE: "title:create",
    EntityType.IDEOLOGY: LORE,
    EntityType.RITE: LORE,
    EntityType.BEAST: "beast:create",
    EntityType.THEORY: LORE,
    EntityType.ART_FORM: LORE,
    EntityType.PHENOMENON: "phenomenon:create",
    EntityType.COSMIC_BEING: "cosmic_being:call",
    EntityType.VEHICLE_TYPE: "design:draw",
    EntityType.UNIT_TYPE: "unit_type:create",
    EntityType.EQUIPMENT_MODEL: "equipment_model:create",
    EntityType.DISH: "dish:create",
    EntityType.BUILDING_TYPE: "structure_design:create",
    EntityType.NETWORK: "network:found",
    EntityType.LEAGUE: "league:found",
    NodeKind.SON: "summon_son",
    NodeKind.FOREIGN_GOD: "foreign_god:place",
    NodeKind.WORLD: "create_world",
    NodeKind.STAR: "cosmic:hang_star",
    NodeKind.GALAXY: "galaxy:create",
    NodeKind.CLUSTER: "cluster:create",
    NodeKind.DIMENSION: "dimension:create",
}
ONE_OF_A_KIND = frozenset({NodeKind.CREATOR, NodeKind.ENTITY})
CHOSEN = frozenset({"name", "values"})


def test_every_kind_of_thing_has_a_creator() -> None:
    kinds = {*EntityType, *(kind for kind in NodeKind if kind not in ONE_OF_A_KIND)}
    assert sorted(kind for kind in kinds if kind not in CREATORS) == []


def test_every_creator_is_a_real_lever_that_takes_chosen_values() -> None:
    missing = sorted({lever for lever in CREATORS.values() if lever not in ACTIONS_BY_ID})
    assert missing == []
    blind = sorted({lever for lever in CREATORS.values() if not CHOSEN & set(ACTIONS_BY_ID[lever].input_model.model_fields)})
    assert blind == []
