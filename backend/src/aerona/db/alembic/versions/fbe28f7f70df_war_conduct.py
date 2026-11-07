import sqlalchemy as sa
from alembic import op

revision = "fbe28f7f70df"
down_revision = "adc3f030249b"
branch_labels = None
depends_on = None

OLD_CAUSES = ("abolition", "independence", "revival", "land_reform", "franchise")
NEW_CAUSES = (*OLD_CAUSES, "peace")


def causes(old: tuple[str, ...], new: tuple[str, ...]) -> None:
    with op.batch_alter_table("movement_profiles", schema=None) as batch_op:
        batch_op.alter_column(
            "cause",
            existing_type=sa.Enum(*old, name="cause", native_enum=False, create_constraint=True, length=40),
            type_=sa.Enum(*new, name="cause", native_enum=False, create_constraint=True, length=40),
            existing_nullable=False,
        )


def upgrade() -> None:
    op.create_table(
        "casus_belli",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("holder_entity_id", sa.Integer(), nullable=False),
        sa.Column("target_entity_id", sa.Integer(), nullable=False),
        sa.Column(
            "kind",
            sa.Enum(
                "claim",
                "holy_war",
                "vendetta",
                "broken_treaty",
                "insult",
                "liberation",
                "trade_dispute",
                "debt_default",
                "resource_need",
                "conquest",
                name="kind",
                native_enum=False,
                create_constraint=True,
                length=40,
            ),
            nullable=False,
        ),
        sa.Column("source_node_id", sa.Integer(), nullable=True),
        sa.Column("justification", sa.Integer(), nullable=False),
        sa.Column("since_epoch", sa.Integer(), nullable=False),
        sa.Column("expires_epoch", sa.Integer(), nullable=True),
        sa.Column("used_war_id", sa.Integer(), nullable=True),
        sa.Column("locked", sa.JSON(), nullable=False),
        sa.CheckConstraint("justification >= 0 AND justification <= 100", name=op.f("ck_casus_belli_justification_range")),
        sa.ForeignKeyConstraint(["holder_entity_id"], ["entities.id"], name=op.f("fk_casus_belli_holder_entity_id_entities"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["source_node_id"], ["nodes.id"], name=op.f("fk_casus_belli_source_node_id_nodes"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["target_entity_id"], ["entities.id"], name=op.f("fk_casus_belli_target_entity_id_entities"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["used_war_id"], ["wars.id"], name=op.f("fk_casus_belli_used_war_id_wars"), ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_casus_belli")),
    )
    with op.batch_alter_table("casus_belli", schema=None) as batch_op:
        batch_op.create_index("ix_casus_belli_holder", ["holder_entity_id", "target_entity_id"], unique=False)
        batch_op.create_index(batch_op.f("ix_casus_belli_target_entity_id"), ["target_entity_id"], unique=False)

    op.create_table(
        "war_production",
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
                "meat",
                "milk",
                "cheese",
                "fruit",
                "tubers",
                "coal",
                "peat",
                "dung",
                name="commodity",
                native_enum=False,
                create_constraint=True,
                length=40,
            ),
            nullable=False,
        ),
        sa.Column("efficiency", sa.Integer(), nullable=False),
        sa.Column("converted", sa.Boolean(), nullable=False),
        sa.Column("since_epoch", sa.Integer(), nullable=False),
        sa.Column("locked", sa.JSON(), nullable=False),
        sa.CheckConstraint("efficiency >= 0", name=op.f("ck_war_production_efficiency_min")),
        sa.ForeignKeyConstraint(["community_entity_id"], ["entities.id"], name=op.f("fk_war_production_community_entity_id_entities"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("community_entity_id", name=op.f("pk_war_production")),
    )
    with op.batch_alter_table("war_sides", schema=None) as batch_op:
        batch_op.add_column(sa.Column("support", sa.Integer(), nullable=False, server_default="60"))
        batch_op.add_column(sa.Column("locked", sa.JSON(), nullable=False, server_default="[]"))

    with op.batch_alter_table("wars", schema=None) as batch_op:
        batch_op.add_column(sa.Column("casus_belli_id", sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column("justified", sa.Boolean(), nullable=False, server_default=sa.true()))
        batch_op.create_foreign_key(batch_op.f("fk_wars_casus_belli_id_casus_belli"), "casus_belli", ["casus_belli_id"], ["id"], ondelete="SET NULL")
    causes(OLD_CAUSES, NEW_CAUSES)


def downgrade() -> None:
    causes(NEW_CAUSES, OLD_CAUSES)
    with op.batch_alter_table("wars", schema=None) as batch_op:
        batch_op.drop_constraint(batch_op.f("fk_wars_casus_belli_id_casus_belli"), type_="foreignkey")
        batch_op.drop_column("justified")
        batch_op.drop_column("casus_belli_id")

    with op.batch_alter_table("war_sides", schema=None) as batch_op:
        batch_op.drop_column("locked")
        batch_op.drop_column("support")

    op.drop_table("war_production")
    with op.batch_alter_table("casus_belli", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_casus_belli_target_entity_id"))
        batch_op.drop_index("ix_casus_belli_holder")

    op.drop_table("casus_belli")
