import sqlalchemy as sa
from alembic import op

revision = "adc3f030249b"
down_revision = "ebc535139834"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "army_templates",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("polity_entity_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column(
            "doctrine",
            sa.Enum(
                "shieldwall",
                "horse_archer",
                "skirmisher",
                "chariot",
                "phalanx",
                "berserker",
                "naval_raider",
                "siege_engineer",
                "war_magic",
                "beast_war",
                name="doctrine",
                native_enum=False,
                create_constraint=True,
                length=40,
            ),
            nullable=False,
        ),
        sa.Column("composition", sa.JSON(), nullable=False),
        sa.Column("active", sa.Boolean(), nullable=False),
        sa.Column("obsolete", sa.Boolean(), nullable=False),
        sa.Column("created_epoch", sa.Integer(), nullable=False),
        sa.Column("upgraded_epoch", sa.Integer(), nullable=True),
        sa.Column("locked", sa.JSON(), nullable=False),
        sa.CheckConstraint("created_epoch >= 0", name=op.f("ck_army_templates_created_epoch_min")),
        sa.ForeignKeyConstraint(["polity_entity_id"], ["entities.id"], name=op.f("fk_army_templates_polity_entity_id_entities"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_army_templates")),
    )
    with op.batch_alter_table("army_templates", schema=None) as batch_op:
        batch_op.create_index("ix_army_templates_polity", ["polity_entity_id"], unique=False)

    with op.batch_alter_table("battles", schema=None) as batch_op:
        batch_op.add_column(sa.Column("standard_entity_id", sa.Integer(), nullable=True))
        batch_op.create_foreign_key(batch_op.f("fk_battles_standard_entity_id_entities"), "entities", ["standard_entity_id"], ["id"], ondelete="SET NULL")


def downgrade() -> None:
    with op.batch_alter_table("battles", schema=None) as batch_op:
        batch_op.drop_constraint(batch_op.f("fk_battles_standard_entity_id_entities"), type_="foreignkey")
        batch_op.drop_column("standard_entity_id")

    with op.batch_alter_table("army_templates", schema=None) as batch_op:
        batch_op.drop_index("ix_army_templates_polity")

    op.drop_table("army_templates")
