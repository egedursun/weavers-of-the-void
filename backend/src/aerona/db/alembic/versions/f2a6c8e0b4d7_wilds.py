import sqlalchemy as sa
from alembic import op

revision = "f2a6c8e0b4d7"
down_revision = "e8f4b2d6a0c3"
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
    "trade_route",
    "disease",
    "polity",
    "house",
    "treaty",
    "ideology",
    "rite",
)
NEW_ENTITY_TYPES = (*OLD_ENTITY_TYPES, "beast")
OLD_ENGINE_KINDS = (
    "war",
    "battle",
    "siege",
    "magic_storm",
    "earthquake",
    "flood",
    "plague",
    "drought",
    "storm",
    "famine",
    "uprising",
    "migration",
    "temple",
    "wall",
    "library",
    "school",
    "observatory",
    "cosmic_archive",
    "wonder",
    "rebels",
    "merchant_guild",
    "priests_council",
    "warrior_band",
    "interworld_federation",
    "wandering_market",
    "void_pirates",
    "peoples_army",
    "holy_guard",
    "mercenary_army",
    "dialect",
    "primitive_language",
    "currency",
    "eclipse_prophecy",
    "cosmic_travel_resource",
    "golem",
    "chimera",
    "descended_soul",
    "mirror_birth",
    "apprentice",
    "comet",
    "ascension_myth",
    "god_corpse",
    "god_shade",
    "resurrection_order",
    "ghost_ship",
    "colony",
)
NEW_ENGINE_KINDS = (*OLD_ENGINE_KINDS, "domesticated")
OLD_TRAITS = ("flying", "venomous", "soul_eater", "radiant", "fissiparous", "hive_mind", "stoneskin", "time_rewinder", "shapeshifter", "mind_reader")
NEW_TRAITS = (
    "flying",
    "venomous",
    "soul_eater",
    "radiant",
    "fissiparous",
    "hive_mind",
    "stoneskin",
    "time_rewinder",
    "shapeshifter",
    "mind_reader",
    "armoured",
    "burrowing",
    "aquatic",
    "amphibious",
    "pack_hunter",
    "ambush_predator",
    "regenerating",
    "poisonous_flesh",
    "fire_breathing",
    "cold_breathing",
    "echolocation",
    "camouflage",
    "swarm_breeder",
    "long_lived",
    "mimic",
    "spirit_sight",
    "iron_eating",
    "crop_pest",
    "plague_bearer",
    "sacred_animal",
)
WIDENED = (
    ("entities", "entity_type", OLD_ENTITY_TYPES, NEW_ENTITY_TYPES, False),
    ("son_powers", "param_entity_type", OLD_ENTITY_TYPES, NEW_ENTITY_TYPES, True),
    ("entities", "engine_kind", OLD_ENGINE_KINDS, NEW_ENGINE_KINDS, True),
    ("entity_traits", "trait", OLD_TRAITS, NEW_TRAITS, False),
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
        "beast_profiles",
        sa.Column("beast_entity_id", sa.Integer(), nullable=False),
        sa.Column("species_entity_id", sa.Integer(), nullable=True),
        sa.Column("endurance", sa.Integer(), nullable=False),
        sa.Column("perception", sa.Integer(), nullable=False),
        sa.Column("willpower", sa.Integer(), nullable=False),
        sa.Column("intelligence", sa.Integer(), nullable=False),
        sa.Column("age", sa.Integer(), nullable=False),
        sa.Column("lifespan", sa.Integer(), nullable=False),
        sa.Column(
            "size_class",
            sa.Enum("tiny", "small", "medium", "large", "huge", "colossal", name="size_class", native_enum=False, create_constraint=True, length=40),
            nullable=False,
        ),
        sa.Column("lair_place_id", sa.Integer(), nullable=True),
        sa.Column(
            "temper",
            sa.Enum("hungry", "territorial", "sleeping", "enraged", "bound", "tamed", name="temper", native_enum=False, create_constraint=True, length=40),
            nullable=False,
        ),
        sa.Column("bound_to_node_id", sa.Integer(), nullable=True),
        sa.Column("hoard", sa.JSON(), nullable=False),
        sa.Column("raids", sa.Integer(), nullable=False),
        sa.Column("woke_epoch", sa.Integer(), nullable=True),
        sa.Column("updated_epoch", sa.Integer(), nullable=False),
        sa.Column("locked", sa.JSON(), nullable=False),
        sa.CheckConstraint("age >= 0", name=op.f("ck_beast_profiles_age_min")),
        sa.CheckConstraint("endurance BETWEEN 0 AND 100", name=op.f("ck_beast_profiles_endurance_range")),
        sa.CheckConstraint("intelligence BETWEEN 0 AND 100", name=op.f("ck_beast_profiles_intelligence_range")),
        sa.CheckConstraint("lifespan >= 1", name=op.f("ck_beast_profiles_lifespan_min")),
        sa.CheckConstraint("perception BETWEEN 0 AND 100", name=op.f("ck_beast_profiles_perception_range")),
        sa.CheckConstraint("willpower BETWEEN 0 AND 100", name=op.f("ck_beast_profiles_willpower_range")),
        sa.ForeignKeyConstraint(["beast_entity_id"], ["entities.id"], name=op.f("fk_beast_profiles_beast_entity_id_entities"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["bound_to_node_id"], ["nodes.id"], name=op.f("fk_beast_profiles_bound_to_node_id_nodes"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["lair_place_id"], ["entities.id"], name=op.f("fk_beast_profiles_lair_place_id_entities"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["species_entity_id"], ["entities.id"], name=op.f("fk_beast_profiles_species_entity_id_entities"), ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("beast_entity_id", name=op.f("pk_beast_profiles")),
    )
    with op.batch_alter_table("beast_profiles", schema=None) as batch_op:
        batch_op.create_index("ix_beast_profiles_species", ["species_entity_id"], unique=False)

    op.create_table(
        "herds",
        sa.Column("community_entity_id", sa.Integer(), nullable=False),
        sa.Column("species_entity_id", sa.Integer(), nullable=False),
        sa.Column("head", sa.Integer(), nullable=False),
        sa.Column(
            "stage",
            sa.Enum("wild", "tamed", "herded", "domesticated", "breed", name="stage", native_enum=False, create_constraint=True, length=40),
            nullable=False,
        ),
        sa.Column("since_epoch", sa.Integer(), nullable=False),
        sa.Column("fed_epochs", sa.Integer(), nullable=False),
        sa.Column("locked", sa.JSON(), nullable=False),
        sa.CheckConstraint("head >= 0", name=op.f("ck_herds_head_min")),
        sa.ForeignKeyConstraint(["community_entity_id"], ["entities.id"], name=op.f("fk_herds_community_entity_id_entities"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["species_entity_id"], ["entities.id"], name=op.f("fk_herds_species_entity_id_entities"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("community_entity_id", "species_entity_id", name=op.f("pk_herds")),
    )
    with op.batch_alter_table("herds", schema=None) as batch_op:
        batch_op.create_index("ix_herds_species", ["species_entity_id"], unique=False)

    op.create_table(
        "species_hosts",
        sa.Column("species_entity_id", sa.Integer(), nullable=False),
        sa.Column("disease_entity_id", sa.Integer(), nullable=False),
        sa.Column("immune", sa.Boolean(), nullable=False),
        sa.ForeignKeyConstraint(["disease_entity_id"], ["entities.id"], name=op.f("fk_species_hosts_disease_entity_id_entities"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["species_entity_id"], ["entities.id"], name=op.f("fk_species_hosts_species_entity_id_entities"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("species_entity_id", "disease_entity_id", name=op.f("pk_species_hosts")),
    )
    op.create_table(
        "species_profiles",
        sa.Column("species_entity_id", sa.Integer(), nullable=False),
        sa.Column("body_plan", sa.String(length=120), nullable=False),
        sa.Column(
            "size_class",
            sa.Enum("tiny", "small", "medium", "large", "huge", "colossal", name="size_class", native_enum=False, create_constraint=True, length=40),
            nullable=False,
        ),
        sa.Column("lifespan_years", sa.Integer(), nullable=False),
        sa.Column("maturity_years", sa.Integer(), nullable=False),
        sa.Column("litter_size", sa.Integer(), nullable=False),
        sa.Column("breeding_seasons", sa.Integer(), nullable=False),
        sa.Column(
            "diet",
            sa.Enum(
                "herbivore",
                "carnivore",
                "omnivore",
                "scavenger",
                "filter",
                "photosynthetic",
                "mineral",
                "soul",
                "void",
                name="diet",
                native_enum=False,
                create_constraint=True,
                length=40,
            ),
            nullable=False,
        ),
        sa.Column("metabolism", sa.Integer(), nullable=False),
        sa.Column("habitat", sa.JSON(), nullable=False),
        sa.Column("temperature_min", sa.Integer(), nullable=False),
        sa.Column("temperature_max", sa.Integer(), nullable=False),
        sa.Column("water_need", sa.Integer(), nullable=False),
        sa.Column("altitude_min", sa.Integer(), nullable=False),
        sa.Column("altitude_max", sa.Integer(), nullable=False),
        sa.Column("nocturnal", sa.Boolean(), nullable=False),
        sa.Column("migratory", sa.Boolean(), nullable=False),
        sa.Column("migration_path", sa.JSON(), nullable=False),
        sa.Column("aggression", sa.Integer(), nullable=False),
        sa.Column("territoriality", sa.Integer(), nullable=False),
        sa.Column(
            "sociality", sa.Enum("solitary", "pack", "herd", "hive", name="sociality", native_enum=False, create_constraint=True, length=40), nullable=False
        ),
        sa.Column("cunning", sa.Integer(), nullable=False),
        sa.Column("fear_of_people", sa.Integer(), nullable=False),
        sa.Column("tameability", sa.Integer(), nullable=False),
        sa.Column(
            "stage",
            sa.Enum("wild", "tamed", "herded", "domesticated", "breed", name="stage", native_enum=False, create_constraint=True, length=40),
            nullable=False,
        ),
        sa.Column("domesticated_from_id", sa.Integer(), nullable=True),
        sa.Column("sacred_to_node_id", sa.Integer(), nullable=True),
        sa.Column("stage_epoch", sa.Integer(), nullable=False),
        sa.Column("updated_epoch", sa.Integer(), nullable=False),
        sa.Column("locked", sa.JSON(), nullable=False),
        sa.CheckConstraint("aggression BETWEEN 0 AND 100", name=op.f("ck_species_profiles_aggression_range")),
        sa.CheckConstraint("breeding_seasons >= 0", name=op.f("ck_species_profiles_breeding_seasons_min")),
        sa.CheckConstraint("cunning BETWEEN 0 AND 100", name=op.f("ck_species_profiles_cunning_range")),
        sa.CheckConstraint("fear_of_people BETWEEN 0 AND 100", name=op.f("ck_species_profiles_fear_of_people_range")),
        sa.CheckConstraint("lifespan_years >= 1", name=op.f("ck_species_profiles_lifespan_years_min")),
        sa.CheckConstraint("litter_size >= 1", name=op.f("ck_species_profiles_litter_size_min")),
        sa.CheckConstraint("maturity_years >= 0", name=op.f("ck_species_profiles_maturity_years_min")),
        sa.CheckConstraint("metabolism BETWEEN 0 AND 100", name=op.f("ck_species_profiles_metabolism_range")),
        sa.CheckConstraint("tameability BETWEEN 0 AND 100", name=op.f("ck_species_profiles_tameability_range")),
        sa.CheckConstraint("territoriality BETWEEN 0 AND 100", name=op.f("ck_species_profiles_territoriality_range")),
        sa.CheckConstraint("water_need BETWEEN 0 AND 100", name=op.f("ck_species_profiles_water_need_range")),
        sa.ForeignKeyConstraint(["domesticated_from_id"], ["entities.id"], name=op.f("fk_species_profiles_domesticated_from_id_entities"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["sacred_to_node_id"], ["nodes.id"], name=op.f("fk_species_profiles_sacred_to_node_id_nodes"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["species_entity_id"], ["entities.id"], name=op.f("fk_species_profiles_species_entity_id_entities"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("species_entity_id", name=op.f("pk_species_profiles")),
    )
    op.create_table(
        "species_ranges",
        sa.Column("species_entity_id", sa.Integer(), nullable=False),
        sa.Column("region_entity_id", sa.Integer(), nullable=False),
        sa.Column("abundance", sa.Integer(), nullable=False),
        sa.Column("trend", sa.Enum("rising", "steady", "falling", name="trend", native_enum=False, create_constraint=True, length=40), nullable=False),
        sa.Column("fit", sa.Integer(), nullable=False),
        sa.Column("hunted", sa.Integer(), nullable=False),
        sa.Column("since_epoch", sa.Integer(), nullable=False),
        sa.Column("updated_epoch", sa.Integer(), nullable=False),
        sa.Column("locked", sa.JSON(), nullable=False),
        sa.CheckConstraint("abundance >= 0", name=op.f("ck_species_ranges_abundance_min")),
        sa.ForeignKeyConstraint(["region_entity_id"], ["entities.id"], name=op.f("fk_species_ranges_region_entity_id_entities"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["species_entity_id"], ["entities.id"], name=op.f("fk_species_ranges_species_entity_id_entities"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("species_entity_id", "region_entity_id", name=op.f("pk_species_ranges")),
    )
    with op.batch_alter_table("species_ranges", schema=None) as batch_op:
        batch_op.create_index("ix_species_ranges_region", ["region_entity_id"], unique=False)

    op.create_table(
        "species_uses",
        sa.Column("species_entity_id", sa.Integer(), nullable=False),
        sa.Column(
            "use",
            sa.Enum(
                "food", "labour", "mount", "war", "guard", "companion", "sacrifice", "magic", name="use", native_enum=False, create_constraint=True, length=40
            ),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["species_entity_id"], ["entities.id"], name=op.f("fk_species_uses_species_entity_id_entities"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("species_entity_id", "use", name=op.f("pk_species_uses")),
    )
    op.create_table(
        "species_yields",
        sa.Column("species_entity_id", sa.Integer(), nullable=False),
        sa.Column("product", sa.String(length=120), nullable=False),
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
            nullable=True,
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
        sa.Column("rate", sa.Integer(), nullable=False),
        sa.CheckConstraint("rate >= 0", name=op.f("ck_species_yields_rate_min")),
        sa.ForeignKeyConstraint(["species_entity_id"], ["entities.id"], name=op.f("fk_species_yields_species_entity_id_entities"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("species_entity_id", "product", name=op.f("pk_species_yields")),
    )


def downgrade() -> None:
    op.drop_table("species_yields")
    op.drop_table("species_uses")
    with op.batch_alter_table("species_ranges", schema=None) as batch_op:
        batch_op.drop_index("ix_species_ranges_region")

    op.drop_table("species_ranges")
    op.drop_table("species_profiles")
    op.drop_table("species_hosts")
    with op.batch_alter_table("herds", schema=None) as batch_op:
        batch_op.drop_index("ix_herds_species")

    op.drop_table("herds")
    with op.batch_alter_table("beast_profiles", schema=None) as batch_op:
        batch_op.drop_index("ix_beast_profiles_species")

    op.drop_table("beast_profiles")
    widen(False)
