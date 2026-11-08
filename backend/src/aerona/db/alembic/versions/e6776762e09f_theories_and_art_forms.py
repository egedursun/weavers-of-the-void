import sqlalchemy as sa
from alembic import op

revision = "e6776762e09f"
down_revision = "5e02eb948261"
branch_labels = None
depends_on = None

OLD_TYPES = (
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
    "title",
    "ideology",
    "rite",
    "beast",
)
NEW_TYPES = (*OLD_TYPES, "theory", "art_form")
TYPED = (("entities", "entity_type", False), ("son_powers", "param_entity_type", True))


def widen(old: bool) -> None:
    before, after = (NEW_TYPES, OLD_TYPES) if old else (OLD_TYPES, NEW_TYPES)
    for table, column, nullable in TYPED:
        with op.batch_alter_table(table, schema=None) as batch_op:
            batch_op.alter_column(
                column,
                existing_type=sa.Enum(*before, name=column, native_enum=False, create_constraint=True, length=40),
                type_=sa.Enum(*after, name=column, native_enum=False, create_constraint=True, length=40),
                existing_nullable=nullable,
            )


def upgrade() -> None:
    widen(old=False)
    op.create_table(
        "art_form_practitioners",
        sa.Column("art_form_entity_id", sa.Integer(), nullable=False),
        sa.Column("practitioner_entity_id", sa.Integer(), nullable=False),
        sa.Column("mastery", sa.Integer(), nullable=False),
        sa.Column("since_epoch", sa.Integer(), nullable=False),
        sa.Column("locked", sa.JSON(), nullable=False),
        sa.CheckConstraint("mastery BETWEEN 0 AND 100", name=op.f("ck_art_form_practitioners_mastery_range")),
        sa.CheckConstraint("since_epoch >= 0", name=op.f("ck_art_form_practitioners_since_epoch_min")),
        sa.ForeignKeyConstraint(
            ["art_form_entity_id"], ["entities.id"], name=op.f("fk_art_form_practitioners_art_form_entity_id_entities"), ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["practitioner_entity_id"], ["entities.id"], name=op.f("fk_art_form_practitioners_practitioner_entity_id_entities"), ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("art_form_entity_id", "practitioner_entity_id", name=op.f("pk_art_form_practitioners")),
    )
    with op.batch_alter_table("art_form_practitioners", schema=None) as batch_op:
        batch_op.create_index("ix_art_form_practitioners_who", ["practitioner_entity_id"], unique=False)

    op.create_table(
        "art_form_profiles",
        sa.Column("art_form_entity_id", sa.Integer(), nullable=False),
        sa.Column(
            "discipline",
            sa.Enum(
                "music",
                "poetry",
                "dance",
                "theatre",
                "painting",
                "sculpture",
                "architecture_style",
                "textile",
                "calligraphy",
                name="discipline",
                native_enum=False,
                create_constraint=True,
                length=40,
            ),
            nullable=False,
        ),
        sa.Column("structure", sa.JSON(), nullable=False),
        sa.Column("origin_culture_id", sa.Integer(), nullable=True),
        sa.Column("founder_entity_id", sa.Integer(), nullable=True),
        sa.Column("language_entity_id", sa.Integer(), nullable=True),
        sa.Column("difficulty", sa.Integer(), nullable=False),
        sa.Column("prestige", sa.Integer(), nullable=False),
        sa.Column("sacred", sa.Boolean(), nullable=False),
        sa.Column("notation", sa.Boolean(), nullable=False),
        sa.Column("occasions", sa.JSON(), nullable=False),
        sa.Column("parent_ids", sa.JSON(), nullable=False),
        sa.Column("updated_epoch", sa.Integer(), nullable=False),
        sa.Column("locked", sa.JSON(), nullable=False),
        sa.CheckConstraint("difficulty BETWEEN 0 AND 100", name=op.f("ck_art_form_profiles_difficulty_range")),
        sa.CheckConstraint("prestige BETWEEN 0 AND 100", name=op.f("ck_art_form_profiles_prestige_range")),
        sa.ForeignKeyConstraint(["art_form_entity_id"], ["entities.id"], name=op.f("fk_art_form_profiles_art_form_entity_id_entities"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["founder_entity_id"], ["entities.id"], name=op.f("fk_art_form_profiles_founder_entity_id_entities"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["language_entity_id"], ["entities.id"], name=op.f("fk_art_form_profiles_language_entity_id_entities"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["origin_culture_id"], ["entities.id"], name=op.f("fk_art_form_profiles_origin_culture_id_entities"), ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("art_form_entity_id", name=op.f("pk_art_form_profiles")),
    )
    op.create_table(
        "epithets",
        sa.Column("mortal_entity_id", sa.Integer(), nullable=False),
        sa.Column("epithet", sa.String(length=200), nullable=False),
        sa.Column("gloss", sa.Text(), nullable=False),
        sa.Column("deed", sa.String(length=120), nullable=False),
        sa.Column("language_entity_id", sa.Integer(), nullable=True),
        sa.Column("epoch", sa.Integer(), nullable=False),
        sa.Column("locked", sa.JSON(), nullable=False),
        sa.CheckConstraint("epoch >= 0", name=op.f("ck_epithets_epoch_min")),
        sa.ForeignKeyConstraint(["language_entity_id"], ["entities.id"], name=op.f("fk_epithets_language_entity_id_entities"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["mortal_entity_id"], ["entities.id"], name=op.f("fk_epithets_mortal_entity_id_entities"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("mortal_entity_id", name=op.f("pk_epithets")),
    )
    op.create_table(
        "name_exonyms",
        sa.Column("node_id", sa.Integer(), nullable=False),
        sa.Column("language_entity_id", sa.Integer(), nullable=False),
        sa.Column("form", sa.String(length=200), nullable=False),
        sa.Column("gloss", sa.Text(), nullable=False),
        sa.Column("epoch", sa.Integer(), nullable=False),
        sa.Column("locked", sa.JSON(), nullable=False),
        sa.CheckConstraint("epoch >= 0", name=op.f("ck_name_exonyms_epoch_min")),
        sa.ForeignKeyConstraint(["language_entity_id"], ["entities.id"], name=op.f("fk_name_exonyms_language_entity_id_entities"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["node_id"], ["nodes.id"], name=op.f("fk_name_exonyms_node_id_nodes"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("node_id", "language_entity_id", name=op.f("pk_name_exonyms")),
    )
    with op.batch_alter_table("name_exonyms", schema=None) as batch_op:
        batch_op.create_index("ix_name_exonyms_language", ["language_entity_id"], unique=False)

    op.create_table(
        "name_meanings",
        sa.Column("node_id", sa.Integer(), nullable=False),
        sa.Column("language_entity_id", sa.Integer(), nullable=True),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("gloss", sa.Text(), nullable=False),
        sa.Column("morphemes", sa.JSON(), nullable=False),
        sa.Column("epoch", sa.Integer(), nullable=False),
        sa.Column("locked", sa.JSON(), nullable=False),
        sa.CheckConstraint("epoch >= 0", name=op.f("ck_name_meanings_epoch_min")),
        sa.ForeignKeyConstraint(["language_entity_id"], ["entities.id"], name=op.f("fk_name_meanings_language_entity_id_entities"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["node_id"], ["nodes.id"], name=op.f("fk_name_meanings_node_id_nodes"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("node_id", name=op.f("pk_name_meanings")),
    )
    op.create_table(
        "paradigm_shifts",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("community_entity_id", sa.Integer(), nullable=False),
        sa.Column(
            "domain",
            sa.Enum(
                "medicine",
                "cosmology",
                "matter",
                "life",
                "mind",
                "magic",
                "history",
                "society",
                name="domain",
                native_enum=False,
                create_constraint=True,
                length=40,
            ),
            nullable=False,
        ),
        sa.Column("old_theory_id", sa.Integer(), nullable=True),
        sa.Column("new_theory_id", sa.Integer(), nullable=True),
        sa.Column("epoch", sa.Integer(), nullable=False),
        sa.CheckConstraint("epoch >= 0", name=op.f("ck_paradigm_shifts_epoch_min")),
        sa.ForeignKeyConstraint(["community_entity_id"], ["entities.id"], name=op.f("fk_paradigm_shifts_community_entity_id_entities"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["new_theory_id"], ["entities.id"], name=op.f("fk_paradigm_shifts_new_theory_id_entities"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["old_theory_id"], ["entities.id"], name=op.f("fk_paradigm_shifts_old_theory_id_entities"), ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_paradigm_shifts")),
    )
    with op.batch_alter_table("paradigm_shifts", schema=None) as batch_op:
        batch_op.create_index("ix_paradigm_shifts_community", ["community_entity_id", "epoch"], unique=False)

    op.create_table(
        "theory_adherents",
        sa.Column("theory_entity_id", sa.Integer(), nullable=False),
        sa.Column("adherent_entity_id", sa.Integer(), nullable=False),
        sa.Column("strength", sa.Integer(), nullable=False),
        sa.Column("orthodox", sa.Boolean(), nullable=False),
        sa.Column("since_epoch", sa.Integer(), nullable=False),
        sa.Column("locked", sa.JSON(), nullable=False),
        sa.CheckConstraint("since_epoch >= 0", name=op.f("ck_theory_adherents_since_epoch_min")),
        sa.CheckConstraint("strength BETWEEN 0 AND 100", name=op.f("ck_theory_adherents_strength_range")),
        sa.ForeignKeyConstraint(["adherent_entity_id"], ["entities.id"], name=op.f("fk_theory_adherents_adherent_entity_id_entities"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["theory_entity_id"], ["entities.id"], name=op.f("fk_theory_adherents_theory_entity_id_entities"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("theory_entity_id", "adherent_entity_id", name=op.f("pk_theory_adherents")),
    )
    with op.batch_alter_table("theory_adherents", schema=None) as batch_op:
        batch_op.create_index("ix_theory_adherents_adherent", ["adherent_entity_id"], unique=False)

    op.create_table(
        "theory_anomalies",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("theory_entity_id", sa.Integer(), nullable=False),
        sa.Column(
            "kind",
            sa.Enum("failed_prediction", "contrary_cure", "observation", "divine_sign", name="kind", native_enum=False, create_constraint=True, length=40),
            nullable=False,
        ),
        sa.Column("weight", sa.Integer(), nullable=False),
        sa.Column("witness_entity_id", sa.Integer(), nullable=True),
        sa.Column("epoch", sa.Integer(), nullable=False),
        sa.CheckConstraint("epoch >= 0", name=op.f("ck_theory_anomalies_epoch_min")),
        sa.CheckConstraint("weight >= 0", name=op.f("ck_theory_anomalies_weight_min")),
        sa.ForeignKeyConstraint(["theory_entity_id"], ["entities.id"], name=op.f("fk_theory_anomalies_theory_entity_id_entities"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["witness_entity_id"], ["entities.id"], name=op.f("fk_theory_anomalies_witness_entity_id_entities"), ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_theory_anomalies")),
    )
    with op.batch_alter_table("theory_anomalies", schema=None) as batch_op:
        batch_op.create_index("ix_theory_anomalies_theory", ["theory_entity_id", "epoch"], unique=False)

    op.create_table(
        "theory_profiles",
        sa.Column("theory_entity_id", sa.Integer(), nullable=False),
        sa.Column(
            "domain",
            sa.Enum(
                "medicine",
                "cosmology",
                "matter",
                "life",
                "mind",
                "magic",
                "history",
                "society",
                name="domain",
                native_enum=False,
                create_constraint=True,
                length=40,
            ),
            nullable=False,
        ),
        sa.Column("claim", sa.Text(), nullable=False),
        sa.Column("correctness", sa.Integer(), nullable=False),
        sa.Column("explanatory_power", sa.Integer(), nullable=False),
        sa.Column("founder_entity_id", sa.Integer(), nullable=True),
        sa.Column("founding_book_id", sa.Integer(), nullable=True),
        sa.Column("rival_entity_id", sa.Integer(), nullable=True),
        sa.Column("endorsed_by", sa.JSON(), nullable=False),
        sa.Column("condemned_by", sa.JSON(), nullable=False),
        sa.Column("revealed_by_son_id", sa.Integer(), nullable=True),
        sa.Column("updated_epoch", sa.Integer(), nullable=False),
        sa.Column("locked", sa.JSON(), nullable=False),
        sa.CheckConstraint("correctness BETWEEN 0 AND 100", name=op.f("ck_theory_profiles_correctness_range")),
        sa.CheckConstraint("explanatory_power BETWEEN 0 AND 100", name=op.f("ck_theory_profiles_explanatory_power_range")),
        sa.ForeignKeyConstraint(["founder_entity_id"], ["entities.id"], name=op.f("fk_theory_profiles_founder_entity_id_entities"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["founding_book_id"], ["entities.id"], name=op.f("fk_theory_profiles_founding_book_id_entities"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["revealed_by_son_id"], ["sons.id"], name=op.f("fk_theory_profiles_revealed_by_son_id_sons"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["rival_entity_id"], ["entities.id"], name=op.f("fk_theory_profiles_rival_entity_id_entities"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["theory_entity_id"], ["entities.id"], name=op.f("fk_theory_profiles_theory_entity_id_entities"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("theory_entity_id", name=op.f("pk_theory_profiles")),
    )
    with op.batch_alter_table("artwork_profiles", schema=None) as batch_op:
        batch_op.add_column(sa.Column("art_form_entity_id", sa.Integer(), nullable=True))
        batch_op.create_foreign_key(
            batch_op.f("fk_artwork_profiles_art_form_entity_id_entities"), "entities", ["art_form_entity_id"], ["id"], ondelete="SET NULL"
        )


def downgrade() -> None:
    widen(old=True)
    with op.batch_alter_table("artwork_profiles", schema=None) as batch_op:
        batch_op.drop_constraint(batch_op.f("fk_artwork_profiles_art_form_entity_id_entities"), type_="foreignkey")
        batch_op.drop_column("art_form_entity_id")

    op.drop_table("theory_profiles")
    with op.batch_alter_table("theory_anomalies", schema=None) as batch_op:
        batch_op.drop_index("ix_theory_anomalies_theory")

    op.drop_table("theory_anomalies")
    with op.batch_alter_table("theory_adherents", schema=None) as batch_op:
        batch_op.drop_index("ix_theory_adherents_adherent")

    op.drop_table("theory_adherents")
    with op.batch_alter_table("paradigm_shifts", schema=None) as batch_op:
        batch_op.drop_index("ix_paradigm_shifts_community")

    op.drop_table("paradigm_shifts")
    op.drop_table("name_meanings")
    with op.batch_alter_table("name_exonyms", schema=None) as batch_op:
        batch_op.drop_index("ix_name_exonyms_language")

    op.drop_table("name_exonyms")
    op.drop_table("epithets")
    op.drop_table("art_form_profiles")
    with op.batch_alter_table("art_form_practitioners", schema=None) as batch_op:
        batch_op.drop_index("ix_art_form_practitioners_who")

    op.drop_table("art_form_practitioners")
