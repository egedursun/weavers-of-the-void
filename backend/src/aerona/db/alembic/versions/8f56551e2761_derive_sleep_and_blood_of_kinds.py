from alembic import op

revision = "8f56551e2761"
down_revision = "9f77bcb27682"
branch_labels = None
depends_on = None

HOME = "SELECT {column} FROM region_environment JOIN entities ON entities.location_id = region_environment.entity_id WHERE entities.id = species_profiles.species_entity_id"


def upgrade() -> None:
    op.execute("UPDATE species_profiles SET thermoregulation = 'ectotherm' WHERE body_plan IN ('serpentine', 'insectoid', 'aquatic')")
    op.execute(
        "UPDATE species_profiles SET dormancy = CASE WHEN (" + HOME.format(column="temperature") + ") < 50 THEN 'hibernation' ELSE 'aestivation' END"
        " WHERE dormancy = 'none' AND migratory = 0 AND size_class IN ('tiny', 'small', 'medium') AND species_class NOT IN ('plant', 'fungus')"
        " AND (" + HOME.format(column="seasonality") + ") >= 20"
    )


def downgrade() -> None:
    op.execute("UPDATE species_profiles SET thermoregulation = 'endotherm', dormancy = 'none'")
