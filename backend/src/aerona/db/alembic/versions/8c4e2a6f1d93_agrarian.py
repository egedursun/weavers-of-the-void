import sqlalchemy as sa
from alembic import op

revision = "8c4e2a6f1d93"
down_revision = "5d2a7c9e4f18"
branch_labels = None
depends_on = None

TECHNIQUES = (
    "phalanx_drill",
    "horse_archery",
    "siegecraft",
    "fortification",
    "logistics",
    "herbalism",
    "surgery",
    "amputation",
    "prosthetics",
    "quarantine",
    "inoculation",
    "irrigation",
    "crop_rotation",
    "terracing",
    "plough",
    "selective_breeding",
    "bronze",
    "iron",
    "steel",
    "skysteel",
    "arch",
    "dome",
    "aqueduct",
    "fortress",
    "alphabet",
    "paper",
    "printing",
    "cryptography",
    "calendar",
    "navigation_stars",
    "eclipse_prediction",
    "sailing",
    "shipwrighting",
    "coinage",
    "banking",
    "warding",
    "summoning",
    "sky_sailing",
    "necromancy",
    "alchemy",
    "astronomy_instruments",
    "cartography",
    "oral_law",
    "written_law",
    "codified_law",
    "bureaucracy",
    "census",
    "postal_service",
    "diplomatic_corps",
    "standing_army_admin",
    "double_entry",
    "joint_stock",
    "insurance",
    "guilds",
    "universities",
    "hospitals",
    "printing_press",
    "organised_clergy",
    "monasticism",
    "theology_schools",
    "logic",
    "natural_philosophy",
    "empiricism",
    "humanist_ideals",
    "examinations",
)
ACTS = (
    "execution",
    "mutilation",
    "betrayal",
    "mercy_to_enemy",
    "human_sacrifice",
    "trade_with_outsiders",
    "building_temples",
    "burning_books",
    "conquest",
    "raiding",
    "duelling",
    "ransom",
    "taking_captives",
    "oathbreaking",
    "learning",
    "hospitality",
    "winter_fighting",
    "guest_killing",
    "ritual_scarring",
    "killing_kin",
    "killing_outsider",
    "killing_in_war",
    "killing_captive",
    "regicide",
    "duel_to_death",
    "revenge_killing",
    "theft",
    "treason",
    "cowardice",
    "desecration",
    "bribery",
    "suicide",
    "torture",
    "eating_sapients",
    "iconoclasm",
    "conversion_by_force",
    "polygamy",
    "incest",
    "magic_use",
    "blood_magic",
    "void_magic",
    "necromancy",
    "hoarding_in_famine",
    "slavery",
    "adultery",
    "usury",
    "infanticide",
    "abandoning_elders",
    "forced_labour",
    "selling_offices",
)
ENTRIES = (
    "tax",
    "tolls",
    "investment",
    "garrison",
    "walls",
    "building",
    "festival",
    "alms",
    "fire",
    "plunder",
    "grant",
    "loan",
    "upkeep",
    "office_sale",
)
OCCASIONS = (
    "courtesy",
    "feast",
    "circuit",
    "offering",
    "marriage",
    "return",
    "alliance",
)
ORIGINS = (
    "gift",
    "rescue",
    "war_support",
    "succession_support",
    "scheme_aid",
    "vote",
)
NEW_ACTS = (*ACTS, "poaching", "enclosing")
NEW_TECHNIQUES = (*TECHNIQUES, "drainage")
NEW_ENTRIES = (*ENTRIES, "relief", "rebuilding", "monopoly")
WIDENED = (
    ("creator_taboos", "act", ACTS, NEW_ACTS, False),
    ("culture_ethics", "act", ACTS, NEW_ACTS, False),
    ("geasa", "act", ACTS, NEW_ACTS, False),
    ("deeds", "act", ACTS, NEW_ACTS, True),
    ("tradition_profiles", "taboo_act", ACTS, NEW_ACTS, True),
    ("artifact_studies", "technique", TECHNIQUES, NEW_TECHNIQUES, False),
    ("guild_secrets", "technique", TECHNIQUES, NEW_TECHNIQUES, False),
    ("holder_techniques", "technique", TECHNIQUES, NEW_TECHNIQUES, False),
    ("institutions", "technique", TECHNIQUES, NEW_TECHNIQUES, False),
    ("research_boosts", "technique", TECHNIQUES, NEW_TECHNIQUES, False),
    ("research_focus", "technique", TECHNIQUES, NEW_TECHNIQUES, False),
    ("research_incidents", "technique", TECHNIQUES, NEW_TECHNIQUES, True),
    ("research_progress", "technique", TECHNIQUES, NEW_TECHNIQUES, False),
    ("excavation_stages", "technique", TECHNIQUES, NEW_TECHNIQUES, True),
    ("polity_treasury", "entry", ENTRIES, NEW_ENTRIES, False),
    ("settlement_treasury", "entry", ENTRIES, NEW_ENTRIES, False),
    ("gifts", "occasion", OCCASIONS, (*OCCASIONS, "relief"), False),
    ("favours", "origin", ORIGINS, (*ORIGINS, "relief"), False),
)


def enum_of(name: str, values: tuple[str, ...]) -> sa.Enum:
    return sa.Enum(*values, name=name, native_enum=False, create_constraint=True, length=40)


def widen(forward: bool) -> None:
    for table, column, old, new, nullable in WIDENED:
        before, after = (old, new) if forward else (new, old)
        with op.batch_alter_table(table, schema=None) as batch_op:
            batch_op.alter_column(column, existing_type=enum_of(column, before), type_=enum_of(column, after), existing_nullable=nullable)


def upgrade() -> None:
    widen(True)
    op.create_table(
        "central_places",
        sa.Column("settlement_entity_id", sa.Integer(), nullable=False),
        sa.Column("rank", sa.Enum("daily", "weekly", "rare", name="rank", native_enum=False, create_constraint=True, length=40), nullable=False),
        sa.Column("catchment", sa.Integer(), nullable=False),
        sa.Column("served_by_entity_id", sa.Integer(), nullable=True),
        sa.Column("centrality", sa.Integer(), nullable=False),
        sa.Column("updated_epoch", sa.Integer(), nullable=False),
        sa.Column("locked", sa.JSON(), nullable=False),
        sa.CheckConstraint("catchment >= 0", name=op.f("ck_central_places_catchment_min")),
        sa.CheckConstraint("centrality BETWEEN 0 AND 100", name=op.f("ck_central_places_centrality_range")),
        sa.CheckConstraint("updated_epoch >= 0", name=op.f("ck_central_places_updated_epoch_min")),
        sa.ForeignKeyConstraint(["served_by_entity_id"], ["entities.id"], name=op.f("fk_central_places_served_by_entity_id_entities"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["settlement_entity_id"], ["entities.id"], name=op.f("fk_central_places_settlement_entity_id_entities"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("settlement_entity_id", name=op.f("pk_central_places")),
    )
    op.create_table(
        "commons",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("region_entity_id", sa.Integer(), nullable=False),
        sa.Column("kind", sa.Enum("pasture", "woods", "fishery", name="kind", native_enum=False, create_constraint=True, length=40), nullable=False),
        sa.Column(
            "rule", sa.Enum("open", "customary", "council", "enclosed", name="rule", native_enum=False, create_constraint=True, length=40), nullable=False
        ),
        sa.Column("condition", sa.Integer(), nullable=False),
        sa.Column("use", sa.Integer(), nullable=False),
        sa.Column("steward_entity_id", sa.Integer(), nullable=True),
        sa.Column("encloser_node_id", sa.Integer(), nullable=True),
        sa.Column("enclosed_epoch", sa.Integer(), nullable=True),
        sa.Column("dispossessed", sa.Integer(), nullable=False),
        sa.Column("since_epoch", sa.Integer(), nullable=False),
        sa.Column("locked", sa.JSON(), nullable=False),
        sa.CheckConstraint("condition BETWEEN 0 AND 100", name=op.f("ck_commons_condition_range")),
        sa.CheckConstraint("dispossessed >= 0", name=op.f("ck_commons_dispossessed_min")),
        sa.CheckConstraint("use BETWEEN 0 AND 200", name=op.f("ck_commons_use_range")),
        sa.ForeignKeyConstraint(["encloser_node_id"], ["nodes.id"], name=op.f("fk_commons_encloser_node_id_nodes"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["region_entity_id"], ["entities.id"], name=op.f("fk_commons_region_entity_id_entities"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["steward_entity_id"], ["entities.id"], name=op.f("fk_commons_steward_entity_id_entities"), ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_commons")),
        sa.UniqueConstraint("region_entity_id", "kind", name="uq_commons_region_kind"),
    )
    with op.batch_alter_table("commons", schema=None) as batch_op:
        batch_op.create_index(batch_op.f("ix_commons_encloser_node_id"), ["encloser_node_id"], unique=False)
        batch_op.create_index(batch_op.f("ix_commons_region_entity_id"), ["region_entity_id"], unique=False)

    op.create_table(
        "famine_lore",
        sa.Column("people_entity_id", sa.Integer(), nullable=False),
        sa.Column("memory", sa.Integer(), nullable=False),
        sa.Column("famine_foods", sa.Boolean(), nullable=False),
        sa.Column("storage", sa.Integer(), nullable=False),
        sa.Column("updated_epoch", sa.Integer(), nullable=False),
        sa.Column("locked", sa.JSON(), nullable=False),
        sa.CheckConstraint("memory BETWEEN 0 AND 100", name=op.f("ck_famine_lore_memory_range")),
        sa.CheckConstraint("storage BETWEEN 0 AND 100", name=op.f("ck_famine_lore_storage_range")),
        sa.CheckConstraint("updated_epoch >= 0", name=op.f("ck_famine_lore_updated_epoch_min")),
        sa.ForeignKeyConstraint(["people_entity_id"], ["entities.id"], name=op.f("fk_famine_lore_people_entity_id_entities"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("people_entity_id", name=op.f("pk_famine_lore")),
    )
    op.create_table(
        "game_reserves",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("region_entity_id", sa.Integer(), nullable=False),
        sa.Column("holder_node_id", sa.Integer(), nullable=True),
        sa.Column("species_entity_id", sa.Integer(), nullable=True),
        sa.Column("strictness", sa.Integer(), nullable=False),
        sa.Column("poaching", sa.Integer(), nullable=False),
        sa.Column("resentment", sa.Integer(), nullable=False),
        sa.Column("since_epoch", sa.Integer(), nullable=False),
        sa.Column("locked", sa.JSON(), nullable=False),
        sa.CheckConstraint("poaching BETWEEN 0 AND 100", name=op.f("ck_game_reserves_poaching_range")),
        sa.CheckConstraint("resentment BETWEEN 0 AND 100", name=op.f("ck_game_reserves_resentment_range")),
        sa.CheckConstraint("since_epoch >= 0", name=op.f("ck_game_reserves_since_epoch_min")),
        sa.CheckConstraint("strictness BETWEEN 0 AND 100", name=op.f("ck_game_reserves_strictness_range")),
        sa.ForeignKeyConstraint(["holder_node_id"], ["nodes.id"], name=op.f("fk_game_reserves_holder_node_id_nodes"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["region_entity_id"], ["entities.id"], name=op.f("fk_game_reserves_region_entity_id_entities"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["species_entity_id"], ["entities.id"], name=op.f("fk_game_reserves_species_entity_id_entities"), ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_game_reserves")),
    )
    with op.batch_alter_table("game_reserves", schema=None) as batch_op:
        batch_op.create_index(batch_op.f("ix_game_reserves_holder_node_id"), ["holder_node_id"], unique=False)
        batch_op.create_index(batch_op.f("ix_game_reserves_region_entity_id"), ["region_entity_id"], unique=False)

    op.create_table(
        "intensification",
        sa.Column("region_entity_id", sa.Integer(), nullable=False),
        sa.Column("pressure", sa.Integer(), nullable=False),
        sa.Column("intensity", sa.Integer(), nullable=False),
        sa.Column("research_boost", sa.Integer(), nullable=False),
        sa.Column("updated_epoch", sa.Integer(), nullable=False),
        sa.Column("locked", sa.JSON(), nullable=False),
        sa.CheckConstraint("intensity BETWEEN 0 AND 100", name=op.f("ck_intensification_intensity_range")),
        sa.CheckConstraint("pressure BETWEEN 0 AND 300", name=op.f("ck_intensification_pressure_range")),
        sa.CheckConstraint("research_boost BETWEEN 0 AND 100", name=op.f("ck_intensification_research_boost_range")),
        sa.CheckConstraint("updated_epoch >= 0", name=op.f("ck_intensification_updated_epoch_min")),
        sa.ForeignKeyConstraint(["region_entity_id"], ["entities.id"], name=op.f("fk_intensification_region_entity_id_entities"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("region_entity_id", name=op.f("pk_intensification")),
    )
    op.create_table(
        "keystone_resources",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("world_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("producer_entity_id", sa.Integer(), nullable=True),
        sa.Column("source_region_entity_id", sa.Integer(), nullable=True),
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
                name="commodity",
                native_enum=False,
                create_constraint=True,
                length=40,
            ),
            nullable=True,
        ),
        sa.Column(
            "use", sa.Enum("navigation", "longevity", "prescience", "rite", name="use", native_enum=False, create_constraint=True, length=40), nullable=False
        ),
        sa.Column("cult_entity_id", sa.Integer(), nullable=True),
        sa.Column("controller_entity_id", sa.Integer(), nullable=True),
        sa.Column("harvest", sa.Integer(), nullable=False),
        sa.Column("supply", sa.Integer(), nullable=False),
        sa.Column("price", sa.Integer(), nullable=False),
        sa.Column("designated_epoch", sa.Integer(), nullable=False),
        sa.Column("designated_by_son_id", sa.Integer(), nullable=True),
        sa.Column("locked", sa.JSON(), nullable=False),
        sa.CheckConstraint("designated_epoch >= 0", name=op.f("ck_keystone_resources_designated_epoch_min")),
        sa.CheckConstraint("harvest BETWEEN 0 AND 100", name=op.f("ck_keystone_resources_harvest_range")),
        sa.CheckConstraint("price >= 0", name=op.f("ck_keystone_resources_price_min")),
        sa.CheckConstraint("supply BETWEEN 0 AND 100", name=op.f("ck_keystone_resources_supply_range")),
        sa.ForeignKeyConstraint(
            ["controller_entity_id"], ["entities.id"], name=op.f("fk_keystone_resources_controller_entity_id_entities"), ondelete="SET NULL"
        ),
        sa.ForeignKeyConstraint(["cult_entity_id"], ["entities.id"], name=op.f("fk_keystone_resources_cult_entity_id_entities"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["designated_by_son_id"], ["sons.id"], name=op.f("fk_keystone_resources_designated_by_son_id_sons"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["producer_entity_id"], ["entities.id"], name=op.f("fk_keystone_resources_producer_entity_id_entities"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(
            ["source_region_entity_id"], ["entities.id"], name=op.f("fk_keystone_resources_source_region_entity_id_entities"), ondelete="SET NULL"
        ),
        sa.ForeignKeyConstraint(["world_id"], ["worlds.id"], name=op.f("fk_keystone_resources_world_id_worlds"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_keystone_resources")),
        sa.UniqueConstraint("world_id", name="uq_keystone_resources_world"),
    )
    op.create_table(
        "land_rings",
        sa.Column("region_entity_id", sa.Integer(), nullable=False),
        sa.Column("market_entity_id", sa.Integer(), nullable=True),
        sa.Column(
            "ring",
            sa.Enum("gardens", "forestry", "grain", "ranching", "wilds", name="ring", native_enum=False, create_constraint=True, length=40),
            nullable=False,
        ),
        sa.Column("distance", sa.Integer(), nullable=False),
        sa.Column("by_water", sa.Boolean(), nullable=False),
        sa.Column("gap", sa.Integer(), nullable=False),
        sa.Column("updated_epoch", sa.Integer(), nullable=False),
        sa.Column("locked", sa.JSON(), nullable=False),
        sa.CheckConstraint("distance >= 0", name=op.f("ck_land_rings_distance_min")),
        sa.CheckConstraint("gap BETWEEN 0 AND 100", name=op.f("ck_land_rings_gap_range")),
        sa.CheckConstraint("updated_epoch >= 0", name=op.f("ck_land_rings_updated_epoch_min")),
        sa.ForeignKeyConstraint(["market_entity_id"], ["entities.id"], name=op.f("fk_land_rings_market_entity_id_entities"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["region_entity_id"], ["entities.id"], name=op.f("fk_land_rings_region_entity_id_entities"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("region_entity_id", name=op.f("pk_land_rings")),
    )
    op.create_table(
        "perennials",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("region_entity_id", sa.Integer(), nullable=False),
        sa.Column("kind", sa.Enum("orchard", "vineyard", "grove", "timber", name="kind", native_enum=False, create_constraint=True, length=40), nullable=False),
        sa.Column("species_entity_id", sa.Integer(), nullable=True),
        sa.Column("owner_node_id", sa.Integer(), nullable=True),
        sa.Column("area", sa.Integer(), nullable=False),
        sa.Column("maturity", sa.Integer(), nullable=False),
        sa.Column("mature_epochs", sa.Integer(), nullable=False),
        sa.Column("condition", sa.Integer(), nullable=False),
        sa.Column("planted_epoch", sa.Integer(), nullable=False),
        sa.Column("felled_epoch", sa.Integer(), nullable=True),
        sa.Column("locked", sa.JSON(), nullable=False),
        sa.CheckConstraint("area BETWEEN 0 AND 100", name=op.f("ck_perennials_area_range")),
        sa.CheckConstraint("condition BETWEEN 0 AND 100", name=op.f("ck_perennials_condition_range")),
        sa.CheckConstraint("mature_epochs >= 1", name=op.f("ck_perennials_mature_epochs_min")),
        sa.CheckConstraint("maturity BETWEEN 0 AND 100", name=op.f("ck_perennials_maturity_range")),
        sa.CheckConstraint("planted_epoch >= 0", name=op.f("ck_perennials_planted_epoch_min")),
        sa.ForeignKeyConstraint(["owner_node_id"], ["nodes.id"], name=op.f("fk_perennials_owner_node_id_nodes"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["region_entity_id"], ["entities.id"], name=op.f("fk_perennials_region_entity_id_entities"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["species_entity_id"], ["entities.id"], name=op.f("fk_perennials_species_entity_id_entities"), ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_perennials")),
    )
    with op.batch_alter_table("perennials", schema=None) as batch_op:
        batch_op.create_index(batch_op.f("ix_perennials_owner_node_id"), ["owner_node_id"], unique=False)
        batch_op.create_index("ix_perennials_region", ["region_entity_id"], unique=False)

    op.create_table(
        "preparedness",
        sa.Column("settlement_entity_id", sa.Integer(), nullable=False),
        sa.Column(
            "kind",
            sa.Enum("levee", "firebreak", "stockpile", "drill", "watchtower", "seawall", name="kind", native_enum=False, create_constraint=True, length=40),
            nullable=False,
        ),
        sa.Column("level", sa.Integer(), nullable=False),
        sa.Column("condition", sa.Integer(), nullable=False),
        sa.Column("averted", sa.Integer(), nullable=False),
        sa.Column("built_epoch", sa.Integer(), nullable=False),
        sa.Column("locked", sa.JSON(), nullable=False),
        sa.CheckConstraint("averted >= 0", name=op.f("ck_preparedness_averted_min")),
        sa.CheckConstraint("built_epoch >= 0", name=op.f("ck_preparedness_built_epoch_min")),
        sa.CheckConstraint("condition BETWEEN 0 AND 100", name=op.f("ck_preparedness_condition_range")),
        sa.CheckConstraint("level BETWEEN 0 AND 5", name=op.f("ck_preparedness_level_range")),
        sa.ForeignKeyConstraint(["settlement_entity_id"], ["entities.id"], name=op.f("fk_preparedness_settlement_entity_id_entities"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("settlement_entity_id", "kind", name=op.f("pk_preparedness")),
    )
    op.create_table(
        "reconstructions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("settlement_entity_id", sa.Integer(), nullable=False),
        sa.Column(
            "cause", sa.Enum("fire", "flood", "quake", "storm", "sack", name="cause", native_enum=False, create_constraint=True, length=40), nullable=False
        ),
        sa.Column("plan", sa.Enum("planned", "opportunistic", name="plan", native_enum=False, create_constraint=True, length=40), nullable=False),
        sa.Column("cost", sa.Integer(), nullable=False),
        sa.Column("paid", sa.Integer(), nullable=False),
        sa.Column("progress", sa.Integer(), nullable=False),
        sa.Column("planner_entity_id", sa.Integer(), nullable=True),
        sa.Column("seized_by_node_id", sa.Integer(), nullable=True),
        sa.Column("seized", sa.Integer(), nullable=False),
        sa.Column("started_epoch", sa.Integer(), nullable=False),
        sa.Column("finished_epoch", sa.Integer(), nullable=True),
        sa.Column("locked", sa.JSON(), nullable=False),
        sa.CheckConstraint("cost >= 0", name=op.f("ck_reconstructions_cost_min")),
        sa.CheckConstraint("paid >= 0", name=op.f("ck_reconstructions_paid_min")),
        sa.CheckConstraint("progress BETWEEN 0 AND 100", name=op.f("ck_reconstructions_progress_range")),
        sa.CheckConstraint("seized >= 0", name=op.f("ck_reconstructions_seized_min")),
        sa.CheckConstraint("started_epoch >= 0", name=op.f("ck_reconstructions_started_epoch_min")),
        sa.ForeignKeyConstraint(["planner_entity_id"], ["entities.id"], name=op.f("fk_reconstructions_planner_entity_id_entities"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["seized_by_node_id"], ["nodes.id"], name=op.f("fk_reconstructions_seized_by_node_id_nodes"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["settlement_entity_id"], ["entities.id"], name=op.f("fk_reconstructions_settlement_entity_id_entities"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_reconstructions")),
    )
    with op.batch_alter_table("reconstructions", schema=None) as batch_op:
        batch_op.create_index("ix_reconstructions_settlement", ["settlement_entity_id"], unique=False)

    op.create_table(
        "soil_nutrients",
        sa.Column("region_entity_id", sa.Integer(), nullable=False),
        sa.Column(
            "nutrient",
            sa.Enum("fixed", "mineral", "organic", "salinity", name="nutrient", native_enum=False, create_constraint=True, length=40),
            nullable=False,
        ),
        sa.Column("stock", sa.Integer(), nullable=False),
        sa.Column("trend", sa.Integer(), nullable=False),
        sa.Column("updated_epoch", sa.Integer(), nullable=False),
        sa.Column("locked", sa.JSON(), nullable=False),
        sa.CheckConstraint("stock BETWEEN 0 AND 100", name=op.f("ck_soil_nutrients_stock_range")),
        sa.CheckConstraint("trend BETWEEN -100 AND 100", name=op.f("ck_soil_nutrients_trend_range")),
        sa.CheckConstraint("updated_epoch >= 0", name=op.f("ck_soil_nutrients_updated_epoch_min")),
        sa.ForeignKeyConstraint(["region_entity_id"], ["entities.id"], name=op.f("fk_soil_nutrients_region_entity_id_entities"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("region_entity_id", "nutrient", name=op.f("pk_soil_nutrients")),
    )
    op.create_table(
        "brands",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("workshop_id", sa.Integer(), nullable=False),
        sa.Column("community_entity_id", sa.Integer(), nullable=False),
        sa.Column("owner_node_id", sa.Integer(), nullable=True),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("reputation", sa.Integer(), nullable=False),
        sa.Column("quality", sa.Integer(), nullable=False),
        sa.Column("renowned", sa.Integer(), nullable=False),
        sa.Column("counterfeits", sa.Integer(), nullable=False),
        sa.Column("since_epoch", sa.Integer(), nullable=False),
        sa.Column("locked", sa.JSON(), nullable=False),
        sa.CheckConstraint("counterfeits BETWEEN 0 AND 100", name=op.f("ck_brands_counterfeits_range")),
        sa.CheckConstraint("quality BETWEEN 0 AND 100", name=op.f("ck_brands_quality_range")),
        sa.CheckConstraint("renowned >= 0", name=op.f("ck_brands_renowned_min")),
        sa.CheckConstraint("reputation BETWEEN 0 AND 100", name=op.f("ck_brands_reputation_range")),
        sa.CheckConstraint("since_epoch >= 0", name=op.f("ck_brands_since_epoch_min")),
        sa.ForeignKeyConstraint(["community_entity_id"], ["entities.id"], name=op.f("fk_brands_community_entity_id_entities"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["owner_node_id"], ["nodes.id"], name=op.f("fk_brands_owner_node_id_nodes"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["workshop_id"], ["workshops.id"], name=op.f("fk_brands_workshop_id_workshops"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_brands")),
        sa.UniqueConstraint("workshop_id", name="uq_brands_workshop"),
    )
    with op.batch_alter_table("brands", schema=None) as batch_op:
        batch_op.create_index(batch_op.f("ix_brands_community_entity_id"), ["community_entity_id"], unique=False)
        batch_op.create_index(batch_op.f("ix_brands_owner_node_id"), ["owner_node_id"], unique=False)

    op.create_table(
        "relief_aid",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("event_entity_id", sa.Integer(), nullable=True),
        sa.Column("giver_node_id", sa.Integer(), nullable=False),
        sa.Column("receiver_entity_id", sa.Integer(), nullable=False),
        sa.Column("kind", sa.Enum("goods", "healers", "labour", name="kind", native_enum=False, create_constraint=True, length=40), nullable=False),
        sa.Column("amount", sa.Integer(), nullable=False),
        sa.Column("god_node_id", sa.Integer(), nullable=True),
        sa.Column("refused", sa.Boolean(), nullable=False),
        sa.Column("gift_id", sa.Integer(), nullable=True),
        sa.Column("epoch", sa.Integer(), nullable=False),
        sa.Column("locked", sa.JSON(), nullable=False),
        sa.CheckConstraint("amount >= 0", name=op.f("ck_relief_aid_amount_min")),
        sa.CheckConstraint("epoch >= 0", name=op.f("ck_relief_aid_epoch_min")),
        sa.ForeignKeyConstraint(["event_entity_id"], ["entities.id"], name=op.f("fk_relief_aid_event_entity_id_entities"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["gift_id"], ["gifts.id"], name=op.f("fk_relief_aid_gift_id_gifts"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["giver_node_id"], ["nodes.id"], name=op.f("fk_relief_aid_giver_node_id_nodes"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["god_node_id"], ["nodes.id"], name=op.f("fk_relief_aid_god_node_id_nodes"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["receiver_entity_id"], ["entities.id"], name=op.f("fk_relief_aid_receiver_entity_id_entities"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_relief_aid")),
    )
    with op.batch_alter_table("relief_aid", schema=None) as batch_op:
        batch_op.create_index(batch_op.f("ix_relief_aid_giver_node_id"), ["giver_node_id"], unique=False)
        batch_op.create_index("ix_relief_aid_receiver", ["receiver_entity_id"], unique=False)


def downgrade() -> None:
    with op.batch_alter_table("relief_aid", schema=None) as batch_op:
        batch_op.drop_index("ix_relief_aid_receiver")
        batch_op.drop_index(batch_op.f("ix_relief_aid_giver_node_id"))

    op.drop_table("relief_aid")
    with op.batch_alter_table("brands", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_brands_owner_node_id"))
        batch_op.drop_index(batch_op.f("ix_brands_community_entity_id"))

    op.drop_table("brands")
    op.drop_table("soil_nutrients")
    with op.batch_alter_table("reconstructions", schema=None) as batch_op:
        batch_op.drop_index("ix_reconstructions_settlement")

    op.drop_table("reconstructions")
    op.drop_table("preparedness")
    with op.batch_alter_table("perennials", schema=None) as batch_op:
        batch_op.drop_index("ix_perennials_region")
        batch_op.drop_index(batch_op.f("ix_perennials_owner_node_id"))

    op.drop_table("perennials")
    op.drop_table("land_rings")
    op.drop_table("keystone_resources")
    op.drop_table("intensification")
    with op.batch_alter_table("game_reserves", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_game_reserves_region_entity_id"))
        batch_op.drop_index(batch_op.f("ix_game_reserves_holder_node_id"))

    op.drop_table("game_reserves")
    op.drop_table("famine_lore")
    with op.batch_alter_table("commons", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_commons_region_entity_id"))
        batch_op.drop_index(batch_op.f("ix_commons_encloser_node_id"))

    op.drop_table("commons")
    op.drop_table("central_places")
    widen(False)
