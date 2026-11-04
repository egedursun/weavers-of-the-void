import sqlalchemy as sa
from alembic import op

revision = "a1c5e7f9b3d2"
down_revision = "f2a6c8e0b4d7"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "mortal_repute",
        sa.Column("mortal_entity_id", sa.Integer(), nullable=False),
        sa.Column("honour", sa.Integer(), nullable=False),
        sa.Column("infamy", sa.Integer(), nullable=False),
        sa.Column("updated_epoch", sa.Integer(), nullable=False),
        sa.Column("locked", sa.JSON(), nullable=False),
        sa.CheckConstraint("honour BETWEEN 0 AND 100", name=op.f("ck_mortal_repute_honour_range")),
        sa.CheckConstraint("infamy BETWEEN 0 AND 100", name=op.f("ck_mortal_repute_infamy_range")),
        sa.ForeignKeyConstraint(["mortal_entity_id"], ["entities.id"], name=op.f("fk_mortal_repute_mortal_entity_id_entities"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("mortal_entity_id", name=op.f("pk_mortal_repute")),
    )
    op.create_table(
        "sentences",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("mortal_entity_id", sa.Integer(), nullable=False),
        sa.Column("settlement_entity_id", sa.Integer(), nullable=True),
        sa.Column("law_entity_id", sa.Integer(), nullable=True),
        sa.Column(
            "crime",
            sa.Enum("theft", "murder", "treason", "blasphemy", "desertion", name="crime", native_enum=False, create_constraint=True, length=40),
            nullable=False,
        ),
        sa.Column("penalty", sa.String(length=120), nullable=False),
        sa.Column("epoch", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["law_entity_id"], ["entities.id"], name=op.f("fk_sentences_law_entity_id_entities"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["mortal_entity_id"], ["entities.id"], name=op.f("fk_sentences_mortal_entity_id_entities"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["settlement_entity_id"], ["entities.id"], name=op.f("fk_sentences_settlement_entity_id_entities"), ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_sentences")),
    )
    with op.batch_alter_table("sentences", schema=None) as batch_op:
        batch_op.create_index("ix_sentences_settlement", ["settlement_entity_id", "epoch"], unique=False)
        batch_op.create_index("ix_sentences_mortal", ["mortal_entity_id"], unique=False)


def downgrade() -> None:
    op.drop_table("sentences")
    op.drop_table("mortal_repute")
