import sqlalchemy as sa
from alembic import op

revision = "5047b9741d7f"
down_revision = "e6776762e09f"
branch_labels = None
depends_on = None

OLD_GOODS = (
    "grain",
    "livestock",
    "fish",
    "fodder",
    "timber",
    "fuel",
    "bread",
    "ore",
    "stone",
    "cloth",
    "tools",
    "weapons",
    "armour",
    "mounts",
    "siege_materiel",
    "medicine",
    "luxuries",
    "incense",
    "sacred_goods",
    "magical_reagents",
    "meat",
    "milk",
    "cheese",
    "fruit",
    "tubers",
    "coal",
    "peat",
    "dung",
)
NEW_GOODS = (*OLD_GOODS, "fibre", "dye", "herbs", "brew_base", "poison", "eggs", "wool")
OLD_USES = ("food", "labour", "mount", "war", "guard", "companion", "sacrifice", "magic")
NEW_USES = (*OLD_USES, "pest_control")
GOODS_COLUMNS = (
    ("community_stocks", "commodity", False),
    ("resource_profiles", "commodity", False),
    ("market_prices", "commodity", False),
    ("market_price_holds", "commodity", False),
    ("mandates", "commodity", True),
    ("trade_flows", "commodity", False),
    ("trade_route_losses", "commodity", False),
    ("community_needs", "commodity", False),
    ("goods_flows", "commodity", False),
    ("labour_reasons", "commodity", True),
    ("species_yields", "commodity", True),
    ("company_profiles", "commodity", True),
    ("production_runs", "output", False),
    ("production_runs", "bottleneck", True),
    ("structure_designs", "upkeep_commodity", True),
    ("people_biology", "staple", False),
    ("war_production", "commodity", False),
    ("trade_policies", "commodity", True),
    ("speculations", "commodity", False),
)
USE_COLUMNS = (("species_uses", "use", False), ("species_use_kinds", "base_use", False))


def widen(old: bool) -> None:
    for columns, narrow, wide in ((GOODS_COLUMNS, OLD_GOODS, NEW_GOODS), (USE_COLUMNS, OLD_USES, NEW_USES)):
        before, after = (wide, narrow) if old else (narrow, wide)
        for table, column, nullable in columns:
            with op.batch_alter_table(table, schema=None) as batch_op:
                batch_op.alter_column(
                    column,
                    existing_type=sa.Enum(*before, name=column, native_enum=False, create_constraint=True, length=40),
                    type_=sa.Enum(*after, name=column, native_enum=False, create_constraint=True, length=40),
                    existing_nullable=nullable,
                )


def upgrade() -> None:
    widen(old=False)
    op.create_table(
        "world_biochemistries",
        sa.Column("world_id", sa.Integer(), nullable=False),
        sa.Column(
            "biochemistry",
            sa.Enum(
                "carbon_water",
                "carbon_ammonia",
                "silicon",
                "crystal",
                "void",
                "spirit",
                name="biochemistry",
                native_enum=False,
                create_constraint=True,
                length=40,
            ),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["world_id"], ["worlds.id"], name=op.f("fk_world_biochemistries_world_id_worlds"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("world_id", "biochemistry", name=op.f("pk_world_biochemistries")),
    )
    op.create_table(
        "crop_pests",
        sa.Column("plant_entity_id", sa.Integer(), nullable=False),
        sa.Column("pest_entity_id", sa.Integer(), nullable=False),
        sa.Column("since_epoch", sa.Integer(), nullable=False),
        sa.Column("locked", sa.JSON(), nullable=False),
        sa.ForeignKeyConstraint(["pest_entity_id"], ["entities.id"], name=op.f("fk_crop_pests_pest_entity_id_entities"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["plant_entity_id"], ["entities.id"], name=op.f("fk_crop_pests_plant_entity_id_entities"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("plant_entity_id", "pest_entity_id", name=op.f("pk_crop_pests")),
    )
    op.create_table(
        "plant_profiles",
        sa.Column("species_entity_id", sa.Integer(), nullable=False),
        sa.Column(
            "growth_cycle", sa.Enum("annual", "perennial", "tree", name="growth_cycle", native_enum=False, create_constraint=True, length=40), nullable=False
        ),
        sa.Column("growing_seasons", sa.Integer(), nullable=False),
        sa.Column("soil_need", sa.Integer(), nullable=False),
        sa.Column(
            "cultivation",
            sa.Enum("wild", "gathered", "cultivated", "cultivar", name="cultivation", native_enum=False, create_constraint=True, length=40),
            nullable=False,
        ),
        sa.Column("cultivar_of_id", sa.Integer(), nullable=True),
        sa.Column("since_epoch", sa.Integer(), nullable=False),
        sa.Column("locked", sa.JSON(), nullable=False),
        sa.CheckConstraint("growing_seasons >= 1", name=op.f("ck_plant_profiles_growing_seasons_min")),
        sa.CheckConstraint("soil_need BETWEEN 0 AND 100", name=op.f("ck_plant_profiles_soil_need_range")),
        sa.ForeignKeyConstraint(["cultivar_of_id"], ["entities.id"], name=op.f("fk_plant_profiles_cultivar_of_id_entities"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["species_entity_id"], ["entities.id"], name=op.f("fk_plant_profiles_species_entity_id_entities"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("species_entity_id", name=op.f("pk_plant_profiles")),
    )
    op.create_table(
        "region_crops",
        sa.Column("region_entity_id", sa.Integer(), nullable=False),
        sa.Column("plant_entity_id", sa.Integer(), nullable=False),
        sa.Column("share", sa.Integer(), nullable=False),
        sa.Column("since_epoch", sa.Integer(), nullable=False),
        sa.Column("locked", sa.JSON(), nullable=False),
        sa.CheckConstraint("share BETWEEN 0 AND 100", name=op.f("ck_region_crops_share_range")),
        sa.ForeignKeyConstraint(["plant_entity_id"], ["entities.id"], name=op.f("fk_region_crops_plant_entity_id_entities"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["region_entity_id"], ["entities.id"], name=op.f("fk_region_crops_region_entity_id_entities"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("region_entity_id", "plant_entity_id", name=op.f("pk_region_crops")),
    )
    with op.batch_alter_table("species_profiles", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column(
                "species_class",
                sa.Enum("animal", "plant", "fungus", "vermin", name="species_class", native_enum=False, create_constraint=True, length=40),
                nullable=False,
                server_default="animal",
            )
        )
        batch_op.add_column(
            sa.Column(
                "biochemistry",
                sa.Enum(
                    "carbon_water",
                    "carbon_ammonia",
                    "silicon",
                    "crystal",
                    "void",
                    "spirit",
                    name="biochemistry",
                    native_enum=False,
                    create_constraint=True,
                    length=40,
                ),
                nullable=False,
                server_default="carbon_water",
            )
        )


def downgrade() -> None:
    with op.batch_alter_table("species_profiles", schema=None) as batch_op:
        batch_op.drop_column("biochemistry")
        batch_op.drop_column("species_class")

    op.drop_table("region_crops")
    op.drop_table("plant_profiles")
    op.drop_table("crop_pests")
    op.drop_table("world_biochemistries")
    widen(old=True)
