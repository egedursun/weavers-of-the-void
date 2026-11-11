import sqlalchemy as sa
from alembic import op

OLD_SYSTEMS = ("alphabet", "syllabary", "pictographic", "knot", "notch")
NEW_SYSTEMS = (*OLD_SYSTEMS, "logographic", "mixed", "abjad")


def systems(values: tuple[str, ...]) -> sa.Enum:
    return sa.Enum(*values, name="writing_system", native_enum=False, create_constraint=True, length=40)


revision = "8e98c75f797c"
down_revision = "09d7dc547388"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "decipher_works",
        sa.Column("language_entity_id", sa.Integer(), nullable=False),
        sa.Column("progress", sa.Integer(), nullable=False),
        sa.Column("corpus", sa.Integer(), nullable=False),
        sa.Column("bilingual", sa.Boolean(), nullable=False),
        sa.Column("errors", sa.Integer(), nullable=False),
        sa.Column("scholar_entity_id", sa.Integer(), nullable=True),
        sa.Column("started_epoch", sa.Integer(), nullable=False),
        sa.Column("updated_epoch", sa.Integer(), nullable=False),
        sa.Column("locked", sa.JSON(), nullable=False),
        sa.CheckConstraint("corpus >= 0", name=op.f("ck_decipher_works_corpus_min")),
        sa.CheckConstraint("errors >= 0", name=op.f("ck_decipher_works_errors_min")),
        sa.CheckConstraint("progress BETWEEN 0 AND 100", name=op.f("ck_decipher_works_progress_range")),
        sa.CheckConstraint("started_epoch >= 0", name=op.f("ck_decipher_works_started_epoch_min")),
        sa.ForeignKeyConstraint(["language_entity_id"], ["entities.id"], name=op.f("fk_decipher_works_language_entity_id_entities"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["scholar_entity_id"], ["entities.id"], name=op.f("fk_decipher_works_scholar_entity_id_entities"), ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("language_entity_id", name=op.f("pk_decipher_works")),
    )
    op.create_table(
        "divine_tongues",
        sa.Column("god_node_id", sa.Integer(), nullable=False),
        sa.Column("language_entity_id", sa.Integer(), nullable=False),
        sa.Column("since_epoch", sa.Integer(), nullable=False),
        sa.Column("locked", sa.JSON(), nullable=False),
        sa.CheckConstraint("since_epoch >= 0", name=op.f("ck_divine_tongues_since_epoch_min")),
        sa.ForeignKeyConstraint(["god_node_id"], ["nodes.id"], name=op.f("fk_divine_tongues_god_node_id_nodes"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["language_entity_id"], ["entities.id"], name=op.f("fk_divine_tongues_language_entity_id_entities"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("god_node_id", name=op.f("pk_divine_tongues")),
        sa.UniqueConstraint("language_entity_id", name=op.f("uq_divine_tongues_language_entity_id")),
    )
    op.create_table(
        "language_grammar",
        sa.Column("language_entity_id", sa.Integer(), nullable=False),
        sa.Column(
            "word_order",
            sa.Enum("sov", "svo", "vso", "vos", "ovs", "osv", "free", name="word_order", native_enum=False, create_constraint=True, length=40),
            nullable=False,
        ),
        sa.Column(
            "morphology",
            sa.Enum("isolating", "agglutinative", "fusional", "polysynthetic", name="morphology", native_enum=False, create_constraint=True, length=40),
            nullable=False,
        ),
        sa.Column("cases", sa.Integer(), nullable=False),
        sa.Column("noun_classes", sa.Integer(), nullable=False),
        sa.Column("evidentiality", sa.Boolean(), nullable=False),
        sa.Column("honorific_levels", sa.Integer(), nullable=False),
        sa.Column(
            "number_system",
            sa.Enum("none", "singular_plural", "dual", "trial", "paucal", name="number_system", native_enum=False, create_constraint=True, length=40),
            nullable=False,
        ),
        sa.Column("updated_epoch", sa.Integer(), nullable=False),
        sa.Column("locked", sa.JSON(), nullable=False),
        sa.CheckConstraint("cases BETWEEN 0 AND 20", name=op.f("ck_language_grammar_cases_range")),
        sa.CheckConstraint("honorific_levels BETWEEN 0 AND 6", name=op.f("ck_language_grammar_honorific_levels_range")),
        sa.CheckConstraint("noun_classes BETWEEN 0 AND 20", name=op.f("ck_language_grammar_noun_classes_range")),
        sa.CheckConstraint("updated_epoch >= 0", name=op.f("ck_language_grammar_updated_epoch_min")),
        sa.ForeignKeyConstraint(["language_entity_id"], ["entities.id"], name=op.f("fk_language_grammar_language_entity_id_entities"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("language_entity_id", name=op.f("pk_language_grammar")),
    )
    op.create_table(
        "language_policies",
        sa.Column("holder_entity_id", sa.Integer(), nullable=False),
        sa.Column("language_entity_id", sa.Integer(), nullable=False),
        sa.Column(
            "policy",
            sa.Enum("official", "liturgical", "suppressed", "revival", name="policy", native_enum=False, create_constraint=True, length=40),
            nullable=False,
        ),
        sa.Column("strength", sa.Integer(), nullable=False),
        sa.Column("since_epoch", sa.Integer(), nullable=False),
        sa.Column("locked", sa.JSON(), nullable=False),
        sa.CheckConstraint("since_epoch >= 0", name=op.f("ck_language_policies_since_epoch_min")),
        sa.CheckConstraint("strength BETWEEN 0 AND 100", name=op.f("ck_language_policies_strength_range")),
        sa.ForeignKeyConstraint(["holder_entity_id"], ["entities.id"], name=op.f("fk_language_policies_holder_entity_id_entities"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["language_entity_id"], ["entities.id"], name=op.f("fk_language_policies_language_entity_id_entities"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("holder_entity_id", "language_entity_id", "policy", name=op.f("pk_language_policies")),
    )
    with op.batch_alter_table("language_policies", schema=None) as batch_op:
        batch_op.create_index("ix_language_policies_language", ["language_entity_id"], unique=False)

    op.create_table(
        "scripts",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column(
            "system",
            sa.Enum(
                "alphabet",
                "syllabary",
                "pictographic",
                "knot",
                "notch",
                "logographic",
                "mixed",
                "abjad",
                name="system",
                native_enum=False,
                create_constraint=True,
                length=40,
            ),
            nullable=False,
        ),
        sa.Column("parent_script_id", sa.Integer(), nullable=True),
        sa.Column("origin_language_id", sa.Integer(), nullable=True),
        sa.Column("signs", sa.Integer(), nullable=False),
        sa.Column(
            "cause",
            sa.Enum("invention", "reform", "simplification", "borrowing", name="cause", native_enum=False, create_constraint=True, length=40),
            nullable=False,
        ),
        sa.Column("epoch", sa.Integer(), nullable=False),
        sa.Column("locked", sa.JSON(), nullable=False),
        sa.CheckConstraint("epoch >= 0", name=op.f("ck_scripts_epoch_min")),
        sa.CheckConstraint("signs >= 0", name=op.f("ck_scripts_signs_min")),
        sa.ForeignKeyConstraint(["origin_language_id"], ["entities.id"], name=op.f("fk_scripts_origin_language_id_entities"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["parent_script_id"], ["scripts.id"], name=op.f("fk_scripts_parent_script_id_scripts"), ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_scripts")),
    )
    with op.batch_alter_table("scripts", schema=None) as batch_op:
        batch_op.create_index("ix_scripts_parent", ["parent_script_id"], unique=False)

    op.create_table(
        "sound_changes",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("language_entity_id", sa.Integer(), nullable=False),
        sa.Column(
            "kind",
            sa.Enum("shift", "lenition", "vowel_shift", "merger", "loss", name="kind", native_enum=False, create_constraint=True, length=40),
            nullable=False,
        ),
        sa.Column("source", sa.String(length=120), nullable=False),
        sa.Column("target", sa.String(length=120), nullable=False),
        sa.Column(
            "environment",
            sa.Enum("anywhere", "initial", "final", "between_vowels", name="environment", native_enum=False, create_constraint=True, length=40),
            nullable=False,
        ),
        sa.Column(
            "cause",
            sa.Enum("contact", "prestige", "migration", "drift", "inherited", "decree", name="cause", native_enum=False, create_constraint=True, length=40),
            nullable=False,
        ),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("epoch", sa.Integer(), nullable=False),
        sa.Column("locked", sa.JSON(), nullable=False),
        sa.CheckConstraint("epoch >= 0", name=op.f("ck_sound_changes_epoch_min")),
        sa.CheckConstraint("position >= 0", name=op.f("ck_sound_changes_position_min")),
        sa.ForeignKeyConstraint(["language_entity_id"], ["entities.id"], name=op.f("fk_sound_changes_language_entity_id_entities"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_sound_changes")),
    )
    with op.batch_alter_table("sound_changes", schema=None) as batch_op:
        batch_op.create_index("ix_sound_changes_language", ["language_entity_id", "position"], unique=False)

    op.create_table(
        "meaning_shifts",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("lexeme_id", sa.Integer(), nullable=False),
        sa.Column(
            "shift",
            sa.Enum(
                "broadened",
                "narrowed",
                "pejorative",
                "ameliorative",
                "euphemism",
                "restored",
                name="shift",
                native_enum=False,
                create_constraint=True,
                length=40,
            ),
            nullable=False,
        ),
        sa.Column("old_meaning", sa.String(length=200), nullable=False),
        sa.Column("new_meaning", sa.String(length=200), nullable=False),
        sa.Column("replaced_by_id", sa.Integer(), nullable=True),
        sa.Column("cause_node_id", sa.Integer(), nullable=True),
        sa.Column("epoch", sa.Integer(), nullable=False),
        sa.CheckConstraint("epoch >= 0", name=op.f("ck_meaning_shifts_epoch_min")),
        sa.ForeignKeyConstraint(["cause_node_id"], ["nodes.id"], name=op.f("fk_meaning_shifts_cause_node_id_nodes"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["lexeme_id"], ["lexemes.id"], name=op.f("fk_meaning_shifts_lexeme_id_lexemes"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["replaced_by_id"], ["lexemes.id"], name=op.f("fk_meaning_shifts_replaced_by_id_lexemes"), ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_meaning_shifts")),
    )
    with op.batch_alter_table("meaning_shifts", schema=None) as batch_op:
        batch_op.create_index("ix_meaning_shifts_lexeme", ["lexeme_id"], unique=False)

    with op.batch_alter_table("language_profiles", schema=None) as batch_op:
        batch_op.add_column(sa.Column("script_id", sa.Integer(), nullable=True))
        batch_op.add_column(
            sa.Column(
                "modality",
                sa.Enum("vocal", "sign", "scent", "colour", "telepathic", name="modality", native_enum=False, create_constraint=True, length=40),
                server_default="vocal",
                nullable=False,
            )
        )
        batch_op.add_column(
            sa.Column(
                "stage",
                sa.Enum("natural", "pidgin", "creole", "divine", name="stage", native_enum=False, create_constraint=True, length=40),
                server_default="natural",
                nullable=False,
            )
        )
        batch_op.create_foreign_key(batch_op.f("fk_language_profiles_script_id_scripts"), "scripts", ["script_id"], ["id"], ondelete="SET NULL")
        batch_op.alter_column("writing_system", existing_type=systems(OLD_SYSTEMS), type_=systems(NEW_SYSTEMS), existing_nullable=True)
    op.execute("UPDATE language_profiles SET stage = 'creole' WHERE entity_id IN (SELECT id FROM entities WHERE subtype = 'creole')")

    with op.batch_alter_table("lexemes", schema=None) as batch_op:
        batch_op.add_column(sa.Column("proto_word", sa.String(length=60), nullable=True))
        batch_op.add_column(
            sa.Column(
                "register",
                sa.Enum("common", "sacred", "poetic", "archaic", name="register", native_enum=False, create_constraint=True, length=40),
                server_default="common",
                nullable=False,
            )
        )


def downgrade() -> None:
    op.execute("UPDATE language_profiles SET writing_system = NULL WHERE writing_system IN ('logographic', 'mixed', 'abjad')")
    with op.batch_alter_table("lexemes", schema=None) as batch_op:
        batch_op.drop_column("register")
        batch_op.drop_column("proto_word")

    with op.batch_alter_table("language_profiles", schema=None) as batch_op:
        batch_op.drop_constraint(batch_op.f("fk_language_profiles_script_id_scripts"), type_="foreignkey")
        batch_op.drop_column("stage")
        batch_op.drop_column("modality")
        batch_op.drop_column("script_id")
        batch_op.alter_column("writing_system", existing_type=systems(NEW_SYSTEMS), type_=systems(OLD_SYSTEMS), existing_nullable=True)

    with op.batch_alter_table("meaning_shifts", schema=None) as batch_op:
        batch_op.drop_index("ix_meaning_shifts_lexeme")

    op.drop_table("meaning_shifts")
    with op.batch_alter_table("sound_changes", schema=None) as batch_op:
        batch_op.drop_index("ix_sound_changes_language")

    op.drop_table("sound_changes")
    with op.batch_alter_table("scripts", schema=None) as batch_op:
        batch_op.drop_index("ix_scripts_parent")

    op.drop_table("scripts")
    with op.batch_alter_table("language_policies", schema=None) as batch_op:
        batch_op.drop_index("ix_language_policies_language")

    op.drop_table("language_policies")
    op.drop_table("language_grammar")
    op.drop_table("divine_tongues")
    op.drop_table("decipher_works")
