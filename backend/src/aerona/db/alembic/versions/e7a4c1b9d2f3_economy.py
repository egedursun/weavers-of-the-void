import sqlalchemy as sa
from alembic import op

revision = "e7a4c1b9d2f3"
down_revision = "d5e1a0c3b7f2"
branch_labels = None
depends_on = None

OLD_ENTITY_TYPES = (
    "region",
    "place",
    "resource",
    "settlement",
    "species",
    "people",
    "mortal",
    "item",
    "structure",
    "language",
    "legend",
    "tradition",
    "cult",
    "faction",
    "celestial",
    "artwork",
    "law",
    "spirit",
    "knowledge",
    "prophecy",
    "event",
    "vessel",
    "outer_being",
    "army",
    "natural_law",
)
NEW_ENTITY_TYPES = (*OLD_ENTITY_TYPES, "trade_route")
OLD_MATERIALS = (
    "wood",
    "bone",
    "hide",
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
    "dragonbone",
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
)
NEW_MATERIALS = (*OLD_MATERIALS[:3], "leather", *OLD_MATERIALS[3:])
OLD_CAUSES = (
    "hostility",
    "uprising",
    "tribute_revolt",
    "incited",
    "declared",
    "betrayal",
    "conquest_journey",
    "foreign_god",
    "independence",
    "vendetta",
    "grudge",
    "divine_grudge",
    "rivalry",
    "debt",
    "espionage",
    "sabotage",
    "envy",
    "schism",
    "beast",
    "resource",
)
NEW_CAUSES = (*OLD_CAUSES, "trade_route")
WIDENED = (
    ("entities", "entity_type", OLD_ENTITY_TYPES, NEW_ENTITY_TYPES, False),
    ("son_powers", "param_entity_type", OLD_ENTITY_TYPES, NEW_ENTITY_TYPES, True),
    ("prostheses", "material", OLD_MATERIALS, NEW_MATERIALS, False),
    ("bonds", "war_cause", OLD_CAUSES, NEW_CAUSES, True),
    ("wars", "cause", OLD_CAUSES, NEW_CAUSES, False),
)
PROFILE_COLUMNS = (
    "resource_entity_id",
    "commodity",
    "material",
    "reserve",
    "initial_reserve",
    "richness",
    "regeneration",
    "extraction_difficulty",
    "required_branch",
    "required_level",
    "quality",
    "byproduct_material",
    "byproduct_pct",
    "revealed",
    "sealed_until_epoch",
    "last_output",
)
PROFILE_VALUES = (
    "rc.resource_entity_id",
    "CASE rc.commodity WHEN 'food' THEN 'grain' WHEN 'ore' THEN 'ore' ELSE 'timber' END",
    "CASE rc.commodity WHEN 'goods' THEN 'wood' ELSE NULL END",
    "MIN(8000, MAX(0, COALESCE(json_extract(e.stats, '$.abundance'), 50)) * 20)",
    "2000",
    "MAX(1, MIN(100, COALESCE(json_extract(e.stats, '$.value'), 50)))",
    "CASE rc.commodity WHEN 'ore' THEN 0 ELSE 240 END",
    "CASE rc.commodity WHEN 'ore' THEN 55 WHEN 'goods' THEN 30 ELSE 20 END",
    "NULL",
    "0",
    "MAX(0, MIN(100, COALESCE(json_extract(e.stats, '$.might'), 50)))",
    "NULL",
    "0",
    "1",
    "NULL",
    "0",
)
FOOD_KINDS = ("grain", "livestock", "fish", "fodder", "bread")
ORE_KINDS = ("ore", "stone")


def profiles_from_commodities() -> str:
    source = "FROM resource_commodities rc JOIN entities e ON e.id = rc.resource_entity_id"
    return f"INSERT INTO resource_profiles ({', '.join(PROFILE_COLUMNS)}) SELECT {', '.join(PROFILE_VALUES)} {source}"


def commodities_from_profiles() -> str:
    food = ", ".join(f"'{kind}'" for kind in FOOD_KINDS)
    ore = ", ".join(f"'{kind}'" for kind in ORE_KINDS)
    aggregate = f"CASE WHEN commodity IN ({food}) THEN 'food' WHEN commodity IN ({ore}) THEN 'ore' ELSE 'goods' END"
    return f"INSERT INTO resource_commodities (resource_entity_id, commodity) SELECT resource_entity_id, {aggregate} FROM resource_profiles"


STOCK_KEY_INDEX = (
    "CREATE UNIQUE INDEX ux_community_stocks_key ON community_stocks (community_entity_id, commodity, coalesce(material, ''), coalesce(world_material_id, 0))"
)


def enum_of(name: str, values: tuple[str, ...]) -> sa.Enum:
    return sa.Enum(*values, name=name, native_enum=False, create_constraint=True, length=40)


def widen(forward: bool) -> None:
    for table, column, old, new, nullable in WIDENED:
        before, after = (old, new) if forward else (new, old)
        with op.batch_alter_table(table, schema=None) as batch_op:
            batch_op.alter_column(column, existing_type=enum_of(column, before), type_=enum_of(column, after), existing_nullable=nullable)


def upgrade() -> None:
    op.create_table(
        "currencies",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("issuer_entity_id", sa.Integer(), nullable=False),
        sa.Column("item_entity_id", sa.Integer(), nullable=True),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column(
            "metal",
            sa.Enum(
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
                "dragonbone",
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
                name="metal",
                native_enum=False,
                create_constraint=True,
                length=40,
            ),
            nullable=False,
        ),
        sa.Column("purity", sa.Integer(), nullable=False),
        sa.Column("supply", sa.Integer(), nullable=False),
        sa.Column("trust", sa.Integer(), nullable=False),
        sa.Column("minted_epoch", sa.Integer(), nullable=False),
        sa.Column("debased_epoch", sa.Integer(), nullable=True),
        sa.CheckConstraint("purity BETWEEN 0 AND 100", name=op.f("ck_currencies_purity_range")),
        sa.CheckConstraint("supply >= 0", name=op.f("ck_currencies_supply_min")),
        sa.CheckConstraint("trust BETWEEN 0 AND 100", name=op.f("ck_currencies_trust_range")),
        sa.ForeignKeyConstraint(["issuer_entity_id"], ["entities.id"], name=op.f("fk_currencies_issuer_entity_id_entities"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["item_entity_id"], ["entities.id"], name=op.f("fk_currencies_item_entity_id_entities"), ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_currencies")),
    )
    with op.batch_alter_table("currencies", schema=None) as batch_op:
        batch_op.create_index(batch_op.f("ix_currencies_issuer_entity_id"), ["issuer_entity_id"], unique=False)

    op.create_table(
        "goods_flows",
        sa.Column("epoch", sa.Integer(), nullable=False),
        sa.Column("community_entity_id", sa.Integer(), nullable=False),
        sa.Column(
            "commodity",
            sa.Enum(
                "grain",
                "livestock",
                "fish",
                "fodder",
                "timber",
                "fuel",
                "bread",
                "ore",
                "stone",
                "cloth",
                "tools",
                "weapons",
                "armour",
                "mounts",
                "siege_materiel",
                "medicine",
                "luxuries",
                "incense",
                "sacred_goods",
                "magical_reagents",
                name="commodity",
                native_enum=False,
                create_constraint=True,
                length=40,
            ),
            nullable=False,
        ),
        sa.Column(
            "flow",
            sa.Enum(
                "extraction",
                "harvest",
                "production",
                "input",
                "consumption",
                "trade",
                "tribute",
                "aid",
                "loot",
                "loss",
                "siege",
                "war",
                "construction",
                "overflow",
                "decay",
                "player",
                "tool",
                "seed",
                "offering",
                name="flow",
                native_enum=False,
                create_constraint=True,
                length=40,
            ),
            nullable=False,
        ),
        sa.Column("quantity", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["community_entity_id"], ["entities.id"], name=op.f("fk_goods_flows_community_entity_id_entities"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("epoch", "community_entity_id", "commodity", "flow", name=op.f("pk_goods_flows")),
    )
    op.create_table(
        "market_prices",
        sa.Column("market_entity_id", sa.Integer(), nullable=False),
        sa.Column(
            "commodity",
            sa.Enum(
                "grain",
                "livestock",
                "fish",
                "fodder",
                "timber",
                "fuel",
                "bread",
                "ore",
                "stone",
                "cloth",
                "tools",
                "weapons",
                "armour",
                "mounts",
                "siege_materiel",
                "medicine",
                "luxuries",
                "incense",
                "sacred_goods",
                "magical_reagents",
                name="commodity",
                native_enum=False,
                create_constraint=True,
                length=40,
            ),
            nullable=False,
        ),
        sa.Column("epoch", sa.Integer(), nullable=False),
        sa.Column("price", sa.Integer(), nullable=False),
        sa.Column("supply", sa.Integer(), nullable=False),
        sa.Column("demand", sa.Integer(), nullable=False),
        sa.Column("imported", sa.Integer(), nullable=False),
        sa.Column("exported", sa.Integer(), nullable=False),
        sa.CheckConstraint("demand >= 0", name=op.f("ck_market_prices_demand_min")),
        sa.CheckConstraint("price >= 0", name=op.f("ck_market_prices_price_min")),
        sa.CheckConstraint("supply >= 0", name=op.f("ck_market_prices_supply_min")),
        sa.ForeignKeyConstraint(["market_entity_id"], ["entities.id"], name=op.f("fk_market_prices_market_entity_id_entities"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("market_entity_id", "commodity", "epoch", name=op.f("pk_market_prices")),
    )
    with op.batch_alter_table("market_prices", schema=None) as batch_op:
        batch_op.create_index("ix_market_prices_epoch", ["epoch"], unique=False)

    op.create_table(
        "production_runs",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("epoch", sa.Integer(), nullable=False),
        sa.Column("community_entity_id", sa.Integer(), nullable=False),
        sa.Column("step", sa.String(length=64), nullable=False),
        sa.Column(
            "workshop",
            sa.Enum(
                "market",
                "granary",
                "warehouse",
                "mine",
                "lumber_camp",
                "fishery",
                "charcoal_kiln",
                "forge",
                "tannery",
                "mill",
                "brewery",
                "weavery",
                "stable",
                "mason_yard",
                "shipyard",
                "siege_yard",
                "alchemist",
                "shrine_workshop",
                "mint",
                name="workshop",
                native_enum=False,
                create_constraint=True,
                length=40,
            ),
            nullable=True,
        ),
        sa.Column("resource_entity_id", sa.Integer(), nullable=True),
        sa.Column(
            "output",
            sa.Enum(
                "grain",
                "livestock",
                "fish",
                "fodder",
                "timber",
                "fuel",
                "bread",
                "ore",
                "stone",
                "cloth",
                "tools",
                "weapons",
                "armour",
                "mounts",
                "siege_materiel",
                "medicine",
                "luxuries",
                "incense",
                "sacred_goods",
                "magical_reagents",
                name="output",
                native_enum=False,
                create_constraint=True,
                length=40,
            ),
            nullable=False,
        ),
        sa.Column(
            "material",
            sa.Enum(
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
                "dragonbone",
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
                name="material",
                native_enum=False,
                create_constraint=True,
                length=40,
            ),
            nullable=True,
        ),
        sa.Column("quantity", sa.Integer(), nullable=False),
        sa.Column("quality", sa.Integer(), nullable=False),
        sa.Column("inputs", sa.JSON(), nullable=False),
        sa.Column("workers", sa.Integer(), nullable=False),
        sa.Column(
            "bottleneck",
            sa.Enum(
                "grain",
                "livestock",
                "fish",
                "fodder",
                "timber",
                "fuel",
                "bread",
                "ore",
                "stone",
                "cloth",
                "tools",
                "weapons",
                "armour",
                "mounts",
                "siege_materiel",
                "medicine",
                "luxuries",
                "incense",
                "sacred_goods",
                "magical_reagents",
                name="bottleneck",
                native_enum=False,
                create_constraint=True,
                length=40,
            ),
            nullable=True,
        ),
        sa.CheckConstraint("quality BETWEEN 0 AND 100", name=op.f("ck_production_runs_quality_range")),
        sa.CheckConstraint("quantity >= 0", name=op.f("ck_production_runs_quantity_min")),
        sa.CheckConstraint("workers >= 0", name=op.f("ck_production_runs_workers_min")),
        sa.ForeignKeyConstraint(["community_entity_id"], ["entities.id"], name=op.f("fk_production_runs_community_entity_id_entities"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["resource_entity_id"], ["entities.id"], name=op.f("fk_production_runs_resource_entity_id_entities"), ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_production_runs")),
    )
    with op.batch_alter_table("production_runs", schema=None) as batch_op:
        batch_op.create_index("ix_production_runs_epoch", ["epoch", "community_entity_id"], unique=False)

    op.create_table(
        "resource_workers",
        sa.Column("resource_entity_id", sa.Integer(), nullable=False),
        sa.Column("community_entity_id", sa.Integer(), nullable=False),
        sa.Column("workers", sa.Integer(), nullable=False),
        sa.CheckConstraint("workers >= 0", name=op.f("ck_resource_workers_workers_min")),
        sa.ForeignKeyConstraint(["community_entity_id"], ["entities.id"], name=op.f("fk_resource_workers_community_entity_id_entities"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["resource_entity_id"], ["entities.id"], name=op.f("fk_resource_workers_resource_entity_id_entities"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("resource_entity_id", "community_entity_id", name=op.f("pk_resource_workers")),
    )
    with op.batch_alter_table("resource_workers", schema=None) as batch_op:
        batch_op.create_index(batch_op.f("ix_resource_workers_community_entity_id"), ["community_entity_id"], unique=False)

    op.create_table(
        "trade_flows",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("route_entity_id", sa.Integer(), nullable=False),
        sa.Column("epoch", sa.Integer(), nullable=False),
        sa.Column(
            "commodity",
            sa.Enum(
                "grain",
                "livestock",
                "fish",
                "fodder",
                "timber",
                "fuel",
                "bread",
                "ore",
                "stone",
                "cloth",
                "tools",
                "weapons",
                "armour",
                "mounts",
                "siege_materiel",
                "medicine",
                "luxuries",
                "incense",
                "sacred_goods",
                "magical_reagents",
                name="commodity",
                native_enum=False,
                create_constraint=True,
                length=40,
            ),
            nullable=False,
        ),
        sa.Column(
            "material",
            sa.Enum(
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
                "dragonbone",
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
                name="material",
                native_enum=False,
                create_constraint=True,
                length=40,
            ),
            nullable=True,
        ),
        sa.Column("from_entity_id", sa.Integer(), nullable=False),
        sa.Column("to_entity_id", sa.Integer(), nullable=False),
        sa.Column("volume", sa.Integer(), nullable=False),
        sa.Column("lost", sa.Integer(), nullable=False),
        sa.Column("loss", sa.Enum("bandits", "sea", "beasts", "weather", name="loss", native_enum=False, create_constraint=True, length=40), nullable=True),
        sa.Column("value", sa.Integer(), nullable=False),
        sa.Column("toll_paid", sa.Integer(), nullable=False),
        sa.CheckConstraint("lost >= 0", name=op.f("ck_trade_flows_lost_min")),
        sa.CheckConstraint("toll_paid >= 0", name=op.f("ck_trade_flows_toll_paid_min")),
        sa.CheckConstraint("value >= 0", name=op.f("ck_trade_flows_value_min")),
        sa.CheckConstraint("volume >= 0", name=op.f("ck_trade_flows_volume_min")),
        sa.ForeignKeyConstraint(["from_entity_id"], ["entities.id"], name=op.f("fk_trade_flows_from_entity_id_entities"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["route_entity_id"], ["entities.id"], name=op.f("fk_trade_flows_route_entity_id_entities"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["to_entity_id"], ["entities.id"], name=op.f("fk_trade_flows_to_entity_id_entities"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_trade_flows")),
    )
    with op.batch_alter_table("trade_flows", schema=None) as batch_op:
        batch_op.create_index("ix_trade_flows_route", ["route_entity_id", "epoch"], unique=False)

    op.create_table(
        "trade_route_profiles",
        sa.Column("route_entity_id", sa.Integer(), nullable=False),
        sa.Column("first_market_id", sa.Integer(), nullable=False),
        sa.Column("second_market_id", sa.Integer(), nullable=False),
        sa.Column("mode", sa.Enum("road", "river", "sea", "caravan", "sky", name="mode", native_enum=False, create_constraint=True, length=40), nullable=False),
        sa.Column(
            "status",
            sa.Enum("forming", "open", "blockaded", "closed", "decayed", name="status", native_enum=False, create_constraint=True, length=40),
            nullable=False,
        ),
        sa.Column("length", sa.Integer(), nullable=False),
        sa.Column("controller_entity_id", sa.Integer(), nullable=True),
        sa.Column("blockaded_by_entity_id", sa.Integer(), nullable=True),
        sa.Column("founded_epoch", sa.Integer(), nullable=False),
        sa.Column("last_traffic_epoch", sa.Integer(), nullable=True),
        sa.Column("traffic_epochs", sa.Integer(), nullable=False),
        sa.Column("closed_by_player", sa.Boolean(), nullable=False),
        sa.CheckConstraint("first_market_id <> second_market_id", name=op.f("ck_trade_route_profiles_distinct_markets")),
        sa.CheckConstraint("length >= 1", name=op.f("ck_trade_route_profiles_length_min")),
        sa.CheckConstraint("traffic_epochs >= 0", name=op.f("ck_trade_route_profiles_traffic_epochs_min")),
        sa.ForeignKeyConstraint(
            ["blockaded_by_entity_id"], ["entities.id"], name=op.f("fk_trade_route_profiles_blockaded_by_entity_id_entities"), ondelete="SET NULL"
        ),
        sa.ForeignKeyConstraint(
            ["controller_entity_id"], ["entities.id"], name=op.f("fk_trade_route_profiles_controller_entity_id_entities"), ondelete="SET NULL"
        ),
        sa.ForeignKeyConstraint(["first_market_id"], ["entities.id"], name=op.f("fk_trade_route_profiles_first_market_id_entities"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["route_entity_id"], ["entities.id"], name=op.f("fk_trade_route_profiles_route_entity_id_entities"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["second_market_id"], ["entities.id"], name=op.f("fk_trade_route_profiles_second_market_id_entities"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("route_entity_id", name=op.f("pk_trade_route_profiles")),
    )
    with op.batch_alter_table("trade_route_profiles", schema=None) as batch_op:
        batch_op.create_index("ix_trade_route_markets", ["first_market_id", "second_market_id"], unique=False)

    op.create_table(
        "trade_route_regions",
        sa.Column("route_entity_id", sa.Integer(), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("region_entity_id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["region_entity_id"], ["entities.id"], name=op.f("fk_trade_route_regions_region_entity_id_entities"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["route_entity_id"], ["entities.id"], name=op.f("fk_trade_route_regions_route_entity_id_entities"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("route_entity_id", "position", name=op.f("pk_trade_route_regions")),
    )
    with op.batch_alter_table("trade_route_regions", schema=None) as batch_op:
        batch_op.create_index(batch_op.f("ix_trade_route_regions_region_entity_id"), ["region_entity_id"], unique=False)

    op.create_table(
        "trade_route_tolls",
        sa.Column("route_entity_id", sa.Integer(), nullable=False),
        sa.Column("region_entity_id", sa.Integer(), nullable=False),
        sa.Column("controller_entity_id", sa.Integer(), nullable=False),
        sa.Column("rate_pct", sa.Integer(), nullable=False),
        sa.Column("set_by_player", sa.Boolean(), nullable=False),
        sa.CheckConstraint("rate_pct BETWEEN 0 AND 100", name=op.f("ck_trade_route_tolls_rate_pct_range")),
        sa.ForeignKeyConstraint(["controller_entity_id"], ["entities.id"], name=op.f("fk_trade_route_tolls_controller_entity_id_entities"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["region_entity_id"], ["entities.id"], name=op.f("fk_trade_route_tolls_region_entity_id_entities"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["route_entity_id"], ["entities.id"], name=op.f("fk_trade_route_tolls_route_entity_id_entities"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("route_entity_id", "region_entity_id", name=op.f("pk_trade_route_tolls")),
    )
    op.create_table(
        "workshops",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("community_entity_id", sa.Integer(), nullable=False),
        sa.Column(
            "kind",
            sa.Enum(
                "market",
                "granary",
                "warehouse",
                "mine",
                "lumber_camp",
                "fishery",
                "charcoal_kiln",
                "forge",
                "tannery",
                "mill",
                "brewery",
                "weavery",
                "stable",
                "mason_yard",
                "shipyard",
                "siege_yard",
                "alchemist",
                "shrine_workshop",
                "mint",
                name="kind",
                native_enum=False,
                create_constraint=True,
                length=40,
            ),
            nullable=False,
        ),
        sa.Column("level", sa.Integer(), nullable=False),
        sa.Column("structure_entity_id", sa.Integer(), nullable=True),
        sa.Column("built_epoch", sa.Integer(), nullable=False),
        sa.Column("fleet", sa.Integer(), nullable=False),
        sa.Column("idle_epochs", sa.Integer(), nullable=False),
        sa.CheckConstraint("fleet >= 0", name=op.f("ck_workshops_fleet_min")),
        sa.CheckConstraint("idle_epochs >= 0", name=op.f("ck_workshops_idle_epochs_min")),
        sa.CheckConstraint("level >= 1", name=op.f("ck_workshops_level_min")),
        sa.ForeignKeyConstraint(["community_entity_id"], ["entities.id"], name=op.f("fk_workshops_community_entity_id_entities"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["structure_entity_id"], ["entities.id"], name=op.f("fk_workshops_structure_entity_id_entities"), ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_workshops")),
    )
    with op.batch_alter_table("workshops", schema=None) as batch_op:
        batch_op.create_index(batch_op.f("ix_workshops_community_entity_id"), ["community_entity_id"], unique=False)
        batch_op.create_index("ux_workshops_kind", ["community_entity_id", "kind"], unique=True)

    op.create_table(
        "world_materials",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("world_id", sa.Integer(), nullable=False),
        sa.Column(
            "origin",
            sa.Enum(
                "catalog", "god_remains", "dead_star", "beast", "leak_crystal", "research", name="origin", native_enum=False, create_constraint=True, length=40
            ),
            nullable=False,
        ),
        sa.Column(
            "base_kind",
            sa.Enum(
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
                "dragonbone",
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
                name="base_kind",
                native_enum=False,
                create_constraint=True,
                length=40,
            ),
            nullable=True,
        ),
        sa.Column("name", sa.String(length=200), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column(
            "family",
            sa.Enum("organic", "stone", "metal", "precious", "exotic", name="family", native_enum=False, create_constraint=True, length=40),
            nullable=False,
        ),
        sa.Column("hardness", sa.Integer(), nullable=False),
        sa.Column("toughness", sa.Integer(), nullable=False),
        sa.Column("weight", sa.Integer(), nullable=False),
        sa.Column("edge", sa.Integer(), nullable=False),
        sa.Column("conductivity", sa.Integer(), nullable=False),
        sa.Column("sanctity", sa.Integer(), nullable=False),
        sa.Column("corruption", sa.Integer(), nullable=False),
        sa.Column("rarity", sa.Integer(), nullable=False),
        sa.Column("base_value", sa.Integer(), nullable=False),
        sa.Column("decay", sa.Integer(), nullable=False),
        sa.Column(
            "branch",
            sa.Enum(
                "agriculture",
                "metallurgy",
                "seafaring",
                "writing",
                "architecture",
                "medicine",
                "magic",
                "warfare",
                "astronomy",
                "trade",
                "sky_navigation",
                "shipbuilding",
                "gate_lore",
                "pathfinding",
                "void_living",
                "immortality",
                "biomancy",
                "forbidden",
                name="branch",
                native_enum=False,
                create_constraint=True,
                length=40,
            ),
            nullable=True,
        ),
        sa.Column("level", sa.Integer(), nullable=False),
        sa.Column("source_node_id", sa.Integer(), nullable=True),
        sa.Column("deposit_entity_id", sa.Integer(), nullable=True),
        sa.Column("created_epoch", sa.Integer(), nullable=False),
        sa.CheckConstraint("base_value BETWEEN 0 AND 100", name=op.f("ck_world_materials_base_value_range")),
        sa.CheckConstraint("conductivity BETWEEN 0 AND 100", name=op.f("ck_world_materials_conductivity_range")),
        sa.CheckConstraint("corruption BETWEEN 0 AND 100", name=op.f("ck_world_materials_corruption_range")),
        sa.CheckConstraint("decay BETWEEN 0 AND 100", name=op.f("ck_world_materials_decay_range")),
        sa.CheckConstraint("edge BETWEEN 0 AND 100", name=op.f("ck_world_materials_edge_range")),
        sa.CheckConstraint("hardness BETWEEN 0 AND 100", name=op.f("ck_world_materials_hardness_range")),
        sa.CheckConstraint("level >= 0", name=op.f("ck_world_materials_level_min")),
        sa.CheckConstraint("rarity BETWEEN 0 AND 100", name=op.f("ck_world_materials_rarity_range")),
        sa.CheckConstraint("sanctity BETWEEN 0 AND 100", name=op.f("ck_world_materials_sanctity_range")),
        sa.CheckConstraint("toughness BETWEEN 0 AND 100", name=op.f("ck_world_materials_toughness_range")),
        sa.CheckConstraint("weight BETWEEN 0 AND 100", name=op.f("ck_world_materials_weight_range")),
        sa.ForeignKeyConstraint(["deposit_entity_id"], ["entities.id"], name=op.f("fk_world_materials_deposit_entity_id_entities"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["source_node_id"], ["nodes.id"], name=op.f("fk_world_materials_source_node_id_nodes"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["world_id"], ["worlds.id"], name=op.f("fk_world_materials_world_id_worlds"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_world_materials")),
    )
    with op.batch_alter_table("world_materials", schema=None) as batch_op:
        batch_op.create_index("ix_world_materials_world", ["world_id"], unique=False)
        batch_op.create_index("ux_world_materials_override", ["world_id", "base_kind"], unique=True, sqlite_where=sa.text("origin = 'catalog'"))

    op.create_table(
        "community_stocks",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("community_entity_id", sa.Integer(), nullable=False),
        sa.Column(
            "commodity",
            sa.Enum(
                "grain",
                "livestock",
                "fish",
                "fodder",
                "timber",
                "fuel",
                "bread",
                "ore",
                "stone",
                "cloth",
                "tools",
                "weapons",
                "armour",
                "mounts",
                "siege_materiel",
                "medicine",
                "luxuries",
                "incense",
                "sacred_goods",
                "magical_reagents",
                name="commodity",
                native_enum=False,
                create_constraint=True,
                length=40,
            ),
            nullable=False,
        ),
        sa.Column(
            "material",
            sa.Enum(
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
                "dragonbone",
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
                name="material",
                native_enum=False,
                create_constraint=True,
                length=40,
            ),
            nullable=True,
        ),
        sa.Column("world_material_id", sa.Integer(), nullable=True),
        sa.Column("quantity", sa.Integer(), nullable=False),
        sa.Column("quality", sa.Integer(), nullable=False),
        sa.CheckConstraint("quality BETWEEN 0 AND 100", name=op.f("ck_community_stocks_quality_range")),
        sa.CheckConstraint("quantity >= 0", name=op.f("ck_community_stocks_quantity_min")),
        sa.ForeignKeyConstraint(["community_entity_id"], ["entities.id"], name=op.f("fk_community_stocks_community_entity_id_entities"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["world_material_id"], ["world_materials.id"], name=op.f("fk_community_stocks_world_material_id_world_materials"), ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_community_stocks")),
    )
    with op.batch_alter_table("community_stocks", schema=None) as batch_op:
        batch_op.create_index("ix_community_stocks_commodity", ["commodity"], unique=False)
        batch_op.create_index(batch_op.f("ix_community_stocks_community_entity_id"), ["community_entity_id"], unique=False)
    op.execute(STOCK_KEY_INDEX)

    op.create_table(
        "loans",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("lender_entity_id", sa.Integer(), nullable=False),
        sa.Column("borrower_entity_id", sa.Integer(), nullable=False),
        sa.Column("currency_id", sa.Integer(), nullable=True),
        sa.Column("principal", sa.Integer(), nullable=False),
        sa.Column("interest_pct", sa.Integer(), nullable=False),
        sa.Column("repaid", sa.Integer(), nullable=False),
        sa.Column("issued_epoch", sa.Integer(), nullable=False),
        sa.Column("due_epoch", sa.Integer(), nullable=False),
        sa.Column(
            "status", sa.Enum("open", "repaid", "defaulted", "forgiven", name="status", native_enum=False, create_constraint=True, length=40), nullable=False
        ),
        sa.Column("purpose", sa.String(length=64), nullable=False),
        sa.Column("war_id", sa.Integer(), nullable=True),
        sa.CheckConstraint("interest_pct BETWEEN 0 AND 100", name=op.f("ck_loans_interest_pct_range")),
        sa.CheckConstraint("lender_entity_id <> borrower_entity_id", name=op.f("ck_loans_distinct_parties")),
        sa.CheckConstraint("principal >= 1", name=op.f("ck_loans_principal_min")),
        sa.CheckConstraint("repaid >= 0", name=op.f("ck_loans_repaid_min")),
        sa.ForeignKeyConstraint(["borrower_entity_id"], ["entities.id"], name=op.f("fk_loans_borrower_entity_id_entities"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["currency_id"], ["currencies.id"], name=op.f("fk_loans_currency_id_currencies"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["lender_entity_id"], ["entities.id"], name=op.f("fk_loans_lender_entity_id_entities"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["war_id"], ["wars.id"], name=op.f("fk_loans_war_id_wars"), ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_loans")),
    )
    with op.batch_alter_table("loans", schema=None) as batch_op:
        batch_op.create_index(batch_op.f("ix_loans_borrower_entity_id"), ["borrower_entity_id"], unique=False)
        batch_op.create_index(batch_op.f("ix_loans_lender_entity_id"), ["lender_entity_id"], unique=False)
        batch_op.create_index("ix_loans_status", ["status"], unique=False)

    op.create_table(
        "node_materials",
        sa.Column("node_id", sa.Integer(), nullable=False),
        sa.Column(
            "slot", sa.Enum("body", "weapons", "armour", "hull", "fabric", name="slot", native_enum=False, create_constraint=True, length=40), nullable=False
        ),
        sa.Column(
            "material",
            sa.Enum(
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
                "dragonbone",
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
                name="material",
                native_enum=False,
                create_constraint=True,
                length=40,
            ),
            nullable=True,
        ),
        sa.Column("world_material_id", sa.Integer(), nullable=True),
        sa.CheckConstraint("(material IS NULL) <> (world_material_id IS NULL)", name=op.f("ck_node_materials_one_material")),
        sa.ForeignKeyConstraint(["node_id"], ["nodes.id"], name=op.f("fk_node_materials_node_id_nodes"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["world_material_id"], ["world_materials.id"], name=op.f("fk_node_materials_world_material_id_world_materials"), ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("node_id", "slot", name=op.f("pk_node_materials")),
    )
    op.create_table(
        "resource_profiles",
        sa.Column("resource_entity_id", sa.Integer(), nullable=False),
        sa.Column(
            "commodity",
            sa.Enum(
                "grain",
                "livestock",
                "fish",
                "fodder",
                "timber",
                "fuel",
                "bread",
                "ore",
                "stone",
                "cloth",
                "tools",
                "weapons",
                "armour",
                "mounts",
                "siege_materiel",
                "medicine",
                "luxuries",
                "incense",
                "sacred_goods",
                "magical_reagents",
                name="commodity",
                native_enum=False,
                create_constraint=True,
                length=40,
            ),
            nullable=False,
        ),
        sa.Column(
            "material",
            sa.Enum(
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
                "dragonbone",
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
                name="material",
                native_enum=False,
                create_constraint=True,
                length=40,
            ),
            nullable=True,
        ),
        sa.Column("world_material_id", sa.Integer(), nullable=True),
        sa.Column("reserve", sa.Integer(), nullable=False),
        sa.Column("initial_reserve", sa.Integer(), nullable=False),
        sa.Column("richness", sa.Integer(), nullable=False),
        sa.Column("regeneration", sa.Integer(), nullable=False),
        sa.Column("extraction_difficulty", sa.Integer(), nullable=False),
        sa.Column(
            "required_branch",
            sa.Enum(
                "agriculture",
                "metallurgy",
                "seafaring",
                "writing",
                "architecture",
                "medicine",
                "magic",
                "warfare",
                "astronomy",
                "trade",
                "sky_navigation",
                "shipbuilding",
                "gate_lore",
                "pathfinding",
                "void_living",
                "immortality",
                "biomancy",
                "forbidden",
                name="required_branch",
                native_enum=False,
                create_constraint=True,
                length=40,
            ),
            nullable=True,
        ),
        sa.Column("required_level", sa.Integer(), nullable=False),
        sa.Column("quality", sa.Integer(), nullable=False),
        sa.Column(
            "byproduct_material",
            sa.Enum(
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
                "dragonbone",
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
                name="byproduct_material",
                native_enum=False,
                create_constraint=True,
                length=40,
            ),
            nullable=True,
        ),
        sa.Column("byproduct_pct", sa.Integer(), nullable=False),
        sa.Column("revealed", sa.Boolean(), nullable=False),
        sa.Column("sealed_until_epoch", sa.Integer(), nullable=True),
        sa.Column("last_output", sa.Integer(), nullable=False),
        sa.CheckConstraint("byproduct_pct BETWEEN 0 AND 100", name=op.f("ck_resource_profiles_byproduct_pct_range")),
        sa.CheckConstraint("extraction_difficulty BETWEEN 0 AND 100", name=op.f("ck_resource_profiles_extraction_difficulty_range")),
        sa.CheckConstraint("initial_reserve >= 1", name=op.f("ck_resource_profiles_initial_reserve_min")),
        sa.CheckConstraint("last_output >= 0", name=op.f("ck_resource_profiles_last_output_min")),
        sa.CheckConstraint("quality BETWEEN 0 AND 100", name=op.f("ck_resource_profiles_quality_range")),
        sa.CheckConstraint("regeneration >= 0", name=op.f("ck_resource_profiles_regeneration_min")),
        sa.CheckConstraint("required_level >= 0", name=op.f("ck_resource_profiles_required_level_min")),
        sa.CheckConstraint("reserve <= initial_reserve * 4", name=op.f("ck_resource_profiles_reserve_bounded")),
        sa.CheckConstraint("reserve >= 0", name=op.f("ck_resource_profiles_reserve_min")),
        sa.CheckConstraint("richness BETWEEN 0 AND 100", name=op.f("ck_resource_profiles_richness_range")),
        sa.ForeignKeyConstraint(["resource_entity_id"], ["entities.id"], name=op.f("fk_resource_profiles_resource_entity_id_entities"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["world_material_id"], ["world_materials.id"], name=op.f("fk_resource_profiles_world_material_id_world_materials"), ondelete="SET NULL"
        ),
        sa.PrimaryKeyConstraint("resource_entity_id", name=op.f("pk_resource_profiles")),
    )
    op.execute(profiles_from_commodities())
    with op.batch_alter_table("resource_commodities", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_resource_commodities_commodity"))

    op.drop_table("resource_commodities")
    with op.batch_alter_table("bonds", schema=None) as batch_op:
        batch_op.add_column(sa.Column("debt_currency_id", sa.Integer(), nullable=True))
        batch_op.create_foreign_key(batch_op.f("fk_bonds_debt_currency_id_currencies"), "currencies", ["debt_currency_id"], ["id"], ondelete="SET NULL")

    with op.batch_alter_table("community_societies", schema=None) as batch_op:
        batch_op.add_column(sa.Column("currency_id", sa.Integer(), nullable=True))
        batch_op.create_foreign_key(batch_op.f("fk_community_societies_currency_id_currencies"), "currencies", ["currency_id"], ["id"], ondelete="SET NULL")

    with op.batch_alter_table("resource_mechanics", schema=None) as batch_op:
        batch_op.add_column(sa.Column("magnitude", sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column("epochs", sa.Integer(), nullable=True))
    widen(True)


def downgrade() -> None:
    widen(False)
    with op.batch_alter_table("resource_mechanics", schema=None) as batch_op:
        batch_op.drop_column("epochs")
        batch_op.drop_column("magnitude")

    with op.batch_alter_table("community_societies", schema=None) as batch_op:
        batch_op.drop_constraint(batch_op.f("fk_community_societies_currency_id_currencies"), type_="foreignkey")
        batch_op.drop_column("currency_id")

    with op.batch_alter_table("bonds", schema=None) as batch_op:
        batch_op.drop_constraint(batch_op.f("fk_bonds_debt_currency_id_currencies"), type_="foreignkey")
        batch_op.drop_column("debt_currency_id")

    op.create_table(
        "resource_commodities",
        sa.Column("resource_entity_id", sa.INTEGER(), nullable=False),
        sa.Column("commodity", sa.VARCHAR(length=40), nullable=False),
        sa.CheckConstraint("commodity IN ('food', 'ore', 'goods')", name=op.f("ck_resource_commodities_commodity")),
        sa.ForeignKeyConstraint(["resource_entity_id"], ["entities.id"], name=op.f("fk_resource_commodities_resource_entity_id_entities"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("resource_entity_id", name=op.f("pk_resource_commodities")),
    )
    with op.batch_alter_table("resource_commodities", schema=None) as batch_op:
        batch_op.create_index(batch_op.f("ix_resource_commodities_commodity"), ["commodity"], unique=False)
    op.execute(commodities_from_profiles())

    op.drop_table("resource_profiles")
    op.drop_table("node_materials")
    with op.batch_alter_table("loans", schema=None) as batch_op:
        batch_op.drop_index("ix_loans_status")
        batch_op.drop_index(batch_op.f("ix_loans_lender_entity_id"))
        batch_op.drop_index(batch_op.f("ix_loans_borrower_entity_id"))

    op.drop_table("loans")
    op.execute("DROP INDEX IF EXISTS ux_community_stocks_key")
    with op.batch_alter_table("community_stocks", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_community_stocks_community_entity_id"))
        batch_op.drop_index("ix_community_stocks_commodity")

    op.drop_table("community_stocks")
    with op.batch_alter_table("world_materials", schema=None) as batch_op:
        batch_op.drop_index("ux_world_materials_override", sqlite_where=sa.text("origin = 'catalog'"))
        batch_op.drop_index("ix_world_materials_world")

    op.drop_table("world_materials")
    with op.batch_alter_table("workshops", schema=None) as batch_op:
        batch_op.drop_index("ux_workshops_kind")
        batch_op.drop_index(batch_op.f("ix_workshops_community_entity_id"))

    op.drop_table("workshops")
    op.drop_table("trade_route_tolls")
    with op.batch_alter_table("trade_route_regions", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_trade_route_regions_region_entity_id"))

    op.drop_table("trade_route_regions")
    with op.batch_alter_table("trade_route_profiles", schema=None) as batch_op:
        batch_op.drop_index("ix_trade_route_markets")

    op.drop_table("trade_route_profiles")
    with op.batch_alter_table("trade_flows", schema=None) as batch_op:
        batch_op.drop_index("ix_trade_flows_route")

    op.drop_table("trade_flows")
    with op.batch_alter_table("resource_workers", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_resource_workers_community_entity_id"))

    op.drop_table("resource_workers")
    with op.batch_alter_table("production_runs", schema=None) as batch_op:
        batch_op.drop_index("ix_production_runs_epoch")

    op.drop_table("production_runs")
    with op.batch_alter_table("market_prices", schema=None) as batch_op:
        batch_op.drop_index("ix_market_prices_epoch")

    op.drop_table("market_prices")
    op.drop_table("goods_flows")
    with op.batch_alter_table("currencies", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_currencies_issuer_entity_id"))

    op.drop_table("currencies")
