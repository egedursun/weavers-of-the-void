import sqlalchemy as sa
from alembic import op

revision = "c6e8a0b2d4f3"
down_revision = "b5d7f9a1c3e2"
branch_labels = None
depends_on = None

PHYSICS_DEFAULTS = (
    ("melting_point", 100),
    ("ignition_point", 100),
    ("boiling_point", 100),
    ("density", 50),
    ("impact_yield", 50),
    ("impact_fracture", 50),
    ("shear_yield", 50),
    ("shear_fracture", 50),
    ("elasticity", 0),
    ("thermal_conductivity", 50),
    ("solid_density", 50),
    ("max_edge", 0),
)


def upgrade() -> None:
    with op.batch_alter_table("world_materials", schema=None) as batch_op:
        for column, default in PHYSICS_DEFAULTS:
            batch_op.add_column(sa.Column(column, sa.Integer(), server_default=str(default), nullable=False))
            batch_op.create_check_constraint(f"{column}_range", f"{column} BETWEEN 0 AND 100")


def downgrade() -> None:
    with op.batch_alter_table("world_materials", schema=None) as batch_op:
        for column, _ in PHYSICS_DEFAULTS:
            batch_op.drop_constraint(f"{column}_range", type_="check")
            batch_op.drop_column(column)
