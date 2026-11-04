import sqlalchemy as sa
from alembic import op

revision = "f1a3c5e7b9d0"
down_revision = "a7c3e9d1f5b2"
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
SIZE_CLASSES = ("tiny", "small", "medium", "large", "huge", "colossal")
DIETS = ("omnivore", "herbivore", "carnivore", "piscivore", "scavenger", "sanguivore", "lithovore", "essence_feeder", "phototroph")
FUNERAL_RITES = ("burial", "cremation", "sky_burial", "sea_burial", "entombment", "ancestor_shrine", "endocannibalism", "reanimation", "soul_binding")


def kind(name: str, values: tuple[str, ...]) -> sa.Enum:
    return sa.Enum(*values, name=name, native_enum=False, create_constraint=True, length=40)


def upgrade() -> None:
    with op.batch_alter_table("people_biology", schema=None) as batch_op:
        batch_op.add_column(sa.Column("body_plan", kind("body_plan", BODY_PLANS), nullable=False, server_default="humanoid"))
        batch_op.add_column(sa.Column("size_class", kind("size_class", SIZE_CLASSES), nullable=False, server_default="medium"))
        batch_op.add_column(sa.Column("diet", kind("diet", DIETS), nullable=False, server_default="omnivore"))
    with op.batch_alter_table("people_culture", schema=None) as batch_op:
        batch_op.add_column(sa.Column("funeral_rite", kind("funeral_rite", FUNERAL_RITES), nullable=False, server_default="burial"))
        batch_op.add_column(sa.Column("martial_record", sa.JSON(), nullable=False, server_default=sa.text("'{}'")))
        batch_op.add_column(sa.Column("martial_epoch", sa.Integer(), nullable=False, server_default=sa.text("'0'")))


def downgrade() -> None:
    with op.batch_alter_table("people_culture", schema=None) as batch_op:
        batch_op.drop_column("martial_epoch")
        batch_op.drop_column("martial_record")
        batch_op.drop_column("funeral_rite")
    with op.batch_alter_table("people_biology", schema=None) as batch_op:
        batch_op.drop_column("diet")
        batch_op.drop_column("size_class")
        batch_op.drop_column("body_plan")
