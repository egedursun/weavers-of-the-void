import sqlalchemy as sa
from alembic import op

revision = "e5f9b3a7c2d1"
down_revision = "d8a2c6e4f1b7"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "court_positions",
        sa.Column("polity_entity_id", sa.Integer(), nullable=False),
        sa.Column(
            "position",
            sa.Enum(
                "steward",
                "champion",
                "physician",
                "tutor",
                "chronicler",
                "master_of_revels",
                name="position",
                native_enum=False,
                create_constraint=True,
                length=40,
            ),
            nullable=False,
        ),
        sa.Column("holder_entity_id", sa.Integer(), nullable=True),
        sa.Column("since_epoch", sa.Integer(), nullable=False),
        sa.Column("locked", sa.Boolean(), nullable=False),
        sa.CheckConstraint("since_epoch >= 0", name=op.f("ck_court_positions_since_epoch_min")),
        sa.ForeignKeyConstraint(["holder_entity_id"], ["entities.id"], name=op.f("fk_court_positions_holder_entity_id_entities"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["polity_entity_id"], ["entities.id"], name=op.f("fk_court_positions_polity_entity_id_entities"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("polity_entity_id", "position", name=op.f("pk_court_positions")),
    )
    with op.batch_alter_table("court_positions", schema=None) as batch_op:
        batch_op.create_index(batch_op.f("ix_court_positions_holder_entity_id"), ["holder_entity_id"], unique=False)

    op.create_table(
        "courts",
        sa.Column("polity_entity_id", sa.Integer(), nullable=False),
        sa.Column("grandeur", sa.Integer(), nullable=False),
        sa.Column("courtiers", sa.Integer(), nullable=False),
        sa.Column("parts", sa.JSON(), nullable=False),
        sa.Column("epoch", sa.Integer(), nullable=False),
        sa.Column("locked", sa.JSON(), nullable=False),
        sa.CheckConstraint("courtiers >= 0", name=op.f("ck_courts_courtiers_min")),
        sa.CheckConstraint("grandeur BETWEEN 0 AND 100", name=op.f("ck_courts_grandeur_range")),
        sa.ForeignKeyConstraint(["polity_entity_id"], ["entities.id"], name=op.f("fk_courts_polity_entity_id_entities"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("polity_entity_id", name=op.f("pk_courts")),
    )
    op.create_table(
        "resolutions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("assembly_entity_id", sa.Integer(), nullable=False),
        sa.Column(
            "kind",
            sa.Enum("route_security", "embargo", "void_ban", "sanction", name="kind", native_enum=False, create_constraint=True, length=40),
            nullable=False,
        ),
        sa.Column("target_node_id", sa.Integer(), nullable=True),
        sa.Column("votes_for", sa.Integer(), nullable=False),
        sa.Column("votes_against", sa.Integer(), nullable=False),
        sa.Column(
            "state", sa.Enum("proposed", "passed", "rejected", "lapsed", name="state", native_enum=False, create_constraint=True, length=40), nullable=False
        ),
        sa.Column("proposed_epoch", sa.Integer(), nullable=False),
        sa.Column("until_epoch", sa.Integer(), nullable=True),
        sa.Column("locked", sa.JSON(), nullable=False),
        sa.CheckConstraint("proposed_epoch >= 0", name=op.f("ck_resolutions_proposed_epoch_min")),
        sa.CheckConstraint("votes_against >= 0", name=op.f("ck_resolutions_votes_against_min")),
        sa.CheckConstraint("votes_for >= 0", name=op.f("ck_resolutions_votes_for_min")),
        sa.ForeignKeyConstraint(["assembly_entity_id"], ["entities.id"], name=op.f("fk_resolutions_assembly_entity_id_entities"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["target_node_id"], ["nodes.id"], name=op.f("fk_resolutions_target_node_id_nodes"), ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_resolutions")),
    )
    with op.batch_alter_table("resolutions", schema=None) as batch_op:
        batch_op.create_index("ix_resolutions_assembly", ["assembly_entity_id", "state"], unique=False)
        batch_op.create_index(batch_op.f("ix_resolutions_target_node_id"), ["target_node_id"], unique=False)

    op.create_table(
        "resolution_votes",
        sa.Column("resolution_id", sa.Integer(), nullable=False),
        sa.Column("member_node_id", sa.Integer(), nullable=False),
        sa.Column("aye", sa.Boolean(), nullable=False),
        sa.Column("weight", sa.Integer(), nullable=False),
        sa.Column("locked", sa.Boolean(), nullable=False),
        sa.CheckConstraint("weight >= 0", name=op.f("ck_resolution_votes_weight_min")),
        sa.ForeignKeyConstraint(["member_node_id"], ["nodes.id"], name=op.f("fk_resolution_votes_member_node_id_nodes"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["resolution_id"], ["resolutions.id"], name=op.f("fk_resolution_votes_resolution_id_resolutions"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("resolution_id", "member_node_id", name=op.f("pk_resolution_votes")),
    )
    with op.batch_alter_table("resolution_votes", schema=None) as batch_op:
        batch_op.create_index(batch_op.f("ix_resolution_votes_member_node_id"), ["member_node_id"], unique=False)


def downgrade() -> None:
    with op.batch_alter_table("resolution_votes", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_resolution_votes_member_node_id"))

    op.drop_table("resolution_votes")
    with op.batch_alter_table("resolutions", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_resolutions_target_node_id"))
        batch_op.drop_index("ix_resolutions_assembly")

    op.drop_table("resolutions")
    op.drop_table("courts")
    with op.batch_alter_table("court_positions", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_court_positions_holder_entity_id"))

    op.drop_table("court_positions")
