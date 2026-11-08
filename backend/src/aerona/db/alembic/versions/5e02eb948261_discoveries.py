import sqlalchemy as sa
from alembic import op

revision = "5e02eb948261"
down_revision = "808e16b8c9ee"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "world_eras",
        sa.Column("world_id", sa.Integer(), nullable=False),
        sa.Column("era", sa.Integer(), nullable=False),
        sa.Column("since_epoch", sa.Integer(), nullable=False),
        sa.Column("locked", sa.JSON(), nullable=False),
        sa.CheckConstraint("era >= 1", name=op.f("ck_world_eras_era_min")),
        sa.CheckConstraint("since_epoch >= 0", name=op.f("ck_world_eras_since_epoch_min")),
        sa.ForeignKeyConstraint(["world_id"], ["worlds.id"], name=op.f("fk_world_eras_world_id_worlds"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("world_id", name=op.f("pk_world_eras")),
    )
    op.create_table(
        "artifact_studies",
        sa.Column("holder_entity_id", sa.Integer(), nullable=False),
        sa.Column("item_entity_id", sa.Integer(), nullable=False),
        sa.Column(
            "technique",
            sa.Enum(
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
                name="technique",
                native_enum=False,
                create_constraint=True,
                length=40,
            ),
            nullable=False,
        ),
        sa.Column("progress", sa.Integer(), nullable=False),
        sa.Column("epoch", sa.Integer(), nullable=False),
        sa.Column("locked", sa.JSON(), nullable=False),
        sa.CheckConstraint("epoch >= 0", name=op.f("ck_artifact_studies_epoch_min")),
        sa.CheckConstraint("progress BETWEEN 0 AND 100", name=op.f("ck_artifact_studies_progress_range")),
        sa.ForeignKeyConstraint(["holder_entity_id"], ["entities.id"], name=op.f("fk_artifact_studies_holder_entity_id_entities"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["item_entity_id"], ["entities.id"], name=op.f("fk_artifact_studies_item_entity_id_entities"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("holder_entity_id", "item_entity_id", name=op.f("pk_artifact_studies")),
    )
    with op.batch_alter_table("artifact_studies", schema=None) as batch_op:
        batch_op.create_index("ix_artifact_studies_item", ["item_entity_id"], unique=False)

    op.create_table(
        "banned_works",
        sa.Column("polity_entity_id", sa.Integer(), nullable=False),
        sa.Column("work_entity_id", sa.Integer(), nullable=False),
        sa.Column("since_epoch", sa.Integer(), nullable=False),
        sa.Column("locked", sa.JSON(), nullable=False),
        sa.CheckConstraint("since_epoch >= 0", name=op.f("ck_banned_works_since_epoch_min")),
        sa.ForeignKeyConstraint(["polity_entity_id"], ["entities.id"], name=op.f("fk_banned_works_polity_entity_id_entities"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["work_entity_id"], ["entities.id"], name=op.f("fk_banned_works_work_entity_id_entities"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("polity_entity_id", "work_entity_id", name=op.f("pk_banned_works")),
    )
    with op.batch_alter_table("banned_works", schema=None) as batch_op:
        batch_op.create_index("ix_banned_works_work", ["work_entity_id"], unique=False)

    op.create_table(
        "blueprints",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column(
            "kind",
            sa.Enum("vessel", "siege_engine", "structure", "artifact_pattern", name="kind", native_enum=False, create_constraint=True, length=40),
            nullable=False,
        ),
        sa.Column("subject", sa.String(length=120), nullable=False),
        sa.Column("holder_node_id", sa.Integer(), nullable=False),
        sa.Column("book_entity_id", sa.Integer(), nullable=True),
        sa.Column("origin_node_id", sa.Integer(), nullable=True),
        sa.Column(
            "source",
            sa.Enum("drawn", "stolen", "traded", "licensed", "granted", name="source", native_enum=False, create_constraint=True, length=40),
            nullable=False,
        ),
        sa.Column("licensed_to", sa.JSON(), nullable=False),
        sa.Column("quality", sa.Integer(), nullable=False),
        sa.Column("since_epoch", sa.Integer(), nullable=False),
        sa.Column("locked", sa.JSON(), nullable=False),
        sa.CheckConstraint("quality BETWEEN 0 AND 100", name=op.f("ck_blueprints_quality_range")),
        sa.CheckConstraint("since_epoch >= 0", name=op.f("ck_blueprints_since_epoch_min")),
        sa.ForeignKeyConstraint(["book_entity_id"], ["entities.id"], name=op.f("fk_blueprints_book_entity_id_entities"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["holder_node_id"], ["nodes.id"], name=op.f("fk_blueprints_holder_node_id_nodes"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["origin_node_id"], ["nodes.id"], name=op.f("fk_blueprints_origin_node_id_nodes"), ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_blueprints")),
    )
    with op.batch_alter_table("blueprints", schema=None) as batch_op:
        batch_op.create_index("ix_blueprints_holder", ["holder_node_id"], unique=False)

    op.create_table(
        "era_deeds",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("polity_entity_id", sa.Integer(), nullable=False),
        sa.Column(
            "deed",
            sa.Enum(
                "first_technique",
                "first_institution",
                "great_victory",
                "wonder",
                "great_person",
                "defeat",
                "famine",
                name="deed",
                native_enum=False,
                create_constraint=True,
                length=40,
            ),
            nullable=False,
        ),
        sa.Column("points", sa.Integer(), nullable=False),
        sa.Column("epoch", sa.Integer(), nullable=False),
        sa.Column("subject_node_id", sa.Integer(), nullable=True),
        sa.CheckConstraint("epoch >= 0", name=op.f("ck_era_deeds_epoch_min")),
        sa.ForeignKeyConstraint(["polity_entity_id"], ["entities.id"], name=op.f("fk_era_deeds_polity_entity_id_entities"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["subject_node_id"], ["nodes.id"], name=op.f("fk_era_deeds_subject_node_id_nodes"), ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_era_deeds")),
    )
    with op.batch_alter_table("era_deeds", schema=None) as batch_op:
        batch_op.create_index("ix_era_deeds_polity", ["polity_entity_id", "epoch"], unique=False)

    op.create_table(
        "great_people",
        sa.Column("mortal_entity_id", sa.Integer(), nullable=False),
        sa.Column(
            "field",
            sa.Enum(
                "scholar",
                "artist",
                "general",
                "prophet",
                "engineer",
                "merchant",
                "explorer",
                name="field",
                native_enum=False,
                create_constraint=True,
                length=40,
            ),
            nullable=False,
        ),
        sa.Column("holder_entity_id", sa.Integer(), nullable=True),
        sa.Column("promoted_epoch", sa.Integer(), nullable=False),
        sa.Column("deed_done", sa.Boolean(), nullable=False),
        sa.Column("deed_epoch", sa.Integer(), nullable=True),
        sa.Column("locked", sa.JSON(), nullable=False),
        sa.CheckConstraint("promoted_epoch >= 0", name=op.f("ck_great_people_promoted_epoch_min")),
        sa.ForeignKeyConstraint(["holder_entity_id"], ["entities.id"], name=op.f("fk_great_people_holder_entity_id_entities"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["mortal_entity_id"], ["entities.id"], name=op.f("fk_great_people_mortal_entity_id_entities"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("mortal_entity_id", name=op.f("pk_great_people")),
    )
    with op.batch_alter_table("great_people", schema=None) as batch_op:
        batch_op.create_index("ix_great_people_holder", ["holder_entity_id"], unique=False)

    op.create_table(
        "great_person_points",
        sa.Column("holder_entity_id", sa.Integer(), nullable=False),
        sa.Column(
            "field",
            sa.Enum(
                "scholar",
                "artist",
                "general",
                "prophet",
                "engineer",
                "merchant",
                "explorer",
                name="field",
                native_enum=False,
                create_constraint=True,
                length=40,
            ),
            nullable=False,
        ),
        sa.Column("points", sa.Integer(), nullable=False),
        sa.Column("updated_epoch", sa.Integer(), nullable=False),
        sa.Column("locked", sa.JSON(), nullable=False),
        sa.CheckConstraint("points >= 0", name=op.f("ck_great_person_points_points_min")),
        sa.CheckConstraint("updated_epoch >= 0", name=op.f("ck_great_person_points_updated_epoch_min")),
        sa.ForeignKeyConstraint(["holder_entity_id"], ["entities.id"], name=op.f("fk_great_person_points_holder_entity_id_entities"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("holder_entity_id", "field", name=op.f("pk_great_person_points")),
    )
    op.create_table(
        "polity_eras",
        sa.Column("polity_entity_id", sa.Integer(), nullable=False),
        sa.Column("score", sa.Integer(), nullable=False),
        sa.Column("age", sa.Enum("normal", "golden", "dark", "heroic", name="age", native_enum=False, create_constraint=True, length=40), nullable=False),
        sa.Column("since_epoch", sa.Integer(), nullable=False),
        sa.Column("lowest", sa.Integer(), nullable=False),
        sa.Column("locked", sa.JSON(), nullable=False),
        sa.CheckConstraint("score BETWEEN -1000 AND 1000", name=op.f("ck_polity_eras_score_range")),
        sa.CheckConstraint("since_epoch >= 0", name=op.f("ck_polity_eras_since_epoch_min")),
        sa.ForeignKeyConstraint(["polity_entity_id"], ["entities.id"], name=op.f("fk_polity_eras_polity_entity_id_entities"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("polity_entity_id", name=op.f("pk_polity_eras")),
    )
    op.create_table(
        "research_incidents",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("holder_entity_id", sa.Integer(), nullable=False),
        sa.Column(
            "kind",
            sa.Enum(
                "leak",
                "released_beast",
                "plague",
                "backlash",
                "fire",
                "explosion",
                "poisoning",
                "summoning_gone_wrong",
                name="kind",
                native_enum=False,
                create_constraint=True,
                length=40,
            ),
            nullable=False,
        ),
        sa.Column(
            "technique",
            sa.Enum(
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
                name="technique",
                native_enum=False,
                create_constraint=True,
                length=40,
            ),
            nullable=True,
        ),
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
                "civics",
                name="branch",
                native_enum=False,
                create_constraint=True,
                length=40,
            ),
            nullable=True,
        ),
        sa.Column("severity", sa.Integer(), nullable=False),
        sa.Column("dead", sa.Integer(), nullable=False),
        sa.Column("epoch", sa.Integer(), nullable=False),
        sa.CheckConstraint("dead >= 0", name=op.f("ck_research_incidents_dead_min")),
        sa.CheckConstraint("epoch >= 0", name=op.f("ck_research_incidents_epoch_min")),
        sa.CheckConstraint("severity BETWEEN 0 AND 100", name=op.f("ck_research_incidents_severity_range")),
        sa.ForeignKeyConstraint(["holder_entity_id"], ["entities.id"], name=op.f("fk_research_incidents_holder_entity_id_entities"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_research_incidents")),
    )
    with op.batch_alter_table("research_incidents", schema=None) as batch_op:
        batch_op.create_index("ix_research_incidents_holder", ["holder_entity_id", "epoch"], unique=False)

    with op.batch_alter_table("community_methods", schema=None) as batch_op:
        batch_op.add_column(sa.Column("obsolete_since", sa.Integer(), nullable=True))

    with op.batch_alter_table("structure_profiles", schema=None) as batch_op:
        batch_op.add_column(sa.Column("obsolete_since", sa.Integer(), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("structure_profiles", schema=None) as batch_op:
        batch_op.drop_column("obsolete_since")

    with op.batch_alter_table("community_methods", schema=None) as batch_op:
        batch_op.drop_column("obsolete_since")

    with op.batch_alter_table("research_incidents", schema=None) as batch_op:
        batch_op.drop_index("ix_research_incidents_holder")

    op.drop_table("research_incidents")
    op.drop_table("polity_eras")
    op.drop_table("great_person_points")
    with op.batch_alter_table("great_people", schema=None) as batch_op:
        batch_op.drop_index("ix_great_people_holder")

    op.drop_table("great_people")
    with op.batch_alter_table("era_deeds", schema=None) as batch_op:
        batch_op.drop_index("ix_era_deeds_polity")

    op.drop_table("era_deeds")
    with op.batch_alter_table("blueprints", schema=None) as batch_op:
        batch_op.drop_index("ix_blueprints_holder")

    op.drop_table("blueprints")
    with op.batch_alter_table("banned_works", schema=None) as batch_op:
        batch_op.drop_index("ix_banned_works_work")

    op.drop_table("banned_works")
    with op.batch_alter_table("artifact_studies", schema=None) as batch_op:
        batch_op.drop_index("ix_artifact_studies_item")

    op.drop_table("artifact_studies")
    op.drop_table("world_eras")
