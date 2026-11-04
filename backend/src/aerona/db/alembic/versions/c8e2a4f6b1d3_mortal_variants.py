import sqlalchemy as sa
from alembic import op

revision = "c8e2a4f6b1d3"
down_revision = "b9d4f2a6c8e1"
branch_labels = None
depends_on = None


def named_enum(name: str, values: tuple[str, ...]) -> sa.Enum:
    return sa.Enum(*values, name=name, native_enum=False, create_constraint=True, length=40)


PROFESSIONS = (
    "soldier",
    "rider",
    "smith",
    "builder",
    "weaver",
    "healer",
    "scholar",
    "priest",
    "sorcerer",
    "merchant",
    "diplomat",
    "hunter",
    "sailor",
    "commander",
)
VARIANT_TABLES = ("conditions", "skills", "traits")


def variants_upgrade() -> None:
    op.create_table(
        "kind_variants",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("world_id", sa.Integer(), nullable=True),
        sa.Column("family", named_enum("family", ("trait", "skill", "condition")), nullable=False),
        sa.Column("base", sa.String(length=120), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("strength_pct", sa.Integer(), nullable=False),
        sa.Column("learning_pct", sa.Integer(), nullable=False),
        sa.Column("created_epoch", sa.Integer(), nullable=False),
        sa.Column("locked", sa.JSON(), nullable=False),
        sa.CheckConstraint("learning_pct >= 0", name=op.f("ck_kind_variants_learning_pct_min")),
        sa.CheckConstraint("strength_pct >= 0", name=op.f("ck_kind_variants_strength_pct_min")),
        sa.ForeignKeyConstraint(["world_id"], ["worlds.id"], name=op.f("fk_kind_variants_world_id_worlds"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_kind_variants")),
    )
    with op.batch_alter_table("kind_variants", schema=None) as batch_op:
        batch_op.create_index("ix_kind_variants_family", ["family"], unique=False)
    for table in VARIANT_TABLES:
        with op.batch_alter_table(table, schema=None) as batch_op:
            batch_op.add_column(sa.Column("variant_id", sa.Integer(), nullable=True))
            batch_op.create_foreign_key(batch_op.f(f"fk_{table}_variant_id_kind_variants"), "kind_variants", ["variant_id"], ["id"], ondelete="SET NULL")
    with op.batch_alter_table("mortal_profiles", schema=None) as batch_op:
        batch_op.add_column(sa.Column("profession", named_enum("profession", PROFESSIONS), nullable=True))
    with op.batch_alter_table("prostheses", schema=None) as batch_op:
        batch_op.add_column(sa.Column("world_material_id", sa.Integer(), nullable=True))
        batch_op.create_foreign_key(
            batch_op.f("fk_prostheses_world_material_id_world_materials"), "world_materials", ["world_material_id"], ["id"], ondelete="SET NULL"
        )


def variants_downgrade() -> None:
    with op.batch_alter_table("prostheses", schema=None) as batch_op:
        batch_op.drop_constraint(batch_op.f("fk_prostheses_world_material_id_world_materials"), type_="foreignkey")
        batch_op.drop_column("world_material_id")
    with op.batch_alter_table("mortal_profiles", schema=None) as batch_op:
        batch_op.drop_column("profession")
    for table in VARIANT_TABLES:
        with op.batch_alter_table(table, schema=None) as batch_op:
            batch_op.drop_constraint(batch_op.f(f"fk_{table}_variant_id_kind_variants"), type_="foreignkey")
            batch_op.drop_column("variant_id")
    with op.batch_alter_table("kind_variants", schema=None) as batch_op:
        batch_op.drop_index("ix_kind_variants_family")
    op.drop_table("kind_variants")


def upgrade() -> None:
    variants_upgrade()


def downgrade() -> None:
    variants_downgrade()
