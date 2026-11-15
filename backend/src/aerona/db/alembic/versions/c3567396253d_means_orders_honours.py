import sqlalchemy as sa
from alembic import op

revision = "c3567396253d"
down_revision = "43f37860bb0b"
branch_labels = None
depends_on = None


MATERIALS_BEFORE = (
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
)
MATERIALS_AFTER = (*MATERIALS_BEFORE, "mud_brick", "fired_brick", "dressed_stone", "rubble", "lime_mortar", "hydraulic_concrete", "thatch", "tile")
FACTIONS_BEFORE = (
    "merchant_guild",
    "craft_guild",
    "priesthood",
    "warrior_order",
    "noble_council",
    "peasant_league",
    "rebels",
    "bandits",
    "pirates",
    "assassins",
    "scholars_academy",
    "secret_society",
    "mercenary_company",
    "interworld_federation",
    "wandering_market",
    "void_pirates",
    "social_circle",
    "mage_order",
    "estate",
    "party",
    "movement",
    "chartered_company",
    "holy_order",
    "crime_family",
    "thieves_guild",
    "smuggling_ring",
    "pirate_confederacy",
    "art_movement",
    "club",
    "league",
    "workers_union",
    "engineers_society",
    "financiers",
)
FACTIONS_AFTER = (*FACTIONS_BEFORE, "veterans")
MATERIAL_COLUMNS = (
    ("creature_anatomy", "hoards", True),
    ("constructs", "material", False),
    ("currencies", "metal", False),
    ("place_secrets", "material", True),
    ("production_runs", "material", True),
    ("structure_designs", "material", True),
    ("trade_flows", "material", True),
    ("world_materials", "base_kind", True),
    ("community_stocks", "material", True),
    ("equipment_models", "material", True),
    ("node_materials", "material", True),
    ("resource_profiles", "material", True),
    ("resource_profiles", "byproduct_material", True),
    ("species_yields", "material", True),
    ("structure_design_sections", "material", True),
    ("structure_sections", "material", True),
    ("prostheses", "material", False),
)
STOCK_KEY_INDEX = (
    "CREATE UNIQUE INDEX ux_community_stocks_key ON community_stocks (community_entity_id, commodity, coalesce(material, ''), coalesce(world_material_id, 0))"
)


def enum_of(name: str, values: tuple[str, ...]) -> sa.Enum:
    return sa.Enum(*values, name=name, native_enum=False, create_constraint=True, length=40)


def widen(forward: bool) -> None:
    before, after = (MATERIALS_BEFORE, MATERIALS_AFTER) if forward else (MATERIALS_AFTER, MATERIALS_BEFORE)
    op.execute("DROP INDEX IF EXISTS ux_community_stocks_key")
    for table, column, nullable in MATERIAL_COLUMNS:
        with op.batch_alter_table(table, schema=None) as batch_op:
            batch_op.alter_column(column, existing_type=enum_of(column, before), type_=enum_of(column, after), existing_nullable=nullable)
    op.execute(STOCK_KEY_INDEX)
    kinds, wider = (FACTIONS_BEFORE, FACTIONS_AFTER) if forward else (FACTIONS_AFTER, FACTIONS_BEFORE)
    with op.batch_alter_table("faction_profiles", schema=None) as batch_op:
        batch_op.alter_column("kind", existing_type=enum_of("kind", kinds), type_=enum_of("kind", wider), existing_nullable=False)


def upgrade() -> None:
    op.create_table(
        "economic_order_kinds",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column(
            "ownership",
            sa.Enum(
                "household",
                "kin_group",
                "community",
                "temple",
                "ruler",
                "state",
                "private",
                "cooperative",
                "company",
                "common",
                "none",
                name="ownership",
                native_enum=False,
                create_constraint=True,
                length=40,
            ),
            nullable=False,
        ),
        sa.Column(
            "allocation",
            sa.Enum(
                "market",
                "redistribution",
                "command",
                "obligation",
                "gift",
                "need",
                "abundance",
                name="allocation",
                native_enum=False,
                create_constraint=True,
                length=40,
            ),
            nullable=False,
        ),
        sa.Column(
            "labour",
            sa.Enum(
                "free",
                "kin",
                "corvee",
                "serf",
                "bound",
                "enslaved",
                "conscripted",
                "cooperative",
                "made",
                name="labour",
                native_enum=False,
                create_constraint=True,
                length=40,
            ),
            nullable=False,
        ),
        sa.Column(
            "distribution",
            sa.Enum(
                "by_holding",
                "by_office",
                "by_need",
                "by_work",
                "by_share",
                "equal",
                "by_prestige",
                name="distribution",
                native_enum=False,
                create_constraint=True,
                length=40,
            ),
            nullable=False,
        ),
        sa.Column("built_in", sa.Boolean(), nullable=False),
        sa.Column("locked", sa.JSON(), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_economic_order_kinds")),
    )
    op.create_table(
        "savings",
        sa.Column("household_id", sa.Integer(), nullable=False),
        sa.Column("share_pct", sa.Integer(), nullable=False),
        sa.Column("form", sa.Enum("hoard", "deposit", "investment", name="form", native_enum=False, create_constraint=True, length=40), nullable=False),
        sa.Column("saved", sa.Integer(), nullable=False),
        sa.Column("updated_epoch", sa.Integer(), nullable=False),
        sa.Column("locked", sa.JSON(), nullable=False),
        sa.CheckConstraint("saved >= 0", name=op.f("ck_savings_saved_min")),
        sa.CheckConstraint("share_pct BETWEEN 0 AND 100", name=op.f("ck_savings_share_pct_range")),
        sa.ForeignKeyConstraint(["household_id"], ["households.id"], name=op.f("fk_savings_household_id_households"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("household_id", name=op.f("pk_savings")),
    )
    op.create_table(
        "bills_of_exchange",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("drawer_node_id", sa.Integer(), nullable=False),
        sa.Column("payee_node_id", sa.Integer(), nullable=False),
        sa.Column("from_entity_id", sa.Integer(), nullable=False),
        sa.Column("to_entity_id", sa.Integer(), nullable=False),
        sa.Column("amount", sa.Integer(), nullable=False),
        sa.Column("issued_epoch", sa.Integer(), nullable=False),
        sa.Column("settled", sa.Boolean(), nullable=False),
        sa.Column("locked", sa.JSON(), nullable=False),
        sa.CheckConstraint("amount >= 0", name=op.f("ck_bills_of_exchange_amount_min")),
        sa.CheckConstraint("issued_epoch >= 0", name=op.f("ck_bills_of_exchange_issued_epoch_min")),
        sa.ForeignKeyConstraint(["drawer_node_id"], ["nodes.id"], name=op.f("fk_bills_of_exchange_drawer_node_id_nodes"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["from_entity_id"], ["entities.id"], name=op.f("fk_bills_of_exchange_from_entity_id_entities"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["payee_node_id"], ["nodes.id"], name=op.f("fk_bills_of_exchange_payee_node_id_nodes"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["to_entity_id"], ["entities.id"], name=op.f("fk_bills_of_exchange_to_entity_id_entities"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_bills_of_exchange")),
    )
    op.create_table(
        "chain_holdings",
        sa.Column("holder_entity_id", sa.Integer(), nullable=False),
        sa.Column("town_entity_id", sa.Integer(), nullable=False),
        sa.Column(
            "product",
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
                "meat",
                "milk",
                "cheese",
                "fruit",
                "tubers",
                "coal",
                "peat",
                "dung",
                "fibre",
                "dye",
                "herbs",
                "brew_base",
                "poison",
                "eggs",
                "wool",
                name="product",
                native_enum=False,
                create_constraint=True,
                length=40,
            ),
            nullable=False,
        ),
        sa.Column("share_pct", sa.Integer(), nullable=False),
        sa.Column("since_epoch", sa.Integer(), nullable=False),
        sa.Column("locked", sa.JSON(), nullable=False),
        sa.CheckConstraint("share_pct BETWEEN 0 AND 100", name=op.f("ck_chain_holdings_share_pct_range")),
        sa.CheckConstraint("since_epoch >= 0", name=op.f("ck_chain_holdings_since_epoch_min")),
        sa.ForeignKeyConstraint(["holder_entity_id"], ["entities.id"], name=op.f("fk_chain_holdings_holder_entity_id_entities"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["town_entity_id"], ["entities.id"], name=op.f("fk_chain_holdings_town_entity_id_entities"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("holder_entity_id", "town_entity_id", "product", name=op.f("pk_chain_holdings")),
    )
    op.create_table(
        "container_stocks",
        sa.Column("community_entity_id", sa.Integer(), nullable=False),
        sa.Column(
            "kind",
            sa.Enum("amphora", "barrel", "sack", "crate", "jar", "chest", name="kind", native_enum=False, create_constraint=True, length=40),
            nullable=False,
        ),
        sa.Column("count", sa.Integer(), nullable=False),
        sa.Column("broken", sa.Integer(), nullable=False),
        sa.Column("locked", sa.JSON(), nullable=False),
        sa.CheckConstraint("broken >= 0", name=op.f("ck_container_stocks_broken_min")),
        sa.CheckConstraint("count >= 0", name=op.f("ck_container_stocks_count_min")),
        sa.ForeignKeyConstraint(["community_entity_id"], ["entities.id"], name=op.f("fk_container_stocks_community_entity_id_entities"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("community_entity_id", "kind", name=op.f("pk_container_stocks")),
    )
    with op.batch_alter_table("container_stocks", schema=None) as batch_op:
        batch_op.create_index("ix_container_stocks_kind", ["kind"], unique=False)

    op.create_table(
        "economic_orders",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("polity_entity_id", sa.Integer(), nullable=False),
        sa.Column(
            "sector",
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
                "meat",
                "milk",
                "cheese",
                "fruit",
                "tubers",
                "coal",
                "peat",
                "dung",
                "fibre",
                "dye",
                "herbs",
                "brew_base",
                "poison",
                "eggs",
                "wool",
                name="sector",
                native_enum=False,
                create_constraint=True,
                length=40,
            ),
            nullable=True,
        ),
        sa.Column(
            "ownership",
            sa.Enum(
                "household",
                "kin_group",
                "community",
                "temple",
                "ruler",
                "state",
                "private",
                "cooperative",
                "company",
                "common",
                "none",
                name="ownership",
                native_enum=False,
                create_constraint=True,
                length=40,
            ),
            nullable=False,
        ),
        sa.Column(
            "allocation",
            sa.Enum(
                "market",
                "redistribution",
                "command",
                "obligation",
                "gift",
                "need",
                "abundance",
                name="allocation",
                native_enum=False,
                create_constraint=True,
                length=40,
            ),
            nullable=False,
        ),
        sa.Column(
            "labour",
            sa.Enum(
                "free",
                "kin",
                "corvee",
                "serf",
                "bound",
                "enslaved",
                "conscripted",
                "cooperative",
                "made",
                name="labour",
                native_enum=False,
                create_constraint=True,
                length=40,
            ),
            nullable=False,
        ),
        sa.Column(
            "distribution",
            sa.Enum(
                "by_holding",
                "by_office",
                "by_need",
                "by_work",
                "by_share",
                "equal",
                "by_prestige",
                name="distribution",
                native_enum=False,
                create_constraint=True,
                length=40,
            ),
            nullable=False,
        ),
        sa.Column("planning_capacity", sa.Integer(), nullable=False),
        sa.Column("kind_id", sa.Integer(), nullable=True),
        sa.Column("since_epoch", sa.Integer(), nullable=False),
        sa.Column("locked", sa.JSON(), nullable=False),
        sa.CheckConstraint("planning_capacity BETWEEN 0 AND 100", name=op.f("ck_economic_orders_planning_capacity_range")),
        sa.CheckConstraint("since_epoch >= 0", name=op.f("ck_economic_orders_since_epoch_min")),
        sa.ForeignKeyConstraint(["kind_id"], ["economic_order_kinds.id"], name=op.f("fk_economic_orders_kind_id_economic_order_kinds"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["polity_entity_id"], ["entities.id"], name=op.f("fk_economic_orders_polity_entity_id_entities"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_economic_orders")),
    )
    with op.batch_alter_table("economic_orders", schema=None) as batch_op:
        batch_op.create_index("ix_economic_orders_polity", ["polity_entity_id"], unique=False)

    op.create_table(
        "hoards",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("holder_node_id", sa.Integer(), nullable=True),
        sa.Column("place_entity_id", sa.Integer(), nullable=False),
        sa.Column("amount", sa.Integer(), nullable=False),
        sa.Column("state", sa.Enum("hidden", "lost", "found", "spent", name="state", native_enum=False, create_constraint=True, length=40), nullable=False),
        sa.Column("hidden_epoch", sa.Integer(), nullable=False),
        sa.Column("found_by_node_id", sa.Integer(), nullable=True),
        sa.Column("found_epoch", sa.Integer(), nullable=True),
        sa.Column("locked", sa.JSON(), nullable=False),
        sa.CheckConstraint("amount >= 0", name=op.f("ck_hoards_amount_min")),
        sa.CheckConstraint("hidden_epoch >= 0", name=op.f("ck_hoards_hidden_epoch_min")),
        sa.ForeignKeyConstraint(["found_by_node_id"], ["nodes.id"], name=op.f("fk_hoards_found_by_node_id_nodes"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["holder_node_id"], ["nodes.id"], name=op.f("fk_hoards_holder_node_id_nodes"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["place_entity_id"], ["entities.id"], name=op.f("fk_hoards_place_entity_id_entities"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_hoards")),
    )
    with op.batch_alter_table("hoards", schema=None) as batch_op:
        batch_op.create_index("ix_hoards_place", ["place_entity_id"], unique=False)

    op.create_table(
        "navigation_kits",
        sa.Column("holder_entity_id", sa.Integer(), nullable=False),
        sa.Column(
            "aid", sa.Enum("compass", "astrolabe", "log_line", "charts", name="aid", native_enum=False, create_constraint=True, length=40), nullable=False
        ),
        sa.Column("quality", sa.Integer(), nullable=False),
        sa.Column("since_epoch", sa.Integer(), nullable=False),
        sa.Column("locked", sa.JSON(), nullable=False),
        sa.CheckConstraint("quality BETWEEN 0 AND 100", name=op.f("ck_navigation_kits_quality_range")),
        sa.CheckConstraint("since_epoch >= 0", name=op.f("ck_navigation_kits_since_epoch_min")),
        sa.ForeignKeyConstraint(["holder_entity_id"], ["entities.id"], name=op.f("fk_navigation_kits_holder_entity_id_entities"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("holder_entity_id", "aid", name=op.f("pk_navigation_kits")),
    )
    op.create_table(
        "order_transitions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("polity_entity_id", sa.Integer(), nullable=False),
        sa.Column(
            "sector",
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
                "meat",
                "milk",
                "cheese",
                "fruit",
                "tubers",
                "coal",
                "peat",
                "dung",
                "fibre",
                "dye",
                "herbs",
                "brew_base",
                "poison",
                "eggs",
                "wool",
                name="sector",
                native_enum=False,
                create_constraint=True,
                length=40,
            ),
            nullable=True,
        ),
        sa.Column(
            "kind",
            sa.Enum(
                "collectivisation",
                "nationalisation",
                "privatisation",
                "land_reform",
                "enclosure",
                "emancipation",
                "decollectivisation",
                "restoration_of_holdings",
                name="kind",
                native_enum=False,
                create_constraint=True,
                length=40,
            ),
            nullable=False,
        ),
        sa.Column("from_axes", sa.JSON(), nullable=False),
        sa.Column("to_axes", sa.JSON(), nullable=False),
        sa.Column(
            "stage", sa.Enum("proclaimed", "transferring", "done", "failed", name="stage", native_enum=False, create_constraint=True, length=40), nullable=False
        ),
        sa.Column(
            "compensation", sa.Enum("none", "partial", "full", name="compensation", native_enum=False, create_constraint=True, length=40), nullable=False
        ),
        sa.Column("resistance", sa.Integer(), nullable=False),
        sa.Column("transferred", sa.Integer(), nullable=False),
        sa.Column("started_epoch", sa.Integer(), nullable=False),
        sa.Column("ended_epoch", sa.Integer(), nullable=True),
        sa.Column("locked", sa.JSON(), nullable=False),
        sa.CheckConstraint("resistance BETWEEN 0 AND 100", name=op.f("ck_order_transitions_resistance_range")),
        sa.CheckConstraint("started_epoch >= 0", name=op.f("ck_order_transitions_started_epoch_min")),
        sa.ForeignKeyConstraint(["polity_entity_id"], ["entities.id"], name=op.f("fk_order_transitions_polity_entity_id_entities"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_order_transitions")),
    )
    with op.batch_alter_table("order_transitions", schema=None) as batch_op:
        batch_op.create_index("ix_order_transitions_polity", ["polity_entity_id"], unique=False)

    op.create_table(
        "putting_out",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("merchant_entity_id", sa.Integer(), nullable=False),
        sa.Column("town_entity_id", sa.Integer(), nullable=False),
        sa.Column(
            "raw",
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
                "meat",
                "milk",
                "cheese",
                "fruit",
                "tubers",
                "coal",
                "peat",
                "dung",
                "fibre",
                "dye",
                "herbs",
                "brew_base",
                "poison",
                "eggs",
                "wool",
                name="raw",
                native_enum=False,
                create_constraint=True,
                length=40,
            ),
            nullable=False,
        ),
        sa.Column(
            "product",
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
                "meat",
                "milk",
                "cheese",
                "fruit",
                "tubers",
                "coal",
                "peat",
                "dung",
                "fibre",
                "dye",
                "herbs",
                "brew_base",
                "poison",
                "eggs",
                "wool",
                name="product",
                native_enum=False,
                create_constraint=True,
                length=40,
            ),
            nullable=False,
        ),
        sa.Column("volume", sa.Integer(), nullable=False),
        sa.Column("active", sa.Boolean(), nullable=False),
        sa.Column("since_epoch", sa.Integer(), nullable=False),
        sa.Column("locked", sa.JSON(), nullable=False),
        sa.CheckConstraint("since_epoch >= 0", name=op.f("ck_putting_out_since_epoch_min")),
        sa.CheckConstraint("volume >= 0", name=op.f("ck_putting_out_volume_min")),
        sa.ForeignKeyConstraint(["merchant_entity_id"], ["entities.id"], name=op.f("fk_putting_out_merchant_entity_id_entities"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["town_entity_id"], ["entities.id"], name=op.f("fk_putting_out_town_entity_id_entities"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_putting_out")),
    )
    with op.batch_alter_table("putting_out", schema=None) as batch_op:
        batch_op.create_index("ix_putting_out_town", ["town_entity_id"], unique=False)

    op.create_table(
        "securities",
        sa.Column("holder_entity_id", sa.Integer(), nullable=False),
        sa.Column(
            "lock",
            sa.Enum("bar", "warded", "tumbler", "combination", "warded_seal", name="lock", native_enum=False, create_constraint=True, length=40),
            nullable=True,
        ),
        sa.Column("lock_quality", sa.Integer(), nullable=False),
        sa.Column("sealed", sa.Boolean(), nullable=False),
        sa.Column("guards", sa.Integer(), nullable=False),
        sa.Column("traps", sa.Boolean(), nullable=False),
        sa.Column("thwarted", sa.Integer(), nullable=False),
        sa.Column("since_epoch", sa.Integer(), nullable=False),
        sa.Column("locked", sa.JSON(), nullable=False),
        sa.CheckConstraint("guards >= 0", name=op.f("ck_securities_guards_min")),
        sa.CheckConstraint("lock_quality BETWEEN 0 AND 100", name=op.f("ck_securities_lock_quality_range")),
        sa.CheckConstraint("since_epoch >= 0", name=op.f("ck_securities_since_epoch_min")),
        sa.ForeignKeyConstraint(["holder_entity_id"], ["entities.id"], name=op.f("fk_securities_holder_entity_id_entities"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("holder_entity_id", name=op.f("pk_securities")),
    )
    op.create_table(
        "tourist_flows",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("origin_entity_id", sa.Integer(), nullable=False),
        sa.Column("sight_entity_id", sa.Integer(), nullable=False),
        sa.Column(
            "sight",
            sa.Enum("wonder", "baths", "sacred", "battlefield", "city", name="sight", native_enum=False, create_constraint=True, length=40),
            nullable=False,
        ),
        sa.Column("visitors", sa.Integer(), nullable=False),
        sa.Column("income", sa.Integer(), nullable=False),
        sa.Column("epoch", sa.Integer(), nullable=False),
        sa.Column("locked", sa.JSON(), nullable=False),
        sa.CheckConstraint("income >= 0", name=op.f("ck_tourist_flows_income_min")),
        sa.CheckConstraint("visitors >= 0", name=op.f("ck_tourist_flows_visitors_min")),
        sa.ForeignKeyConstraint(["origin_entity_id"], ["entities.id"], name=op.f("fk_tourist_flows_origin_entity_id_entities"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["sight_entity_id"], ["entities.id"], name=op.f("fk_tourist_flows_sight_entity_id_entities"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_tourist_flows")),
    )
    with op.batch_alter_table("tourist_flows", schema=None) as batch_op:
        batch_op.create_index("ix_tourist_flows_sight", ["sight_entity_id"], unique=False)

    op.create_table(
        "veteran_grants",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("polity_entity_id", sa.Integer(), nullable=False),
        sa.Column("kind", sa.Enum("land", "pension", "none", name="kind", native_enum=False, create_constraint=True, length=40), nullable=False),
        sa.Column("veterans", sa.Integer(), nullable=False),
        sa.Column("settlement_entity_id", sa.Integer(), nullable=True),
        sa.Column("war_entity_id", sa.Integer(), nullable=True),
        sa.Column("epoch", sa.Integer(), nullable=False),
        sa.Column("locked", sa.JSON(), nullable=False),
        sa.CheckConstraint("epoch >= 0", name=op.f("ck_veteran_grants_epoch_min")),
        sa.CheckConstraint("veterans >= 0", name=op.f("ck_veteran_grants_veterans_min")),
        sa.ForeignKeyConstraint(["polity_entity_id"], ["entities.id"], name=op.f("fk_veteran_grants_polity_entity_id_entities"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["settlement_entity_id"], ["entities.id"], name=op.f("fk_veteran_grants_settlement_entity_id_entities"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["war_entity_id"], ["entities.id"], name=op.f("fk_veteran_grants_war_entity_id_entities"), ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_veteran_grants")),
    )
    with op.batch_alter_table("veteran_grants", schema=None) as batch_op:
        batch_op.create_index("ix_veteran_grants_polity", ["polity_entity_id"], unique=False)

    op.create_table(
        "water_lifts",
        sa.Column("settlement_entity_id", sa.Integer(), nullable=False),
        sa.Column(
            "device",
            sa.Enum("shaduf", "noria", "screw", "chain_pump", "steam_pump", name="device", native_enum=False, create_constraint=True, length=40),
            nullable=False,
        ),
        sa.Column("count", sa.Integer(), nullable=False),
        sa.Column("since_epoch", sa.Integer(), nullable=False),
        sa.Column("locked", sa.JSON(), nullable=False),
        sa.CheckConstraint("count >= 0", name=op.f("ck_water_lifts_count_min")),
        sa.CheckConstraint("since_epoch >= 0", name=op.f("ck_water_lifts_since_epoch_min")),
        sa.ForeignKeyConstraint(["settlement_entity_id"], ["entities.id"], name=op.f("fk_water_lifts_settlement_entity_id_entities"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("settlement_entity_id", "device", name=op.f("pk_water_lifts")),
    )
    op.create_table(
        "writing_customs",
        sa.Column("people_entity_id", sa.Integer(), nullable=False),
        sa.Column(
            "medium",
            sa.Enum(
                "clay_tablet",
                "wax_tablet",
                "bark",
                "palm_leaf",
                "papyrus",
                "parchment",
                "paper",
                "metal_plate",
                "stone",
                "knotted_cord",
                name="medium",
                native_enum=False,
                create_constraint=True,
                length=40,
            ),
            nullable=False,
        ),
        sa.Column("since_epoch", sa.Integer(), nullable=False),
        sa.Column("locked", sa.JSON(), nullable=False),
        sa.CheckConstraint("since_epoch >= 0", name=op.f("ck_writing_customs_since_epoch_min")),
        sa.ForeignKeyConstraint(["people_entity_id"], ["entities.id"], name=op.f("fk_writing_customs_people_entity_id_entities"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("people_entity_id", name=op.f("pk_writing_customs")),
    )
    op.create_table(
        "written_works",
        sa.Column("work_entity_id", sa.Integer(), nullable=False),
        sa.Column(
            "medium",
            sa.Enum(
                "clay_tablet",
                "wax_tablet",
                "bark",
                "palm_leaf",
                "papyrus",
                "parchment",
                "paper",
                "metal_plate",
                "stone",
                "knotted_cord",
                name="medium",
                native_enum=False,
                create_constraint=True,
                length=40,
            ),
            nullable=False,
        ),
        sa.Column("condition", sa.Integer(), nullable=False),
        sa.Column("copies", sa.Integer(), nullable=False),
        sa.Column("written_epoch", sa.Integer(), nullable=False),
        sa.Column("locked", sa.JSON(), nullable=False),
        sa.CheckConstraint("condition BETWEEN 0 AND 100", name=op.f("ck_written_works_condition_range")),
        sa.CheckConstraint("copies >= 0", name=op.f("ck_written_works_copies_min")),
        sa.CheckConstraint("written_epoch >= 0", name=op.f("ck_written_works_written_epoch_min")),
        sa.ForeignKeyConstraint(["work_entity_id"], ["entities.id"], name=op.f("fk_written_works_work_entity_id_entities"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("work_entity_id", name=op.f("pk_written_works")),
    )
    op.create_table(
        "exchange_rates",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("base_currency_id", sa.Integer(), nullable=False),
        sa.Column("quote_currency_id", sa.Integer(), nullable=False),
        sa.Column("market_entity_id", sa.Integer(), nullable=True),
        sa.Column("rate", sa.Integer(), nullable=False),
        sa.Column("spread_pct", sa.Integer(), nullable=False),
        sa.Column("changer_node_id", sa.Integer(), nullable=True),
        sa.Column("convertible", sa.Boolean(), nullable=False),
        sa.Column("volume", sa.Integer(), nullable=False),
        sa.Column("updated_epoch", sa.Integer(), nullable=False),
        sa.Column("locked", sa.JSON(), nullable=False),
        sa.CheckConstraint("rate >= 1", name=op.f("ck_exchange_rates_rate_min")),
        sa.CheckConstraint("spread_pct BETWEEN 0 AND 100", name=op.f("ck_exchange_rates_spread_pct_range")),
        sa.CheckConstraint("volume >= 0", name=op.f("ck_exchange_rates_volume_min")),
        sa.ForeignKeyConstraint(["base_currency_id"], ["currencies.id"], name=op.f("fk_exchange_rates_base_currency_id_currencies"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["changer_node_id"], ["nodes.id"], name=op.f("fk_exchange_rates_changer_node_id_nodes"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["market_entity_id"], ["entities.id"], name=op.f("fk_exchange_rates_market_entity_id_entities"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["quote_currency_id"], ["currencies.id"], name=op.f("fk_exchange_rates_quote_currency_id_currencies"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_exchange_rates")),
    )
    with op.batch_alter_table("exchange_rates", schema=None) as batch_op:
        batch_op.create_index("ix_exchange_rates_pair", ["base_currency_id", "quote_currency_id"], unique=False)

    op.create_table(
        "named_units",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("unit_id", sa.Integer(), nullable=True),
        sa.Column("owner_entity_id", sa.Integer(), nullable=True),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("nickname", sa.String(length=200), nullable=True),
        sa.Column("raised_from_entity_id", sa.Integer(), nullable=True),
        sa.Column("esprit", sa.Integer(), nullable=False),
        sa.Column("battles", sa.Integer(), nullable=False),
        sa.Column("formed_epoch", sa.Integer(), nullable=False),
        sa.Column("disbanded_epoch", sa.Integer(), nullable=True),
        sa.Column("locked", sa.JSON(), nullable=False),
        sa.CheckConstraint("battles >= 0", name=op.f("ck_named_units_battles_min")),
        sa.CheckConstraint("esprit BETWEEN 0 AND 100", name=op.f("ck_named_units_esprit_range")),
        sa.CheckConstraint("formed_epoch >= 0", name=op.f("ck_named_units_formed_epoch_min")),
        sa.ForeignKeyConstraint(["owner_entity_id"], ["entities.id"], name=op.f("fk_named_units_owner_entity_id_entities"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["raised_from_entity_id"], ["entities.id"], name=op.f("fk_named_units_raised_from_entity_id_entities"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["unit_id"], ["army_units.id"], name=op.f("fk_named_units_unit_id_army_units"), ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_named_units")),
        sa.UniqueConstraint("unit_id", name=op.f("uq_named_units_unit_id")),
    )
    with op.batch_alter_table("named_units", schema=None) as batch_op:
        batch_op.create_index("ix_named_units_owner", ["owner_entity_id"], unique=False)

    op.create_table(
        "unit_honours",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("named_unit_id", sa.Integer(), nullable=False),
        sa.Column(
            "kind",
            sa.Enum("victory", "stand", "siege", "survival", "massacre", name="kind", native_enum=False, create_constraint=True, length=40),
            nullable=False,
        ),
        sa.Column("note", sa.String(), nullable=False),
        sa.Column("epoch", sa.Integer(), nullable=False),
        sa.Column("locked", sa.JSON(), nullable=False),
        sa.CheckConstraint("epoch >= 0", name=op.f("ck_unit_honours_epoch_min")),
        sa.ForeignKeyConstraint(["named_unit_id"], ["named_units.id"], name=op.f("fk_unit_honours_named_unit_id_named_units"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_unit_honours")),
    )
    with op.batch_alter_table("unit_honours", schema=None) as batch_op:
        batch_op.create_index("ix_unit_honours_unit", ["named_unit_id"], unique=False)
    widen(True)


def downgrade() -> None:
    for table, column, _ in MATERIAL_COLUMNS:
        values = ", ".join(f"'{value}'" for value in MATERIALS_AFTER[len(MATERIALS_BEFORE) :])
        op.execute(f"UPDATE {table} SET {column} = 'stone' WHERE {column} IN ({values})")
    op.execute("UPDATE faction_profiles SET kind = 'warrior_order' WHERE kind = 'veterans'")
    widen(False)
    with op.batch_alter_table("unit_honours", schema=None) as batch_op:
        batch_op.drop_index("ix_unit_honours_unit")

    op.drop_table("unit_honours")
    with op.batch_alter_table("named_units", schema=None) as batch_op:
        batch_op.drop_index("ix_named_units_owner")

    op.drop_table("named_units")
    with op.batch_alter_table("exchange_rates", schema=None) as batch_op:
        batch_op.drop_index("ix_exchange_rates_pair")

    op.drop_table("exchange_rates")
    op.drop_table("written_works")
    op.drop_table("writing_customs")
    op.drop_table("water_lifts")
    with op.batch_alter_table("veteran_grants", schema=None) as batch_op:
        batch_op.drop_index("ix_veteran_grants_polity")

    op.drop_table("veteran_grants")
    with op.batch_alter_table("tourist_flows", schema=None) as batch_op:
        batch_op.drop_index("ix_tourist_flows_sight")

    op.drop_table("tourist_flows")
    op.drop_table("securities")
    with op.batch_alter_table("putting_out", schema=None) as batch_op:
        batch_op.drop_index("ix_putting_out_town")

    op.drop_table("putting_out")
    with op.batch_alter_table("order_transitions", schema=None) as batch_op:
        batch_op.drop_index("ix_order_transitions_polity")

    op.drop_table("order_transitions")
    op.drop_table("navigation_kits")
    with op.batch_alter_table("hoards", schema=None) as batch_op:
        batch_op.drop_index("ix_hoards_place")

    op.drop_table("hoards")
    with op.batch_alter_table("economic_orders", schema=None) as batch_op:
        batch_op.drop_index("ix_economic_orders_polity")

    op.drop_table("economic_orders")
    with op.batch_alter_table("container_stocks", schema=None) as batch_op:
        batch_op.drop_index("ix_container_stocks_kind")

    op.drop_table("container_stocks")
    op.drop_table("chain_holdings")
    op.drop_table("bills_of_exchange")
    op.drop_table("savings")
    op.drop_table("economic_order_kinds")
