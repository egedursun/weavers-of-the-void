import sqlalchemy as sa
from alembic import op

revision = "39ded63f7c3f"
down_revision = "c3567396253d"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "world_type_profiles",
        sa.Column("world_id", sa.Integer(), nullable=False),
        sa.Column(
            "light",
            sa.Enum(
                "star",
                "lava_glow",
                "magic",
                "inner_sun",
                "divine",
                "ship_cycle",
                "fading_god",
                "none",
                name="light",
                native_enum=False,
                create_constraint=True,
                length=40,
            ),
            nullable=False,
        ),
        sa.Column(
            "need",
            sa.Enum("none", "water", "heat", "air", "offerings", "belief", name="need", native_enum=False, create_constraint=True, length=40),
            nullable=False,
        ),
        sa.Column(
            "settle",
            sa.Enum(
                "ground", "floating", "stilt", "oasis", "vent", "habitat", "band", "deck", name="settle", native_enum=False, create_constraint=True, length=40
            ),
            nullable=False,
        ),
        sa.Column(
            "war", sa.Enum("land", "naval", "sky", "boarding", "strata", name="war", native_enum=False, create_constraint=True, length=40), nullable=False
        ),
        sa.Column("seasons", sa.Boolean(), nullable=False),
        sa.Column("nights", sa.Boolean(), nullable=False),
        sa.Column("fire", sa.Boolean(), nullable=False),
        sa.Column("soil", sa.Boolean(), nullable=False),
        sa.Column("timber_pct", sa.Integer(), nullable=False),
        sa.Column("food_need_pct", sa.Integer(), nullable=False),
        sa.Column("capacity_pct", sa.Integer(), nullable=False),
        sa.Column("ore_yield_pct", sa.Integer(), nullable=False),
        sa.Column("storm_pct", sa.Integer(), nullable=False),
        sa.Column("quake_pct", sa.Integer(), nullable=False),
        sa.Column("flood_pct", sa.Integer(), nullable=False),
        sa.Column("drought_pct", sa.Integer(), nullable=False),
        sa.Column("plague_pct", sa.Integer(), nullable=False),
        sa.Column("route_danger", sa.Integer(), nullable=False),
        sa.Column("leak", sa.Integer(), nullable=False),
        sa.Column("leak_repair", sa.Integer(), nullable=False),
        sa.Column("sanity_erosion", sa.Integer(), nullable=False),
        sa.Column("fertility_decay", sa.Integer(), nullable=False),
        sa.Column("updated_epoch", sa.Integer(), nullable=False),
        sa.Column("locked", sa.JSON(), nullable=False),
        sa.CheckConstraint("capacity_pct BETWEEN 0 AND 500", name=op.f("ck_world_type_profiles_capacity_pct_range")),
        sa.CheckConstraint("drought_pct BETWEEN 0 AND 500", name=op.f("ck_world_type_profiles_drought_pct_range")),
        sa.CheckConstraint("fertility_decay BETWEEN 0 AND 100", name=op.f("ck_world_type_profiles_fertility_decay_range")),
        sa.CheckConstraint("flood_pct BETWEEN 0 AND 500", name=op.f("ck_world_type_profiles_flood_pct_range")),
        sa.CheckConstraint("food_need_pct BETWEEN 0 AND 500", name=op.f("ck_world_type_profiles_food_need_pct_range")),
        sa.CheckConstraint("leak BETWEEN 0 AND 100", name=op.f("ck_world_type_profiles_leak_range")),
        sa.CheckConstraint("leak_repair BETWEEN 0 AND 100", name=op.f("ck_world_type_profiles_leak_repair_range")),
        sa.CheckConstraint("ore_yield_pct BETWEEN 0 AND 500", name=op.f("ck_world_type_profiles_ore_yield_pct_range")),
        sa.CheckConstraint("plague_pct BETWEEN 0 AND 500", name=op.f("ck_world_type_profiles_plague_pct_range")),
        sa.CheckConstraint("quake_pct BETWEEN 0 AND 500", name=op.f("ck_world_type_profiles_quake_pct_range")),
        sa.CheckConstraint("route_danger BETWEEN 0 AND 100", name=op.f("ck_world_type_profiles_route_danger_range")),
        sa.CheckConstraint("sanity_erosion BETWEEN 0 AND 100", name=op.f("ck_world_type_profiles_sanity_erosion_range")),
        sa.CheckConstraint("storm_pct BETWEEN 0 AND 500", name=op.f("ck_world_type_profiles_storm_pct_range")),
        sa.CheckConstraint("timber_pct BETWEEN 0 AND 500", name=op.f("ck_world_type_profiles_timber_pct_range")),
        sa.CheckConstraint("updated_epoch >= 0", name=op.f("ck_world_type_profiles_updated_epoch_min")),
        sa.ForeignKeyConstraint(["world_id"], ["worlds.id"], name=op.f("fk_world_type_profiles_world_id_worlds"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("world_id", name=op.f("pk_world_type_profiles")),
    )


def downgrade() -> None:
    op.drop_table("world_type_profiles")
