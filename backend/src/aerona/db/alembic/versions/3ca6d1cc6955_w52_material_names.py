import sqlalchemy as sa
from alembic import op

revision = "3ca6d1cc6955"
down_revision = "9c9860da5822"
branch_labels = None
depends_on = None

OLD = (
    "wood",
    "bone",
    "hide",
    "leather",
    "cloth",
    "stone",
    "flint",
    "obsidian",
    "copper",
    "tin",
    "bronze",
    "iron",
    "steel",
    "silver",
    "gold",
    "glass",
    "crystal",
    "ivory",
    "chitin",
    "great_bone",
    "star_metal",
    "void_glass",
    "godflesh",
    "living_wood",
    "salt",
    "amber",
    "lead",
    "skysteel",
    "sulfur",
    "clay",
    "gems",
    "mud_brick",
    "fired_brick",
    "dressed_stone",
    "rubble",
    "lime_mortar",
    "hydraulic_concrete",
    "thatch",
    "tile",
)
NEW = (
    "wood",
    "calcified_tissue",
    "hide",
    "leather",
    "cloth",
    "stone",
    "flint",
    "obsidian",
    "copper",
    "tin",
    "bronze",
    "iron",
    "steel",
    "silver",
    "gold",
    "glass",
    "crystal",
    "ivory",
    "chitin",
    "great_beast_tissue",
    "star_metal",
    "void_glass",
    "divine_tissue",
    "living_wood",
    "halite",
    "amber",
    "lead",
    "skysteel",
    "sulfur",
    "clay",
    "gems",
    "mud_brick",
    "fired_brick",
    "dressed_stone",
    "rubble",
    "lime_mortar",
    "hydraulic_concrete",
    "thatch",
    "tile",
)
RENAMED = {"bone": "calcified_tissue", "great_bone": "great_beast_tissue", "godflesh": "divine_tissue", "salt": "halite"}
COLUMNS = (
    ("creature_anatomy", "hoards", "hoards", True),
    ("power_source_resistances", "material", "material", True),
    ("constructs", "material", "material", False),
    ("currencies", "metal", "metal", True),
    ("place_secrets", "material", "material", True),
    ("production_runs", "material", "material", True),
    ("record_media", "material", "material", True),
    ("structure_designs", "material", "material", True),
    ("trade_flows", "material", "material", True),
    ("world_materials", "base_kind", "base_kind", True),
    ("community_stocks", "material", "material", True),
    ("equipment_models", "material", "material", True),
    ("node_materials", "material", "material", True),
    ("replicator_lines", "feedstock", "feedstock", False),
    ("resource_profiles", "material", "material", True),
    ("resource_profiles", "byproduct_material", "byproduct_material", True),
    ("species_products", "material", "material", True),
    ("structure_design_sections", "material", "material", True),
    ("structure_sections", "material", "material", True),
    ("prostheses", "material", "material", False),
)
JSON_COLUMNS = (("item_profiles", "secondary_materials"), ("beast_profiles", "hoard"))
PRODUCTS = {"bone": "calcified_tissue", "great_bone": "great_beast_tissue"}


def enum_of(values: tuple[str, ...], name: str) -> sa.Enum:
    return sa.Enum(*values, name=name, native_enum=False, create_constraint=True, length=40)


def rename(mapping: dict[str, str], before: tuple[str, ...], after: tuple[str, ...]) -> None:
    both = tuple(dict.fromkeys((*before, *after)))
    for table, column, name, nullable in COLUMNS:
        with op.batch_alter_table(table, schema=None) as batch_op:
            batch_op.alter_column(column, existing_type=enum_of(before, name), type_=enum_of(both, name), existing_nullable=nullable)
        for was, now in mapping.items():
            op.execute(f"UPDATE {table} SET {column} = '{now}' WHERE {column} = '{was}'")
        with op.batch_alter_table(table, schema=None) as batch_op:
            batch_op.alter_column(column, existing_type=enum_of(both, name), type_=enum_of(after, name), existing_nullable=nullable)
    for was, now in mapping.items():
        for table, column in JSON_COLUMNS:
            op.execute(f"UPDATE {table} SET {column} = replace({column}, '\"{was}\"', '\"{now}\"') WHERE {column} LIKE '%\"{was}\"%'")
        op.execute(f"UPDATE incident_facts SET enum_value = '{now}' WHERE enum_name IN ('MaterialKind', 'YieldProduct') AND enum_value = '{was}'")
        op.execute(f"UPDATE state_changes SET before_text = '{now}' WHERE before_text = '{was}' AND table_name IN ({', '.join(repr(t) for t, *_ in COLUMNS)})")
        op.execute(f"UPDATE state_changes SET after_text = '{now}' WHERE after_text = '{was}' AND table_name IN ({', '.join(repr(t) for t, *_ in COLUMNS)})")


def upgrade() -> None:
    rename(RENAMED, OLD, NEW)
    for was, now in PRODUCTS.items():
        op.execute(f"UPDATE species_products SET product = '{now}' WHERE product = '{was}'")


def downgrade() -> None:
    for was, now in PRODUCTS.items():
        op.execute(f"UPDATE species_products SET product = '{was}' WHERE product = '{now}'")
    rename({now: was for was, now in RENAMED.items()}, NEW, OLD)
