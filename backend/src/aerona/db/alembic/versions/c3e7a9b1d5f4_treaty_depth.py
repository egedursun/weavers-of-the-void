import sqlalchemy as sa
from alembic import op

revision = "c3e7a9b1d5f4"
down_revision = "b2d6f8a0c4e3"
branch_labels = None
depends_on = None

OLD_STATUS = ("in_force", "fulfilled", "broken", "expired")
NEW_STATUS = (*OLD_STATUS, "proposed", "rejected")


def enum_of(name: str, values: tuple[str, ...]) -> sa.Enum:
    return sa.Enum(*values, name=name, native_enum=False, create_constraint=True, length=40)


def upgrade() -> None:
    with op.batch_alter_table("treaty_profiles", schema=None) as batch_op:
        batch_op.alter_column("status", existing_type=enum_of("status", OLD_STATUS), type_=enum_of("status", NEW_STATUS), existing_nullable=False)
        batch_op.add_column(sa.Column("proposed_by_node_id", sa.Integer(), nullable=True))
        batch_op.create_foreign_key(op.f("fk_treaty_profiles_proposed_by_node_id_nodes"), "nodes", ["proposed_by_node_id"], ["id"], ondelete="SET NULL")
    for table in ("vassalages", "treaty_clauses"):
        with op.batch_alter_table(table, schema=None) as batch_op:
            batch_op.add_column(sa.Column("locked", sa.JSON(), nullable=False, server_default="[]"))


def downgrade() -> None:
    for table in ("vassalages", "treaty_clauses"):
        with op.batch_alter_table(table, schema=None) as batch_op:
            batch_op.drop_column("locked")
    op.execute("UPDATE treaty_profiles SET status = 'expired' WHERE status IN ('proposed', 'rejected')")
    with op.batch_alter_table("treaty_profiles", schema=None) as batch_op:
        batch_op.drop_constraint(op.f("fk_treaty_profiles_proposed_by_node_id_nodes"), type_="foreignkey")
        batch_op.drop_column("proposed_by_node_id")
        batch_op.alter_column("status", existing_type=enum_of("status", NEW_STATUS), type_=enum_of("status", OLD_STATUS), existing_nullable=False)
