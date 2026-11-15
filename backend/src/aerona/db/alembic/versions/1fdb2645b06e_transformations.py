import sqlalchemy as sa
from alembic import op

revision = "1fdb2645b06e"
down_revision = "c6bde0bacf5d"
branch_labels = None
depends_on = None


STATUS_OLD = ("active", "asleep", "exiled", "dead")
STATUS_NEW = ("active", "asleep", "exiled", "fallen", "dead")
PUNISHMENT_OLD = ("chain", "exile", "strip_power")
PUNISHMENT_NEW = (*PUNISHMENT_OLD, "strip_divinity")


def enum_of(values: tuple[str, ...], name: str) -> sa.Enum:
    return sa.Enum(*values, name=name, native_enum=False, create_constraint=True, length=40)


def retype(table: str, column: str, change: tuple[tuple[str, ...], tuple[str, ...]], nullable: bool) -> None:
    before, after = change
    with op.batch_alter_table(table, schema=None) as batch_op:
        batch_op.alter_column(column, existing_type=enum_of(before, column), type_=enum_of(after, column), existing_nullable=nullable)


def upgrade() -> None:
    retype("sons", "status", (STATUS_OLD, STATUS_NEW), False)
    retype("council_rulings", "punishment", (PUNISHMENT_OLD, PUNISHMENT_NEW), True)
    op.create_table(
        "transform_prospects",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column(
            "kind",
            sa.Enum(
                "deification",
                "mantling",
                "spirit_rising",
                "reincarnation",
                "possession",
                "local_god",
                "beast_curse",
                "curse_lifted",
                "uplift",
                "city_state",
                "secession",
                "theocracy",
                "title_raised",
                "realm_from_title",
                "manifestation",
                "legend_fixed",
                "artwork_remembered",
                "event_phenomenon",
                "god_corpse",
                "construct",
                "beast_promotion",
                "language_death",
                "language_revival",
                "theory_settled",
                "tradition_codified",
                "fall",
                "restoration",
                "loss_of_sapience",
                "ethnoreligious",
                "nation_building",
                "house_people",
                "pocket_world",
                "world_soul",
                "star_god",
                "sacralisation",
                "secularisation",
                "progenitor",
                "outer_entry",
                "corruption",
                "colossal_corpse",
                name="kind",
                native_enum=False,
                create_constraint=True,
                length=40,
            ),
            nullable=False,
        ),
        sa.Column("subject_node_id", sa.Integer(), nullable=False),
        sa.Column("progress", sa.Integer(), nullable=False),
        sa.Column("stance", sa.Enum("open", "blocked", "forced", name="stance", native_enum=False, create_constraint=True, length=40), nullable=False),
        sa.Column(
            "trigger",
            sa.Enum(
                "engine",
                "forced",
                "creator",
                "council",
                "fading",
                "son",
                "curse",
                "void",
                "dark_age",
                "punishment",
                "backfill",
                name="trigger",
                native_enum=False,
                create_constraint=True,
                length=40,
            ),
            nullable=False,
        ),
        sa.Column("warned_epoch", sa.Integer(), nullable=True),
        sa.Column("due_epoch", sa.Integer(), nullable=True),
        sa.Column("updated_epoch", sa.Integer(), nullable=False),
        sa.Column("locked", sa.JSON(), nullable=False),
        sa.CheckConstraint("progress BETWEEN 0 AND 100", name=op.f("ck_transform_prospects_progress_range")),
        sa.CheckConstraint("updated_epoch >= 0", name=op.f("ck_transform_prospects_updated_epoch_min")),
        sa.ForeignKeyConstraint(["subject_node_id"], ["nodes.id"], name=op.f("fk_transform_prospects_subject_node_id_nodes"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_transform_prospects")),
        sa.UniqueConstraint("kind", "subject_node_id", name="uq_transform_prospects_kind_subject"),
    )
    with op.batch_alter_table("transform_prospects", schema=None) as batch_op:
        batch_op.create_index("ix_transform_prospects_subject", ["subject_node_id"], unique=False)

    op.create_table(
        "star_modifiers",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("star_id", sa.Integer(), nullable=False),
        sa.Column("source", sa.Enum("god_death", "divine_act", name="source", native_enum=False, create_constraint=True, length=40), nullable=False),
        sa.Column("luminosity_pct", sa.Integer(), nullable=False),
        sa.Column("age_epochs", sa.Integer(), nullable=False),
        sa.Column("aged", sa.Boolean(), nullable=False),
        sa.Column("decay", sa.Integer(), nullable=False),
        sa.Column("epoch", sa.Integer(), nullable=False),
        sa.Column("cause_node_id", sa.Integer(), nullable=True),
        sa.Column("locked", sa.JSON(), nullable=False),
        sa.CheckConstraint("age_epochs >= 0", name=op.f("ck_star_modifiers_age_epochs_min")),
        sa.CheckConstraint("decay BETWEEN 0 AND 100", name=op.f("ck_star_modifiers_decay_range")),
        sa.CheckConstraint("epoch >= 0", name=op.f("ck_star_modifiers_epoch_min")),
        sa.CheckConstraint("luminosity_pct BETWEEN -90 AND 90", name=op.f("ck_star_modifiers_luminosity_pct_range")),
        sa.ForeignKeyConstraint(["cause_node_id"], ["nodes.id"], name=op.f("fk_star_modifiers_cause_node_id_nodes"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["star_id"], ["stars.id"], name=op.f("fk_star_modifiers_star_id_stars"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_star_modifiers")),
    )
    with op.batch_alter_table("star_modifiers", schema=None) as batch_op:
        batch_op.create_index("ix_star_modifiers_star", ["star_id"], unique=False)

    op.create_table(
        "transformations",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column(
            "kind",
            sa.Enum(
                "deification",
                "mantling",
                "spirit_rising",
                "reincarnation",
                "possession",
                "local_god",
                "beast_curse",
                "curse_lifted",
                "uplift",
                "city_state",
                "secession",
                "theocracy",
                "title_raised",
                "realm_from_title",
                "manifestation",
                "legend_fixed",
                "artwork_remembered",
                "event_phenomenon",
                "god_corpse",
                "construct",
                "beast_promotion",
                "language_death",
                "language_revival",
                "theory_settled",
                "tradition_codified",
                "fall",
                "restoration",
                "loss_of_sapience",
                "ethnoreligious",
                "nation_building",
                "house_people",
                "pocket_world",
                "world_soul",
                "star_god",
                "sacralisation",
                "secularisation",
                "progenitor",
                "outer_entry",
                "corruption",
                "colossal_corpse",
                name="kind",
                native_enum=False,
                create_constraint=True,
                length=40,
            ),
            nullable=False,
        ),
        sa.Column("epoch", sa.Integer(), nullable=False),
        sa.Column(
            "trigger",
            sa.Enum(
                "engine",
                "forced",
                "creator",
                "council",
                "fading",
                "son",
                "curse",
                "void",
                "dark_age",
                "punishment",
                "backfill",
                name="trigger",
                native_enum=False,
                create_constraint=True,
                length=40,
            ),
            nullable=False,
        ),
        sa.Column("state", sa.Enum("done", "reverted", name="state", native_enum=False, create_constraint=True, length=40), nullable=False),
        sa.Column("subject_node_id", sa.Integer(), nullable=True),
        sa.Column("result_node_id", sa.Integer(), nullable=True),
        sa.Column("subject_name", sa.String(length=200), nullable=False),
        sa.Column("result_name", sa.String(length=200), nullable=True),
        sa.Column("incident_id", sa.Integer(), nullable=True),
        sa.Column("undo", sa.JSON(), nullable=False),
        sa.Column("locked", sa.JSON(), nullable=False),
        sa.CheckConstraint("epoch >= 0", name=op.f("ck_transformations_epoch_min")),
        sa.ForeignKeyConstraint(["incident_id"], ["incidents.id"], name=op.f("fk_transformations_incident_id_incidents"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["result_node_id"], ["nodes.id"], name=op.f("fk_transformations_result_node_id_nodes"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["subject_node_id"], ["nodes.id"], name=op.f("fk_transformations_subject_node_id_nodes"), ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_transformations")),
    )
    with op.batch_alter_table("transformations", schema=None) as batch_op:
        batch_op.create_index("ix_transformations_epoch", ["epoch"], unique=False)
        batch_op.create_index("ix_transformations_result", ["result_node_id"], unique=False)
        batch_op.create_index("ix_transformations_subject", ["subject_node_id"], unique=False)

    with op.batch_alter_table("foreign_gods", schema=None) as batch_op:
        batch_op.add_column(sa.Column("anchor_world_id", sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column("anchor_star_id", sa.Integer(), nullable=True))
        batch_op.create_foreign_key(batch_op.f("fk_foreign_gods_anchor_star_id_stars"), "stars", ["anchor_star_id"], ["id"], ondelete="SET NULL")
        batch_op.create_foreign_key(batch_op.f("fk_foreign_gods_anchor_world_id_worlds"), "worlds", ["anchor_world_id"], ["id"], ondelete="SET NULL")

    with op.batch_alter_table("sons", schema=None) as batch_op:
        batch_op.add_column(sa.Column("body_entity_id", sa.Integer(), nullable=True))
        batch_op.create_foreign_key(batch_op.f("fk_sons_body_entity_id_entities"), "entities", ["body_entity_id"], ["id"], ondelete="SET NULL", use_alter=True)


def downgrade() -> None:
    op.execute("UPDATE sons SET status = 'dead' WHERE status = 'fallen'")
    op.execute("UPDATE council_rulings SET punishment = 'chain' WHERE punishment = 'strip_divinity'")
    retype("sons", "status", (STATUS_NEW, STATUS_OLD), False)
    retype("council_rulings", "punishment", (PUNISHMENT_NEW, PUNISHMENT_OLD), True)
    with op.batch_alter_table("sons", schema=None) as batch_op:
        batch_op.drop_constraint(batch_op.f("fk_sons_body_entity_id_entities"), type_="foreignkey")
        batch_op.drop_column("body_entity_id")

    with op.batch_alter_table("foreign_gods", schema=None) as batch_op:
        batch_op.drop_constraint(batch_op.f("fk_foreign_gods_anchor_world_id_worlds"), type_="foreignkey")
        batch_op.drop_constraint(batch_op.f("fk_foreign_gods_anchor_star_id_stars"), type_="foreignkey")
        batch_op.drop_column("anchor_star_id")
        batch_op.drop_column("anchor_world_id")

    with op.batch_alter_table("transformations", schema=None) as batch_op:
        batch_op.drop_index("ix_transformations_subject")
        batch_op.drop_index("ix_transformations_result")
        batch_op.drop_index("ix_transformations_epoch")

    op.drop_table("transformations")
    with op.batch_alter_table("star_modifiers", schema=None) as batch_op:
        batch_op.drop_index("ix_star_modifiers_star")

    op.drop_table("star_modifiers")
    with op.batch_alter_table("transform_prospects", schema=None) as batch_op:
        batch_op.drop_index("ix_transform_prospects_subject")

    op.drop_table("transform_prospects")
