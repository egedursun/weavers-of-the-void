import sqlalchemy as sa
from alembic import op

revision = "e8a0c2d4f6b5"
down_revision = "d7f9b1c3e5a4"
branch_labels = None
depends_on = None

OLD_PARTS = (
    "aura",
    "core",
    "eye",
    "face",
    "fingers",
    "gills",
    "groin",
    "gut",
    "head",
    "heart",
    "horn",
    "jaw",
    "left_antenna",
    "left_arm",
    "left_branch",
    "left_ear",
    "left_eye",
    "left_fin",
    "left_foot",
    "left_foreleg",
    "left_hand",
    "left_hindleg",
    "left_leg",
    "left_midleg",
    "left_wing",
    "lungs",
    "neck",
    "nose",
    "pseudopods",
    "right_antenna",
    "right_arm",
    "right_branch",
    "right_ear",
    "right_eye",
    "right_fin",
    "right_foot",
    "right_foreleg",
    "right_hand",
    "right_hindleg",
    "right_leg",
    "right_midleg",
    "right_wing",
    "roots",
    "tail",
    "tongue",
    "torso",
    "venom_gland",
    "wings",
)
NEW_PARTS = (*OLD_PARTS, "teeth", "toes")
PART_TABLES = (("injuries", False), ("conditions", True), ("prostheses", False))
TISSUES = ("skin", "scale", "chitin", "bark", "fat", "muscle", "tendon", "bone", "artery", "motor_nerve", "sensory_nerve", "organ")


def parts(old: tuple[str, ...], new: tuple[str, ...]) -> None:
    for table, nullable in PART_TABLES:
        with op.batch_alter_table(table, schema=None) as batch_op:
            batch_op.alter_column(
                "part",
                existing_type=sa.Enum(*old, name="part", native_enum=False, create_constraint=True, length=40),
                type_=sa.Enum(*new, name="part", native_enum=False, create_constraint=True, length=40),
                existing_nullable=nullable,
            )


def upgrade() -> None:
    parts(OLD_PARTS, NEW_PARTS)
    with op.batch_alter_table("bodies", schema=None) as batch_op:
        batch_op.add_column(sa.Column("toes", sa.Integer(), server_default="10", nullable=False))
        batch_op.add_column(sa.Column("teeth", sa.Integer(), server_default="32", nullable=False))
        batch_op.add_column(sa.Column("blood", sa.Integer(), server_default="100", nullable=False))
        batch_op.add_column(sa.Column("exertion", sa.Integer(), server_default="0", nullable=False))
        batch_op.add_column(
            sa.Column(
                "consciousness",
                sa.Enum("awake", "nauseous", "dizzy", "unconscious", name="consciousness", native_enum=False, create_constraint=True, length=40),
                server_default="awake",
                nullable=False,
            )
        )
        batch_op.create_check_constraint("toes_min", "toes >= 0")
        batch_op.create_check_constraint("teeth_min", "teeth >= 0")
        batch_op.create_check_constraint("blood_range", "blood BETWEEN 0 AND 100")
        batch_op.create_check_constraint("exertion_range", "exertion BETWEEN 0 AND 100")
    with op.batch_alter_table("injuries", schema=None) as batch_op:
        batch_op.add_column(sa.Column("tissue", sa.Enum(*TISSUES, name="tissue", native_enum=False, create_constraint=True, length=40), nullable=True))
        batch_op.add_column(sa.Column("bleeding", sa.Integer(), server_default="0", nullable=False))
        batch_op.add_column(
            sa.Column(
                "nerve",
                sa.Enum("none", "motor", "sensory", name="nerve", native_enum=False, create_constraint=True, length=40),
                server_default="none",
                nullable=False,
            )
        )
        batch_op.add_column(sa.Column("treatments", sa.JSON(), server_default="[]", nullable=False))
        batch_op.add_column(sa.Column("misdiagnosed", sa.Boolean(), server_default="0", nullable=False))
        batch_op.create_check_constraint("bleeding_range", "bleeding BETWEEN 0 AND 100")


def downgrade() -> None:
    with op.batch_alter_table("injuries", schema=None) as batch_op:
        batch_op.drop_constraint("bleeding_range", type_="check")
        for column in ("misdiagnosed", "treatments", "nerve", "bleeding", "tissue"):
            batch_op.drop_column(column)
    with op.batch_alter_table("bodies", schema=None) as batch_op:
        for name in ("exertion_range", "blood_range", "teeth_min", "toes_min"):
            batch_op.drop_constraint(name, type_="check")
        for column in ("consciousness", "exertion", "blood", "teeth", "toes"):
            batch_op.drop_column(column)
    parts(NEW_PARTS, OLD_PARTS)
