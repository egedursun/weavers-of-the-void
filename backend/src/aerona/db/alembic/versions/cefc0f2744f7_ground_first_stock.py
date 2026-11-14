import sqlalchemy as sa
from alembic import op

revision = "cefc0f2744f7"
down_revision = "d4845e88e7b8"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("catch_grounds", schema=None) as batch_op:
        batch_op.add_column(sa.Column("first_stock", sa.Integer(), server_default="100", nullable=False))
        batch_op.create_check_constraint(op.f("ck_catch_grounds_first_stock_min"), "first_stock >= 1")
    op.execute(
        "UPDATE catch_grounds SET first_stock = MAX(1, COALESCE((SELECT species_ranges.abundance FROM species_ranges "
        "WHERE species_ranges.species_entity_id = catch_grounds.source_entity_id "
        "AND species_ranges.region_entity_id = catch_grounds.region_entity_id), 1)), collapsed = 0 "
        "WHERE ground IN ('trapping', 'fowling')"
    )
    op.execute(
        "UPDATE catch_grounds SET first_stock = MAX(1, COALESCE((SELECT resource_profiles.initial_reserve FROM resource_profiles "
        "WHERE resource_profiles.resource_entity_id = catch_grounds.source_entity_id), 100)) "
        "WHERE ground IN ('fishery', 'marine_hunt')"
    )


def downgrade() -> None:
    with op.batch_alter_table("catch_grounds", schema=None) as batch_op:
        batch_op.drop_constraint(op.f("ck_catch_grounds_first_stock_min"), type_="check")
        batch_op.drop_column("first_stock")
