import sqlalchemy as sa
from alembic import op

revision = "3ccb476b4bb5"
down_revision = "8e98c75f797c"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "world_cycles",
        sa.Column("world_id", sa.Integer(), nullable=False),
        sa.Column("carbon", sa.Integer(), nullable=False),
        sa.Column("water", sa.Integer(), nullable=False),
        sa.Column("nutrients", sa.Integer(), nullable=False),
        sa.Column("carbon_in", sa.Integer(), nullable=False),
        sa.Column("carbon_out", sa.Integer(), nullable=False),
        sa.Column("water_in", sa.Integer(), nullable=False),
        sa.Column("water_out", sa.Integer(), nullable=False),
        sa.Column("nutrients_in", sa.Integer(), nullable=False),
        sa.Column("nutrients_out", sa.Integer(), nullable=False),
        sa.Column("updated_epoch", sa.Integer(), nullable=False),
        sa.Column("locked", sa.JSON(), nullable=False),
        sa.CheckConstraint("carbon BETWEEN 0 AND 100", name=op.f("ck_world_cycles_carbon_range")),
        sa.CheckConstraint("nutrients BETWEEN 0 AND 100", name=op.f("ck_world_cycles_nutrients_range")),
        sa.CheckConstraint("water BETWEEN 0 AND 100", name=op.f("ck_world_cycles_water_range")),
        sa.ForeignKeyConstraint(["world_id"], ["worlds.id"], name=op.f("fk_world_cycles_world_id_worlds"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("world_id", name=op.f("pk_world_cycles")),
    )
    op.create_table(
        "cure_research",
        sa.Column("institution_entity_id", sa.Integer(), nullable=False),
        sa.Column("disease_entity_id", sa.Integer(), nullable=False),
        sa.Column("points", sa.Integer(), nullable=False),
        sa.Column("specimens", sa.Integer(), nullable=False),
        sa.Column("started_epoch", sa.Integer(), nullable=False),
        sa.Column("cured_epoch", sa.Integer(), nullable=True),
        sa.Column("locked", sa.JSON(), nullable=False),
        sa.CheckConstraint("points >= 0", name=op.f("ck_cure_research_points_min")),
        sa.CheckConstraint("specimens >= 0", name=op.f("ck_cure_research_specimens_min")),
        sa.CheckConstraint("started_epoch >= 0", name=op.f("ck_cure_research_started_epoch_min")),
        sa.ForeignKeyConstraint(["disease_entity_id"], ["entities.id"], name=op.f("fk_cure_research_disease_entity_id_entities"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["institution_entity_id"], ["entities.id"], name=op.f("fk_cure_research_institution_entity_id_entities"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("institution_entity_id", "disease_entity_id", name=op.f("pk_cure_research")),
    )
    op.create_table(
        "disease_carriers",
        sa.Column("mortal_entity_id", sa.Integer(), nullable=False),
        sa.Column("disease_entity_id", sa.Integer(), nullable=False),
        sa.Column("home_region_id", sa.Integer(), nullable=True),
        sa.Column("identified", sa.Boolean(), nullable=False),
        sa.Column("seeded", sa.Integer(), nullable=False),
        sa.Column("since_epoch", sa.Integer(), nullable=False),
        sa.Column("locked", sa.JSON(), nullable=False),
        sa.CheckConstraint("since_epoch >= 0", name=op.f("ck_disease_carriers_since_epoch_min")),
        sa.ForeignKeyConstraint(["disease_entity_id"], ["entities.id"], name=op.f("fk_disease_carriers_disease_entity_id_entities"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["home_region_id"], ["entities.id"], name=op.f("fk_disease_carriers_home_region_id_entities"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["mortal_entity_id"], ["entities.id"], name=op.f("fk_disease_carriers_mortal_entity_id_entities"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("mortal_entity_id", "disease_entity_id", name=op.f("pk_disease_carriers")),
    )
    with op.batch_alter_table("disease_carriers", schema=None) as batch_op:
        batch_op.create_index("ix_disease_carriers_disease", ["disease_entity_id"], unique=False)

    op.create_table(
        "ecosystem_services",
        sa.Column("region_entity_id", sa.Integer(), nullable=False),
        sa.Column(
            "role",
            sa.Enum("pollinator", "soil_maker", "dam_builder", "scavenger", name="role", native_enum=False, create_constraint=True, length=40),
            nullable=False,
        ),
        sa.Column("species_entity_id", sa.Integer(), nullable=True),
        sa.Column("strength", sa.Integer(), nullable=False),
        sa.Column("epoch", sa.Integer(), nullable=False),
        sa.Column("locked", sa.JSON(), nullable=False),
        sa.CheckConstraint("strength BETWEEN 0 AND 100", name=op.f("ck_ecosystem_services_strength_range")),
        sa.ForeignKeyConstraint(["region_entity_id"], ["entities.id"], name=op.f("fk_ecosystem_services_region_entity_id_entities"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["species_entity_id"], ["entities.id"], name=op.f("fk_ecosystem_services_species_entity_id_entities"), ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("region_entity_id", "role", name=op.f("pk_ecosystem_services")),
    )
    op.create_table(
        "lineage_marks",
        sa.Column("species_entity_id", sa.Integer(), nullable=False),
        sa.Column(
            "package",
            sa.Enum(
                "snake_venom",
                "drink_dependence",
                "drug_dependence",
                "lycanthropy",
                "vampirism",
                "divine_blessing",
                "void_taint",
                "possession",
                "trauma",
                "hunger_curse",
                "warping",
                "vis_dependence",
                "geas_doom",
                "soul_trapped",
                name="package",
                native_enum=False,
                create_constraint=True,
                length=40,
            ),
            nullable=False,
        ),
        sa.Column("blessing", sa.Boolean(), nullable=False),
        sa.Column("source_node_id", sa.Integer(), nullable=True),
        sa.Column("epoch", sa.Integer(), nullable=False),
        sa.Column("locked", sa.JSON(), nullable=False),
        sa.CheckConstraint("epoch >= 0", name=op.f("ck_lineage_marks_epoch_min")),
        sa.ForeignKeyConstraint(["source_node_id"], ["nodes.id"], name=op.f("fk_lineage_marks_source_node_id_nodes"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["species_entity_id"], ["entities.id"], name=op.f("fk_lineage_marks_species_entity_id_entities"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("species_entity_id", "package", name=op.f("pk_lineage_marks")),
    )
    op.create_table(
        "plague_responses",
        sa.Column("community_entity_id", sa.Integer(), nullable=False),
        sa.Column("disease_entity_id", sa.Integer(), nullable=False),
        sa.Column(
            "response",
            sa.Enum(
                "close_borders",
                "quarantine",
                "burn_dead",
                "expel_sick",
                "prayer",
                "seek_cure",
                name="response",
                native_enum=False,
                create_constraint=True,
                length=40,
            ),
            nullable=False,
        ),
        sa.Column("strength", sa.Integer(), nullable=False),
        sa.Column("since_epoch", sa.Integer(), nullable=False),
        sa.Column("until_epoch", sa.Integer(), nullable=True),
        sa.Column("locked", sa.JSON(), nullable=False),
        sa.CheckConstraint("since_epoch >= 0", name=op.f("ck_plague_responses_since_epoch_min")),
        sa.CheckConstraint("strength BETWEEN 0 AND 100", name=op.f("ck_plague_responses_strength_range")),
        sa.ForeignKeyConstraint(["community_entity_id"], ["entities.id"], name=op.f("fk_plague_responses_community_entity_id_entities"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["disease_entity_id"], ["entities.id"], name=op.f("fk_plague_responses_disease_entity_id_entities"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("community_entity_id", "disease_entity_id", "response", name=op.f("pk_plague_responses")),
    )
    op.create_table(
        "species_traits",
        sa.Column("species_entity_id", sa.Integer(), nullable=False),
        sa.Column("region_entity_id", sa.Integer(), nullable=False),
        sa.Column(
            "trait",
            sa.Enum(
                "size",
                "speed",
                "armour",
                "venom",
                "camouflage",
                "cold_tolerance",
                "intelligence",
                "fecundity",
                "wariness",
                name="trait",
                native_enum=False,
                create_constraint=True,
                length=40,
            ),
            nullable=False,
        ),
        sa.Column("mean", sa.Integer(), nullable=False),
        sa.Column("variance", sa.Integer(), nullable=False),
        sa.Column("updated_epoch", sa.Integer(), nullable=False),
        sa.Column("locked", sa.JSON(), nullable=False),
        sa.CheckConstraint("mean BETWEEN 0 AND 100", name=op.f("ck_species_traits_mean_range")),
        sa.CheckConstraint("variance BETWEEN 0 AND 50", name=op.f("ck_species_traits_variance_range")),
        sa.ForeignKeyConstraint(["region_entity_id"], ["entities.id"], name=op.f("fk_species_traits_region_entity_id_entities"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["species_entity_id"], ["entities.id"], name=op.f("fk_species_traits_species_entity_id_entities"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("species_entity_id", "region_entity_id", "trait", name=op.f("pk_species_traits")),
    )
    with op.batch_alter_table("species_traits", schema=None) as batch_op:
        batch_op.create_index("ix_species_traits_region", ["region_entity_id"], unique=False)

    op.create_table(
        "trophic_levels",
        sa.Column("region_entity_id", sa.Integer(), nullable=False),
        sa.Column(
            "level", sa.Enum("producer", "herbivore", "carnivore", "apex", name="level", native_enum=False, create_constraint=True, length=40), nullable=False
        ),
        sa.Column("biomass", sa.Integer(), nullable=False),
        sa.Column("cap", sa.Integer(), nullable=False),
        sa.Column("epoch", sa.Integer(), nullable=False),
        sa.CheckConstraint("biomass >= 0", name=op.f("ck_trophic_levels_biomass_min")),
        sa.CheckConstraint("cap >= 0", name=op.f("ck_trophic_levels_cap_min")),
        sa.ForeignKeyConstraint(["region_entity_id"], ["entities.id"], name=op.f("fk_trophic_levels_region_entity_id_entities"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("region_entity_id", "level", name=op.f("pk_trophic_levels")),
    )
    with op.batch_alter_table("disease_profiles", schema=None) as batch_op:
        batch_op.add_column(sa.Column("cold_tolerance", sa.Integer(), server_default="50", nullable=False))
        batch_op.add_column(sa.Column("heat_tolerance", sa.Integer(), server_default="50", nullable=False))
        batch_op.add_column(sa.Column("resistance", sa.Integer(), server_default="0", nullable=False))

    with op.batch_alter_table("region_environment", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column(
                "succession",
                sa.Enum(
                    "bare",
                    "grassland",
                    "shrubland",
                    "young_forest",
                    "old_forest",
                    "marsh",
                    "swamp_forest",
                    name="succession",
                    native_enum=False,
                    create_constraint=True,
                    length=40,
                ),
                server_default="grassland",
                nullable=False,
            )
        )
        batch_op.add_column(sa.Column("succession_progress", sa.Integer(), server_default="0", nullable=False))
        batch_op.add_column(sa.Column("burned_epoch", sa.Integer(), nullable=True))

    with op.batch_alter_table("species_profiles", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column(
                "keystone",
                sa.Enum("pollinator", "soil_maker", "dam_builder", "scavenger", name="keystone", native_enum=False, create_constraint=True, length=40),
                nullable=True,
            )
        )
        batch_op.add_column(sa.Column("feral_epoch", sa.Integer(), nullable=True))
    land = sa.table("region_environment", sa.column("succession"), sa.column("wetland"), sa.column("forest_cover"), sa.column("soil_fertility"))
    stage = sa.case(
        (sa.and_(land.c.wetland >= 40, land.c.forest_cover >= 40), "swamp_forest"),
        (land.c.wetland >= 40, "marsh"),
        (land.c.forest_cover >= 60, "old_forest"),
        (land.c.forest_cover >= 35, "young_forest"),
        (land.c.forest_cover >= 15, "shrubland"),
        (sa.and_(land.c.forest_cover < 5, land.c.soil_fertility < 10), "bare"),
        else_="grassland",
    )
    op.execute(land.update().values(succession=stage))


def downgrade() -> None:
    with op.batch_alter_table("species_profiles", schema=None) as batch_op:
        batch_op.drop_column("feral_epoch")
        batch_op.drop_column("keystone")

    with op.batch_alter_table("region_environment", schema=None) as batch_op:
        batch_op.drop_column("burned_epoch")
        batch_op.drop_column("succession_progress")
        batch_op.drop_column("succession")

    with op.batch_alter_table("disease_profiles", schema=None) as batch_op:
        batch_op.drop_column("resistance")
        batch_op.drop_column("heat_tolerance")
        batch_op.drop_column("cold_tolerance")

    op.drop_table("trophic_levels")
    with op.batch_alter_table("species_traits", schema=None) as batch_op:
        batch_op.drop_index("ix_species_traits_region")

    op.drop_table("species_traits")
    op.drop_table("plague_responses")
    op.drop_table("lineage_marks")
    op.drop_table("ecosystem_services")
    with op.batch_alter_table("disease_carriers", schema=None) as batch_op:
        batch_op.drop_index("ix_disease_carriers_disease")

    op.drop_table("disease_carriers")
    op.drop_table("cure_research")
    op.drop_table("world_cycles")
