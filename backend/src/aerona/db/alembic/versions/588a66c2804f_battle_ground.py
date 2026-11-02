import sqlalchemy as sa
from alembic import op

revision = "588a66c2804f"
down_revision = "3c72e270d169"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("battles", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column(
                "weather",
                sa.Enum(
                    "clear",
                    "overcast",
                    "rain",
                    "downpour",
                    "storm",
                    "fog",
                    "snow",
                    "blizzard",
                    "heat_wave",
                    "drought_wind",
                    "sandstorm",
                    "hail",
                    "magic_storm",
                    "ash_fall",
                    "void_rain",
                    "eclipse_dark",
                    "aurora",
                    name="weather",
                    native_enum=False,
                    create_constraint=True,
                    length=40,
                ),
                nullable=True,
            )
        )
        batch_op.add_column(sa.Column("season_name", sa.String(length=200), nullable=True))
        batch_op.add_column(
            sa.Column(
                "terrain",
                sa.Enum(
                    "plain",
                    "steppe",
                    "forest",
                    "jungle",
                    "marsh",
                    "hills",
                    "mountains",
                    "high_pass",
                    "desert",
                    "tundra",
                    "ice_sheet",
                    "volcanic",
                    "coast",
                    "island",
                    "river_valley",
                    "canyon",
                    "underground",
                    "crystal_field",
                    "flesh",
                    "void_shore",
                    "ruin_field",
                    "urban",
                    "sea",
                    name="terrain",
                    native_enum=False,
                    create_constraint=True,
                    length=40,
                ),
                nullable=True,
            )
        )
        batch_op.add_column(sa.Column("year", sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column("night", sa.Boolean(), server_default=sa.false(), nullable=False))


def downgrade() -> None:
    with op.batch_alter_table("battles", schema=None) as batch_op:
        batch_op.drop_column("night")
        batch_op.drop_column("year")
        batch_op.drop_column("terrain")
        batch_op.drop_column("season_name")
        batch_op.drop_column("weather")
