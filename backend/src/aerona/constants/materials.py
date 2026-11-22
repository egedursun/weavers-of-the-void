from collections.abc import Mapping
from types import MappingProxyType

RENAMED_MATERIALS: Mapping[str, str] = MappingProxyType(
    {"bone": "calcified_tissue", "great_bone": "great_beast_tissue", "godflesh": "divine_tissue", "salt": "halite"}
)
MATERIAL_TEXT_COLUMNS = (
    ("item_profiles", "material"),
    ("vessel_profiles", "hull_material"),
    ("vessel_profiles", "fabric_material"),
    ("army_units", "material"),
    ("inspirations", "material"),
)
MATERIAL_KEY_JSON_COLUMNS = (("region_environment", "mineral_layers"),)
