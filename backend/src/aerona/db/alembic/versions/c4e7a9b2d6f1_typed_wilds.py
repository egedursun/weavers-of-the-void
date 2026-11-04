import sqlalchemy as sa
from alembic import op

revision = "c4e7a9b2d6f1"
down_revision = "f2a6c8e0b4d7"
branch_labels = None
depends_on = None

BODY_PLANS = (
    "humanoid",
    "quadruped",
    "avian",
    "serpentine",
    "insectoid",
    "aquatic",
    "amorphous",
    "arboreal",
    "incorporeal",
    "colossal",
    "construct",
    "divine_manifest",
)
USES = ("food", "labour", "mount", "war", "guard", "companion", "sacrifice", "magic")
RENAMED = (("piscine", "aquatic"), ("arthropod", "insectoid"), ("plant", "arboreal"))


def plan_type() -> sa.Enum:
    return sa.Enum(*BODY_PLANS, name="body_plan", native_enum=False, create_constraint=True, length=40)


def upgrade() -> None:
    for old, new in RENAMED:
        op.execute(sa.text("UPDATE species_profiles SET body_plan = :new WHERE body_plan = :old").bindparams(new=new, old=old))
    known = ", ".join(f"'{plan}'" for plan in BODY_PLANS)
    op.execute(sa.text(f"UPDATE species_profiles SET body_plan = 'quadruped' WHERE body_plan NOT IN ({known})"))
    with op.batch_alter_table("species_profiles", schema=None) as batch_op:
        batch_op.alter_column("body_plan", existing_type=sa.String(length=120), type_=plan_type(), existing_nullable=False)
        batch_op.add_column(sa.Column("pinned_prey", sa.JSON(), nullable=False, server_default="[]"))
        batch_op.add_column(sa.Column("barred_prey", sa.JSON(), nullable=False, server_default="[]"))
    with op.batch_alter_table("species_hosts", schema=None) as batch_op:
        batch_op.add_column(sa.Column("locked", sa.JSON(), nullable=False, server_default="[]"))
    with op.batch_alter_table("species_yields", schema=None) as batch_op:
        batch_op.add_column(sa.Column("world_material_id", sa.Integer(), nullable=True))
        batch_op.create_foreign_key(
            op.f("fk_species_yields_world_material_id_world_materials"), "world_materials", ["world_material_id"], ["id"], ondelete="SET NULL"
        )
    op.create_table(
        "species_use_kinds",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("base_use", sa.Enum(*USES, name="base_use", native_enum=False, create_constraint=True, length=40), nullable=False),
        sa.Column("output_pct", sa.Integer(), nullable=False),
        sa.Column("description", sa.String(length=300), nullable=True),
        sa.Column("locked", sa.JSON(), nullable=False),
        sa.CheckConstraint("output_pct BETWEEN 0 AND 1000", name=op.f("ck_species_use_kinds_output_pct_range")),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_species_use_kinds")),
    )
    op.create_table(
        "species_custom_uses",
        sa.Column("species_entity_id", sa.Integer(), nullable=False),
        sa.Column("kind_id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["kind_id"], ["species_use_kinds.id"], name=op.f("fk_species_custom_uses_kind_id_species_use_kinds"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["species_entity_id"], ["entities.id"], name=op.f("fk_species_custom_uses_species_entity_id_entities"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("species_entity_id", "kind_id", name=op.f("pk_species_custom_uses")),
    )
    with op.batch_alter_table("species_custom_uses", schema=None) as batch_op:
        batch_op.create_index("ix_species_custom_uses_kind", ["kind_id"], unique=False)


def downgrade() -> None:
    with op.batch_alter_table("species_custom_uses", schema=None) as batch_op:
        batch_op.drop_index("ix_species_custom_uses_kind")
    op.drop_table("species_custom_uses")
    op.drop_table("species_use_kinds")
    with op.batch_alter_table("species_yields", schema=None) as batch_op:
        batch_op.drop_constraint(op.f("fk_species_yields_world_material_id_world_materials"), type_="foreignkey")
        batch_op.drop_column("world_material_id")
    with op.batch_alter_table("species_hosts", schema=None) as batch_op:
        batch_op.drop_column("locked")
    with op.batch_alter_table("species_profiles", schema=None) as batch_op:
        batch_op.drop_column("barred_prey")
        batch_op.drop_column("pinned_prey")
        batch_op.alter_column("body_plan", existing_type=plan_type(), type_=sa.String(length=120), existing_nullable=False)
