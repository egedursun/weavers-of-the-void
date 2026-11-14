import sqlalchemy as sa
from alembic import op

revision = "9f77bcb27682"
down_revision = "b3b8a89e6218"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "ferment_cultures",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("holder_entity_id", sa.Integer(), nullable=False),
        sa.Column(
            "kind", sa.Enum("yeast", "starter", "mould", "lactic", "vinegar", name="kind", native_enum=False, create_constraint=True, length=40), nullable=False
        ),
        sa.Column("quality", sa.Integer(), nullable=False),
        sa.Column("since_epoch", sa.Integer(), nullable=False),
        sa.Column("lost_epoch", sa.Integer(), nullable=True),
        sa.Column("locked", sa.JSON(), nullable=False),
        sa.CheckConstraint("quality BETWEEN 0 AND 100", name=op.f("ck_ferment_cultures_quality_range")),
        sa.CheckConstraint("since_epoch >= 0", name=op.f("ck_ferment_cultures_since_epoch_min")),
        sa.ForeignKeyConstraint(["holder_entity_id"], ["entities.id"], name=op.f("fk_ferment_cultures_holder_entity_id_entities"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_ferment_cultures")),
    )
    with op.batch_alter_table("ferment_cultures", schema=None) as batch_op:
        batch_op.create_index("ix_ferment_cultures_holder", ["holder_entity_id"], unique=False)

    op.create_table(
        "sense_profiles",
        sa.Column("holder_entity_id", sa.Integer(), nullable=False),
        sa.Column(
            "sense",
            sa.Enum(
                "sight",
                "night_vision",
                "smell",
                "hearing",
                "echolocation",
                "vibration",
                "magnetic",
                "spirit_sight",
                "heat",
                name="sense",
                native_enum=False,
                create_constraint=True,
                length=40,
            ),
            nullable=False,
        ),
        sa.Column("acuity", sa.Integer(), nullable=False),
        sa.Column("locked", sa.JSON(), nullable=False),
        sa.CheckConstraint("acuity BETWEEN 0 AND 100", name=op.f("ck_sense_profiles_acuity_range")),
        sa.ForeignKeyConstraint(["holder_entity_id"], ["entities.id"], name=op.f("fk_sense_profiles_holder_entity_id_entities"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("holder_entity_id", "sense", name=op.f("pk_sense_profiles")),
    )
    op.create_table(
        "soil_microbiota",
        sa.Column("region_entity_id", sa.Integer(), nullable=False),
        sa.Column("life", sa.Integer(), nullable=False),
        sa.Column("sterile_epochs", sa.Integer(), nullable=False),
        sa.Column("updated_epoch", sa.Integer(), nullable=False),
        sa.Column("locked", sa.JSON(), nullable=False),
        sa.CheckConstraint("life BETWEEN 0 AND 100", name=op.f("ck_soil_microbiota_life_range")),
        sa.CheckConstraint("sterile_epochs >= 0", name=op.f("ck_soil_microbiota_sterile_epochs_min")),
        sa.CheckConstraint("updated_epoch >= 0", name=op.f("ck_soil_microbiota_updated_epoch_min")),
        sa.ForeignKeyConstraint(["region_entity_id"], ["entities.id"], name=op.f("fk_soil_microbiota_region_entity_id_entities"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("region_entity_id", name=op.f("pk_soil_microbiota")),
    )
    op.create_table(
        "species_relations",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("first_species_id", sa.Integer(), nullable=False),
        sa.Column("second_species_id", sa.Integer(), nullable=False),
        sa.Column(
            "kind",
            sa.Enum("mutualism", "commensalism", "parasitism", "mimicry", name="kind", native_enum=False, create_constraint=True, length=40),
            nullable=False,
        ),
        sa.Column("strength", sa.Integer(), nullable=False),
        sa.Column("since_epoch", sa.Integer(), nullable=False),
        sa.Column("locked", sa.JSON(), nullable=False),
        sa.CheckConstraint("since_epoch >= 0", name=op.f("ck_species_relations_since_epoch_min")),
        sa.CheckConstraint("strength BETWEEN 0 AND 100", name=op.f("ck_species_relations_strength_range")),
        sa.ForeignKeyConstraint(["first_species_id"], ["entities.id"], name=op.f("fk_species_relations_first_species_id_entities"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["second_species_id"], ["entities.id"], name=op.f("fk_species_relations_second_species_id_entities"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_species_relations")),
        sa.UniqueConstraint("first_species_id", "second_species_id", "kind", name="uq_species_relations_pair"),
    )
    with op.batch_alter_table("species_relations", schema=None) as batch_op:
        batch_op.create_index("ix_species_relations_second", ["second_species_id"], unique=False)

    with op.batch_alter_table("people_biology", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column(
                "thermoregulation",
                sa.Enum("endotherm", "ectotherm", name="thermoregulation", native_enum=False, create_constraint=True, length=40),
                nullable=False,
                server_default="endotherm",
            )
        )

    with op.batch_alter_table("plant_profiles", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column(
                "defence",
                sa.Enum("none", "thorns", "toxins", "allelopathy", "carnivorous", name="defence", native_enum=False, create_constraint=True, length=40),
                nullable=False,
                server_default="none",
            )
        )
        batch_op.add_column(sa.Column("defence_potency", sa.Integer(), nullable=False, server_default="0"))
        batch_op.create_check_constraint(op.f("ck_plant_profiles_defence_potency_range"), "defence_potency BETWEEN 0 AND 100")

    with op.batch_alter_table("species_profiles", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column(
                "dormancy",
                sa.Enum("none", "hibernation", "aestivation", name="dormancy", native_enum=False, create_constraint=True, length=40),
                nullable=False,
                server_default="none",
            )
        )
        batch_op.add_column(
            sa.Column(
                "thermoregulation",
                sa.Enum("endotherm", "ectotherm", name="thermoregulation", native_enum=False, create_constraint=True, length=40),
                nullable=False,
                server_default="endotherm",
            )
        )
        batch_op.add_column(sa.Column("woken_epoch", sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column("endemic", sa.Boolean(), nullable=False, server_default=sa.false()))
        batch_op.add_column(sa.Column("relict", sa.Boolean(), nullable=False, server_default=sa.false()))
        batch_op.add_column(sa.Column("island_epochs", sa.Integer(), nullable=False, server_default="0"))
        batch_op.add_column(sa.Column("range_peak", sa.Integer(), nullable=False, server_default="0"))
        batch_op.create_check_constraint(op.f("ck_species_profiles_island_epochs_min"), "island_epochs >= 0")
        batch_op.create_check_constraint(op.f("ck_species_profiles_range_peak_min"), "range_peak >= 0")
    op.execute("UPDATE people_biology SET thermoregulation = 'ectotherm' WHERE traits LIKE '%cold_blooded%'")


def downgrade() -> None:
    with op.batch_alter_table("species_profiles", schema=None) as batch_op:
        for name in ("dormancy", "thermoregulation", "island_epochs_min", "range_peak_min"):
            batch_op.drop_constraint(op.f(f"ck_species_profiles_{name}"), type_="check")
        batch_op.drop_column("range_peak")
        batch_op.drop_column("island_epochs")
        batch_op.drop_column("relict")
        batch_op.drop_column("endemic")
        batch_op.drop_column("woken_epoch")
        batch_op.drop_column("thermoregulation")
        batch_op.drop_column("dormancy")

    with op.batch_alter_table("plant_profiles", schema=None) as batch_op:
        batch_op.drop_constraint(op.f("ck_plant_profiles_defence"), type_="check")
        batch_op.drop_constraint(op.f("ck_plant_profiles_defence_potency_range"), type_="check")
        batch_op.drop_column("defence_potency")
        batch_op.drop_column("defence")

    with op.batch_alter_table("people_biology", schema=None) as batch_op:
        batch_op.drop_constraint(op.f("ck_people_biology_thermoregulation"), type_="check")
        batch_op.drop_column("thermoregulation")

    with op.batch_alter_table("species_relations", schema=None) as batch_op:
        batch_op.drop_index("ix_species_relations_second")

    op.drop_table("species_relations")
    op.drop_table("soil_microbiota")
    op.drop_table("sense_profiles")
    with op.batch_alter_table("ferment_cultures", schema=None) as batch_op:
        batch_op.drop_index("ix_ferment_cultures_holder")

    op.drop_table("ferment_cultures")
