import sqlalchemy as sa
from alembic import op

revision = "6895a56dc94a"
down_revision = "8ae40f7ec3db"
branch_labels = None
depends_on = None

STYLES = (
    "shieldwall",
    "horse_archer",
    "skirmisher",
    "chariot",
    "phalanx",
    "shock",
    "naval_raider",
    "siege_engineer",
    "war_magic",
    "beast_war",
    "mechanised",
    "air_mobile",
    "guerrilla",
    "drone_war",
    "orbital",
    "combined_arms",
)


def upgrade() -> None:
    known = ", ".join(f"'{style}'" for style in STYLES)
    op.execute(sa.text(f"UPDATE army_profiles SET doctrine = 'shieldwall' WHERE doctrine IS NULL OR doctrine NOT IN ({known})"))
    with op.batch_alter_table("army_profiles", schema=None) as batch_op:
        batch_op.alter_column(
            "doctrine",
            existing_type=sa.String(length=120),
            type_=sa.Enum(*STYLES, name="doctrine", native_enum=False, create_constraint=True, length=40),
            existing_nullable=False,
        )


def downgrade() -> None:
    with op.batch_alter_table("army_profiles", schema=None) as batch_op:
        batch_op.alter_column(
            "doctrine",
            existing_type=sa.Enum(*STYLES, name="doctrine", native_enum=False, create_constraint=True, length=40),
            type_=sa.String(length=120),
            existing_nullable=False,
        )
