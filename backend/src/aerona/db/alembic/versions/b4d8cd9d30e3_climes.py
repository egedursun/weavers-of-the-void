import sqlalchemy as sa
from alembic import op

revision = "b4d8cd9d30e3"
down_revision = "cefc0f2744f7"
branch_labels = None
depends_on = None

CHANNELS_BEFORE = ("witness", "route", "pilgrimage", "journey", "spy", "planted")
CHANNELS_AFTER = (*CHANNELS_BEFORE, "current")


def widen(forward: bool) -> None:
    before, after = (CHANNELS_BEFORE, CHANNELS_AFTER) if forward else (CHANNELS_AFTER, CHANNELS_BEFORE)
    with op.batch_alter_table("rumours", schema=None) as batch_op:
        batch_op.alter_column(
            "channel",
            existing_type=sa.Enum(*before, name="channel", native_enum=False, create_constraint=True, length=40),
            type_=sa.Enum(*after, name="channel", native_enum=False, create_constraint=True, length=40),
            existing_nullable=False,
        )


def upgrade() -> None:
    widen(True)
    op.create_table(
        "climate_oscillations",
        sa.Column("world_id", sa.Integer(), nullable=False),
        sa.Column("phase", sa.Enum("neutral", "warm", "cold", name="phase", native_enum=False, create_constraint=True, length=40), nullable=False),
        sa.Column("period", sa.Integer(), nullable=False),
        sa.Column("step", sa.Integer(), nullable=False),
        sa.Column("strength", sa.Integer(), nullable=False),
        sa.Column("locked", sa.JSON(), nullable=False),
        sa.CheckConstraint("period BETWEEN 2 AND 100", name=op.f("ck_climate_oscillations_period_range")),
        sa.CheckConstraint("step >= 0", name=op.f("ck_climate_oscillations_step_min")),
        sa.CheckConstraint("strength BETWEEN 0 AND 100", name=op.f("ck_climate_oscillations_strength_range")),
        sa.ForeignKeyConstraint(["world_id"], ["worlds.id"], name=op.f("fk_climate_oscillations_world_id_worlds"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("world_id", name=op.f("pk_climate_oscillations")),
    )
    op.create_table(
        "launch_windows",
        sa.Column("from_world_id", sa.Integer(), nullable=False),
        sa.Column("to_world_id", sa.Integer(), nullable=False),
        sa.Column("synodic", sa.Integer(), nullable=False),
        sa.Column("offset", sa.Integer(), nullable=False),
        sa.Column("open", sa.Boolean(), nullable=False),
        sa.Column("locked", sa.JSON(), nullable=False),
        sa.CheckConstraint("offset >= 0", name=op.f("ck_launch_windows_offset_min")),
        sa.CheckConstraint("synodic BETWEEN 1 AND 100", name=op.f("ck_launch_windows_synodic_range")),
        sa.ForeignKeyConstraint(["from_world_id"], ["worlds.id"], name=op.f("fk_launch_windows_from_world_id_worlds"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["to_world_id"], ["worlds.id"], name=op.f("fk_launch_windows_to_world_id_worlds"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("from_world_id", "to_world_id", name=op.f("pk_launch_windows")),
    )
    op.create_table(
        "monsoon_seasons",
        sa.Column("world_id", sa.Integer(), nullable=False),
        sa.Column("epoch", sa.Integer(), nullable=False),
        sa.Column("strength", sa.Integer(), nullable=False),
        sa.Column("failed", sa.Boolean(), nullable=False),
        sa.Column("locked", sa.JSON(), nullable=False),
        sa.CheckConstraint("epoch >= 0", name=op.f("ck_monsoon_seasons_epoch_min")),
        sa.CheckConstraint("strength BETWEEN 0 AND 200", name=op.f("ck_monsoon_seasons_strength_range")),
        sa.ForeignKeyConstraint(["world_id"], ["worlds.id"], name=op.f("fk_monsoon_seasons_world_id_worlds"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("world_id", "epoch", name=op.f("pk_monsoon_seasons")),
    )
    op.create_table(
        "region_winds",
        sa.Column("region_entity_id", sa.Integer(), nullable=False),
        sa.Column(
            "band",
            sa.Enum("trade", "westerly", "polar", "single_cell", "terminator", "still", name="band", native_enum=False, create_constraint=True, length=40),
            nullable=False,
        ),
        sa.Column("wind_from", sa.Integer(), nullable=False),
        sa.Column("strength", sa.Integer(), nullable=False),
        sa.Column("windward", sa.Boolean(), nullable=False),
        sa.Column("shadow", sa.Integer(), nullable=False),
        sa.Column("monsoon", sa.Integer(), nullable=False),
        sa.Column("upwelling", sa.Boolean(), nullable=False),
        sa.Column("read_epoch", sa.Integer(), nullable=False),
        sa.Column("locked", sa.JSON(), nullable=False),
        sa.CheckConstraint("monsoon BETWEEN 0 AND 100", name=op.f("ck_region_winds_monsoon_range")),
        sa.CheckConstraint("read_epoch >= 0", name=op.f("ck_region_winds_read_epoch_min")),
        sa.CheckConstraint("shadow BETWEEN 0 AND 100", name=op.f("ck_region_winds_shadow_range")),
        sa.CheckConstraint("strength BETWEEN 0 AND 100", name=op.f("ck_region_winds_strength_range")),
        sa.CheckConstraint("wind_from BETWEEN 0 AND 7", name=op.f("ck_region_winds_wind_from_range")),
        sa.ForeignKeyConstraint(["region_entity_id"], ["entities.id"], name=op.f("fk_region_winds_region_entity_id_entities"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("region_entity_id", name=op.f("pk_region_winds")),
    )
    op.create_table(
        "cosmopolitan_cultures",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("route_id", sa.Integer(), nullable=True),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("lingua_franca_entity_id", sa.Integer(), nullable=True),
        sa.Column("strength", sa.Integer(), nullable=False),
        sa.Column("values", sa.JSON(), nullable=False),
        sa.Column("formed_epoch", sa.Integer(), nullable=False),
        sa.Column("locked", sa.JSON(), nullable=False),
        sa.CheckConstraint("formed_epoch >= 0", name=op.f("ck_cosmopolitan_cultures_formed_epoch_min")),
        sa.CheckConstraint("strength BETWEEN 0 AND 100", name=op.f("ck_cosmopolitan_cultures_strength_range")),
        sa.ForeignKeyConstraint(
            ["lingua_franca_entity_id"], ["entities.id"], name=op.f("fk_cosmopolitan_cultures_lingua_franca_entity_id_entities"), ondelete="SET NULL"
        ),
        sa.ForeignKeyConstraint(["route_id"], ["routes.id"], name=op.f("fk_cosmopolitan_cultures_route_id_routes"), ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_cosmopolitan_cultures")),
    )
    with op.batch_alter_table("cosmopolitan_cultures", schema=None) as batch_op:
        batch_op.create_index("ix_cosmopolitan_cultures_route", ["route_id"], unique=False)

    op.create_table(
        "cosmopolitan_members",
        sa.Column("culture_id", sa.Integer(), nullable=False),
        sa.Column("community_entity_id", sa.Integer(), nullable=False),
        sa.Column("share", sa.Integer(), nullable=False),
        sa.Column("joined_epoch", sa.Integer(), nullable=False),
        sa.Column("locked", sa.JSON(), nullable=False),
        sa.CheckConstraint("joined_epoch >= 0", name=op.f("ck_cosmopolitan_members_joined_epoch_min")),
        sa.CheckConstraint("share BETWEEN 0 AND 100", name=op.f("ck_cosmopolitan_members_share_range")),
        sa.ForeignKeyConstraint(
            ["community_entity_id"], ["entities.id"], name=op.f("fk_cosmopolitan_members_community_entity_id_entities"), ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["culture_id"], ["cosmopolitan_cultures.id"], name=op.f("fk_cosmopolitan_members_culture_id_cosmopolitan_cultures"), ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("culture_id", "community_entity_id", name=op.f("pk_cosmopolitan_members")),
    )
    with op.batch_alter_table("cosmopolitan_members", schema=None) as batch_op:
        batch_op.create_index(batch_op.f("ix_cosmopolitan_members_community_entity_id"), ["community_entity_id"], unique=False)


def downgrade() -> None:
    op.execute("DELETE FROM rumours WHERE channel = 'current'")
    widen(False)
    with op.batch_alter_table("cosmopolitan_members", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_cosmopolitan_members_community_entity_id"))

    op.drop_table("cosmopolitan_members")
    with op.batch_alter_table("cosmopolitan_cultures", schema=None) as batch_op:
        batch_op.drop_index("ix_cosmopolitan_cultures_route")

    op.drop_table("cosmopolitan_cultures")
    op.drop_table("region_winds")
    op.drop_table("monsoon_seasons")
    op.drop_table("launch_windows")
    op.drop_table("climate_oscillations")
