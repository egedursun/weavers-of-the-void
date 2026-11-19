import sqlalchemy as sa
from alembic import op

revision = "6217b56bb2ff"
down_revision = "6895a56dc94a"
branch_labels = None
depends_on = None

PHASES = ("scouting", "plan", "command", "missile", "charge", "melee", "reserves", "rites", "pursuit", "salvage", "aftermath")
PUNISHMENTS = (
    "fine",
    "flogging",
    "exile",
    "branding",
    "hand",
    "tongue",
    "eyes",
    "death",
    "public_shaming",
    "imprisonment",
    "remaking",
    "forced_dormancy",
    "forced_edit",
    "seat_confinement",
    "state_seizure",
    "erasure",
    "restitution",
    "compensation",
    "penal_labour",
    "servitude",
    "outlawry",
    "confiscation",
    "loss_of_rank",
    "excommunication",
    "penance",
    "banishment_from_place",
    "house_arrest",
    "probation",
    "reeducation",
    "transportation",
    "community_work",
    "dampening",
)
MATERIALS = ("timber", "stone")
JOB_KINDS = (
    "epoch",
    "genesis",
    "deepen",
    "summon",
    "image",
    "backup",
    "book",
    "import",
    "simulation",
    "son_turn",
    "naming",
    "completion",
    "revelation",
    "world_creation",
    "awakening",
    "content",
    "maintenance",
    "retry",
    "prehistory",
    "deep_time",
)
JOB_STATUSES = ("queued", "running", "succeeded", "failed", "cancelled", "interrupted")


def enum_of(values: tuple[str, ...], name: str) -> sa.Enum:
    return sa.Enum(*values, name=name, native_enum=False, create_constraint=True, length=40)


def listed(values: tuple[str, ...]) -> str:
    return ", ".join(f"'{value}'" for value in values)


def upgrade() -> None:
    op.execute(sa.text(f"DELETE FROM battle_phases WHERE phase NOT IN ({listed(PHASES)})"))
    op.execute(sa.text(f"UPDATE sentences SET penalty = 'fine' WHERE penalty NOT IN ({listed(PUNISHMENTS)})"))
    op.execute(sa.text(f"UPDATE sieges SET wall_material = NULL WHERE wall_material NOT IN ({listed(MATERIALS)})"))
    with op.batch_alter_table("crime_cases", schema=None) as batch_op:
        batch_op.add_column(sa.Column("immune", sa.Boolean(), nullable=False, server_default="0"))
    op.execute(sa.text("UPDATE crime_cases SET immune = 1 WHERE penalty = 'immunity'"))
    op.execute(sa.text(f"UPDATE crime_cases SET penalty = NULL WHERE penalty NOT IN ({listed(PUNISHMENTS)})"))
    with op.batch_alter_table("battle_phases", schema=None) as batch_op:
        batch_op.alter_column("phase", existing_type=sa.String(length=120), type_=enum_of(PHASES, "phase"), existing_nullable=False)
    with op.batch_alter_table("sentences", schema=None) as batch_op:
        batch_op.alter_column("penalty", existing_type=sa.String(length=120), type_=enum_of(PUNISHMENTS, "penalty"), existing_nullable=False)
    with op.batch_alter_table("crime_cases", schema=None) as batch_op:
        batch_op.alter_column("penalty", existing_type=sa.String(length=120), type_=enum_of(PUNISHMENTS, "penalty"), existing_nullable=True)
    with op.batch_alter_table("sieges", schema=None) as batch_op:
        batch_op.alter_column("wall_material", existing_type=sa.String(length=200), type_=enum_of(MATERIALS, "wall_material"), existing_nullable=True)
    op.execute(sa.text(f"DELETE FROM jobs WHERE kind NOT IN ({listed(JOB_KINDS)}) OR status NOT IN ({listed(JOB_STATUSES)})"))
    with op.batch_alter_table("jobs", schema=None) as batch_op:
        batch_op.alter_column("kind", existing_type=sa.String(length=32), type_=enum_of(JOB_KINDS, "kind"), existing_nullable=False)
        batch_op.alter_column("status", existing_type=sa.String(length=16), type_=enum_of(JOB_STATUSES, "status"), existing_nullable=False)


def downgrade() -> None:
    with op.batch_alter_table("jobs", schema=None) as batch_op:
        batch_op.alter_column("status", existing_type=enum_of(JOB_STATUSES, "status"), type_=sa.String(length=16), existing_nullable=False)
        batch_op.alter_column("kind", existing_type=enum_of(JOB_KINDS, "kind"), type_=sa.String(length=32), existing_nullable=False)
    with op.batch_alter_table("sieges", schema=None) as batch_op:
        batch_op.alter_column("wall_material", existing_type=enum_of(MATERIALS, "wall_material"), type_=sa.String(length=200), existing_nullable=True)
    with op.batch_alter_table("crime_cases", schema=None) as batch_op:
        batch_op.alter_column("penalty", existing_type=enum_of(PUNISHMENTS, "penalty"), type_=sa.String(length=120), existing_nullable=True)
    op.execute(sa.text("UPDATE crime_cases SET penalty = 'immunity' WHERE immune = 1"))
    with op.batch_alter_table("crime_cases", schema=None) as batch_op:
        batch_op.drop_column("immune")
    with op.batch_alter_table("sentences", schema=None) as batch_op:
        batch_op.alter_column("penalty", existing_type=enum_of(PUNISHMENTS, "penalty"), type_=sa.String(length=120), existing_nullable=False)
    with op.batch_alter_table("battle_phases", schema=None) as batch_op:
        batch_op.alter_column("phase", existing_type=enum_of(PHASES, "phase"), type_=sa.String(length=120), existing_nullable=False)
