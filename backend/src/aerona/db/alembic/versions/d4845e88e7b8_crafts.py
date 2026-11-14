import sqlalchemy as sa
from alembic import op

revision = "d4845e88e7b8"
down_revision = "0d554b5d77ad"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "assistive_aids",
        sa.Column("holder_node_id", sa.Integer(), nullable=False),
        sa.Column(
            "kind",
            sa.Enum("spectacles", "magnifier", "telescope", "hearing_horn", "cane", name="kind", native_enum=False, create_constraint=True, length=40),
            nullable=False,
        ),
        sa.Column("quality", sa.Integer(), nullable=False),
        sa.Column("since_epoch", sa.Integer(), nullable=False),
        sa.Column("locked", sa.JSON(), nullable=False),
        sa.CheckConstraint("quality BETWEEN 0 AND 100", name=op.f("ck_assistive_aids_quality_range")),
        sa.CheckConstraint("since_epoch >= 0", name=op.f("ck_assistive_aids_since_epoch_min")),
        sa.ForeignKeyConstraint(["holder_node_id"], ["nodes.id"], name=op.f("fk_assistive_aids_holder_node_id_nodes"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("holder_node_id", "kind", name=op.f("pk_assistive_aids")),
    )
    op.create_table(
        "incorporeal_rights",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("holder_node_id", sa.Integer(), nullable=False),
        sa.Column(
            "kind",
            sa.Enum(
                "song",
                "dance",
                "story",
                "rite",
                "design",
                "name",
                "title",
                "trademark",
                "market_privilege",
                name="kind",
                native_enum=False,
                create_constraint=True,
                length=40,
            ),
            nullable=False,
        ),
        sa.Column("subject_node_id", sa.Integer(), nullable=True),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column(
            "acquired",
            sa.Enum("created", "inherited", "bought", "licensed", "stolen", "granted", name="acquired", native_enum=False, create_constraint=True, length=40),
            nullable=False,
        ),
        sa.Column("licensed_to_node_id", sa.Integer(), nullable=True),
        sa.Column("since_epoch", sa.Integer(), nullable=False),
        sa.Column("locked", sa.JSON(), nullable=False),
        sa.CheckConstraint("since_epoch >= 0", name=op.f("ck_incorporeal_rights_since_epoch_min")),
        sa.ForeignKeyConstraint(["holder_node_id"], ["nodes.id"], name=op.f("fk_incorporeal_rights_holder_node_id_nodes"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["licensed_to_node_id"], ["nodes.id"], name=op.f("fk_incorporeal_rights_licensed_to_node_id_nodes"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["subject_node_id"], ["nodes.id"], name=op.f("fk_incorporeal_rights_subject_node_id_nodes"), ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_incorporeal_rights")),
    )
    with op.batch_alter_table("incorporeal_rights", schema=None) as batch_op:
        batch_op.create_index("ix_incorporeal_rights_holder", ["holder_node_id"], unique=False)
        batch_op.create_index(batch_op.f("ix_incorporeal_rights_subject_node_id"), ["subject_node_id"], unique=False)

    op.create_table(
        "sympathetic_links",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("holder_node_id", sa.Integer(), nullable=False),
        sa.Column("target_node_id", sa.Integer(), nullable=False),
        sa.Column(
            "token",
            sa.Enum("hair", "blood", "name", "portrait", "fragment", name="token", native_enum=False, create_constraint=True, length=40),
            nullable=False,
        ),
        sa.Column("strength", sa.Integer(), nullable=False),
        sa.Column("obtained_epoch", sa.Integer(), nullable=False),
        sa.Column("locked", sa.JSON(), nullable=False),
        sa.CheckConstraint("obtained_epoch >= 0", name=op.f("ck_sympathetic_links_obtained_epoch_min")),
        sa.CheckConstraint("strength BETWEEN 0 AND 100", name=op.f("ck_sympathetic_links_strength_range")),
        sa.ForeignKeyConstraint(["holder_node_id"], ["nodes.id"], name=op.f("fk_sympathetic_links_holder_node_id_nodes"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["target_node_id"], ["nodes.id"], name=op.f("fk_sympathetic_links_target_node_id_nodes"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_sympathetic_links")),
    )
    with op.batch_alter_table("sympathetic_links", schema=None) as batch_op:
        batch_op.create_index(batch_op.f("ix_sympathetic_links_holder_node_id"), ["holder_node_id"], unique=False)
        batch_op.create_index("ix_sympathetic_links_target", ["target_node_id"], unique=False)

    op.create_table(
        "catch_grounds",
        sa.Column("source_entity_id", sa.Integer(), nullable=False),
        sa.Column("region_entity_id", sa.Integer(), nullable=False),
        sa.Column(
            "ground",
            sa.Enum("fishery", "trapping", "fowling", "marine_hunt", name="ground", native_enum=False, create_constraint=True, length=40),
            nullable=False,
        ),
        sa.Column(
            "gear",
            sa.Enum("lines", "nets", "weirs", "traps", "snares", "harpoons", name="gear", native_enum=False, create_constraint=True, length=40),
            nullable=False,
        ),
        sa.Column("right", sa.Enum("commons", "owned", name="right", native_enum=False, create_constraint=True, length=40), nullable=False),
        sa.Column("owner_node_id", sa.Integer(), nullable=True),
        sa.Column("effort", sa.Integer(), nullable=False),
        sa.Column("collapse_at", sa.Integer(), nullable=False),
        sa.Column("collapsed", sa.Boolean(), nullable=False),
        sa.Column("last_catch", sa.Integer(), nullable=False),
        sa.Column("locked", sa.JSON(), nullable=False),
        sa.CheckConstraint("collapse_at BETWEEN 0 AND 100", name=op.f("ck_catch_grounds_collapse_at_range")),
        sa.CheckConstraint("effort BETWEEN 0 AND 100", name=op.f("ck_catch_grounds_effort_range")),
        sa.CheckConstraint("last_catch >= 0", name=op.f("ck_catch_grounds_last_catch_min")),
        sa.ForeignKeyConstraint(["owner_node_id"], ["nodes.id"], name=op.f("fk_catch_grounds_owner_node_id_nodes"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["region_entity_id"], ["entities.id"], name=op.f("fk_catch_grounds_region_entity_id_entities"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["source_entity_id"], ["entities.id"], name=op.f("fk_catch_grounds_source_entity_id_entities"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("source_entity_id", "region_entity_id", name=op.f("pk_catch_grounds")),
    )
    with op.batch_alter_table("catch_grounds", schema=None) as batch_op:
        batch_op.create_index(batch_op.f("ix_catch_grounds_region_entity_id"), ["region_entity_id"], unique=False)

    op.create_table(
        "chemical_works",
        sa.Column("settlement_entity_id", sa.Integer(), nullable=False),
        sa.Column(
            "product",
            sa.Enum(
                "dye",
                "soap",
                "mordant",
                "tanning",
                "fertiliser",
                "medicine",
                "incendiary",
                "explosive",
                name="product",
                native_enum=False,
                create_constraint=True,
                length=40,
            ),
            nullable=False,
        ),
        sa.Column("output", sa.Integer(), nullable=False),
        sa.Column("hazard", sa.Integer(), nullable=False),
        sa.Column("pollution", sa.Integer(), nullable=False),
        sa.Column("accidents", sa.Integer(), nullable=False),
        sa.Column("founded_epoch", sa.Integer(), nullable=False),
        sa.Column("locked", sa.JSON(), nullable=False),
        sa.CheckConstraint("accidents >= 0", name=op.f("ck_chemical_works_accidents_min")),
        sa.CheckConstraint("hazard BETWEEN 0 AND 100", name=op.f("ck_chemical_works_hazard_range")),
        sa.CheckConstraint("output BETWEEN 0 AND 100", name=op.f("ck_chemical_works_output_range")),
        sa.CheckConstraint("pollution BETWEEN 0 AND 100", name=op.f("ck_chemical_works_pollution_range")),
        sa.ForeignKeyConstraint(["settlement_entity_id"], ["entities.id"], name=op.f("fk_chemical_works_settlement_entity_id_entities"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("settlement_entity_id", "product", name=op.f("pk_chemical_works")),
    )
    op.create_table(
        "emotion_spirits",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("region_entity_id", sa.Integer(), nullable=False),
        sa.Column(
            "emotion",
            sa.Enum(
                "joy",
                "contentment",
                "pride",
                "love",
                "gratitude",
                "relief",
                "hope",
                "awe",
                "amusement",
                "fear",
                "anxiety",
                "anger",
                "rage",
                "grief",
                "sadness",
                "shame",
                "guilt",
                "envy",
                "jealousy",
                "disgust",
                "loneliness",
                "boredom",
                "despair",
                "longing",
                name="emotion",
                native_enum=False,
                create_constraint=True,
                length=40,
            ),
            nullable=False,
        ),
        sa.Column("strength", sa.Integer(), nullable=False),
        sa.Column("born_epoch", sa.Integer(), nullable=False),
        sa.Column("lifetime", sa.Integer(), nullable=False),
        sa.Column("bound_by_node_id", sa.Integer(), nullable=True),
        sa.Column("locked", sa.JSON(), nullable=False),
        sa.CheckConstraint("born_epoch >= 0", name=op.f("ck_emotion_spirits_born_epoch_min")),
        sa.CheckConstraint("lifetime >= 0", name=op.f("ck_emotion_spirits_lifetime_min")),
        sa.CheckConstraint("strength BETWEEN 0 AND 100", name=op.f("ck_emotion_spirits_strength_range")),
        sa.ForeignKeyConstraint(["bound_by_node_id"], ["nodes.id"], name=op.f("fk_emotion_spirits_bound_by_node_id_nodes"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["region_entity_id"], ["entities.id"], name=op.f("fk_emotion_spirits_region_entity_id_entities"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_emotion_spirits")),
    )
    with op.batch_alter_table("emotion_spirits", schema=None) as batch_op:
        batch_op.create_index(batch_op.f("ix_emotion_spirits_region_entity_id"), ["region_entity_id"], unique=False)

    op.create_table(
        "games",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column(
            "kind", sa.Enum("board", "dice", "cards", "ball", "wrestling", name="kind", native_enum=False, create_constraint=True, length=40), nullable=False
        ),
        sa.Column("rule", sa.Enum("strategy", "chance", "physical", name="rule", native_enum=False, create_constraint=True, length=40), nullable=False),
        sa.Column("origin_entity_id", sa.Integer(), nullable=True),
        sa.Column("created_epoch", sa.Integer(), nullable=False),
        sa.Column("locked", sa.JSON(), nullable=False),
        sa.CheckConstraint("created_epoch >= 0", name=op.f("ck_games_created_epoch_min")),
        sa.ForeignKeyConstraint(["origin_entity_id"], ["entities.id"], name=op.f("fk_games_origin_entity_id_entities"), ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_games")),
    )
    with op.batch_alter_table("games", schema=None) as batch_op:
        batch_op.create_index(batch_op.f("ix_games_origin_entity_id"), ["origin_entity_id"], unique=False)

    op.create_table(
        "insurance_policies",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("insurer_entity_id", sa.Integer(), nullable=False),
        sa.Column("holder_node_id", sa.Integer(), nullable=False),
        sa.Column("cover", sa.Enum("cargo", "house", "life", name="cover", native_enum=False, create_constraint=True, length=40), nullable=False),
        sa.Column("premium", sa.Integer(), nullable=False),
        sa.Column("sum_insured", sa.Integer(), nullable=False),
        sa.Column("active", sa.Boolean(), nullable=False),
        sa.Column("since_epoch", sa.Integer(), nullable=False),
        sa.Column("claims", sa.Integer(), nullable=False),
        sa.Column("locked", sa.JSON(), nullable=False),
        sa.CheckConstraint("claims >= 0", name=op.f("ck_insurance_policies_claims_min")),
        sa.CheckConstraint("premium >= 0", name=op.f("ck_insurance_policies_premium_min")),
        sa.CheckConstraint("sum_insured >= 0", name=op.f("ck_insurance_policies_sum_insured_min")),
        sa.ForeignKeyConstraint(["holder_node_id"], ["nodes.id"], name=op.f("fk_insurance_policies_holder_node_id_nodes"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["insurer_entity_id"], ["entities.id"], name=op.f("fk_insurance_policies_insurer_entity_id_entities"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_insurance_policies")),
    )
    with op.batch_alter_table("insurance_policies", schema=None) as batch_op:
        batch_op.create_index("ix_insurance_policies_holder", ["holder_node_id"], unique=False)
        batch_op.create_index(batch_op.f("ix_insurance_policies_insurer_entity_id"), ["insurer_entity_id"], unique=False)

    op.create_table(
        "insurers",
        sa.Column("insurer_entity_id", sa.Integer(), nullable=False),
        sa.Column("pool", sa.Integer(), nullable=False),
        sa.Column("risk_belief", sa.Integer(), nullable=False),
        sa.Column("premium_pct", sa.Integer(), nullable=False),
        sa.Column("ruined", sa.Boolean(), nullable=False),
        sa.Column("claims_seen", sa.Integer(), nullable=False),
        sa.Column("locked", sa.JSON(), nullable=False),
        sa.CheckConstraint("claims_seen >= 0", name=op.f("ck_insurers_claims_seen_min")),
        sa.CheckConstraint("premium_pct BETWEEN 0 AND 100", name=op.f("ck_insurers_premium_pct_range")),
        sa.CheckConstraint("risk_belief BETWEEN 0 AND 100", name=op.f("ck_insurers_risk_belief_range")),
        sa.ForeignKeyConstraint(["insurer_entity_id"], ["entities.id"], name=op.f("fk_insurers_insurer_entity_id_entities"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("insurer_entity_id", name=op.f("pk_insurers")),
    )
    op.create_table(
        "number_systems",
        sa.Column("people_entity_id", sa.Integer(), nullable=False),
        sa.Column("base", sa.Integer(), nullable=False),
        sa.Column("notation", sa.Enum("additive", "positional", name="notation", native_enum=False, create_constraint=True, length=40), nullable=False),
        sa.Column("zero", sa.Boolean(), nullable=False),
        sa.Column("numeracy", sa.Integer(), nullable=False),
        sa.Column("locked", sa.JSON(), nullable=False),
        sa.CheckConstraint("base BETWEEN 2 AND 60", name=op.f("ck_number_systems_base_range")),
        sa.CheckConstraint("numeracy BETWEEN 0 AND 100", name=op.f("ck_number_systems_numeracy_range")),
        sa.ForeignKeyConstraint(["people_entity_id"], ["entities.id"], name=op.f("fk_number_systems_people_entity_id_entities"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("people_entity_id", name=op.f("pk_number_systems")),
    )
    op.create_table(
        "public_clocks",
        sa.Column("settlement_entity_id", sa.Integer(), nullable=False),
        sa.Column(
            "kind",
            sa.Enum(
                "sundial",
                "water_clock",
                "sand_glass",
                "candle_clock",
                "mechanical",
                "astronomical",
                name="kind",
                native_enum=False,
                create_constraint=True,
                length=40,
            ),
            nullable=False,
        ),
        sa.Column("precision", sa.Integer(), nullable=False),
        sa.Column("built_epoch", sa.Integer(), nullable=False),
        sa.Column("locked", sa.JSON(), nullable=False),
        sa.CheckConstraint("built_epoch >= 0", name=op.f("ck_public_clocks_built_epoch_min")),
        sa.CheckConstraint("precision BETWEEN 0 AND 100", name=op.f("ck_public_clocks_precision_range")),
        sa.ForeignKeyConstraint(["settlement_entity_id"], ["entities.id"], name=op.f("fk_public_clocks_settlement_entity_id_entities"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("settlement_entity_id", name=op.f("pk_public_clocks")),
    )
    op.create_table(
        "game_followings",
        sa.Column("people_entity_id", sa.Integer(), nullable=False),
        sa.Column("game_id", sa.Integer(), nullable=False),
        sa.Column("popularity", sa.Integer(), nullable=False),
        sa.Column("adopted_epoch", sa.Integer(), nullable=False),
        sa.Column("locked", sa.JSON(), nullable=False),
        sa.CheckConstraint("adopted_epoch >= 0", name=op.f("ck_game_followings_adopted_epoch_min")),
        sa.CheckConstraint("popularity BETWEEN 0 AND 100", name=op.f("ck_game_followings_popularity_range")),
        sa.ForeignKeyConstraint(["game_id"], ["games.id"], name=op.f("fk_game_followings_game_id_games"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["people_entity_id"], ["entities.id"], name=op.f("fk_game_followings_people_entity_id_entities"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("people_entity_id", "game_id", name=op.f("pk_game_followings")),
    )
    op.create_table(
        "material_affinities",
        sa.Column("material_id", sa.Integer(), nullable=False),
        sa.Column(
            "school",
            sa.Enum(
                "elemental_fire",
                "elemental_water",
                "earth",
                "storm",
                "life",
                "death",
                "mind",
                "illusion",
                "divination",
                "warding",
                "binding",
                "summoning",
                "blood",
                "void",
                name="school",
                native_enum=False,
                create_constraint=True,
                length=40,
            ),
            nullable=False,
        ),
        sa.Column(
            "mode", sa.Enum("consumed", "worn", "inscribed", "ground", name="mode", native_enum=False, create_constraint=True, length=40), nullable=False
        ),
        sa.Column("power", sa.Integer(), nullable=False),
        sa.Column("locked", sa.JSON(), nullable=False),
        sa.CheckConstraint("power BETWEEN 0 AND 100", name=op.f("ck_material_affinities_power_range")),
        sa.ForeignKeyConstraint(["material_id"], ["world_materials.id"], name=op.f("fk_material_affinities_material_id_world_materials"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("material_id", "school", name=op.f("pk_material_affinities")),
    )


def downgrade() -> None:
    op.drop_table("material_affinities")
    op.drop_table("game_followings")
    op.drop_table("public_clocks")
    op.drop_table("number_systems")
    op.drop_table("insurers")
    with op.batch_alter_table("insurance_policies", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_insurance_policies_insurer_entity_id"))
        batch_op.drop_index("ix_insurance_policies_holder")

    op.drop_table("insurance_policies")
    with op.batch_alter_table("games", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_games_origin_entity_id"))

    op.drop_table("games")
    with op.batch_alter_table("emotion_spirits", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_emotion_spirits_region_entity_id"))

    op.drop_table("emotion_spirits")
    op.drop_table("chemical_works")
    with op.batch_alter_table("catch_grounds", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_catch_grounds_region_entity_id"))

    op.drop_table("catch_grounds")
    with op.batch_alter_table("sympathetic_links", schema=None) as batch_op:
        batch_op.drop_index("ix_sympathetic_links_target")
        batch_op.drop_index(batch_op.f("ix_sympathetic_links_holder_node_id"))

    op.drop_table("sympathetic_links")
    with op.batch_alter_table("incorporeal_rights", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_incorporeal_rights_subject_node_id"))
        batch_op.drop_index("ix_incorporeal_rights_holder")

    op.drop_table("incorporeal_rights")
    op.drop_table("assistive_aids")
