import sqlalchemy as sa
from alembic import op

revision = "7e3748499664"
down_revision = "b2d4f6a8c0e1"
branch_labels = None
depends_on = None

PROCESSES = (
    "farming",
    "fishing",
    "logging",
    "mining",
    "milling",
    "weaving",
    "smelting",
    "tanning",
    "brewing",
    "distilling",
    "masonry",
    "charcoal",
    "preserving",
)

METHODS = (
    "hand_sickle",
    "ox_plough",
    "irrigated_terraces",
    "crop_rotation",
    "divine_harvest",
    "line_and_net",
    "fish_weirs",
    "deep_sea_fleets",
    "axe_felling",
    "water_sawmill",
    "pick_and_shovel",
    "fire_setting",
    "pumped_shafts",
    "earth_shaping",
    "hand_quern",
    "watermill",
    "windmill",
    "hand_loom",
    "water_frame",
    "bloomery",
    "blast_furnace",
    "divine_forge",
    "pit_tanning",
    "oil_curing",
    "open_vat",
    "cellar_brewing",
    "herbal_still",
    "arcane_alembic",
    "hand_chisel",
    "water_saw",
    "clamp_kiln",
    "retort_kiln",
    "salting",
    "smoking",
    "drying",
    "icing",
    "magic_keeping",
)

ENERGY = ("muscle", "water", "wind", "heat", "magic", "divine")
POLLUTION = ("air", "water", "soil")


def enum(values: tuple[str, ...], name: str) -> sa.Enum:
    return sa.Enum(*values, name=name, native_enum=False, create_constraint=True, length=40)


def node_fk(table: str, column: str) -> sa.ForeignKeyConstraint:
    return sa.ForeignKeyConstraint([column], ["nodes.id"], name=op.f(f"fk_{table}_{column}_nodes"), ondelete="CASCADE")


def upgrade() -> None:
    op.create_table(
        "community_methods",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("community_node_id", sa.Integer(), nullable=False),
        sa.Column("process", enum(PROCESSES, "process"), nullable=False),
        sa.Column("method", enum(METHODS, "method"), nullable=False),
        sa.Column("adopted_epoch", sa.Integer(), nullable=False),
        sa.Column("displaced", sa.Integer(), nullable=False),
        sa.Column("locked", sa.JSON(), nullable=False),
        sa.CheckConstraint("adopted_epoch >= 0", name=op.f("ck_community_methods_adopted_epoch_min")),
        sa.CheckConstraint("displaced >= 0", name=op.f("ck_community_methods_displaced_min")),
        node_fk("community_methods", "community_node_id"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_community_methods")),
        sa.UniqueConstraint("community_node_id", "process", name="uq_community_methods_community_process"),
    )
    with op.batch_alter_table("community_methods", schema=None) as batch_op:
        batch_op.create_index(batch_op.f("ix_community_methods_community_node_id"), ["community_node_id"], unique=False)
    op.create_table(
        "community_industry",
        sa.Column("community_node_id", sa.Integer(), nullable=False),
        *(sa.Column(column, sa.Integer(), nullable=False) for column in ENERGY),
        sa.Column("spent", sa.JSON(), nullable=False),
        sa.Column("short", sa.JSON(), nullable=False),
        sa.Column("heat_need", sa.Integer(), nullable=False),
        sa.Column("tools_worn", sa.Integer(), nullable=False),
        sa.Column("spoiled", sa.Integer(), nullable=False),
        sa.Column("preserved", sa.Integer(), nullable=False),
        sa.Column("meal_quality", sa.Integer(), nullable=False),
        sa.Column("epoch", sa.Integer(), nullable=False),
        sa.Column("locked", sa.JSON(), nullable=False),
        *(sa.CheckConstraint(f"{column} >= 0", name=op.f(f"ck_community_industry_{column}_min")) for column in ENERGY),
        *(
            sa.CheckConstraint(f"{column} >= 0", name=op.f(f"ck_community_industry_{column}_min"))
            for column in ("heat_need", "tools_worn", "spoiled", "preserved", "epoch")
        ),
        sa.CheckConstraint("meal_quality BETWEEN 0 AND 100", name=op.f("ck_community_industry_meal_quality_range")),
        node_fk("community_industry", "community_node_id"),
        sa.PrimaryKeyConstraint("community_node_id", name=op.f("pk_community_industry")),
    )
    op.create_table(
        "region_pollution",
        sa.Column("region_node_id", sa.Integer(), nullable=False),
        *(sa.Column(column, sa.Integer(), nullable=False) for column in POLLUTION),
        sa.Column("polluters", sa.JSON(), nullable=False),
        sa.Column("epoch", sa.Integer(), nullable=False),
        sa.Column("locked", sa.JSON(), nullable=False),
        *(sa.CheckConstraint(f"{column} BETWEEN 0 AND 100", name=op.f(f"ck_region_pollution_{column}_range")) for column in POLLUTION),
        sa.CheckConstraint("epoch >= 0", name=op.f("ck_region_pollution_epoch_min")),
        node_fk("region_pollution", "region_node_id"),
        sa.PrimaryKeyConstraint("region_node_id", name=op.f("pk_region_pollution")),
    )
    with op.batch_alter_table("community_stocks", schema=None) as batch_op:
        batch_op.add_column(sa.Column("preserved", sa.Integer(), server_default="0", nullable=False))
    with op.batch_alter_table("production_runs", schema=None) as batch_op:
        batch_op.add_column(sa.Column("method", enum(METHODS, "method"), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("production_runs", schema=None) as batch_op:
        batch_op.drop_column("method")
    with op.batch_alter_table("community_stocks", schema=None) as batch_op:
        batch_op.drop_column("preserved")
    op.drop_table("region_pollution")
    op.drop_table("community_industry")
    with op.batch_alter_table("community_methods", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_community_methods_community_node_id"))
    op.drop_table("community_methods")
